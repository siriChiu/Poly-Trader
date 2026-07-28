from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from execution.control_plane import (
    CONTROL_MODE,
    CONTROL_PLANE_OPERATOR_MESSAGE,
    CONTROL_PLANE_UPGRADE_PREREQUISITE,
    PRIMARY_SLEEVE_META,
    PRIMARY_SLEEVE_ORDER,
    build_execution_strategy_source_snapshot,
)
from execution.config import resolve_cost_aware_edge_config, resolve_trading_config
from execution.range_chop_playbook import build_range_chop_playbook
from execution.risk_control import check_position_size


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}



def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []



def _to_float(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None
    return None



def _to_int(value: Any) -> Optional[int]:
    number = _to_float(value)
    if number is None:
        return None
    return int(number)


LIVE_CANARY_MAX_BASE_QTY_CAP = 0.0001


def _normalize_symbol(value: Any) -> str:
    return str(value or "").strip().upper().replace("/", "")


def _build_live_canary_policy_gate(config: Optional[Dict[str, Any]], symbol: str) -> Dict[str, Any]:
    resolved = resolve_trading_config(config or {})
    live_canary = resolved.get("live_canary") if isinstance(resolved.get("live_canary"), dict) else {}
    normalized_symbol = _normalize_symbol(symbol)
    allowed_symbols = [
        _normalize_symbol(item)
        for item in _as_list(live_canary.get("allowed_symbols"))
        if _normalize_symbol(item)
    ]
    max_by_symbol_raw = live_canary.get("max_base_qty_by_symbol")
    max_by_symbol = max_by_symbol_raw if isinstance(max_by_symbol_raw, dict) else {}
    normalized_caps = {_normalize_symbol(key): value for key, value in max_by_symbol.items()}
    symbol_max_qty = _to_float(max_by_symbol.get(symbol) or max_by_symbol.get(normalized_symbol) or normalized_caps.get(normalized_symbol))

    mode_is_live = str(resolved.get("mode") or "").strip().lower() == "live"
    enable_live_trading = bool(resolved.get("enable_live_trading"))
    live_canary_enabled = bool(live_canary.get("enabled"))
    explicit_symbol_allowed = bool(allowed_symbols) and normalized_symbol in set(allowed_symbols)
    symbol_cap_configured = symbol_max_qty is not None and symbol_max_qty > 0
    symbol_cap_within_bound = symbol_max_qty is not None and 0 < symbol_max_qty <= LIVE_CANARY_MAX_BASE_QTY_CAP
    kill_switch_clear = not bool(resolved.get("kill_switch"))
    passed = bool(
        mode_is_live
        and enable_live_trading
        and live_canary_enabled
        and explicit_symbol_allowed
        and symbol_cap_configured
        and symbol_cap_within_bound
        and kill_switch_clear
    )

    blockers: List[str] = []
    if not mode_is_live:
        blockers.append("execution.mode must be live")
    if not enable_live_trading:
        blockers.append("enable_live_trading must be true")
    if not live_canary_enabled:
        blockers.append("execution.live_canary.enabled must be true")
    if not explicit_symbol_allowed:
        blockers.append("explicit allowed_symbols must include the symbol")
    if not symbol_cap_configured:
        blockers.append("symbol max_base_qty_by_symbol cap must be configured")
    elif not symbol_cap_within_bound:
        blockers.append(f"symbol max_base_qty_by_symbol cap must be <= {LIVE_CANARY_MAX_BASE_QTY_CAP}")
    if not kill_switch_clear:
        blockers.append("kill_switch must be false")

    return {
        "key": "live_canary_policy_gate",
        "label": "Live-canary policy gate",
        "status": "passed" if passed else "blocked",
        "passed": passed,
        "current": 1 if passed else 0,
        "required": 1,
        "gap": 0 if passed else 1,
        "summary": (
            f"mode={resolved.get('mode') or '—'} / enable_live_trading={str(enable_live_trading).lower()} / "
            f"live_canary.enabled={str(live_canary_enabled).lower()} / "
            f"allowed_symbol={str(explicit_symbol_allowed).lower()} / "
            f"symbol_cap={symbol_max_qty if symbol_max_qty is not None else '—'} / "
            f"max_allowed_cap={LIVE_CANARY_MAX_BASE_QTY_CAP}"
        ),
        "blockers": blockers,
        "next_action": f"若所有 runtime gate 通過，仍必須先配置 explicit allowed_symbols 與每 symbol <= {LIVE_CANARY_MAX_BASE_QTY_CAP} BTC 的 cap，adapter 前才可允許最小 canary。",
    }


def build_live_canary_policy_gate(config: Optional[Dict[str, Any]], symbol: str) -> Dict[str, Any]:
    return _build_live_canary_policy_gate(config, symbol)


def _api_trade_symbol(symbol: Any) -> str:
    """Prefer the hyphenated spot symbol shape used by operator trade probes."""
    text = str(symbol or "BTCUSDT").strip().upper().replace("/", "-")
    if "-" in text:
        return text
    for quote in ("USDT", "USDC", "USD"):
        if text.endswith(quote) and len(text) > len(quote):
            return f"{text[:-len(quote)]}-{quote}"
    return text or "BTC-USDT"


def _build_milestone_progression(
    *,
    symbol: str,
    canary_ready: bool,
    shadow_ready: bool,
    support_passed: bool,
    release_passed: bool,
    venue_passed: bool,
    model_gate_passed: bool,
    live_canary_policy_passed: bool,
    blocking_gate: Optional[Dict[str, Any]],
    venue_dry_run_proof: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build an operator-safe MILESTONE router so a closed live gate does not deadlock the program.

    The router never unlocks live buy/add by itself.  It gives callers a deterministic
    next lane: no-order wait, paper/shadow buy, venue proof, or bounded canary only
    after every hard gate is green.
    """
    trade_symbol = _api_trade_symbol(symbol)
    tiny_shadow_qty = 0.00001
    blocked_key = str(_as_dict(blocking_gate).get("key") or "")
    blocked_label = str(_as_dict(blocking_gate).get("label") or "無")
    proof = _as_dict(venue_dry_run_proof)

    can_enter_shadow = bool(shadow_ready and not canary_ready)
    if canary_ready:
        active_lane = "bounded_live_canary"
        active_label = "M5 bounded live-canary"
        progression_status = "bounded_canary_ready"
        preferred_entrypoint: Dict[str, Any] = {
            "endpoint": "/api/trade",
            "method": "POST",
            "payload_template": {"side": "buy", "symbol": trade_symbol, "qty": "<= execution.live_canary.max_base_qty_by_symbol[symbol]"},
            "expected_result": "僅允許 bounded live-canary cap 內的第一層最小委託；仍由 adapter 前 guardrail 複查。",
            "live_order_submitted": "only_after_adapter_guardrails_pass",
        }
    elif can_enter_shadow:
        active_lane = "paper_shadow_buy"
        active_label = "M5 safe paper/shadow entry lane"
        progression_status = "safe_lane_active"
        preferred_entrypoint = {
            "endpoint": "/api/trade",
            "method": "POST",
            "payload": {"side": "shadow_buy", "symbol": trade_symbol, "qty": tiny_shadow_qty},
            "expected_result": "HTTP 200；dry_run=true；shadow_trade=true；live_order_submitted=false。",
            "live_order_submitted": False,
        }
    elif not venue_passed:
        active_lane = "venue_dry_run_lifecycle"
        active_label = "M5 venue dry-run lifecycle lane"
        progression_status = "safe_lane_active"
        preferred_entrypoint = {
            "command": proof.get("verify_next") or "python scripts/venue_dry_run_proof.py",
            "expected_result": "產生 preview / ack / cancel / fill / reconciliation proof；不送 live order。",
            "live_order_submitted": False,
        }
    else:
        active_lane = "wait_hold_no_order"
        active_label = "M5 wait/hold no-order lane"
        progression_status = "safe_lane_active"
        preferred_entrypoint = {
            "endpoint": "/api/trade",
            "method": "POST",
            "payload": {"side": "wait", "symbol": trade_symbol, "qty": 0},
            "expected_result": "HTTP 200；no_order_submitted=true。",
            "live_order_submitted": False,
        }

    safe_entry_lanes = [
        {
            "key": "wait_hold_no_order",
            "label": "等待 / 觀望 no-order",
            "can_enter": True,
            "endpoint": "/api/trade",
            "payload": {"side": "wait", "symbol": trade_symbol, "qty": 0},
            "expected_result": "HTTP 200；no_order_submitted=true。",
            "live_order_submitted": False,
        },
        {
            "key": "paper_shadow_buy",
            "label": "Paper / Shadow 買入演練",
            "can_enter": bool(shadow_ready),
            "endpoint": "/api/trade",
            "payload": {"side": "shadow_buy", "symbol": trade_symbol, "qty": tiny_shadow_qty},
            "expected_result": "HTTP 200；dry_run=true；只寫 paper/shadow ledger，不送 OKX live buy/add。",
            "dry_run_required": True,
            "live_order_submitted": False,
        },
        {
            "key": "venue_dry_run_lifecycle",
            "label": "Venue dry-run lifecycle proof",
            "can_enter": True,
            "command": proof.get("verify_next") or "python scripts/venue_dry_run_proof.py",
            "expected_result": "補 preview / ack / cancel / fill / reconciliation 證據鏈；live_exposure_allowed=false。",
            "live_order_submitted": False,
        },
        {
            "key": "risk_reduction",
            "label": "減風險 / 取消掛單路徑",
            "can_enter": True,
            "endpoint": "/api/trade",
            "payload_examples": [
                {"side": "wait", "symbol": trade_symbol, "qty": 0},
                {"side": "reduce", "symbol": trade_symbol, "qty": tiny_shadow_qty},
            ],
            "expected_result": "只降低或不增加曝險；是否可送出由場館/account state 再檢查。",
            "live_order_submitted": "risk_reduction_only_when_account_state_allows",
        },
        {
            "key": "bounded_live_canary",
            "label": "Bounded live-canary",
            "can_enter": bool(canary_ready),
            "required_gates": [
                "model_gate",
                "current_lane_actionability_gate",
                "current_live_support_gate",
                "circuit_breaker_gate",
                "venue_gate",
                "live_canary_policy_gate",
            ],
            "expected_result": "只有全部 gate passed 且 symbol cap 內，才可進第一層最小 canary；不是 full deploy。",
        },
    ]

    milestones = [
        {
            "key": "M1_runtime_truth",
            "label": "M1 現場 truth / no-order safety",
            "status": "passed",
            "next_lane_if_blocked": "wait_hold_no_order",
        },
        {
            "key": "M2_support_and_breaker",
            "label": "M2 當前 lane actionability + 熔斷解除",
            "status": "passed" if support_passed and release_passed else "blocked",
            "support_passed": support_passed,
            "current_lane_gate_key": "current_lane_actionability_gate",
            "strict_exact_support_gate_key": "current_live_support_gate",
            "release_passed": release_passed,
            "next_lane_if_blocked": "paper_shadow_buy" if shadow_ready else "wait_hold_no_order",
        },
        {
            "key": "M3_model_shadow_to_decision",
            "label": "M3 模型 shadow → decision",
            "status": "passed" if model_gate_passed else ("safe_lane_active" if shadow_ready else "blocked"),
            "model_gate_passed": model_gate_passed,
            "shadow_ready": shadow_ready,
            "next_lane_if_blocked": "paper_shadow_buy" if shadow_ready else "wait_hold_no_order",
        },
        {
            "key": "M4_venue_lifecycle_proof",
            "label": "M4 場館 lifecycle proof",
            "status": "passed" if venue_passed else "safe_lane_active",
            "venue_passed": venue_passed,
            "next_lane_if_blocked": "venue_dry_run_lifecycle",
        },
        {
            "key": "M5_bounded_canary_or_safe_lane",
            "label": "M5 canary / safe practical lane",
            "status": "passed" if canary_ready else "safe_lane_active",
            "live_canary_policy_passed": live_canary_policy_passed,
            "active_lane": active_lane,
        },
    ]

    return {
        "status": progression_status,
        "current_milestone": "M5",
        "active_lane": active_lane,
        "active_lane_label": active_label,
        "blocked_live_gate_key": blocked_key or None,
        "blocked_live_gate_label": blocked_label,
        "auto_adjustment_applied": not canary_ready,
        "auto_adjustment_reason": (
            "live buy/add gate 未全過，所以自動轉入可執行的 paper/shadow / dry-run / no-order lane；不是停在 blocked recap。"
            if not canary_ready
            else "所有 hard gate 已通過，只能進 bounded canary，不是 full deploy。"
        ),
        "preferred_entrypoint": preferred_entrypoint,
        "fallback_entrypoint": {
            "endpoint": "/api/trade",
            "method": "POST",
            "payload": {"side": "wait", "symbol": trade_symbol, "qty": 0},
            "expected_result": "HTTP 200；no_order_submitted=true；永遠不送 live order。",
            "live_order_submitted": False,
        },
        "safe_entry_lanes": safe_entry_lanes,
        "milestones": milestones,
        "operator_message": (
            f"MILESTONE 不再只卡死在 {blocked_label}：目前自動進入 {active_label}。"
            if not canary_ready
            else "MILESTONE 已到 bounded canary；仍按 cap 與 adapter guardrail 執行。"
        ),
    }


def attach_live_runner_shadow_gate_to_readiness(
    overview: Dict[str, Any],
    live_runner_overview: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Attach standalone runner 24h evidence as a hard canary-readiness gate.

    This mutates a copy of the overview.  The gate is evidence-only: it can
    downgrade canary readiness, but it never enables order submission by itself.
    """

    result = dict(overview or {})
    readiness = dict(_as_dict(result.get("execution_readiness")))
    if not readiness:
        return result

    runner = _as_dict(live_runner_overview)
    summary = _as_dict(runner.get("summary"))
    gate = _as_dict(runner.get("shadow_evidence_gate"))
    raw_status = str(gate.get("status") or runner.get("status") or "needs_live_runner_shadow_run")
    candidate_decisions = _to_int(gate.get("candidate_decisions")) or _to_int(summary.get("candidate_decisions")) or 0
    pending_outcomes = _to_int(gate.get("pending_outcomes")) or 0
    resolved_outcomes = _to_int(gate.get("resolved_outcomes")) or 0
    awaiting_label_replay = _to_int(gate.get("awaiting_label_replay")) or 0
    jsonl_backed = bool(summary.get("jsonl_backed"))
    live_order_submitted = bool(summary.get("live_order_submitted") or gate.get("live_order_submitted"))
    passed = bool(
        raw_status == "runner_24h_resolved_evidence_ready"
        and resolved_outcomes > 0
        and jsonl_backed
        and not live_order_submitted
    )
    pending = raw_status == "runner_24h_pending_observation" or pending_outcomes > 0
    if live_order_submitted:
        gate_status = "blocked"
        gate_summary = "live runner evidence 出現 live_order_submitted=true；必須先停止並稽核。"
        next_action = "立即停止 standalone runner，檢查 DB/JSONL 與 ExecutionService guardrail。"
    elif passed:
        gate_status = "passed"
        gate_summary = f"live runner 24h shadow evidence resolved {resolved_outcomes} 筆，JSONL 對齊。"
        next_action = "保留 fail-closed；只有其他 hard gates 也通過後才可進 bounded live-canary review。"
    elif pending:
        gate_status = "pending"
        gate_summary = f"live runner 已產生 {candidate_decisions} 筆 shadow candidate，等待 24h window / label 對齊。"
        next_action = "保持 runner --dry-run --no-submit --shadow-candidate 定時執行，24h 後 reconcile labels。"
    elif awaiting_label_replay > 0:
        gate_status = "blocked"
        gate_summary = f"live runner 有 {awaiting_label_replay} 筆 candidate 已到期但缺 1440m label。"
        next_action = "補跑 labels/backfill，再重新讀取 /api/execution/overview。"
    else:
        gate_status = "blocked"
        gate_summary = "live runner 尚未累積可用的 24h shadow candidate evidence。"
        next_action = "啟動 standalone runner：bin/poly-trader-live --config config.yaml --dry-run --no-submit --shadow-candidate。"

    readiness_gate = {
        "key": "live_runner_24h_shadow_gate",
        "label": "Standalone runner 24h shadow gate",
        "status": gate_status,
        "raw_status": raw_status,
        "passed": passed,
        "current": resolved_outcomes,
        "required": 1,
        "gap": 0 if passed else 1,
        "candidate_decisions": candidate_decisions,
        "pending_outcomes": pending_outcomes,
        "resolved_outcomes": resolved_outcomes,
        "awaiting_label_replay": awaiting_label_replay,
        "jsonl_backed": jsonl_backed,
        "next_reconcile_at": gate.get("next_reconcile_at"),
        "pending_hours_remaining_min": gate.get("pending_hours_remaining_min"),
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
        "live_order_submitted": live_order_submitted,
        "summary": gate_summary,
        "next_action": next_action,
        "operator_message": gate.get("operator_message") or gate_summary,
    }

    gates = [dict(item) for item in _as_list(readiness.get("gates")) if isinstance(item, dict)]
    gates = [item for item in gates if item.get("key") != "live_runner_24h_shadow_gate"]
    insert_at = next((idx for idx, item in enumerate(gates) if item.get("key") == "live_canary_policy_gate"), len(gates))
    gates.insert(insert_at, readiness_gate)
    readiness["gates"] = gates
    readiness["live_runner_24h_shadow_gate"] = readiness_gate
    readiness["order_submission_enabled"] = False
    readiness["risk_on_order_enabled"] = False

    previous_canary_ready = bool(readiness.get("canary_ready"))
    canary_ready = bool(previous_canary_ready and passed)
    readiness["canary_ready"] = canary_ready
    if not canary_ready:
        if previous_canary_ready or not readiness.get("blocking_gate_key"):
            readiness["blocking_gate_key"] = "live_runner_24h_shadow_gate"
            readiness["blocking_gate_label"] = "Standalone runner 24h shadow gate"
        if readiness.get("status") == "canary_ready":
            readiness["status"] = "shadow_reduce_only"
            readiness["stage_label"] = "Shadow / Reduce-only"
        if previous_canary_ready and not passed:
            readiness["operator_message"] = "live-canary 仍被 standalone runner 24h shadow evidence gate 擋住：可持續演練與記錄，不可買入 / 加倉。"
    else:
        readiness["status"] = "canary_ready"
        readiness["stage_label"] = "Canary-ready"

    release_condition = str(readiness.get("next_release_condition") or "")
    runner_condition = "standalone runner 24h shadow evidence resolved ≥ 1 且 JSONL/DB 對齊"
    if runner_condition not in release_condition:
        readiness["next_release_condition"] = f"{release_condition}；{runner_condition}" if release_condition else runner_condition

    what_can_do = list(_as_list(readiness.get("what_can_do_now")))
    runner_action = "讓 standalone live runner 以 --dry-run --no-submit --shadow-candidate 定時產生 shadow candidate，累積 24h resolved evidence"
    if runner_action not in what_can_do:
        what_can_do.append(runner_action)
    readiness["what_can_do_now"] = what_can_do

    milestone = dict(_as_dict(readiness.get("milestone_progression")))
    if milestone:
        milestones = [dict(item) for item in _as_list(milestone.get("milestones")) if isinstance(item, dict)]
        milestones = [item for item in milestones if item.get("key") != "M4_5_live_runner_24h_shadow_evidence"]
        runner_milestone = {
            "key": "M4_5_live_runner_24h_shadow_evidence",
            "label": "M4.5 standalone runner 24h shadow evidence",
            "status": "passed" if passed else ("pending" if pending else "blocked"),
            "raw_status": raw_status,
            "candidate_decisions": candidate_decisions,
            "pending_outcomes": pending_outcomes,
            "resolved_outcomes": resolved_outcomes,
            "jsonl_backed": jsonl_backed,
            "next_lane_if_blocked": "standalone_live_runner_shadow_candidate",
        }
        insert_at = next((idx for idx, item in enumerate(milestones) if item.get("key") == "M5_bounded_canary_or_safe_lane"), len(milestones))
        milestones.insert(insert_at, runner_milestone)
        milestone["milestones"] = milestones
        milestone["live_runner_24h_shadow_gate"] = readiness_gate
        if not canary_ready and (previous_canary_ready or readiness.get("blocking_gate_key") == "live_runner_24h_shadow_gate"):
            trade_symbol = _api_trade_symbol(result.get("symbol") or "BTCUSDT")
            milestone["status"] = "safe_lane_active" if not live_order_submitted else "blocked"
            milestone["active_lane"] = "standalone_live_runner_shadow_candidate"
            milestone["active_lane_label"] = "M4.5 standalone runner shadow evidence lane"
            milestone["preferred_entrypoint"] = {
                "command": "bin/poly-trader-live --config config.yaml --dry-run --no-submit --shadow-candidate",
                "expected_result": f"定時為 {trade_symbol} 寫入 live_runner_decisions / JSONL shadow candidate；live_order_submitted=false。",
                "live_order_submitted": False,
            }
            milestone["operator_message"] = "Roadmap 已轉入 M4.5：先累積 standalone runner 24h resolved evidence，再回到 bounded canary。"
        readiness["milestone_progression"] = milestone

    result["execution_readiness"] = readiness
    answers = dict(_as_dict(result.get("canary_gap_answers")))
    if answers:
        answers["canary_ready"] = readiness.get("canary_ready")
        answers["live_runner_24h_shadow_gate"] = readiness_gate
        answers["milestone_progression"] = readiness.get("milestone_progression")
        first_plan = dict(_as_dict(answers.get("first_canary_plan_if_all_gates_pass")))
        if first_plan:
            first_plan["required_shadow_evidence_gate"] = "standalone runner 24h shadow evidence resolved ≥ 1 且 JSONL/DB 對齊"
            stop_conditions = list(_as_list(first_plan.get("stop_conditions")))
            if "24h runner shadow evidence missing/regressed" not in stop_conditions:
                stop_conditions.append("24h runner shadow evidence missing/regressed")
            first_plan["stop_conditions"] = stop_conditions
            answers["first_canary_plan_if_all_gates_pass"] = first_plan
        result["canary_gap_answers"] = answers
    result["user_action_state"] = _build_user_action_state(result, result.get("timestamp"))
    return result



def _load_high_conviction_topk(status_payload: Dict[str, Any]) -> Dict[str, Any]:
    execution_surface_contract = _as_dict(status_payload.get("execution_surface_contract"))
    execution = _as_dict(status_payload.get("execution"))
    return _as_dict(
        execution_surface_contract.get("high_conviction_topk")
        or execution.get("high_conviction_topk")
        or status_payload.get("high_conviction_topk")
    )



def _load_circuit_breaker_audit(status_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return the current circuit-breaker audit without requiring it to be the active blocker.

    `/api/status.execution.live_runtime_truth.deployment_blocker_details` is shaped by the
    active blocker.  When exact support is the blocker, breaker release math is not embedded
    there, but the execution workspace still needs to show the breaker gate as clear instead
    of falling back to an unknown/blocked state.
    """

    execution_surface_contract = _as_dict(status_payload.get("execution_surface_contract"))
    execution = _as_dict(status_payload.get("execution"))
    embedded = _as_dict(
        status_payload.get("circuit_breaker_audit")
        or execution.get("circuit_breaker_audit")
        or execution_surface_contract.get("circuit_breaker_audit")
    )
    if embedded:
        return embedded

    audit_path = Path(__file__).resolve().parents[1] / "data" / "circuit_breaker_audit.json"
    try:
        with audit_path.open("r", encoding="utf-8") as fh:
            return _as_dict(json.load(fh))
    except (OSError, json.JSONDecodeError):
        return {}


def _load_customer_safe_alternative_proof(status_payload: Dict[str, Any]) -> Dict[str, Any]:
    execution_surface_contract = _as_dict(status_payload.get("execution_surface_contract"))
    execution = _as_dict(status_payload.get("execution"))
    embedded = _as_dict(
        status_payload.get("customer_safe_alternative_proof")
        or execution.get("customer_safe_alternative_proof")
        or execution_surface_contract.get("customer_safe_alternative_proof")
    )
    if embedded:
        return embedded

    proof_path = Path(__file__).resolve().parents[1] / "data" / "customer_safe_alternative_proof.json"
    try:
        with proof_path.open("r", encoding="utf-8") as fh:
            return _as_dict(json.load(fh))
    except (OSError, json.JSONDecodeError):
        return {}



def _build_high_conviction_shadow_contract(status_payload: Dict[str, Any]) -> Dict[str, Any]:
    topk = _load_high_conviction_topk(status_payload)
    if not topk:
        return {"shadow_available": False}

    risk_qualified_count = _to_int(topk.get("risk_qualified_count")) or 0
    runtime_blocked_candidate_count = _to_int(topk.get("runtime_blocked_candidate_count")) or 0
    deployable_count = _to_int(topk.get("deployable_count")) or 0
    readiness_status = str(topk.get("deployment_readiness_status") or "").strip()
    support_context = _as_dict(topk.get("support_context"))
    nearest_rows = [row for row in _as_list(topk.get("nearest_deployable_rows")) if isinstance(row, dict)]
    nearest = nearest_rows[0] if nearest_rows else {}

    shadow_available = bool(
        risk_qualified_count > 0
        and runtime_blocked_candidate_count > 0
        and deployable_count == 0
        and readiness_status in {"paper_shadow_only", "stale_artifact_shadow_only", "freshness_unknown_shadow_only"}
    )
    support_rows = _to_int(support_context.get("current_live_structure_bucket_rows"))
    minimum_rows = _to_int(support_context.get("minimum_support_rows"))
    gap_rows = _first_int(
        support_context.get("support_rows_needed"),
        support_context.get("current_live_structure_bucket_gap_to_minimum"),
    )
    stalled_runs = _to_int(support_context.get("stagnant_run_count"))
    start_reason = (
        f"高信心 OOS 已通過離線 / 風控門檻 {risk_qualified_count} 筆，但可部署仍為 0；"
        f"目前精準支持 {support_rows if support_rows is not None else '—'} / {minimum_rows if minimum_rows is not None else '—'}"
        f"（缺 {gap_rows if gap_rows is not None else '—'}），可先啟動影子觀察運行，只記錄決策與共享帳戶預覽，不送單、不加倉。"
    )
    next_action = (
        "啟動高信念精選的影子觀察運行：只納入即時監控、事件紀錄與同商品共享預覽，"
        "等精準樣本與場館證據鏈通過後再升級小流量。"
    )
    support_summary_parts = []
    if support_rows is not None and minimum_rows is not None:
        support_summary_parts.append(f"支持 {support_rows}/{minimum_rows}")
    if gap_rows is not None:
        support_summary_parts.append(f"缺 {gap_rows}")
    if stalled_runs is not None and support_context.get("stalled_support_accumulation") is True:
        support_summary_parts.append(f"連續停滯 {stalled_runs} 輪")

    return {
        "shadow_available": shadow_available,
        "shadow_only": True,
        "risk_on_order_enabled": False,
        "shadow_mode": "paper_shadow",
        "readiness_status": readiness_status,
        "risk_qualified_count": risk_qualified_count,
        "runtime_blocked_candidate_count": runtime_blocked_candidate_count,
        "deployable_count": deployable_count,
        "operator_message": topk.get("operator_message") or start_reason,
        "start_reason": start_reason,
        "next_operator_action": next_action,
        "support_summary": " · ".join(support_summary_parts) if support_summary_parts else None,
        "support_context": support_context,
        "nearest_candidate": {
            "model_name": nearest.get("model_name"),
            "threshold_name": nearest.get("threshold_name"),
            "deployment_candidate_tier": nearest.get("deployment_candidate_tier"),
            "blocked_only_by_live_guardrails": nearest.get("blocked_only_by_live_guardrails"),
            "deployable": nearest.get("deployable"),
            "signal": nearest.get("signal"),
            "allowed_layers": nearest.get("allowed_layers"),
        } if nearest else None,
    }



def _record_text(record: Any, keys: Iterable[str]) -> Optional[str]:
    if not isinstance(record, dict):
        return None
    for key in keys:
        value = record.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None



def _symbol_key(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text.replace("/", "").replace("-", "").replace("_", "").upper()



def _symbol_keys(*values: Optional[str]) -> List[str]:
    ordered: List[str] = []
    seen = set()
    for value in values:
        normalized = _symbol_key(value)
        if normalized and normalized not in seen:
            ordered.append(normalized)
            seen.add(normalized)
    return ordered



def _filter_records_for_symbol(records: Iterable[Any], symbol_keys: List[str]) -> List[Dict[str, Any]]:
    symbol_key_set = set(symbol_keys)
    matched: List[Dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        record_symbol = _record_text(record, ["symbol", "instId", "market", "pair"])
        record_key = _symbol_key(record_symbol)
        if symbol_key_set and record_key and record_key in symbol_key_set:
            matched.append(record)
    return matched



def _planned_budget(
    *,
    active: bool,
    total_balance: Optional[float],
    deployable_capital: Optional[float],
    active_count: int,
) -> Dict[str, Optional[float]]:
    if not active or active_count <= 0 or deployable_capital is None:
        return {
            "planned_budget_amount": 0.0 if active_count > 0 else None,
            "planned_budget_ratio_of_balance": 0.0 if total_balance not in (None, 0) else None,
        }
    amount = float(deployable_capital) / float(active_count)
    ratio = None
    if total_balance not in (None, 0):
        ratio = float(amount) / float(total_balance)
    return {
        "planned_budget_amount": amount,
        "planned_budget_ratio_of_balance": ratio,
    }



def _first_text(*values: Any) -> Optional[str]:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None



def _first_int(*values: Any) -> Optional[int]:
    for value in values:
        number = _to_int(value)
        if number is not None:
            return number
    return None



def _first_float(*values: Any) -> Optional[float]:
    for value in values:
        number = _to_float(value)
        if number is not None:
            return number
    return None



def _nearest_high_conviction_candidate(topk: Dict[str, Any]) -> Dict[str, Any]:
    nearest_rows = [row for row in _as_list(topk.get("nearest_deployable_rows")) if isinstance(row, dict)]
    if nearest_rows:
        return nearest_rows[0]
    rows = [row for row in _as_list(topk.get("rows")) if isinstance(row, dict)]
    return rows[0] if rows else {}



def _venue_record_for_payload(status_payload: Dict[str, Any]) -> Dict[str, Any]:
    execution = _as_dict(status_payload.get("execution"))
    metadata_smoke = _as_dict(status_payload.get("execution_metadata_smoke"))
    venues = [item for item in _as_list(metadata_smoke.get("venues")) if isinstance(item, dict)]
    target_venue = str(execution.get("venue") or "").strip().lower()
    if target_venue:
        for venue in venues:
            if str(venue.get("venue") or "").strip().lower() == target_venue:
                return venue
    return venues[0] if venues else {}


_SECRETISH_FIELD_MARKERS = (
    "api_key",
    "apikey",
    "api_secret",
    "secret",
    "password",
    "passphrase",
    "private_key",
    "token",
)


def _secret_safe_payload(value: Any) -> Any:
    if isinstance(value, dict):
        safe: Dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            normalized_key = key_text.lower().replace("-", "_")
            if any(marker in normalized_key for marker in _SECRETISH_FIELD_MARKERS):
                continue
            safe[key] = _secret_safe_payload(item)
        return safe
    if isinstance(value, list):
        return [_secret_safe_payload(item) for item in value]
    if isinstance(value, str):
        normalized_value = value.lower().replace("-", "_")
        if any(marker in normalized_value for marker in _SECRETISH_FIELD_MARKERS):
            return "[redacted]"
    return value


def _venue_dry_run_proof_for_payload(status_payload: Dict[str, Any]) -> Dict[str, Any]:
    execution = _as_dict(status_payload.get("execution"))
    execution_surface_contract = _as_dict(status_payload.get("execution_surface_contract"))
    return _as_dict(
        status_payload.get("venue_dry_run_proof")
        or execution.get("venue_dry_run_proof")
        or execution_surface_contract.get("venue_dry_run_proof")
    )


def _selected_venue_from_dry_run_proof(proof_payload: Dict[str, Any], target_venue: Any) -> Dict[str, Any]:
    venues = [item for item in _as_list(proof_payload.get("venues")) if isinstance(item, dict)]
    target = str(target_venue or "").strip().lower()
    if target:
        for venue in venues:
            if str(venue.get("venue") or "").strip().lower() == target:
                return venue
    return venues[0] if venues else {}


def _first_text_list(*values: Any) -> List[str]:
    for value in values:
        items = [str(item).strip() for item in _as_list(value) if str(item).strip()]
        if items:
            return items
    return []


def _normalize_venue_dry_run_artifact(
    proof_payload: Dict[str, Any],
    *,
    symbol: str,
    execution: Dict[str, Any],
    fallback_venue_record: Dict[str, Any],
    execution_reconciliation: Dict[str, Any],
    live_ready_blockers: List[str],
) -> Dict[str, Any]:
    proof = _as_dict(_secret_safe_payload(proof_payload))
    if not proof:
        return {}

    selected_venue = _selected_venue_from_dry_run_proof(proof, execution.get("venue"))
    result = dict(proof)
    result["artifact"] = _first_text(result.get("artifact"), "venue_dry_run_proof") or "venue_dry_run_proof"
    result["status"] = _first_text(result.get("status"), "blocked_missing_runtime_backed_proof") or "blocked_missing_runtime_backed_proof"
    result["symbol"] = _first_text(result.get("symbol"), symbol) or symbol
    result["venue"] = _first_text(
        result.get("venue"),
        selected_venue.get("venue"),
        fallback_venue_record.get("venue"),
        execution.get("venue"),
        "unknown",
    ) or "unknown"
    result["secrets_redacted"] = True
    if "credential_present" not in result:
        result["credential_present"] = bool(
            result.get("credentials_configured_any")
            or selected_venue.get("credential_present")
            or selected_venue.get("credentials_configured")
            or fallback_venue_record.get("credentials_configured")
        )
    result["live_exposure_allowed"] = bool(result.get("live_exposure_allowed") is True)
    result["order_submission_enabled"] = bool(result.get("order_submission_enabled") is True)
    result["risk_on_order_enabled"] = bool(result.get("risk_on_order_enabled") is True)
    result["dry_run_only"] = result.get("dry_run_only") is not False
    result["runtime_ready"] = bool(result.get("runtime_ready") is True)
    blockers = _first_text_list(
        result.get("runtime_ready_blockers"),
        result.get("blockers"),
        selected_venue.get("blockers"),
        fallback_venue_record.get("blockers"),
        live_ready_blockers,
    )
    result["blockers"] = blockers
    if "runtime_ready_blockers" not in result:
        result["runtime_ready_blockers"] = blockers
    result["proof_state"] = _first_text(
        result.get("proof_state"),
        selected_venue.get("proof_state"),
        selected_venue.get("readiness_state"),
        fallback_venue_record.get("proof_state"),
        "missing_runtime_backed_order_lifecycle",
    )
    result["operator_next_action"] = _first_text(
        result.get("operator_next_action"),
        selected_venue.get("operator_next_action"),
        fallback_venue_record.get("operator_next_action"),
        "先跑 dry-run preview，再補 ack / cancel / fill / reconciliation proof。",
    )
    result["verify_next"] = _first_text(
        result.get("verify_next"),
        selected_venue.get("verify_next"),
        fallback_venue_record.get("verify_next"),
        "python scripts/venue_dry_run_proof.py",
    )
    for key in (
        "order_preview",
        "ack_simulation",
        "cancel_simulation",
        "fill_simulation",
        "reconciliation_check",
    ):
        if not isinstance(result.get(key), dict) and isinstance(selected_venue.get(key), dict):
            result[key] = selected_venue[key]
    if not isinstance(result.get("reconciliation_check"), dict):
        result["reconciliation_check"] = {
            "status": _first_text(execution_reconciliation.get("status"), "limited_evidence_no_runtime_order"),
            "runtime_backed": False,
            "summary": _first_text(execution_reconciliation.get("summary"), "尚未有 runtime-backed order / fill lifecycle 可對帳。"),
        }
    return result


def _customer_safe_false_when_missing(value: Any) -> bool:
    return bool(value is True)


def _customer_safe_int(*values: Any) -> Optional[int]:
    return _first_int(*values)


def _customer_safe_text(*values: Any) -> Optional[str]:
    return _first_text(*values)


def _project_mapping(source: Dict[str, Any], keys: Iterable[str]) -> Dict[str, Any]:
    return {key: source.get(key) for key in keys if key in source}


def _compact_customer_safe_alternative_proof(proof_payload: Dict[str, Any]) -> Dict[str, Any]:
    proof = _as_dict(proof_payload)
    if not proof:
        fallback = {
            "artifact": "customer_safe_alternative_proof",
            "status": "missing_artifact_fail_closed",
            "generated_at": None,
            "canary_ready": False,
            "live_exposure_allowed": False,
            "order_submission_enabled": False,
            "risk_on_order_enabled": False,
            "alternative_solution_required": True,
            "alternative_solution_option_count": 0,
            "alternative_solution_options": 0,
            "selected_alternative_solution": None,
            "selected_alternative": None,
            "selected_next_customer_artifact": "data/customer_safe_alternative_proof.json",
            "selected_next_artifact": "data/customer_safe_alternative_proof.json",
            "blocked_live_lane_count": 0,
            "next_customer_action_count": 0,
            "alternative_solutions": [],
            "next_customer_actions": [],
            "blocked_live_lanes": [],
            "operator_summary": "customer-safe alternative proof artifact missing; live buy/add and order submission remain fail-closed.",
        }
        fallback["summary"] = _project_mapping(
            fallback,
            (
                "canary_ready",
                "live_exposure_allowed",
                "order_submission_enabled",
                "risk_on_order_enabled",
                "alternative_solution_required",
                "alternative_solution_option_count",
                "alternative_solution_options",
                "selected_alternative_solution",
                "selected_alternative",
                "selected_next_customer_artifact",
                "selected_next_artifact",
                "blocked_live_lane_count",
                "next_customer_action_count",
                "operator_summary",
            ),
        )
        return fallback

    source_summary = _as_dict(proof.get("summary"))
    source_support = _as_dict(proof.get("current_live_support"))
    source_topk = _as_dict(proof.get("topk_shadow_candidate_context"))
    source_venue = _as_dict(proof.get("venue_runtime_proof"))
    alternative_solutions = [row for row in _as_list(proof.get("alternative_solutions")) if isinstance(row, dict)]
    next_customer_actions = [row for row in _as_list(proof.get("next_customer_actions")) if isinstance(row, dict)]
    blocked_live_lanes = [row for row in _as_list(proof.get("blocked_live_lanes")) if isinstance(row, dict)]
    portfolio = _as_dict(proof.get("alternative_solution_portfolio"))

    option_count = _customer_safe_int(
        proof.get("alternative_solution_options"),
        proof.get("alternative_solution_option_count"),
        source_summary.get("alternative_solution_options"),
        source_summary.get("alternative_solution_option_count"),
        portfolio.get("option_count"),
    )
    if option_count is None:
        option_count = len(alternative_solutions)

    selected_alternative = _customer_safe_text(
        proof.get("selected_alternative_solution"),
        proof.get("selected_alternative"),
        source_summary.get("selected_alternative_solution"),
        source_summary.get("selected_alternative"),
        portfolio.get("selected_option"),
    )
    selected_next_artifact = _customer_safe_text(
        proof.get("selected_next_customer_artifact"),
        proof.get("selected_next_artifact"),
        source_summary.get("selected_next_customer_artifact"),
        source_summary.get("selected_next_artifact"),
        portfolio.get("selected_next_artifact"),
    )

    result = {
        "artifact": _customer_safe_text(proof.get("artifact"), "customer_safe_alternative_proof") or "customer_safe_alternative_proof",
        "generated_at": proof.get("generated_at"),
        "canary_ready": _customer_safe_false_when_missing(proof.get("canary_ready")),
        "live_exposure_allowed": _customer_safe_false_when_missing(proof.get("live_exposure_allowed")),
        "order_submission_enabled": _customer_safe_false_when_missing(proof.get("order_submission_enabled")),
        "risk_on_order_enabled": _customer_safe_false_when_missing(proof.get("risk_on_order_enabled")),
        "support_rows": _customer_safe_int(
            proof.get("support_rows"),
            source_summary.get("support_rows"),
            source_support.get("current_rows"),
        ),
        "minimum_support_rows": _customer_safe_int(
            proof.get("minimum_support_rows"),
            source_summary.get("minimum_support_rows"),
            source_support.get("minimum_support_rows"),
        ),
        "support_gap": _customer_safe_int(
            proof.get("support_gap"),
            source_summary.get("support_gap"),
            source_support.get("gap_to_minimum"),
        ),
        "blocking_gate": _customer_safe_text(proof.get("blocking_gate"), source_summary.get("blocking_gate")),
        "primary_blocking_gate": _customer_safe_text(
            proof.get("primary_blocking_gate"),
            source_summary.get("primary_blocking_gate"),
        ),
        "blocking_gates": [
            str(item)
            for item in _as_list(proof.get("blocking_gates") or source_summary.get("blocking_gates"))
            if str(item).strip()
        ],
        "breaker_release_ready": _customer_safe_false_when_missing(
            proof.get("breaker_release_ready", source_summary.get("breaker_release_ready"))
        ),
        "current_recent_window_wins": _customer_safe_int(
            proof.get("current_recent_window_wins"),
            source_summary.get("current_recent_window_wins"),
        ),
        "required_recent_window_wins": _customer_safe_int(
            proof.get("required_recent_window_wins"),
            source_summary.get("required_recent_window_wins"),
        ),
        "additional_recent_window_wins_needed": _customer_safe_int(
            proof.get("additional_recent_window_wins_needed"),
            source_summary.get("additional_recent_window_wins_needed"),
        ),
        "topk_deployable_rows": _customer_safe_int(
            proof.get("topk_deployable_rows"),
            source_summary.get("topk_deployable_rows"),
            source_topk.get("deployable_rows"),
        ),
        "topk_risk_qualified_rows": _customer_safe_int(
            proof.get("topk_risk_qualified_rows"),
            source_summary.get("topk_risk_qualified_rows"),
            source_topk.get("risk_qualified_rows"),
        ),
        "topk_runtime_blocked_candidate_rows": _customer_safe_int(
            proof.get("topk_runtime_blocked_candidate_rows"),
            source_summary.get("topk_runtime_blocked_candidate_rows"),
            source_topk.get("runtime_blocked_candidate_rows"),
        ),
        "topk_support_context_status": _customer_safe_text(
            proof.get("topk_support_context_status"),
            source_summary.get("topk_support_context_status"),
            source_topk.get("support_context_status"),
        ),
        "topk_support_context_freshness_status": _customer_safe_text(
            proof.get("topk_support_context_freshness_status"),
            source_summary.get("topk_support_context_freshness_status"),
            source_topk.get("support_context_freshness_status"),
        ),
        "topk_support_context_deployment_blocking": _customer_safe_false_when_missing(
            proof.get(
                "topk_support_context_deployment_blocking",
                source_summary.get(
                    "topk_support_context_deployment_blocking",
                    source_topk.get("support_context_deployment_blocking"),
                ),
            )
        ),
        "topk_live_truth_overlay_blocker": _customer_safe_text(
            proof.get("topk_live_truth_overlay_blocker"),
            source_summary.get("topk_live_truth_overlay_blocker"),
            source_topk.get("live_truth_overlay_blocker"),
        ),
        "venue_runtime_ready": _customer_safe_false_when_missing(
            proof.get("venue_runtime_ready", source_summary.get("venue_runtime_ready", source_venue.get("runtime_ready")))
        ),
        "venue_status": _customer_safe_text(
            proof.get("venue_status"),
            source_summary.get("venue_status"),
            source_venue.get("status"),
        ),
        "blocked_live_lane_count": _customer_safe_int(
            proof.get("blocked_live_lane_count"),
            source_summary.get("blocked_live_lane_count"),
        ),
        "alternative_solution_required": _customer_safe_false_when_missing(
            proof.get("alternative_solution_required", source_summary.get("alternative_solution_required"))
        ),
        "alternative_solution_option_count": option_count,
        "alternative_solution_options": option_count,
        "selected_alternative_solution": selected_alternative,
        "selected_alternative": selected_alternative,
        "selected_next_customer_artifact": selected_next_artifact,
        "selected_next_artifact": selected_next_artifact,
        "next_customer_action_count": _customer_safe_int(
            proof.get("next_customer_action_count"),
            source_summary.get("next_customer_action_count"),
        ),
        "operator_summary": _customer_safe_text(source_summary.get("operator_summary"), proof.get("operator_summary")),
    }
    if result["blocked_live_lane_count"] is None:
        result["blocked_live_lane_count"] = len(blocked_live_lanes)
    if result["next_customer_action_count"] is None:
        result["next_customer_action_count"] = len(next_customer_actions)

    result["alternative_solution_portfolio"] = _project_mapping(
        portfolio,
        (
            "pm_challenge_answered",
            "option_count",
            "selected_option",
            "selected_next_artifact",
            "time_to_evidence_bucket",
            "missing_capability_class",
        ),
    )
    result["alternative_solutions"] = [
        _project_mapping(
            row,
            (
                "id",
                "role",
                "next_artifact",
                "deployable",
                "live_exposure_allowed",
                "order_submission_enabled",
                "risk_on_order_enabled",
                "reference_window",
                "reference_rows",
            ),
        )
        for row in alternative_solutions
    ]
    result["next_customer_actions"] = [
        _project_mapping(
            row,
            (
                "id",
                "surface",
                "mode",
                "action",
                "expected_evidence",
                "verify_command",
                "breaker_release_ready",
                "current_recent_window_wins",
                "required_recent_window_wins",
                "support_rows",
                "minimum_support_rows",
                "support_gap",
                "topk_deployable_rows",
                "topk_support_context_status",
                "topk_support_context_freshness_status",
                "topk_support_context_deployment_blocking",
                "topk_live_truth_overlay_blocker",
                "venue_runtime_ready",
                "live_exposure_allowed",
                "order_submission_enabled",
                "risk_on_order_enabled",
            ),
        )
        for row in next_customer_actions
    ]
    compact_release_keys = (
        "primary_blocking_gate",
        "breaker_release_ready",
        "current_recent_window_wins",
        "required_recent_window_wins",
        "additional_recent_window_wins_needed",
        "support_rows",
        "minimum_support_rows",
        "support_gap",
        "support_route_verdict",
        "topk_deployable_rows",
        "topk_support_context_status",
        "topk_support_context_freshness_status",
        "topk_support_context_deployment_blocking",
        "topk_live_truth_overlay_blocker",
        "venue_runtime_ready",
        "venue_status",
    )
    result["blocked_live_lanes"] = [
        {
            **_project_mapping(
                row,
                (
                    "id",
                    "blocking_gate",
                    "blocked_actions",
                    "live_exposure_allowed",
                    "order_submission_enabled",
                    "risk_on_order_enabled",
                    "allowed_alternative",
                ),
            ),
            "release_condition": _project_mapping(_as_dict(row.get("release_condition")), compact_release_keys),
        }
        for row in blocked_live_lanes
    ]
    result["summary"] = _project_mapping(
        result,
        (
            "canary_ready",
            "live_exposure_allowed",
            "order_submission_enabled",
            "risk_on_order_enabled",
            "support_rows",
            "minimum_support_rows",
            "support_gap",
            "blocking_gate",
            "primary_blocking_gate",
            "blocking_gates",
            "breaker_release_ready",
            "current_recent_window_wins",
            "required_recent_window_wins",
            "additional_recent_window_wins_needed",
            "topk_deployable_rows",
            "topk_risk_qualified_rows",
            "topk_runtime_blocked_candidate_rows",
            "topk_support_context_status",
            "topk_support_context_freshness_status",
            "topk_support_context_deployment_blocking",
            "topk_live_truth_overlay_blocker",
            "venue_runtime_ready",
            "venue_status",
            "blocked_live_lane_count",
            "alternative_solution_required",
            "alternative_solution_option_count",
            "alternative_solution_options",
            "selected_alternative_solution",
            "selected_alternative",
            "selected_next_customer_artifact",
            "selected_next_artifact",
            "next_customer_action_count",
            "operator_summary",
        ),
    )
    return result



def build_execution_readiness_bundle(
    status_payload: Optional[Dict[str, Any]],
    *,
    range_chop_playbook: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build M5 operator-safe execution readiness, shadow ledger, and venue proof payloads.

    This is intentionally fail-closed: OOS/model quality can open only a shadow
    observation lane.  Buy/add exposure and live order submission stay disabled
    until exact support, breaker/release math, venue proof chain, and surface
    contract all pass.
    """

    payload = _as_dict(status_payload)
    execution_surface_contract = _as_dict(payload.get("execution_surface_contract"))
    execution = _as_dict(payload.get("execution"))
    live_runtime_truth = _as_dict(execution.get("live_runtime_truth") or execution_surface_contract.get("live_runtime_truth"))
    account = _as_dict(payload.get("account"))
    execution_reconciliation = _as_dict(payload.get("execution_reconciliation"))
    topk = _load_high_conviction_topk(payload)
    high_conviction_shadow = _build_high_conviction_shadow_contract(payload)
    range_chop = _as_dict(range_chop_playbook or execution.get("range_chop_playbook") or execution_surface_contract.get("range_chop_playbook") or payload.get("range_chop_playbook"))
    venue_record = _venue_record_for_payload(payload)
    venue_dry_run_artifact = _venue_dry_run_proof_for_payload(payload)
    venue_dry_run_artifact_venue = _selected_venue_from_dry_run_proof(venue_dry_run_artifact, execution.get("venue"))
    customer_safe_alternative_artifact = _load_customer_safe_alternative_proof(payload)

    support_progress = _as_dict(live_runtime_truth.get("support_progress"))
    topk_support_context = _as_dict(topk.get("support_context"))
    blocker_details = _as_dict(live_runtime_truth.get("deployment_blocker_details"))
    circuit_breaker_audit = _load_circuit_breaker_audit(payload)
    release_condition = _as_dict(blocker_details.get("release_condition"))
    if not release_condition:
        release_condition = _as_dict(circuit_breaker_audit.get("release_condition"))
    recent_window_details = _as_dict(blocker_details.get("recent_window"))
    if not recent_window_details:
        recent_window_details = _as_dict(circuit_breaker_audit.get("tail_pathology"))

    support_rows = _first_int(
        support_progress.get("current_rows"),
        live_runtime_truth.get("current_live_structure_bucket_rows"),
        topk_support_context.get("current_live_structure_bucket_rows"),
    )
    support_minimum = _first_int(
        support_progress.get("minimum_support_rows"),
        live_runtime_truth.get("minimum_support_rows"),
        topk_support_context.get("minimum_support_rows"),
    )
    support_gap = _first_int(
        support_progress.get("gap_to_minimum"),
        live_runtime_truth.get("current_live_structure_bucket_gap_to_minimum"),
        topk_support_context.get("support_rows_needed"),
        topk_support_context.get("current_live_structure_bucket_gap_to_minimum"),
    )
    if support_gap is None and support_rows is not None and support_minimum is not None:
        support_gap = max(int(support_minimum) - int(support_rows), 0)
    support_passed = bool(
        support_rows is not None
        and support_minimum is not None
        and int(support_rows) >= int(support_minimum)
        and str(live_runtime_truth.get("support_route_verdict") or "").strip() in {"exact_bucket_supported", "exact_live_bucket_supported"}
    )

    support_delta = _first_int(
        support_progress.get("delta_vs_previous"),
        support_progress.get("support_delta_vs_previous"),
        topk_support_context.get("support_delta_vs_previous"),
        topk_support_context.get("delta_vs_previous"),
    )
    support_previous_rows = _first_int(
        support_progress.get("previous_rows"),
        topk_support_context.get("support_previous_rows"),
    )
    stagnant_run_count = _first_int(
        support_progress.get("stagnant_run_count"),
        topk_support_context.get("support_progress_stagnant_run_count"),
        topk_support_context.get("stagnant_run_count"),
    ) or 0
    stalled_support = bool(
        support_progress.get("stalled_support_accumulation")
        or topk_support_context.get("support_progress_stalled_support_accumulation")
        or topk_support_context.get("stalled_support_accumulation")
        or (stagnant_run_count > 0 and (support_delta is None or int(support_delta) <= 0))
    )
    estimated_heartbeats_to_support = None
    estimated_hours_at_hourly_heartbeat = None
    estimated_days_at_hourly_heartbeat = None
    if support_gap is not None and int(support_gap) <= 0:
        time_to_evidence_status = "support_already_met"
        time_to_evidence_summary = "即時精準支持已達最低樣本；仍需檢查熔斷與場館證據鏈。"
        estimated_heartbeats_to_support = 0
        estimated_hours_at_hourly_heartbeat = 0
        estimated_days_at_hourly_heartbeat = 0.0
        alternative_solution_required = False
    elif support_gap is not None and support_delta is not None and int(support_delta) > 0:
        estimated_heartbeats_to_support = max((int(support_gap) + int(support_delta) - 1) // int(support_delta), 1)
        estimated_hours_at_hourly_heartbeat = estimated_heartbeats_to_support
        estimated_days_at_hourly_heartbeat = round(estimated_hours_at_hourly_heartbeat / 24.0, 2)
        time_to_evidence_status = "estimable_from_recent_delta"
        time_to_evidence_summary = (
            f"即時精準支持最近增加 {int(support_delta)} 筆（{support_previous_rows if support_previous_rows is not None else '—'}→"
            f"{support_rows if support_rows is not None else '—'}），以每輪同速估算還需 {estimated_heartbeats_to_support} 輪；"
            f"若工程心跳維持約每小時一次，約 {estimated_days_at_hourly_heartbeat} 天。"
        )
        alternative_solution_required = bool(estimated_days_at_hourly_heartbeat > 7.0)
    elif support_gap is not None:
        time_to_evidence_status = "indeterminate_stalled_support" if stalled_support else "indeterminate_no_positive_delta"
        time_to_evidence_summary = (
            f"即時精準支持仍缺 {int(support_gap)} 筆，但最近沒有正向增量；無法給出可靠完成時間，"
            "本輪必須啟動替代解法評審而不是只等待。"
        )
        alternative_solution_required = True
    else:
        time_to_evidence_status = "unknown_support_gap"
        time_to_evidence_summary = "即時精準支持缺口未知；先修復 support artifact，再評估完成時間與替代解法。"
        alternative_solution_required = True

    time_to_evidence = {
        "status": time_to_evidence_status,
        "summary": time_to_evidence_summary,
        "current_rows": support_rows,
        "minimum_support_rows": support_minimum,
        "gap_to_minimum": support_gap,
        "delta_vs_previous": support_delta,
        "previous_rows": support_previous_rows,
        "stagnant_run_count": stagnant_run_count,
        "stalled_support_accumulation": stalled_support,
        "estimated_heartbeats_to_support": estimated_heartbeats_to_support,
        "heartbeat_interval_assumption_hours": 1,
        "estimated_hours_at_hourly_heartbeat": estimated_hours_at_hourly_heartbeat,
        "estimated_days_at_hourly_heartbeat": estimated_days_at_hourly_heartbeat,
        "alternative_solution_required": alternative_solution_required,
        "operator_message": time_to_evidence_summary,
    }
    alternative_solution_review = {
        "status": "required" if alternative_solution_required else "watch_only",
        "trigger": "time_to_evidence_over_7_days_or_indeterminate" if alternative_solution_required else "support_eta_within_7_days_under_recent_delta",
        "primary_alternative": "paper_shadow_reduce_only_with_range_chop_playbook" if alternative_solution_required else "continue_exact_support_accumulation",
        "live_exposure_allowed": False,
        "order_submission_enabled": False,
        "allowed_today": [
            "用 /api/trade shadow_buy / paper_buy 進入 paper-shadow 實戰演練（dry-run only）",
            "啟動 paper-shadow 訊號帳本並追 24h pyramid outcome",
            "保留減碼 / 取消掛單 / 賣出風險降低路徑",
            "補 venue dry-run preview、ack、cancel、fill、reconciliation 證據鏈",
        ],
        "not_allowed": ["買入 / 加倉", "把寬範圍或舊語義支持包裝成部署閉環"],
        "next_review_trigger": "每輪 heartbeat 重新計算 support_delta；若 estimated_days_at_hourly_heartbeat > 7 或無正增量，PM/工程需重排替代路線。",
        "operator_message": "即時支持若無法在可預期時間內補齊，先交付影子觀察、減風險與場館證據鏈，不開買入 / 加倉。",
    }

    release_window = _first_int(release_condition.get("recent_window"), recent_window_details.get("window_size"), 50) or 50
    release_wins = _first_int(release_condition.get("current_recent_window_wins"), recent_window_details.get("wins"))
    release_required_wins = _first_int(release_condition.get("required_recent_window_wins"))
    release_gap = _first_int(release_condition.get("additional_recent_window_wins_needed"))
    release_ready = bool(release_condition.get("release_ready"))
    if release_required_wins is None and release_window:
        release_required_wins = 15 if int(release_window) == 50 else None
    if release_gap is None and release_wins is not None and release_required_wins is not None:
        release_gap = max(int(release_required_wins) - int(release_wins), 0)
    if release_ready is False and release_gap == 0 and release_wins is not None and release_required_wins is not None:
        release_ready = int(release_wins) >= int(release_required_wins)
    release_known = bool(release_condition or recent_window_details or release_wins is not None)
    release_passed = bool(release_ready or (release_known and release_gap == 0 and release_wins is not None))

    live_ready = bool(execution_surface_contract.get("live_ready"))
    risk_qualified_count = _to_int(topk.get("risk_qualified_count")) or _to_int(high_conviction_shadow.get("risk_qualified_count")) or 0
    runtime_blocked_candidate_count = _to_int(topk.get("runtime_blocked_candidate_count")) or _to_int(high_conviction_shadow.get("runtime_blocked_candidate_count")) or 0
    deployable_count = _to_int(topk.get("deployable_count")) or _to_int(high_conviction_shadow.get("deployable_count")) or 0
    nearest_candidate = _nearest_high_conviction_candidate(topk)
    candidate_model = _first_text(
        nearest_candidate.get("model_name"),
        nearest_candidate.get("model"),
        _as_dict(high_conviction_shadow.get("nearest_candidate")).get("model_name"),
        "no_model_candidate",
    ) or "no_model_candidate"
    candidate_threshold = _first_text(nearest_candidate.get("threshold_name"), nearest_candidate.get("top_k"), nearest_candidate.get("threshold"))
    model_shadow_ready = bool(
        (risk_qualified_count > 0 and runtime_blocked_candidate_count > 0 and deployable_count == 0)
        or high_conviction_shadow.get("shadow_available")
    )
    model_gate_passed = bool(deployable_count > 0)
    model_gate_status = "passed" if model_gate_passed else ("shadow_ready" if model_shadow_ready else "blocked")

    execution_cost_cfg = resolve_cost_aware_edge_config(config or {})
    trading_cost_cfg = _as_dict(config.get("trading"))
    forecast_edge_bps = _first_float(
        live_runtime_truth.get("forecast_edge_bps"),
        live_runtime_truth.get("expected_edge_bps"),
        live_runtime_truth.get("model_edge_bps"),
        nearest_candidate.get("forecast_edge_bps"),
        nearest_candidate.get("expected_edge_bps"),
        nearest_candidate.get("edge_bps"),
    )
    oos_roi_proxy = _first_float(nearest_candidate.get("avg_pnl"), nearest_candidate.get("oos_roi"))
    trade_count_proxy = _first_int(nearest_candidate.get("trade_count"), nearest_candidate.get("trades"))
    reference_edge_proxy_bps = None
    if forecast_edge_bps is None and oos_roi_proxy is not None and trade_count_proxy:
        reference_edge_proxy_bps = round(float(oos_roi_proxy) / max(int(trade_count_proxy), 1) * 10000.0, 2)
    fee_bps = _first_float(
        live_runtime_truth.get("taker_fee_bps"),
        live_runtime_truth.get("fee_bps"),
        execution_cost_cfg.get("taker_fee_bps"),
        execution_cost_cfg.get("fee_bps"),
        trading_cost_cfg.get("taker_fee_bps"),
        trading_cost_cfg.get("fee_bps"),
    )
    spread_bps = _first_float(
        live_runtime_truth.get("spread_bps"),
        execution_cost_cfg.get("spread_bps"),
        trading_cost_cfg.get("spread_bps"),
    )
    slippage_bps = _first_float(
        live_runtime_truth.get("slippage_bps"),
        execution_cost_cfg.get("slippage_bps"),
        trading_cost_cfg.get("slippage_bps"),
    )
    volatility_buffer_bps = _first_float(
        live_runtime_truth.get("volatility_buffer_bps"),
        execution_cost_cfg.get("volatility_buffer_bps"),
        trading_cost_cfg.get("volatility_buffer_bps"),
    )
    drawdown_buffer_bps = _first_float(
        live_runtime_truth.get("drawdown_buffer_bps"),
        live_runtime_truth.get("pyramid_drawdown_buffer_bps"),
        execution_cost_cfg.get("drawdown_buffer_bps"),
        trading_cost_cfg.get("drawdown_buffer_bps"),
        execution_cost_cfg.get("pyramid_drawdown_buffer_bps"),
    )
    cost_components = {
        "fee_bps": fee_bps,
        "spread_bps": spread_bps,
        "slippage_bps": slippage_bps,
        "volatility_buffer_bps": volatility_buffer_bps,
        "drawdown_buffer_bps": drawdown_buffer_bps,
    }
    present_cost_components = [float(value) for value in cost_components.values() if value is not None]
    required_edge_bps = round(sum(present_cost_components), 4) if present_cost_components else None
    if forecast_edge_bps is None:
        cost_aware_status = "needs_forecast_edge"
        cost_aware_summary = "尚缺 forecast_edge_bps / expected_edge_bps；OOS ROI proxy 只可作研究參考，不可放行 paper 風險進攻 candidate。"
    elif required_edge_bps is None:
        cost_aware_status = "needs_cost_inputs"
        cost_aware_summary = "已有 forecast edge，但尚缺 fee / spread / slippage / volatility buffer 成本模型；先不放行風險進攻 candidate。"
    elif float(forecast_edge_bps) > float(required_edge_bps):
        cost_aware_status = "passed"
        cost_aware_summary = f"forecast edge {float(forecast_edge_bps):.2f}bps > 成本門檻 {float(required_edge_bps):.2f}bps；只可作 paper/shadow candidate filter。"
    else:
        cost_aware_status = "blocked_edge_below_cost"
        cost_aware_summary = f"forecast edge {float(forecast_edge_bps):.2f}bps 未高於成本門檻 {float(required_edge_bps):.2f}bps；不進風險進攻 candidate。"
    cost_aware_passed = cost_aware_status == "passed"
    cost_aware_gap = None
    if forecast_edge_bps is not None and required_edge_bps is not None:
        cost_aware_gap = max(round(float(required_edge_bps) - float(forecast_edge_bps), 4), 0.0)

    if venue_dry_run_artifact:
        credential_present = bool(
            venue_dry_run_artifact.get("credential_present")
            or venue_dry_run_artifact.get("credentials_configured_any")
            or venue_dry_run_artifact_venue.get("credential_present")
            or venue_dry_run_artifact_venue.get("credentials_configured")
        )
    else:
        credential_present = bool(
            venue_record.get("credentials_configured")
            or _as_dict(account.get("health")).get("credentials_configured")
            or _as_dict(execution.get("health")).get("credentials_configured")
        )
    live_ready_blockers = [str(item) for item in _as_list(execution_surface_contract.get("live_ready_blockers")) if str(item).strip()]
    if venue_dry_run_artifact:
        venue_blockers = _first_text_list(
            venue_dry_run_artifact.get("runtime_ready_blockers"),
            venue_dry_run_artifact.get("blockers"),
            venue_dry_run_artifact_venue.get("blockers"),
        )
        proof_state = _first_text(
            venue_dry_run_artifact.get("proof_state"),
            venue_dry_run_artifact.get("status"),
            venue_dry_run_artifact_venue.get("proof_state"),
            venue_dry_run_artifact_venue.get("readiness_state"),
            "missing_runtime_backed_order_lifecycle",
        )
        venue_passed = bool(
            (venue_dry_run_artifact.get("runtime_ready") is True or venue_dry_run_artifact_venue.get("runtime_ready") is True)
            and not venue_blockers
            and str(venue_dry_run_artifact.get("status") or "").strip() in {"ready", "runtime_ready", "runtime_backed_proof_complete"}
        )
    else:
        venue_blockers = [str(item) for item in _as_list(venue_record.get("blockers")) if str(item).strip()]
        proof_state = _first_text(venue_record.get("proof_state"), "missing_runtime_backed_order_lifecycle")
        venue_passed = bool(credential_present and not venue_blockers and live_ready and proof_state in {"runtime_backed_proof_complete", "ready"})
    venue_status = "passed" if venue_passed else "blocked"

    symbol = str(payload.get("symbol") or "BTCUSDT")
    live_canary_policy_gate = _build_live_canary_policy_gate(config, symbol)
    live_canary_policy_passed = bool(live_canary_policy_gate.get("passed"))
    shadow_ready = bool(model_shadow_ready or range_chop.get("shadow_available") or range_chop.get("risk_reduction_allowed"))
    current_lane_live_prerequisites_passed = bool(support_passed and cost_aware_passed)
    canary_ready = bool(live_ready and model_gate_passed and current_lane_live_prerequisites_passed and release_passed and venue_passed and live_canary_policy_passed)
    risk_on_order_enabled = False
    order_submission_enabled = False
    readiness_status = "canary_ready" if canary_ready else ("shadow_reduce_only" if shadow_ready or range_chop.get("risk_reduction_allowed") else "blocked")

    model_detail_parts = []
    if risk_qualified_count:
        model_detail_parts.append(f"離線 / 風控已過 {risk_qualified_count} 筆")
    if runtime_blocked_candidate_count:
        model_detail_parts.append(f"執行期阻塞候選 {runtime_blocked_candidate_count} 筆")
    model_detail_parts.append(f"可部署樣本 {deployable_count} 筆")

    support_summary = (
        f"即時部署精準支持 {support_rows if support_rows is not None else '—'}/{support_minimum if support_minimum is not None else '—'}"
        f"，還差 {support_gap if support_gap is not None else '—'}"
    )
    release_summary = (
        f"最近 {release_window} 筆目前 {release_wins if release_wins is not None else '—'}/{release_window} 勝"
        f"，解除門檻 {release_required_wins if release_required_wins is not None else '—'} 勝"
        f"，還差 {release_gap if release_gap is not None else '—'} 勝"
    )
    release_next_action = (
        "熔斷已解除；仍需即時支持 gate 與場館證據鏈通過後才可升級 canary。"
        if release_passed
        else "最近窗勝場未達門檻前，只做 shadow / reduce-only，不升級 canary。"
    )
    release_evidence_status = (
        "release_ready"
        if release_passed
        else ("needs_more_resolved_wins" if release_gap is not None else "awaiting_release_math")
    )
    release_evidence_lane = {
        "status": release_evidence_status,
        "release_ready": release_passed,
        "blocked_by": [str(item) for item in _as_list(release_condition.get("blocked_by")) if str(item).strip()],
        "horizon_minutes": _first_int(release_condition.get("horizon_minutes"), circuit_breaker_audit.get("canonical_horizon_minutes"), 1440) or 1440,
        "recent_window": release_window,
        "current_recent_window_wins": release_wins,
        "required_recent_window_wins": release_required_wins,
        "wins_needed": release_gap,
        "current_recent_window_win_rate": _first_float(release_condition.get("current_recent_window_win_rate")),
        "current_streak": _first_int(release_condition.get("current_streak")),
        "streak_must_be_below": _first_int(release_condition.get("streak_must_be_below")),
        "next_validation_artifact": "data/circuit_breaker_audit.json",
        "verify_next": "venv/bin/python scripts/hb_circuit_breaker_audit.py",
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
        "live_order_submitted": False,
        "operator_message": (
            "熔斷解除 evidence 已通過；仍不代表可送單，需其他 hard gates 同時通過。"
            if release_passed
            else f"熔斷解除還差 {release_gap if release_gap is not None else '—'} 個 24h resolved wins；重跑 circuit breaker audit 驗證，不可繞過。"
        ),
    }

    strict_exact_support_subgate = {
        "key": "strict_exact_support_subgate",
        "label": "精準 exact support subgate",
        "status": "passed" if support_passed else "live_blocked",
        "passed": support_passed,
        "current": support_rows,
        "required": support_minimum,
        "gap": support_gap,
        "deployment_role": "live_canary_prerequisite",
        "live_exposure_allowed": False,
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
        "summary": (
            f"當前 exact live bucket {support_rows if support_rows is not None else '—'}/{support_minimum if support_minimum is not None else '—'}；live buy/add "
            f"{'仍需其他 hard gates' if support_passed else '保持阻塞'}。"
        ),
        "next_action": "這只決定 live-canary 前置條件；不足時不要只等待 50 筆，需轉入 shadow / cost-aware evidence lane。",
    }
    shadow_evidence_ready = bool(shadow_ready)
    shadow_evidence_subgate = {
        "key": "shadow_evidence_subgate",
        "label": "paper/shadow evidence subgate",
        "status": "ready" if shadow_evidence_ready else "blocked",
        "passed": shadow_evidence_ready,
        "shadow_ready": shadow_evidence_ready,
        "current": 1 if shadow_evidence_ready else 0,
        "required": 1,
        "gap": 0 if shadow_evidence_ready else 1,
        "risk_qualified_count": risk_qualified_count,
        "runtime_blocked_candidate_count": runtime_blocked_candidate_count,
        "live_candidate_count": deployable_count,
        "paper_shadow_available": shadow_evidence_ready,
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
        "summary": (
            "已有離線 / 風控候選或區間劇本，可做 paper/shadow observation；真實送單仍關閉。"
            if shadow_evidence_ready
            else "尚未形成可記錄的 paper/shadow evidence lane。"
        ),
        "next_action": "先記錄訊號、假想 entry、24h outcome 與 missed-entry reason；不可標成 live clearance。",
    }
    cost_aware_edge_subgate = {
        "key": "cost_aware_edge_subgate",
        "label": "成本感知 edge subgate",
        "status": cost_aware_status,
        "passed": cost_aware_passed,
        "current": forecast_edge_bps,
        "required": required_edge_bps,
        "gap": cost_aware_gap,
        "forecast_edge_bps": forecast_edge_bps,
        "required_edge_bps": required_edge_bps,
        "cost_components_bps": cost_components,
        "reference_edge_proxy_bps": reference_edge_proxy_bps,
        "edge_proxy_source": "topk_oos_roi_per_trade_reference_only" if reference_edge_proxy_bps is not None else None,
        "deployment_role": "paper_shadow_candidate_filter",
        "live_exposure_allowed": False,
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
        "summary": cost_aware_summary,
        "next_action": "接入 fee + spread + slippage + volatility / drawdown buffer；只有 forecast edge 明確大於成本門檻，才允許 paper/shadow 風險進攻候選。",
    }
    paper_shadow_buy_candidate_ready = bool(shadow_evidence_ready and cost_aware_passed)
    if support_passed and cost_aware_passed:
        current_lane_status = "exact_support_and_cost_ready"
        current_lane_summary = f"當前 lane exact support 與成本感知 edge 已達標：{support_summary}；但仍需模型、熔斷、場館與 canary policy 同時通過。"
    elif support_passed:
        current_lane_status = "exact_support_ready_cost_pending"
        current_lane_summary = f"當前 lane exact support 已達標：{support_summary}；但成本感知 edge subgate 尚未通過，live buy/add 仍保持阻塞。"
    elif shadow_evidence_ready:
        current_lane_status = "shadow_observation_ready_live_blocked"
        current_lane_summary = f"當前 exact live support 未達標：{support_summary}；live buy/add 阻塞，但可轉入 paper/shadow observation 與成本感知 edge 補證。"
    else:
        current_lane_status = "hold_only_live_blocked"
        current_lane_summary = f"當前 exact live support 未達標：{support_summary}；暫時只保留 wait/hold、減風險與 evidence collection。"
    if not support_passed:
        current_lane_next_action = "不要把 exact support 0/50 寫成只剩等待；先走 paper/shadow observation、cost-aware edge、venue dry-run 與 24h outcome evidence，live buy/add 仍 fail-closed。"
    elif not cost_aware_passed:
        current_lane_next_action = "exact support 已達標但成本感知 edge 尚未通過；補 forecast_edge_bps 與 fee/spread/slippage/buffer 後再評估 buy/add。"
    else:
        current_lane_next_action = "exact support 與成本感知 edge 都只是 live prerequisites；繼續檢查模型、熔斷、場館與 bounded canary policy。"
    current_lane_actionability_gate = {
        "key": "current_lane_actionability_gate",
        "label": "當前 lane 可行動 gate",
        "status": current_lane_status,
        "passed": current_lane_live_prerequisites_passed,
        "shadow_ready": shadow_evidence_ready,
        "paper_shadow_available": shadow_evidence_ready,
        "paper_shadow_buy_candidate_ready": paper_shadow_buy_candidate_ready,
        "live_buy_add_allowed": False,
        "live_exposure_allowed": False,
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
        "current": support_rows,
        "required": support_minimum,
        "gap": support_gap,
        "actionability": "live_canary_prerequisite_ready" if current_lane_live_prerequisites_passed else ("paper_shadow_observation_only" if shadow_evidence_ready else "wait_hold_reduce_only"),
        "summary": current_lane_summary,
        "next_action": current_lane_next_action,
        "sub_gates": [strict_exact_support_subgate, shadow_evidence_subgate, cost_aware_edge_subgate],
    }

    gates = [
        {
            "key": "model_gate",
            "label": "模型 gate",
            "status": model_gate_status,
            "passed": model_gate_passed,
            "shadow_ready": model_shadow_ready,
            "current": deployable_count,
            "required": 1,
            "gap": 0 if model_gate_passed else 1,
            "summary": "；".join(model_detail_parts),
            "next_action": "研究勝出模型可進影子觀察；不可標成可部署，直到即時 gate 與場館證據鏈通過。",
        },
        current_lane_actionability_gate,
        {
            "key": "current_live_support_gate",
            "label": "即時支持 gate（legacy exact subgate）",
            "status": "passed" if support_passed else "blocked",
            "passed": support_passed,
            "current": support_rows,
            "required": support_minimum,
            "gap": support_gap,
            "summary": support_summary,
            "sub_gate_of": "current_lane_actionability_gate",
            "next_action": "精準 exact support 是 live-canary 前置條件；不足時 live buy/add 仍關閉，但不要只等待 50 筆，需走 paper/shadow + cost-aware evidence lane。",
        },
        {
            "key": "circuit_breaker_gate",
            "label": "熔斷 gate",
            "status": "passed" if release_passed else "blocked",
            "passed": release_passed,
            "current": release_wins,
            "required": release_required_wins,
            "gap": release_gap,
            "release_ready": release_passed,
            "release_condition": release_condition or None,
            "release_evidence_lane": release_evidence_lane,
            "next_validation_artifact": "data/circuit_breaker_audit.json",
            "verify_next": "venv/bin/python scripts/hb_circuit_breaker_audit.py",
            "order_submission_enabled": False,
            "risk_on_order_enabled": False,
            "live_order_submitted": False,
            "summary": release_summary,
            "next_action": release_next_action,
        },
        {
            "key": "venue_gate",
            "label": "場館 gate",
            "status": venue_status,
            "passed": venue_passed,
            "current": 1 if credential_present else 0,
            "required": 1,
            "gap": 0 if credential_present else 1,
            "summary": (
                f"venue dry-run proof {venue_dry_run_artifact.get('status')}；runtime_ready "
                f"{venue_dry_run_artifact.get('runtime_ready_count', '—')}/{venue_dry_run_artifact.get('venues_checked', '—')}"
                if venue_dry_run_artifact
                else ("credential present 已確認" if credential_present else "credential present 尚未有 runtime-backed proof")
            ),
            "blockers": venue_blockers or live_ready_blockers,
            "next_action": _first_text(
                venue_dry_run_artifact.get("operator_next_action"),
                venue_dry_run_artifact_venue.get("operator_next_action"),
                venue_record.get("operator_next_action"),
                "補齊 credential presence、order ack、cancel、fill lifecycle 與 reconciliation proof。",
            ),
        },
        {
            "key": "shadow_observation_gate",
            "label": "影子觀察 gate",
            "status": "ready" if shadow_ready else "blocked",
            "passed": shadow_ready,
            "current": 1 if shadow_ready else 0,
            "required": 1,
            "gap": 0 if shadow_ready else 1,
            "summary": "影子觀察可記錄訊號 / 假想 entry / 24h 結果；不送單。" if shadow_ready else "尚未形成可記錄的影子觀察候選。",
            "next_action": "今天可啟動影子觀察、dry-run preview、ack / cancel / fill simulation 與減風險演練。",
        },
        live_canary_policy_gate,
    ]
    gate_by_key = {gate["key"]: gate for gate in gates}
    blocking_gate = None
    for gate_key in (
        "circuit_breaker_gate",
        "current_lane_actionability_gate",
        "venue_gate",
        "model_gate",
        "live_canary_policy_gate",
        "current_live_support_gate",
        "shadow_observation_gate",
    ):
        gate = gate_by_key.get(gate_key)
        if gate is not None and not gate.get("passed"):
            blocking_gate = gate
            break

    what_can_do_now = [
        "用 /api/trade shadow_buy / paper_buy 進入 paper/shadow 實戰演練（dry_run=true，不送 OKX live order）",
        "啟動影子觀察並寫入 Shadow Trade Ledger",
        "做 venue dry-run proof：order preview、ack simulation、cancel simulation、fill simulation、reconciliation check",
        "減碼 / 取消掛單 / 賣出風險降低路徑仍可用",
        "持續收集即時部署精準支持與 24h pyramid outcome",
    ]
    if not release_passed:
        what_can_do_now.append(
            f"熔斷 release evidence：目前 {release_wins if release_wins is not None else '—'}/{release_window} 勝，還差 {release_gap if release_gap is not None else '—'} 個 resolved wins；重跑 scripts/hb_circuit_breaker_audit.py 驗證。"
        )
    what_cannot_do_now = [
        "買入 / 加倉仍鎖住，直到當前 lane exact support、熔斷 gate、場館 gate 全過",
        "不能把 OOS 勝出模型、寬範圍分桶或參考支持標成可部署",
        "不能啟用風險進攻自動下單或完整實單自動化",
    ]

    execution_readiness = {
        "status": readiness_status,
        "stage_label": "Shadow / Reduce-only" if not canary_ready else "Canary-ready",
        "canary_ready": canary_ready,
        "live_ready": live_ready,
        "risk_on_order_enabled": risk_on_order_enabled,
        "order_submission_enabled": order_submission_enabled,
        "blocking_gate_key": blocking_gate.get("key") if blocking_gate else None,
        "blocking_gate_label": blocking_gate.get("label") if blocking_gate else None,
        "operator_message": "實戰準備度目前停在 Shadow / Reduce-only：可以演練與記錄，不可買入 / 加倉。" if not canary_ready else "所有 gate 已通過；只能進入最小 canary，不是 full deploy。",
        "gates": gates,
        "what_can_do_now": what_can_do_now,
        "what_cannot_do_now": what_cannot_do_now,
        "time_to_evidence": time_to_evidence,
        "alternative_solution_review": alternative_solution_review,
        "circuit_breaker_release_evidence_lane": release_evidence_lane,
        "next_release_condition": "current lane exact support ≥ 50/50、recent 50 ≥ 15 勝、venue proof chain 完整、live_canary policy 完整，且 live_ready=true。",
    }

    timestamp = str(payload.get("timestamp") or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    structure_bucket = _first_text(live_runtime_truth.get("structure_bucket"), live_runtime_truth.get("current_live_structure_bucket"), "—") or "—"
    regime = f"{_first_text(live_runtime_truth.get('regime_label'), '—')} / {_first_text(live_runtime_truth.get('regime_gate'), '—')} / {structure_bucket}"
    confidence = _first_float(live_runtime_truth.get("confidence"))
    entry_id_timestamp = timestamp.replace(":", "").replace("-", "").replace(".", "")
    shadow_entry = {
        "id": f"shadow-{symbol}-{entry_id_timestamp}",
        "signal_time": timestamp,
        "candidate_model": candidate_model,
        "candidate_threshold": candidate_threshold,
        "confidence": confidence,
        "regime": regime,
        "hypothetical_entry": {
            "symbol": symbol,
            "side": "shadow_long_observation",
            "entry_source": "next_runtime_signal_close_or_preview_price",
            "order_submission_enabled": False,
            "operator_copy": "假想 entry 只記錄，不送單、不加倉。",
        },
        "outcome_24h": {
            "status": "pending_observation_window",
            "window_hours": 24,
            "pnl_pct": None,
            "pyramid_win": None,
        },
        "pyramid_win": None,
        "operator_note": "此列是影子訊號帳本 entry；用來回答 24h 後是否符合 pyramid win，不是委託紀錄。",
    }
    shadow_trade_ledger = {
        "status": "recording_ready" if shadow_ready else "waiting_for_shadow_candidate",
        "mode": "paper_shadow_no_order",
        "order_submission_enabled": False,
        "schema": ["signal_time", "candidate_model", "confidence", "regime", "hypothetical_entry", "outcome_24h", "pyramid_win"],
        "entries": [shadow_entry] if shadow_ready else [],
        "operator_message": "Shadow Trade Ledger 會記錄每個影子訊號、假想 entry 與 24h outcome；它不是下單帳本。",
    }

    venue_label = _first_text(venue_record.get("venue"), execution.get("venue"), "unknown") or "unknown"
    fallback_venue_dry_run_proof = {
        "status": "ready" if venue_passed else "blocked_missing_runtime_backed_proof",
        "venue": venue_label,
        "credential_present": credential_present,
        "secrets_redacted": True,
        "proof_state": proof_state,
        "blockers": venue_blockers or live_ready_blockers or ["credential / order ack / fill lifecycle proof 尚未完成"],
        "operator_next_action": _first_text(venue_record.get("operator_next_action"), "先跑 dry-run preview，再補 ack / cancel / fill / reconciliation proof。"),
        "verify_next": _first_text(venue_record.get("verify_next"), "python scripts/execution_metadata_smoke.py --symbol BTCUSDT --venues okx"),
        "order_preview": {
            "status": "preview_available",
            "symbol": symbol,
            "side": "buy_preview_only",
            "qty": 0.001,
            "order_submission_enabled": False,
            "runtime_backed": False,
        },
        "ack_simulation": {
            "status": "simulation_only_waiting_runtime_ack",
            "runtime_backed": False,
        },
        "cancel_simulation": {
            "status": "simulation_only_waiting_runtime_cancel_ack",
            "runtime_backed": False,
        },
        "fill_simulation": {
            "status": "simulation_only_waiting_runtime_fill",
            "runtime_backed": False,
        },
        "reconciliation_check": {
            "status": _first_text(execution_reconciliation.get("status"), "limited_evidence_no_runtime_order"),
            "runtime_backed": False,
            "summary": _first_text(execution_reconciliation.get("summary"), "尚未有 runtime-backed order / fill lifecycle 可對帳。"),
        },
    }
    venue_dry_run_proof = _normalize_venue_dry_run_artifact(
        venue_dry_run_artifact,
        symbol=symbol,
        execution=execution,
        fallback_venue_record=venue_record,
        execution_reconciliation=execution_reconciliation,
        live_ready_blockers=live_ready_blockers,
    ) or fallback_venue_dry_run_proof
    customer_safe_alternative_proof = _compact_customer_safe_alternative_proof(customer_safe_alternative_artifact)

    distance_to_canary = [
        f"熔斷 gate：{release_summary}",
        f"當前 lane 可行動 gate：{current_lane_summary}",
        f"精準 exact support subgate：{support_summary}",
        f"成本感知 edge subgate：{cost_aware_summary}",
        f"time-to-evidence：{time_to_evidence_summary}",
        "場館 gate：credential present、order preview、ack simulation、cancel simulation、fill simulation、reconciliation check 都必須 runtime-backed。",
        f"Live-canary policy gate：{live_canary_policy_gate.get('summary')}",
    ]
    milestone_progression = _build_milestone_progression(
        symbol=symbol,
        canary_ready=canary_ready,
        shadow_ready=shadow_ready,
        support_passed=support_passed,
        release_passed=release_passed,
        venue_passed=venue_passed,
        model_gate_passed=model_gate_passed,
        live_canary_policy_passed=live_canary_policy_passed,
        blocking_gate=blocking_gate,
        venue_dry_run_proof=venue_dry_run_proof,
    )
    execution_readiness["milestone_progression"] = milestone_progression
    execution_readiness["milestone_progression"]["circuit_breaker_release_evidence_lane"] = release_evidence_lane
    for milestone in execution_readiness["milestone_progression"].get("milestones", []):
        if isinstance(milestone, dict) and milestone.get("key") == "M2_support_and_breaker":
            milestone["circuit_breaker_release_evidence_lane"] = release_evidence_lane
            milestone["next_validation_artifact"] = "data/circuit_breaker_audit.json"
            milestone["verify_next"] = "venv/bin/python scripts/hb_circuit_breaker_audit.py"
            break

    canary_gap_answers = {
        "canary_ready": canary_ready,
        "distance_to_canary": distance_to_canary,
        "drills_available_today": what_can_do_now,
        "blocked_gate_key": blocking_gate.get("key") if blocking_gate else None,
        "blocking_gate": blocking_gate.get("label") if blocking_gate else "無",
        "blocked_gate_summary": blocking_gate.get("summary") if blocking_gate else "所有 gate 已通過，只允許最小 canary。",
        "time_to_evidence": time_to_evidence,
        "alternative_solution_review": alternative_solution_review,
        "milestone_progression": milestone_progression,
        "circuit_breaker_release_evidence_lane": release_evidence_lane,
        "first_canary_plan_if_all_gates_pass": {
            "exposure_pct_max": 0.01,
            "pyramid_layer": "20% first layer only",
            "symbol": symbol,
            "mode": "canary_only_after_all_gates_pass",
            "order_type": "post-only/limit preview first, then tiny canary after operator review",
            "add_exposure_enabled": False,
            "stop_conditions": ["gate regression", "venue proof stale", "24h pyramid outcome fails", "unexpected reconciliation issue"],
        },
    }

    return {
        "execution_readiness": execution_readiness,
        "shadow_trade_ledger": shadow_trade_ledger,
        "venue_dry_run_proof": venue_dry_run_proof,
        "customer_safe_alternative_proof": customer_safe_alternative_proof,
        "canary_gap_answers": canary_gap_answers,
    }

def _build_user_action_state(readiness_bundle: Dict[str, Any], timestamp: Any) -> Dict[str, Any]:
    """Collapse execution governance into one actionable, safety-preserving product contract."""

    bundle = _as_dict(readiness_bundle)
    readiness = _as_dict(bundle.get("execution_readiness"))
    gap_answers = _as_dict(bundle.get("canary_gap_answers"))
    time_to_evidence = _as_dict(gap_answers.get("time_to_evidence"))
    alternative_review = _as_dict(gap_answers.get("alternative_solution_review"))
    milestone = _as_dict(readiness.get("milestone_progression"))
    gates = [item for item in _as_list(readiness.get("gates")) if isinstance(item, dict)]
    blocking_key = str(readiness.get("blocking_gate_key") or gap_answers.get("blocked_gate_key") or "")
    blocking_gate = next((item for item in gates if str(item.get("key") or "") == blocking_key), {})
    live_ready = bool(readiness.get("live_ready") or readiness.get("canary_ready"))
    current = blocking_gate.get("current")
    required = blocking_gate.get("required")
    preferred = _as_dict(milestone.get("preferred_entrypoint"))
    alternative_required = bool(time_to_evidence.get("alternative_solution_required") or alternative_review.get("status") == "required")

    if live_ready:
        state = "bounded_canary_ready"
        next_action = "以明確數量上限執行最小 canary，任何 gate 回退立即停止。"
        cta_label = "檢查 bounded canary 設定"
    elif milestone.get("active_lane") == "paper_shadow_buy":
        state = "paper_shadow_active"
        next_action = "立即執行 Paper/Shadow worker，持續累積 24h outcome；不必等待 Live gate。"
        cta_label = "執行下一次安全演練"
    else:
        state = "safe_lane_active"
        next_action = str(alternative_review.get("operator_message") or readiness.get("operator_message") or "保持 no-order 並執行下一個安全證據步驟。")
        cta_label = "執行安全替代路線"

    return {
        "state": state,
        "progress_current": current,
        "progress_target": required,
        "freshness": {"as_of": timestamp, "status": "current_snapshot"},
        "blocking_reason": blocking_gate.get("summary") or gap_answers.get("blocked_gate_summary"),
        "next_action": next_action,
        "cta": {
            "id": "advance_safe_lane",
            "label": cta_label,
            "endpoint": preferred.get("endpoint"),
            "method": preferred.get("method"),
            "payload": preferred.get("payload"),
            "command": preferred.get("command"),
            "live_order_submitted": False if not live_ready else "only_after_adapter_guardrails_pass",
        },
        "deadline": {
            "status": time_to_evidence.get("status") or "unknown",
            "estimated_heartbeats": time_to_evidence.get("estimated_heartbeats_to_support"),
            "estimated_hours": time_to_evidence.get("estimated_hours_at_hourly_heartbeat"),
            "estimated_days": time_to_evidence.get("estimated_days_at_hourly_heartbeat"),
            "summary": time_to_evidence.get("summary") or "尚無可靠完成時間。",
        },
        "alternative_lane": {
            "required": alternative_required,
            "key": milestone.get("active_lane") or alternative_review.get("primary_alternative"),
            "label": milestone.get("active_lane_label") or alternative_review.get("primary_alternative"),
            "auto_adjustment_applied": bool(milestone.get("auto_adjustment_applied")),
            "live_exposure_allowed": False if not live_ready else True,
        },
        "operator_fix": {
            "required": alternative_required,
            "trigger": alternative_review.get("trigger"),
            "next_review_trigger": alternative_review.get("next_review_trigger"),
            "label": "改走可執行的 Paper/Shadow、場館 dry-run 與 drift/rebaseline 評估；不可只顯示等待。" if alternative_required else None,
        },
        "safety": {
            "order_submission_enabled": bool(readiness.get("order_submission_enabled")) if live_ready else False,
            "risk_on_order_enabled": bool(readiness.get("risk_on_order_enabled")) if live_ready else False,
            "live_order_submitted": False,
        },
    }


def build_execution_overview(
    status_payload: Optional[Dict[str, Any]],
    config: Optional[Dict[str, Any]] = None,
    control_plane: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload = _as_dict(status_payload)
    config = _as_dict(config)
    control_plane = _as_dict(control_plane)

    symbol = str(payload.get("symbol") or "BTCUSDT")
    timestamp = payload.get("timestamp") or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    execution_surface_contract = _as_dict(payload.get("execution_surface_contract"))
    live_runtime_truth = _as_dict(_as_dict(payload.get("execution")).get("live_runtime_truth") or execution_surface_contract.get("live_runtime_truth"))
    sleeve_routing = _as_dict(live_runtime_truth.get("sleeve_routing"))
    account = _as_dict(payload.get("account"))
    runs_by_profile = _as_dict(control_plane.get("runs_by_profile"))
    strategy_source_snapshot = build_execution_strategy_source_snapshot()
    strategy_bindings = _as_dict(strategy_source_snapshot.get("sleeve_bindings"))
    high_conviction_shadow_contract = _build_high_conviction_shadow_contract(payload)
    high_conviction_topk = _load_high_conviction_topk(payload)
    range_chop_playbook = build_range_chop_playbook(live_runtime_truth, high_conviction_topk)
    range_chop_shadow_available = bool(range_chop_playbook.get("shadow_available"))

    positions = [item for item in _as_list(account.get("positions")) if isinstance(item, dict)]
    open_orders = [item for item in _as_list(account.get("open_orders")) if isinstance(item, dict)]
    requested_symbol = account.get("requested_symbol")
    normalized_symbol = account.get("normalized_symbol")
    symbol_scope_keys = _symbol_keys(symbol, requested_symbol if isinstance(requested_symbol, str) else None, normalized_symbol if isinstance(normalized_symbol, str) else None)
    symbol_positions = _filter_records_for_symbol(positions, symbol_scope_keys)
    symbol_open_orders = _filter_records_for_symbol(open_orders, symbol_scope_keys)

    balance = _as_dict(account.get("balance"))
    balance_total = _to_float(balance.get("total"))
    balance_free = _to_float(balance.get("free"))
    allocated_capital = None
    if balance_total is not None and balance_free is not None:
        allocated_capital = max(float(balance_total) - float(balance_free), 0.0)

    trading_cfg = _as_dict(config.get("trading"))
    max_position_ratio = _to_float(trading_cfg.get("max_position_ratio"))
    if max_position_ratio is None:
        max_position_ratio = 0.05
    confidence = _to_float(live_runtime_truth.get("confidence"))
    deployable_capital = None
    if balance_total is not None and confidence is not None:
        deployable_capital = check_position_size(balance_total, confidence, max_position_ratio=max_position_ratio)

    active_items = {
        str(item.get("key") or "").strip(): item
        for item in _as_list(sleeve_routing.get("active_sleeves"))
        if isinstance(item, dict)
    }
    inactive_items = {
        str(item.get("key") or "").strip(): item
        for item in _as_list(sleeve_routing.get("inactive_sleeves"))
        if isinstance(item, dict)
    }
    active_count = len(active_items)
    global_blocker = str(
        live_runtime_truth.get("deployment_blocker")
        or live_runtime_truth.get("execution_guardrail_reason")
        or sleeve_routing.get("global_blocker_reason")
        or ""
    ).strip()

    cards: List[Dict[str, Any]] = []
    blocked_count = 0
    standby_count = 0
    monitoring_count = 0

    for key in PRIMARY_SLEEVE_ORDER:
        active_item = active_items.get(key)
        inactive_item = inactive_items.get(key)
        routing_item = active_item or inactive_item or {}
        fallback = PRIMARY_SLEEVE_META.get(key, {"label": key, "summary": ""})
        label = str(routing_item.get("label") or fallback.get("label") or key)
        summary = str(routing_item.get("summary") or fallback.get("summary") or "")
        active = active_item is not None
        routing_reason = str(routing_item.get("why") or "尚未取得 routing reason。")
        shadow_candidate = bool(
            key == "selective"
            and global_blocker
            and high_conviction_shadow_contract.get("shadow_available")
        )

        if active and (symbol_positions or symbol_open_orders):
            lifecycle_status = "monitoring_shared_symbol"
            next_action = "目前 symbol scope 已有持倉或掛單；先對帳 shared position / open orders，再決定是否擴充成獨立 bot runtime。"
            monitoring_count += 1
        elif active:
            lifecycle_status = "ready_preview"
            next_action = "目前 routing 允許此 sleeve；可用這張卡做 preview-level bot/profile 規劃，但 start/pause/stop mutation API 尚未落地。"
        elif shadow_candidate:
            lifecycle_status = "shadow_monitoring"
            next_action = str(high_conviction_shadow_contract.get("next_operator_action") or "啟動影子觀察運行；只記錄決策，不送單、不加倉。")
            monitoring_count += 1
        elif range_chop_shadow_available and key in {"pullback", "rebound", "selective"}:
            lifecycle_status = "range_shadow_candidate"
            next_action = str(
                range_chop_playbook.get("next_operator_action")
                or "高低震盪不是永遠不能實戰；先做影子觀察與減風險檢查，買入 / 加倉仍等即時部署門檻。"
            )
            monitoring_count += 1
        elif global_blocker:
            lifecycle_status = "blocked_preview"
            next_action = f"先解除全域 blocker：{global_blocker}。解除前不要把這個 sleeve 包裝成可啟動 bot。"
            blocked_count += 1
        else:
            lifecycle_status = "standby"
            next_action = "目前 routing 未啟用此 sleeve；先觀察 regime/gate 變化，不要預先啟動。"
            standby_count += 1

        budget = _planned_budget(
            active=active,
            total_balance=balance_total,
            deployable_capital=deployable_capital,
            active_count=active_count,
        )

        current_run = _as_dict(runs_by_profile.get(key))
        current_run_state = str(current_run.get("state") or "").strip()
        current_run_event = _as_dict(current_run.get("latest_event"))

        if current_run_state == "running":
            start_status = "already_running"
            start_reason = "此 sleeve 已有 stateful running run；可直接 pause/stop，或讓它維持目前 control-plane 狀態。"
            pause_status = "available"
            stop_status = "available"
            next_action = "目前已有 stateful running run；下一步應確認 per-bot capital / position attribution 是否已接上，而不是再重複 start。"
        elif current_run_state == "paused":
            start_status = "resume_available"
            start_reason = "此 sleeve 先前已建立 paused run；可直接 resume，不必重新建立新 run。"
            pause_status = "already_paused"
            stop_status = "available"
            next_action = "此 sleeve 目前在 paused；若要繼續，請 resume 並對齊 per-bot runtime binding。"
        elif shadow_candidate:
            start_status = "shadow_start_available"
            start_reason = str(high_conviction_shadow_contract.get("start_reason") or "可啟動影子觀察運行；只記錄決策，不送單、不加倉。")
            pause_status = "available_when_running"
            stop_status = "available_when_running"
        elif active and not global_blocker:
            start_status = "ready_control_plane"
            start_reason = "routing active，且目前沒有全域 execution blocker；可建立 stateful run control beta。"
            pause_status = "available_when_running"
            stop_status = "available_when_running"
        elif active:
            start_status = "blocked_preview"
            start_reason = f"routing 雖 active，但目前仍被 blocker 擋下：{global_blocker}。"
            pause_status = "blocked_until_started"
            stop_status = "blocked_until_started"
        else:
            start_status = "inactive_preview"
            start_reason = routing_reason
            pause_status = "blocked_until_started"
            stop_status = "blocked_until_started"

        strategy_binding = _as_dict(_as_dict(strategy_bindings.get(key)).get("recommended")) or None
        control_contract = {
            "mode": control_plane.get("controls_mode") or CONTROL_MODE,
            "start_status": start_status,
            "start_reason": start_reason,
            "pause_status": pause_status,
            "stop_status": stop_status,
            "latest_event_type": current_run.get("last_event_type"),
            "latest_event_message": current_run.get("last_event_message") or current_run_event.get("message"),
            "upgrade_required": True,
            "upgrade_prerequisite": CONTROL_PLANE_UPGRADE_PREREQUISITE,
        }
        if range_chop_shadow_available:
            control_contract.update(
                {
                    "range_chop_playbook": range_chop_playbook,
                    "risk_reduction_allowed": True,
                    "buy_add_requires_current_live_gate": True,
                    "risk_on_order_enabled": False,
                    "order_submission_enabled": False,
                }
            )
        if shadow_candidate:
            control_contract.update(
                {
                    "shadow_only": True,
                    "risk_on_order_enabled": False,
                    "shadow_mode": high_conviction_shadow_contract.get("shadow_mode") or "paper_shadow",
                    "high_conviction_topk": high_conviction_shadow_contract,
                    "upgrade_prerequisite": (
                        "先以影子觀察運行收集即時決策與事件紀錄；只有當即時精準樣本、"
                        "場館憑證 / 委託 / 成交證據鏈與單一 Bot 帳本都通過後，才能升級小流量。"
                    ),
                }
            )

        cards.append(
            {
                "key": key,
                "profile_id": key,
                "label": label,
                "summary": summary,
                "activation_status": "active" if active else ("shadow_candidate" if shadow_candidate else "inactive"),
                "lifecycle_status": lifecycle_status,
                "routing_reason": routing_reason,
                "current_regime": sleeve_routing.get("current_regime") or live_runtime_truth.get("regime_label"),
                "current_regime_gate": sleeve_routing.get("current_regime_gate") or live_runtime_truth.get("regime_gate"),
                "current_structure_bucket": sleeve_routing.get("current_structure_bucket") or live_runtime_truth.get("structure_bucket"),
                "allowed_layers": live_runtime_truth.get("allowed_layers"),
                "allowed_layers_reason": live_runtime_truth.get("allowed_layers_reason"),
                "deployment_blocker": live_runtime_truth.get("deployment_blocker"),
                "execution_guardrail_reason": live_runtime_truth.get("execution_guardrail_reason"),
                "strategy_binding": strategy_binding,
                "controls_mode": control_plane.get("controls_mode") or CONTROL_MODE,
                "current_run": current_run or None,
                "current_run_state": current_run_state or None,
                "control_contract": control_contract,
                "symbol_scoped_position_count": len(symbol_positions),
                "symbol_scoped_open_order_count": len(symbol_open_orders),
                "next_operator_action": next_action,
                **budget,
            }
        )

    controls_mode = control_plane.get("controls_mode") or CONTROL_MODE
    control_plane_summary = _as_dict(control_plane.get("summary"))
    summary = {
        "total_profiles": len(cards),
        "active_profiles": active_count,
        "standby_profiles": standby_count,
        "blocked_profiles": blocked_count,
        "monitoring_profiles": monitoring_count,
        "running_runs": control_plane_summary.get("running_runs", 0),
        "paused_runs": control_plane_summary.get("paused_runs", 0),
        "stopped_runs": control_plane_summary.get("stopped_runs", 0),
        "total_runs": control_plane_summary.get("total_runs", 0),
        "controls_mode": controls_mode,
        "allocation_rule": "equal_split_active_sleeves",
        "operator_message": control_plane.get("operator_message") or CONTROL_PLANE_OPERATOR_MESSAGE,
    }

    capital_plan = {
        "currency": balance.get("currency") or "USDT",
        "total_balance": balance_total,
        "free_balance": balance_free,
        "allocated_capital": allocated_capital,
        "deployable_capital": deployable_capital,
        "max_position_ratio": max_position_ratio,
        "confidence": confidence,
        "active_profile_count": active_count,
        "per_active_profile_budget": (float(deployable_capital) / float(active_count)) if deployable_capital is not None and active_count > 0 else None,
        "allocation_rule": "equal_split_active_sleeves",
        "symbol_scoped_position_count": len(symbol_positions),
        "symbol_scoped_open_order_count": len(symbol_open_orders),
        "operator_message": "可部署資金目前仍先依風險控管頭寸公式估算，再由啟用倉位腿均分；運行控制雖已可持久化，但每個 Bot 的資金帳本仍未落地。",
    }

    readiness_bundle = build_execution_readiness_bundle(payload, range_chop_playbook=range_chop_playbook, config=config)

    return {
        "symbol": symbol,
        "timestamp": timestamp,
        "controls_mode": controls_mode,
        "source_route": "/api/status",
        "operator_message": summary["operator_message"],
        "upgrade_prerequisite": control_plane.get("upgrade_prerequisite") or CONTROL_PLANE_UPGRADE_PREREQUISITE,
        "summary": summary,
        "capital_plan": capital_plan,
        "strategy_source_summary": _as_dict(strategy_source_snapshot.get("summary")),
        "profile_cards": cards,
        "range_chop_playbook": range_chop_playbook,
        **readiness_bundle,
        "user_action_state": _build_user_action_state(readiness_bundle, timestamp),
        "live_ready": bool(execution_surface_contract.get("live_ready", False)),
        "live_ready_blockers": _as_list(execution_surface_contract.get("live_ready_blockers")),
    }
