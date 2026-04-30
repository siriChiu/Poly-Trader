import json

import pandas as pd
import pytest

from scripts import topk_walkforward_precision as topk


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
