import json
import runpy
import sys
from pathlib import Path

import pandas as pd
import pytest

from scripts import topk_walkforward_precision as topk


def test_artifact_freshness_fields_are_machine_readable_deployment_gate():
    fresh = topk.artifact_freshness_fields(
        "2026-05-02T02:00:00+00:00",
        now=topk.datetime(2026, 5, 2, 2, 30, tzinfo=topk.timezone.utc),
    )
    stale = topk.artifact_freshness_fields(
        "2026-05-02T02:00:00+00:00",
        now=topk.datetime(2026, 5, 2, 3, 30, tzinfo=topk.timezone.utc),
    )

    assert fresh["artifact_freshness_status"] == "fresh"
    assert fresh["artifact_deployment_blocking"] is False
    assert fresh["artifact_stale_after_minutes"] == 60.0
    assert stale["artifact_freshness_status"] == "stale"
    assert stale["artifact_freshness_reason"] == "artifact_older_than_policy"
    assert stale["artifact_deployment_blocking"] is True


def test_direct_script_execution_bootstraps_project_root(monkeypatch, tmp_path):
    script_path = Path(topk.__file__).resolve()
    project_root = script_path.parent.parent
    scripts_dir = script_path.parent
    filtered_paths = []
    for entry in sys.path:
        if not entry:
            continue
        try:
            resolved = Path(entry).resolve()
        except Exception:
            filtered_paths.append(entry)
            continue
        if resolved in {project_root, scripts_dir}:
            continue
        filtered_paths.append(entry)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "path", [str(scripts_dir), *filtered_paths])

    runpy.run_path(str(script_path), run_name="__topk_bootstrap_test__")

    assert sys.path[0] == str(project_root)


def test_summarize_subset_includes_oos_roi_profit_factor_and_drawdown():
    subset = pd.DataFrame(
        {
            "timestamp": pd.to_datetime([
                "2026-01-01T00:00:00Z",
                "2026-01-02T00:00:00Z",
                "2026-01-03T00:00:00Z",
            ]),
            "simulated_pyramid_win": [1, 0, 1],
            "simulated_pyramid_pnl": [0.05, -0.02, 0.04],
            "score": [0.91, 0.88, 0.84],
            "regime_label": ["bull", "bull", "chop"],
        }
    )

    summary = topk.summarize_subset(subset, "simulated_pyramid_win")

    assert summary["trade_count"] == 3
    assert summary["oos_roi"] == pytest.approx(0.07)
    assert summary["profit_factor"] == pytest.approx(4.5)
    assert summary["max_drawdown"] == pytest.approx(0.02)
    assert summary["regime_mix"] == {"bull": 2, "chop": 1}


def test_build_high_conviction_oos_matrix_keeps_current_live_blocker_fail_closed():
    passing_metrics = {
        "trade_count": 80,
        "n": 80,
        "win_rate": 0.64,
        "oos_roi": 0.18,
        "profit_factor": 1.8,
        "max_drawdown": 0.05,
        "avg_score": 0.82,
        "wins": 51,
        "losses": 29,
        "regime_mix": {"bull": 80},
    }
    report = {
        "folds": [
            {"fold": 0, "top_slices": {"top_1pct": {**passing_metrics, "oos_roi": 0.05}}},
            {"fold": 1, "top_slices": {"top_1pct": {**passing_metrics, "oos_roi": 0.04}}},
        ],
        "aggregate_top_slices": {"top_1pct": passing_metrics},
        "aggregate_regime_top_slices": {},
    }

    rows = topk.build_high_conviction_oos_matrix_rows(
        "catboost",
        report,
        support_context={
            "support_route_verdict": "exact_bucket_unsupported_block",
            "support_governance_route": "no_support_proxy",
            "deployment_blocker": "circuit_breaker_active",
            "current_live_structure_bucket": "CAUTION|base_caution_regime_or_bias|q35",
            "current_live_structure_bucket_rows": 0,
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 50,
            "allowed_layers": 0,
            "signal": "HOLD",
            "source_live_probe_generated_at": "2026-04-30T05:28:04Z",
            "release_condition": {
                "release_ready": False,
                "recent_window": 25,
                "current_recent_window_wins": 5,
                "required_recent_window_wins": 13,
                "additional_recent_window_wins_needed": 8,
                "current_recent_window_win_rate": 0.2,
            },
            "release_ready": False,
            "recent_window": 25,
            "current_recent_window_wins": 5,
            "required_recent_window_wins": 13,
            "additional_recent_window_wins_needed": 8,
        },
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["model"] == "catboost"
    assert row["feature_profile"] == "current_full"
    assert row["regime"] == "all"
    assert row["top_k"] == "top_1pct"
    assert row["oos_roi"] == pytest.approx(0.18)
    assert row["worst_fold"] == pytest.approx(0.04)
    assert row["support_route"] == "exact_bucket_unsupported_block"
    assert row["support_governance_route"] == "no_support_proxy"
    assert row["deployment_blocker"] == "circuit_breaker_active"
    assert row["current_live_structure_bucket_rows"] == 0
    assert row["minimum_support_rows"] == 50
    assert row["current_live_structure_bucket_gap_to_minimum"] == 50
    assert row["allowed_layers"] == 0
    assert row["signal"] == "HOLD"
    assert row["source_live_probe_generated_at"] == "2026-04-30T05:28:04Z"
    assert row["release_condition"]["release_ready"] is False
    assert row["release_ready"] is False
    assert row["recent_window"] == 25
    assert row["current_recent_window_wins"] == 5
    assert row["required_recent_window_wins"] == 13
    assert row["additional_recent_window_wins_needed"] == 8
    assert row["deployable_verdict"] == "not_deployable"
    assert "support_route_not_deployable" in row["gate_failures"]
    assert "deployment_blocker_active" in row["gate_failures"]


def test_build_high_conviction_oos_matrix_marks_nearest_deployable_runtime_blocked_candidates():
    passing_metrics = {
        "trade_count": 146,
        "n": 146,
        "win_rate": 0.78,
        "oos_roi": 1.72,
        "profit_factor": 7.9,
        "max_drawdown": 0.069,
        "avg_score": 0.78,
        "wins": 114,
        "losses": 32,
        "regime_mix": {"bull": 146},
    }
    report = {
        "folds": [
            {"fold": 0, "top_slices": {"top_5pct": {**passing_metrics, "oos_roi": 0.14}}},
            {"fold": 1, "top_slices": {"top_5pct": {**passing_metrics, "oos_roi": 0.09}}},
        ],
        "aggregate_top_slices": {"top_5pct": passing_metrics},
        "aggregate_regime_top_slices": {},
    }

    rows = topk.build_high_conviction_oos_matrix_rows(
        "random_forest",
        report,
        support_context={
            "support_route_verdict": "exact_bucket_unsupported_block",
            "support_route_deployable": False,
            "deployment_blocker": "unsupported_exact_live_structure_bucket",
        },
    )

    row = rows[0]
    assert row["deployable_verdict"] == "not_deployable"
    assert row["oos_gate_passed"] is True
    assert row["blocked_only_by_live_guardrails"] is True
    assert row["model_gate_failures"] == []
    assert row["live_gate_failures"] == ["support_route_not_deployable", "deployment_blocker_active"]
    assert row["deployment_candidate_tier"] == "runtime_blocked_oos_pass"


def test_build_high_conviction_oos_matrix_treats_string_false_support_deployable_as_blocked():
    passing_metrics = {
        "trade_count": 80,
        "n": 80,
        "win_rate": 0.67,
        "oos_roi": 0.21,
        "profit_factor": 2.2,
        "max_drawdown": 0.03,
        "avg_score": 0.86,
        "wins": 54,
        "losses": 26,
        "regime_mix": {"bull": 80},
    }
    report = {
        "folds": [
            {"fold": 0, "top_slices": {"top_2pct": {**passing_metrics, "oos_roi": 0.08}}},
            {"fold": 1, "top_slices": {"top_2pct": {**passing_metrics, "oos_roi": 0.06}}},
        ],
        "aggregate_top_slices": {"top_2pct": passing_metrics},
        "aggregate_regime_top_slices": {},
    }

    rows = topk.build_high_conviction_oos_matrix_rows(
        "logistic_regression",
        report,
        support_context={
            "support_route_verdict": "exact_bucket_supported",
            "support_route_deployable": "false",
            "deployment_blocker": None,
        },
    )

    row = rows[0]
    assert row["oos_gate_passed"] is True
    assert row["deployable_verdict"] == "not_deployable"
    assert row["deployment_candidate_tier"] == "runtime_blocked_oos_pass"
    assert row["live_gate_failures"] == ["support_route_not_deployable"]
    assert row["model_gate_failures"] == []


def test_build_high_conviction_oos_matrix_release_not_ready_blocks_otherwise_deployable_row():
    passing_metrics = {
        "trade_count": 80,
        "n": 80,
        "win_rate": 0.67,
        "oos_roi": 0.21,
        "profit_factor": 2.2,
        "max_drawdown": 0.03,
        "avg_score": 0.86,
        "wins": 54,
        "losses": 26,
        "regime_mix": {"bull": 80},
    }
    report = {
        "folds": [
            {"fold": 0, "top_slices": {"top_2pct": {**passing_metrics, "oos_roi": 0.08}}},
            {"fold": 1, "top_slices": {"top_2pct": {**passing_metrics, "oos_roi": 0.06}}},
        ],
        "aggregate_top_slices": {"top_2pct": passing_metrics},
        "aggregate_regime_top_slices": {},
    }

    rows = topk.build_high_conviction_oos_matrix_rows(
        "logistic_regression",
        report,
        support_context={
            "support_route_verdict": "exact_bucket_supported",
            "support_route_deployable": True,
            "deployment_blocker": None,
            "runtime_closure_state": "breaker_clear",
            "release_ready": False,
            "release_condition": {
                "release_ready": False,
                "recent_window": 50,
                "current_recent_window_wins": 11,
                "required_recent_window_wins": 15,
                "additional_recent_window_wins_needed": 4,
            },
        },
    )

    row = rows[0]
    assert row["oos_gate_passed"] is True
    assert row["deployable_verdict"] == "not_deployable"
    assert row["deployment_candidate_tier"] == "runtime_blocked_oos_pass"
    assert row["gate_failures"] == ["breaker_release_not_ready"]
    assert row["live_gate_failures"] == ["breaker_release_not_ready"]
    assert row["model_gate_failures"] == []
    assert row["blocked_only_by_live_guardrails"] is True


def test_load_support_context_preserves_current_live_support_progress(monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "live_predict_probe.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-30T05:28:04.465304Z",
                "current_live_structure_bucket": "BLOCK|structure_quality_block|q00",
                "support_route_verdict": "exact_bucket_unsupported_block",
                "support_governance_route": "no_support_proxy",
                "deployment_blocker": "unsupported_exact_live_structure_bucket",
                "runtime_closure_state": "patch_inactive_or_blocked",
                "allowed_layers": 0,
                "signal": "HOLD",
                "support_progress": {
                    "current_rows": 0,
                    "minimum_support_rows": 50,
                    "gap_to_minimum": 50,
                },
                "deployment_blocker_details": {
                    "support_progress": {
                        "status": "regressed_under_minimum",
                        "reason": "semantic_support_rebaseline",
                        "regression_basis": "current_identity",
                        "stagnant_run_count": 4,
                        "stalled_support_accumulation": True,
                        "escalate_to_blocker": True,
                        "delta_vs_previous": -43,
                        "previous_rows": 50,
                        "gap_to_minimum": 43,
                    },
                    "release_condition": {
                        "release_ready": False,
                        "recent_window": 50,
                        "current_recent_window_wins": 9,
                        "required_recent_window_wins": 25,
                        "additional_recent_window_wins_needed": 16,
                        "current_recent_window_win_rate": 0.18,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    context = topk._load_support_context()

    assert context["current_live_structure_bucket"] == "BLOCK|structure_quality_block|q00"
    assert context["support_route_verdict"] == "exact_bucket_unsupported_block"
    assert context["support_governance_route"] == "no_support_proxy"
    assert context["deployment_blocker"] == "unsupported_exact_live_structure_bucket"
    assert context["current_live_structure_bucket_rows"] == 0
    assert context["minimum_support_rows"] == 50
    assert context["current_live_structure_bucket_gap_to_minimum"] == 50
    assert context["allowed_layers"] == 0
    assert context["signal"] == "HOLD"
    assert context["source_live_probe_generated_at"] == "2026-04-30T05:28:04.465304Z"
    assert context["live_truth_source_artifact"] == "data/live_predict_probe.json"
    assert context["release_condition"]["release_ready"] is False
    assert context["release_ready"] is False
    assert context["recent_window"] == 50
    assert context["current_recent_window_wins"] == 9
    assert context["required_recent_window_wins"] == 25
    assert context["additional_recent_window_wins_needed"] == 16
    assert context["current_recent_window_win_rate"] == pytest.approx(0.18)
    assert context["support_progress_status"] == "regressed_under_minimum"
    assert context["support_progress_reason"] == "semantic_support_rebaseline"
    assert context["support_progress_regression_basis"] == "current_identity"
    assert context["support_progress_stagnant_run_count"] == 4
    assert context["support_progress_stalled_support_accumulation"] is True
    assert context["support_progress_escalate_to_blocker"] is True
    assert context["support_delta_vs_previous"] == -43
    assert context["support_previous_rows"] == 50
    assert context["support_rows_needed"] == 50
    assert context["stagnant_run_count"] == 4
    assert context["stalled_support_accumulation"] is True
    assert context["escalate_to_blocker"] is True

    rows = topk.build_high_conviction_oos_matrix_rows(
        "catboost",
        {
            "folds": [
                {"fold": 0, "top_slices": {"top_1pct": {"trade_count": 80, "n": 80, "win_rate": 0.66, "oos_roi": 0.04, "profit_factor": 2.0, "max_drawdown": 0.03}}},
                {"fold": 1, "top_slices": {"top_1pct": {"trade_count": 80, "n": 80, "win_rate": 0.65, "oos_roi": 0.03, "profit_factor": 1.9, "max_drawdown": 0.04}}},
            ],
            "aggregate_top_slices": {
                "top_1pct": {"trade_count": 80, "n": 80, "win_rate": 0.66, "oos_roi": 0.11, "profit_factor": 2.0, "max_drawdown": 0.04, "wins": 53, "losses": 27}
            },
            "aggregate_regime_top_slices": {},
        },
        support_context=context,
    )
    row = rows[0]
    assert row["support_progress_status"] == "regressed_under_minimum"
    assert row["support_progress_reason"] == "semantic_support_rebaseline"
    assert row["support_progress_regression_basis"] == "current_identity"
    assert row["support_delta_vs_previous"] == -43
    assert row["support_previous_rows"] == 50
    assert row["support_rows_needed"] == 50
    assert row["stagnant_run_count"] == 4
    assert row["stalled_support_accumulation"] is True
    assert row["deployable_verdict"] == "not_deployable"
    assert "support_route_not_deployable" in row["live_gate_failures"]


def test_coalesce_regime_label_handles_merge_suffixes():
    frame = pd.DataFrame(
        {
            "regime_label_x": ["bull", None],
            "regime_label_y": [None, "chop"],
        }
    )

    coalesced = topk._coalesce_regime_label(frame)

    assert list(coalesced["regime_label"]) == ["bull", "chop"]
    assert "regime_label_x" not in coalesced.columns
    assert "regime_label_y" not in coalesced.columns


def test_apply_top_level_live_gate_summary_exposes_breaker_release_math():
    result = {
        "generated_at": "2026-05-16T02:03:09+00:00",
        "support_context": {},
        "rows": [],
    }
    support_context = {
        "support_route_verdict": "exact_bucket_present_but_below_minimum",
        "support_governance_route": "exact_live_bucket_present_but_below_minimum",
        "deployment_blocker": "circuit_breaker_active",
        "runtime_closure_state": "circuit_breaker_active",
        "current_live_structure_bucket": "BLOCK|structure_quality_block|q00",
        "current_live_structure_bucket_rows": 10,
        "minimum_support_rows": 50,
        "current_live_structure_bucket_gap_to_minimum": 40,
        "release_condition": {
            "release_ready": False,
            "recent_window": 50,
            "current_recent_window_wins": 14,
            "required_recent_window_wins": 15,
            "additional_recent_window_wins_needed": 1,
            "current_recent_window_win_rate": 0.28,
        },
        "release_ready": False,
        "current_streak": 36,
        "recent_window": 50,
        "current_recent_window_win_rate": 0.28,
        "current_recent_window_wins": 14,
        "required_recent_window_wins": 15,
        "additional_recent_window_wins_needed": 1,
        "support_progress_status": "regressed_under_minimum",
        "support_progress_regression_basis": "current_identity",
        "support_progress_stagnant_run_count": 2,
        "support_progress_stalled_support_accumulation": False,
        "support_delta_vs_previous": -7,
        "support_previous_rows": 17,
        "support_rows_needed": 40,
        "source_live_probe_generated_at": "2026-05-16T02:02:18Z",
        "live_truth_source_artifact": "data/live_predict_probe.json",
    }

    topk.apply_top_level_live_gate_summary(result, support_context)

    assert result["deployment_blocker"] == "circuit_breaker_active"
    assert result["runtime_closure_state"] == "circuit_breaker_active"
    assert result["support_route_verdict"] == "exact_bucket_present_but_below_minimum"
    assert result["current_live_structure_bucket"] == "BLOCK|structure_quality_block|q00"
    assert result["current_live_structure_bucket_rows"] == 10
    assert result["minimum_support_rows"] == 50
    assert result["current_live_structure_bucket_gap_to_minimum"] == 40
    assert result["release_condition"]["release_ready"] is False
    assert result["release_ready"] is False
    assert result["current_streak"] == 36
    assert result["recent_window"] == 50
    assert result["current_recent_window_win_rate"] == pytest.approx(0.28)
    assert result["current_recent_window_wins"] == 14
    assert result["required_recent_window_wins"] == 15
    assert result["additional_recent_window_wins_needed"] == 1
    assert result["support_progress_status"] == "regressed_under_minimum"
    assert result["support_progress_regression_basis"] == "current_identity"
    assert result["support_delta_vs_previous"] == -7
    assert result["support_previous_rows"] == 17
    assert result["support_rows_needed"] == 40
    assert result["source_live_probe_generated_at"] == "2026-05-16T02:02:18Z"
    assert result["live_truth_source_artifact"] == "data/live_predict_probe.json"
    assert result["live_gate_summary"]["additional_recent_window_wins_needed"] == 1
    assert result["live_gate_summary"]["support_progress_status"] == "regressed_under_minimum"
    assert result["live_gate_summary"]["support_rows_needed"] == 40


def test_apply_top_level_candidate_summary_surfaces_runtime_blocked_rows_fail_closed():
    result = {
        "rows": [
            {
                "model": "xgboost",
                "feature_profile": "current_full",
                "regime": "all",
                "top_k": "top_5pct",
                "oos_roi": 1.9,
                "win_rate": 0.79,
                "profit_factor": 9.1,
                "max_drawdown": 0.10,
                "worst_fold": -0.26,
                "trade_count": 146,
                "deployable_verdict": "not_deployable",
                "gate_failures": [
                    "max_drawdown_too_high",
                    "worst_fold_negative",
                    "support_route_not_deployable",
                    "deployment_blocker_active",
                ],
            },
            {
                "model": "random_forest",
                "feature_profile": "current_full_no_bull_collapse_4h",
                "regime": "all",
                "top_k": "top_5pct",
                "oos_roi": 1.2,
                "win_rate": 0.68,
                "profit_factor": 2.4,
                "max_drawdown": 0.04,
                "worst_fold": 0.03,
                "trade_count": 88,
                "deployable_verdict": "not_deployable",
                "gate_failures": ["support_route_not_deployable", "deployment_blocker_active", "breaker_release_not_ready"],
                "support_route": "exact_bucket_present_but_below_minimum",
                "deployment_blocker": "circuit_breaker_active",
                "runtime_closure_state": "circuit_breaker_active",
                "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
                "current_live_structure_bucket_rows": 21,
                "minimum_support_rows": 50,
                "current_live_structure_bucket_gap_to_minimum": 29,
                "release_ready": False,
                "recent_window": 50,
                "current_recent_window_wins": 0,
                "required_recent_window_wins": 15,
                "additional_recent_window_wins_needed": 15,
                "support_rows_needed": 29,
            },
        ]
    }

    topk.apply_top_level_candidate_summary(result)

    assert result["nearest_deployable_candidate"]["model"] == "random_forest"
    assert result["nearest_deployable_candidate"]["deployable_verdict"] == "not_deployable"
    assert result["nearest_deployable_candidate"]["deployment_candidate_tier"] == "runtime_blocked_oos_pass"
    assert result["nearest_deployable_candidate"]["oos_gate_passed"] is True
    assert result["nearest_deployable_candidate"]["blocked_only_by_live_guardrails"] is True
    assert result["nearest_deployable_candidate"]["deployment_blocker"] == "circuit_breaker_active"
    assert result["nearest_deployable_candidate"]["release_ready"] is False
    assert result["nearest_deployable_candidate"]["additional_recent_window_wins_needed"] == 15
    assert result["nearest_deployable_candidate"]["current_live_structure_bucket_rows"] == 21
    assert result["nearest_deployable_candidate"]["support_rows_needed"] == 29
    assert result["nearest_deployable_rows"][0] == result["nearest_deployable_candidate"]
    assert result["best_not_deployable"] == result["nearest_deployable_candidate"]
    assert result["highest_roi_not_deployable"]["model"] == "xgboost"
    assert result["highest_roi_not_deployable"]["deployment_candidate_tier"] == "research_oos_gate_failed"
