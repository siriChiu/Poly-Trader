import importlib.util
import json
import warnings
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hb_leaderboard_candidate_probe.py"
spec = importlib.util.spec_from_file_location("hb_leaderboard_candidate_probe_test_module", MODULE_PATH)
hb_leaderboard_candidate_probe = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(hb_leaderboard_candidate_probe)


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
