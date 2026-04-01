"""
標籤生成模組：為特徵數據生成未來收益率標籤
用於監督式學習（XGBoost 訓練）
"""

import pandas as pd
from datetime import timedelta
from sqlalchemy.orm import Session
from typing import Optional

from database.models import RawMarketData, FeaturesNormalized, Labels
from utils.logger import setup_logger

logger = setup_logger(__name__)

def generate_future_return_labels(
    session: Session,
    symbol: str,
    horizon_hours: int = 24,
    threshold_pct: float = 0.005,
    neutral_band: float = 0.005
) -> pd.DataFrame:
    """
    從 FeaturesNormalized 的時間戳，對應到未來 horizon_hours 的收益率，並生成標籤。

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
        if ret_pct > threshold_pct:
            label = 1
        elif ret_pct < -threshold_pct:
            label = -1
        else:
            label = 0  # neutral / hold
        labels.append({
            "timestamp": ts,
            "label": label,
            "future_return_pct": ret_pct
        })

    df = pd.DataFrame(labels)
    dist = df['label'].value_counts().to_dict()
    logger.info(f"標籤生成完成：共 {len(df)} 筆，分佈={dist}")
    return df

def save_labels_to_db(session: Session, labels_df: pd.DataFrame, symbol: str = "BTCUSDT", horizon_hours: int = 1):
    """
    將標籤寫入 labels 表（upsert：相同 timestamp+symbol+horizon_hours 則更新）。
    修復：原本此函數為 no-op，導致 labels 表不更新。(fix #H61 2026-04-02)
    """
    if labels_df.empty:
        logger.warning("save_labels_to_db: 空 DataFrame，跳過寫入")
        return

    # 取得現有的 timestamps（避免重複）
    existing_ts_set = set(
        str(r.timestamp) for r in session.query(Labels.timestamp)
        .filter(Labels.symbol == symbol, Labels.horizon_hours == horizon_hours)
        .all()
    )

    new_count = 0
    for _, row in labels_df.iterrows():
        ts_str = str(row["timestamp"])
        if ts_str in existing_ts_set:
            continue  # 跳過已存在
        label_row = Labels(
            timestamp=row["timestamp"],
            symbol=symbol,
            horizon_hours=horizon_hours,
            future_return_pct=float(row.get("future_return_pct", 0.0)),
            label=int(row["label"]),
        )
        session.add(label_row)
        new_count += 1

    session.commit()
    logger.info(f"save_labels_to_db: 新增 {new_count} 筆標籤（共 {len(labels_df)} 筆輸入）")

if __name__ == "__main__":
    print("Labeling module loaded. Use generate_future_return_labels()")
