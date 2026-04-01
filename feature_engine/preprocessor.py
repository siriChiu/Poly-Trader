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

    # 2. Ear: momentum_48h — 48h 價格動量
    #    IC=-0.0937: 負動量 → 反轉信號
    if len(close) >= 49:
        features["feat_ear_zscore"] = float(close.iloc[-1] / close.iloc[-49] - 1)
    elif len(close) >= 12:
        features["feat_ear_zscore"] = float(close.iloc[-1] / close.iloc[-12] - 1)
    else:
        features["feat_ear_zscore"] = 0.0

    # 3. Nose: autocorr_48h — 48h 收益率自相關（regime 檢測）
    #    IC=-0.0712: 負自相關 → mean-reverting regime
    if len(returns) >= 49:
        recent = returns.iloc[-48:].dropna()
        if len(recent) > 5:
            ac = recent.autocorr(lag=1)
            features["feat_nose_sigmoid"] = float(ac) if not np.isnan(ac) else 0.0
        else:
            features["feat_nose_sigmoid"] = 0.0
    elif len(returns) >= 12:
        recent = returns.iloc[-11:].dropna()
        if len(recent) > 3:
            ac = recent.autocorr(lag=1)
            features["feat_nose_sigmoid"] = float(ac) if not np.isnan(ac) else 0.0
        else:
            features["feat_nose_sigmoid"] = 0.0
    else:
        features["feat_nose_sigmoid"] = 0.0

    # 4. Tongue: volatility_24h — 24h 波動率
    #    IC=-0.0560: 高波動 → 方向性不明，通常看跌
    if len(returns) >= 25:
        features["feat_tongue_pct"] = float(returns.iloc[-24:].std())
    elif len(returns) >= 6:
        features["feat_tongue_pct"] = float(returns.std())
    else:
        features["feat_tongue_pct"] = 0.0

    # 5. Body: macd_pct — MACD 背離百分比（EMA12 - EMA26）/ 當前價格 × 100
    #    IC=-0.070 (upgraded from range_pos_24h IC=+0.012, #H16)
    #    原理：MACD 負值 → 短期動能弱於長期 → 偏空（後續回升空間大）
    if len(close) >= 26:
        ema12 = close.ewm(span=12, adjust=False).mean().iloc[-1]
        ema26 = close.ewm(span=26, adjust=False).mean().iloc[-1]
        features["feat_body_roc"] = float((ema12 - ema26) / close.iloc[-1] * 100)
    else:
        features["feat_body_roc"] = 0.0

    # 6. Pulse: funding_trend_bps — funding rate 趨勢（24h MA - 72h MA，in bps ×10000）
    #    IC=-0.0669: 下降趨勢 → 看漲（槓桿冷卻）
    #    #H42 fix: scale to bps so XGBoost can meaningfully split on this feature
    if len(fr) >= 72:
        ma24 = fr.tail(24).mean()
        ma72 = fr.tail(72).mean()
        features["feat_pulse"] = float(ma24 - ma72) * 10000.0
    elif len(fr) >= 24:
        ma24 = fr.tail(24).mean()
        ma_all = fr.mean()
        features["feat_pulse"] = float(ma24 - ma_all) * 10000.0
    else:
        features["feat_pulse"] = 0.0

    # 7. Aura (v4): funding_zscore_288 — 長週期 funding rate z-score（288期≈1天）
    #    原理：相對長期基準的 funding 異常程度，捕捉大週期槓桿情緒
    #    IC=-0.0941（p=0.0007, n=1297），與 ear_zscore 相關僅 0.20（互補信號）
    #    屬於 NEG_IC_FEATS（反轉後使用）
    if len(fr) >= 288:
        window_288 = fr.iloc[-288:]
        mu_288 = float(window_288.mean())
        sigma_288 = float(window_288.std())
        if sigma_288 > 0:
            features["feat_aura"] = float((fr.iloc[-1] - mu_288) / sigma_288)
        else:
            features["feat_aura"] = 0.0
    elif len(fr) >= 48:
        mu = float(fr.mean())
        sigma = float(fr.std())
        if sigma > 0:
            features["feat_aura"] = float((fr.iloc[-1] - mu) / sigma)
        else:
            features["feat_aura"] = 0.0
    else:
        features["feat_aura"] = 0.0

    # 8. Mind: funding_z_24 — 24h funding rate z-score
    #    IC=+0.0619: 正 z-score → 多頭情緒
    if len(fr) >= 25:
        recent = fr.iloc[-24:]
        mean = recent.mean()
        std = recent.std()
        if std > 0:
            features["feat_mind"] = float((fr.iloc[-1] - mean) / std)
        else:
            features["feat_mind"] = 0.0
    elif len(fr) >= 8:
        mean = fr.mean()
        std = fr.std()
        if std > 0:
            features["feat_mind"] = float((fr.iloc[-1] - mean) / std)
        else:
            features["feat_mind"] = 0.0
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
