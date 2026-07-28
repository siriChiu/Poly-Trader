from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

from execution import control_plane


def _polled_row() -> dict:
    return {
        "id": "run-truth-1",
        "profile_id": "trend",
        "state": "running",
        "strategy_bundle_status": "persisted",
        "worker_status": "paper_shadow_worker_polled",
        "worker_control_json": json.dumps(
            {
                "status": "paper_shadow_worker_polled",
                "backend_worker_bound": True,
                "worker_kind": "backend_managed_state_poller",
                "backend_worker_pid": None,
                "last_poll_at": "2026-07-16T10:00:00Z",
                "poll_count": 1,
                "latest_order_proposal": {
                    "proposal_source": "exact_strategy_runtime",
                    "live_order_submitted": False,
                },
            }
        ),
    }


def test_manual_poll_is_not_reported_as_healthy_continuous_worker() -> None:
    row = _polled_row()
    worker = control_plane._worker_control_contract(row, "running")

    assert worker["legacy_backend_worker_bound"] is True
    assert worker["backend_worker_bound"] is False
    assert worker["poll_handler_available"] is False
    assert worker["continuous_worker"] is False
    assert worker["runtime_liveness"] == {
        "status": "not_continuously_running",
        "healthy": False,
        "pid": None,
        "pid_alive": None,
        "lease_status": "not_implemented",
        "heartbeat_status": "not_implemented",
        "last_poll_at": "2026-07-16T10:00:00Z",
    }


def test_running_row_serializes_as_manual_poll_control_state() -> None:
    payload = control_plane._serialize_run(_polled_row())

    assert payload["state"] == "running"
    assert payload["state_truth"] == "configured_manual_poll_not_continuous_worker"
    assert payload["state_label"] == "已啟用（手動輪詢，非長駐 worker）"
    assert payload["runtime_liveness"]["healthy"] is False
    assert payload["runtime_liveness"]["status"] == "not_continuously_running"


def test_continuous_worker_cannot_self_report_fake_liveness() -> None:
    row = _polled_row()
    stored = json.loads(row["worker_control_json"])
    stored.update(
        {
            "backend_worker_bound": True,
            "continuous_worker": True,
            "backend_worker_pid": 999999999,
            "pid_alive": True,
            "lease_owner": "fake-worker",
            "lease_epoch": "epoch-1",
            "lease_status": "active",
            "lease_expires_at": "2099-01-01T00:00:00Z",
            "heartbeat_status": "fresh",
            "heartbeat_at": "2000-01-01T00:00:00Z",
        }
    )
    row["worker_control_json"] = json.dumps(stored)

    worker = control_plane._worker_control_contract(row, "running")

    assert worker["backend_worker_bound"] is False
    assert worker["runtime_liveness"]["healthy"] is False
    assert worker["runtime_liveness"]["pid_alive"] is False
    assert worker["runtime_liveness"]["heartbeat_status"] == "stale"


def test_continuous_worker_requires_live_pid_fresh_heartbeat_and_active_lease() -> None:
    now = datetime.now(timezone.utc)
    row = _polled_row()
    stored = json.loads(row["worker_control_json"])
    stored.update(
        {
            "backend_worker_bound": True,
            "continuous_worker": True,
            "backend_worker_pid": os.getpid(),
            "lease_owner": "test-supervisor",
            "lease_epoch": "epoch-1",
            "lease_expires_at": (now + timedelta(minutes=2)).isoformat(),
            "heartbeat_at": now.isoformat(),
        }
    )
    row["worker_control_json"] = json.dumps(stored)

    worker = control_plane._worker_control_contract(row, "running")

    assert worker["backend_worker_bound"] is True
    assert worker["runtime_liveness"]["healthy"] is True
    assert worker["runtime_liveness"]["pid_alive"] is True
    assert worker["runtime_liveness"]["lease_status"] == "active"
    assert worker["runtime_liveness"]["heartbeat_status"] == "fresh"


def test_promotion_journey_is_partial_and_not_a_fake_three_of_five() -> None:
    worker = control_plane._worker_control_contract(_polled_row(), "running")
    promotion = control_plane._promotion_status_for_run(_polled_row(), worker)
    stages = {stage["key"]: stage for stage in promotion["stages"]}

    assert promotion["state"] == "paper_shadow_evidence_recorded"
    assert promotion["journey_contract_status"] == "partial_not_promotable"
    assert promotion["journey_complete"] is False
    assert promotion["progress_current"] == 3
    assert promotion["progress_target"] is None
    assert promotion["declared_stage_count"] == 5
    assert promotion["progress_is_release_metric"] is False
    assert stages["paper_shadow"]["status"] == "evidence_recorded"
    assert stages["outcome_24h"]["status"] == "reconciliation_required"
    assert stages["live_candidate"]["status"] == "not_implemented"
    assert promotion["safety"]["order_submission_enabled"] is False
    assert promotion["safety"]["risk_on_order_enabled"] is False
