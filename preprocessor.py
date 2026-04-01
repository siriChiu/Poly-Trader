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
    從原始數據計算多感官特徵（最新一筆）。
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
    }

    # 1. Eye: eye_dist 直接使用（已為比例值）
    eye_val = latest.get("eye_dist")
    if pd.notna(eye_val) and eye_val is not None:
        features["feat_eye_dist"] = float(eye_val)

    # 2. Ear: ear_prob 的 Z-score（使用全局統計，與 recompute 一致）
    if "ear_prob" in df.columns:
        ear_series = df["ear_prob"].dropna()
        if len(ear_series) >= 2:
            mean = ear_series.mean()
            std = ear_series.std()
            current = latest["ear_prob"]
            if pd.notna(current) and std > 0:
                features["feat_ear_zscore"] = float((current - mean) / std)
            else:
                features["feat_ear_zscore"] = 0.0

    # 3. Nose: Funding Rate Sigmoid
    fr_val = latest.get("funding_rate")
    if pd.notna(fr_val) and fr_val is not None:
        x = float(fr_val) * 10000
        s = sigmoid(x)
        features["feat_nose_sigmoid"] = float(2 * s - 1)

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

    return features


def save_features_to_db(
    session: Session, features: Dict
) -> Optional[FeaturesNormalized]:
    """將特徵保存為 FeaturesNormalized 記錄。"""
    try:
        record = FeaturesNormalized(
            timestamp=features["timestamp"],
            feat_eye_dist=features.get("feat_eye_dist"),
            feat_ear_zscore=features.get("feat_ear_zscore"),
            feat_nose_sigmoid=features.get("feat_nose_sigmoid"),
            feat_tongue_pct=features.get("feat_tongue_pct"),
            feat_body_roc=features.get("feat_body_roc"),
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
