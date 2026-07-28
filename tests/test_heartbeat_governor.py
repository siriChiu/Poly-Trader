from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.heartbeat_governor import evaluate


UTC_NOW = datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc)


def _write_json(root: Path, relative: str, payload: dict) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _seed_truth(root: Path, *, micro_status: str = "blocked_missing_source") -> None:
    _write_json(
        root,
        "data/live_predict_probe.json",
        {
            "generated_at": "2026-07-17T11:55:00Z",
            "current_live_structure_bucket": "CAUTION|q15",
            "deployment_blocker": "unsupported_exact_live_structure_bucket",
            "current_live_structure_bucket_rows": 0,
            "minimum_support_rows": 50,
            "support_progress": {"current_rows": 0, "previous_rows": 0, "delta_vs_previous": 0, "stagnant_run_count": 2},
            "signal": "HOLD",
            "should_trade": False,
        },
    )
    _write_json(
        root,
        "data/microstructure_contract.json",
        {
            "generated_at": "2026-07-17T11:55:00Z",
            "status": micro_status,
            "source": {"freshness_status": "missing" if micro_status != "ready" else "fresh"},
        },
    )
    _write_json(root, "data/execution_metadata_smoke.json", {"runtime_ready": False})
    _write_json(root, "data/paper_shadow_outcome_reconciliation.json", {"summary": {"pending_count": 0}})
    _write_json(root, "data/high_conviction_topk_oos_matrix.json", {"deployable_rows": 0})


def test_governor_forces_external_branch_when_signature_repeats(tmp_path: Path) -> None:
    _seed_truth(tmp_path)
    state_path = tmp_path / "state.json"
    first = evaluate(tmp_path, state_path, now=UTC_NOW)
    assert first["brief"]["forced_execution_required"] is True
    state_path.write_text(json.dumps(first["state"]), encoding="utf-8")
    second = evaluate(tmp_path, state_path, now=UTC_NOW)

    brief = second["brief"]
    assert brief["anti_self_certification"] == "active"
    assert brief["agent_may_not_self_certify"] is True
    assert brief["same_semantic_signature"] is True
    assert brief["repeat_count"] == 1
    assert brief["forced_execution_required"] is True
    assert brief["selected_forced_branch"] == "map_signal_redesign"
    assert brief["required_evidence"]


def test_governor_does_not_treat_missing_microstructure_as_zero_edge(tmp_path: Path) -> None:
    _seed_truth(tmp_path)
    result = evaluate(tmp_path, tmp_path / "state.json", now=UTC_NOW)
    truth = result["brief"]["truth"]

    assert result["brief"]["selected_forced_branch"] == "map_signal_redesign"
    assert truth["microstructure_status"] == "blocked_missing_source"
    assert truth["microstructure_source_status"] == "missing"
    assert result["brief"]["agent_may_not_self_certify"] is True
