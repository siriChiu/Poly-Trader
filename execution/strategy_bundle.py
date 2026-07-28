from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from execution.config import resolve_trading_config

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STRATEGY_BUNDLE_SCHEMA_VERSION = 1
STRATEGY_BUNDLE_ROOT = Path(os.environ.get("POLY_TRADER_STRATEGY_BUNDLE_DIR", "~/.hermes/poly-trader/strategy_bundles")).expanduser()


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> Optional[str]:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except Exception:
        return None


def _slug(value: Any) -> str:
    text = str(value or "strategy").strip().lower()
    keep: List[str] = []
    last_dash = False
    for char in text:
        if char.isalnum():
            keep.append(char)
            last_dash = False
        elif not last_dash:
            keep.append("-")
            last_dash = True
    return "".join(keep).strip("-") or "strategy"


def _to_float(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed != parsed or parsed in (float("inf"), float("-inf")):
        return None
    return parsed


def _to_int(value: Any) -> Optional[int]:
    parsed = _to_float(value)
    return int(parsed) if parsed is not None else None


def _normalize_symbol(value: Any) -> str:
    text = str(value or "").strip().upper()
    if not text:
        return ""
    if "/" in text:
        return text
    for quote in ("USDT", "USDC", "BUSD", "BTC", "ETH"):
        if text.endswith(quote) and len(text) > len(quote):
            return f"{text[:-len(quote)].rstrip('-_')}/{quote}"
    return text.replace("-", "/") if "-" in text else text


def _status_execution_dict(status_payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    payload: Dict[str, Any] = status_payload if isinstance(status_payload, dict) else {}
    execution_raw = payload.get("execution")
    if not isinstance(execution_raw, dict):
        return {}
    return {str(key): value for key, value in execution_raw.items()}


def _safe_project_source_contract() -> Dict[str, Any]:
    contract: Dict[str, Any] = {
        "project_root": str(PROJECT_ROOT),
        "source_status": "unknown",
    }
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=2,
        ).strip()
        short_commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=PROJECT_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=2,
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--short", "--untracked-files=no"],
            cwd=PROJECT_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
        dirty_files = [line for line in status.splitlines() if line.strip()]
        contract.update(
            {
                "git_commit": commit,
                "git_commit_short": short_commit,
                "source_status": "dirty" if dirty_files else "clean",
                "dirty_tracked_file_count": len(dirty_files),
            }
        )
    except Exception as exc:
        contract.update({"source_status": "unavailable", "error": str(exc)[:160]})
    return contract


def _feature_db_contract(db_path: Optional[str]) -> Dict[str, Any]:
    path = Path(db_path or PROJECT_ROOT / "poly_trader.db")
    contract: Dict[str, Any] = {
        "source": "sqlite.features_normalized",
        "db_path": str(path),
        "status": "unavailable",
        "columns": [],
        "feature_columns": [],
        "row_count": None,
        "min_timestamp": None,
        "max_timestamp": None,
    }
    if not path.exists():
        contract["status"] = "missing_db"
        return contract
    try:
        conn = sqlite3.connect(str(path))
        try:
            columns = [str(row[1]) for row in conn.execute("PRAGMA table_info(features_normalized)").fetchall()]
            feature_columns = [col for col in columns if col.startswith("feat_")]
            row_count = conn.execute("SELECT COUNT(*) FROM features_normalized").fetchone()[0] if columns else None
            min_ts, max_ts = (None, None)
            if "timestamp" in columns:
                min_ts, max_ts = conn.execute("SELECT MIN(timestamp), MAX(timestamp) FROM features_normalized").fetchone()
            contract.update(
                {
                    "status": "available" if columns else "missing_table",
                    "columns": columns,
                    "feature_columns": feature_columns,
                    "row_count": int(row_count) if row_count is not None else None,
                    "min_timestamp": min_ts,
                    "max_timestamp": max_ts,
                    "schema_hash": _sha256_text(canonical_json({"columns": columns, "feature_columns": feature_columns}))[:16],
                }
            )
        finally:
            conn.close()
    except Exception as exc:
        contract.update({"status": "error", "error": str(exc)[:160]})
    return contract


def _predictor_feature_contract(db_path: Optional[str]) -> Dict[str, Any]:
    try:
        from model import predictor

        base_feature_cols = list(getattr(predictor, "BASE_FEATURE_COLS", []) or [])
        lag_steps = list(getattr(predictor, "LAG_STEPS", []) or [])
        target_col = str(getattr(predictor, "DEFAULT_TARGET_COL", "simulated_pyramid_win"))
        model_path_value = str(getattr(predictor, "MODEL_PATH", "model/xgb_model.pkl"))
        status = "available"
    except Exception as exc:
        base_feature_cols = []
        lag_steps = []
        target_col = "simulated_pyramid_win"
        model_path_value = "model/xgb_model.pkl"
        status = "fallback_import_error"
        import_error = str(exc)[:160]
    else:
        import_error = None

    db_contract = _feature_db_contract(db_path)
    payload = {
        "source": "model.predictor.BASE_FEATURE_COLS",
        "status": status,
        "base_feature_columns": base_feature_cols,
        "base_feature_count": len(base_feature_cols),
        "lag_steps": lag_steps,
        "target_col": target_col,
        "disabled_aux_features": [],
        "db_contract": db_contract,
    }
    if import_error:
        payload["import_error"] = import_error
    payload["feature_schema_hash"] = _sha256_text(
        canonical_json(
            {
                "base_feature_columns": base_feature_cols,
                "lag_steps": lag_steps,
                "target_col": target_col,
                "db_feature_columns": db_contract.get("feature_columns") or [],
            }
        )
    )[:16]
    payload["model_path_hint"] = model_path_value
    return payload


def _model_artifact_contract(
    strategy_type: Optional[str],
    model_name: Optional[str],
    *,
    last_results: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    normalized_model = str(model_name or "rule_baseline").strip().lower() or "rule_baseline"
    normalized_type = str(strategy_type or "rule_based").strip().lower() or "rule_based"
    requires_model = normalized_type in {"hybrid", "ml_model"} and normalized_model not in {"rule_baseline", "rule_based"}
    results = last_results if isinstance(last_results, dict) else {}
    exact = results.get("fitted_model_artifact") if isinstance(results.get("fitted_model_artifact"), dict) else {}
    if requires_model and exact:
        exact_path = Path(str(exact.get("model_path") or "")).expanduser()
        expected_sha = str(exact.get("model_sha256") or exact.get("model_hash") or "")
        actual_sha = _sha256_file(exact_path) if exact_path.is_file() else None
        exact_model_name = str(exact.get("model_name") or "").strip().lower()
        exact_valid = bool(
            exact.get("source") == "strategy_lab_backtest"
            and exact_model_name == normalized_model
            and expected_sha
            and actual_sha == expected_sha
        )
        return {
            "strategy_type": normalized_type,
            "model_name": normalized_model,
            "requires_model_artifact": True,
            "status": "exact_backtest_artifact_available" if exact_valid else "exact_backtest_artifact_invalid",
            "source": exact.get("source"),
            "artifacts": [{"path": str(exact_path), "sha256": actual_sha, "size_bytes": exact_path.stat().st_size if exact_path.is_file() else None}],
            "training_data_sha256": exact.get("training_data_sha256"),
            "feature_schema_sha256": exact.get("feature_schema_sha256"),
            "expected_model_sha256": expected_sha or None,
            "operator_note": (
                "已綁定 Strategy Lab 回測時實際評估的 fitted model。"
                if exact_valid
                else "回測 fitted model 的檔案、模型名稱或 checksum 不一致；必須重新回測並固化。"
            ),
        }

    candidate_paths: List[Path] = []
    if normalized_model in {"xgb", "xgboost"}:
        candidate_paths.append(PROJECT_ROOT / "model" / "xgb_model.pkl")
    candidate_paths.append(PROJECT_ROOT / "model" / f"{normalized_model}.pkl")
    candidate_paths.append(PROJECT_ROOT / "model" / "regime_models.pkl")

    seen = set()
    artifacts = []
    for candidate in candidate_paths:
        if str(candidate) in seen:
            continue
        seen.add(str(candidate))
        if not candidate.exists():
            continue
        artifacts.append(
            {
                "path": str(candidate),
                "sha256": _sha256_file(candidate),
                "size_bytes": candidate.stat().st_size,
            }
        )

    status = "not_required_for_rule_based"
    if requires_model and artifacts:
        status = "non_backtest_artifact_available"
    elif requires_model:
        status = "missing_model_artifact_for_hybrid_strategy"

    return {
        "strategy_type": normalized_type,
        "model_name": normalized_model,
        "requires_model_artifact": requires_model,
        "status": status,
        "artifacts": artifacts,
        "operator_note": (
            "Hybrid/ML 策略必須在 binary runtime 中使用同一份模型 artifact / inference format，否則會與 Strategy Lab 漂移。"
            if requires_model
            else "Rule-based 策略不需要外部模型 artifact。"
        ),
    }


def _backtest_contract(last_results: Dict[str, Any]) -> Dict[str, Any]:
    fields = [
        "roi",
        "win_rate",
        "max_drawdown",
        "profit_factor",
        "total_pnl",
        "avg_expected_win_rate",
        "avg_expected_pyramid_pnl",
        "avg_expected_pyramid_quality",
        "avg_expected_drawdown_penalty",
        "avg_expected_time_underwater",
        "avg_decision_quality_score",
    ]
    ints = ["total_trades", "wins", "losses", "max_consecutive_losses"]
    summary: Dict[str, Any] = {}
    for field in fields:
        summary[field] = _to_float(last_results.get(field))
    for field in ints:
        summary[field] = _to_int(last_results.get(field))
    return {
        "metrics": summary,
        "backtest_range": last_results.get("backtest_range") if isinstance(last_results.get("backtest_range"), dict) else None,
        "has_equity_curve": bool(last_results.get("equity_curve")),
        "has_trade_list": bool(last_results.get("trades")),
        "parity_compare_fields": ["total_trades", "roi", "max_drawdown", "profit_factor", "entry_exit_timestamps", "equity_curve_shape"],
    }


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _guardrail_contract(config: Optional[Dict[str, Any]], status_payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    resolved: Dict[str, Any] = resolve_trading_config(config or {})
    payload: Dict[str, Any] = status_payload if isinstance(status_payload, dict) else {}
    status_execution = _status_execution_dict(payload)
    execution_surface_raw = payload.get("execution_surface_contract")
    execution_surface: Dict[str, Any] = execution_surface_raw if isinstance(execution_surface_raw, dict) else {}
    live_runtime_truth_raw = status_execution.get("live_runtime_truth")
    live_runtime_truth: Dict[str, Any] = live_runtime_truth_raw if isinstance(live_runtime_truth_raw, dict) else {}
    live_canary_raw = resolved.get("live_canary")
    live_canary: Dict[str, Any] = live_canary_raw if isinstance(live_canary_raw, dict) else {}
    symbol = _normalize_symbol(payload.get("symbol") or resolved.get("symbol") or "BTC/USDT")
    allowed_symbols = [_normalize_symbol(item) for item in _as_list(live_canary.get("allowed_symbols"))]
    allowed_symbols = [item for item in allowed_symbols if item]
    max_by_symbol_raw_value = live_canary.get("max_base_qty_by_symbol")
    max_by_symbol_raw: Dict[str, Any] = max_by_symbol_raw_value if isinstance(max_by_symbol_raw_value, dict) else {}
    max_by_symbol = {
        _normalize_symbol(key): _to_float(value)
        for key, value in max_by_symbol_raw.items()
        if _normalize_symbol(key)
    }
    fallback_max_qty = _to_float(live_canary.get("max_base_qty"))
    symbol_max_qty = max_by_symbol.get(symbol)
    if symbol_max_qty is None and fallback_max_qty is not None:
        symbol_max_qty = fallback_max_qty
    live_canary_enabled = bool(live_canary.get("enabled", False))
    symbol_allowed = not allowed_symbols or symbol in allowed_symbols
    live_canary_ready = bool(live_canary_enabled and symbol_allowed and symbol_max_qty is not None and symbol_max_qty > 0)
    live_mode = resolved.get("mode") == "live" and bool(resolved.get("enable_live_trading"))
    live_ready = bool(execution_surface.get("live_ready", False))
    live_ready_blockers = _as_list(execution_surface.get("live_ready_blockers"))
    live_buy_add_allowed = bool(live_mode and live_canary_ready and live_ready and not resolved.get("kill_switch"))

    blockers: List[str] = []
    if not live_mode:
        blockers.append("execution mode 不是 live 或 enable_live_trading=false")
    if not live_canary_enabled:
        blockers.append("execution.live_canary.enabled 未開啟")
    if allowed_symbols and not symbol_allowed:
        blockers.append("symbol 不在 live-canary allowlist")
    if symbol_max_qty is None or symbol_max_qty <= 0:
        blockers.append("缺少 symbol-specific max_base_qty cap")
    if resolved.get("kill_switch"):
        blockers.append("kill_switch active")
    if live_ready_blockers:
        blockers.extend(str(item) for item in live_ready_blockers if item)
    deployment_blocker = live_runtime_truth.get("deployment_blocker") or live_runtime_truth.get("execution_guardrail_reason")
    if deployment_blocker:
        blockers.append(str(deployment_blocker))

    venues: Dict[str, Dict[str, Any]] = {}
    venues_raw = resolved.get("venues")
    resolved_venues: Dict[str, Any] = venues_raw if isinstance(venues_raw, dict) else {}
    for venue_key, venue_cfg in resolved_venues.items():
        if not isinstance(venue_cfg, dict):
            continue
        venues[str(venue_key)] = {
            "enabled": bool(venue_cfg.get("enabled", False)),
            "default_type": venue_cfg.get("default_type"),
            "credentials_configured": bool(venue_cfg.get("api_key") and venue_cfg.get("api_secret") and venue_cfg.get("passphrase")),
        }

    return {
        "mode": resolved.get("mode"),
        "venue": resolved.get("venue"),
        "enable_live_trading": bool(resolved.get("enable_live_trading")),
        "dry_run": bool(resolved.get("dry_run", True)),
        "kill_switch": bool(resolved.get("kill_switch", False)),
        "symbol": symbol,
        "venues": venues,
        "live_canary": {
            "enabled": live_canary_enabled,
            "allowed_symbols": allowed_symbols,
            "max_base_qty_by_symbol": max_by_symbol,
            "max_base_qty": fallback_max_qty,
            "symbol_max_base_qty": symbol_max_qty,
            "ready": live_canary_ready,
        },
        "live_ready": live_ready,
        "live_ready_blockers": live_ready_blockers,
        "deployment_blocker": deployment_blocker,
        "order_submission_enabled": live_buy_add_allowed,
        "risk_on_order_enabled": live_buy_add_allowed,
        "live_buy_add_status": "bounded_live_canary_ready" if live_buy_add_allowed else "fail_closed_live_buy_add",
        "fail_closed_reasons": blockers,
        "risk_off_actions": ["wait", "hold", "diagnostics", "reduce", "sell"],
    }


def build_strategy_bundle(
    entry: Dict[str, Any],
    sleeve_key: str,
    *,
    config: Optional[Dict[str, Any]] = None,
    status_payload: Optional[Dict[str, Any]] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    metadata_raw = entry.get("metadata")
    metadata: Dict[str, Any] = dict(metadata_raw) if isinstance(metadata_raw, dict) else {}
    definition_raw = entry.get("definition")
    definition: Dict[str, Any] = dict(definition_raw) if isinstance(definition_raw, dict) else {}
    last_results_raw = entry.get("last_results")
    last_results: Dict[str, Any] = dict(last_results_raw) if isinstance(last_results_raw, dict) else {}
    params_raw = definition.get("params")
    params: Dict[str, Any] = params_raw if isinstance(params_raw, dict) else {}
    strategy_type = metadata.get("strategy_type") or definition.get("type") or "rule_based"
    model_name = metadata.get("model_name") or params.get("model_name") or "rule_baseline"
    strategy_source = str(metadata.get("strategy_source") or entry.get("strategy_source") or "strategy_lab_saved")
    freeze_status = "paper_shadow_topk_bundle_frozen" if strategy_source == "high_conviction_topk_shadow" else "strategy_lab_saved_bundle_frozen"

    feature_contract = _predictor_feature_contract(db_path)
    model_contract = _model_artifact_contract(strategy_type, model_name, last_results=last_results)
    guardrails = _guardrail_contract(config, status_payload)
    backtest = _backtest_contract(last_results)
    project_source = _safe_project_source_contract()

    parity_blockers: List[str] = []
    if model_contract.get("requires_model_artifact") and model_contract.get("status") != "exact_backtest_artifact_available":
        parity_blockers.append(
            f"尚未綁定 Strategy Lab 回測時的 exact fitted model：{model_contract.get('model_name')} ({model_contract.get('status')})"
        )
    if not backtest.get("backtest_range"):
        parity_blockers.append("缺少 backtest_range，binary parity 無法對齊測試窗口")
    if feature_contract.get("status") not in {"available", "fallback_import_error"}:
        parity_blockers.append("feature schema contract 無法從 predictor / DB 完整確認")

    bundle_body = {
        "bundle_schema_version": STRATEGY_BUNDLE_SCHEMA_VERSION,
        "freeze_status": freeze_status,
        "strategy_source": strategy_source,
        "sleeve": {
            "key": sleeve_key,
            "label": metadata.get("primary_sleeve_label"),
        },
        "strategy": {
            "schema_version": entry.get("schema_version"),
            "name": entry.get("name"),
            "slug": entry.get("slug"),
            "created_at": entry.get("created_at"),
            "updated_at": entry.get("updated_at"),
            "definition": definition,
            "metadata": metadata,
        },
        "feature_schema": feature_contract,
        "model_artifact": model_contract,
        "backtest_contract": backtest,
        "execution_guardrails": guardrails,
        "binary_runtime_contract": {
            "status": "backend_managed_worker_required_before_live",
            "ui_invocation_allowed": False,
            "backend_control_plane_required": True,
            "stdout_format": "jsonl",
            "recommended_cli": "polytrader-bot --mode paper|shadow|live-canary --strategy <bundle.json> --db <poly_trader.db> --run-id <execution_run_id>",
            "parity_gates": [
                "read same SQLite/backtest rows as Strategy Lab",
                "emit stable signal/trade timestamps and layers",
                "compare total_trades, ROI, max_drawdown, and equity curve shape",
                "paper/shadow for 24-72h before bounded live-canary",
            ],
        },
        "project_source": project_source,
        "parity_blockers": parity_blockers,
    }
    bundle_hash = _sha256_text(canonical_json(bundle_body))
    deployability_status = "paper_shadow_or_parity_only"
    if guardrails.get("live_buy_add_status") == "bounded_live_canary_ready" and not parity_blockers:
        deployability_status = "live_canary_candidate_after_worker_parity"
    elif guardrails.get("live_buy_add_status") == "fail_closed_live_buy_add":
        deployability_status = "paper_shadow_only_live_buy_add_fail_closed"

    bundle = {
        **bundle_body,
        "bundle_hash": bundle_hash,
        "bundle_id": f"pt-strategy-{bundle_hash[:12]}",
        "bundle_artifact_name": f"{_slug(entry.get('slug') or entry.get('name'))}-{bundle_hash[:12]}.json",
        "deployability_status": deployability_status,
        "operator_action": (
            "Strategy bundle 與回測時 exact fitted model 已固化；backend 可執行受控 Paper/Shadow 推論 cycle，live buy/add 仍依 outcome、venue 與 canary guardrails fail-closed。"
            if model_contract.get("status") == "exact_backtest_artifact_available"
            else "Strategy bundle 已固化，但 Hybrid 尚缺回測時 exact fitted model；請重新回測後再啟動 Paper/Shadow。"
            if model_contract.get("requires_model_artifact")
            else "規則策略 bundle 已固化；可透過 backend paper/shadow cycle 產生演練 event，live buy/add 仍依 guardrails fail-closed。"
            if guardrails.get("live_buy_add_status") == "fail_closed_live_buy_add"
            else "Strategy bundle 與 live-canary guardrails 已具備候選條件；仍需先完成 paper/shadow outcome reconciliation。"
        ),
    }
    return bundle


def bundle_summary(bundle: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(bundle, dict):
        return None
    return {
        "bundle_schema_version": bundle.get("bundle_schema_version"),
        "bundle_id": bundle.get("bundle_id"),
        "bundle_hash": bundle.get("bundle_hash"),
        "freeze_status": bundle.get("freeze_status"),
        "deployability_status": bundle.get("deployability_status"),
        "feature_schema_hash": (bundle.get("feature_schema") or {}).get("feature_schema_hash") if isinstance(bundle.get("feature_schema"), dict) else None,
        "model_artifact_status": (bundle.get("model_artifact") or {}).get("status") if isinstance(bundle.get("model_artifact"), dict) else None,
        "live_buy_add_status": (bundle.get("execution_guardrails") or {}).get("live_buy_add_status") if isinstance(bundle.get("execution_guardrails"), dict) else None,
        "order_submission_enabled": (bundle.get("execution_guardrails") or {}).get("order_submission_enabled") if isinstance(bundle.get("execution_guardrails"), dict) else None,
        "parity_blockers": bundle.get("parity_blockers") if isinstance(bundle.get("parity_blockers"), list) else [],
        "operator_action": bundle.get("operator_action"),
    }


def persist_strategy_bundle(
    bundle: Optional[Dict[str, Any]],
    *,
    run_id: str,
    profile_id: str,
    root: Optional[Path] = None,
) -> Dict[str, Any]:
    if not isinstance(bundle, dict) or not bundle.get("bundle_hash"):
        return {
            "status": "missing_strategy_bundle",
            "strategy_bundle_hash": None,
            "strategy_bundle_path": None,
            "strategy_bundle_json": None,
        }
    target_root = Path(root or STRATEGY_BUNDLE_ROOT).expanduser()
    target_root.mkdir(parents=True, exist_ok=True)
    artifact = {
        **bundle,
        "frozen_at": utcnow_iso(),
        "execution_binding": {
            "run_id": run_id,
            "profile_id": profile_id,
            "binding_status": "control_plane_freeze_persisted",
            "worker_status": "not_started_backend_worker_pending",
        },
    }
    file_name = f"{_slug(profile_id)}-{str(bundle.get('bundle_hash'))[:12]}-{_slug(run_id)[:8]}.json"
    path = target_root / file_name
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return {
        "status": "persisted",
        "strategy_bundle_hash": bundle.get("bundle_hash"),
        "strategy_bundle_path": str(path),
        "strategy_bundle_json": canonical_json(artifact),
    }
