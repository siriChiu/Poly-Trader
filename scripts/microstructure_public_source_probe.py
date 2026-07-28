#!/usr/bin/env python3
"""Collect a public OKX order-book/trade-flow snapshot into the microstructure contract.

This is a read-only market-data probe.  It never uses credentials, calls a trading
adapter, or invents a forecast edge.  The resulting artifact makes the source,
observation time, freshness, coverage, feature formulas, and missing forecast
calibration explicit so the runtime can remain observation-only until a separately
validated forecast lineage exists.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Mapping
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_CONTRACT_PATH = ROOT / "data" / "microstructure_contract.json"
DEFAULT_SOURCE_PATH = ROOT / "data" / "microstructure_source_probe.json"
DEFAULT_BASE_URL = "https://www.okx.com"
STALE_AFTER_SECONDS = 300.0


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_number(value: Any) -> float:
    return float(value)


def _request_json(url: str, *, timeout: float) -> dict[str, Any]:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "poly-trader-microstructure-probe/1"})
    with urlopen(request, timeout=timeout) as response:  # nosec B310 - fixed HTTPS public market endpoint
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict) or payload.get("code") != "0":
        raise RuntimeError(f"public source returned non-success response: {payload!r}")
    return payload


def _rows(raw: Any) -> list[list[str]]:
    return [list(row) for row in raw if isinstance(row, (list, tuple)) and len(row) >= 2]


def _qty(row: list[str]) -> float:
    return max(_parse_number(row[1]), 0.0)


def _price(row: list[str]) -> float:
    return _parse_number(row[0])


def _depth(rows: list[list[str]], *, mid: float, bps: float) -> float:
    boundary = mid * bps / 10000.0
    return sum(_qty(row) for row in rows if abs(_price(row) - mid) <= boundary)


def _imbalance(left: float, right: float) -> float:
    total = left + right
    return (left - right) / total if total > 0 else 0.0


def _trade_ts(trade: Mapping[str, Any]) -> int | None:
    value = trade.get("ts")
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _trade_size(trade: Mapping[str, Any]) -> float:
    value = trade.get("sz")
    if value is None:
        return 0.0
    try:
        return max(_parse_number(value), 0.0)
    except (TypeError, ValueError):
        return 0.0


def derive_contract_payload(
    *,
    books_payload: Mapping[str, Any],
    trades_payload: Mapping[str, Any],
    symbol: str,
    inst_id: str,
    venue: str,
    retrieved_at: datetime,
) -> dict[str, Any]:
    book_data = books_payload.get("data") if isinstance(books_payload.get("data"), list) else []
    if not book_data or not isinstance(book_data[0], Mapping):
        raise RuntimeError("public source returned no order-book snapshot")
    book = book_data[0]
    bids = _rows(book.get("bids"))
    asks = _rows(book.get("asks"))
    if not bids or not asks:
        raise RuntimeError("public source returned an incomplete order-book snapshot")
    bids.sort(key=_price, reverse=True)
    asks.sort(key=_price)
    best_bid = _price(bids[0])
    best_ask = _price(asks[0])
    mid = (best_bid + best_ask) / 2.0
    if mid <= 0 or best_ask < best_bid:
        raise RuntimeError("public source returned invalid best bid/ask")

    raw_trade_data = trades_payload.get("data")
    trade_data: list[Any] = raw_trade_data if isinstance(raw_trade_data, list) else []
    trades: list[Mapping[str, Any]] = [trade for trade in trade_data if isinstance(trade, Mapping)]
    buy_volume = sum(_trade_size(trade) for trade in trades if trade.get("side") == "buy")
    sell_volume = sum(_trade_size(trade) for trade in trades if trade.get("side") == "sell")
    trade_timestamps = [ts for ts in (_trade_ts(trade) for trade in trades) if ts is not None]
    book_ts = int(book.get("ts")) if str(book.get("ts", "")).isdigit() else None
    observed_ms = max([ts for ts in [book_ts, *trade_timestamps] if ts is not None], default=int(retrieved_at.timestamp() * 1000))
    observed_at = datetime.fromtimestamp(observed_ms / 1000.0, tz=timezone.utc)

    l1_bid = _qty(bids[0])
    l1_ask = _qty(asks[0])
    l5_bid = sum(_qty(row) for row in bids[:5])
    l5_ask = sum(_qty(row) for row in asks[:5])
    spread_bps = (best_ask - best_bid) / mid * 10000.0
    microprice = (best_ask * l1_bid + best_bid * l1_ask) / (l1_bid + l1_ask) if l1_bid + l1_ask else mid
    microprice_deviation_bps = (microprice - mid) / mid * 10000.0
    depth_50bps = _depth(bids, mid=mid, bps=50.0) + _depth(asks, mid=mid, bps=50.0)
    depth_200bps = _depth(bids, mid=mid, bps=200.0) + _depth(asks, mid=mid, bps=200.0)
    trade_flow_imbalance = _imbalance(buy_volume, sell_volume)
    # This is a transparent source-derived stress indicator, not a calibrated edge:
    # wider spread and thinner near-touch depth increase stress; no live gate consumes
    # it as a forecast until a separate calibration artifact exists.
    liquidity_stress_score = min(1.0, max(0.0, spread_bps / 50.0 + 1.0 / (1.0 + depth_50bps)))
    coverage_events = len(trades) + 1
    source_name = "okx_public_market_api"
    endpoint_books = "/api/v5/market/books"
    endpoint_trades = "/api/v5/market/trades"
    feature_source = f"{source_name}:{inst_id}"

    features = {
        "orderbook_imbalance_l1": {"value": _imbalance(l1_bid, l1_ask), "source": feature_source, "formula": "(bid_qty_l1-ask_qty_l1)/(bid_qty_l1+ask_qty_l1)"},
        "orderbook_imbalance_l5": {"value": _imbalance(l5_bid, l5_ask), "source": feature_source, "formula": "(sum_bid_qty_l5-sum_ask_qty_l5)/(sum_bid_qty_l5+sum_ask_qty_l5)"},
        "spread_bps": {"value": spread_bps, "source": feature_source, "formula": "(best_ask-best_bid)/mid*10000"},
        "depth_50bps": {"value": depth_50bps, "source": feature_source, "formula": "base_asset_qty_within_50bps_of_mid"},
        "depth_200bps": {"value": depth_200bps, "source": feature_source, "formula": "base_asset_qty_within_200bps_of_mid"},
        "microprice_deviation": {"value": microprice_deviation_bps, "source": feature_source, "formula": "(microprice-mid)/mid*10000"},
        "trade_flow_imbalance": {"value": trade_flow_imbalance, "source": feature_source, "formula": "(buy_volume-sell_volume)/(buy_volume+sell_volume)"},
        "liquidity_stress_score": {"value": liquidity_stress_score, "source": feature_source, "formula": "clip(spread_bps/50 + 1/(1+depth_50bps),0,1); uncalibrated"},
    }
    return {
        "schema_version": 1,
        "generated_at": _iso(retrieved_at),
        "symbol": symbol,
        "venue": venue,
        "status": "source_observed_forecast_unavailable",
        "source": {
            "kind": "orderbook_and_trade_flow",
            "name": source_name,
            "configured": True,
            "available": True,
            "provider": "OKX public market API",
            "endpoints": {"books": endpoint_books, "trades": endpoint_trades},
            "instrument": inst_id,
            "observed_at": _iso(observed_at),
            "retrieved_at": _iso(retrieved_at),
            "freshness_status": "fresh",
        },
        "freshness": {
            "artifact_status": "fresh",
            "source_status": "fresh",
            "stale_after_seconds": STALE_AFTER_SECONDS,
        },
        "coverage": {
            "window_minutes": 5,
            "observed_events": coverage_events,
            "covered_events": coverage_events,
            "coverage_ratio": 1.0,
            "coverage_mode": "one_orderbook_snapshot_plus_recent_public_trades",
            "books_levels_observed": min(len(bids), len(asks)),
            "trades_observed": len(trades),
        },
        "snapshot_summary": {
            "best_bid": best_bid,
            "best_ask": best_ask,
            "mid": mid,
            "buy_volume": buy_volume,
            "sell_volume": sell_volume,
        },
        "features": features,
        "feature_lineage": {name: {"source": item["source"], "formula": item["formula"]} for name, item in features.items()},
        "forecast_edge_bps": None,
        "forecast": {
            "available": False,
            "value_bps": None,
            "source": "unavailable",
            "freshness_status": "missing",
            "lineage_status": "not_calibrated_from_source_snapshot",
            "calibration_artifact": None,
        },
        "decision_contract": {
            "status": "observation_only",
            "observation_only": True,
            "paper_shadow_risk_on_allowed": False,
            "live_risk_on_allowed": False,
            "reason": "source-backed microstructure features observed; forecast edge calibration is not available, so remain observation-only",
        },
        "operator_next_action": "保留 source-backed microstructure observation；先建立可重現 forecast calibration artifact，再評估 paper/shadow risk-on。live buy/add 仍受所有既有 gates fail-closed 約束。",
    }


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--inst-id", default="BTC-USDT")
    parser.add_argument("--symbol", default="BTC/USDT")
    parser.add_argument("--venue", default="okx")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--source-output", type=Path, default=DEFAULT_SOURCE_PATH)
    parser.add_argument("--contract-output", type=Path, default=DEFAULT_CONTRACT_PATH)
    args = parser.parse_args(argv)

    retrieved_at = _utc_now()
    query = urlencode({"instId": args.inst_id, "sz": "5"})
    books = _request_json(f"{args.base_url.rstrip('/')}/api/v5/market/books?{query}", timeout=args.timeout)
    trades = _request_json(
        f"{args.base_url.rstrip('/')}/api/v5/market/trades?{urlencode({'instId': args.inst_id, 'limit': '20'})}",
        timeout=args.timeout,
    )
    raw = derive_contract_payload(
        books_payload=books,
        trades_payload=trades,
        symbol=args.symbol,
        inst_id=args.inst_id,
        venue=args.venue,
        retrieved_at=retrieved_at,
    )
    write_json(args.source_output, raw)

    # Feed the same source-backed payload through the runtime normalizer.  It
    # preserves the no-forecast fail-closed decision while making the source
    # visible to /api/status consumers.
    from execution.microstructure import build_microstructure_contract

    normalized = build_microstructure_contract(raw, now=retrieved_at, symbol=args.symbol, venue=args.venue)
    normalized["source_lineage"] = raw["source"]
    normalized["feature_lineage"] = raw["feature_lineage"]
    normalized["forecast_lineage"] = raw["forecast"]
    normalized["snapshot_summary"] = raw["snapshot_summary"]
    normalized["operator_next_action"] = raw["operator_next_action"]
    normalized["decision_contract"]["reason"] = raw["decision_contract"]["reason"]
    write_json(args.contract_output, normalized)
    print(
        "microstructure_public_source_probe: "
        f"source={raw['source']['name']} "
        f"observed_at={raw['source']['observed_at']} "
        f"trades={raw['coverage']['trades_observed']} "
        f"features={len(raw['features'])} "
        f"forecast_edge_bps={normalized['forecast_edge_bps']} "
        f"status={normalized['status']} "
        f"live_risk_on_allowed={normalized['decision_contract']['live_risk_on_allowed']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
