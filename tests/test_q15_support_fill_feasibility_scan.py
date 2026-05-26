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
    assert verdict["current_exact_identity_rows"] == 0
    assert verdict["current_exact_identity_non_bucket_rows"] == 0
    assert verdict["current_exact_bucket_rows"] == 0
    assert verdict["gap_to_minimum"] == 50
    assert verdict["can_historical_backfill_close_current_identity"] is False
    assert verdict["can_count_reference_windows_as_deployable"] is False
    assert verdict["best_reference_exact_bucket_rows"] == 60
    assert verdict["time_to_evidence_bucket"] == "semantic_rebaseline_review_required_before_reference_rows_count"
    assert verdict["missing_capability_class"] == "Constraint/Review"
    assert verdict["alternative_solution_required"] is True
    assert verdict["customer_safe_lane"] == "paper/shadow decision-support; no buy/add live exposure"
    assert len(verdict["alternative_solutions"]) >= 3
    assert verdict["alternative_solutions"][1]["id"] == "semantic_rebaseline_review"
    assert verdict["alternative_solutions"][1]["reference_window"] == "200"

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
    assert "current support-fill feasibility scan (q15/q35 compatibility)" in md
    assert "Scanned current support identity" in md
    assert "Scanned q15 support identity" not in md
    assert "semantic_window_gap_not_raw_backfill_gap" in md
    assert "current exact bucket rows (deployable support candidate)" in md
    assert "current exact identity rows before bucket filter" in md
    assert "PM delivery pressure" in md
    assert "semantic_rebaseline_review_required_before_reference_rows_count" in md
    assert "paper_shadow_decision_support_sleeve" in md
    assert "不能把它們直接補成 current deployment support rows" in md


def test_recommended_actions_use_current_calibration_window_and_under_minimum_copy():
    identity = {
        "target_col": "simulated_pyramid_win",
        "horizon_minutes": 1440,
        "current_live_structure_bucket": "CAUTION|bull_q15_bias50_watch|q15",
        "regime_label": "bull",
        "regime_gate": "CAUTION",
        "entry_quality_label": "C",
        "calibration_window": 200,
        "bucket_semantic_signature": scan.BUCKET_SEMANTIC_SIGNATURE,
    }
    exact_rows = [
        _row(
            i,
            regime="bull",
            gate="CAUTION",
            label="C",
            bucket="CAUTION|bull_q15_bias50_watch|q15",
            win=i % 2,
        )
        for i in range(38)
    ]
    non_matching_rows = [_row(i + 38, bucket="ALLOW|different|q65") for i in range(220)]

    report = scan.build_feasibility_report(
        rows=exact_rows + non_matching_rows,
        support_identity=identity,
        generated_at="2026-05-05T00:00:00+00:00",
        windows=(100, 200, 600),
        minimum_support_rows=50,
    )

    assert report["verdict"]["classification"] == "true_support_under_minimum"
    assert report["verdict"]["current_exact_identity_rows"] == 38
    assert report["verdict"]["current_exact_identity_non_bucket_rows"] == 0
    assert report["verdict"]["current_exact_bucket_rows"] == 38
    actions = {action["id"]: action for action in report["recommended_actions"]}
    collect_action = actions["collect_forward_exact_current_identity_rows"]
    assert collect_action["current_calibration_window"] == 200
    assert "current calibration_window=200" in collect_action["description"]
    assert "current calibration_window=100" not in collect_action["description"]
    assert "regime=bull" in collect_action["description"]
    assert "gate=CAUTION" in collect_action["description"]
    assert "entry_label=C" in collect_action["description"]
    assert "bucket=CAUTION|bull_q15_bias50_watch|q15" in collect_action["description"]

    keep_action = actions["keep_deployment_fail_closed"]
    assert "current support identity exact rows 38/50" in keep_action["description"]
    assert "unsupported_exact_live_structure_bucket" not in keep_action["description"]

    rebaseline_action = actions["semantic_rebaseline_if_using_older_windows"]
    assert "足量 rows" not in rebaseline_action["description"]
    assert rebaseline_action["reference_rows"] == 38

    md = scan.markdown(report)
    assert "current calibration_window=200" in md
    assert "current calibration_window=100" not in md
    assert "足量 rows" not in md


def test_recommended_actions_switch_to_remaining_gates_copy_when_current_support_ready():
    identity = {
        "target_col": "simulated_pyramid_win",
        "horizon_minutes": 1440,
        "current_live_structure_bucket": "CAUTION|base_caution_regime_or_bias|q15",
        "regime_label": "bear",
        "regime_gate": "CAUTION",
        "entry_quality_label": "C",
        "calibration_window": 200,
        "bucket_semantic_signature": scan.BUCKET_SEMANTIC_SIGNATURE,
    }
    exact_rows = [
        _row(
            i,
            regime="bear",
            gate="CAUTION",
            label="C",
            bucket="CAUTION|base_caution_regime_or_bias|q15",
            win=1,
        )
        for i in range(67)
    ]
    non_matching_rows = [_row(i + 67, bucket="ALLOW|different|q65") for i in range(160)]

    report = scan.build_feasibility_report(
        rows=exact_rows + non_matching_rows,
        support_identity=identity,
        generated_at="2026-05-22T09:03:59+00:00",
        windows=(100, 200, 600),
        minimum_support_rows=50,
    )

    verdict = report["verdict"]
    assert verdict["classification"] == "current_identity_support_ready"
    assert verdict["current_exact_bucket_rows"] == 67
    assert verdict["gap_to_minimum"] == 0
    assert verdict["time_to_evidence_bucket"] == "ready_for_remaining_live_execution_gates"
    assert verdict["engineering_next_gate"].startswith("exact current support rows 67/50 already meet minimum")
    assert "must reach minimum" not in verdict["engineering_next_gate"]

    actions = {action["id"]: action for action in report["recommended_actions"]}
    keep_action = actions["keep_deployment_fail_closed"]
    assert "current support identity exact rows 67/50 已達門檻" in keep_action["description"]
    assert "未達門檻前" not in keep_action["description"]
    assert "support gate 不是 deployment closure" in keep_action["description"]
    assert keep_action["rows_needed"] == 0
    collect_action = actions["collect_forward_exact_current_identity_rows"]
    assert "維持 >= 50" in collect_action["success_condition"]

    md = scan.markdown(report)
    assert "current support identity exact rows 67/50 已達門檻" in md
    assert "must reach minimum" not in md
    assert "support gate 不是 deployment closure" in md


def test_current_window_reports_identity_rows_that_do_not_match_current_bucket():
    identity = {
        "target_col": "simulated_pyramid_win",
        "horizon_minutes": 1440,
        "current_live_structure_bucket": "CAUTION|base_caution_regime_or_bias|q00",
        "regime_label": "bear",
        "regime_gate": "CAUTION",
        "entry_quality_label": "C",
        "calibration_window": 20,
        "bucket_semantic_signature": scan.BUCKET_SEMANTIC_SIGNATURE,
    }
    current_bucket = [
        _row(0, regime="bear", gate="CAUTION", label="C", bucket="CAUTION|base_caution_regime_or_bias|q00")
    ]
    same_identity_wrong_bucket = [
        _row(
            i + 1,
            regime="bear",
            gate="CAUTION",
            label="C",
            bucket="CAUTION|base_caution_regime_or_bias|q15",
        )
        for i in range(12)
    ]
    non_matching_rows = [_row(i + 13, bucket="ALLOW|different|q65") for i in range(30)]

    report = scan.build_feasibility_report(
        rows=current_bucket + same_identity_wrong_bucket + non_matching_rows,
        support_identity=identity,
        generated_at="2026-05-23T00:00:00+08:00",
        windows=(20,),
        minimum_support_rows=50,
    )

    verdict = report["verdict"]
    assert verdict["current_exact_bucket_rows"] == 1
    assert verdict["current_exact_identity_rows"] == 13
    assert verdict["current_exact_identity_non_bucket_rows"] == 12
    assert verdict["gap_to_minimum"] == 49

    md = scan.markdown(report)
    assert "current exact bucket rows (deployable support candidate): **1/50**" in md
    assert "current exact identity rows before bucket filter: **13**" in md
    assert "non-current-bucket: **12**" in md
    assert "reference only, not deployment support" in md


def test_support_identity_compression_proof_selects_rebaseline_candidate_without_deploying():
    identity = {
        "target_col": "simulated_pyramid_win",
        "horizon_minutes": 1440,
        "current_live_structure_bucket": "CAUTION|base_caution_regime_or_bias|q15",
        "regime_label": "chop",
        "regime_gate": "CAUTION",
        "entry_quality_label": "D",
        "calibration_window": 20,
        "bucket_semantic_signature": scan.BUCKET_SEMANTIC_SIGNATURE,
    }
    current_exact_rows = [
        _row(i, regime="chop", gate="CAUTION", label="D", bucket="CAUTION|base_caution_regime_or_bias|q15", win=1)
        for i in range(7)
    ]
    current_non_matching = [_row(i + 7, bucket="ALLOW|different|q65", win=0) for i in range(13)]
    older_exact_rows = [
        _row(i + 20, regime="chop", gate="CAUTION", label="D", bucket="CAUTION|base_caution_regime_or_bias|q15", win=1)
        for i in range(60)
    ]

    report = scan.build_feasibility_report(
        rows=current_exact_rows + current_non_matching + older_exact_rows,
        support_identity=identity,
        generated_at="2026-05-26T07:00:00+00:00",
        windows=(20, 80),
        minimum_support_rows=50,
    )

    proof = report["support_identity_compression_proof"]
    assert proof["anti_treadmill"] is True
    assert proof["decision"] == "candidate_found_not_deployable"
    assert proof["selected_candidate_id"] == "rebaseline_calibration_window_only"
    assert proof["selected_candidate_rows"] == 67
    assert proof["live_exposure_allowed"] is False
    candidates = {candidate["id"]: candidate for candidate in proof["candidates"]}
    assert candidates["current_exact_identity_window"]["rows"] == 7
    assert candidates["current_exact_identity_window"]["ready_by_count"] is False
    assert candidates["rebaseline_calibration_window_only"]["ready_by_count"] is True
    assert candidates["rebaseline_calibration_window_only"]["deployable_support"] is False
    assert "rerun replay/OOS/Top-K" in proof["promotion_requirements"][0]
    assert "enable_live_buy_or_add_from_this proof alone" in proof["forbidden_shortcuts"]

    actions = {action["id"]: action for action in report["recommended_actions"]}
    assert actions["support_identity_compression_proof"]["selected_candidate_id"] == "rebaseline_calibration_window_only"
    assert actions["support_identity_compression_proof"]["live_exposure_allowed"] is False

    md = scan.markdown(report)
    assert "## Support identity compression proof" in md
    assert "candidate_found_not_deployable" in md
    assert "buy/add remains fail-closed" in md
