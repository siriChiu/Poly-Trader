from __future__ import annotations

import hashlib
from pathlib import Path

from execution.strategy_bundle import build_strategy_bundle


def test_strategy_bundle_prefers_exact_backtest_model_artifact(tmp_path: Path):
    model_path = tmp_path / "exact.pkl"
    model_path.write_bytes(b"exact-backtest-model")
    model_sha = hashlib.sha256(model_path.read_bytes()).hexdigest()
    entry = {
        "schema_version": 3,
        "name": "Exact Hybrid",
        "slug": "exact-hybrid",
        "definition": {"type": "hybrid", "params": {"model_name": "random_forest"}},
        "metadata": {"strategy_type": "hybrid", "model_name": "random_forest"},
        "last_results": {
            "backtest_range": {"effective": {"start": "2026-01-01", "end": "2026-02-01"}},
            "fitted_model_artifact": {
                "source": "strategy_lab_backtest",
                "model_name": "random_forest",
                "model_path": str(model_path),
                "model_sha256": model_sha,
                "feature_schema_sha256": "feature-schema-1",
                "training_data_sha256": "training-data-1",
            },
        },
    }

    bundle = build_strategy_bundle(entry, "trend", db_path=str(tmp_path / "missing.db"))

    assert bundle["model_artifact"]["status"] == "exact_backtest_artifact_available"
    assert bundle["model_artifact"]["source"] == "strategy_lab_backtest"
    assert bundle["model_artifact"]["artifacts"][0]["path"] == str(model_path)
    assert bundle["model_artifact"]["artifacts"][0]["sha256"] == model_sha
    assert not any("model artifact" in blocker for blocker in bundle["parity_blockers"])
