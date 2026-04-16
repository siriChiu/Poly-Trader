from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict


DEFAULT_EXECUTION_CONFIG: Dict[str, Any] = {
    "mode": "paper",
    "venue": "binance",
    "enable_live_trading": False,
    "max_daily_loss_pct": 0.03,
    "max_consecutive_failures": 3,
    "kill_switch": False,
    "venues": {
        "binance": {
            "enabled": True,
            "api_key": "",
            "api_secret": "",
            "passphrase": "",
            "default_type": "spot",
        },
        "okx": {
            "enabled": False,
            "api_key": "",
            "api_secret": "",
            "passphrase": "",
            "default_type": "spot",
        },
    },
}


def resolve_trading_config(config: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(DEFAULT_EXECUTION_CONFIG)
    source = deepcopy(config or {})
    execution_cfg = source.get("execution") or {}
    trading_cfg = source.get("trading") or {}
    binance_cfg = source.get("binance") or {}
    okx_cfg = source.get("okx") or {}

    merged.update({k: v for k, v in execution_cfg.items() if k != "venues" and v is not None})
    merged["mode"] = str(execution_cfg.get("mode") or ("paper" if trading_cfg.get("dry_run", True) else "live_canary"))
    merged["venue"] = str(execution_cfg.get("venue") or trading_cfg.get("venue") or "binance")
    merged["enable_live_trading"] = bool(execution_cfg.get("enable_live_trading", not trading_cfg.get("dry_run", True)))
    merged["kill_switch"] = bool(execution_cfg.get("kill_switch", False))
    merged["max_daily_loss_pct"] = float(execution_cfg.get("max_daily_loss_pct", merged["max_daily_loss_pct"]))
    merged["max_consecutive_failures"] = int(execution_cfg.get("max_consecutive_failures", merged["max_consecutive_failures"]))

    venue_overrides = execution_cfg.get("venues") or {}
    merged["venues"]["binance"].update(binance_cfg)
    merged["venues"]["okx"].update(okx_cfg)
    for venue_name, venue_cfg in venue_overrides.items():
        if venue_name not in merged["venues"] or not isinstance(venue_cfg, dict):
            continue
        merged["venues"][venue_name].update(venue_cfg)

    merged["venues"]["binance"]["enabled"] = bool(merged["venues"]["binance"].get("enabled", True))
    merged["venues"]["okx"]["enabled"] = bool(merged["venues"]["okx"].get("enabled", False))
    merged["dry_run"] = merged["mode"] != "live" or not merged["enable_live_trading"]
    return merged
