import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "q15_map_signal_redesign_proof.py"
spec = importlib.util.spec_from_file_location("q15_map_signal_redesign_proof_test_module", MODULE_PATH)
proof = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(proof)


CURRENT_BUCKET = "BLOCK|bias200_below_min|q15"
NEIGHBOR_BUCKET = "BLOCK|bear_bias200_hard_block|q00"


def _row(idx, *, bucket=CURRENT_BUCKET, label="C", win=1):
    return {
        "timestamp": f"2026-05-{idx % 28 + 1:02d} {idx % 24:02d}:00:00",
        "symbol": "BTCUSDT",
        "regime_label": "bear",
        "regime_gate": "BLOCK",
        "entry_quality_label": label,
        "structure_bucket": bucket,
        "simulated_pyramid_win": win,
        "simulated_pyramid_pnl": 0.02 if win else -0.01,
        "simulated_pyramid_quality": 0.6 if win else -0.25,
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


def _root_cause():
    return {
        "generated_at": "2026-06-05T00:00:00Z",
        "verdict": "same_lane_neighbor_bucket_dominates",
        "candidate_patch_type": "structure_component_scoring",
        "candidate_patch_feature": "feat_4h_bb_pct_b",
        "exact_live_lane": {
            "dominant_neighbor_bucket": NEIGHBOR_BUCKET,
            "dominant_neighbor_rows": 80,
            "near_boundary_rows": 9,
        },
    }


def test_map_signal_redesign_keeps_neighbor_reference_only_when_current_window_rejects_metrics():
    current_neighbor_losses = [_row(i, bucket=NEIGHBOR_BUCKET, win=0) for i in range(20)]
    current_other = [_row(i + 20, bucket="BLOCK|different|q00", win=0) for i in range(80)]
    older_neighbor_wins = [_row(i + 100, bucket=NEIGHBOR_BUCKET, win=1) for i in range(60)]

    report = proof.build_report(
        rows=current_neighbor_losses + current_other + older_neighbor_wins,
        support_identity=_identity(),
        q15_root_cause=_root_cause(),
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
    assert verdict["status"] == "map_signal_redesign_reference_only_current_window_rejected"
    assert verdict["selected_candidate_id"] == "dominant_neighbor_exact_lane"
    assert verdict["selected_target_bucket"] == NEIGHBOR_BUCKET
    assert verdict["selected_current_window_rows"] == 20
    assert verdict["selected_all_history_rows"] == 80
    assert verdict["primary_failed_gate"] == "current_window_metric_gate"
    assert verdict["deployable"] is False
    assert verdict["live_exposure_allowed"] is False
    assert verdict["order_submission_enabled"] is False

    candidate = next(item for item in report["candidate_matrix"] if item["id"] == "dominant_neighbor_exact_lane")
    assert candidate["status"] == "reference_candidate_current_window_metric_rejected"
    assert candidate["window_evaluations"]["100"]["metrics"]["win_rate"] == 0.0
    assert candidate["window_evaluations"]["all"]["metric_gate_candidate"] is True

    md = proof.markdown(report)
    assert "map_signal_redesign_reference_only_current_window_rejected" in md
    assert "This artifact is not deployment clearance" in md


def test_map_signal_redesign_current_window_candidate_requires_replay_not_live():
    current_neighbor_wins = [_row(i, bucket=NEIGHBOR_BUCKET, win=1) for i in range(65)]
    current_other = [_row(i + 65, bucket="BLOCK|different|q00", win=0) for i in range(35)]

    report = proof.build_report(
        rows=current_neighbor_wins + current_other,
        support_identity=_identity(),
        q15_root_cause=_root_cause(),
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
    assert verdict["status"] == "map_signal_candidate_requires_oos_replay_not_deployable"
    assert verdict["selected_candidate_id"] == "dominant_neighbor_exact_lane"
    assert verdict["selected_current_window_rows"] == 65
    assert verdict["selected_all_history_rows"] == 65
    assert verdict["primary_failed_gate"] == "oos_replay_required_before_live"
    assert verdict["deployable"] is False
    assert "enable_live_buy_or_add_from_map_signal_proof_alone" in report["forbidden_shortcuts"]
