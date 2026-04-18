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


def test_summarize_support_progress_detects_stalled_exact_support(tmp_path):
    for idx in range(2):
        (tmp_path / f"heartbeat_{700 + idx}_summary.json").write_text(
            json.dumps(
                {
                    "heartbeat": str(700 + idx),
                    "timestamp": f"2026-04-15T21:0{idx}:00+00:00",
                    "leaderboard_candidate_diagnostics": {
                        "live_current_structure_bucket": "CAUTION|structure_quality_caution|q35",
                        "live_current_structure_bucket_rows": 15,
                        "minimum_support_rows": 50,
                        "support_governance_route": "exact_live_bucket_present_but_below_minimum",
                        "governance_contract": {"verdict": "dual_role_governance_active"},
                    },
                }
            ),
            encoding="utf-8",
        )

    progress = hb_leaderboard_candidate_probe._summarize_support_progress(
        current_bucket="CAUTION|structure_quality_caution|q35",
        current_route="exact_live_bucket_present_but_below_minimum",
        live_bucket_rows=15,
        minimum_support_rows=50,
        current_label="fast",
        data_dir=tmp_path,
    )

    assert progress["status"] == "stalled_under_minimum"
    assert progress["stalled_support_accumulation"] is True
    assert progress["stagnant_run_count"] == 3
    assert progress["escalate_to_blocker"] is True
    assert progress["history"][0]["heartbeat"] == "fast"


def test_summarize_support_progress_reuses_previous_fast_summary(tmp_path):
    (tmp_path / "heartbeat_fast_summary.json").write_text(
        json.dumps(
            {
                "heartbeat": "fast",
                "timestamp": "2026-04-15T21:00:00+00:00",
                "leaderboard_candidate_diagnostics": {
                    "live_current_structure_bucket": "CAUTION|structure_quality_caution|q35",
                    "live_current_structure_bucket_rows": 13,
                    "governance_contract": {
                        "verdict": "dual_role_governance_active",
                        "minimum_support_rows": 50,
                        "support_governance_route": "exact_live_bucket_present_but_below_minimum",
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    progress = hb_leaderboard_candidate_probe._summarize_support_progress(
        current_bucket="CAUTION|structure_quality_caution|q35",
        current_route="exact_live_bucket_present_but_below_minimum",
        live_bucket_rows=13,
        minimum_support_rows=50,
        current_label="fast",
        data_dir=tmp_path,
    )

    assert progress["status"] == "stalled_under_minimum"
    assert progress["previous_rows"] == 13
    assert progress["delta_vs_previous"] == 0
    assert any(item["heartbeat"] == "fast" and item["live_current_structure_bucket_rows"] == 13 for item in progress["history"][1:])



def test_summarize_support_progress_tracks_bucket_accumulation_across_route_change(tmp_path):
    (tmp_path / "heartbeat_701_summary.json").write_text(
        json.dumps(
            {
                "heartbeat": "701",
                "timestamp": "2026-04-15T20:59:00+00:00",
                "leaderboard_candidate_diagnostics": {
                    "live_current_structure_bucket": "CAUTION|structure_quality_caution|q35",
                    "live_current_structure_bucket_rows": 0,
                    "minimum_support_rows": 50,
                    "support_governance_route": "exact_live_lane_proxy_available",
                    "governance_contract": {"verdict": "dual_role_governance_active"},
                },
            }
        ),
        encoding="utf-8",
    )

    progress = hb_leaderboard_candidate_probe._summarize_support_progress(
        current_bucket="CAUTION|structure_quality_caution|q35",
        current_route="exact_live_bucket_present_but_below_minimum",
        live_bucket_rows=3,
        minimum_support_rows=50,
        current_label="702",
        data_dir=tmp_path,
    )

    assert progress["status"] == "accumulating"
    assert progress["previous_rows"] == 0
    assert progress["delta_vs_previous"] == 3
    assert progress["previous_route_changed"] is True
    assert progress["previous_support_governance_route"] == "exact_live_lane_proxy_available"
    assert progress["stagnant_run_count"] == 0
    assert progress["stalled_support_accumulation"] is False
    assert progress["escalate_to_blocker"] is False
    assert progress["history"][0]["live_current_structure_bucket_rows"] == 3
    assert progress["history"][1]["live_current_structure_bucket_rows"] == 0


def test_summarize_support_progress_prefers_q15_audit_truth(tmp_path, monkeypatch):
    q15_audit = tmp_path / "q15_support_audit.json"
    q15_audit.write_text(
        json.dumps(
            {
                "current_live": {
                    "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
                    "current_live_structure_bucket_rows": 4,
                },
                "support_route": {
                    "minimum_support_rows": 50,
                    "support_governance_route": "exact_live_bucket_present_but_below_minimum",
                    "support_progress": {
                        "status": "accumulating",
                        "reason": "from q15 audit",
                        "current_rows": 4,
                        "minimum_support_rows": 50,
                        "gap_to_minimum": 46,
                        "delta_vs_previous": 4,
                        "previous_rows": 0,
                        "previous_route_changed": True,
                        "previous_support_route_verdict": "exact_bucket_missing_proxy_reference_only",
                        "previous_support_governance_route": "exact_live_bucket_proxy_available",
                        "stagnant_run_count": 0,
                        "stalled_support_accumulation": False,
                        "escalate_to_blocker": False,
                        "history": [
                            {
                                "heartbeat": "current",
                                "live_current_structure_bucket": "CAUTION|structure_quality_caution|q15",
                                "live_current_structure_bucket_rows": 4,
                            },
                            {
                                "heartbeat": "1014",
                                "live_current_structure_bucket": "CAUTION|structure_quality_caution|q15",
                                "live_current_structure_bucket_rows": 0,
                            },
                        ],
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(hb_leaderboard_candidate_probe, "Q15_SUPPORT_AUDIT_PATH", q15_audit)

    progress = hb_leaderboard_candidate_probe._summarize_support_progress(
        current_bucket="CAUTION|structure_quality_caution|q15",
        current_route="exact_live_bucket_present_but_below_minimum",
        live_bucket_rows=4,
        minimum_support_rows=50,
        current_label="fast",
        data_dir=tmp_path,
    )

    assert progress["status"] == "accumulating"
    assert progress["delta_vs_previous"] == 4
    assert progress["previous_rows"] == 0
    assert progress["reason"] == "from q15 audit"
    assert progress["history"][1]["heartbeat"] == "1014"


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



def test_build_alignment_prefers_live_probe_bucket_over_stale_bull_pocket_context(tmp_path, monkeypatch):
    last_metrics = tmp_path / "last_metrics.json"
    live_probe = tmp_path / "live_predict_probe.json"
    bull_pocket = tmp_path / "bull_4h_pocket_ablation.json"
    feature_ablation = tmp_path / "feature_group_ablation.json"

    last_metrics.write_text(json.dumps({"feature_profile": "core_plus_macro"}), encoding="utf-8")
    live_probe.write_text(
        json.dumps(
            {
                "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
                "current_live_structure_bucket_rows": 4,
                "regime_gate": "CAUTION",
                "entry_quality_label": "D",
                "execution_guardrail_reason": "unsupported_live_structure_bucket_blocks_trade; under_minimum_exact_live_structure_bucket",
            }
        ),
        encoding="utf-8",
    )
    bull_pocket.write_text(
        json.dumps(
            {
                "live_context": {
                    "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
                    "current_live_structure_bucket_rows": 1,
                    "supported_neighbor_buckets": ["CAUTION|structure_quality_caution|q15"],
                },
                "support_pathology_summary": {
                    "minimum_support_rows": 50,
                    "exact_bucket_root_cause": "exact_bucket_present_but_below_minimum",
                    "blocker_state": "exact_lane_proxy_fallback_only",
                    "proxy_boundary_verdict": "proxy_governance_reference_only_exact_support_blocked",
                    "proxy_boundary_reason": "historical same-bucket proxy 可保留作 governance 參考，但 current live structure bucket 仍低於 minimum support；在 exact support 補滿前，proxy 不得當成 deployment 放行依據。",
                    "exact_lane_bucket_verdict": "no_exact_lane_sub_bucket_split",
                    "exact_lane_toxic_bucket": None,
                },
                "cohorts": {
                    "bull_exact_live_lane_proxy": {
                        "rows": 58,
                        "recommended_profile": "core_plus_macro",
                    },
                    "bull_live_exact_lane_bucket_proxy": {
                        "rows": 1,
                        "recommended_profile": None,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    feature_ablation.write_text(json.dumps({"recommended_profile": "core_only"}), encoding="utf-8")

    monkeypatch.setattr(hb_leaderboard_candidate_probe, "LAST_METRICS_PATH", last_metrics)
    monkeypatch.setattr(hb_leaderboard_candidate_probe, "LIVE_PROBE_PATH", live_probe)
    monkeypatch.setattr(hb_leaderboard_candidate_probe, "BULL_POCKET_PATH", bull_pocket)
    monkeypatch.setattr(hb_leaderboard_candidate_probe, "FEATURE_ABLATION_PATH", feature_ablation)
    monkeypatch.setattr(hb_leaderboard_candidate_probe, "Q15_SUPPORT_AUDIT_PATH", tmp_path / "missing_q15_support_audit.json")

    alignment = hb_leaderboard_candidate_probe._build_alignment(
        {
            "selected_feature_profile": "core_plus_macro",
            "selected_feature_profile_source": "bull_4h_pocket_ablation.support_aware_profile",
            "feature_profile_candidate_diagnostics": [],
        }
    )

    assert alignment["live_current_structure_bucket"] == "CAUTION|structure_quality_caution|q15"
    assert alignment["live_current_structure_bucket_rows"] == 4
    assert alignment["live_current_structure_bucket_gap_to_minimum"] == 46
    assert alignment["support_governance_route"] == "exact_live_bucket_present_but_below_minimum"
    assert alignment["support_progress"]["current_rows"] == 4



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



def test_build_alignment_marks_train_exact_supported_profile_stale_when_live_bucket_regresses(tmp_path, monkeypatch):
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
                    "support_cohort": "bull_all",
                    "support_rows": 761,
                    "exact_live_bucket_rows": 90,
                },
            }
        ),
        encoding="utf-8",
    )
    live_probe.write_text(
        json.dumps(
            {
                "regime_gate": "CAUTION",
                "entry_quality_label": "C",
                "execution_guardrail_reason": None,
            }
        ),
        encoding="utf-8",
    )
    bull_pocket.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-15 22:15:45",
                "live_context": {
                    "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
                    "current_live_structure_bucket_rows": 10,
                    "supported_neighbor_buckets": ["CAUTION|structure_quality_caution|q15"],
                },
                "support_pathology_summary": {
                    "minimum_support_rows": 50,
                    "exact_bucket_root_cause": "exact_bucket_present_but_below_minimum",
                    "blocker_state": "exact_lane_proxy_fallback_only",
                    "proxy_boundary_verdict": "proxy_governance_reference_only_exact_support_blocked",
                    "proxy_boundary_reason": "historical same-bucket proxy 可保留作 governance 參考，但 current live structure bucket 仍低於 minimum support；在 exact support 補滿前，proxy 不得當成 deployment 放行依據。",
                    "exact_lane_bucket_verdict": "no_exact_lane_sub_bucket_split",
                    "exact_lane_toxic_bucket": None,
                },
                "cohorts": {
                    "bull_exact_live_lane_proxy": {
                        "rows": 58,
                        "recommended_profile": "core_plus_macro",
                    },
                    "bull_live_exact_lane_bucket_proxy": {
                        "rows": 1,
                        "recommended_profile": None,
                    },
                    "bull_supported_neighbor_buckets_proxy": {
                        "rows": 0,
                        "recommended_profile": None,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    feature_ablation.write_text(
        json.dumps({"recommended_profile": "core_plus_4h", "generated_at": "2026-04-15 22:15:43"}),
        encoding="utf-8",
    )

    monkeypatch.setattr(hb_leaderboard_candidate_probe, "LAST_METRICS_PATH", last_metrics)
    monkeypatch.setattr(hb_leaderboard_candidate_probe, "LIVE_PROBE_PATH", live_probe)
    monkeypatch.setattr(hb_leaderboard_candidate_probe, "BULL_POCKET_PATH", bull_pocket)
    monkeypatch.setattr(hb_leaderboard_candidate_probe, "FEATURE_ABLATION_PATH", feature_ablation)

    alignment = hb_leaderboard_candidate_probe._build_alignment(
        {
            "selected_feature_profile": "core_plus_4h",
            "selected_feature_profile_source": "feature_group_ablation.recommended_profile",
            "feature_profile_candidate_diagnostics": [],
        },
        leaderboard_snapshot_created_at="2026-04-15T16:08:55.658093Z",
        alignment_evaluated_at="2026-04-15T22:19:48.190047Z",
    )

    assert alignment["support_governance_route"] == "exact_live_bucket_present_but_below_minimum"
    assert alignment["dual_profile_state"] == "train_exact_supported_profile_stale_under_minimum"
    assert alignment["governance_contract"]["verdict"] == "train_profile_contract_stale_against_current_support"
    assert alignment["governance_contract"]["treat_as_parity_blocker"] is False
    assert alignment["governance_contract"]["current_closure"] == "train_still_claims_exact_supported_profile_but_live_bucket_under_minimum"



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



def test_load_leaderboard_payload_prefers_latest_snapshot_when_cache_is_empty(tmp_path, monkeypatch):
    cache_path = tmp_path / "model_leaderboard_cache.json"
    cache_path.write_text(json.dumps({"payload": {}, "updated_at": 0.0, "error": "cache broken"}), encoding="utf-8")
    monkeypatch.setattr(hb_leaderboard_candidate_probe.api_module, "MODEL_LB_CACHE_PATH", cache_path, raising=False)
    monkeypatch.setattr(
        hb_leaderboard_candidate_probe.api_module,
        "_load_latest_model_leaderboard_snapshot_payload",
        lambda: {
            "payload": {
                "target_col": "simulated_pyramid_win",
                "count": 1,
                "leaderboard": [{"selected_feature_profile": "core_only"}],
                "snapshot_history": [{"created_at": "2026-04-14T13:08:04Z"}],
            },
            "updated_at": 1713100000.0,
            "error": None,
        },
    )
    monkeypatch.setattr(
        hb_leaderboard_candidate_probe.api_module,
        "_build_model_leaderboard_payload",
        lambda: (_ for _ in ()).throw(AssertionError("live rebuild should not run when snapshot exists")),
    )

    payload, meta = hb_leaderboard_candidate_probe._load_leaderboard_payload(allow_rebuild=False)

    assert payload["leaderboard"][0]["selected_feature_profile"] == "core_only"
    assert meta["source"] == "latest_persisted_snapshot"
    assert meta["cache_error"] == "cache broken"



def test_load_leaderboard_payload_rebuilds_when_cached_payload_is_stale_and_missing_selection_fields(tmp_path, monkeypatch):
    cache_path = tmp_path / "model_leaderboard_cache.json"
    stale_updated_at = 1_713_100_000.0
    cache_path.write_text(
        json.dumps(
            {
                "payload": {
                    "target_col": "simulated_pyramid_win",
                    "count": 1,
                    "leaderboard": [{"model_name": "xgboost"}],
                },
                "updated_at": stale_updated_at,
                "error": None,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(hb_leaderboard_candidate_probe.api_module, "MODEL_LB_CACHE_PATH", cache_path, raising=False)
    monkeypatch.setattr(
        hb_leaderboard_candidate_probe.api_module,
        "_load_latest_model_leaderboard_snapshot_payload",
        lambda: None,
    )
    monkeypatch.setattr(hb_leaderboard_candidate_probe.time, "time", lambda: stale_updated_at + 3600)
    monkeypatch.setattr(
        hb_leaderboard_candidate_probe.api_module,
        "_build_model_leaderboard_payload",
        lambda: {
            "target_col": "simulated_pyramid_win",
            "count": 1,
            "leaderboard": [
                {
                    "model_name": "xgboost",
                    "selected_feature_profile": "core_plus_macro",
                    "selected_deployment_profile": "stable_turning_point_all_regimes_strict_v1",
                }
            ],
        },
    )

    payload, meta = hb_leaderboard_candidate_probe._load_leaderboard_payload(allow_rebuild=True)

    assert payload["leaderboard"][0]["selected_feature_profile"] == "core_plus_macro"
    assert payload["leaderboard"][0]["selected_deployment_profile"] == "stable_turning_point_all_regimes_strict_v1"
    assert meta["source"] == "live_rebuild"
    assert meta["stale"] is False



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

    monkeypatch.setattr(
        hb_leaderboard_candidate_probe,
        "_load_leaderboard_payload",
        lambda allow_rebuild=True: (
            fake_payload(),
            {
                "source": "latest_persisted_snapshot",
                "updated_at": "2026-04-14T13:08:04Z",
                "cache_age_sec": 42,
                "stale": False,
                "error": None,
                "cache_error": None,
            },
        ),
    )
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
    assert saved["leaderboard_payload_source"] == "latest_persisted_snapshot"
    assert not caught


def test_build_probe_result_uses_newest_snapshot_timestamp(monkeypatch):
    payload = {
        "target_col": "simulated_pyramid_win",
        "count": 1,
        "leaderboard": [{"selected_feature_profile": "core_only"}],
        "snapshot_history": [
            {"created_at": "2026-04-18T08:53:35.723600Z"},
            {"created_at": "2026-04-18T08:25:59.708532Z"},
        ],
    }
    meta = {
        "source": "model_leaderboard_cache",
        "updated_at": "2026-04-18T09:00:00.767984Z",
        "cache_age_sec": 2,
        "stale": False,
        "error": None,
        "cache_error": None,
    }
    captured = {}

    monkeypatch.setattr(
        hb_leaderboard_candidate_probe,
        "_load_leaderboard_payload",
        lambda allow_rebuild=True: (payload, meta),
    )

    def fake_build_alignment(top_model, leaderboard_snapshot_created_at=None, alignment_evaluated_at=None):
        captured["leaderboard_snapshot_created_at"] = leaderboard_snapshot_created_at
        captured["alignment_evaluated_at"] = alignment_evaluated_at
        return {"ok": True}

    monkeypatch.setattr(hb_leaderboard_candidate_probe, "_build_alignment", fake_build_alignment)

    result = hb_leaderboard_candidate_probe.build_probe_result(
        allow_rebuild=False,
        generated_at="2026-04-18T09:00:03.579117Z",
    )

    assert result is not None
    assert result["leaderboard_snapshot_created_at"] == "2026-04-18T09:00:00.767984Z"
    assert captured["leaderboard_snapshot_created_at"] == "2026-04-18T09:00:00.767984Z"
    assert captured["alignment_evaluated_at"] == "2026-04-18T09:00:03.579117Z"



def test_top_model_payload_falls_back_to_placeholder_rows_when_no_comparable_rows():
    payload = {
        "leaderboard": [],
        "placeholder_rows": [
            {
                "model_name": "rule_baseline",
                "deployment_profile": "stable_turning_point_bull_chop_relaxed_v1",
                "deployment_profile_label": "穩定轉折 · Bull/Chop 寬鬆 v1",
                "deployment_profile_source": "code_backed_promoted_from_scan",
                "selected_deployment_profile": "stable_turning_point_bull_chop_relaxed_v1",
                "selected_deployment_profile_label": "穩定轉折 · Bull/Chop 寬鬆 v1",
                "selected_deployment_profile_source": "code_backed_promoted_from_scan",
                "selected_feature_profile": "core_plus_macro_plus_4h_structure_shift",
                "selected_feature_profile_source": "bull_4h_pocket_ablation.exact_supported_profile",
                "ranking_status": "no_trade_placeholder",
                "ranking_warning": "placeholder warning",
                "placeholder_reason": "no_trades_generated_under_current_deployment_profile",
            }
        ],
        "leaderboard_warning": "all placeholder",
        "comparable_count": 0,
        "placeholder_count": 1,
    }

    top_model = hb_leaderboard_candidate_probe._top_model_payload(payload)

    assert top_model["model_name"] == "rule_baseline"
    assert top_model["selected_deployment_profile"] == "stable_turning_point_bull_chop_relaxed_v1"
    assert top_model["selected_deployment_profile_label"] == "穩定轉折 · Bull/Chop 寬鬆 v1"
    assert top_model["selected_deployment_profile_source"] == "code_backed_promoted_from_scan"
    assert top_model["selected_feature_profile"] == "core_plus_macro_plus_4h_structure_shift"
    assert top_model["ranking_status"] == "no_trade_placeholder"
    assert top_model["top_model_source"] == "placeholder_rows"
    assert top_model["leaderboard_warning"] == "all placeholder"
    assert top_model["comparable_count"] == 0
    assert top_model["placeholder_count"] == 1
