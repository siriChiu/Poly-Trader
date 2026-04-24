import json

from server.routes import api as api_module


def test_q15_root_cause_loader_accepts_non_q15_current_bucket(tmp_path, monkeypatch):
    payload = {
        "generated_at": "2026-04-22T00:00:00Z",
        "verdict": "same_lane_neighbor_bucket_dominates",
        "candidate_patch_type": "structure_component_scoring",
        "candidate_patch_feature": "feat_4h_bb_pct_b",
        "reason": "same exact lane 有明顯鄰近 bucket 樣本。",
        "verify_next": "比較 current row 與 dominant neighbor bucket 的 4H component 差值。",
        "current_live": {
            "structure_bucket": "CAUTION|base_caution_regime_or_bias|q00",
            "gap_to_q35_boundary": 0.2159,
        },
        "exact_live_lane": {
            "dominant_neighbor_bucket": "CAUTION|base_caution_regime_or_bias|q35",
            "dominant_neighbor_rows": 1147,
            "near_boundary_rows": 363,
        },
        "candidate_patch": {
            "type": "structure_component_scoring",
            "feature": "feat_4h_bb_pct_b",
        },
        "artifact_context_freshness": {
            "verdict": "current_context",
            "mismatched_fields": [],
            "reference_mismatched_fields": ["current_live_structure_bucket", "regime_gate"],
            "reference_artifact_warning": "bull_4h_pocket_ablation live_context is stale/reference-only; current q15 root-cause used fresh live_predict_probe support truth.",
        },
    }
    artifact = tmp_path / "q15_bucket_root_cause.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(api_module, "_Q15_BUCKET_ROOT_CAUSE_PATH", artifact)

    summary = api_module._load_q15_bucket_root_cause_summary("CAUTION|base_caution_regime_or_bias|q00")

    assert summary is not None
    assert summary["current_live_structure_bucket"] == "CAUTION|base_caution_regime_or_bias|q00"
    assert summary["verdict"] == "same_lane_neighbor_bucket_dominates"
    assert summary["candidate_patch_feature"] == "feat_4h_bb_pct_b"
    assert summary["artifact_context_freshness_verdict"] == "current_context"
    assert summary["artifact_context_freshness_mismatched_fields"] == []
    assert summary["reference_mismatched_fields"] == ["current_live_structure_bucket", "regime_gate"]
    assert "reference-only" in summary["reference_artifact_warning"]


def test_enrich_confidence_with_q15_root_cause_publishes_generic_alias(tmp_path, monkeypatch):
    payload = {
        "generated_at": "2026-04-22T00:00:00Z",
        "verdict": "same_lane_neighbor_bucket_dominates",
        "candidate_patch_type": "structure_component_scoring",
        "candidate_patch_feature": "feat_4h_bb_pct_b",
        "reason": "same exact lane 有明顯鄰近 bucket 樣本。",
        "verify_next": "比較 current row 與 dominant neighbor bucket 的 4H component 差值。",
        "current_live": {
            "structure_bucket": "CAUTION|base_caution_regime_or_bias|q00",
            "gap_to_q35_boundary": 0.2159,
        },
        "exact_live_lane": {
            "dominant_neighbor_bucket": "CAUTION|base_caution_regime_or_bias|q35",
            "dominant_neighbor_rows": 1147,
            "near_boundary_rows": 363,
        },
        "candidate_patch": {
            "type": "structure_component_scoring",
            "feature": "feat_4h_bb_pct_b",
        },
        "artifact_context_freshness": {
            "verdict": "current_context",
            "mismatched_fields": [],
            "reference_mismatched_fields": ["current_live_structure_bucket", "regime_gate"],
            "reference_artifact_warning": "bull_4h_pocket_ablation live_context is stale/reference-only; current q15 root-cause used fresh live_predict_probe support truth.",
        },
    }
    artifact = tmp_path / "q15_bucket_root_cause.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(api_module, "_Q15_BUCKET_ROOT_CAUSE_PATH", artifact)

    result = api_module._enrich_confidence_with_q15_bucket_root_cause(
        {
            "current_live_structure_bucket": "CAUTION|base_caution_regime_or_bias|q00",
            "deployment_blocker_details": {},
        }
    )

    assert result["q15_bucket_root_cause"]["current_live_structure_bucket"] == "CAUTION|base_caution_regime_or_bias|q00"
    assert result["current_bucket_root_cause"]["current_live_structure_bucket"] == "CAUTION|base_caution_regime_or_bias|q00"
    assert result["deployment_blocker_details"]["current_bucket_root_cause"]["verdict"] == "same_lane_neighbor_bucket_dominates"
    assert result["current_bucket_root_cause"]["artifact_context_freshness_verdict"] == "current_context"
    assert result["current_bucket_root_cause"]["reference_mismatched_fields"] == ["current_live_structure_bucket", "regime_gate"]
