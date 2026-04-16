from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional

from execution.config import resolve_trading_config
from execution.exchanges.binance_adapter import BinanceAdapter
from execution.exchanges.okx_adapter import OKXAdapter

ADAPTER_FACTORIES = {
    "binance": BinanceAdapter,
    "okx": OKXAdapter,
}


def _normalize_symbol(symbol: str) -> str:
    value = str(symbol or "").strip().upper()
    if not value:
        return "BTC/USDT"
    if "/" in value:
        return value
    common_quotes = ("USDT", "USDC", "BUSD", "BTC", "ETH")
    for quote in common_quotes:
        if value.endswith(quote) and len(value) > len(quote):
            base = value[:-len(quote)]
            return f"{base}/{quote}"
    return value


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _build_contract_summary(rules: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "symbol": rules.get("symbol"),
        "base": rules.get("base"),
        "quote": rules.get("quote"),
        "min_qty": rules.get("min_qty"),
        "min_cost": rules.get("min_cost"),
        "amount_precision": rules.get("amount_precision"),
        "price_precision": rules.get("price_precision"),
        "step_size": rules.get("step_size"),
        "tick_size": rules.get("tick_size"),
        "qty_contract": rules.get("qty_contract") or {},
        "price_contract": rules.get("price_contract") or {},
    }


def _iter_venues(execution_cfg: Dict[str, Any], venues: Optional[Iterable[str]]) -> list[str]:
    if venues:
        normalized = [str(v).strip().lower() for v in venues if str(v).strip()]
        return list(dict.fromkeys(normalized))
    configured = list((execution_cfg.get("venues") or {}).keys())
    return configured or list(ADAPTER_FACTORIES.keys())


def run_metadata_smoke(
    config: Dict[str, Any],
    *,
    symbol: str = "BTC/USDT",
    venues: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    execution_cfg = resolve_trading_config(config or {})
    smoke_symbol = _normalize_symbol(symbol)
    results: Dict[str, Any] = {}

    for venue in _iter_venues(execution_cfg, venues):
        venue_key = str(venue or "").lower()
        adapter_cls = ADAPTER_FACTORIES.get(venue_key)
        venue_cfg = ((execution_cfg.get("venues") or {}).get(venue_key) or {}).copy()
        venue_enabled = bool(venue_cfg.get("enabled", False))
        if adapter_cls is None:
            results[venue_key] = {
                "ok": False,
                "venue": venue_key,
                "symbol": smoke_symbol,
                "enabled_in_config": venue_enabled,
                "error": f"unsupported venue: {venue_key}",
            }
            continue
        try:
            adapter = adapter_cls(venue_cfg, dry_run=True)
            rules = adapter.market_rules(smoke_symbol)
            summary = _build_contract_summary(rules)
            results[venue_key] = {
                "ok": True,
                "venue": venue_key,
                "symbol": smoke_symbol,
                "enabled_in_config": venue_enabled,
                "credentials_configured": adapter.credentials_configured(),
                "contract": summary,
            }
        except Exception as exc:
            results[venue_key] = {
                "ok": False,
                "venue": venue_key,
                "symbol": smoke_symbol,
                "enabled_in_config": venue_enabled,
                "error": str(exc),
            }

    ok_count = sum(1 for item in results.values() if item.get("ok"))
    return {
        "generated_at": _utc_now(),
        "symbol": smoke_symbol,
        "all_ok": bool(results) and ok_count == len(results),
        "ok_count": ok_count,
        "venues_checked": len(results),
        "results": results,
    }
