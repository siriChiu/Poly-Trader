"""
標籤生成模組：為特徵數據生成未來收益率標籤
用於監督式學習（XGBoost 訓練）
"""

import pandas as pd
from datetime import timedelta
from sqlalchemy.orm import Session
from typing import Optional

from database.models import RawMarketData, FeaturesNormalized
from utils.logger import setup_logger

logger = setup_logger(__name__)

def generate_future_return_labels(
    session: Session,
    symbol: str,
    horizon_hours: int = 24,
    threshold_pct: float = 0.0
) -> pd.DataFrame:
    """
    從 FeaturesNormalized 的時間戳，對應到未來 horizon_hooks 的收益率，並生成標籤。

    Returns:
        DataFrame 包含: timestamp (特徵時間), label (0/1), future_return_pct
    """
    # 取所有特徵時間
    query = session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp)
    rows = query.all()
    if not rows:
        logger.error("無特徵數據")
        return pd.DataFrame()

    feature_times = [r.timestamp for r in rows]
    # 取 RawMarketData 的價格時間序列
    raw_query = session.query(RawMarketData).filter(
        RawMarketData.symbol == symbol
    ).order_by(RawMarketData.timestamp)
    raw_rows = raw_query.all()
    if not raw_rows:
        logger.error("無原始價格數據")
        return pd.DataFrame()

    # 構建價格時間序列 DataFrame
    prices_df = pd.DataFrame([
        {"timestamp": r.timestamp, "close_price": r.close_price}
        for r in raw_rows if r.close_price is not None
    ]).dropna().set_index("timestamp").sort_index()

    labels = []
    for ts in feature_times:
        future_ts = ts + timedelta(hours=horizon_hours)
        # 向前查找最接近 future_ts 的價格
        future_price_series = prices_df.reindex(prices_df.index.union([future_ts])).loc[future_ts:]
        if future_price_series.empty:
            continue
        future_price = future_price_series.iloc[0]["close_price"]
        # 當前價格：用特徵時間對應的價格（若特徵表無，從 prices_df 找最近）
        current_price_series = prices_df.reindex(prices_df.index.union([ts])).loc[:ts]
        if current_price_series.empty:
            continue
        current_price = current_price_series.iloc[-1]["close_price"]
        if current_price == 0:
            continue
        ret_pct = (future_price - current_price) / current_price
        label = 1 if ret_pct > threshold_pct else 0
        labels.append({
            "timestamp": ts,
            "label": label,
            "future_return_pct": ret_pct
        })

    df = pd.DataFrame(labels)
    logger.info(f"標籤生成完成：共 {len(df)} 筆，正样例比例={df['label'].mean():.2%}")
    return df

def save_labels_to_db(session: Session, labels_df: pd.DataFrame):
    """
    將標籤寫入資料庫（需要新增 labels 表）。
    為簡化，暫時不建立新表，而是將 label 與 future_return 存入 features_normalized 的備註欄（需要擴展 Schema）。
    我們選擇返回 DataFrame，供 training 直接使用。
    """
    logger.info("標籤 DataFrame 已準備好，可直接用於訓練。")
    return labels_df

if __name__ == "__main__":
    print("Labeling module loaded. Use generate_future_return_labels()")
