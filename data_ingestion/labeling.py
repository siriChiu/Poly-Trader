"""
標籤生成模組：為特徵數據生成未來收益率標籤
用於監督式學習（XGBoost 訓練）
"""

from datetime import timedelta
from typing import Optional, Iterable

import pandas as pd
from sqlalchemy.orm import Session

from database.models import RawMarketData, FeaturesNormalized, Labels
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Canonical label settings for the spot-long pyramiding strategy.
DEFAULT_LABEL_HORIZON_HOURS = 24
DEFAULT_LONG_TP_PCT = 0.02
DEFAULT_LONG_MAX_DD_PCT = 0.05
DEFAULT_PYRAMID_LAYERS = (0.20, 0.30, 0.50)
DEFAULT_PYRAMID_LAYER2_DROP = -0.02
DEFAULT_PYRAMID_LAYER3_DROP = -0.05


def _simulate_pyramid_outcome(
    horizon_prices: Iterable[float],
    entry_price: float,
    take_profit_pct: float = DEFAULT_LONG_TP_PCT,
    stop_loss_pct: float = DEFAULT_LONG_MAX_DD_PCT,
) -> tuple[int, float, float, float, float]:
    prices = [float(p) for p in horizon_prices if p is not None]
    if not prices or entry_price <= 0:
        return 0, 0.0, -1.0, 1.0, 1.0

    invested = 0.0
    units = 0.0
    deployed = []
    max_drawdown_seen = 0.0
    underwater_steps = 0
    total_steps = 0

    def add_layer(weight: float, price: float) -> None:
        nonlocal invested, units
        if weight <= 0:
            return
        invested += weight
        units += weight / max(price, 1e-9)
        deployed.append((weight, price))

    def finalize(win_flag: int, pnl_pct: float) -> tuple[int, float, float, float, float]:
        pnl_component = pnl_pct / max(take_profit_pct, 1e-9)
        drawdown_penalty = max_drawdown_seen / max(stop_loss_pct, 1e-9)
        time_underwater = underwater_steps / max(total_steps, 1)
        quality = (
            0.45 * float(win_flag)
            + 0.25 * pnl_component
            - 0.20 * drawdown_penalty
            - 0.10 * time_underwater
        )
        return win_flag, pnl_pct, float(quality), float(drawdown_penalty), float(time_underwater)

    add_layer(DEFAULT_PYRAMID_LAYERS[0], entry_price)
    layer2_trigger = entry_price * (1 + DEFAULT_PYRAMID_LAYER2_DROP)
    layer3_trigger = entry_price * (1 + DEFAULT_PYRAMID_LAYER3_DROP)

    for price in prices:
        if len(deployed) == 1 and price <= layer2_trigger:
            add_layer(DEFAULT_PYRAMID_LAYERS[1], price)
        if len(deployed) == 2 and price <= layer3_trigger:
            add_layer(DEFAULT_PYRAMID_LAYERS[2], price)

        avg_price = invested / max(units, 1e-9)
        pnl_pct = (price - avg_price) / avg_price
        total_steps += 1
        if pnl_pct < 0:
            underwater_steps += 1
        max_drawdown_seen = max(max_drawdown_seen, max(0.0, -pnl_pct))
        if pnl_pct >= take_profit_pct:
            return finalize(1, pnl_pct)
        if pnl_pct <= -stop_loss_pct:
            return finalize(0, pnl_pct)

    final_price = prices[-1]
    avg_price = invested / max(units, 1e-9)
    pnl_pct = (final_price - avg_price) / avg_price
    return finalize(int(pnl_pct > 0), pnl_pct)


def _compute_turning_point_labels(current_price: float, horizon_prices: list[float], threshold_pct: float) -> tuple[int, int, float]:
    prices = [float(p) for p in horizon_prices if p is not None]
    if not prices or current_price <= 0:
        return 0, 0, 0.0
    future_min = min(prices)
    future_max = max(prices)
    future_range = max(future_max - future_min, 1e-9)
    near_future_min = max(0.0, 1.0 - abs(current_price - future_min) / future_range)
    near_future_max = max(0.0, 1.0 - abs(current_price - future_max) / future_range)
    runup_pct = (future_max - current_price) / current_price
    drawdown_pct = (future_min - current_price) / current_price
    bottom_score = max(0.0, min(1.0, 0.6 * near_future_min + 0.4 * max(0.0, runup_pct / max(threshold_pct, 1e-9))))
    top_score = max(0.0, min(1.0, 0.6 * near_future_max + 0.4 * max(0.0, abs(drawdown_pct) / max(threshold_pct, 1e-9))))
    label_local_bottom = int(near_future_min >= 0.65 and runup_pct >= threshold_pct)
    label_local_top = int(near_future_max >= 0.65 and drawdown_pct <= -threshold_pct)
    turning_point_score = float(max(bottom_score, top_score))
    return label_local_bottom, label_local_top, turning_point_score


def generate_future_return_labels(
    session: Session,
    symbol: str = "BTCUSDT",
    horizon_hours: int = DEFAULT_LABEL_HORIZON_HOURS,
    threshold_pct: float = DEFAULT_LONG_TP_PCT,
    neutral_band: float = DEFAULT_LONG_MAX_DD_PCT
) -> pd.DataFrame:
    """
    從 FeaturesNormalized 的時間戳，對應到未來 horizon_hours 的收益率，並生成標籤。

    Canonical target:
      label_spot_long_win = 1 when the setup can support a profitable spot-long pyramid
      within the horizon: price finishes above the profit target AND never breaches
      the maximum allowed drawdown.

    Returns:
        DataFrame 包含: timestamp (特徵時間), label (0/1), future_return_pct
    """
    # P0: canonical feature rows must align on (timestamp, symbol).
    # Prefer exact-symbol rows, but fall back to legacy NULL-symbol rows only when no
    # canonical row exists for the timestamp.
    query = (
        session.query(FeaturesNormalized)
        .filter((FeaturesNormalized.symbol == symbol) | (FeaturesNormalized.symbol.is_(None)))
        .order_by(FeaturesNormalized.timestamp, FeaturesNormalized.symbol.is_(None))
    )
    rows = query.all()
    if not rows:
        logger.error("無特徵數據")
        return pd.DataFrame()

    feature_times = []
    seen_feature_ts = set()
    for r in rows:
        if r.timestamp in seen_feature_ts:
            continue
        seen_feature_ts.add(r.timestamp)
        feature_times.append(r.timestamp)
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
        # P0: Compute future max drawdown/runup within the horizon.
        # For the spot-long pyramiding target, the key condition is that the trade
        # can survive the configured drawdown budget while still reaching profit.
        mask_horizon = (prices_df.index >= ts) & (prices_df.index <= future_ts + FUTURE_TOLERANCE)
        horizon_prices = prices_df[mask_horizon].copy()
        if not horizon_prices.empty:
            max_price_during = horizon_prices["close_price"].max()
            min_price_during = horizon_prices["close_price"].min()
            if current_price > 0 and max_price_during > 0:
                max_drawdown = (min_price_during - current_price) / current_price
                max_runup = (max_price_during - current_price) / current_price
            else:
                max_drawdown = None
                max_runup = None
        else:
            max_drawdown = None
            max_runup = None

        # P1: use a path-aware label instead of final-close-only thresholding.
        # A spot-long pyramid setup should count as a win if price reaches the
        # profit target at any point within the horizon while staying within the
        # allowed drawdown budget.
        tp_hit = int(max_runup is not None and max_runup >= threshold_pct)
        dd_ok = int(max_drawdown is None or max_drawdown >= -neutral_band)
        long_win = int(tp_hit == 1 and dd_ok == 1)
        # Continuous quality score for later ranking/regression experiments.
        runup_component = (max_runup or 0.0) / max(threshold_pct, 1e-9)
        dd_component = abs(min(max_drawdown or 0.0, 0.0)) / max(neutral_band, 1e-9)
        quality_score = runup_component - 0.7 * dd_component + 0.3 * ret_pct / max(threshold_pct, 1e-9)

        horizon_price_list = horizon_prices["close_price"].tolist() if not horizon_prices.empty else []
        (
            simulated_win,
            simulated_pnl,
            simulated_quality,
            simulated_drawdown_penalty,
            simulated_time_underwater,
        ) = _simulate_pyramid_outcome(
            horizon_price_list,
            current_price,
            take_profit_pct=threshold_pct,
            stop_loss_pct=neutral_band,
        )
        label_local_bottom, label_local_top, turning_point_score = _compute_turning_point_labels(
            current_price,
            horizon_price_list,
            threshold_pct,
        )

        tri_label = long_win
        label_sell_win = 1 - long_win
        label_up = long_win
        labels.append({
            "timestamp": ts,
            "label": tri_label,
            "label_spot_long_win": long_win,
            "label_spot_long_tp_hit": tp_hit,
            "label_spot_long_quality": quality_score,
            "simulated_pyramid_win": simulated_win,
            "simulated_pyramid_pnl": simulated_pnl,
            "simulated_pyramid_quality": simulated_quality,
            "simulated_pyramid_drawdown_penalty": simulated_drawdown_penalty,
            "simulated_pyramid_time_underwater": simulated_time_underwater,
            "label_local_bottom": label_local_bottom,
            "label_local_top": label_local_top,
            "turning_point_score": turning_point_score,
            "label_sell_win": label_sell_win,
            "label_up": label_up,
            "future_return_pct": ret_pct,
            "future_max_drawdown": max_drawdown,
            "future_max_runup": max_runup,
            "regime_label": None,  # Will be backfilled from features_normalized.regime_label
        })

    df = pd.DataFrame(labels)
    dist = df['label'].value_counts().to_dict()
    logger.info(f"標籤生成完成：共 {len(df)} 筆，分佈={dist}")
    return df

def save_labels_to_db(session: Session, labels_df: pd.DataFrame, symbol: str = "BTCUSDT", horizon_hours: int = DEFAULT_LABEL_HORIZON_HOURS, force_update_all: bool = False):
    """
    將標籤寫入 labels 表（upsert：相同 timestamp+symbol+horizon_hours 則更新）。
    修復：原本此函數為 no-op，導致 labels 表不更新。(fix #H61 2026-04-02)
    P0 fix: 自動填入 regime_label(從 features_normalized)，不再產生 NULL。(fix #H381)
    P0 force_update_all: 更新所有現有標籤（用於 sell_win 定義修正後全面重建）。(fix #SELL_WIN_40)
    """
    if labels_df.empty:
        logger.warning("save_labels_to_db: 空 DataFrame，跳過寫入")
        return

    # 建立 timestamp → regime_label 映射(從 features_normalized)
    feature_rows = (
        session.query(FeaturesNormalized.timestamp, FeaturesNormalized.regime_label, FeaturesNormalized.symbol)
        .filter((FeaturesNormalized.symbol == symbol) | (FeaturesNormalized.symbol.is_(None)))
        .order_by(FeaturesNormalized.timestamp, FeaturesNormalized.symbol.is_(None))
        .all()
    )
    regime_map = {}
    for r in feature_rows:
        ts_key = str(r.timestamp)
        if ts_key in regime_map:
            continue
        if r.regime_label is not None:
            regime_map[ts_key] = r.regime_label

    # 取得現有行
    existing_rows = {
        str(r.timestamp): r for r in session.query(Labels)
        .filter(Labels.symbol == symbol, Labels.horizon_minutes == horizon_hours * 60)
        .all()
    }

    new_count = 0
    update_count = 0
    for _, row in labels_df.iterrows():
        ts_str = str(row["timestamp"])
        fut_ret = row.get("future_return_pct")
        spot_long_win = int(row.get("label_spot_long_win", row.get("label_up", 0)))
        spot_long_tp_hit = int(row.get("label_spot_long_tp_hit", spot_long_win))
        spot_long_quality = float(row.get("label_spot_long_quality") or 0.0)
        simulated_win = int(row.get("simulated_pyramid_win", 0))
        simulated_pnl = float(row.get("simulated_pyramid_pnl") or 0.0)
        simulated_quality = float(row.get("simulated_pyramid_quality") or 0.0)
        simulated_drawdown_penalty = float(row.get("simulated_pyramid_drawdown_penalty") or 0.0)
        simulated_time_underwater = float(row.get("simulated_pyramid_time_underwater") or 0.0)
        label_local_bottom = int(row.get("label_local_bottom", 0) or 0)
        label_local_top = int(row.get("label_local_top", 0) or 0)
        turning_point_score = float(row.get("turning_point_score") or 0.0)
        label_sell_win = int(row.get("label_sell_win", 1 - spot_long_win))
        label_up = int(row.get("label_up", spot_long_win))
        future_max_drawdown = float(row.get("future_max_drawdown") or 0)
        future_max_runup = float(row.get("future_max_runup") or 0)
        # 從此 timestamp 對應的 feature 中取得 regime
        regime_val = regime_map.get(ts_str)

        if ts_str in existing_rows:
            existing = existing_rows[ts_str]
            needs_update = False
            canonical_missing = any(
                getattr(existing, field) is None
                for field in (
                    "label_spot_long_win",
                    "label_spot_long_tp_hit",
                    "label_spot_long_quality",
                    "simulated_pyramid_win",
                    "simulated_pyramid_pnl",
                    "simulated_pyramid_quality",
                    "simulated_pyramid_drawdown_penalty",
                    "simulated_pyramid_time_underwater",
                    "label_local_bottom",
                    "label_local_top",
                    "turning_point_score",
                    "label_up",
                )
            )
            if force_update_all:
                # P0 #SELL_WIN_40: 強制更新所有標籤
                existing.label_spot_long_win = spot_long_win
                existing.label_spot_long_tp_hit = spot_long_tp_hit
                existing.label_spot_long_quality = spot_long_quality
                existing.simulated_pyramid_win = simulated_win
                existing.simulated_pyramid_pnl = simulated_pnl
                existing.simulated_pyramid_quality = simulated_quality
                existing.simulated_pyramid_drawdown_penalty = simulated_drawdown_penalty
                existing.simulated_pyramid_time_underwater = simulated_time_underwater
                existing.label_local_bottom = label_local_bottom
                existing.label_local_top = label_local_top
                existing.turning_point_score = turning_point_score
                existing.label_sell_win = label_sell_win
                existing.label_up = label_up
                existing.future_return_pct = float(fut_ret) if fut_ret is not None else existing.future_return_pct
                existing.future_max_drawdown = future_max_drawdown
                existing.future_max_runup = future_max_runup
                needs_update = True
            elif existing.future_return_pct is None and fut_ret is not None:
                # 更新 NULL label：現在有未來數據了
                existing.future_return_pct = float(fut_ret)
                existing.label_spot_long_win = spot_long_win
                existing.label_spot_long_tp_hit = spot_long_tp_hit
                existing.label_spot_long_quality = spot_long_quality
                existing.simulated_pyramid_win = simulated_win
                existing.simulated_pyramid_pnl = simulated_pnl
                existing.simulated_pyramid_quality = simulated_quality
                existing.simulated_pyramid_drawdown_penalty = simulated_drawdown_penalty
                existing.simulated_pyramid_time_underwater = simulated_time_underwater
                existing.label_local_bottom = label_local_bottom
                existing.label_local_top = label_local_top
                existing.turning_point_score = turning_point_score
                existing.label_sell_win = label_sell_win
                existing.label_up = label_up
                existing.future_max_drawdown = future_max_drawdown
                existing.future_max_runup = future_max_runup
                needs_update = True
            elif canonical_missing:
                # Legacy rows may already have future_return_pct but still miss the
                # canonical spot-long / simulated target columns. Backfill them in-place
                # so heartbeat freshness reflects the actual label horizon state.
                existing.label_spot_long_win = spot_long_win
                existing.label_spot_long_tp_hit = spot_long_tp_hit
                existing.label_spot_long_quality = spot_long_quality
                existing.simulated_pyramid_win = simulated_win
                existing.simulated_pyramid_pnl = simulated_pnl
                existing.simulated_pyramid_quality = simulated_quality
                existing.simulated_pyramid_drawdown_penalty = simulated_drawdown_penalty
                existing.simulated_pyramid_time_underwater = simulated_time_underwater
                existing.label_local_bottom = label_local_bottom
                existing.label_local_top = label_local_top
                existing.turning_point_score = turning_point_score
                if existing.label_sell_win is None:
                    existing.label_sell_win = label_sell_win
                existing.label_up = label_up
                if existing.future_max_drawdown is None:
                    existing.future_max_drawdown = future_max_drawdown
                if existing.future_max_runup is None:
                    existing.future_max_runup = future_max_runup
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
        spot_long_win = int(row.get("label_spot_long_win", row.get("label_up", 0)))
        label_row = Labels(
            timestamp=row["timestamp"],
            symbol=symbol,
            horizon_minutes=horizon_hours * 60,
            future_return_pct=float(row["future_return_pct"]) if row.get("future_return_pct") is not None and row["future_return_pct"] != "" else None,
            future_max_drawdown=float(row.get("future_max_drawdown") or 0),
            future_max_runup=float(row.get("future_max_runup") or 0),
            label_spot_long_win=spot_long_win,
            label_spot_long_tp_hit=int(row.get("label_spot_long_tp_hit", spot_long_win)),
            label_spot_long_quality=float(row.get("label_spot_long_quality") or 0.0),
            simulated_pyramid_win=int(row.get("simulated_pyramid_win", 0)),
            simulated_pyramid_pnl=float(row.get("simulated_pyramid_pnl") or 0.0),
            simulated_pyramid_quality=float(row.get("simulated_pyramid_quality") or 0.0),
            simulated_pyramid_drawdown_penalty=float(row.get("simulated_pyramid_drawdown_penalty") or 0.0),
            simulated_pyramid_time_underwater=float(row.get("simulated_pyramid_time_underwater") or 0.0),
            label_local_bottom=int(row.get("label_local_bottom", 0) or 0),
            label_local_top=int(row.get("label_local_top", 0) or 0),
            turning_point_score=float(row.get("turning_point_score") or 0.0),
            label_sell_win=int(row.get("label_sell_win", 1 - spot_long_win)),
            label_up=int(row.get("label_up", spot_long_win)),
            regime_label=regime_val,  # P0 fix: 自動填入 regime
        )
        session.add(label_row)
        new_count += 1

    session.commit()
    if force_update_all:
        logger.info(f"save_labels_to_db: 新增 {new_count} 筆，強制更新 {update_count} 筆（共 {len(labels_df)} 筆輸入）")
    else:
        logger.info(f"save_labels_to_db: 新增 {new_count} 筆，更新 {update_count} 筆 NULL labels（共 {len(labels_df)} 筆輸入）")

if __name__ == "__main__":
    print("Labeling module loaded. Use generate_future_return_labels()")
