from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "paper_shadow_outcome_api_consistency_probe.py"


def _proof(
    *,
    pending_outcomes: int = 1,
    next_reconcile_at: str = "2026-06-04T09:54:57Z",
    generated_at: str = "2026-06-04T08:00:00Z",
    pending_hours_remaining_min: float = 1.8,
) -> dict:
    summary = {
        "worker_poll_events": 1,
        "pending_outcomes": pending_outcomes,
        "resolved_outcomes": 0,
        "awaiting_label_replay": 0,
        "parity_blocked_events": 0,
        "live_order_submitted": False,
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
    }
    rehearsal_proof = {
        "status": "pending_observation_window",
        "can_poll_workers": False,
        "poll_blocked_by_pending_outcome": True,
        "next_reconcile_at": next_reconcile_at,
        "resolution_due_count": 0,
        "reconciliation_due": False,
        "pending_hours_remaining_min": pending_hours_remaining_min,
        "live_order_submitted": False,
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
    }
    stable_fields = {
        "artifact_schema_version": 2,
        "status": "recording_pending_outcomes",
        "rehearsal_status": rehearsal_proof["status"],
        "worker_poll_events": summary["worker_poll_events"],
        "pending_outcomes": pending_outcomes,
        "resolved_outcomes": summary["resolved_outcomes"],
        "awaiting_label_replay": summary["awaiting_label_replay"],
        "parity_blocked_events": summary["parity_blocked_events"],
        "can_poll_workers": rehearsal_proof["can_poll_workers"],
        "poll_blocked_by_pending_outcome": rehearsal_proof["poll_blocked_by_pending_outcome"],
        "next_reconcile_at": next_reconcile_at,
        "resolution_due_count": rehearsal_proof["resolution_due_count"],
        "reconciliation_due": rehearsal_proof["reconciliation_due"],
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
        "live_order_submitted": False,
    }
    return {
        "artifact": "paper_shadow_outcome_reconciliation",
        "generated_at": generated_at,
        "pending_hours_remaining_min": pending_hours_remaining_min,
        **stable_fields,
        "summary": summary,
        "rehearsal_proof": rehearsal_proof,
        "quick_read": dict(stable_fields),
        "entries": [
            {
                "event_id": "paper-shadow-1",
                "proposal": {
                    "symbol": "BTCUSDT",
                    "live_order_submitted": False,
                },
            }
        ],
    }


def _overview_payload(proof: dict) -> dict:
    return {"paper_shadow_outcome_reconciliation": proof}


def _run(args: list[str], *, input_payload: dict | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=json.dumps(input_payload) if input_payload is not None else None,
        text=True,
        capture_output=True,
        cwd=PROJECT_ROOT,
    )


def test_probe_passes_when_api_and_artifact_match_stable_schema_v2_fields(tmp_path: Path) -> None:
    overview_proof = _proof(generated_at="2026-06-04T08:01:00Z", pending_hours_remaining_min=1.79)
    artifact_proof = _proof(generated_at="2026-06-04T08:00:00Z", pending_hours_remaining_min=1.88)
    overview_file = tmp_path / "execution_overview.json"
    artifact_file = tmp_path / "paper_shadow_outcome_reconciliation.json"
    overview_file.write_text(json.dumps(_overview_payload(overview_proof)), encoding="utf-8")
    artifact_file.write_text(json.dumps(artifact_proof), encoding="utf-8")

    result = _run(
        [
            "--overview-file",
            str(overview_file),
            "--artifact-file",
            str(artifact_file),
            "--strict",
            "--compact",
        ]
    )

    assert result.returncode == 0, result.stderr + result.stdout
    summary = json.loads(result.stdout)
    assert summary["strict_ok"] is True
    assert summary["api_consistent"] is True
    assert summary["quick_read_consistent"] is True
    assert summary["schema_v2"] is True
    assert summary["fail_closed"] is True
    assert summary["pending_guard_ok"] is True
    assert summary["secret_safe"] is True


def test_probe_fails_strict_when_quick_read_drifts_from_nested_proof() -> None:
    proof = _proof()
    overview_proof = _proof()
    overview_proof["quick_read"] = dict(overview_proof["quick_read"], pending_outcomes=99)

    result = _run(
        ["--strict"],
        input_payload={
            "execution_overview": _overview_payload(overview_proof),
            "artifact": proof,
        },
    )

    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert summary["strict_ok"] is False
    assert summary["quick_read_consistent"] is False
    assert any(
        item["source"] == "overview" and item["field"] == "pending_outcomes"
        for item in summary["quick_read_mismatches"]
    )


def test_probe_fails_strict_when_fail_closed_flags_open_live_order_path() -> None:
    overview_proof = _proof()
    artifact_proof = _proof()
    artifact_proof["entries"][0]["proposal"]["live_order_submitted"] = True

    result = _run(
        ["--strict"],
        input_payload={
            "execution_overview": _overview_payload(overview_proof),
            "artifact": artifact_proof,
        },
    )

    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert summary["strict_ok"] is False
    assert summary["artifact_fail_closed"] is False
    assert summary["fail_closed"] is False


def test_probe_fails_strict_when_api_and_artifact_stable_fields_diverge() -> None:
    overview_proof = _proof(next_reconcile_at="2026-06-04T09:54:57Z")
    artifact_proof = _proof(next_reconcile_at="2026-06-04T10:54:57Z")

    result = _run(
        ["--strict"],
        input_payload={
            "execution_overview": _overview_payload(overview_proof),
            "artifact": artifact_proof,
        },
    )

    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert summary["strict_ok"] is False
    assert summary["api_consistent"] is False
    assert any(
        item["field"] == "next_reconcile_at"
        and item["overview"] == "2026-06-04T09:54:57Z"
        and item["artifact"] == "2026-06-04T10:54:57Z"
        for item in summary["overview_artifact_mismatches"]
    )


def test_probe_fails_strict_when_payload_contains_secret_like_key_without_value_leak() -> None:
    overview_proof = _proof()
    artifact_proof = _proof()
    overview_proof["worker_context"] = {"api_key": "should_not_be_printed"}

    result = _run(
        ["--strict"],
        input_payload={
            "execution_overview": _overview_payload(overview_proof),
            "artifact": artifact_proof,
        },
    )

    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert summary["strict_ok"] is False
    assert summary["secret_safe"] is False
    assert "overview.worker_context.api_key" in summary["secret_like_key_paths"]
    assert "should_not_be_printed" not in result.stdout


def test_probe_fails_strict_when_pending_outcome_lacks_poll_guard() -> None:
    overview_proof = _proof()
    artifact_proof = _proof()
    overview_proof["can_poll_workers"] = True
    overview_proof["quick_read"] = dict(overview_proof["quick_read"], can_poll_workers=True)

    result = _run(
        ["--strict"],
        input_payload={
            "execution_overview": _overview_payload(overview_proof),
            "artifact": artifact_proof,
        },
    )

    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert summary["strict_ok"] is False
    assert summary["overview_pending_guard_ok"] is False
    assert summary["pending_guard_ok"] is False
