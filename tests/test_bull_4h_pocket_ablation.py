import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "bull_4h_pocket_ablation.py"
spec = importlib.util.spec_from_file_location("bull_4h_pocket_ablation_test_module", MODULE_PATH)
bull_4h_pocket_ablation = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(bull_4h_pocket_ablation)


def test_load_frame_accepts_feature_group_source_meta(monkeypatch):
    x = bull_4h_pocket_ablation.pd.DataFrame(
        {
            "feat_eye": [0.1, 0.2],
            "feat_4h_bias50": [0.3, 0.4],
        }
    )
    y = bull_4h_pocket_ablation.pd.Series([1, 0])
    regimes = bull_4h_pocket_ablation.pd.Series(["bull", "bear"])
    source_meta = {"target_col": "simulated_pyramid_win"}

    monkeypatch.setattr(
        bull_4h_pocket_ablation.feature_group_module,
        "_load_training_frame",
        lambda: (x.copy(), y.copy(), regimes.copy(), source_meta.copy()),
    )

    frame, got_y, got_regimes = bull_4h_pocket_ablation._load_frame()

    assert list(frame["regime_label"]) == ["bull", "bear"]
    assert got_y.tolist() == [1, 0]
    assert got_regimes.tolist() == ["bull", "bear"]


def test_load_frame_with_source_meta_returns_source_meta(monkeypatch):
    x = bull_4h_pocket_ablation.pd.DataFrame({"feat_eye": [0.1]})
    y = bull_4h_pocket_ablation.pd.Series([1])
    regimes = bull_4h_pocket_ablation.pd.Series(["bull"])
    source_meta = {
        "label_rows": 21913,
        "latest_label_timestamp": "2026-04-17 04:05:06",
        "horizon_minutes": 1440,
        "target_col": "simulated_pyramid_win",
    }

    monkeypatch.setattr(
        bull_4h_pocket_ablation.feature_group_module,
        "_load_training_frame",
        lambda: (x.copy(), y.copy(), regimes.copy(), source_meta.copy()),
    )

    frame, got_y, got_regimes, got_source_meta = bull_4h_pocket_ablation._load_frame_with_source_meta()

    assert list(frame["regime_label"]) == ["bull"]
    assert got_y.tolist() == [1]
    assert got_regimes.tolist() == ["bull"]
    assert got_source_meta == source_meta
