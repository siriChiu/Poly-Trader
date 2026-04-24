import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hb_q15_support_audit.py"
spec = importlib.util.spec_from_file_location("hb_q15_support_audit_test_module", MODULE_PATH)
q15_support_audit = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(q15_support_audit)


def _support_identity(
    bucket="CAUTION|structure_quality_caution|q15",
    *,
    regime_gate="CAUTION",
    entry_quality_label="D",
):
    return {
        "target_col": "simulated_pyramid_win",
        "horizon_minutes": 1440,
        "current_live_structure_bucket": bucket,
        "regime_label": "bull",
        "regime_gate": regime_gate,
        "entry_quality_label": entry_quality_label,
        "calibration_window": 600,
        "bucket_semantic_signature": q15_support_audit.BUCKET_SEMANTIC_SIGNATURE,
    }


def test_summarize_support_progress_detects_stalled_q15_exact_support(tmp_path):
    identity = _support_identity()
    for idx in range(2):
        (tmp_path / f"heartbeat_{900 + idx}_summary.json").write_text(
            json.dumps(
                {
                    "heartbeat": str(900 + idx),
                    "timestamp": f"2026-04-16T08:0{idx}:00+00:00",
                    "q15_support_audit": {
                        "current_live": {
                            "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
                            "current_live_structure_bucket_rows": 4,
                        },
                        "support_identity": identity,
                        "support_route": {
                            "verdict": "exact_bucket_present_but_below_minimum",
                            "support_governance_route": "exact_live_bucket_present_but_below_minimum",
                            "minimum_support_rows": 50,
                        },
                    },
                }
            ),
            encoding="utf-8",
        )

    progress = q15_support_audit._summarize_support_progress(
        current_bucket="CAUTION|structure_quality_caution|q15",
        support_route_verdict="exact_bucket_present_but_below_minimum",
        support_governance_route="exact_live_bucket_present_but_below_minimum",
        live_bucket_rows=4,
        minimum_support_rows=50,
        current_label="fast",
        support_identity=identity,
        data_dir=tmp_path,
    )

    assert progress["status"] == "stalled_under_minimum"
    assert progress["previous_rows"] == 4
    assert progress["delta_vs_previous"] == 0
    assert progress["stagnant_run_count"] == 3
    assert progress["previous_route_changed"] is False
    assert progress["escalate_to_blocker"] is True



def test_summarize_support_progress_treats_legacy_supported_anchor_as_reference_only(tmp_path):
    identity = _support_identity(bucket="BLOCK|bull_q15_bias50_overextended_block|q15", regime_gate="BLOCK")
    (tmp_path / "heartbeat_920_summary.json").write_text(
        json.dumps(
            {
                "heartbeat": "920",
                "timestamp": "2026-04-23T04:31:17+00:00",
                "q15_support_audit": {
                    "current_live": {
                        "current_live_structure_bucket": "BLOCK|bull_q15_bias50_overextended_block|q15",
                        "current_live_structure_bucket_rows": 199,
                    },
                    "support_route": {
                        "verdict": "exact_bucket_supported",
                        "support_governance_route": "exact_live_bucket_supported",
                        "minimum_support_rows": 50,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "heartbeat_921_summary.json").write_text(
        json.dumps(
            {
                "heartbeat": "921",
                "timestamp": "2026-04-23T08:35:32+00:00",
                "q15_support_audit": {
                    "current_live": {
                        "current_live_structure_bucket": "BLOCK|bull_q15_bias50_overextended_block|q15",
                        "current_live_structure_bucket_rows": 0,
                    },
                    "support_route": {
                        "verdict": "exact_bucket_missing_proxy_reference_only",
                        "support_governance_route": "exact_live_bucket_proxy_available",
                        "minimum_support_rows": 50,
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    progress = q15_support_audit._summarize_support_progress(
        current_bucket="BLOCK|bull_q15_bias50_overextended_block|q15",
        support_route_verdict="exact_bucket_missing_proxy_reference_only",
        support_governance_route="exact_live_bucket_proxy_available",
        live_bucket_rows=0,
        minimum_support_rows=50,
        current_label="fast",
        support_identity=identity,
        data_dir=tmp_path,
    )

    assert progress["status"] == "semantic_rebaseline_under_minimum"
    assert progress["regression_basis"] == "legacy_or_different_semantic_signature"
    assert progress["previous_rows"] is None
    assert progress["delta_vs_previous"] is None
    assert progress["regressed_from_supported"] is False
    assert progress["recent_supported_rows"] is None
    assert progress["legacy_supported_reference"]["live_current_structure_bucket_rows"] == 199
    assert progress["legacy_supported_reference"]["heartbeat"] == "920"
    assert progress["escalate_to_blocker"] is True
    assert "legacy reference" in progress["reason"]



def test_summarize_support_progress_rebaselines_legacy_supported_anchor_when_identity_is_missing(tmp_path):
    (tmp_path / "heartbeat_920_summary.json").write_text(
        json.dumps(
            {
                "heartbeat": "920",
                "timestamp": "2026-04-23T04:31:17+00:00",
                "q15_support_audit": {
                    "current_live": {
                        "current_live_structure_bucket": "BLOCK|bull_q15_bias50_overextended_block|q15",
                        "current_live_structure_bucket_rows": 199,
                    },
                    "support_route": {
                        "verdict": "exact_bucket_supported",
                        "support_governance_route": "exact_live_bucket_supported",
                        "minimum_support_rows": 50,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    current_identity = {
        "target_col": "simulated_pyramid_win",
        "horizon_minutes": 1440,
        "current_live_structure_bucket": "BLOCK|bull_q15_bias50_overextended_block|q15",
        "regime_label": "bull",
        "regime_gate": "BLOCK",
        "entry_quality_label": "D",
        "calibration_window": 600,
        "bucket_semantic_signature": q15_support_audit.BUCKET_SEMANTIC_SIGNATURE,
    }

    progress = q15_support_audit._summarize_support_progress(
        current_bucket="BLOCK|bull_q15_bias50_overextended_block|q15",
        support_route_verdict="exact_bucket_present_but_below_minimum",
        support_governance_route="exact_live_bucket_present_but_below_minimum",
        live_bucket_rows=16,
        minimum_support_rows=50,
        current_label="fast",
        support_identity=current_identity,
        data_dir=tmp_path,
    )

    assert progress["status"] == "semantic_rebaseline_under_minimum"
    assert progress["regression_basis"] == "legacy_or_different_semantic_signature"
    assert progress["recent_supported_rows"] is None
    assert progress["legacy_supported_reference"]["live_current_structure_bucket_rows"] == 199
    assert progress["legacy_supported_reference"]["support_identity"] is None
    assert progress["legacy_supported_reference"]["reference_only_reason"] == "missing_or_different_support_identity_or_bucket_semantic_signature"
    assert progress["comparable_history_count"] == 0
    assert progress["legacy_reference_history_count"] == 1
    assert progress["escalate_to_blocker"] is True



def test_summarize_support_progress_preserves_supported_anchor_after_many_newer_stalled_heartbeats(tmp_path, monkeypatch):
    identity = _support_identity(bucket="BLOCK|bull_q15_bias50_overextended_block|q15", regime_gate="BLOCK")

    def _row(overrides):
        base = {
            "support_identity": identity,
        }
        base.update(overrides)
        return base

    def fake_history(*, current_entry, data_dir=None):
        return [
            {k: v for k, v in current_entry.items() if k != "observed_at"},
            _row({
                "heartbeat": "935",
                "timestamp": "2026-04-23T08:00:00+00:00",
                "live_current_structure_bucket": "BLOCK|bull_q15_bias50_overextended_block|q15",
                "live_current_structure_bucket_rows": 0,
                "minimum_support_rows": 50,
                "support_route_verdict": "exact_bucket_missing_proxy_reference_only",
                "support_governance_route": "exact_live_bucket_proxy_available",
            }),
            _row({
                "heartbeat": "934",
                "timestamp": "2026-04-23T07:00:00+00:00",
                "live_current_structure_bucket": "BLOCK|bull_q15_bias50_overextended_block|q15",
                "live_current_structure_bucket_rows": 0,
                "minimum_support_rows": 50,
                "support_route_verdict": "exact_bucket_missing_proxy_reference_only",
                "support_governance_route": "exact_live_bucket_proxy_available",
            }),
            _row({
                "heartbeat": "933",
                "timestamp": "2026-04-23T06:00:00+00:00",
                "live_current_structure_bucket": "BLOCK|bull_q15_bias50_overextended_block|q15",
                "live_current_structure_bucket_rows": 0,
                "minimum_support_rows": 50,
                "support_route_verdict": "exact_bucket_missing_proxy_reference_only",
                "support_governance_route": "exact_live_bucket_proxy_available",
            }),
            _row({
                "heartbeat": "932",
                "timestamp": "2026-04-23T05:00:00+00:00",
                "live_current_structure_bucket": "BLOCK|bull_q15_bias50_overextended_block|q15",
                "live_current_structure_bucket_rows": 0,
                "minimum_support_rows": 50,
                "support_route_verdict": "exact_bucket_missing_proxy_reference_only",
                "support_governance_route": "exact_live_bucket_proxy_available",
            }),
            _row({
                "heartbeat": "931",
                "timestamp": "2026-04-23T04:40:00+00:00",
                "live_current_structure_bucket": "BLOCK|bull_q15_bias50_overextended_block|q15",
                "live_current_structure_bucket_rows": 0,
                "minimum_support_rows": 50,
                "support_route_verdict": "exact_bucket_missing_proxy_reference_only",
                "support_governance_route": "exact_live_bucket_proxy_available",
            }),
            _row({
                "heartbeat": "930",
                "timestamp": "2026-04-23T04:31:17+00:00",
                "live_current_structure_bucket": "BLOCK|bull_q15_bias50_overextended_block|q15",
                "live_current_structure_bucket_rows": 199,
                "minimum_support_rows": 50,
                "support_route_verdict": "exact_bucket_supported",
                "support_governance_route": "exact_live_bucket_supported",
            }),
        ]

    monkeypatch.setattr(q15_support_audit, "_load_recent_q15_support_history", fake_history)

    progress = q15_support_audit._summarize_support_progress(
        current_bucket="BLOCK|bull_q15_bias50_overextended_block|q15",
        support_route_verdict="exact_bucket_missing_proxy_reference_only",
        support_governance_route="exact_live_bucket_proxy_available",
        live_bucket_rows=0,
        minimum_support_rows=50,
        current_label="fast",
        support_identity=identity,
        data_dir=tmp_path,
    )

    assert progress["status"] == "regressed_under_minimum"
    assert progress["regression_basis"] == "same_identity_same_semantic_signature"
    assert progress["recent_supported_rows"] == 199
    assert progress["recent_supported_heartbeat"] == "930"
    assert progress["delta_vs_recent_supported"] == -199
    assert any(item["heartbeat"] == "930" for item in progress["history"])



def test_summarize_support_progress_uses_current_live_copy_for_non_q15_bucket(tmp_path):
    identity = _support_identity(bucket="CAUTION|structure_quality_caution|q35")
    for idx in range(2):
        (tmp_path / f"heartbeat_{910 + idx}_summary.json").write_text(
            json.dumps(
                {
                    "heartbeat": str(910 + idx),
                    "timestamp": f"2026-04-21T12:0{idx}:00+00:00",
                    "q15_support_audit": {
                        "current_live": {
                            "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
                            "current_live_structure_bucket_rows": 12,
                        },
                        "support_identity": identity,
                        "support_route": {
                            "verdict": "exact_bucket_present_but_below_minimum",
                            "support_governance_route": "exact_live_bucket_present_but_below_minimum",
                            "minimum_support_rows": 50,
                        },
                    },
                }
            ),
            encoding="utf-8",
        )

    progress = q15_support_audit._summarize_support_progress(
        current_bucket="CAUTION|structure_quality_caution|q35",
        support_route_verdict="exact_bucket_present_but_below_minimum",
        support_governance_route="exact_live_bucket_present_but_below_minimum",
        live_bucket_rows=12,
        minimum_support_rows=50,
        current_label="fast",
        support_identity=identity,
        data_dir=tmp_path,
    )

    assert progress["status"] == "stalled_under_minimum"
    assert progress["reason"].startswith("current live exact support")
    assert "q15" not in progress["reason"]



def test_summarize_support_progress_tracks_bucket_accumulation_across_route_change(tmp_path):
    identity = _support_identity()
    (tmp_path / "heartbeat_901_summary.json").write_text(
        json.dumps(
            {
                "heartbeat": "901",
                "timestamp": "2026-04-16T07:59:00+00:00",
                "q15_support_audit": {
                    "current_live": {
                        "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
                        "current_live_structure_bucket_rows": 0,
                    },
                    "support_identity": identity,
                    "support_route": {
                        "verdict": "exact_bucket_missing_proxy_reference_only",
                        "support_governance_route": "exact_live_bucket_proxy_available",
                        "minimum_support_rows": 50,
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    progress = q15_support_audit._summarize_support_progress(
        current_bucket="CAUTION|structure_quality_caution|q15",
        support_route_verdict="exact_bucket_present_but_below_minimum",
        support_governance_route="exact_live_lane_proxy_available",
        live_bucket_rows=4,
        minimum_support_rows=50,
        current_label="902",
        support_identity=identity,
        data_dir=tmp_path,
    )

    assert progress["status"] == "accumulating"
    assert progress["previous_rows"] == 0
    assert progress["delta_vs_previous"] == 4
    assert progress["previous_route_changed"] is True
    assert progress["stagnant_run_count"] == 0
    assert progress["stalled_support_accumulation"] is False
    assert progress["escalate_to_blocker"] is False
    assert progress["history"][0]["live_current_structure_bucket_rows"] == 4
    assert progress["history"][1]["live_current_structure_bucket_rows"] == 0


def test_support_route_decision_marks_proxy_reference_only_when_exact_bucket_missing():
    result = q15_support_audit._support_route_decision(
        current_bucket_rows=0,
        minimum_support_rows=50,
        exact_bucket_proxy_rows=4,
        exact_lane_proxy_rows=418,
        supported_neighbor_rows=155,
        exact_bucket_root_cause="same_lane_shifted_to_neighbor_bucket",
        preferred_support_cohort="bull_exact_live_lane_proxy",
        support_governance_route="exact_live_bucket_proxy_available",
    )

    assert result["verdict"] == "exact_bucket_missing_proxy_reference_only"
    assert result["deployable"] is False
    assert result["governance_reference_only"] is True
    assert result["preferred_support_cohort"] == "bull_live_exact_bucket_proxy"


def test_floor_cross_legality_blocks_component_release_when_support_missing():
    support_route = {
        "deployable": False,
    }
    best_single_component = {
        "feature": "feat_4h_bias50",
        "can_single_component_cross_floor": True,
        "required_score_delta_to_cross_floor": 0.066,
    }

    result = q15_support_audit._floor_cross_legality(
        support_route=support_route,
        runtime_blocker=None,
        remaining_gap_to_floor=0.0198,
        best_single_component=best_single_component,
    )

    assert result["verdict"] == "math_cross_possible_but_illegal_without_exact_support"
    assert result["legal_to_relax_runtime_gate"] is False
    assert "feat_4h_bias50" in result["reason"]


def test_build_report_combines_support_route_and_floor_cross_legality(monkeypatch):
    probe = {
        "feature_timestamp": "2026-04-15 07:03:58",
        "target_col": "simulated_pyramid_win",
        "signal": "HOLD",
        "regime_label": "bull",
        "regime_gate": "CAUTION",
        "entry_quality": 0.5302,
        "entry_quality_label": "D",
        "decision_quality_label": "B",
        "allowed_layers": 0,
        "allowed_layers_reason": "entry_quality_below_trade_floor",
        "execution_guardrail_reason": "unsupported_exact_live_structure_bucket_blocks_trade",
    }
    drilldown = {
        "component_gap_attribution": {
            "remaining_gap_to_floor": 0.0198,
            "best_single_component": {
                "feature": "feat_4h_bias50",
                "required_score_delta_to_cross_floor": 0.066,
                "can_single_component_cross_floor": True,
            }
        }
    }
    bull_pocket = {
        "target_col": "simulated_pyramid_win",
        "live_context": {
            "regime_label": "bull",
            "regime_gate": "CAUTION",
            "entry_quality_label": "D",
            "execution_guardrail_reason": "unsupported_exact_live_structure_bucket_blocks_trade",
            "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
            "current_live_structure_bucket_rows": 0,
        },
        "support_pathology_summary": {
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 50,
            "exact_bucket_root_cause": "same_lane_shifted_to_neighbor_bucket",
            "preferred_support_cohort": "bull_exact_live_lane_proxy",
            "recommended_action": "維持 0 layers；優先查 exact bucket 缺口與 same-bucket pathology，而不是再重訓。",
        },
    }
    leaderboard_probe = {
        "alignment": {
            "support_governance_route": "exact_live_bucket_proxy_available",
            "bull_exact_live_bucket_proxy_rows": 4,
            "bull_exact_live_lane_proxy_rows": 418,
            "bull_support_neighbor_rows": 155,
        }
    }

    monkeypatch.setattr(
        q15_support_audit,
        "_load_recent_q15_support_history",
        lambda **kwargs: [kwargs["current_entry"]],
    )

    report = q15_support_audit.build_report(probe, drilldown, bull_pocket, leaderboard_probe)

    assert report["support_route"]["verdict"] == "exact_bucket_missing_proxy_reference_only"
    assert report["support_route"]["deployable"] is False
    assert report["support_route"]["preferred_support_cohort"] == "bull_live_exact_bucket_proxy"
    assert report["support_route"]["support_progress"]["status"] == "no_recent_comparable_history"
    assert report["support_route"]["support_progress"]["gap_to_minimum"] == 50
    assert report["floor_cross_legality"]["verdict"] == "math_cross_possible_but_illegal_without_exact_support"
    assert report["floor_cross_legality"]["best_single_component"] == "feat_4h_bias50"


def test_build_report_prefers_probe_live_bucket_over_stale_bull_pocket_context():
    probe = {
        "feature_timestamp": "2026-04-15 15:48:14",
        "target_col": "simulated_pyramid_win",
        "signal": "HOLD",
        "regime_label": "bull",
        "regime_gate": "CAUTION",
        "entry_quality": 0.5091,
        "entry_quality_label": "D",
        "decision_quality_label": "C",
        "allowed_layers": 0,
        "allowed_layers_reason": "entry_quality_below_trade_floor",
        "execution_guardrail_reason": "unsupported_exact_live_structure_bucket_blocks_trade",
        "decision_quality_scope_diagnostics": {
            "regime_label+regime_gate+entry_quality_label": {
                "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
                "current_live_structure_bucket_rows": 0,
            }
        },
    }
    drilldown = {
        "chosen_scope_summary": {
            "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
            "current_live_structure_bucket_rows": 0,
        },
        "component_gap_attribution": {
            "remaining_gap_to_floor": 0.0409,
            "best_single_component": {
                "feature": "feat_4h_bias50",
                "required_score_delta_to_cross_floor": 0.1363,
                "can_single_component_cross_floor": True,
            },
        },
    }
    bull_pocket = {
        "target_col": "simulated_pyramid_win",
        "live_context": {
            "regime_label": "bull",
            "regime_gate": "CAUTION",
            "entry_quality_label": "D",
            "execution_guardrail_reason": "bull_q35_no_deploy_governance",
            "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
            "current_live_structure_bucket_rows": 51,
        },
        "support_pathology_summary": {
            "minimum_support_rows": 50,
            "exact_bucket_root_cause": "exact_bucket_supported",
            "preferred_support_cohort": "exact_live_bucket",
            "recommended_action": "舊 q35 snapshot，不應覆蓋目前 q15 live bucket。",
        },
    }
    leaderboard_probe = {
        "alignment": {
            "support_governance_route": "exact_live_bucket_proxy_available",
            "bull_exact_live_bucket_proxy_rows": 4,
            "bull_exact_live_lane_proxy_rows": 418,
            "bull_support_neighbor_rows": 155,
        }
    }

    report = q15_support_audit.build_report(probe, drilldown, bull_pocket, leaderboard_probe)

    assert report["current_live"]["feature_timestamp"] == "2026-04-15 15:48:14"
    assert report["current_live"]["current_live_structure_bucket"] == "CAUTION|structure_quality_caution|q15"
    assert report["current_live"]["current_live_structure_bucket_rows"] == 0
    assert report["current_live"]["execution_guardrail_reason"] == "unsupported_exact_live_structure_bucket_blocks_trade"
    assert report["current_live"]["raw_features"] == {}
    assert report["support_route"]["verdict"] == "exact_bucket_missing_proxy_reference_only"
    assert report["support_route"]["current_live_structure_bucket_gap_to_minimum"] == 50
    assert report["floor_cross_legality"]["verdict"] == "math_cross_possible_but_illegal_without_exact_support"
    assert report["component_experiment"]["verdict"] == "reference_only_until_exact_support_ready"
    assert report["component_experiment"]["machine_read_answer"]["support_ready"] is False


def test_resolve_current_live_context_keeps_exact_scope_zero_rows_even_when_broader_scope_matches_bucket():
    probe = {
        "regime_label": "bull",
        "regime_gate": "CAUTION",
        "entry_quality_label": "D",
        "decision_quality_scope_diagnostics": {
            "regime_label+regime_gate+entry_quality_label": {
                "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
                "current_live_structure_bucket_rows": 0,
            }
        },
    }
    drilldown = {
        "chosen_scope_summary": {
            "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
            "current_live_structure_bucket_rows": 79,
        }
    }
    bull_pocket = {
        "live_context": {
            "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
            "current_live_structure_bucket_rows": 79,
        }
    }

    resolved = q15_support_audit._resolve_current_live_context(probe, drilldown, bull_pocket)

    assert resolved["current_live_structure_bucket"] == "CAUTION|structure_quality_caution|q15"
    assert resolved["current_live_structure_bucket_rows"] == 0


def test_build_report_prefers_explicit_probe_execution_guardrail_reason_over_stale_fallback():
    probe = {
        "feature_timestamp": "2026-04-16 23:00:23.100224",
        "target_col": "simulated_pyramid_win",
        "signal": "HOLD",
        "regime_label": "bull",
        "regime_gate": "CAUTION",
        "entry_quality": 0.3238,
        "entry_quality_label": "D",
        "decision_quality_label": "C",
        "allowed_layers": 0,
        "allowed_layers_reason": "entry_quality_below_trade_floor",
        "execution_guardrail_reason": None,
        "decision_quality_scope_diagnostics": {
            "regime_label+regime_gate+entry_quality_label": {
                "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
                "current_live_structure_bucket_rows": 77,
            }
        },
    }
    drilldown = {
        "generated_at": "2026-04-16 21:38:10.597255",
        "execution_guardrail_reason": "unsupported_live_structure_bucket_blocks_trade; under_minimum_exact_live_structure_bucket",
        "component_gap_attribution": {
            "remaining_gap_to_floor": 0.233,
            "best_single_component": {
                "feature": "feat_4h_bias50",
                "required_score_delta_to_cross_floor": 0.7767,
                "can_single_component_cross_floor": True,
            }
        },
    }
    bull_pocket = {
        "target_col": "simulated_pyramid_win",
        "live_context": {
            "regime_label": "bull",
            "regime_gate": "CAUTION",
            "entry_quality_label": "D",
            "execution_guardrail_reason": "unsupported_live_structure_bucket_blocks_trade",
            "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
            "current_live_structure_bucket_rows": 77,
        },
        "support_pathology_summary": {
            "minimum_support_rows": 50,
            "exact_bucket_root_cause": "exact_bucket_supported",
            "preferred_support_cohort": "exact_live_bucket",
            "recommended_action": "可回到 exact live bucket 直接治理與驗證。",
        },
    }
    leaderboard_probe = {
        "alignment": {
            "support_governance_route": "exact_live_bucket_present_but_below_minimum",
            "bull_exact_live_bucket_proxy_rows": 1,
            "bull_exact_live_lane_proxy_rows": 58,
            "bull_support_neighbor_rows": 0,
        }
    }

    report = q15_support_audit.build_report(probe, drilldown, bull_pocket, leaderboard_probe)

    assert report["current_live"]["execution_guardrail_reason"] is None
    assert report["support_route"]["verdict"] == "exact_bucket_supported"
    assert report["support_route"]["support_governance_route"] == "exact_live_bucket_supported"
    assert report["support_route"]["exact_bucket_root_cause"] == "exact_bucket_supported"
    assert report["support_route"]["recommended_action"].startswith("保持 current_live_structure_bucket_rows >= minimum_support_rows")
    assert report["component_experiment"]["verdict"] == "exact_supported_component_experiment_ready"


def test_refresh_live_drilldown_if_needed_regenerates_stale_artifact(tmp_path, monkeypatch):
    probe = {"feature_timestamp": "2026-04-16T23:00:23.100224+00:00"}
    stale = {"generated_at": "2026-04-16T21:38:10.597255+00:00"}
    refreshed = {"generated_at": "2026-04-16T23:00:23.100224+00:00", "component_gap_attribution": {"remaining_gap_to_floor": 0.1}}
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    script_path = scripts_dir / "live_decision_quality_drilldown.py"
    script_path.write_text(
        "from pathlib import Path\n"
        f"OUT_JSON = Path({str((tmp_path / 'live_decision_quality_drilldown.json')).__repr__()})\n"
        "def main():\n"
        f"    OUT_JSON.write_text({(json.dumps(refreshed, ensure_ascii=False) + chr(10))!r}, encoding='utf-8')\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(q15_support_audit, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(q15_support_audit, "DRILLDOWN_PATH", tmp_path / "live_decision_quality_drilldown.json")

    result = q15_support_audit._refresh_live_drilldown_if_needed(probe, stale)

    assert result == refreshed


def test_build_report_support_ready_exposes_component_experiment_machine_read_answer():
    probe = {
        "feature_timestamp": "2026-04-15 15:25:08",
        "target_col": "simulated_pyramid_win",
        "signal": "HOLD",
        "regime_label": "bull",
        "regime_gate": "CAUTION",
        "entry_quality": 0.4959,
        "entry_quality_label": "D",
        "decision_quality_label": "C",
        "allowed_layers": 0,
        "allowed_layers_reason": "entry_quality_below_trade_floor",
        "execution_guardrail_reason": "bull_q35_no_deploy_governance",
        "decision_quality_scope_diagnostics": {
            "regime_label+regime_gate+entry_quality_label": {
                "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
                "current_live_structure_bucket_rows": 50,
                "current_live_structure_bucket_metrics": {
                    "rows": 50,
                    "win_rate": 0.93,
                    "avg_quality": 0.48,
                    "avg_pnl": 0.0052,
                },
                "exact_lane_bucket_diagnostics": {
                    "buckets": {
                        "CAUTION|structure_quality_caution|q15": {
                            "rows": 50,
                            "win_rate": 0.93,
                            "avg_quality": 0.48,
                            "avg_pnl": 0.0052,
                        },
                        "CAUTION|structure_quality_caution|q35": {
                            "rows": 80,
                            "win_rate": 0.81,
                            "avg_quality": 0.31,
                            "avg_pnl": 0.0021,
                        },
                    }
                },
            }
        },
    }
    drilldown = {
        "component_gap_attribution": {
            "trade_floor": 0.55,
            "remaining_gap_to_floor": 0.0541,
            "best_single_component": {
                "feature": "feat_4h_bias50",
                "required_score_delta_to_cross_floor": 0.1803,
                "can_single_component_cross_floor": True,
            },
            "bias50_floor_counterfactual": {
                "entry_if_bias50_fully_relaxed": 0.7208,
                "layers_if_bias50_fully_relaxed": 2,
                "required_bias50_cap_for_floor": 0.247,
            },
        }
    }
    bull_pocket = {
        "target_col": "simulated_pyramid_win",
        "support_pathology_summary": {
            "minimum_support_rows": 50,
            "exact_bucket_root_cause": "exact_bucket_supported",
            "preferred_support_cohort": "exact_live_bucket",
            "recommended_action": "可回到 exact live bucket 直接治理與驗證。",
        },
    }
    leaderboard_probe = {
        "alignment": {
            "support_governance_route": "exact_live_bucket_supported",
            "bull_exact_live_bucket_proxy_rows": 171,
            "bull_exact_live_lane_proxy_rows": 434,
            "bull_support_neighbor_rows": 0,
        }
    }

    report = q15_support_audit.build_report(probe, drilldown, bull_pocket, leaderboard_probe)

    assert report["scope_applicability"]["status"] == "current_live_q15_lane_active"
    assert report["scope_applicability"]["active_for_current_live_row"] is True
    assert report["support_route"]["verdict"] == "exact_bucket_supported"
    assert report["floor_cross_legality"]["verdict"] == "legal_component_experiment_after_support_ready"
    assert report["component_experiment"]["verdict"] == "exact_supported_component_experiment_ready"
    assert report["component_experiment"]["feature"] == "feat_4h_bias50"
    assert report["component_experiment"]["machine_read_answer"]["support_ready"] is True
    assert report["component_experiment"]["machine_read_answer"]["entry_quality_ge_0_55"] is True
    assert report["component_experiment"]["machine_read_answer"]["allowed_layers_gt_0"] is True
    assert report["component_experiment"]["machine_read_answer"]["preserves_positive_discrimination"] is True
    assert report["component_experiment"]["machine_read_answer"]["preserves_positive_discrimination_status"] == "verified_exact_lane_bucket_dominance"
    assert report["component_experiment"]["positive_discrimination_evidence"]["comparisons"][0]["bucket"] == "CAUTION|structure_quality_caution|q35"


def test_build_report_keeps_support_reference_only_while_reusing_chosen_scope_metrics_for_q15_positive_discrimination():
    probe = {
        "feature_timestamp": "2026-04-15 17:35:54",
        "target_col": "simulated_pyramid_win",
        "signal": "BUY",
        "regime_label": "bull",
        "regime_gate": "CAUTION",
        "entry_quality": 0.55,
        "entry_quality_label": "C",
        "decision_quality_label": "D",
        "allowed_layers": 0,
        "allowed_layers_reason": "decision_quality_below_trade_floor",
        "execution_guardrail_reason": "decision_quality_below_trade_floor",
        "decision_quality_scope_diagnostics": {
            "regime_label+regime_gate+entry_quality_label": {
                "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
                "current_live_structure_bucket_rows": 0,
                "current_live_structure_bucket_metrics": None,
                "exact_lane_bucket_diagnostics": {
                    "buckets": {
                        "CAUTION|structure_quality_caution|q35": {
                            "rows": 80,
                            "win_rate": 0.81,
                            "avg_quality": 0.31,
                            "avg_pnl": 0.0021,
                        }
                    }
                },
            }
        },
    }
    drilldown = {
        "chosen_scope_summary": {
            "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
            "current_live_structure_bucket_rows": 50,
            "current_live_structure_bucket_metrics": {
                "win_rate": 0.93,
                "avg_quality": 0.48,
                "avg_pnl": 0.0052,
            },
        },
        "component_gap_attribution": {
            "trade_floor": 0.55,
            "remaining_gap_to_floor": 0.0541,
            "best_single_component": {
                "feature": "feat_4h_bias50",
                "required_score_delta_to_cross_floor": 0.1803,
                "can_single_component_cross_floor": True,
            },
            "bias50_floor_counterfactual": {
                "entry_if_bias50_fully_relaxed": 0.7208,
                "layers_if_bias50_fully_relaxed": 2,
                "required_bias50_cap_for_floor": 0.247,
            },
        },
    }
    bull_pocket = {
        "target_col": "simulated_pyramid_win",
        "support_pathology_summary": {
            "minimum_support_rows": 50,
            "exact_bucket_root_cause": "exact_bucket_supported",
            "preferred_support_cohort": "exact_live_bucket",
            "recommended_action": "可回到 exact live bucket 直接治理與驗證。",
        },
    }
    leaderboard_probe = {
        "alignment": {
            "support_governance_route": "exact_live_bucket_supported",
            "bull_exact_live_bucket_proxy_rows": 171,
            "bull_exact_live_lane_proxy_rows": 434,
            "bull_support_neighbor_rows": 0,
        }
    }

    report = q15_support_audit.build_report(probe, drilldown, bull_pocket, leaderboard_probe)

    assert report["support_route"]["verdict"] == "exact_bucket_missing_proxy_reference_only"
    assert report["component_experiment"]["machine_read_answer"]["support_ready"] is False
    assert report["component_experiment"]["machine_read_answer"]["preserves_positive_discrimination"] is None
    assert report["component_experiment"]["positive_discrimination_evidence"]["current_bucket_metrics"]["win_rate"] == 0.93
    assert report["component_experiment"]["positive_discrimination_evidence"]["comparisons"][0]["bucket"] == "CAUTION|structure_quality_caution|q35"


def test_build_report_falls_back_to_probe_exact_lane_bucket_diagnostics_for_q15_positive_discrimination():
    probe = {
        "feature_timestamp": "2026-04-18 12:29:28.706281",
        "target_col": "simulated_pyramid_win",
        "signal": "BUY",
        "regime_label": "bull",
        "regime_gate": "CAUTION",
        "entry_quality": 0.55,
        "entry_quality_label": "C",
        "decision_quality_label": "D",
        "allowed_layers": 0,
        "allowed_layers_reason": "decision_quality_below_trade_floor",
        "execution_guardrail_reason": "decision_quality_below_trade_floor",
        "decision_quality_scope_diagnostics": {
            "regime_label+regime_gate+entry_quality_label": {
                "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
                "current_live_structure_bucket_rows": 0,
                "current_live_structure_bucket_metrics": None,
                "exact_lane_bucket_diagnostics": {
                    "buckets": {}
                },
            }
        },
        "decision_quality_exact_live_lane_bucket_diagnostics": {
            "buckets": {
                "CAUTION|structure_quality_caution|q15": {
                    "rows": 95,
                    "win_rate": 0.9579,
                    "avg_quality": 0.5977,
                    "avg_pnl": 0.0158,
                },
                "CAUTION|structure_quality_caution|q35": {
                    "rows": 101,
                    "win_rate": 0.4554,
                    "avg_quality": 0.157,
                    "avg_pnl": 0.0035,
                },
            }
        },
    }
    drilldown = {
        "chosen_scope_summary": {
            "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
            "current_live_structure_bucket_rows": 95,
            "current_live_structure_bucket_metrics": {
                "win_rate": 0.9579,
                "avg_quality": 0.5977,
                "avg_pnl": 0.0158,
            },
        },
        "component_gap_attribution": {
            "trade_floor": 0.55,
            "remaining_gap_to_floor": 0.2013,
            "best_single_component": {
                "feature": "feat_4h_bias50",
                "required_score_delta_to_cross_floor": 0.671,
                "can_single_component_cross_floor": True,
            },
            "bias50_floor_counterfactual": {
                "entry_if_bias50_fully_relaxed": 0.55,
                "layers_if_bias50_fully_relaxed": 1,
                "required_bias50_cap_for_floor": None,
            },
        },
    }
    bull_pocket = {
        "target_col": "simulated_pyramid_win",
        "support_pathology_summary": {
            "minimum_support_rows": 50,
            "exact_bucket_root_cause": "exact_bucket_supported",
            "preferred_support_cohort": "exact_live_bucket",
            "recommended_action": "可回到 exact live bucket 直接治理與驗證。",
        },
    }
    leaderboard_probe = {
        "alignment": {
            "support_governance_route": "exact_live_bucket_supported",
            "bull_exact_live_bucket_proxy_rows": 0,
            "bull_exact_live_lane_proxy_rows": 1,
            "bull_support_neighbor_rows": 1,
        }
    }

    report = q15_support_audit.build_report(probe, drilldown, bull_pocket, leaderboard_probe)

    assert report["component_experiment"]["machine_read_answer"]["preserves_positive_discrimination"] is True
    assert report["component_experiment"]["machine_read_answer"]["preserves_positive_discrimination_status"] == "verified_exact_lane_bucket_dominance"
    assert report["component_experiment"]["positive_discrimination_evidence"]["current_bucket_metrics"]["win_rate"] == 0.9579
    assert report["component_experiment"]["positive_discrimination_evidence"]["comparisons"][0]["bucket"] == "CAUTION|structure_quality_caution|q35"


def test_build_report_marks_q15_experiment_as_standby_when_current_live_row_is_q35():
    probe = {
        "feature_timestamp": "2026-04-15 17:35:54",
        "target_col": "simulated_pyramid_win",
        "signal": "HOLD",
        "regime_label": "bull",
        "regime_gate": "CAUTION",
        "entry_quality": 0.4115,
        "entry_quality_label": "D",
        "decision_quality_label": "C",
        "allowed_layers": 0,
        "allowed_layers_reason": "entry_quality_below_trade_floor",
        "decision_quality_scope_diagnostics": {
            "regime_label+regime_gate+entry_quality_label": {
                "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
                "current_live_structure_bucket_rows": 50,
            }
        },
    }
    drilldown = {
        "component_gap_attribution": {
            "trade_floor": 0.55,
            "remaining_gap_to_floor": 0.1385,
            "best_single_component": {
                "feature": "feat_4h_bias50",
                "required_score_delta_to_cross_floor": 0.4617,
                "can_single_component_cross_floor": True,
            },
            "bias50_floor_counterfactual": {
                "entry_if_bias50_fully_relaxed": 0.6411,
                "layers_if_bias50_fully_relaxed": 1,
                "required_bias50_cap_for_floor": -1.0815,
            },
        }
    }
    bull_pocket = {
        "target_col": "simulated_pyramid_win",
        "support_pathology_summary": {
            "minimum_support_rows": 50,
            "exact_bucket_root_cause": "exact_bucket_supported",
            "preferred_support_cohort": "exact_live_bucket",
            "recommended_action": "q15 support ready, but current live row is no longer in q15.",
        },
    }
    leaderboard_probe = {
        "alignment": {
            "support_governance_route": "exact_live_bucket_supported",
            "bull_exact_live_bucket_proxy_rows": 178,
            "bull_exact_live_lane_proxy_rows": 441,
            "bull_support_neighbor_rows": 0,
        }
    }

    report = q15_support_audit.build_report(probe, drilldown, bull_pocket, leaderboard_probe)

    assert report["scope_applicability"]["status"] == "current_live_not_q15_lane"
    assert report["scope_applicability"]["active_for_current_live_row"] is False
    assert report["support_route"]["verdict"] == "exact_bucket_supported"
    assert report["component_experiment"]["verdict"] == "exact_supported_component_experiment_ready_but_current_live_not_q15"
    assert report["component_experiment"]["machine_read_answer"]["support_ready"] is True
    assert report["component_experiment"]["machine_read_answer"]["entry_quality_ge_0_55"] is True
    assert report["component_experiment"]["machine_read_answer"]["allowed_layers_gt_0"] is True
    assert report["component_experiment"]["machine_read_answer"]["preserves_positive_discrimination_status"] == "not_applicable_current_live_not_q15_lane"
    assert "q35 current-live blocker" in report["next_action"]
