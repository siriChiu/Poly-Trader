from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from database.models import init_db
from execution.control_plane import WORKER_POLL_EVENT_TYPE, ensure_execution_control_plane_schema
from scripts.paper_shadow_outcome_reconciliation import (
    strict_failures,
    summarize_reconciliation_result,
)
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "paper_shadow_outcome_reconciliation.py"


def _pending_artifact() -> dict:
    return {
        "artifact_schema_version": 2,
        "status": "recording_pending_outcomes",
        "rehearsal_status": "pending_observation_window",
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
        "live_order_submitted": False,
        "worker_poll_events": 1,
        "pending_outcomes": 1,
        "resolved_outcomes": 0,
        "awaiting_label_replay": 0,
        "parity_blocked_events": 0,
        "can_poll_workers": False,
        "poll_blocked_by_pending_outcome": True,
        "next_reconcile_at": "2026-06-05T00:00:00Z",
        "pending_hours_remaining_min": 1.0,
        "resolution_due_count": 0,
        "reconciliation_due": False,
        "summary": {
            "worker_poll_events": 1,
            "pending_outcomes": 1,
            "resolved_outcomes": 0,
            "awaiting_label_replay": 0,
            "parity_blocked_events": 0,
            "live_order_submitted": False,
        },
        "rehearsal_proof": {
            "status": "pending_observation_window",
            "can_poll_workers": False,
            "poll_blocked_by_pending_outcome": True,
            "next_reconcile_at": "2026-06-05T00:00:00Z",
            "pending_hours_remaining_min": 1.0,
            "resolution_due_count": 0,
            "order_submission_enabled": False,
            "risk_on_order_enabled": False,
            "live_order_submitted": False,
        },
        "quick_read": {
            "status": "recording_pending_outcomes",
            "rehearsal_status": "pending_observation_window",
            "worker_poll_events": 1,
            "pending_outcomes": 1,
            "resolved_outcomes": 0,
            "awaiting_label_replay": 0,
            "parity_blocked_events": 0,
            "can_poll_workers": False,
            "poll_blocked_by_pending_outcome": True,
            "next_reconcile_at": "2026-06-05T00:00:00Z",
            "pending_hours_remaining_min": 1.0,
            "resolution_due_count": 0,
            "reconciliation_due": False,
            "order_submission_enabled": False,
            "risk_on_order_enabled": False,
            "live_order_submitted": False,
            "blocked_live_actions": ["live_buy", "live_add", "automation_enable"],
            "operator_message": "paper/shadow proof",
        },
        "entries": [
            {
                "order_submission_enabled": False,
                "risk_on_order_enabled": False,
                "live_order_submitted": False,
                "proposal": {"live_order_submitted": False},
            }
        ],
    }


def test_strict_summary_accepts_pending_fail_closed_artifact() -> None:
    artifact = _pending_artifact()

    result = {
        "artifact": artifact,
        "artifact_path": "data/paper_shadow_outcome_reconciliation.json",
        "persisted": True,
    }
    summary = summarize_reconciliation_result(result)

    assert strict_failures(artifact) == []
    assert summary["strict_ok"] is True
    assert summary["status"] == "recording_pending_outcomes"
    assert summary["rehearsal_status"] == "pending_observation_window"
    assert summary["pending_outcomes"] == 1
    assert summary["can_poll_workers"] is False
    assert summary["poll_blocked_by_pending_outcome"] is True


def test_strict_summary_rejects_quick_read_drift() -> None:
    artifact = _pending_artifact()
    artifact["quick_read"]["pending_outcomes"] = 0

    failures = strict_failures(artifact)

    assert "quick_read.pending_outcomes_mismatch" in failures


def test_strict_summary_rejects_any_live_or_risk_on_flag() -> None:
    artifact = _pending_artifact()
    artifact["entries"][0]["proposal"]["live_order_submitted"] = True
    artifact["rehearsal_proof"]["risk_on_order_enabled"] = True

    failures = strict_failures(artifact)

    assert "rehearsal_proof.risk_on_order_enabled_true" in failures
    assert "entries[0].proposal.live_order_submitted_true" in failures


def test_cli_persists_pending_reconciliation_from_local_db(tmp_path: Path) -> None:
    db_path = tmp_path / "paper_shadow.db"
    artifact_path = tmp_path / "paper_shadow_outcome_reconciliation.json"
    session = init_db(f"sqlite:///{db_path}")
    ensure_execution_control_plane_schema(session)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    run_id = "run-paper-shadow"
    session.execute(
        text(
            """
            INSERT INTO execution_runs (
                id, profile_id, label, symbol, venue, mode, state, control_mode,
                runtime_binding_status, start_time, worker_status, strategy_bundle_hash,
                last_event_type, last_event_at, created_at, updated_at
            ) VALUES (
                :id, :profile_id, :label, :symbol, :venue, :mode, :state, :control_mode,
                :runtime_binding_status, :start_time, :worker_status, :strategy_bundle_hash,
                :last_event_type, :last_event_at, :created_at, :updated_at
            )
            """
        ),
        {
            "id": run_id,
            "profile_id": "selective",
            "label": "paper shadow",
            "symbol": "BTCUSDT",
            "venue": "okx",
            "mode": "paper_shadow",
            "state": "running",
            "control_mode": "stateful_run_control_beta",
            "runtime_binding_status": "paper_shadow_runtime_blocked",
            "start_time": now,
            "worker_status": "paper_shadow_worker_polled",
            "strategy_bundle_hash": "bundle-hash",
            "last_event_type": WORKER_POLL_EVENT_TYPE,
            "last_event_at": now,
            "created_at": now,
            "updated_at": now,
        },
    )
    payload = {
        "order_proposal": {
            "generated_at": now,
            "symbol": "BTCUSDT",
            "side": "buy",
            "live_order_submitted": False,
        },
        "bundle_gate": {"status": "bundle_hash_match"},
    }
    session.execute(
        text(
            """
            INSERT INTO execution_run_events (
                run_id, profile_id, event_type, level, message, payload_json, created_at
            ) VALUES (
                :run_id, :profile_id, :event_type, :level, :message, :payload_json, :created_at
            )
            """
        ),
        {
            "run_id": run_id,
            "profile_id": "selective",
            "event_type": WORKER_POLL_EVENT_TYPE,
            "level": "info",
            "message": "paper shadow proposal",
            "payload_json": json.dumps(payload, ensure_ascii=False),
            "created_at": now,
        },
    )
    session.commit()
    session.close()

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--db-path",
            str(db_path),
            "--artifact-path",
            str(artifact_path),
            "--persist",
            "--strict",
            "--compact",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    summary = json.loads(result.stdout)
    assert summary["strict_ok"] is True
    assert summary["persisted"] is True
    assert summary["status"] == "recording_pending_outcomes"
    assert summary["rehearsal_status"] == "pending_observation_window"
    assert summary["pending_outcomes"] == 1
    assert summary["can_poll_workers"] is False
    assert summary["poll_blocked_by_pending_outcome"] is True
    assert summary["next_reconcile_at"]

    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["artifact_schema_version"] == 2
    assert artifact["pending_outcomes"] == 1
    assert artifact["resolved_outcomes"] == 0
    assert artifact["rehearsal_status"] == "pending_observation_window"
    assert artifact["next_reconcile_at"]
    assert artifact["quick_read"]["pending_outcomes"] == 1
    assert artifact["quick_read"]["rehearsal_status"] == "pending_observation_window"
    assert artifact["quick_read"]["order_submission_enabled"] is False
    assert artifact["quick_read"]["risk_on_order_enabled"] is False
    assert artifact["quick_read"]["live_order_submitted"] is False
    assert artifact["summary"]["pending_outcomes"] == 1
    assert artifact["rehearsal_proof"]["order_submission_enabled"] is False
    assert artifact["rehearsal_proof"]["risk_on_order_enabled"] is False
    assert artifact["rehearsal_proof"]["live_order_submitted"] is False
