"""
特徵工程模組：將原始 market data 轉換為標準化特徵
支援 ROC、Z-score、Sigmoid 壓縮等正規化方法
"""

from typing import Optional, Dict
from datetime import datetime
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from database.models import RawMarketData, FeaturesNormalized
from utils.logger import setup_logger

logger = setup_logger(__name__)


def sigmoid(x: float) -> float:
    """Sigmoid 函數"""
    return 1 / (1 + np.exp(-x))


def load_latest_raw_data(
    session: Session, symbol: str, limit: int = 0
) -> pd.DataFrame:
    """從資料庫讀取 raw_market_data（含 eye_dist, ear_prob）。
    limit=0 表示載入全部記錄（用於 ear_zscore 全局統計）。
    """
    query = (
        session.query(RawMarketData)
        .filter(RawMarketData.symbol == symbol)
        .order_by(RawMarketData.timestamp.asc())
    )
    if limit > 0:
        query = query.limit(limit)
    rows = query.all()
    if not rows:
        return pd.DataFrame()

    data = []
    for r in rows:
        data.append({
            "timestamp": r.timestamp,
            "close_price": r.close_price,
            "funding_rate": r.funding_rate,
            "fear_greed_index": r.fear_greed_index,
            "stablecoin_mcap": r.stablecoin_mcap,
            "polymarket_prob": r.polymarket_prob,
            "eye_dist": r.eye_dist,
            "ear_prob": r.ear_prob,
            "tongue_sentiment": getattr(r, "tongue_sentiment", None),
        })
    return pd.DataFrame(data)


def compute_features_from_raw(df: pd.DataFrame) -> Optional[Dict]:
    """
    從原始數據計算五感特徵（最新一筆）。
    需要多筆歷史數據才能計算 Z-score 等滾動特徵。
    """
    if df.empty:
        logger.warning("Raw data 為空")
        return None

    latest = df.iloc[-1]
    n_rows = len(df)

    features = {
        "timestamp": latest.get("timestamp", datetime.utcnow()),
        "feat_eye_dist": None,
        "feat_ear_zscore": None,
        "feat_nose_sigmoid": None,
        "feat_tongue_pct": None,
        "feat_body_roc": None,
        "feat_pulse": None,
        "feat_aura": None,
        "feat_mind": None,
    }

    # 1. Eye: eye_dist 使用歷史 min-max 正規化到 -1~1
    eye_val = latest.get("eye_dist")
    if pd.notna(eye_val) and eye_val is not None:
        eye_val = float(eye_val)
        if "eye_dist" in df.columns:
            eye_hist = df["eye_dist"].dropna()
            if len(eye_hist) >= 2:
                e_min = eye_hist.min()
                e_max = eye_hist.max()
                if e_max > e_min:
                    # Min-max to 0~1, then scale to -1~1
                    features["feat_eye_dist"] = float(2 * (eye_val - e_min) / (e_max - e_min) - 1)
                else:
                    features["feat_eye_dist"] = 0.0
            else:
                features["feat_eye_dist"] = 0.0
        else:
            features["feat_eye_dist"] = eye_val

    # 2. Ear: Funding Rate 短期 Z-score（取代 ear_prob，因 ear_prob 壓縮後近零變異）
    #    使用 funding_rate 的短期波動作為市場「聲音」
    if "funding_rate" in df.columns:
        fr_series = df["funding_rate"].dropna().astype(float)
        if len(fr_series) >= 10:
            # 用最近 50 筆計算 rolling stats，再取最新值的 zscore
            window = min(50, len(fr_series))
            recent_fr = fr_series.tail(window)
            mean = recent_fr.mean()
            std = recent_fr.std()
            current = float(latest["funding_rate"])
            if pd.notna(current) and std > 0:
                import math
                z = (current - mean) / std
                features["feat_ear_zscore"] = float(math.tanh(z / 2))  # tanh(z/2) → -1~1, z=±2→±0.76
            else:
                features["feat_ear_zscore"] = 0.0
        elif len(fr_series) >= 2:
            mean = fr_series.mean()
            std = fr_series.std()
            current = float(latest["funding_rate"])
            if pd.notna(current) and std > 0:
                import math
                z = (current - mean) / std
                features["feat_ear_zscore"] = float(math.tanh(z / 2))
            else:
                features["feat_ear_zscore"] = 0.0

    # 3. Nose: OI ROC (取代 funding_rate, 解除與 Ear 的洩漏)
    oi_val = latest.get("stablecoin_mcap")
    if pd.notna(oi_val) and oi_val is not None:
        features["feat_nose_sigmoid"] = float(oi_val)

    # 4. Tongue: 情緒綜合分數 v2（-1~1，直接使用）
    tongue_val = latest.get("tongue_sentiment")
    if pd.notna(tongue_val) and tongue_val is not None:
        features["feat_tongue_pct"] = float(tongue_val)
    else:
        # Fallback: 舊版 FNG 百分比
        fng_val = latest.get("fear_greed_index")
        if pd.notna(fng_val) and fng_val is not None:
            features["feat_tongue_pct"] = float(fng_val) / 100.0

    # 5. Body: stablecoin_mcap 已存為 ROC 值，使用連續值（不離散化）
    roc_val = latest.get("stablecoin_mcap")
    if pd.notna(roc_val) and roc_val is not None:
        features["feat_body_roc"] = float(roc_val)

    # 6. Pulse: 20-period return volatility z-score
    if "close_price" in df.columns:
        closes = df["close_price"].dropna()
        if len(closes) >= 20:
            returns = closes.pct_change().dropna()
            if len(returns) >= 20:
                vol = returns.tail(20).std()
                vol_window = []
                for i in range(19, len(returns)):
                    chunk = returns.iloc[max(0,i-19):i+1]
                    vol_window.append(chunk.std())
                if len(vol_window) >= 10:
                    v_mean = np.mean(vol_window[:-1])
                    v_std = np.std(vol_window[:-1])
                    if v_std > 0:
                        z = (vol - v_mean) / v_std
                        features["feat_pulse"] = float(np.tanh(z / 2))

    # 7. Aura: funding_rate * price_roc divergence
    fr_val = latest.get("funding_rate")
    if pd.notna(fr_val) and fr_val is not None:
        closes2 = df["close_price"].dropna()
        if len(closes2) >= 2:
            prev_close = float(closes2.iloc[-2])
            curr_close = float(closes2.iloc[-1])
            price_roc = (curr_close - prev_close) / prev_close if prev_close > 0 else 0
            product = float(fr_val) * price_roc
            if product >= 0:
                features["feat_aura"] = float(np.tanh(product * 10000) * 0.3)
            else:
                features["feat_aura"] = float(-np.tanh(product * 10000) * 0.6)

    return features


def save_features_to_db(
    session: Session, features: Dict
) -> Optional[FeaturesNormalized]:
    """將特徵保存為 FeaturesNormalized 記錄（含去重檢查）。"""
    try:
        ts = features["timestamp"]
        # 去重：若相同時間戳已存在，跳過
        existing = (
            session.query(FeaturesNormalized)
            .filter(FeaturesNormalized.timestamp == ts)
            .first()
        )
        if existing:
            logger.info(f"特徵已存在 (timestamp={ts}, id={existing.id})，跳過重複寫入")
            return existing

        record = FeaturesNormalized(
            timestamp=ts,
            feat_eye_dist=features.get("feat_eye_dist"),
            feat_ear_zscore=features.get("feat_ear_zscore"),
            feat_nose_sigmoid=features.get("feat_nose_sigmoid"),
            feat_tongue_pct=features.get("feat_tongue_pct"),
            feat_body_roc=features.get("feat_body_roc"),
            feat_pulse=features.get("feat_pulse"),
            feat_aura=features.get("feat_aura"),
            feat_mind=features.get("feat_mind"),
        )
        session.add(record)
        session.commit()
        logger.info(f"特徵已保存: id={record.id}")
        return record
    except Exception as e:
        session.rollback()
        logger.error(f"保存特徵失敗: {e}")
        return None


def run_preprocessor(
    session: Session, symbol: str = "BTCUSDT"
) -> Optional[Dict]:
    """
    完整特徵工程流程：
    1. 讀取原始數據
    2. 計算標準化特徵
    3. 保存至資料庫
    """
    logger.info("開始執行特徵工程...")
    df = load_latest_raw_data(session, symbol, limit=0)
    if df.empty:
        logger.error("無原始數據可供處理")
        return None

    features = compute_features_from_raw(df)
    if not features:
        logger.error("特徵計算失敗")
        return None

    saved = save_features_to_db(session, features)
    if saved:
        logger.info(f"特徵計算完成: eye={features['feat_eye_dist']}, "
                     f"ear={features['feat_ear_zscore']}, "
                     f"nose={features['feat_nose_sigmoid']}, "
                     f"tongue={features['feat_tongue_pct']}, "
                     f"body={features['feat_body_roc']}")
        return features
    return None
