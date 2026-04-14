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
    assert alignment["support_governance_route"] == "exact_live_bucket_proxy_available"



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
    monkeypatch.setattr(hb_leaderboard_candidate_probe, "_build_alignment", lambda top_model: {"dual_profile_state": "aligned"})

    with warnings.catch_warnings(record=True) as caught:
        rc = hb_leaderboard_candidate_probe.main()

    assert rc == 0
    assert out_path.exists()
    saved = json.loads(out_path.read_text(encoding="utf-8"))
    assert saved["top_model"]["selected_feature_profile"] == "core_only"
    assert not caught
