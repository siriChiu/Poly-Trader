"""Machine-readable microstructure readiness contract.

This module deliberately does not fabricate order-book or trade-flow values.  It
normalizes an optional source artifact and keeps the execution edge gate in
observation-only mode until a fresh, source-backed contract is available.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional


MICROSTRUCTURE_CONTRACT_SCHEMA_VERSION = 1
MICROSTRUCTURE_FEATURES = (
    "orderbook_imbalance_l1",
    "orderbook_imbalance_l5",
    "spread_bps",
    "depth_50bps",
    "depth_200bps",
    "microprice_deviation",
    "trade_flow_imbalance",
    "liquidity_stress_score",
)
DEFAULT_STALE_AFTER_SECONDS = 300.0
DEFAULT_WINDOW_MINUTES = 60
DEFAULT_ARTIFACT_PATH = Path(__file__).resolve().parents[1] / "data" / "microstructure_contract.json"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1]
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_time(value: Any) -> Optional[datetime]:
    normalized = _iso(value)
    if normalized is None:
        return None
    return datetime.fromisoformat(normalized.replace("Z", "+00:00"))


def _number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result else None


def _as_dict(value: Any) -> Dict[str, Any]:
    return {str(key): item for key, item in value.items()} if isinstance(value, Mapping) else {}


def _config_source(config: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    source = config or {}
    micro_cfg = source.get("microstructure") if isinstance(source, Mapping) else None
    if not isinstance(micro_cfg, Mapping):
        execution_cfg = source.get("execution") if isinstance(source, Mapping) else None
        micro_cfg = execution_cfg.get("microstructure") if isinstance(execution_cfg, Mapping) else None
    return dict(micro_cfg) if isinstance(micro_cfg, Mapping) else {}


def _feature_contract(
    name: str,
    raw: Any,
    *,
    source_available: bool,
    source_fresh: bool,
    coverage_ratio: float,
) -> Dict[str, Any]:
    item = dict(raw) if isinstance(raw, Mapping) else {}
    value = _number(item.get("value"))
    available = bool(item.get("available", source_available and value is not None))
    item["value"] = value
    item["available"] = bool(available and source_available)
    item["coverage_ratio"] = max(min(float(item.get("coverage_ratio", coverage_ratio) or 0.0), 1.0), 0.0)
    item["freshness_status"] = "fresh" if item["available"] and source_fresh else "missing"
    item["source"] = str(item.get("source") or "unavailable") if item["available"] else "unavailable"
    item["maturity"] = str(item.get("maturity") or ("mature" if item["available"] else "blocked"))
    return item


def build_microstructure_contract(
    artifact: Optional[Mapping[str, Any]] = None,
    *,
    config: Optional[Mapping[str, Any]] = None,
    now: Optional[datetime] = None,
    symbol: Optional[str] = None,
    venue: Optional[str] = None,
) -> Dict[str, Any]:
    """Return normalized microstructure truth without inventing missing values."""
    now_dt = now or _utc_now()
    raw = dict(artifact) if isinstance(artifact, Mapping) else {}
    source_cfg = _config_source(config)
    raw_source = _as_dict(raw.get("source"))
    configured = bool(raw_source.get("configured", source_cfg.get("enabled", False)))
    source_available = bool(raw_source.get("available", False)) and configured
    generated_at = _iso(raw.get("generated_at"))
    generated_dt = _parse_time(generated_at)
    freshness_raw = _as_dict(raw.get("freshness"))
    stale_after = _number(freshness_raw.get("stale_after_seconds"))
    stale_after = stale_after if stale_after is not None and stale_after > 0 else DEFAULT_STALE_AFTER_SECONDS
    age_seconds: Optional[float] = None
    if generated_dt is not None:
        age_seconds = max((now_dt.astimezone(timezone.utc) - generated_dt).total_seconds(), 0.0)
    artifact_fresh = generated_dt is not None and age_seconds is not None and age_seconds <= stale_after
    observed_at = _iso(raw_source.get("observed_at"))
    observed_dt = _parse_time(observed_at)
    source_fresh = bool(source_available and observed_dt is not None and (now_dt.astimezone(timezone.utc) - observed_dt).total_seconds() <= stale_after)

    coverage_raw = _as_dict(raw.get("coverage"))
    coverage_ratio = _number(coverage_raw.get("coverage_ratio")) or 0.0
    coverage_ratio = max(min(coverage_ratio, 1.0), 0.0)
    feature_raw = _as_dict(raw.get("features"))
    features = {
        name: _feature_contract(
            name,
            feature_raw.get(name),
            source_available=source_available,
            source_fresh=source_fresh,
            coverage_ratio=coverage_ratio,
        )
        for name in MICROSTRUCTURE_FEATURES
    }
    all_features_ready = all(
        bool(item.get("available"))
        and item.get("freshness_status") == "fresh"
        and float(item.get("coverage_ratio") or 0.0) > 0.0
        for item in features.values()
    )
    forecast = _as_dict(raw.get("forecast"))
    forecast_edge_bps = _number(raw.get("forecast_edge_bps"))
    forecast_source = str(forecast.get("source") or raw.get("forecast_source") or "unavailable")
    forecast_available = bool(
        forecast_edge_bps is not None
        and source_available
        and source_fresh
        and artifact_fresh
        and all_features_ready
    )
    if not forecast_available:
        forecast_edge_bps = None
    ready = bool(source_available and source_fresh and artifact_fresh and all_features_ready and forecast_available)
    source_status = "ready" if source_available and source_fresh else ("missing" if not source_available else "stale")
    status = "ready" if ready else ("blocked_missing_source" if not source_available else "observation_only")
    reason = (
        "fresh source-backed microstructure features and forecast are available"
        if ready
        else "microstructure source/coverage/forecast is unavailable or stale; remain observation-only"
    )

    return {
        "schema_version": MICROSTRUCTURE_CONTRACT_SCHEMA_VERSION,
        "generated_at": generated_at,
        "symbol": str(symbol or raw.get("symbol") or source_cfg.get("symbol") or "BTC/USDT"),
        "venue": str(venue or raw.get("venue") or source_cfg.get("venue") or "okx"),
        "status": status,
        "source": {
            "kind": str(raw_source.get("kind") or source_cfg.get("kind") or "orderbook_and_trade_flow"),
            "name": str(raw_source.get("name") or source_cfg.get("name") or "not_configured"),
            "configured": configured,
            "available": source_available,
            "observed_at": observed_at,
            "freshness_status": source_status,
        },
        "freshness": {
            "artifact_status": "fresh" if artifact_fresh else "stale_or_missing",
            "artifact_age_seconds": round(age_seconds, 3) if age_seconds is not None else None,
            "source_status": source_status,
            "stale_after_seconds": stale_after,
        },
        "coverage": {
            "window_minutes": int(_number(coverage_raw.get("window_minutes")) or DEFAULT_WINDOW_MINUTES),
            "observed_events": int(_number(coverage_raw.get("observed_events")) or 0),
            "covered_events": int(_number(coverage_raw.get("covered_events")) or 0),
            "coverage_ratio": coverage_ratio,
        },
        "features": features,
        "forecast_edge_bps": forecast_edge_bps,
        "forecast": {
            "available": forecast_available,
            "value_bps": forecast_edge_bps,
            "source": forecast_source if forecast_available else "unavailable",
            "freshness_status": "fresh" if forecast_available else "missing",
        },
        "decision_contract": {
            "status": "candidate_ready" if ready else "observation_only",
            "observation_only": not ready,
            "paper_shadow_risk_on_allowed": ready,
            "live_risk_on_allowed": False,
            "reason": reason,
        },
        "operator_next_action": (
            "維持 observation-only；接入可驗證的 orderbook/trade-flow source，補齊 freshness、coverage 與 forecast_edge_bps 後再評估 paper/shadow risk-on。"
            if not ready
            else "僅可進入 paper/shadow candidate review；live buy/add 仍需其他 exact support、venue、breaker 與 bounded-canary gates。"
        ),
    }


def load_microstructure_contract(
    path: Path = DEFAULT_ARTIFACT_PATH,
    *,
    config: Optional[Mapping[str, Any]] = None,
    now: Optional[datetime] = None,
    symbol: Optional[str] = None,
    venue: Optional[str] = None,
) -> Dict[str, Any]:
    """Load and normalize the optional artifact; missing/invalid means blocked."""
    raw: Optional[Dict[str, Any]] = None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            raw = payload
    except (OSError, json.JSONDecodeError, TypeError):
        raw = None
    return build_microstructure_contract(raw, config=config, now=now, symbol=symbol, venue=venue)


def write_microstructure_contract(
    path: Path = DEFAULT_ARTIFACT_PATH,
    *,
    config: Optional[Mapping[str, Any]] = None,
    now: Optional[datetime] = None,
    symbol: Optional[str] = None,
    venue: Optional[str] = None,
) -> Dict[str, Any]:
    """Write a deterministic missing-source/observed-source contract artifact."""
    now_dt = now or _utc_now()
    current = build_microstructure_contract(
        {"generated_at": _iso(now_dt)},
        config=config,
        now=now_dt,
        symbol=symbol,
        venue=venue,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return current
