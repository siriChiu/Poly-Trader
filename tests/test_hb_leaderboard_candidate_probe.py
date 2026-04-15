import importlib.util
import json
import warnings
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hb_leaderboard_candidate_probe.py"
spec = importlib.util.spec_from_file_location("hb_leaderboard_candidate_probe_test_module", MODULE_PATH)
hb_leaderboard_candidate_probe = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(hb_leaderboard_candidate_probe)


def test_build_alignment_surfaces_support_governance_route(tmp_path, monkeypatch):
    last_metrics = tmp_path / "last_metrics.json"
    live_probe = tmp_path / "live_predict_probe.json"
    bull_pocket = tmp_path / "bull_4h_pocket_ablation.json"
    feature_ablation = tmp_path / "feature_group_ablation.json"

    last_metrics.write_text(
        json.dumps(
            {
                "feature_profile": "core_plus_macro",
                "feature_profile_meta": {
                    "source": "bull_4h_pocket_ablation.support_aware_profile",
                    "support_cohort": "bull_supported_neighbor_buckets_proxy",
                    "support_rows": 84,
                    "exact_live_bucket_rows": 0,
                },
            }
        ),
        encoding="utf-8",
    )
    live_probe.write_text(
        json.dumps(
            {
                "regime_gate": "ALLOW",
                "entry_quality_label": "D",
                "execution_guardrail_reason": "unsupported_exact_live_structure_bucket_blocks_trade",
            }
        ),
        encoding="utf-8",
    )
    bull_pocket.write_text(
        json.dumps(
            {
                "live_context": {
                    "current_live_structure_bucket": "ALLOW|base_allow|q65",
                    "current_live_structure_bucket_rows": 0,
                    "supported_neighbor_buckets": ["ALLOW|base_allow|q85"],
                },
                "support_pathology_summary": {
                    "minimum_support_rows": 50,
                    "exact_bucket_root_cause": "same_lane_exists_but_q65_missing",
                    "blocker_state": "exact_live_bucket_proxy_ready_but_exact_missing",
                    "proxy_boundary_verdict": "proxy_too_wide_vs_exact_bucket",
                    "proxy_boundary_reason": "proxy 邊界過寬",
                    "exact_lane_bucket_verdict": "no_exact_lane_rows",
                    "exact_lane_toxic_bucket": {},
                },
                "cohorts": {
                    "bull_supported_neighbor_buckets_proxy": {
                        "rows": 12,
                        "recommended_profile": None,
                    },
                    "bull_exact_live_lane_proxy": {
                        "rows": 50,
                        "recommended_profile": "core_plus_macro",
                    },
                    "bull_live_exact_lane_bucket_proxy": {
                        "rows": 38,
                        "recommended_profile": "core_plus_macro",
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    feature_ablation.write_text(
        json.dumps({"recommended_profile": "core_only"}),
        encoding="utf-8",
    )

    monkeypatch.setattr(hb_leaderboard_candidate_probe, "LAST_METRICS_PATH", last_metrics)
    monkeypatch.setattr(hb_leaderboard_candidate_probe, "LIVE_PROBE_PATH", live_probe)
    monkeypatch.setattr(hb_leaderboard_candidate_probe, "BULL_POCKET_PATH", bull_pocket)
    monkeypatch.setattr(hb_leaderboard_candidate_probe, "FEATURE_ABLATION_PATH", feature_ablation)

    alignment = hb_leaderboard_candidate_probe._build_alignment(
        {
            "selected_feature_profile": "core_only",
            "selected_feature_profile_source": "feature_group_ablation.recommended_profile",
            "feature_profile_candidate_diagnostics": [
                {
                    "feature_profile": "core_plus_macro",
                    "feature_profile_source": "bull_4h_pocket_ablation.support_aware_profile",
                    "support_cohort": "bull_supported_neighbor_buckets_proxy",
                    "support_rows": 84,
                    "exact_live_bucket_rows": 0,
                    "blocker_applied": True,
                    "blocker_reason": "unsupported_exact_live_structure_bucket",
                }
            ],
        }
    )

    assert alignment["dual_profile_state"] == "leaderboard_global_winner_vs_train_support_fallback"
    assert alignment["bull_exact_live_lane_proxy_profile"] == "core_plus_macro"
    assert alignment["bull_exact_live_lane_proxy_rows"] == 50
    assert alignment["bull_live_exact_bucket_proxy_profile"] == "core_plus_macro"
    assert alignment["bull_live_exact_bucket_proxy_rows"] == 38
    assert alignment["minimum_support_rows"] == 50
    assert alignment["live_current_structure_bucket_gap_to_minimum"] == 50
    assert alignment["exact_bucket_root_cause"] == "same_lane_exists_but_q65_missing"
    assert alignment["support_blocker_state"] == "exact_live_bucket_proxy_ready_but_exact_missing"
    assert alignment["proxy_boundary_verdict"] == "proxy_too_wide_vs_exact_bucket"
    assert alignment["proxy_boundary_reason"] == "proxy 邊界過寬"
    assert alignment["exact_lane_bucket_verdict"] == "no_exact_lane_rows"
    assert alignment["exact_lane_toxic_bucket"] == {}
    assert alignment["support_governance_route"] == "exact_live_bucket_proxy_available"
    assert alignment["governance_contract"]["verdict"] == "dual_role_governance_active"
    assert alignment["governance_contract"]["treat_as_parity_blocker"] is False
    assert alignment["governance_contract"]["current_closure"] == "global_ranking_vs_support_aware_production_split"



def test_build_alignment_marks_under_supported_exact_bucket(tmp_path, monkeypatch):
    last_metrics = tmp_path / "last_metrics.json"
    live_probe = tmp_path / "live_predict_probe.json"
    bull_pocket = tmp_path / "bull_4h_pocket_ablation.json"
    feature_ablation = tmp_path / "feature_group_ablation.json"

    last_metrics.write_text(json.dumps({"feature_profile": "core_plus_macro"}), encoding="utf-8")
    live_probe.write_text(
        json.dumps(
            {
                "regime_gate": "CAUTION",
                "entry_quality_label": "D",
                "execution_guardrail_reason": "decision_quality_below_trade_floor",
            }
        ),
        encoding="utf-8",
    )
    bull_pocket.write_text(
        json.dumps(
            {
                "live_context": {
                    "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
                    "current_live_structure_bucket_rows": 5,
                    "supported_neighbor_buckets": ["CAUTION|base_caution_regime_or_bias|q15"],
                },
                "support_pathology_summary": {
                    "minimum_support_rows": 50,
                    "exact_bucket_root_cause": "exact_bucket_present_but_below_minimum",
                    "blocker_state": "exact_lane_proxy_fallback_only",
                    "proxy_boundary_verdict": "proxy_governance_reference_only_exact_support_blocked",
                    "proxy_boundary_reason": "historical same-bucket proxy 可保留作 governance 參考，但 current live structure bucket 仍低於 minimum support；在 exact support 補滿前，proxy 不得當成 deployment 放行依據。",
                    "exact_lane_bucket_verdict": "toxic_sub_bucket_identified",
                    "exact_lane_toxic_bucket": {"bucket": "CAUTION|structure_quality_caution|q15"},
                },
                "cohorts": {
                    "bull_supported_neighbor_buckets_proxy": {
                        "rows": 84,
                        "recommended_profile": "core_plus_macro",
                    },
                    "bull_exact_live_lane_proxy": {
                        "rows": 311,
                        "recommended_profile": "core_plus_macro",
                    },
                    "bull_live_exact_lane_bucket_proxy": {
                        "rows": 52,
                        "recommended_profile": None,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    feature_ablation.write_text(
        json.dumps({"recommended_profile": "core_only"}),
        encoding="utf-8",
    )

    monkeypatch.setattr(hb_leaderboard_candidate_probe, "LAST_METRICS_PATH", last_metrics)
    monkeypatch.setattr(hb_leaderboard_candidate_probe, "LIVE_PROBE_PATH", live_probe)
    monkeypatch.setattr(hb_leaderboard_candidate_probe, "BULL_POCKET_PATH", bull_pocket)
    monkeypatch.setattr(hb_leaderboard_candidate_probe, "FEATURE_ABLATION_PATH", feature_ablation)

    alignment = hb_leaderboard_candidate_probe._build_alignment(
        {
            "selected_feature_profile": "core_plus_macro",
            "selected_feature_profile_source": "bull_4h_pocket_ablation.support_aware_profile",
            "feature_profile_candidate_diagnostics": [],
        }
    )

    assert alignment["minimum_support_rows"] == 50
    assert alignment["live_current_structure_bucket_gap_to_minimum"] == 45
    assert alignment["exact_bucket_root_cause"] == "exact_bucket_present_but_below_minimum"
    assert alignment["support_blocker_state"] == "exact_lane_proxy_fallback_only"
    assert alignment["proxy_boundary_verdict"] == "proxy_governance_reference_only_exact_support_blocked"
    assert alignment["exact_lane_bucket_verdict"] == "toxic_sub_bucket_identified"
    assert alignment["exact_lane_toxic_bucket"] == {"bucket": "CAUTION|structure_quality_caution|q15"}
    assert alignment["support_governance_route"] == "exact_live_bucket_present_but_below_minimum"



def test_build_alignment_marks_stale_alignment_snapshot_when_train_is_newer(tmp_path, monkeypatch):
    last_metrics = tmp_path / "last_metrics.json"
    live_probe = tmp_path / "live_predict_probe.json"
    bull_pocket = tmp_path / "bull_4h_pocket_ablation.json"
    feature_ablation = tmp_path / "feature_group_ablation.json"

    last_metrics.write_text(
        json.dumps(
            {
                "feature_profile": "core_plus_macro_plus_4h_structure_shift",
                "trained_at": "2026-04-14T19:59:42Z",
                "feature_profile_meta": {
                    "source": "bull_4h_pocket_ablation.exact_supported_profile",
                    "support_cohort": "bull_all",
                    "support_rows": 759,
                    "exact_live_bucket_rows": 85,
                },
            }
        ),
        encoding="utf-8",
    )
    live_probe.write_text(
        json.dumps(
            {
                "regime_gate": "CAUTION",
                "entry_quality_label": "D",
                "execution_guardrail_reason": None,
            }
        ),
        encoding="utf-8",
    )
    bull_pocket.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-14 19:39:13",
                "live_context": {
                    "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
                    "current_live_structure_bucket_rows": 85,
                    "supported_neighbor_buckets": ["CAUTION|structure_quality_caution|q15"],
                },
                "support_pathology_summary": {
                    "minimum_support_rows": 50,
                    "exact_bucket_root_cause": "exact_bucket_supported",
                    "blocker_state": "exact_live_bucket_supported",
                    "proxy_boundary_verdict": "exact_bucket_supported_proxy_not_required",
                    "proxy_boundary_reason": "current live structure bucket 已達 minimum support；後續治理與驗證應直接以 exact bucket 為主，proxy 只保留輔助比較，不再作 blocker 判讀。",
                    "exact_lane_bucket_verdict": "toxic_sub_bucket_identified",
                    "exact_lane_toxic_bucket": {"bucket": "CAUTION|structure_quality_caution|q15"},
                },
                "cohorts": {
                    "bull_supported_neighbor_buckets_proxy": {
                        "rows": 84,
                        "recommended_profile": "core_plus_macro",
                    },
                    "bull_exact_live_lane_proxy": {
                        "rows": 392,
                        "recommended_profile": "core_plus_macro",
                    },
                    "bull_live_exact_lane_bucket_proxy": {
                        "rows": 129,
                        "recommended_profile": None,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    feature_ablation.write_text(
        json.dumps({"recommended_profile": "core_only", "generated_at": "2026-04-14 19:39:11"}),
        encoding="utf-8",
    )

    monkeypatch.setattr(hb_leaderboard_candidate_probe, "LAST_METRICS_PATH", last_metrics)
    monkeypatch.setattr(hb_leaderboard_candidate_probe, "LIVE_PROBE_PATH", live_probe)
    monkeypatch.setattr(hb_leaderboard_candidate_probe, "BULL_POCKET_PATH", bull_pocket)
    monkeypatch.setattr(hb_leaderboard_candidate_probe, "FEATURE_ABLATION_PATH", feature_ablation)

    alignment = hb_leaderboard_candidate_probe._build_alignment(
        {
            "selected_feature_profile": "core_plus_macro",
            "selected_feature_profile_source": "bull_4h_pocket_ablation.exact_supported_profile",
            "feature_profile_candidate_diagnostics": [],
        },
        leaderboard_snapshot_created_at="2026-04-14T06:51:24Z",
        alignment_evaluated_at="2026-04-14T06:51:24Z",
    )

    assert alignment["dual_profile_state"] == "stale_alignment_snapshot"
    assert alignment["artifact_recency"]["alignment_snapshot_stale"] is True
    assert alignment["artifact_recency"]["stale_against_train"] is True
    assert alignment["artifact_recency"]["stale_against_bull_pocket"] is True
    assert alignment["artifact_recency"]["stale_against_feature_ablation"] is True
    assert alignment["current_alignment_inputs_stale"] is True
    assert alignment["current_alignment_recency"]["inputs_current"] is False
    assert alignment["leaderboard_snapshot_created_at"] == "2026-04-14T06:51:24Z"



def test_build_alignment_keeps_aligned_when_live_probe_matches_train_despite_old_snapshot(tmp_path, monkeypatch):
    last_metrics = tmp_path / "last_metrics.json"
    live_probe = tmp_path / "live_predict_probe.json"
    bull_pocket = tmp_path / "bull_4h_pocket_ablation.json"
    feature_ablation = tmp_path / "feature_group_ablation.json"

    last_metrics.write_text(
        json.dumps(
            {
                "feature_profile": "core_plus_macro_plus_4h_structure_shift",
                "trained_at": "2026-04-14T19:59:42Z",
                "feature_profile_meta": {
                    "source": "bull_4h_pocket_ablation.exact_supported_profile",
                    "support_cohort": "bull_all",
                    "support_rows": 759,
                    "exact_live_bucket_rows": 85,
                },
            }
        ),
        encoding="utf-8",
    )
    live_probe.write_text(
        json.dumps(
            {
                "regime_gate": "CAUTION",
                "entry_quality_label": "D",
                "execution_guardrail_reason": None,
            }
        ),
        encoding="utf-8",
    )
    bull_pocket.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-14 19:39:13",
                "live_context": {
                    "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
                    "current_live_structure_bucket_rows": 85,
                    "supported_neighbor_buckets": ["CAUTION|structure_quality_caution|q15"],
                },
                "support_pathology_summary": {
                    "minimum_support_rows": 50,
                    "exact_bucket_root_cause": "exact_bucket_supported",
                    "blocker_state": "exact_live_bucket_supported",
                    "proxy_boundary_verdict": "exact_bucket_supported_proxy_not_required",
                    "proxy_boundary_reason": "current live structure bucket 已達 minimum support；後續治理與驗證應直接以 exact bucket 為主，proxy 只保留輔助比較，不再作 blocker 判讀。",
                    "exact_lane_bucket_verdict": "toxic_sub_bucket_identified",
                    "exact_lane_toxic_bucket": {"bucket": "CAUTION|structure_quality_caution|q15"},
                },
                "cohorts": {
                    "bull_supported_neighbor_buckets_proxy": {
                        "rows": 84,
                        "recommended_profile": "core_plus_macro",
                    },
                    "bull_exact_live_lane_proxy": {
                        "rows": 392,
                        "recommended_profile": "core_plus_macro",
                    },
                    "bull_live_exact_lane_bucket_proxy": {
                        "rows": 129,
                        "recommended_profile": None,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    feature_ablation.write_text(
        json.dumps({"recommended_profile": "core_only", "generated_at": "2026-04-14 19:39:11"}),
        encoding="utf-8",
    )

    monkeypatch.setattr(hb_leaderboard_candidate_probe, "LAST_METRICS_PATH", last_metrics)
    monkeypatch.setattr(hb_leaderboard_candidate_probe, "LIVE_PROBE_PATH", live_probe)
    monkeypatch.setattr(hb_leaderboard_candidate_probe, "BULL_POCKET_PATH", bull_pocket)
    monkeypatch.setattr(hb_leaderboard_candidate_probe, "FEATURE_ABLATION_PATH", feature_ablation)

    alignment = hb_leaderboard_candidate_probe._build_alignment(
        {
            "selected_feature_profile": "core_plus_macro_plus_4h_structure_shift",
            "selected_feature_profile_source": "bull_4h_pocket_ablation.exact_supported_profile",
            "feature_profile_candidate_diagnostics": [],
        },
        leaderboard_snapshot_created_at="2026-04-14T06:51:24Z",
        alignment_evaluated_at="2026-04-14T21:00:00Z",
    )

    assert alignment["dual_profile_state"] == "aligned"
    assert alignment["artifact_recency"]["alignment_snapshot_stale"] is True
    assert alignment["artifact_recency"]["stale_against_train"] is True
    assert alignment["artifact_recency"]["stale_against_bull_pocket"] is True
    assert alignment["artifact_recency"]["stale_against_feature_ablation"] is True
    assert alignment["current_alignment_inputs_stale"] is False
    assert alignment["current_alignment_recency"]["inputs_current"] is True



def test_build_alignment_prefers_current_governance_state_over_old_snapshot_when_inputs_are_fresh(tmp_path, monkeypatch):
    last_metrics = tmp_path / "last_metrics.json"
    live_probe = tmp_path / "live_predict_probe.json"
    bull_pocket = tmp_path / "bull_4h_pocket_ablation.json"
    feature_ablation = tmp_path / "feature_group_ablation.json"

    last_metrics.write_text(
        json.dumps(
            {
                "feature_profile": "core_plus_macro",
                "trained_at": "2026-04-14T22:04:35Z",
                "feature_profile_meta": {
                    "source": "bull_4h_pocket_ablation.exact_supported_profile",
                    "support_cohort": "bull_exact_live_lane_proxy",
                    "support_rows": 396,
                    "exact_live_bucket_rows": 4,
                },
            }
        ),
        encoding="utf-8",
    )
    live_probe.write_text(
        json.dumps(
            {
                "regime_gate": "CAUTION",
                "entry_quality_label": "D",
                "execution_guardrail_reason": None,
            }
        ),
        encoding="utf-8",
    )
    bull_pocket.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-14 22:08:34",
                "live_context": {
                    "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
                    "current_live_structure_bucket_rows": 90,
                    "supported_neighbor_buckets": ["CAUTION|structure_quality_caution|q15"],
                },
                "support_pathology_summary": {
                    "minimum_support_rows": 50,
                    "exact_bucket_root_cause": "exact_bucket_supported",
                    "blocker_state": "exact_live_bucket_supported",
                    "proxy_boundary_verdict": "exact_bucket_supported_proxy_not_required",
                    "proxy_boundary_reason": "current live structure bucket 已達 minimum support；後續治理與驗證應直接以 exact bucket 為主，proxy 只保留輔助比較，不再作 blocker 判讀。",
                    "exact_lane_bucket_verdict": "toxic_sub_bucket_identified",
                    "exact_lane_toxic_bucket": {"bucket": "CAUTION|structure_quality_caution|q15"},
                },
                "cohorts": {
                    "bull_supported_neighbor_buckets_proxy": {
                        "rows": 84,
                        "recommended_profile": "core_plus_macro",
                    },
                    "bull_exact_live_lane_proxy": {
                        "rows": 396,
                        "recommended_profile": "core_plus_macro",
                    },
                    "bull_live_exact_lane_bucket_proxy": {
                        "rows": 133,
                        "recommended_profile": None,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    feature_ablation.write_text(
        json.dumps({"recommended_profile": "core_only", "generated_at": "2026-04-14 22:08:32"}),
        encoding="utf-8",
    )

    monkeypatch.setattr(hb_leaderboard_candidate_probe, "LAST_METRICS_PATH", last_metrics)
    monkeypatch.setattr(hb_leaderboard_candidate_probe, "LIVE_PROBE_PATH", live_probe)
    monkeypatch.setattr(hb_leaderboard_candidate_probe, "BULL_POCKET_PATH", bull_pocket)
    monkeypatch.setattr(hb_leaderboard_candidate_probe, "FEATURE_ABLATION_PATH", feature_ablation)

    alignment = hb_leaderboard_candidate_probe._build_alignment(
        {
            "selected_feature_profile": "core_plus_macro_plus_4h_structure_shift",
            "selected_feature_profile_source": "bull_4h_pocket_ablation.exact_supported_profile",
            "feature_profile_candidate_diagnostics": [],
        },
        leaderboard_snapshot_created_at="2026-04-14T06:51:24Z",
        alignment_evaluated_at="2026-04-14T22:12:16Z",
    )

    assert alignment["dual_profile_state"] == "post_threshold_profile_governance_stalled"
    assert alignment["governance_contract"]["verdict"] == "post_threshold_governance_contract_needs_leaderboard_sync"
    assert alignment["governance_contract"]["treat_as_parity_blocker"] is True
    assert alignment["artifact_recency"]["alignment_snapshot_stale"] is True
    assert alignment["current_alignment_inputs_stale"] is False
    assert alignment["current_alignment_recency"]["inputs_current"] is True



def test_build_alignment_marks_proxy_not_required_when_exact_bucket_supported(tmp_path, monkeypatch):
    last_metrics = tmp_path / "last_metrics.json"
    live_probe = tmp_path / "live_predict_probe.json"
    bull_pocket = tmp_path / "bull_4h_pocket_ablation.json"
    feature_ablation = tmp_path / "feature_group_ablation.json"

    last_metrics.write_text(
        json.dumps(
            {
                "feature_profile": "core_plus_macro_plus_4h_structure_shift",
                "feature_profile_meta": {
                    "source": "bull_4h_pocket_ablation.exact_supported_profile",
                    "support_cohort": "exact_live_bucket",
                    "support_rows": 55,
                    "exact_live_bucket_rows": 55,
                },
            }
        ),
        encoding="utf-8",
    )
    live_probe.write_text(
        json.dumps(
            {
                "regime_gate": "CAUTION",
                "entry_quality_label": "D",
                "execution_guardrail_reason": None,
            }
        ),
        encoding="utf-8",
    )
    bull_pocket.write_text(
        json.dumps(
            {
                "live_context": {
                    "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
                    "current_live_structure_bucket_rows": 55,
                    "supported_neighbor_buckets": ["CAUTION|structure_quality_caution|q15"],
                },
                "support_pathology_summary": {
                    "minimum_support_rows": 50,
                    "exact_bucket_root_cause": "exact_bucket_supported",
                    "blocker_state": "exact_live_bucket_supported",
                    "proxy_boundary_verdict": "exact_bucket_supported_proxy_not_required",
                    "proxy_boundary_reason": "current live structure bucket 已達 minimum support；後續治理與驗證應直接以 exact bucket 為主，proxy 只保留輔助比較，不再作 blocker 判讀。",
                    "exact_lane_bucket_verdict": "toxic_sub_bucket_identified",
                    "exact_lane_toxic_bucket": {"bucket": "CAUTION|structure_quality_caution|q15"},
                },
                "cohorts": {
                    "bull_supported_neighbor_buckets_proxy": {
                        "rows": 84,
                        "recommended_profile": "core_plus_macro",
                    },
                    "bull_exact_live_lane_proxy": {
                        "rows": 370,
                        "recommended_profile": "core_plus_macro",
                    },
                    "bull_live_exact_lane_bucket_proxy": {
                        "rows": 107,
                        "recommended_profile": None,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    feature_ablation.write_text(
        json.dumps({"recommended_profile": "core_only"}),
        encoding="utf-8",
    )

    monkeypatch.setattr(hb_leaderboard_candidate_probe, "LAST_METRICS_PATH", last_metrics)
    monkeypatch.setattr(hb_leaderboard_candidate_probe, "LIVE_PROBE_PATH", live_probe)
    monkeypatch.setattr(hb_leaderboard_candidate_probe, "BULL_POCKET_PATH", bull_pocket)
    monkeypatch.setattr(hb_leaderboard_candidate_probe, "FEATURE_ABLATION_PATH", feature_ablation)

    alignment = hb_leaderboard_candidate_probe._build_alignment(
        {
            "selected_feature_profile": "core_only",
            "selected_feature_profile_source": "feature_group_ablation.recommended_profile",
            "feature_profile_candidate_diagnostics": [],
        }
    )

    assert alignment["minimum_support_rows"] == 50
    assert alignment["live_current_structure_bucket_gap_to_minimum"] == 0
    assert alignment["exact_bucket_root_cause"] == "exact_bucket_supported"
    assert alignment["support_blocker_state"] == "exact_live_bucket_supported"
    assert alignment["proxy_boundary_verdict"] == "exact_bucket_supported_proxy_not_required"
    assert alignment["support_governance_route"] == "exact_live_bucket_supported"
    assert alignment["dual_profile_state"] == "post_threshold_profile_governance_stalled"
    assert alignment["governance_contract"]["verdict"] == "post_threshold_governance_contract_needs_leaderboard_sync"
    assert alignment["governance_contract"]["current_closure"] == "exact_supported_but_leaderboard_not_synced"



def test_main_suppresses_known_sklearn_feature_name_warnings(tmp_path, monkeypatch):
    out_path = tmp_path / "leaderboard_feature_profile_probe.json"
    monkeypatch.setattr(hb_leaderboard_candidate_probe, "OUT_PATH", out_path)

    def _emit_sklearn_warning(message: str) -> None:
        warnings.warn_explicit(
            message,
            UserWarning,
            filename="/tmp/sklearn/utils/validation.py",
            lineno=2684,
            module="sklearn.utils.validation",
        )

    def fake_payload():
        _emit_sklearn_warning("X has feature names, but LogisticRegression was fitted without feature names")
        _emit_sklearn_warning("X has feature names, but MLPClassifier was fitted without feature names")
        _emit_sklearn_warning("X has feature names, but SVC was fitted without feature names")
        return {
            "snapshot_history": [{"created_at": "2026-04-14T13:08:04Z"}],
            "target_col": "simulated_pyramid_win",
            "count": 1,
            "leaderboard": [{"selected_feature_profile": "core_only"}],
        }

    monkeypatch.setattr(hb_leaderboard_candidate_probe.api_module, "_build_model_leaderboard_payload", fake_payload)
    monkeypatch.setattr(
        hb_leaderboard_candidate_probe,
        "_build_alignment",
        lambda top_model, leaderboard_snapshot_created_at=None, alignment_evaluated_at=None: {"dual_profile_state": "aligned"},
    )

    with warnings.catch_warnings(record=True) as caught:
        rc = hb_leaderboard_candidate_probe.main()

    assert rc == 0
    assert out_path.exists()
    saved = json.loads(out_path.read_text(encoding="utf-8"))
    assert saved["top_model"]["selected_feature_profile"] == "core_only"
    assert not caught
