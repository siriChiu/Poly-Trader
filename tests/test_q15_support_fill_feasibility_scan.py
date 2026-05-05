import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "q15_support_fill_feasibility_scan.py"
spec = importlib.util.spec_from_file_location("q15_support_fill_feasibility_scan_test_module", MODULE_PATH)
scan = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(scan)


def _row(idx, *, regime="chop", gate="ALLOW", label="A", bucket="ALLOW|ok|q65", win=1):
    return {
        "timestamp": f"2026-05-04 {idx:02d}:00:00",
        "symbol": "BTCUSDT",
        "regime_label": regime,
        "regime_gate": gate,
        "entry_quality_label": label,
        "structure_bucket": bucket,
        "simulated_pyramid_win": win,
        "simulated_pyramid_pnl": 0.01 if win else -0.01,
        "simulated_pyramid_quality": 0.5 if win else 0.1,
        "simulated_pyramid_drawdown_penalty": 0.02,
        "simulated_pyramid_time_underwater": 0.1,
    }


def test_feasibility_scan_separates_reference_window_rows_from_current_identity():
    identity = {
        "target_col": "simulated_pyramid_win",
        "horizon_minutes": 1440,
        "current_live_structure_bucket": "BLOCK|bull_q15_bias50_overextended_block|q15",
        "regime_label": "bull",
        "regime_gate": "BLOCK",
        "entry_quality_label": "D",
        "calibration_window": 100,
        "bucket_semantic_signature": scan.BUCKET_SEMANTIC_SIGNATURE,
    }
    recent_non_matching = [_row(i) for i in range(100)]
    older_exact_bucket = [
        _row(
            i,
            regime="bull",
            gate="BLOCK",
            label="D",
            bucket="BLOCK|bull_q15_bias50_overextended_block|q15",
            win=i % 2,
        )
        for i in range(60)
    ]

    report = scan.build_feasibility_report(
        rows=recent_non_matching + older_exact_bucket,
        support_identity=identity,
        generated_at="2026-05-05T00:00:00+00:00",
        windows=(100, 200),
        minimum_support_rows=50,
    )

    verdict = report["verdict"]
    assert verdict["classification"] == "semantic_window_gap_not_raw_backfill_gap"
    assert verdict["current_exact_bucket_rows"] == 0
    assert verdict["gap_to_minimum"] == 50
    assert verdict["can_historical_backfill_close_current_identity"] is False
    assert verdict["can_count_reference_windows_as_deployable"] is False
    assert verdict["best_reference_exact_bucket_rows"] == 60

    current_window = report["window_scan"]["100"]
    assert current_window["evidence_role"] == "current_support_identity"
    assert current_window["exact_bucket_rows"] == 0
    assert current_window["deployment_promotable_under_current_identity"] is False

    reference_window = report["window_scan"]["200"]
    assert reference_window["support_ready_by_count"] is True
    assert reference_window["evidence_role"] == "reference_only_calibration_window_mismatch"
    assert reference_window["semantic_mismatched_fields_vs_current"] == ["calibration_window"]
    assert reference_window["deployment_promotable_under_current_identity"] is False

    md = scan.markdown(report)
    assert "semantic_window_gap_not_raw_backfill_gap" in md
    assert "不能把它們直接補成 current deployment support rows" in md
