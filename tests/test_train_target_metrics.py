from pathlib import Path
import sqlite3

import pandas as pd

from model import train as train_module


class _DummyModel:
    import numpy as _np
    feature_importances_ = _np.array([0.6, 0.4])

    def get_params(self):
        return {"n_estimators": 5, "max_depth": 2}

    def predict(self, X):
        return [1 if i % 2 else 0 for i in range(len(X))]


class _DummyFoldModel:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def fit(self, X, y, sample_weight=None):
        return self

    def predict(self, X):
        return [1 if i % 2 else 0 for i in range(len(X))]


def test_run_training_writes_target_specific_last_metrics(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("model").mkdir()
    conn = sqlite3.connect("poly_trader.db")
    conn.execute("CREATE TABLE model_metrics (timestamp TEXT, train_accuracy REAL, cv_accuracy REAL, cv_std REAL, n_features INTEGER, notes TEXT)")
    conn.commit()
    conn.close()

    X = pd.DataFrame({"feat_a": [0.1] * 80, "feat_b": [0.2] * 80})
    y = pd.Series(([0, 1] * 40), name="simulated_pyramid_win")
    y_return = pd.Series([0.01] * 80)

    monkeypatch.setattr(train_module, "load_training_data", lambda *args, **kwargs: (X, y, y_return))
    monkeypatch.setattr(train_module, "train_xgboost", lambda X, y: _DummyModel())
    monkeypatch.setattr(train_module, "fit_probability_calibrator", lambda model, X, y: {"kind": "stub"})
    monkeypatch.setattr(train_module, "save_model", lambda payload: None)
    monkeypatch.setattr(train_module.xgb, "XGBClassifier", _DummyFoldModel)

    assert train_module.run_training(session=None, target_col="simulated_pyramid_win") is True

    metrics = Path("model/last_metrics.json").read_text(encoding="utf-8")
    assert '"target_col": "simulated_pyramid_win"' in metrics
    assert '"n_features": 2' in metrics
