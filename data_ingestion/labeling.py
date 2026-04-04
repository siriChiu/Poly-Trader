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

    # fix #H67: use nearest-match (60min tolerance) for 5-min data where exact timestamps don't align
    FUTURE_TOLERANCE = timedelta(minutes=60)

    labels = []
    for ts in feature_times:
        future_ts = ts + timedelta(hours=horizon_hours)
        # 找未來最近的價格（容差 60min）
        mask_future = (prices_df.index >= future_ts - FUTURE_TOLERANCE) &                       (prices_df.index <= future_ts + FUTURE_TOLERANCE)
        candidates_future = prices_df[mask_future]
        if candidates_future.empty:
            continue
        # 取最近的
        nearest_future_pos = (candidates_future.index - future_ts).to_series().abs().values.argmin()
        future_price = candidates_future.iloc[nearest_future_pos]["close_price"]
        if pd.isna(future_price):
            continue
        # 當前價格：找最近的（容差 10min）
        mask_current = (prices_df.index >= ts - timedelta(minutes=10)) &                        (prices_df.index <= ts + timedelta(minutes=10))
        candidates_current = prices_df[mask_current]
        if candidates_current.empty:
            continue
        nearest_current_pos = (candidates_current.index - ts).to_series().abs().values.argmin()
        current_price = candidates_current.iloc[nearest_current_pos]["close_price"]
        if pd.isna(current_price) or current_price == 0:
            continue
        ret_pct = (future_price - current_price) / current_price
        # Core definition: sell-win means SHORT is profitable = price goes DOWN (negative return)
        if ret_pct < -threshold_pct:
            label = 1
            sell_win = 1
        elif ret_pct > threshold_pct:
            label = -1
            sell_win = 0
        else:
            label = 0
            sell_win = 0
        labels.append({
            "timestamp": ts,
            "label": label,
            "label_sell_win": sell_win,
            "label_up": label,
            "future_return_pct": ret_pct,
            "future_max_drawdown": None,
            "future_max_runup": None,
            "regime_label": None,  # Will be backfilled from features_normalized.regime_label
        })

    df = pd.DataFrame(labels)
    dist = df['label'].value_counts().to_dict()
    logger.info(f"標籤生成完成：共 {len(df)} 筆，分佈={dist}")
    return df

def save_labels_to_db(session: Session, labels_df: pd.DataFrame, symbol: str = "BTCUSDT", horizon_hours: int = 1):
    """
    將標籤寫入 labels 表（upsert：相同 timestamp+symbol+horizon_hours 則更新）。
    修復：原本此函數為 no-op，導致 labels 表不更新。(fix #H61 2026-04-02)
    P0 fix: 自動填入 regime_label（從 features_normalized），不再產生 NULL。(fix #H381)
    """
    if labels_df.empty:
        logger.warning("save_labels_to_db: 空 DataFrame，跳過寫入")
        return

    # 建立 timestamp → regime_label 映射（從 features_normalized）
    feature_rows = session.query(FeaturesNormalized.timestamp, FeaturesNormalized.regime_label).all()
    regime_map = {str(r.timestamp): r.regime_label for r in feature_rows if r.regime_label is not None}

    # 取得現有行（包含 NULL 的需要更新，已有值的跳過）
    existing_rows = {
        str(r.timestamp): r for r in session.query(Labels)
        .filter(Labels.symbol == symbol, Labels.horizon_hours == horizon_hours)
        .all()
    }

    new_count = 0
    update_count = 0
    for _, row in labels_df.iterrows():
        ts_str = str(row["timestamp"])
        fut_ret = row.get("future_return_pct")
        # 從此 timestamp 對應的 feature 中取得 regime
        regime_val = regime_map.get(ts_str)

        if ts_str in existing_rows:
            existing = existing_rows[ts_str]
            needs_update = False
            if existing.future_return_pct is None and fut_ret is not None:
                # 更新 NULL label：現在有未來數據了
                existing.future_return_pct = float(fut_ret)
                existing.label = int(row["label"])
                existing.label_sell_win = int(row.get("label_sell_win", 0))
                existing.label_up = int(row.get("label_up", row["label"]))
                needs_update = True
            # P0 fix: 如果現有 label 的 regime_label 是 NULL，從 features 填充
            if existing.regime_label is None and regime_val is not None:
                existing.regime_label = regime_val
                needs_update = True
            if needs_update:
                update_count += 1
            # 已有值，跳過
            continue
        # 新標籤
        label_row = Labels(
            timestamp=row["timestamp"],
            symbol=symbol,
            horizon_minutes=horizon_hours * 60,
            label_up=int(row.get("label_up", row["label"])),
            regime_label=regime_val,  # P0 fix: 自動填入 regime
        )
        session.add(label_row)
        new_count += 1

    session.commit()
    logger.info(f"save_labels_to_db: 新增 {new_count} 筆，更新 {update_count} 筆 NULL labels（共 {len(labels_df)} 筆輸入）")

if __name__ == "__main__":
    print("Labeling module loaded. Use generate_future_return_labels()")
