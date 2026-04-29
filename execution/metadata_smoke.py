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


def _build_runtime_proof_contract(
    venue: str,
    *,
    metadata_ok: bool,
    enabled: bool,
    credentials_configured: bool,
) -> Dict[str, Any]:
    """Describe what is still missing before a venue can be called live-ready.

    Public market metadata being readable is necessary, but it is not runtime proof
    that credentials, order acknowledgement, fills, and cancel/recovery paths work.
    Persist this contract in the smoke artifact itself so every consumer (API,
    docs, cron summaries, and UI) sees the same blocker semantics instead of
    interpreting ok=True as venue readiness.
    """
    blockers = []
    if not metadata_ok:
        blockers.append("元資料契約尚未通過")
    if not enabled:
        blockers.append("場館設定停用")
    if not credentials_configured:
        blockers.append("live exchange credential 尚未驗證")
    blockers.extend([
        "order ack lifecycle 尚未驗證",
        "fill lifecycle 尚未驗證",
    ])

    if not metadata_ok:
        proof_state = "metadata_contract_failed"
        operator_next_action = f"先修復 {venue} 元資料檢查，再評估憑證與實單生命週期。"
    elif not enabled:
        proof_state = "config_disabled_metadata_only"
        operator_next_action = f"若要啟用 {venue}，先開啟場館設定並配置憑證；目前只能作公開元資料觀測。"
    elif not credentials_configured:
        proof_state = "public_metadata_only"
        operator_next_action = f"先配置 {venue} 交易憑證，再用沙盒或極小額委託捕捉委託確認 / 成交 / 取消生命週期。"
    else:
        proof_state = "credentials_configured_missing_runtime_lifecycle"
        operator_next_action = f"使用 {venue} 沙盒或極小額實單捕捉交易所回傳的委託確認 / 成交 / 取消生命週期。"

    return {
        "proof_state": proof_state,
        "readiness_scope": "venue_runtime_proof_required",
        "blockers": blockers,
        "operator_next_action": operator_next_action,
        "verify_next": "重跑元資料檢查，並在 /api/status 的場館生命週期通道看到交易所回傳的委託確認 / 成交 / 取消證據。",
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
            credentials_configured = bool(
                venue_cfg.get("api_key")
                or venue_cfg.get("api_secret")
                or venue_cfg.get("secret")
                or venue_cfg.get("passphrase")
            )
            results[venue_key] = {
                "ok": False,
                "venue": venue_key,
                "symbol": smoke_symbol,
                "enabled_in_config": venue_enabled,
                "credentials_configured": credentials_configured,
                "error": f"unsupported venue: {venue_key}",
                **_build_runtime_proof_contract(
                    venue_key,
                    metadata_ok=False,
                    enabled=venue_enabled,
                    credentials_configured=credentials_configured,
                ),
            }
            continue
        try:
            adapter = adapter_cls(venue_cfg, dry_run=True)
            credentials_configured = adapter.credentials_configured()
            rules = adapter.market_rules(smoke_symbol)
            summary = _build_contract_summary(rules)
            results[venue_key] = {
                "ok": True,
                "venue": venue_key,
                "symbol": smoke_symbol,
                "enabled_in_config": venue_enabled,
                "credentials_configured": credentials_configured,
                "contract": summary,
                **_build_runtime_proof_contract(
                    venue_key,
                    metadata_ok=True,
                    enabled=venue_enabled,
                    credentials_configured=credentials_configured,
                ),
            }
        except Exception as exc:
            credentials_configured = False
            try:
                credentials_configured = bool(adapter.credentials_configured())  # type: ignore[name-defined]
            except Exception:
                pass
            results[venue_key] = {
                "ok": False,
                "venue": venue_key,
                "symbol": smoke_symbol,
                "enabled_in_config": venue_enabled,
                "credentials_configured": credentials_configured,
                "error": str(exc),
                **_build_runtime_proof_contract(
                    venue_key,
                    metadata_ok=False,
                    enabled=venue_enabled,
                    credentials_configured=credentials_configured,
                ),
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
