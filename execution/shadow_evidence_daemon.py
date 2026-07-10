"""Paper/shadow evidence collection daemon helpers.

This module intentionally collects evidence only.  It forces paper/dry-run mode,
records live-runner decisions/JSONL, reconciles 24h labels when available, and
writes a compact dashboard artifact.  It must never enable live order submission.
"""
from __future__ import annotations

import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from execution.control_plane import build_live_runner_overview, build_paper_shadow_outcome_reconciliation
from execution.live_runner import LiveTradingRunner

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SHADOW_EVIDENCE_DAEMON_ARTIFACT_PATH = PROJECT_ROOT / "data" / "shadow_evidence_daemon.json"
SHADOW_EVIDENCE_DAEMON_LOG_PATH = PROJECT_ROOT / "data" / "shadow_evidence_daemon.jsonl"
DEFAULT_SHADOW_EVIDENCE_RUN_ID = "shadow-evidence-daemon"
DEFAULT_COLLECT_INTERVAL_SECONDS = 900
DEFAULT_OPERATOR_REVIEW_INTERVAL_HOURS = 6.0


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def isoformat_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _latest_decision_summary(live_runner_overview: Dict[str, Any]) -> Dict[str, Any]:
    latest = _as_dict(live_runner_overview.get("latest_decision"))
    if not latest:
        return {
            "status": "no_decision_yet",
            "action": None,
            "reason": "等待下一輪 shadow evidence collection",
        }
    return {
        "status": "available",
        "decision_id": latest.get("decision_id"),
        "run_id": latest.get("run_id"),
        "created_at": latest.get("created_at"),
        "feature_timestamp": latest.get("feature_timestamp"),
        "price": latest.get("price"),
        "action": latest.get("action"),
        "signal": latest.get("signal"),
        "reason": latest.get("reason"),
        "model_confidence": latest.get("model_confidence"),
        "entry_quality": latest.get("entry_quality"),
        "order_submitted": bool(latest.get("order_submitted")),
        "dry_run": latest.get("dry_run"),
        "live_order_submitted": bool(latest.get("live_order_submitted")),
    }


def load_shadow_evidence_daemon_artifact(
    artifact_path: Path = SHADOW_EVIDENCE_DAEMON_ARTIFACT_PATH,
) -> Dict[str, Any]:
    path = Path(artifact_path)
    if not path.exists():
        return {
            "available": False,
            "artifact_path": str(path),
            "status": "daemon_artifact_missing",
            "operator_message": "尚未建立 shadow evidence daemon artifact；先跑 scripts/shadow_evidence_daemon.py --once。",
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "available": False,
            "artifact_path": str(path),
            "status": "daemon_artifact_unreadable",
            "error": str(exc),
            "operator_message": "shadow evidence daemon artifact 無法讀取；需重新跑 daemon tick。",
        }
    if not isinstance(payload, dict):
        return {
            "available": False,
            "artifact_path": str(path),
            "status": "daemon_artifact_invalid",
            "operator_message": "shadow evidence daemon artifact 格式錯誤；需重新產生。",
        }
    return {"available": True, "artifact_path": str(path), **payload}


def _persist_json(path: Path, payload: Dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")
    tmp.replace(path)


def _append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str) + "\n")


def shadow_evidence_runtime_config(config: Dict[str, Any], *, interval_seconds: Optional[int] = None) -> Dict[str, Any]:
    """Return a fail-closed paper/shadow-only runtime config."""

    cfg = copy.deepcopy(config or {})
    live_cfg = cfg.setdefault("live_runner", {})
    trading_cfg = cfg.setdefault("trading", {})
    execution_cfg = cfg.setdefault("execution", {})
    if interval_seconds is not None:
        live_cfg["interval_seconds"] = max(1, int(interval_seconds))
    live_cfg["shadow_candidate_enabled"] = True
    live_cfg["shadow_evidence_mode"] = True
    live_cfg.setdefault("one_shadow_candidate_per_feature_timestamp", True)
    trading_cfg["dry_run"] = True
    execution_cfg["mode"] = "paper"
    execution_cfg["enable_live_trading"] = False
    live_canary = execution_cfg.setdefault("live_canary", {})
    if isinstance(live_canary, dict):
        live_canary["enabled"] = False
    return cfg


def build_shadow_evidence_daemon_artifact(
    *,
    previous_artifact: Optional[Dict[str, Any]] = None,
    live_runner_overview: Optional[Dict[str, Any]] = None,
    outcome_reconciliation: Optional[Dict[str, Any]] = None,
    latest_cycle_decision: Optional[Dict[str, Any]] = None,
    now: Optional[datetime] = None,
    interval_seconds: int = DEFAULT_COLLECT_INTERVAL_SECONDS,
    review_interval_hours: float = DEFAULT_OPERATOR_REVIEW_INTERVAL_HOURS,
    artifact_path: Path = SHADOW_EVIDENCE_DAEMON_ARTIFACT_PATH,
    log_path: Path = SHADOW_EVIDENCE_DAEMON_LOG_PATH,
) -> Dict[str, Any]:
    """Build compact dashboard/operator state for the evidence daemon."""

    now = now or utc_now()
    previous = _as_dict(previous_artifact)
    live_runner = _as_dict(live_runner_overview)
    live_summary = _as_dict(live_runner.get("summary"))
    live_gate = _as_dict(live_runner.get("shadow_evidence_gate"))
    outcome_payload = _as_dict(outcome_reconciliation)
    outcome_artifact = _as_dict(outcome_payload.get("artifact")) if "artifact" in outcome_payload else outcome_payload
    outcome_summary = _as_dict(outcome_artifact.get("summary"))

    previous_summary = _as_dict(previous.get("summary"))
    cycles_completed = _safe_int(previous_summary.get("cycles_completed"), 0) + (1 if latest_cycle_decision is not None else 0)
    last_cycle_at = isoformat_z(now) if latest_cycle_decision is not None else previous_summary.get("last_cycle_at")
    next_collect_at = isoformat_z(now + timedelta(seconds=max(1, int(interval_seconds))))

    last_review_at = _parse_iso(previous_summary.get("last_operator_review_at"))
    if last_review_at is None:
        last_review_at = _parse_iso(previous.get("created_at")) or now
    next_review_dt = last_review_at + timedelta(hours=max(float(review_interval_hours or 0), 0.1))
    confirmation_due = now >= next_review_dt

    total_decisions = _safe_int(live_summary.get("total_decisions"), 0)
    candidate_decisions = _safe_int(live_summary.get("candidate_decisions"), 0)
    pending_outcomes = _safe_int(live_gate.get("pending_outcomes"), 0)
    resolved_outcomes = _safe_int(live_gate.get("resolved_outcomes"), 0)
    awaiting_label_replay = _safe_int(live_gate.get("awaiting_label_replay"), 0)
    worker_pending = _safe_int(outcome_summary.get("pending_outcomes"), 0)
    worker_resolved = _safe_int(outcome_summary.get("resolved_outcomes"), 0)
    live_order_submitted = bool(live_summary.get("live_order_submitted") or live_gate.get("live_order_submitted"))

    if live_order_submitted:
        status = "safety_violation_live_order_submitted"
        operator_message = "偵測到 live_order_submitted=true；請立即停止 daemon 並檢查 fail-closed guardrail。"
    elif confirmation_due:
        status = "operator_confirmation_due"
        operator_message = "shadow evidence daemon 已累積新資料；請檢查 pending/resolved outcome，不需要開真錢。"
    elif pending_outcomes or worker_pending:
        status = "collecting_pending_24h_outcomes"
        operator_message = "daemon 正在蒐集 shadow 候選；等待 24h label 對帳，不送單。"
    elif resolved_outcomes or worker_resolved:
        status = "collecting_resolved_evidence"
        operator_message = "daemon 已有 resolved shadow evidence；可用來判斷是否值得未來小額 canary，但目前仍不送單。"
    elif total_decisions > 0:
        status = "collecting_observation_decisions"
        operator_message = "daemon 正在記錄 HOLD / shadow 決策；目前尚無新的 24h 買賣 outcome。"
    else:
        status = "daemon_started_waiting_first_decision"
        operator_message = "daemon 已啟動，等待第一筆 shadow evidence decision。"

    latest_decision = _latest_decision_summary(live_runner)
    if latest_cycle_decision:
        latest_decision = {
            **latest_decision,
            "cycle_action": latest_cycle_decision.get("action"),
            "cycle_reason": latest_cycle_decision.get("reason"),
            "cycle_created_at": latest_cycle_decision.get("created_at"),
        }

    return {
        "schema_version": 1,
        "created_at": previous.get("created_at") or isoformat_z(now),
        "updated_at": isoformat_z(now),
        "status": status,
        "artifact_path": str(artifact_path),
        "log_path": str(log_path),
        "operator_message": operator_message,
        "operator_review": {
            "confirmation_due": confirmation_due,
            "review_interval_hours": float(review_interval_hours),
            "last_operator_review_at": previous_summary.get("last_operator_review_at"),
            "next_operator_review_at": isoformat_z(next_review_dt),
            "operator_action": "看 Dashboard 的 Shadow evidence 卡：確認 pending/resolved、最近 action、以及 live_order_submitted 必須為 false。",
        },
        "summary": {
            "cycles_completed": cycles_completed,
            "last_cycle_at": last_cycle_at,
            "last_operator_review_at": previous_summary.get("last_operator_review_at"),
            "next_collect_at": next_collect_at,
            "total_decisions": total_decisions,
            "candidate_decisions": candidate_decisions,
            "pending_outcomes": pending_outcomes + worker_pending,
            "resolved_outcomes": resolved_outcomes + worker_resolved,
            "awaiting_label_replay": awaiting_label_replay + _safe_int(outcome_summary.get("awaiting_label_replay"), 0),
            "jsonl_backed": bool(live_summary.get("jsonl_backed")),
            "daemon_interval_seconds": int(interval_seconds),
            "order_submission_enabled": False,
            "risk_on_order_enabled": False,
            "live_order_submitted": live_order_submitted,
        },
        "latest_decision": latest_decision,
        "evidence_sources": {
            "live_runner": {
                "status": live_runner.get("status"),
                "jsonl_root": live_runner.get("jsonl_root"),
                "latest_run_id": _as_dict(live_runner.get("latest_run")).get("run_id"),
                "latest_decision_id": _as_dict(live_runner.get("latest_decision")).get("decision_id"),
            },
            "outcome_reconciliation": {
                "status": outcome_artifact.get("status"),
                "artifact_path": outcome_payload.get("artifact_path"),
                "persisted": outcome_payload.get("persisted"),
            },
        },
        "guardrail": {
            "order_submission_enabled": False,
            "risk_on_order_enabled": False,
            "live_order_submitted": live_order_submitted,
            "blocked_live_actions": ["live_buy", "live_add", "automation_enable"],
            "safety_contract": "paper/shadow evidence only; no real orders are submitted by this daemon.",
        },
    }


def persist_shadow_evidence_daemon_artifact(
    artifact: Dict[str, Any],
    *,
    artifact_path: Path = SHADOW_EVIDENCE_DAEMON_ARTIFACT_PATH,
    log_path: Path = SHADOW_EVIDENCE_DAEMON_LOG_PATH,
) -> Dict[str, Any]:
    _persist_json(Path(artifact_path), artifact)
    _append_jsonl(Path(log_path), {
        "updated_at": artifact.get("updated_at"),
        "status": artifact.get("status"),
        "summary": artifact.get("summary"),
        "latest_decision": artifact.get("latest_decision"),
        "guardrail": artifact.get("guardrail"),
    })
    return artifact


def acknowledge_shadow_evidence_operator_review(
    *,
    artifact_path: Path = SHADOW_EVIDENCE_DAEMON_ARTIFACT_PATH,
    log_path: Path = SHADOW_EVIDENCE_DAEMON_LOG_PATH,
    now: Optional[datetime] = None,
    review_interval_hours: float = DEFAULT_OPERATOR_REVIEW_INTERVAL_HOURS,
) -> Dict[str, Any]:
    """Mark accumulated shadow evidence as reviewed by the operator.

    This is only an acknowledgement of paper/shadow evidence visibility.  It must
    not change any execution guardrail or enable live trading.
    """

    now = now or utc_now()
    loaded = load_shadow_evidence_daemon_artifact(artifact_path)
    artifact = {k: v for k, v in loaded.items() if k != "available"}
    if not isinstance(artifact.get("summary"), dict):
        artifact["summary"] = {}
    if not isinstance(artifact.get("operator_review"), dict):
        artifact["operator_review"] = {}
    if not isinstance(artifact.get("guardrail"), dict):
        artifact["guardrail"] = {}
    reviewed_at = isoformat_z(now)
    next_review_at = isoformat_z(now + timedelta(hours=max(float(review_interval_hours or 0), 0.1)))
    artifact["updated_at"] = reviewed_at
    artifact["status"] = "operator_review_acknowledged"
    artifact["operator_message"] = "使用者已確認目前 shadow evidence；daemon 會繼續蒐集，不送單。"
    artifact["summary"]["last_operator_review_at"] = reviewed_at
    artifact["summary"]["order_submission_enabled"] = False
    artifact["summary"]["risk_on_order_enabled"] = False
    artifact["summary"]["live_order_submitted"] = bool(artifact["guardrail"].get("live_order_submitted"))
    artifact["operator_review"].update({
        "confirmation_due": False,
        "review_interval_hours": float(review_interval_hours),
        "last_operator_review_at": reviewed_at,
        "next_operator_review_at": next_review_at,
        "operator_action": "已確認；下一步讓 daemon 繼續蒐集 pending/resolved shadow outcomes。",
    })
    artifact["guardrail"].update({
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
        "blocked_live_actions": ["live_buy", "live_add", "automation_enable"],
        "safety_contract": "paper/shadow evidence only; no real orders are submitted by this daemon.",
    })
    return persist_shadow_evidence_daemon_artifact(artifact, artifact_path=artifact_path, log_path=log_path)


def run_shadow_evidence_cycle(
    *,
    config: Dict[str, Any],
    session,
    status_payload: Optional[Dict[str, Any]] = None,
    run_id: str = DEFAULT_SHADOW_EVIDENCE_RUN_ID,
    collect_market: bool = True,
    preprocess: bool = True,
    refresh_model: bool = False,
    interval_seconds: int = DEFAULT_COLLECT_INTERVAL_SECONDS,
    review_interval_hours: float = DEFAULT_OPERATOR_REVIEW_INTERVAL_HOURS,
    artifact_path: Path = SHADOW_EVIDENCE_DAEMON_ARTIFACT_PATH,
    log_path: Path = SHADOW_EVIDENCE_DAEMON_LOG_PATH,
) -> Dict[str, Any]:
    """Run one fail-closed evidence collection tick and persist dashboard state."""

    runtime_cfg = shadow_evidence_runtime_config(config, interval_seconds=interval_seconds)
    previous = load_shadow_evidence_daemon_artifact(artifact_path)
    runner = LiveTradingRunner(runtime_cfg, session, run_id=run_id)
    runner.start_run(refresh_model=refresh_model)
    decision = runner.run_cycle(
        collect_market=collect_market,
        preprocess=preprocess,
        submit_orders=False,
    )
    live_runner_overview = build_live_runner_overview(session, status_payload=status_payload)
    outcome_reconciliation = build_paper_shadow_outcome_reconciliation(
        session,
        status_payload=status_payload,
        persist=True,
    )
    artifact = build_shadow_evidence_daemon_artifact(
        previous_artifact=previous,
        live_runner_overview=live_runner_overview,
        outcome_reconciliation=outcome_reconciliation,
        latest_cycle_decision=decision,
        interval_seconds=interval_seconds,
        review_interval_hours=review_interval_hours,
        artifact_path=artifact_path,
        log_path=log_path,
    )
    return persist_shadow_evidence_daemon_artifact(artifact, artifact_path=artifact_path, log_path=log_path)
