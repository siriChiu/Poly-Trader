"""
特徵工程模組：將原始-market data 轉換為標準化特徵
支援 ROC、Z-score、Sigmoid 壓縮等正規化方法
"""

from typing import List, Optional, Dict
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from database.models import RawMarketData, FeaturesNormalized
from utils.logger import setup_logger

logger = setup_logger(__name__)

def calculate_roc(series: pd.Series, periods: int = 1) -> pd.Series:
    """
    計算變化率 (Rate of Change)： (当前 - 过去) / 过去
    """
    return series.pct_change(periods)

def zscore_normalize(series: pd.Series, window: Optional[int] = None) -> pd.Series:
    """
    Z-score 標準化： (x - mean) / std
    如果提供 window，則使用滾動計算；否則使用全局統計。
    """
    if window:
        mean = series.rolling(window=window, min_periods=1).mean()
        std = series.rolling(window=window, min_periods=1).std()
    else:
        mean = series.mean()
        std = series.std()
    # 避免除以零
    std = std.replace(0, np.nan)
    z = (series - mean) / std
    return z

def minmax_normalize(series: pd.Series, feature_range: tuple = (0, 1)) -> pd.Series:
    """
    Min-Max 縮放至指定範圍。
    """
    min_val, max_val = feature_range
    series_min = series.min()
    series_max = series.max()
    if series_max == series_min:
        return pd.Series(min_val, index=series.index)
    normalized = (series - series_min) / (series_max - series_min)
    return normalized * (max_val - min_val) + min_val

def sigmoid(x: float) -> float:
    """Sigmoid 函數：將數值壓縮到 (0,1)"""
    return 1 / (1 + np.exp(-x))

def load_latest_raw_data(session: Session, symbol: str, limit: int = 1) -> pd.DataFrame:
    """
    從資料庫讀取最新的 raw_market_data。
    Returns: DataFrame with columns according to RawMarketData
    """
    query = session.query(RawMarketData).filter(
        RawMarketData.symbol == symbol
    ).order_by(RawMarketData.timestamp.desc()).limit(limit)
    rows = query.all()
    if not rows:
        return pd.DataFrame()
    # 轉換為 DataFrame
    data = []
    for row in rows:
        data.append({
            "timestamp": row.timestamp,
            "symbol": row.symbol,
            "close_price": row.close_price,
            "volume": row.volume,
            "funding_rate": row.funding_rate,
            "fear_greed_index": row.fear_greed_index,
            "stablecoin_mcap": row.stablecoin_mcap,
            "polymarket_prob": row.polymarket_prob
        })
    df = pd.DataFrame(data)
    df.sort_values("timestamp", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

def compute_features_from_raw(df: pd.DataFrame) -> Optional[Dict]:
    """
    從原始數據計算五感特徵（單一時間點的最新數據）。
    假設 df 只包含一條或多條歷史數據以計算滾動特徵。
    返回特徵字典。
    """
    if df.empty:
        logger.warning("Raw data 為空，無法計算特徵")
        return None

    latest = df.iloc[-1]  # 最新的一筆
    features = {
        "timestamp": latest.get("timestamp", datetime.utcnow()),
        "feat_eye_dist": None,
        "feat_ear_zscore": None,
        "feat_nose_sigmoid": None,
        "feat_tongue_pct": None,
        "feat_body_roc": None
    }

    # 1. 眼 (Eye) - 這裏還沒有直接數據，實際應來自 eye_binance.py
    # 暫時留空，稍後 ingestion pipeline 會合併

    # 2. 耳 (Ear) -  Polymarket 機率 Z-score 標準化
    if "polymarket_prob" in df.columns and not df["polymarket_prob"].isna().all():
        prob_series = df["polymarket_prob"].dropna()
        if len(prob_series) >= 2:
            mean = prob_series.mean()
            std = prob_series.std()
            if std > 0:
                current = latest["polymarket_prob"]
                features["feat_ear_zscore"] = (current - mean) / std
            else:
                features["feat_ear_zscore"] = 0.0

    # 3. 鼻 (Nose) - Funding Rate Sigmoid 壓縮
    if "funding_rate" in df.columns and pd.notna(latest.get("funding_rate")):
        fr = latest["funding_rate"]
        x = fr * 10000
        s = sigmoid(x)
        features["feat_nose_sigmoid"] = 2 * s - 1

    # 4. 舌 (Tongue) - 恐懼貪婪指數百分比
    if "fear_greed_index" in df.columns and pd.notna(latest.get("fear_greed_index")):
        fng = latest["fear_greed_index"]
        features["feat_tongue_pct"] = fng / 100.0

    # 5. 身 (Body) - 穩定幣市值 ROC (需要歷史數據)
    if "stablecoin_mcap" in df.columns:
        sc_series = df["stablecoin_mcap"].dropna()
        if len(sc_series) >= 8:  # 至少8點才能算7日變化
            try:
                today = sc_series.iloc[-1]
                week_ago = sc_series.iloc[-8]
                if week_ago != 0:
                    roc = (today - week_ago) / week_ago
                    # 離散化：>0.5% => 1, <-0.5% => -1, else 0
                    if roc > 0.005:
                        features["feat_body_roc"] = 1.0
                    elif roc < -0.005:
                        features["feat_body_roc"] = -1.0
                    else:
                        features["feat_body_roc"] = 0.0
            except Exception as e:
                logger.warning(f"計算 Body ROC 錯誤: {e}")

    return features

def save_features_to_db(session: Session, features: Dict):
    """
    將特徵保存為 FeaturesNormalized 記錄。
    """
    try:
        record = FeaturesNormalized(
            timestamp=features["timestamp"],
            feat_eye_dist=features.get("feat_eye_dist"),
            feat_ear_zscore=features.get("feat_ear_zscore"),
            feat_nose_sigmoid=features.get("feat_nose_sigmoid"),
            feat_tongue_pct=features.get("feat_tongue_pct"),
            feat_body_roc=features.get("feat_body_roc")
        )
        session.add(record)
        session.commit()
        logger.info(f"特徵已保存: id={record.id}")
        return record
    except Exception as e:
        session.rollback()
        logger.error(f"保存特徵失敗: {e}")
        return None

def run_preprocessor(session: Session, symbol: str = "BTCUSDT") -> Optional[Dict]:
    """
    完整的特徵工程流程。
    1. 讀取最新原始數據
    2. 計算標準化特徵
    3. 保存至資料庫
    """
    logger.info("開始執行特徵工程...")
    df = load_latest_raw_data(session, symbol, limit=100)  # 取100筆以計算滾動特徵
    if df.empty:
        logger.error("無原始數據可供處理")
        return None

    features = compute_features_from_raw(df)
    if not features:
        logger.error("特徵計算失敗")
        return None

    saved = save_features_to_db(session, features)
    if saved:
        logger.info(f"特徵計算並保存完成: {features}")
        return features
    else:
        logger.error("特徵保存失敗")
        return None

if __name__ == "__main__":
    # 單元測試：需手動初始化 DB Session
    print("Preprocessor 模組加載成功。請在應用程式中初始化 SQLAlchemy Session 後使用 run_preprocessor。")
