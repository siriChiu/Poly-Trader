"""
特徵工程模組 v4 — multi-sense, sell-win aware, versioned
"""

from typing import Optional, Dict
from datetime import datetime
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from database.models import RawMarketData, FeaturesNormalized
from utils.logger import setup_logger

logger = setup_logger(__name__)

FEATURE_VERSION = "v4-multi-sense"


def load_latest_raw_data(session: Session, symbol: str, limit: int = 0) -> pd.DataFrame:
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
    if df.empty or len(df) < 10:
        logger.warning(f"Raw data 不足 (rows={len(df)})")
        return None

    latest = df.iloc[-1]
    close = df["close_price"].dropna().astype(float)
    returns = close.pct_change().replace([np.inf, -np.inf], np.nan)
    fr = df["funding_rate"].dropna().astype(float) if "funding_rate" in df.columns else pd.Series(dtype=float)
    vol = df["volume"].dropna().astype(float) if "volume" in df.columns else pd.Series(dtype=float)
    pm = df["polymarket_prob"].dropna().astype(float) if "polymarket_prob" in df.columns else pd.Series(dtype=float)
    fgi = df["fear_greed_index"].dropna().astype(float) if "fear_greed_index" in df.columns else pd.Series(dtype=float)

    features = {"timestamp": latest.get("timestamp", datetime.utcnow()), "symbol": latest.get("symbol", None) or "BTCUSDT"}

    features["feat_eye"] = float(fr.tail(48).sum()) if len(fr) >= 48 else float(fr.sum()) if len(fr) > 0 else 0.0
    if len(close) >= 25:
        c24 = float(close.iloc[-25]); features["feat_ear"] = float(close.iloc[-1] / c24 - 1) if c24 > 0 else 0.0
    else:
        features["feat_ear"] = 0.0
    if len(close) >= 15:
        delta = close.diff(); gain = delta.clip(lower=0).rolling(14).mean(); loss = (-delta.clip(upper=0)).rolling(14).mean()
        last_loss = float(loss.iloc[-1]) if not loss.empty else 1e-9; last_gain = float(gain.iloc[-1]) if not gain.empty else 0.0
        rsi = 100 - 100 / (1 + last_gain / last_loss) if last_loss > 0 else 100.0
        features["feat_nose"] = float(rsi) / 100.0
    else:
        features["feat_nose"] = 0.5
    if len(returns) >= 24:
        vol_short = float(returns.iloc[-12:].std()); vol_long = float(returns.iloc[-24:].std()) if len(returns) >= 24 else float(returns.std())
        features["feat_tongue"] = float(vol_short / (vol_long + 1e-10)) if np.isfinite(vol_long) and vol_long != 0 else 1.0
    else:
        features["feat_tongue"] = 1.0
    if len(returns) >= 48:
        pos = (close.iloc[-1] - close.iloc[-48:].min()) / (close.iloc[-48:].max() - close.iloc[-48:].min() + 1e-10)
        features["feat_body"] = float(pos)
    else:
        features["feat_body"] = 0.5
    if len(vol) >= 12:
        vwin = vol.tail(12)
        features["feat_pulse"] = float((vwin.iloc[-1] - vwin.iloc[:-1].mean()) / (vwin.iloc[:-1].std() + 1e-10))
    else:
        features["feat_pulse"] = 0.0
    if len(fr) >= 2:
        features["feat_aura"] = float(abs(fr.iloc[-1]) / (fr.abs().rolling(min(96, len(fr))).max().iloc[-1] + 1e-10))
    else:
        features["feat_aura"] = 0.0
    if len(close) >= 145:
        features["feat_mind"] = float(close.iloc[-1] / close.iloc[-145] - 1)
    elif len(close) >= 25:
        features["feat_mind"] = float(close.iloc[-1] / close.iloc[-25] - 1)
    else:
        features["feat_mind"] = 0.0

    pm_last = float(pm.iloc[-1]) if len(pm) else 0.5
    pm_prev = float(pm.iloc[-2]) if len(pm) >= 2 else pm_last
    fgi_last = float(fgi.iloc[-1]) if len(fgi) else 50.0
    features["feat_whisper"] = float(np.log1p(len(df)) / 10.0)
    features["feat_tone"] = float(np.tanh((fgi_last - 50.0) / 20.0))
    features["feat_chorus"] = float(1.0 - min(1.0, np.nanstd([features["feat_tone"], features["feat_whisper"]]) + 0.0))
    features["feat_hype"] = float(np.clip((vol.tail(12).iloc[-1] / (vol.tail(48).mean() + 1e-10)) if len(vol) >= 12 else 0.0, 0.0, 5.0) / 5.0)
    features["feat_oracle"] = float(pm_last - pm_prev)
    features["feat_shock"] = float(abs(features["feat_oracle"]) + abs(features["feat_tone"]))
    features["feat_tide"] = float(np.tanh(features["feat_eye"] + features["feat_mind"]))
    features["feat_storm"] = float(np.clip(abs(features["feat_pulse"]) + abs(features["feat_shock"]), 0.0, 5.0) / 5.0)
    features["regime_label"] = "trend" if features["feat_ear"] > 0.03 else "panic" if features["feat_shock"] > 0.5 else "chop"
    features["feature_version"] = FEATURE_VERSION

    logger.info(
        f"Features v4: eye={features['feat_eye']:.6f} ear={features['feat_ear']:.6f} nose={features['feat_nose']:.4f} "
        f"whisper={features['feat_whisper']:.4f} oracle={features['feat_oracle']:.6f} tide={features['feat_tide']:.4f}"
    )
    return features


def save_features_to_db(session: Session, features: Dict) -> Optional[FeaturesNormalized]:
    try:
        ts = features["timestamp"]
        symbol = features.get("symbol", "BTCUSDT")
        existing = (
            session.query(FeaturesNormalized)
            .filter(FeaturesNormalized.timestamp == ts, FeaturesNormalized.symbol == symbol)
            .first()
        )
        if existing:
            for k, v in features.items():
                if hasattr(existing, k):
                    setattr(existing, k, v)
            session.commit()
            return existing

        record = FeaturesNormalized(
            timestamp=ts,
            symbol=symbol,
            feat_eye=features.get("feat_eye"),
            feat_ear=features.get("feat_ear"),
            feat_nose=features.get("feat_nose"),
            feat_tongue=features.get("feat_tongue"),
            feat_body=features.get("feat_body"),
            feat_pulse=features.get("feat_pulse"),
            feat_aura=features.get("feat_aura"),
            feat_mind=features.get("feat_mind"),
            feat_whisper=features.get("feat_whisper"),
            feat_tone=features.get("feat_tone"),
            feat_chorus=features.get("feat_chorus"),
            feat_hype=features.get("feat_hype"),
            feat_oracle=features.get("feat_oracle"),
            feat_shock=features.get("feat_shock"),
            feat_tide=features.get("feat_tide"),
            feat_storm=features.get("feat_storm"),
            regime_label=features.get("regime_label"),
            feature_version=features.get("feature_version"),
        )
        session.add(record)
        session.commit()
        return record
    except Exception as e:
        session.rollback()
        logger.error(f"保存特徵失敗: {e}")
        return None


def run_preprocessor(session: Session, symbol: str = "BTCUSDT") -> Optional[Dict]:
    logger.info("開始執行特徵工程 v4...")
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
