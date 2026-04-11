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
    assert args.no_collect is False
    assert hb_parallel_runner.resolve_run_label(args) == "fast"


def test_parse_args_requires_hb_for_full_mode():
    try:
        hb_parallel_runner.parse_args([])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("Expected parser error when --hb missing in full mode")


def test_parse_collect_metadata_extracts_continuity_repair_json():
    payload = '{"inserted_total": 3, "bridge_inserted": 1, "used_bridge": true}'
    stdout = f"hello\nCONTINUITY_REPAIR_META: {payload}\nworld"

    parsed = hb_parallel_runner.parse_collect_metadata(stdout)

    assert parsed["inserted_total"] == 3
    assert parsed["bridge_inserted"] == 1
    assert parsed["used_bridge"] is True


def test_save_summary_uses_run_label_and_persists_source_blockers(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))

    counts = {"raw_market_data": 1, "features_normalized": 2, "labels": 3, "simulated_pyramid_win_rate": 0.5}
    collect_result = {
        "attempted": True,
        "success": True,
        "returncode": 0,
        "stdout": 'CONTINUITY_REPAIR_META: {"inserted_total": 2, "bridge_inserted": 1, "used_bridge": true}',
        "stderr": "",
    }
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
        collect_result,
        results,
        elapsed=1.2,
        fast_mode=True,
        ic_diagnostics={"global_pass": 13, "tw_pass": 10, "total_features": 30},
        drift_diagnostics={"primary_window": "100", "primary_alerts": ["regime_concentration"]},
        auto_propose_result={"attempted": True, "success": True, "returncode": 0, "stdout": "ok", "stderr": ""},
    )

    assert summary["heartbeat"] == "fast"
    assert summary["mode"] == "fast"
    assert summary["collect_result"]["success"] is True
    assert summary["collect_result"]["continuity_repair"]["bridge_inserted"] == 1
    assert summary["collect_result"]["continuity_repair"]["bridge_fallback_streak"] == 1
    assert summary["source_blockers"]["blocked_count"] == 1
    assert summary["ic_diagnostics"]["tw_pass"] == 10
    assert summary["drift_diagnostics"]["primary_window"] == "100"
    assert summary["auto_propose"]["success"] is True
    assert summary_path.endswith("heartbeat_fast_summary.json")

    saved = json.loads(Path(summary_path).read_text())
    assert saved["collect_result"]["attempted"] is True
    assert saved["collect_result"]["continuity_repair"]["used_bridge"] is True
    assert saved["source_blockers"]["blocked_features"][0]["key"] == "nest_pred"
    assert saved["ic_diagnostics"]["global_pass"] == 13
    assert saved["drift_diagnostics"]["primary_alerts"] == ["regime_concentration"]
    assert saved["auto_propose"]["stdout_preview"] == "ok"


def test_collect_recent_drift_diagnostics_reads_primary_window(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "recent_drift_report.json").write_text(
        json.dumps(
            {
                "target_col": "simulated_pyramid_win",
                "horizon_minutes": 1440,
                "full_sample": {"rows": 11134, "win_rate": 0.6459},
                "primary_window": {
                    "window": "100",
                    "alerts": ["regime_concentration"],
                    "summary": {
                        "rows": 100,
                        "win_rate": 0.93,
                        "win_rate_delta_vs_full": 0.2841,
                        "dominant_regime": "chop",
                        "dominant_regime_share": 0.97,
                    },
                },
            }
        )
    )

    diag = hb_parallel_runner.collect_recent_drift_diagnostics()

    assert diag["target_col"] == "simulated_pyramid_win"
    assert diag["primary_window"] == "100"
    assert diag["primary_summary"]["dominant_regime"] == "chop"
