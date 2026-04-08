import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from config import load_config
from database.models import FeaturesNormalized, init_db
from server.senses import SensesEngine, normalize_feature


@pytest.fixture(scope="module")
def session():
    cfg = load_config()
    db = init_db(cfg["database"]["url"])
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def engine(session):
    e = SensesEngine()
    e.set_db(session)
    return e


def test_senses_engine_returns_real_scores(engine):
    scores = engine.calculate_all_scores()

    assert scores, "scores should not be empty"
    assert all(0.0 <= value <= 1.0 for value in scores.values())
    assert any(abs(value - 0.5) > 1e-6 for value in scores.values()), (
        "expected at least one live score to differ from the default 0.5"
    )


def test_generate_advice_returns_structured_payload(engine):
    scores = engine.calculate_all_scores()
    rec = engine.generate_advice(scores)

    assert 0 <= rec["score"] <= 100
    assert rec["action"] in {"strong_buy", "buy", "hold", "reduce", "hold_long"}
    assert rec["summary"]
    assert isinstance(rec["descriptions"], list)
    assert len(rec["descriptions"]) > 0


@pytest.mark.parametrize(
    ("legacy_key", "sample_value"),
    [
        ("feat_eye_dist", 0.02),
        ("feat_ear_zscore", 0.01),
        ("feat_nose_sigmoid", 0.6),
        ("feat_tongue_pct", 0.02),
        ("feat_body_roc", 0.4),
    ],
)
def test_normalize_feature_supports_legacy_feature_names(legacy_key, sample_value):
    normalized = normalize_feature(sample_value, legacy_key)

    assert 0.0 <= normalized <= 1.0
    assert normalize_feature(None, legacy_key) == 0.5


def test_latest_features_row_exists(session):
    row = session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp.desc()).first()

    assert row is not None
    # Canonical columns used by the new engine should exist on the ORM row.
    assert hasattr(row, "feat_eye")
    assert hasattr(row, "feat_ear")
    assert hasattr(row, "feat_nose")
    assert hasattr(row, "feat_tongue")
    assert hasattr(row, "feat_body")
