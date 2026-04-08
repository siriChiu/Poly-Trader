import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hb_parallel_runner.py"
spec = importlib.util.spec_from_file_location("hb_parallel_runner_test_module", MODULE_PATH)
hb_parallel_runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(hb_parallel_runner)


def test_parse_args_allows_fast_without_hb():
    args = hb_parallel_runner.parse_args(["--fast"])

    assert args.fast is True
    assert hb_parallel_runner.resolve_run_label(args) == "fast"


def test_parse_args_requires_hb_for_full_mode():
    try:
        hb_parallel_runner.parse_args([])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("Expected parser error when --hb missing in full mode")


def test_save_summary_uses_run_label_and_persists_source_blockers(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))

    counts = {"raw_market_data": 1, "features_normalized": 2, "labels": 3, "simulated_pyramid_win_rate": 0.5}
    blockers = {
        "blocked_count": 1,
        "counts_by_history_class": {"snapshot_only": 1},
        "blocked_features": [{"key": "nest_pred", "history_class": "snapshot_only"}],
    }
    results = {"full_ic": {"success": True, "stdout": "ok", "stderr": ""}}

    summary, summary_path = hb_parallel_runner.save_summary(
        "fast",
        counts,
        blockers,
        results,
        elapsed=1.2,
        fast_mode=True,
    )

    assert summary["heartbeat"] == "fast"
    assert summary["mode"] == "fast"
    assert summary["source_blockers"]["blocked_count"] == 1
    assert summary_path.endswith("heartbeat_fast_summary.json")

    saved = json.loads(Path(summary_path).read_text())
    assert saved["source_blockers"]["blocked_features"][0]["key"] == "nest_pred"
