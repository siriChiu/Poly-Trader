#!/usr/bin/env python3
r"""
回填多特徵歷史走勢 v1

功能：
1. 用 rolling window 正確重算所有歷史特徵（避免 use future data）
2. 計算每個 timestamp 的 8 特徵分數（0~1 正規化）
3. 寫入 DB

用法：
  cd POLY_TRADER_ROOT
  python scripts/backfill_senses.py

輸出：
  進度 + 最終統計
"""

import sys
import math
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from database.models import RawMarketData, FeaturesNormalized
from server.senses import normalize_feature
from utils.logger import setup_logger

logger = setup_logger(__name__)

SYMBOL = "BTCUSDT"
MAX_FEATURES = 336  # 最大需要的 lookback window


def load_raw(session: Session) -> pd.DataFrame:
    """讀取原始數據，按時間排序。"""
    rows = (
        session.query(RawMarketData)
        .filter(RawMarketData.symbol == SYMBOL)
        .order_by(RawMarketData.timestamp.asc())
        .all()
    )
    if not rows:
        logger.warning("無原始數據")
        return pd.DataFrame()

    data = []
    for r in rows:
        data.append({
            "timestamp": r.timestamp,
            "close_price": r.close_price,
            "volume": r.volume,
            "funding_rate": r.funding_rate,
            "fear_greed_index": r.fear_greed_index,
            "stablecoin_mcap": r.stablecoin_mcap,
            "polymarket_prob": r.polymarket_prob,
            "eye_dist": r.eye_dist,
            "ear_prob": r.ear_prob,
            "tongue_sentiment": getattr(r, "tongue_sentiment", None),
            "volatility": getattr(r, "volatility", None),
            "oi_roc": getattr(r, "oi_roc", None),
        })
    return pd.DataFrame(data)


def compute_features_rolling(window: pd.DataFrame) -> dict:
    """
    對一個 rolling window 計算 8 個特徵。
    邏輯與 preprocessor.compute_features_from_raw 完全一致。
    """
    n = len(window)
    if n < 10:
        return None

    close = window["close_price"].dropna().astype(float)
    returns = close.pct_change()
    fr = window["funding_rate"].dropna().astype(float) if "funding_rate" in window.columns else pd.Series(dtype=float)
    vol = window["volume"].dropna().astype(float) if "volume" in window.columns else pd.Series(dtype=float)

    feat = {"timestamp": window.iloc[-1]["timestamp"]}

    # 1. Eye: fr_cumsum_48
    if len(fr) >= 48:
        feat["feat_eye_dist"] = float(fr.tail(48).sum())
    elif len(fr) >= 8:
        feat["feat_eye_dist"] = float(fr.sum())
    else:
        feat["feat_eye_dist"] = 0.0

    # 2. Ear: mom_24
    if len(close) >= 25:
        c24 = float(close.iloc[-25])
        feat["feat_ear_zscore"] = float(close.iloc[-1] / c24 - 1) if c24 > 0 else 0.0
    elif len(close) >= 13:
        c12 = float(close.iloc[-13])
        feat["feat_ear_zscore"] = float(close.iloc[-1] / c12 - 1) if c12 > 0 else 0.0
    else:
        feat["feat_ear_zscore"] = 0.0

    # 3. Nose: rsi14_norm
    if len(close) >= 15:
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        last_loss = float(loss.iloc[-1]) if not loss.empty else 1e-9
        last_gain = float(gain.iloc[-1]) if not gain.empty else 0.0
        rsi = 100.0 if last_loss <= 0 else 100 - 100 / (1 + last_gain / last_loss)
        feat["feat_nose_sigmoid"] = float(rsi) / 100.0
    else:
        feat["feat_nose_sigmoid"] = 0.5

    # 4. Tongue: vol_ratio_24_144
    if len(returns) >= 144:
        vol24 = float(returns.iloc[-24:].std())
        vol144 = float(returns.iloc[-144:].std())
        feat["feat_tongue_pct"] = float(vol24 / (vol144 + 1e-10))
    elif len(returns) >= 24:
        vol_short = float(returns.iloc[-12:].std())
        vol_long = float(returns.std())
        feat["feat_tongue_pct"] = float(vol_short / (vol_long + 1e-10))
    else:
        feat["feat_tongue_pct"] = 1.0

    # 5. Body: vol_zscore_48
    if len(returns) >= 336:
        vol48 = float(returns.iloc[-48:].std())
        vol_hist = np.array([returns.iloc[max(0, i-48):i].std() for i in range(len(returns)-288, len(returns))])
        vol_hist = vol_hist[~np.isnan(vol_hist)]
        if len(vol_hist) > 5 and vol_hist.std() > 0:
            feat["feat_body_roc"] = float((vol48 - vol_hist.mean()) / vol_hist.std())
        else:
            feat["feat_body_roc"] = 0.0
    elif len(returns) >= 48:
        vol48 = float(returns.iloc[-48:].std())
        vol_all = float(returns.std())
        vol_all_std = float(returns.rolling(48).std().std()) if len(returns) >= 96 else 1e-9
        feat["feat_body_roc"] = float((vol48 - vol_all) / (vol_all_std + 1e-9))
    else:
        feat["feat_body_roc"] = 0.0

    # 6. Pulse: vol_spike12
    if len(vol) >= 12:
        vol_win = vol.iloc[-12:].values
        mean_v = float(vol_win[:-1].mean())
        std_v = float(vol_win[:-1].std()) + 1e-10
        vol_z = (float(vol_win[-1]) - mean_v) / std_v
        feat["feat_pulse"] = float(1 / (1 + math.exp(-vol_z / 2)))
    elif len(vol) >= 3:
        mean_v = float(vol.iloc[:-1].mean())
        std_v = float(vol.iloc[:-1].std()) + 1e-10
        vol_z = (float(vol.iloc[-1]) - mean_v) / std_v
        feat["feat_pulse"] = float(1 / (1 + math.exp(-vol_z / 2)))
    else:
        feat["feat_pulse"] = 0.5

    # 7. Aura: fr_abs_norm
    if "funding_rate" in window.columns:
        fr_all = window["funding_rate"].dropna().astype(float)
        if len(fr_all) >= 2:
            fr_abs = float(abs(fr_all.iloc[-1]))
            roll_len = min(96, len(fr_all))
            fr_max = float(fr_all.abs().rolling(roll_len).max().iloc[-1]) + 1e-10
            feat["feat_aura"] = float(fr_abs / fr_max)
        else:
            feat["feat_aura"] = 0.0
    else:
        feat["feat_aura"] = 0.0

    # 8. Mind: ret_144
    if len(close) >= 145:
        feat["feat_mind"] = float(close.iloc[-1] / close.iloc[-145] - 1)
    elif len(close) >= 25:
        feat["feat_mind"] = float(close.iloc[-1] / close.iloc[-25] - 1)
    else:
        feat["feat_mind"] = 0.0

    return feat


def score_all_senses(features: dict) -> dict:
    """將 8 個 raw 特徵轉為 0~1 特徵分數。"""
    mapping = {
        "eye": "feat_eye_dist",
        "ear": "feat_ear_zscore",
        "nose": "feat_nose_sigmoid",
        "tongue": "feat_tongue_pct",
        "body": "feat_body_roc",
        "pulse": "feat_pulse",
        "aura": "feat_aura",
        "mind": "feat_mind",
    }
    return {
        sense: normalize_feature(features.get(feat), feat)
        for sense, feat in mapping.items()
    }


def main():
    from server.dependencies import get_db

    print(f"\n{'='*60}")
    print(f"  多特徵歷史回填 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
    print(f"{'='*60}\n")

    session = get_db()

    # 1. 讀原始
    df = load_raw(session)
    print(f"[1/3] 原始數據: {len(df)} 筆")
    if len(df) < 10:
        print("  數據量不足，跳過回填")
        return

    # 2. 統計現有特徵
    existing_count = session.query(FeaturesNormalized).count()
    print(f"[2/3] 現有特徵筆數: {existing_count}")

    # 3. Rolling window 回填
    feat_keys = ["feat_eye_dist", "feat_ear_zscore", "feat_nose_sigmoid",
                 "feat_tongue_pct", "feat_body_roc", "feat_pulse",
                 "feat_aura", "feat_mind"]
    sense_keys = ["eye", "ear", "nose", "tongue", "body", "pulse", "aura", "mind"]

    saved = 0
    updated = 0
    skipped = 0
    failed = 0

    min_window = 10
    total = len(df)
    batch = 0

    print(f"[3/3] 開始回填... (total={total} rows, min_window={min_window})")

    for end_idx in range(min_window, total + 1):
        window = df.iloc[:end_idx].tail(MAX_FEATURES)  # 最多看 MAX_FEATURES 筆
        ts = window.iloc[-1]["timestamp"]

        feat = compute_features_rolling(window)
        if not feat:
            failed += 1
            continue

        existing = (
            session.query(FeaturesNormalized)
            .filter(FeaturesNormalized.timestamp == ts)
            .first()
        )

        if existing:
            # 更新既有
            for k in feat_keys:
                setattr(existing, k, feat.get(k))
            updated += 1
        else:
            # 新增
            record = FeaturesNormalized(
                timestamp=ts,
                **{k: feat.get(k) for k in feat_keys}
            )
            session.add(record)
            saved += 1

        batch += 1
        if batch % 500 == 0:
            session.commit()
            pct = end_idx / total * 100
            print(f"  進度: {end_idx}/{total} ({pct:.0f}%) | 新增={saved} 更新={updated} 跳過={skipped}")

    session.commit()

    # 4. 統計
    final_count = session.query(FeaturesNormalized).count()

    # 讀取最後一筆特徵，計算 sense scores
    last_feat_row = (
        session.query(FeaturesNormalized)
        .order_by(FeaturesNormalized.timestamp.desc())
        .first()
    )
    latest_sense_scores = {}
    if last_feat_row:
        feat_dict = {
            "feat_eye_dist": last_feat_row.feat_eye_dist,
            "feat_ear_zscore": last_feat_row.feat_ear_zscore,
            "feat_nose_sigmoid": last_feat_row.feat_nose_sigmoid,
            "feat_tongue_pct": last_feat_row.feat_tongue_pct,
            "feat_body_roc": last_feat_row.feat_body_roc,
            "feat_pulse": last_feat_row.feat_pulse,
            "feat_aura": last_feat_row.feat_aura,
            "feat_mind": last_feat_row.feat_mind,
        }
        latest_sense_scores = score_all_senses(feat_dict)

    print(f"\n{'='*60}")
    print(f"  回填完成!")
    print(f"{'='*60}")
    print(f"  新增: {saved} 筆")
    print(f"  更新: {updated} 筆")
    print(f"  失敗: {failed} 筆")
    print(f"  特徵總計: {final_count} 筆")
    if latest_sense_scores:
        print("\n  最新特徵分數:")
        emoji_map = {"eye": "[Eye]", "ear": "[Ear]", "nose": "[Nose]", "tongue": "[Tongue]",
                     "body": "[Body]", "pulse": "[Pulse]", "aura": "[Aura]", "mind": "[Mind]"}
        for s in sense_keys:
            val = latest_sense_scores[s]
            print(f"    {emoji_map.get(s, s)}: {val:.4f}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
