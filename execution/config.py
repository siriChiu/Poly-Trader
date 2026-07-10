from __future__ import annotations

from copy import deepcopy
import os
from typing import Any, Dict

SUPPORTED_EXECUTION_VENUES = {"okx"}
DEFAULT_EXECUTION_VENUE = "okx"

DEFAULT_COST_AWARE_EDGE_CONFIG: Dict[str, float] = {
    # Conservative first production-default model: taker fee + spread + slippage
    # + one safety buffer = 15 bps.  drawdown_buffer_bps is explicit so the
    # readiness contract can show it, but starts at 0 until runtime supplies a
    # model-specific drawdown buffer.
    "taker_fee_bps": 5.0,
    "spread_bps": 3.0,
    "slippage_bps": 2.0,
    "volatility_buffer_bps": 5.0,
    "drawdown_buffer_bps": 0.0,
}
_COST_AWARE_EDGE_ALIASES = {
    "fee_bps": "taker_fee_bps",
    "pyramid_drawdown_buffer_bps": "drawdown_buffer_bps",
}


DEFAULT_EXECUTION_CONFIG: Dict[str, Any] = {
    "mode": "paper",
    "venue": DEFAULT_EXECUTION_VENUE,
    "enable_live_trading": False,
    "max_daily_loss_pct": 0.03,
    "max_consecutive_failures": 3,
    "kill_switch": False,
    "cost_aware_edge": dict(DEFAULT_COST_AWARE_EDGE_CONFIG),
    "venues": {
        "okx": {
            "enabled": True,
            "api_key": "",
            "api_secret": "",
            "passphrase": "",
            "default_type": "spot",
        },
    },
}


def _first_env_value(*names: str) -> str:
    for name in names:
        value = os.environ.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _normalize_execution_venue(value: Any) -> tuple[str, str | None]:
    requested = str(value or DEFAULT_EXECUTION_VENUE).strip().lower() or DEFAULT_EXECUTION_VENUE
    if requested in SUPPORTED_EXECUTION_VENUES:
        return requested, None
    return DEFAULT_EXECUTION_VENUE, requested


def resolve_trading_config(config: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(DEFAULT_EXECUTION_CONFIG)
    source = deepcopy(config or {})
    execution_cfg = source.get("execution") or {}
    trading_cfg = source.get("trading") or {}
    okx_cfg = source.get("okx") or {}

    merged.update({k: v for k, v in execution_cfg.items() if k not in {"venues", "cost_aware_edge"} and v is not None})
    cost_aware_edge = deepcopy(DEFAULT_COST_AWARE_EDGE_CONFIG)

    def _merge_cost_source(cost_source: Any) -> None:
        if not isinstance(cost_source, dict):
            return
        for raw_key, raw_value in cost_source.items():
            key = _COST_AWARE_EDGE_ALIASES.get(str(raw_key), str(raw_key))
            if key not in DEFAULT_COST_AWARE_EDGE_CONFIG or raw_value is None:
                continue
            try:
                cost_aware_edge[key] = float(raw_value)
            except (TypeError, ValueError):
                continue

    _merge_cost_source(source.get("cost_aware_edge"))
    _merge_cost_source({key: trading_cfg.get(key) for key in [*DEFAULT_COST_AWARE_EDGE_CONFIG.keys(), *_COST_AWARE_EDGE_ALIASES.keys()]})
    _merge_cost_source(execution_cfg.get("cost_aware_edge"))
    merged["cost_aware_edge"] = cost_aware_edge
    merged["mode"] = str(execution_cfg.get("mode") or ("paper" if trading_cfg.get("dry_run", True) else "live_canary"))
    requested_venue = execution_cfg.get("venue") or trading_cfg.get("venue") or merged.get("venue") or DEFAULT_EXECUTION_VENUE
    normalized_venue, unsupported_requested = _normalize_execution_venue(requested_venue)
    merged["venue"] = normalized_venue
    if unsupported_requested:
        merged["unsupported_venue_requested"] = unsupported_requested
    else:
        merged.pop("unsupported_venue_requested", None)
    merged["enable_live_trading"] = bool(execution_cfg.get("enable_live_trading", not trading_cfg.get("dry_run", True)))
    merged["kill_switch"] = bool(execution_cfg.get("kill_switch", False))
    merged["max_daily_loss_pct"] = float(execution_cfg.get("max_daily_loss_pct", merged["max_daily_loss_pct"]))
    merged["max_consecutive_failures"] = int(execution_cfg.get("max_consecutive_failures", merged["max_consecutive_failures"]))

    venue_overrides = execution_cfg.get("venues") or {}
    merged["venues"]["okx"].update(okx_cfg)
    for venue_name, venue_cfg in venue_overrides.items():
        venue_key = str(venue_name or "").strip().lower()
        if not venue_key or not isinstance(venue_cfg, dict):
            continue
        # Preserve unsupported venues (for example Binance before an adapter exists)
        # so readiness surfaces can show an explicit unsupported/configured blocker
        # instead of silently falling back to OKX and hiding operator intent.
        if venue_key not in merged["venues"]:
            merged["venues"][venue_key] = {}
        merged["venues"][venue_key].update(venue_cfg)

    for venue_key, venue_cfg in list(merged["venues"].items()):
        if not isinstance(venue_cfg, dict):
            merged["venues"][venue_key] = {"enabled": False}
            continue
        venue_cfg["enabled"] = bool(venue_cfg.get("enabled", venue_key == DEFAULT_EXECUTION_VENUE))
        if venue_key == "okx":
            env_values = {
                "api_key": _first_env_value("POLY_TRADER_OKX_API_KEY", "OKX_API_KEY"),
                "api_secret": _first_env_value("POLY_TRADER_OKX_API_SECRET", "OKX_API_SECRET"),
                "passphrase": _first_env_value("POLY_TRADER_OKX_PASSPHRASE", "OKX_PASSPHRASE"),
            }
            for key, value in env_values.items():
                if value:
                    venue_cfg[key] = value
    merged["dry_run"] = merged["mode"] != "live" or not merged["enable_live_trading"]
    return merged


def resolve_cost_aware_edge_config(config: Dict[str, Any]) -> Dict[str, float]:
    """Return normalized cost-aware edge inputs used by readiness gates.

    The returned dict always contains every machine-readable component.  Missing
    forecast edge still fails closed in readiness; defaults only prevent the
    cost side of the contract from being absent.
    """

    resolved = resolve_trading_config(config or {})
    values = resolved.get("cost_aware_edge") if isinstance(resolved.get("cost_aware_edge"), dict) else {}
    merged = deepcopy(DEFAULT_COST_AWARE_EDGE_CONFIG)
    for key, value in values.items():
        if key not in merged or value is None:
            continue
        try:
            merged[key] = float(value)
        except (TypeError, ValueError):
            continue
    return merged
