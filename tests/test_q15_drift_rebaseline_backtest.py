import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "q15_drift_rebaseline_backtest.py"
spec = importlib.util.spec_from_file_location("q15_drift_rebaseline_backtest_test_module", MODULE_PATH)
drift = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(drift)


def _row(idx, *, regime="bear", gate="BLOCK", label="D", bucket="BLOCK|bias200_below_min|q15", win=1):
    return {
        "timestamp": f"2026-05-{idx % 28 + 1:02d} {idx % 24:02d}:00:00",
        "symbol": "BTCUSDT",
        "regime_label": regime,
        "regime_gate": gate,
        "entry_quality_label": label,
        "structure_bucket": bucket,
        "simulated_pyramid_win": win,
        "simulated_pyramid_pnl": 0.012 if win else -0.006,
        "simulated_pyramid_quality": 0.48 if win else 0.08,
        "simulated_pyramid_drawdown_penalty": 0.1 if win else 0.22,
        "simulated_pyramid_time_underwater": 0.2 if win else 0.5,
    }


def _identity():
    return {
        "target_col": "simulated_pyramid_win",
        "horizon_minutes": 1440,
        "current_live_structure_bucket": "BLOCK|bias200_below_min|q15",
        "regime_label": "bear",
        "regime_gate": "BLOCK",
        "entry_quality_label": "C",
        "calibration_window": 200,
        "bucket_semantic_signature": "live_structure_bucket:q15_support_identity:v2",
    }


def test_rebaseline_backtest_keeps_historical_candidate_reference_only_when_current_window_empty():
    current_window_non_bucket = [
        _row(i, label="C", bucket="BLOCK|different_bucket|q15", win=0)
        for i in range(200)
    ]
    older_semantic_candidate = [
        _row(i + 200, label="D", bucket="BLOCK|bias200_below_min|q15", win=1)
        for i in range(80)
    ]

    report = drift.build_report(
        rows=current_window_non_bucket + older_semantic_candidate,
        support_identity=_identity(),
        support_fill={
            "verdict": {
                "current_exact_bucket_rows": 0,
                "minimum_support_rows": 50,
                "gap_to_minimum": 50,
            }
        },
        generated_at="2026-06-05T00:00:00Z",
        minimum_support_rows=50,
    )

    verdict = report["verdict"]
    assert verdict["status"] == "reference_candidate_found_but_current_window_unproven"
    assert verdict["selected_candidate_id"] == "semantic_entry_quality_family"
    assert verdict["selected_current_window_rows"] == 0
    assert verdict["selected_all_history_rows"] == 80
    assert verdict["deployable"] is False
    assert verdict["live_exposure_allowed"] is False
    assert verdict["order_submission_enabled"] is False

    candidate = next(item for item in report["candidate_matrix"] if item["id"] == "semantic_entry_quality_family")
    assert candidate["status"] == "reference_candidate_current_window_empty"
    assert candidate["deployable_support"] is False
    assert candidate["window_evaluations"]["200"]["rows"] == 0
    assert candidate["window_evaluations"]["all"]["metric_gate_candidate"] is True

    md = drift.markdown(report)
    assert "reference_candidate_found_but_current_window_unproven" in md
    assert "live_exposure_allowed: **False**" in md
    assert "not deployment clearance" in md


def test_rebaseline_backtest_current_window_candidate_requires_replay_not_live():
    current_window_candidate = [
        _row(i, label="D", bucket="BLOCK|bias200_below_min|q15", win=1)
        for i in range(65)
    ]
    current_window_other = [
        _row(i + 65, label="C", bucket="BLOCK|different_bucket|q15", win=0)
        for i in range(135)
    ]

    report = drift.build_report(
        rows=current_window_candidate + current_window_other,
        support_identity=_identity(),
        support_fill={
            "verdict": {
                "current_exact_bucket_rows": 0,
                "minimum_support_rows": 50,
                "gap_to_minimum": 50,
            }
        },
        generated_at="2026-06-05T00:00:00Z",
        minimum_support_rows=50,
    )

    verdict = report["verdict"]
    assert verdict["status"] == "candidate_requires_oos_replay_not_deployable"
    assert verdict["selected_candidate_id"] == "semantic_entry_quality_family"
    assert verdict["selected_current_window_rows"] == 65
    assert verdict["deployable"] is False
    assert report["promotion_requirements"]
    assert "enable_live_buy_or_add_from_rebaseline_proof_alone" in report["forbidden_shortcuts"]
