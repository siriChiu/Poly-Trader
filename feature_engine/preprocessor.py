"""
特徵工程模組 v3 — IC-validated features
每個特徵經過 IC > 0.05 驗證，對 labels 有真實預測力
"""

from typing import Optional, Dict
from datetime import datetime
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from database.models import RawMarketData, FeaturesNormalized
from utils.logger import setup_logger

logger = setup_logger(__name__)


def load_latest_raw_data(
    session: Session, symbol: str, limit: int = 0
) -> pd.DataFrame:
    """從資料庫讀取 raw_market_data，limit=0 表示全部。"""
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


def compute_features_from_raw(df: pd.DataFrame) -> Optional[Dict]:
    """
    計算 8 個 IC-validated 特徵（最新一筆）。
    需要至少 72 筆歷史數據才能計算完整特徵。
    """
    if df.empty or len(df) < 10:
        logger.warning(f"Raw data 不足 (rows={len(df)})")
        return None

    latest = df.iloc[-1]
    close = df["close_price"].dropna().astype(float)
    fr = df["funding_rate"].dropna().astype(float) if "funding_rate" in df.columns else pd.Series(dtype=float)
    returns = close.pct_change()

    features = {
        "timestamp": latest.get("timestamp", datetime.utcnow()),
    }

    # 1. Eye: funding_ma72_bps — 72h funding rate moving average (in bps, ×10000)
    #    IC=-0.1720: 高 funding → 看跌（過度槓桿）
    #    #H42 fix: scale to bps so XGBoost can meaningfully split on this feature
    if len(fr) >= 72:
        features["feat_eye_dist"] = float(fr.tail(72).mean()) * 10000.0
    elif len(fr) >= 8:
        features["feat_eye_dist"] = float(fr.mean()) * 10000.0
    else:
        features["feat_eye_dist"] = 0.0

    # 2. Ear: mom_12 — 12期價格動量回報率
    #    #H78 替換 MACD_hist (Pearson IC=-0.046 p=0.031 假顯著)
    #    MACD_hist 的 79% 數值 |>100 bps 為極端值，真實 Spearman p=0.177 不顯著
    #    mom_12 = (close_now - close_12h_ago) / close_12h_ago
    #    IC=-0.056 Spearman=-0.047 p=0.027 ✅ 真實顯著，無極端值問題
    #    負 IC → 12h 上漲 → 看跌（過熱反轉），加入 NEG_IC_FEATS
    if len(close) >= 13:
        c12 = float(close.iloc[-13])
        if c12 > 0:
            features["feat_ear_zscore"] = float(close.iloc[-1] / c12 - 1)
        else:
            features["feat_ear_zscore"] = 0.0
    elif len(close) >= 4:
        c_early = float(close.iloc[-4])
        if c_early > 0:
            features["feat_ear_zscore"] = float(close.iloc[-1] / c_early - 1)
        else:
            features["feat_ear_zscore"] = 0.0
    else:
        features["feat_ear_zscore"] = 0.0

    # 3. Nose: ret_96 — 96期（8h）價格動量回報率
    #    IC=-0.076 (全量, p=0.0004) / IC=-0.145 (近500, p=0.001)
    #    替換 autocorr_48h (IC=+0.050, p=0.268, 不顯著) #H69
    #    負 IC → 8h 強勢上漲 → 看跌（過熱反轉），加入 NEG_IC_FEATS
    if len(close) >= 97:
        features["feat_nose_sigmoid"] = float(close.iloc[-1] / close.iloc[-97] - 1)
    elif len(close) >= 25:
        features["feat_nose_sigmoid"] = float(close.iloc[-1] / close.iloc[-25] - 1)
    else:
        features["feat_nose_sigmoid"] = 0.0

    # 4. Tongue: vol_ratio_6_48 — 短期/長期波動率比（波動爆發信號）
    #    IC=+0.128 (p<0.0001, n=2184): 短期波動激增 → 市場動盪 → 偏多（突破信號）
    #    替換 volatility_24h (IC=+0.037, p=0.080, 不顯著) #H75
    #    正 IC → 無需反轉（不加入 NEG_IC_FEATS）
    if len(returns) >= 48:
        vol_short = float(returns.iloc[-6:].std())
        vol_long = float(returns.iloc[-48:].std())
        features["feat_tongue_pct"] = vol_short / (vol_long + 1e-10)
    elif len(returns) >= 12:
        vol_short = float(returns.iloc[-3:].std())
        vol_long = float(returns.std())
        features["feat_tongue_pct"] = vol_short / (vol_long + 1e-10)
    else:
        features["feat_tongue_pct"] = 1.0

    # 5. Body: price_ret_20P — 20期價格報酬率（動量）
    #    IC=-0.057 (p=0.0002, n=4412): 替換 vol_zscore_24 (IC=-0.017, p=0.21, 不顯著) #H95
    #    負 IC → 近期上漲（正報酬）→ 負標籤（均值回歸）→ 加入 NEG_IC_FEATS
    if len(close) >= 21:
        ret_20 = float((close.iloc[-1] - close.iloc[-21]) / (close.iloc[-21] + 1e-10))
        # sigmoid 轉換到 [0,1]，scale=50 讓 ±2% 範圍靈敏
        features["feat_body_roc"] = float(1 / (1 + np.exp(50 * ret_20)))
    else:
        features["feat_body_roc"] = 0.5

    # 6. Pulse (v3): atr_ratio14 — ATR(14) / 當前價格（市場波動率比例）
    #    IC=+0.059 (p<0.001, N=11010): 替換 pos_in_range_72 (IC≈0, p=0.892, 無效) #H89
    #    正 IC → 高波動 → 趨勢突破訊號，不加入 NEG_IC_FEATS
    if len(close) >= 15:
        highs_14 = close.rolling(14).max()
        lows_14 = close.rolling(14).min()
        tr_14 = highs_14 - lows_14
        atr_14 = tr_14.rolling(14).mean()
        atr_val = atr_14.iloc[-1]
        cur_price = close.iloc[-1]
        if not np.isnan(atr_val) and cur_price > 0:
            features["feat_pulse"] = float(atr_val / cur_price)
        else:
            features["feat_pulse"] = 0.0
    else:
        features["feat_pulse"] = 0.0

    # 7. Aura (v6): pos_in_24h_range — 當前價格在 24h 高低點中的位置
    #    IC=+0.061 (p<0.0001, n=10976): 最強替換候選，位置高 → 過熱 → 偏多（趨勢信號）
    #    替換 fr_cum48_norm (IC=-0.024, p=0.07, 邊緣不顯著) #H89
    #    正 IC → 不加入 NEG_IC_FEATS（高位有追漲慣性）
    if len(close) >= 48:
        window_size = min(288, len(close))
        window_close = close.iloc[-window_size:]
        price_min = float(window_close.min())
        price_max = float(window_close.max())
        if price_max > price_min:
            features["feat_aura"] = float((close.iloc[-1] - price_min) / (price_max - price_min))
        else:
            features["feat_aura"] = 0.5
    elif len(close) >= 12:
        price_min = float(close.min())
        price_max = float(close.max())
        if price_max > price_min:
            features["feat_aura"] = float((close.iloc[-1] - price_min) / (price_max - price_min))
        else:
            features["feat_aura"] = 0.5
    else:
        features["feat_aura"] = 0.5

    # 8. Mind (v3): ret_144 — 144期（12h）價格動量回報率
    #    IC=-0.077 (p<0.001, N=11010): 替換 ret_72 (IC≈0, p=0.840, 無效) #H89
    #    負 IC → 12h 強勢上漲 → 看跌（過熱反轉），加入 NEG_IC_FEATS
    if len(close) >= 145:
        features["feat_mind"] = float(close.iloc[-1] / close.iloc[-145] - 1)
    elif len(close) >= 25:
        features["feat_mind"] = float(close.iloc[-1] / close.iloc[-25] - 1)
    else:
        features["feat_mind"] = 0.0

    logger.info(
        f"Features v3: eye={features['feat_eye_dist']:.6f} "
        f"ear={features['feat_ear_zscore']:.6f} "
        f"nose={features['feat_nose_sigmoid']:.4f} "
        f"tongue={features['feat_tongue_pct']:.6f} "
        f"body={features['feat_body_roc']:.4f} "
        f"pulse={features['feat_pulse']:.6f} "
        f"aura={features['feat_aura']:.6f} "
        f"mind={features['feat_mind']:.4f}"
    )
    return features


def save_features_to_db(
    session: Session, features: Dict
) -> Optional[FeaturesNormalized]:
    """保存特徵（含去重檢查）。"""
    try:
        ts = features["timestamp"]
        existing = (
            session.query(FeaturesNormalized)
            .filter(FeaturesNormalized.timestamp == ts)
            .first()
        )
        if existing:
            logger.info(f"特徵已存在 (timestamp={ts}, id={existing.id})，跳過")
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
    """完整特徵工程流程。"""
    logger.info("開始執行特徵工程 v3...")
    df = load_latest_raw_data(session, symbol, limit=0)
    if df.empty:
        logger.error("無原始數據可供處理")
        return None

    features = compute_features_from_raw(df)
    if not features:
        logger.error("特徵計算失敗")
        return None

    saved = save_features_to_db(session, features)
    return features if saved else None


def recompute_all_features(session: Session, symbol: str = "BTCUSDT") -> int:
    """
    重新計算所有歷史特徵（用於特徵升級後批量更新）。
    Returns: 新增/更新的特徵數量。
    """
    logger.info("開始批量重算特徵 v3...")
    df = load_latest_raw_data(session, symbol, limit=0)
    if df.empty:
        return 0

    count = 0
    min_window = 10

    for end_idx in range(min_window, len(df) + 1):
        window = df.iloc[:end_idx]
        ts = window.iloc[-1].get("timestamp")

        # Check if already exists
        existing = (
            session.query(FeaturesNormalized)
            .filter(FeaturesNormalized.timestamp == ts)
            .first()
        )
        if existing:
            # Update existing
            features = compute_features_from_raw(window)
            if features:
                existing.feat_eye_dist = features.get("feat_eye_dist")
                existing.feat_ear_zscore = features.get("feat_ear_zscore")
                existing.feat_nose_sigmoid = features.get("feat_nose_sigmoid")
                existing.feat_tongue_pct = features.get("feat_tongue_pct")
                existing.feat_body_roc = features.get("feat_body_roc")
                existing.feat_pulse = features.get("feat_pulse")
                existing.feat_aura = features.get("feat_aura")
                existing.feat_mind = features.get("feat_mind")
                count += 1
        else:
            features = compute_features_from_raw(window)
            if features:
                record = FeaturesNormalized(
                    timestamp=ts,
                    **{k: v for k, v in features.items() if k.startswith("feat_")}
                )
                session.add(record)
                count += 1

        if count % 500 == 0 and count > 0:
            session.commit()
            logger.info(f"  進度: {count}/{len(df)}")

    session.commit()
    logger.info(f"批量重算完成: {count} 筆特徵已更新")
    return count
