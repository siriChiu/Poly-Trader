import sys
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from model import predictor as predictor_mod
from model import train as train_mod


def test_predictor_base_features_cover_training_features():
    missing = sorted(set(train_mod.FEATURE_COLS) - set(predictor_mod.BASE_FEATURE_COLS))
    assert missing == [], f"predictor BASE_FEATURE_COLS missing training features: {missing}"


def test_predictor_lag_features_cover_training_lag_space():
    predictor_lags = {
        f"{col}_lag{lag}"
        for col in predictor_mod.BASE_FEATURE_COLS
        for lag in predictor_mod.LAG_STEPS
    }
    training_lags = {
        f"{col}_lag{lag}"
        for col in train_mod.FEATURE_COLS
        for lag in train_mod.LAG_STEPS
    }
    missing = sorted(training_lags - predictor_lags)
    assert missing == [], f"predictor lag space missing training lag features: {missing}"


def test_full_ic_tracks_all_training_base_features():
    with open(PROJECT_ROOT / 'scripts' / 'full_ic.py', 'r', encoding='utf-8') as f:
        text = f.read()
    missing = [col for col in train_mod.FEATURE_COLS if col not in text]
    assert missing == [], f"full_ic.py missing training features: {missing}"


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows
        self._limit = None

    def order_by(self, *_args, **_kwargs):
        return self

    def limit(self, n):
        self._limit = n
        return self

    def all(self):
        if self._limit is None:
            return list(self._rows)
        return list(self._rows)[:self._limit]


class _FakeSession:
    def __init__(self, rows):
        self._rows = rows

    def query(self, *_args, **_kwargs):
        return _FakeQuery(self._rows)


def _fake_row(timestamp, **overrides):
    payload = {col: None for col in predictor_mod.BASE_FEATURE_COLS}
    payload.update({
        'timestamp': timestamp,
        'regime_label': 'chop',
        'feat_claw': None,
        'feat_claw_intensity': None,
        'feat_fang_pcr': None,
        'feat_fang_skew': None,
        'feat_fin_netflow': None,
        'feat_web_whale': None,
        'feat_scales_ssr': None,
        'feat_nest_pred': None,
        'feat_nq_return_1h': None,
        'feat_nq_return_24h': None,
    })
    payload.update(overrides)
    return SimpleNamespace(**payload)


def test_load_latest_features_uses_training_style_4h_alignment():
    rows_desc = [
        _fake_row('2026-04-10 10:00:00', feat_eye=1.0, feat_vix=20.0),
        _fake_row(
            '2026-04-10 09:00:00',
            feat_eye=0.5,
            feat_vix=19.0,
            feat_4h_bias50=-1.2,
            feat_4h_bias20=-0.6,
            feat_4h_bias200=-2.4,
            feat_4h_rsi14=42.0,
            feat_4h_macd_hist=15.0,
            feat_4h_bb_pct_b=0.3,
            feat_4h_dist_bb_lower=4.5,
            feat_4h_ma_order=1.0,
            feat_4h_dist_swing_low=3.1,
            feat_4h_vol_ratio=1.7,
        ),
    ]
    features = predictor_mod.load_latest_features(_FakeSession(rows_desc))

    assert features['feat_4h_bias50'] == -1.2
    assert features['feat_4h_bias20'] == -0.6
    assert features['feat_4h_bias200'] == -2.4
    assert features['feat_4h_dist_bb_lower'] == 4.5
    assert features['feat_4h_vol_ratio'] == 1.7
