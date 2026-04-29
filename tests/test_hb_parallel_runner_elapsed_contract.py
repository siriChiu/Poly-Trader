import json
from pathlib import Path

import pytest

from scripts import hb_parallel_runner


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "hb_parallel_runner.py"


@pytest.mark.parametrize(
    ("diagnostics", "expected_required", "expected_reason"),
    [
        ({}, True, "missing_leaderboard_probe_artifact"),
        ({"leaderboard_payload_stale": True, "leaderboard_payload_source": "latest_persisted_snapshot", "leaderboard_count": 6}, True, "stale_leaderboard_payload"),
        ({"leaderboard_payload_error": "cache read failed", "leaderboard_payload_source": "latest_persisted_snapshot", "leaderboard_count": 6}, True, "leaderboard_payload_error"),
        ({"leaderboard_payload_source": None, "leaderboard_payload_stale": False, "leaderboard_count": 6}, True, "missing_leaderboard_payload_source"),
        ({"leaderboard_payload_source": "live_rebuild", "leaderboard_payload_stale": False, "leaderboard_count": 6}, False, None),
    ],
)
def test_leaderboard_payload_fast_refresh_requirement(diagnostics, expected_required, expected_reason):
    required, reason = hb_parallel_runner._leaderboard_payload_fast_refresh_requirement(diagnostics)

    assert required is expected_required
    assert reason == expected_reason


def test_parallel_runner_elapsed_contract_uses_stable_run_baseline_and_total_run_summary():
    source = RUNNER.read_text(encoding="utf-8")
    assert 'run_start_monotonic = time.monotonic()' in source
    assert 'parallel_start = datetime.now()' in source
    assert 'parallel_start_monotonic = time.monotonic()' in source
    assert '"elapsed_seconds": round(time.monotonic() - run_start_monotonic, 1),' in source
    assert 'run_elapsed_seconds = round(time.monotonic() - run_start_monotonic, 1)' in source
    assert 'elapsed_seconds=run_elapsed_seconds,' in source
    assert 'elapsed=run_elapsed_seconds,' in source
    assert 'elapsed = (datetime.now() - parallel_start).total_seconds()' not in source
    assert '"elapsed_seconds": round(time.monotonic() - start_monotonic, 1),' not in source
    assert 'elapsed = (datetime.now() - start).total_seconds()' not in source


def test_main_parallel_progress_elapsed_never_moves_backwards(tmp_path, monkeypatch):
    class Args:
        fast = True
        hb = "elapsed-monotonic"
        no_collect = True
        no_train = True
        no_dw = True

    class FakeFuture:
        def __init__(self, payload):
            self._payload = payload

        def result(self):
            return self._payload

    class FakeExecutor:
        def __init__(self, *args, **kwargs):
            self._futures = {
                "full_ic": FakeFuture(("full_ic", True, "ok", "")),
                "regime_ic": FakeFuture(("regime_ic", True, "ok", "")),
            }

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def submit(self, fn, task):
            return self._futures[task["name"]]

    def _ok(stdout: str = ""):
        return {"attempted": True, "success": True, "returncode": 0, "stdout": stdout, "stderr": ""}

    wait_calls = {"count": 0}

    def _fake_wait(pending, timeout=None, return_when=None):
        wait_calls["count"] += 1
        pending_list = list(pending)
        by_name = {future.result()[0]: future for future in pending_list}
        if wait_calls["count"] == 1:
            return {by_name["full_ic"]}, {by_name["regime_ic"]}
        if wait_calls["count"] == 2:
            return set(), set(pending)
        return set(pending), set()

    progress_snapshots = []
    original_write_progress = hb_parallel_runner.write_progress

    def _capture_write_progress(*args, **kwargs):
        path = original_write_progress(*args, **kwargs)
        if len(args) >= 2 and args[1] == "parallel_tasks":
            payload = json.loads(Path(path).read_text())
            details = payload.get("details") or {}
            if "elapsed_seconds" in details:
                progress_snapshots.append(details["elapsed_seconds"])
        return path

    monotonic_values = iter([100.0, 130.0, 165.0, 165.0, 180.0, 180.0, 190.0, 190.0, 220.0])
    monkeypatch.setattr(hb_parallel_runner.time, "monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(hb_parallel_runner, "write_progress", _capture_write_progress)
    monkeypatch.setattr(
        hb_parallel_runner,
        "TASKS",
        [
            {"name": "full_ic", "label": "Full IC", "cmd": ["python", "scripts/full_ic.py"]},
            {"name": "regime_ic", "label": "Regime IC", "cmd": ["python", "scripts/regime_aware_ic.py"]},
        ],
    )
    monkeypatch.setattr(hb_parallel_runner, "parse_args", lambda argv=None: Args())
    monkeypatch.setattr(hb_parallel_runner, "resolve_run_label", lambda args: "elapsed-monotonic")
    monkeypatch.setattr(hb_parallel_runner, "run_collect_step", lambda skip=False: {"attempted": False, "success": True, "returncode": 0, "stdout": "", "stderr": ""})
    monkeypatch.setattr(
        hb_parallel_runner,
        "quick_counts",
        lambda: {
            "raw_market_data": 1,
            "features_normalized": 1,
            "labels": 1,
            "simulated_pyramid_win_rate": 0.5,
            "latest_raw_timestamp": "2026-04-15 00:00:00",
            "label_horizons": [],
        },
    )
    monkeypatch.setattr(hb_parallel_runner, "collect_source_blockers", lambda: {"blocked_count": 0, "counts_by_history_class": {}, "blocked_features": []})
    monkeypatch.setattr(hb_parallel_runner, "print_source_blockers", lambda payload: None)
    monkeypatch.setattr(hb_parallel_runner, "refresh_train_prerequisites", lambda needs_train: {})
    monkeypatch.setattr(hb_parallel_runner.concurrent.futures, "ProcessPoolExecutor", FakeExecutor)
    monkeypatch.setattr(hb_parallel_runner.concurrent.futures, "wait", _fake_wait)
    monkeypatch.setattr(hb_parallel_runner, "collect_ic_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_recent_drift_report", lambda: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_recent_drift_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_q35_scaling_audit", lambda: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_q35_scaling_audit_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_predict_probe", lambda: _ok("{}"))
    monkeypatch.setattr(hb_parallel_runner, "_persist_live_predictor_probe", lambda stdout: None)
    monkeypatch.setattr(hb_parallel_runner, "collect_live_predictor_diagnostics", lambda result=None: {})
    monkeypatch.setattr(hb_parallel_runner, "run_live_decision_quality_drilldown", lambda: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_live_decision_quality_drilldown_diagnostics", lambda result=None: {})
    monkeypatch.setattr(hb_parallel_runner, "run_circuit_breaker_audit", lambda run_label: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_circuit_breaker_audit_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_leaderboard_candidate_probe", lambda run_label=None: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_leaderboard_candidate_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_q15_support_audit", lambda: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_q15_support_audit_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_q15_bucket_root_cause", lambda: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_q15_bucket_root_cause_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_q15_boundary_replay", lambda: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_q15_boundary_replay_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_auto_propose", lambda run_label=None: _ok())
    monkeypatch.setattr(hb_parallel_runner, "overwrite_current_state_docs", lambda *args, **kwargs: {"success": True, "written_docs": [], "errors": []})
    monkeypatch.setattr(hb_parallel_runner, "collect_current_state_docs_sync_status", lambda: {"ok": True, "stale_docs": [], "reference_artifacts": []})

    hb_parallel_runner.main(["--fast", "--hb", "elapsed-monotonic"])

    assert progress_snapshots == sorted(progress_snapshots), progress_snapshots
