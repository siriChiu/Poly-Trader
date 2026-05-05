"""
多特徵數據整合收集器 v4
- 支援 raw_events 紀錄
- 支援 market / social / prediction / macro 擴充
- 保留舊 raw_market_data 寫入路徑
"""

import json
import sys
from bisect import bisect_left
from pathlib import Path
_PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from data_ingestion.body_liquidation import get_body_feature
from data_ingestion.tongue_sentiment import get_tongue_feature
from data_ingestion.nose_futures import get_nose_feature
from data_ingestion.eye_okx import get_eye_feature
from data_ingestion.ear_polymarket import get_ear_feature
from data_ingestion.okx_derivatives import get_derivatives_features
from data_ingestion.backfill_historical import fetch_okx_klines
from data_ingestion.macro_data import fetch_macro_latest, compute_nq_features
from data_ingestion.claw_liquidation import get_claw_feature
from data_ingestion.fang_options import get_fang_feature
from data_ingestion.fin_etf import get_fin_feature
from data_ingestion.web_whale import get_web_feature
from data_ingestion.scales_ssr import get_scales_feature
from data_ingestion.nest_polymarket import get_nest_feature
from database.models import RawMarketData, RawEvent
from utils.logger import setup_logger

logger = setup_logger(__name__)


def _json_payload(payload) -> str | None:
    if payload is None:
        return None
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)


def _sum_optional(*values):
    numeric = [float(v) for v in values if v is not None]
    if not numeric:
        return None
    return float(sum(numeric))


def _raw_event(source: str, entity: str, subtype: str, value, confidence=0.5, quality_score=0.5, payload_json=None, language=None, region=None):
    return RawEvent(
        timestamp=datetime.utcnow(),
        source=source,
        entity=entity,
        subtype=subtype,
        value=value,
        confidence=confidence,
        quality_score=quality_score,
        payload_json=_json_payload(payload_json),
        language=language,
        region=region,
    )


def _snapshot_event(source: str, entity: str, subtype: str, snapshot: Dict, *, value_key: str | None = None, confidence: float = 0.6):
    value = snapshot.get(value_key) if value_key else None
    meta = snapshot.get("_meta") or {}
    signal_values = [v for k, v in snapshot.items() if not str(k).startswith("_")]
    has_signal = any(v is not None for v in signal_values)
    status = meta.get("status") or ("ok" if has_signal else "missing")
    payload = {
        "status": status,
        "snapshot": {k: v for k, v in snapshot.items() if not str(k).startswith("_")},
    }
    if meta.get("message"):
        payload["message"] = meta["message"]
    return _raw_event(
        source,
        entity,
        subtype,
        value,
        confidence=confidence,
        quality_score=1.0 if status == "ok" and has_signal else 0.0,
        payload_json=payload,
    )


def _has_nearby_timestamp(sorted_timestamps, ts: datetime, tolerance: timedelta) -> bool:
    if not sorted_timestamps:
        return False
    pos = bisect_left(sorted_timestamps, ts)
    neighbors = []
    if pos < len(sorted_timestamps):
        neighbors.append(sorted_timestamps[pos])
    if pos > 0:
        neighbors.append(sorted_timestamps[pos - 1])
    return any(abs(candidate - ts) <= tolerance for candidate in neighbors)


def _insert_klines_into_raw(
    session: Session,
    symbol: str,
    existing_timestamps,
    klines_df,
    *,
    cutoff: datetime,
    tolerance: timedelta,
) -> int:
    inserted = 0
    if klines_df is None or klines_df.empty:
        return 0

    for _, row in klines_df.sort_values("timestamp").iterrows():
        ts = row.get("timestamp")
        if ts is None:
            continue
        ts = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts
        if ts < cutoff:
            continue
        if _has_nearby_timestamp(existing_timestamps, ts, tolerance):
            continue
        close_price = row.get("close")
        volume = row.get("volume")
        if close_price is None:
            continue
        session.add(
            RawMarketData(
                timestamp=ts,
                symbol=symbol,
                close_price=float(close_price),
                volume=float(volume) if volume is not None else None,
            )
        )
        existing_timestamps.insert(bisect_left(existing_timestamps, ts), ts)
        inserted += 1
    return inserted


def _insert_interpolated_gap_bridges(
    session: Session,
    symbol: str,
    existing_timestamps,
    *,
    cutoff: datetime,
    tolerance: timedelta,
    max_gap_hours: float = 12.0,
    bridge_interval_hours: int = 1,
) -> int:
    rows = (
        session.query(RawMarketData.timestamp, RawMarketData.close_price)
        .filter(RawMarketData.symbol == symbol, RawMarketData.timestamp >= cutoff)
        .order_by(RawMarketData.timestamp)
        .all()
    )
    inserted = 0
    step = timedelta(hours=bridge_interval_hours)
    for (prev_ts, prev_price), (curr_ts, curr_price) in zip(rows, rows[1:]):
        if prev_ts is None or curr_ts is None or prev_price is None or curr_price is None:
            continue
        gap_hours = (curr_ts - prev_ts).total_seconds() / 3600
        if gap_hours <= bridge_interval_hours + 0.5 or gap_hours > max_gap_hours:
            continue
        bridge_ts = prev_ts + step
        while bridge_ts < curr_ts:
            if not _has_nearby_timestamp(existing_timestamps, bridge_ts, tolerance):
                weight = (bridge_ts - prev_ts).total_seconds() / (curr_ts - prev_ts).total_seconds()
                bridge_price = float(prev_price) + (float(curr_price) - float(prev_price)) * weight
                session.add(
                    RawMarketData(
                        timestamp=bridge_ts,
                        symbol=symbol,
                        close_price=float(bridge_price),
                        volume=None,
                    )
                )
                existing_timestamps.insert(bisect_left(existing_timestamps, bridge_ts), bridge_ts)
                inserted += 1
            bridge_ts += step
    return inserted


def repair_recent_raw_continuity(
    session: Session,
    symbol: str = "BTC/USDT",
    *,
    lookback_days: int = 7,
    interval: str = "4h",
    alignment_tolerance_minutes: int = 30,
    klines_df=None,
    fine_grain_interval: str = "1h",
    fine_grain_days: int = 2,
    fine_grain_klines_df=None,
    return_details: bool = False,
) -> int | Dict[str, Any]:
    """Backfill missing recent OKX klines into raw_market_data.

    Heartbeat #628 root-cause fix: the live collector only appends a single snapshot row,
    so if the scheduler stalls for several hours the raw timeline develops large gaps and
    4h canonical labels stop growing (`raw_gap_blocked`). Heartbeat #629 extends the repair
    lane with a finer 1h public-kline pass so the 240m label path is not stuck waiting for
    the next 4h closed candle.
    """
    tolerance = timedelta(minutes=alignment_tolerance_minutes)
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
    existing_rows = (
        session.query(RawMarketData.timestamp)
        .filter(RawMarketData.symbol == symbol, RawMarketData.timestamp >= cutoff)
        .order_by(RawMarketData.timestamp)
        .all()
    )
    existing_timestamps = [ts for (ts,) in existing_rows if ts is not None]

    if klines_df is None:
        klines_df = fetch_okx_klines(symbol=symbol, interval=interval, days=lookback_days)

    inserted_coarse = _insert_klines_into_raw(
        session,
        symbol,
        existing_timestamps,
        klines_df,
        cutoff=cutoff,
        tolerance=tolerance,
    )

    fine_cutoff = max(cutoff, datetime.utcnow() - timedelta(days=fine_grain_days))
    if fine_grain_klines_df is None:
        fine_grain_klines_df = fetch_okx_klines(
            symbol=symbol,
            interval=fine_grain_interval,
            days=fine_grain_days,
        )
    inserted_fine = _insert_klines_into_raw(
        session,
        symbol,
        existing_timestamps,
        fine_grain_klines_df,
        cutoff=fine_cutoff,
        tolerance=tolerance,
    )
    inserted_bridge = _insert_interpolated_gap_bridges(
        session,
        symbol,
        existing_timestamps,
        cutoff=fine_cutoff,
        tolerance=tolerance,
    )
    inserted_total = inserted_coarse + inserted_fine + inserted_bridge
    details = {
        "symbol": symbol,
        "lookback_days": lookback_days,
        "coarse_interval": interval,
        "fine_interval": fine_grain_interval,
        "coarse_inserted": inserted_coarse,
        "fine_inserted": inserted_fine,
        "bridge_inserted": inserted_bridge,
        "inserted_total": inserted_total,
        "used_bridge": inserted_bridge > 0,
        "used_fine_grain": inserted_fine > 0,
        "skipped_no_klines": bool(
            (klines_df is None or klines_df.empty)
            and (fine_grain_klines_df is None or fine_grain_klines_df.empty)
        ),
    }

    if inserted_total:
        logger.info(
            "recent raw continuity repair inserted %s rows for %s (coarse=%s via %s, fine=%s via %s, bridge=%s interpolated)",
            inserted_total,
            symbol,
            inserted_coarse,
            interval,
            inserted_fine,
            fine_grain_interval,
            inserted_bridge,
        )
    elif (klines_df is None or klines_df.empty) and (fine_grain_klines_df is None or fine_grain_klines_df.empty):
        logger.warning("recent raw continuity repair skipped: no OKX klines fetched")
    return details if return_details else inserted_total


def collect_all_senses(symbol: str = "BTC/USDT") -> Optional[Dict]:
    logger.info("開始多特徵數據收集 v4...")

    body = get_body_feature() or {}
    tongue = get_tongue_feature() or {}
    nose = get_nose_feature() or {}
    eye = get_eye_feature() or {}
    ear = get_ear_feature() or {}
    derivatives = get_derivatives_features(symbol) or {}

    eye_dist_val = eye.get("feat_eye_up") or eye.get("feat_eye_down")
    ear_prob_val = ear.get("prob")
    stablecoin_roc = body.get("raw_roc")
    body_label = body.get("body_label")
    oi_roc = body.get("oi_roc")
    tongue_sentiment = tongue.get("feat_tongue_sentiment")
    volatility = tongue.get("volatility")

    # Fetch VIX/DXY macro data
    macro = fetch_macro_latest()

    record = RawMarketData(
        timestamp=datetime.utcnow(),
        symbol=symbol,
        close_price=eye.get("current_price"),
        volume=eye.get("volume"),
        funding_rate=nose.get("funding_rate_raw"),
        fear_greed_index=tongue.get("fear_greed_index"),
        stablecoin_mcap=stablecoin_roc,
        polymarket_prob=ear_prob_val,
        eye_dist=eye_dist_val,
        ear_prob=ear_prob_val,
        tongue_sentiment=tongue_sentiment,
        volatility=volatility,
        oi_roc=oi_roc,
        body_label=body_label,
        vix_value=macro.get("vix_value"),
        dxy_value=macro.get("dxy_value"),
        nq_value=macro.get("nq_value"),
        # P0/P1: New feature data
        claw_liq_ratio=None,
        claw_liq_total=None,
        fang_pcr=None,
        fang_iv_skew=None,
        fin_etf_netflow=None,
        fin_etf_trend=None,
        web_whale_pressure=None,
        web_large_trades_count=None,
        scales_ssr=None,
        nest_pred=None,
    )
    record._derivatives = derivatives
    # P0/P1: Store new feature in _new_feature for preprocessor
    claw = get_claw_feature()
    fang = get_fang_feature()
    fin = get_fin_feature()
    web = get_web_feature()
    scales = get_scales_feature()
    nest = get_nest_feature()
    nq_feats = compute_nq_features(macro.get('nq_history', []))
    record._new_feature = {
        **claw, **fang, **fin, **web, **scales, **nest, **nq_feats,
    }

    # Actually map new feature to RawMarketData columns
    record.claw_liq_ratio = claw.get("claw_ratio")
    record.claw_liq_total = _sum_optional(claw.get("claw_long_liq"), claw.get("claw_short_liq"))
    record.fang_pcr = fang.get("fang_raw_pcr")
    record.fang_iv_skew = fang.get("fang_iv_skew_raw")
    fin_val = fin.get("fin_raw_netflow")
    record.fin_etf_netflow = fin_val
    record.fin_etf_trend = None  # need trend calc separately
    record.web_whale_pressure = web.get("web_sell_ratio")
    record.web_large_trades_count = web.get("web_large_trades")
    record.scales_ssr = scales.get("feat_scales_ssr")
    record.nest_pred = nest.get("nest_raw_prob")

    record._raw_events = [
        _raw_event("exchange", symbol, "price", eye.get("current_price"), confidence=0.9, payload_json=eye),
        _raw_event("exchange", symbol, "volume", eye.get("volume"), confidence=0.9, payload_json=eye),
        _raw_event("exchange", symbol, "funding", nose.get("funding_rate_raw"), confidence=0.9, payload_json=nose),
        _raw_event("prediction", symbol, "polymarket_prob", ear_prob_val, confidence=0.8, payload_json=ear),
        _raw_event("sentiment", symbol, "fear_greed", tongue.get("fear_greed_index"), confidence=0.7, payload_json=tongue),
        _raw_event("derivatives", symbol, "oi_roc", oi_roc, confidence=0.8, payload_json=derivatives),
        _snapshot_event("liquidation", symbol, "claw_snapshot", claw, value_key="claw_ratio", confidence=0.7),
        _snapshot_event("options", symbol, "fang_snapshot", fang, value_key="fang_raw_pcr", confidence=0.7),
        _snapshot_event("etf_flow", symbol, "fin_snapshot", fin, value_key="fin_raw_netflow", confidence=0.7),
        _snapshot_event("whale", symbol, "web_snapshot", web, value_key="web_sell_ratio", confidence=0.6),
        _snapshot_event("stablecoin", symbol, "scales_snapshot", scales, value_key="scales_total_stablecap_m", confidence=0.6),
        _snapshot_event("prediction", symbol, "nest_snapshot", nest, value_key="nest_raw_prob", confidence=0.7),
        _snapshot_event("macro", symbol, "macro_snapshot", {
            "vix_value": macro.get("vix_value"),
            "dxy_value": macro.get("dxy_value"),
            "nq_value": macro.get("nq_value"),
        }, value_key="vix_value", confidence=0.7),
    ]

    logger.info(
        f"收集完成 v5: price={eye.get('current_price')}, LSR={derivatives.get('lsr_ratio')}, "
        f"GSR={derivatives.get('gsr_ratio')}, Taker={derivatives.get('taker_ratio')}, OI={derivatives.get('oi_value')}"
    )
    return record


def run_collection_and_save(session: Session, symbol: str = "BTC/USDT") -> bool:
    try:
        record = collect_all_senses(symbol)
        if record is None:
            logger.error("收集失敗")
            return False

        session.add(record)
        raw_events = getattr(record, '_raw_events', [])
        for evt in raw_events:
            session.add(evt)
        session.commit()
        logger.info(f"Raw data 已保存，id={record.id}, raw_events={len(raw_events)}")
        return True
    except Exception as e:
        session.rollback()
        logger.exception(f"保存 raw data 失敗: {e}")
        return False
