import json
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


def test_load_tw_ic_guardrail_reads_dynamic_window_and_recent_drift(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    dw_result = data_dir / "dw_result.json"
    drift_report = data_dir / "recent_drift_report.json"
    dw_result.write_text(
        json.dumps(
            {
                "raw_best_n": 600,
                "recommended_best_n": 5000,
                "guardrail_policy": {"disqualifying_alerts": ["constant_target", "regime_concentration"]},
                "600": {"alerts": ["label_imbalance", "regime_concentration"], "distribution_guardrail": True},
            }
        ),
        encoding="utf-8",
    )
    drift_report.write_text(
        json.dumps(
            {
                "primary_window": {
                    "window": "100",
                    "alerts": ["constant_target", "regime_concentration"],
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(train_module, "DW_RESULT_PATH", dw_result)
    monkeypatch.setattr(train_module, "RECENT_DRIFT_REPORT_PATH", drift_report)

    guardrail = train_module._load_tw_ic_guardrail()

    assert guardrail["recommended_best_n"] == 5000
    assert guardrail["raw_best_n"] == 600
    assert guardrail["raw_best_guardrailed"] is True
    assert guardrail["should_dampen_recent_window"] is True
    assert "recent_window=100" in guardrail["guardrail_reason"]



def test_build_time_decay_weights_damps_guardrailed_recent_window():
    weights, metadata = train_module._build_time_decay_weights(
        10,
        tau=2,
        guardrail={
            "primary_window": 3,
            "recommended_best_n": 5,
            "raw_best_n": 2,
            "should_dampen_recent_window": True,
            "guardrail_reason": "recent_window=3 alerts=['constant_target']",
        },
    )

    assert metadata["applied"] is True
    assert metadata["damped_recent_rows"] == 3
    assert metadata["recommended_best_n"] == 5
    assert weights[-1] == weights[-2] == weights[-3]
    assert weights[-1] < weights[-4]
