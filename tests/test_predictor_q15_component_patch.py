import json

from model import predictor


Q15_BUCKET = "CAUTION|base_caution_regime_or_bias|q15"


def _write_q15_audit(path, *, bucket=Q15_BUCKET, regime="chop", timestamp="2026-05-13 12:02:08.937098"):
    payload = {
        "generated_at": timestamp,
        "scope_applicability": {
            "status": "current_live_q15_lane_active",
            "active_for_current_live_row": True,
            "current_structure_bucket": bucket,
        },
        "current_live": {
            "feature_timestamp": timestamp,
            "regime_label": regime,
            "current_live_structure_bucket": bucket,
            "raw_features": {
                "feat_4h_bias50": -0.4221,
                "feat_nose": 0.4159,
                "feat_pulse": 0.3835,
                "feat_ear": 0.0027,
            },
        },
        "support_route": {"verdict": "exact_bucket_supported", "deployable": True},
        "floor_cross_legality": {
            "verdict": "legal_component_experiment_after_support_ready",
            "legal_to_relax_runtime_gate": True,
            "best_single_component_required_score_delta": 0.2257,
        },
        "component_experiment": {
            "verdict": "exact_supported_component_experiment_ready",
            "feature": "feat_4h_bias50",
            "mode": "single_component_headroom",
            "machine_read_answer": {
                "support_ready": True,
                "entry_quality_ge_0_55": True,
                "allowed_layers_gt_0": True,
                "preserves_positive_discrimination": True,
                "preserves_positive_discrimination_status": "verified_exact_lane_bucket_dominance",
            },
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _features(*, bucket=Q15_BUCKET, regime="chop", timestamp="2026-05-13 12:02:08.937098"):
    return {
        "timestamp": timestamp,
        "regime_label": regime,
        "current_live_structure_bucket": bucket,
        "feat_4h_bias50": -0.4221,
        "feat_nose": 0.4159,
        "feat_pulse": 0.3835,
        "feat_ear": 0.0027,
    }


def _entry_quality_breakdown():
    return {
        "entry_quality": 0.4823,
        "base_quality": 0.5824,
        "structure_quality": 0.1819,
        "base_quality_weight": 0.75,
        "structure_quality_weight": 0.25,
        "trade_floor_gap": -0.0677,
        "base_components": [
            {"feature": "feat_4h_bias50", "normalized_score": 0.5644, "weight": 0.4},
            {"feature": "feat_nose", "normalized_score": 0.5841, "weight": 0.18},
            {"feature": "feat_pulse", "normalized_score": 0.3835, "weight": 0.27},
            {"feature": "feat_ear", "normalized_score": 0.9865, "weight": 0.15},
        ],
    }


def test_q15_exact_supported_component_patch_applies_to_current_non_legacy_q15_lane(monkeypatch, tmp_path):
    """The live q15 lane is not always the legacy structure_quality bucket.

    HB#1188 current-live support is exact-supported for CAUTION|base_caution_regime_or_bias|q15
    in chop regime.  The runtime patch must follow the audited current q15 bucket instead of
    fail-closing on a hard-coded bull/structure_quality bucket.
    """
    audit_path = tmp_path / "q15_support_audit.json"
    _write_q15_audit(audit_path)
    monkeypatch.setattr(predictor, "Q15_SUPPORT_AUDIT_PATH", audit_path)

    updated, meta = predictor._maybe_apply_q15_exact_supported_component_patch(
        _features(),
        "CAUTION",
        Q15_BUCKET,
        _entry_quality_breakdown(),
    )

    assert meta is not None
    assert meta["applied"] is True
    assert meta["source"] == "q15_support_audit.exact_supported_component_experiment_ready"
    assert meta["feature"] == "feat_4h_bias50"
    assert updated["entry_quality"] >= 0.55
    assert updated["q15_exact_supported_component_patch"]["machine_read_answer"]["preserves_positive_discrimination"] is True


def test_q15_exact_supported_component_patch_rejects_audit_bucket_mismatch(monkeypatch, tmp_path):
    audit_path = tmp_path / "q15_support_audit.json"
    _write_q15_audit(audit_path, bucket="CAUTION|structure_quality_caution|q15")
    monkeypatch.setattr(predictor, "Q15_SUPPORT_AUDIT_PATH", audit_path)

    original = _entry_quality_breakdown()
    updated, meta = predictor._maybe_apply_q15_exact_supported_component_patch(
        _features(),
        "CAUTION",
        Q15_BUCKET,
        original,
    )

    assert meta is None
    assert updated == original


def test_q15_exact_supported_audit_overrides_stale_under_minimum_scope_rows(monkeypatch, tmp_path):
    """Support closure from q15 audit must prevent stale 2-row DQ scope counts from re-blocking support."""
    audit_path = tmp_path / "q15_support_audit.json"
    _write_q15_audit(audit_path)
    audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
    audit_payload["support_route"]["support_progress"] = {
        "status": "exact_supported",
        "current_rows": 95,
        "minimum_support_rows": 50,
        "gap_to_minimum": 0,
    }
    audit_payload["current_live"]["current_live_structure_bucket_rows"] = 95
    audit_path.write_text(json.dumps(audit_payload), encoding="utf-8")
    monkeypatch.setattr(predictor, "Q15_SUPPORT_AUDIT_PATH", audit_path)

    decision_profile = {
        "structure_bucket": Q15_BUCKET,
        "regime_label": "chop",
        "regime_gate": "CAUTION",
        "entry_quality": 0.55,
        "entry_quality_label": "C",
        "entry_quality_components": {"trade_floor": 0.55},
        "allowed_layers": 1,
        "allowed_layers_reason": "entry_quality_C_single_layer",
        "q15_exact_supported_component_patch_applied": True,
    }
    decision_quality_contract = {
        "decision_quality_label": "D",
        "decision_quality_score": 0.3031,
        "decision_quality_structure_bucket_support_mode": "exact_bucket_present_but_below_minimum",
        "decision_quality_structure_bucket_guardrail_applied": True,
        "decision_quality_exact_live_structure_bucket_support_rows": 2,
        "decision_quality_scope_diagnostics": {
            "regime_label+regime_gate+entry_quality_label": {
                "current_live_structure_bucket": Q15_BUCKET,
                "current_live_structure_bucket_rows": 2,
                "alerts": [],
            }
        },
    }

    blocker = predictor._infer_deployment_blocker(decision_profile, decision_quality_contract)

    assert blocker["type"] == "decision_quality_below_trade_floor"
    assert blocker["support_route_deployable"] is True
    assert blocker["current_live_structure_bucket_rows"] == 95
    assert blocker["exact_live_structure_bucket_rows"] == 95
    assert blocker["current_live_structure_bucket_gap_to_minimum"] == 0
    assert blocker["q15_exact_supported_component_patch_applied"] is True
