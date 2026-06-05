import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "q15_exact_bucket_row_harvest_proof.py"
spec = importlib.util.spec_from_file_location("q15_exact_bucket_row_harvest_proof_test_module", MODULE_PATH)
proof = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(proof)


CURRENT_BUCKET = "BLOCK|bias200_below_min|q00"


def _row(idx, *, bucket=CURRENT_BUCKET, label="C", win=1):
    return {
        "timestamp": f"2026-06-{idx % 28 + 1:02d} {idx % 24:02d}:00:00",
        "symbol": "BTCUSDT",
        "regime_label": "bear",
        "regime_gate": "BLOCK",
        "entry_quality_label": label,
        "structure_bucket": bucket,
        "simulated_pyramid_win": win,
        "simulated_pyramid_pnl": 0.02 if win else -0.01,
        "simulated_pyramid_quality": 0.5 if win else -0.2,
        "simulated_pyramid_drawdown_penalty": 0.1 if win else 0.4,
        "simulated_pyramid_time_underwater": 0.2 if win else 0.8,
    }


def _identity():
    return {
        "target_col": "simulated_pyramid_win",
        "horizon_minutes": 1440,
        "current_live_structure_bucket": CURRENT_BUCKET,
        "regime_label": "bear",
        "regime_gate": "BLOCK",
        "entry_quality_label": "C",
        "calibration_window": 100,
        "bucket_semantic_signature": "live_structure_bucket:q15_support_identity:v2",
    }


def test_row_harvest_positive_delta_under_minimum_stays_fail_closed():
    exact_rows = [_row(i, win=1 if i % 3 == 0 else 0) for i in range(19)]
    non_bucket_identity_rows = [_row(i + 19, bucket="BLOCK|other|q00") for i in range(14)]
    unrelated_rows = [_row(i + 33, bucket="CAUTION|other|q35", label="B") for i in range(67)]

    report = proof.build_report(
        rows=exact_rows + non_bucket_identity_rows + unrelated_rows,
        support_identity=_identity(),
        probe={
            "generated_at": "2026-06-05T00:00:00Z",
            "support_progress": {
                "status": "semantic_rebaseline_under_minimum",
                "current_rows": 19,
                "previous_rows": 0,
                "delta_vs_previous": 19,
                "stagnant_run_count": 0,
                "semantic_signature_delta_vs_previous": 18,
                "regression_basis": "legacy_or_different_semantic_signature",
            },
        },
        q15_audit={"generated_at": "2026-06-05T00:01:00Z"},
        support_fill={
            "generated_at": "2026-06-05T00:02:00Z",
            "verdict": {
                "time_to_evidence_bucket": "within_week_if_exact_identity_keeps_accumulating",
                "missing_capability_class": "Signal/Support",
                "alternative_solution_required": True,
            },
        },
        generated_at="2026-06-05T00:03:00Z",
        minimum_support_rows=50,
    )

    verdict = report["verdict"]
    assert verdict["status"] == "exact_bucket_row_harvest_positive_delta_under_minimum"
    assert verdict["current_exact_bucket_rows"] == 19
    assert verdict["previous_rows"] == 0
    assert verdict["delta_vs_previous"] == 19
    assert verdict["gap_to_minimum"] == 31
    assert verdict["support_gate_ready"] is False
    assert verdict["primary_failed_gate"] == "current_live_support_gate"
    assert verdict["live_exposure_allowed"] is False
    assert verdict["order_submission_enabled"] is False
    assert verdict["time_to_evidence_bucket"] == "within_week_if_exact_identity_keeps_accumulating"

    assert report["harvest_window"]["exact_identity_rows"] == 33
    assert report["harvest_window"]["exact_bucket_rows"] == 19
    assert report["harvest_window"]["non_bucket_identity_rows"] == 14
    assert "enable_live_buy_or_add_from_row_harvest_proof_alone" in report["forbidden_shortcuts"]

    md = proof.markdown(report)
    assert "exact_bucket_row_harvest_positive_delta_under_minimum" in md
    assert "This artifact is not deployment clearance" in md


def test_row_harvest_support_ready_still_requires_remaining_live_gates():
    exact_rows = [_row(i, win=1) for i in range(55)]
    unrelated_rows = [_row(i + 55, bucket="BLOCK|other|q00") for i in range(45)]

    report = proof.build_report(
        rows=exact_rows + unrelated_rows,
        support_identity=_identity(),
        probe={
            "support_progress": {
                "current_rows": 55,
                "previous_rows": 45,
                "delta_vs_previous": 10,
                "stagnant_run_count": 0,
            },
        },
        generated_at="2026-06-05T00:03:00Z",
        minimum_support_rows=50,
    )

    verdict = report["verdict"]
    assert verdict["status"] == "exact_bucket_row_harvest_support_ready_remaining_gates"
    assert verdict["support_gate_ready"] is True
    assert verdict["current_exact_bucket_rows"] == 55
    assert verdict["gap_to_minimum"] == 0
    assert verdict["primary_failed_gate"] == "remaining_live_gates"
    assert verdict["deployable"] is False
    assert verdict["live_exposure_allowed"] is False
    assert "venue lifecycle proof passes" in report["promotion_requirements"][3]
