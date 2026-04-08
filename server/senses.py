"""Backward-compatibility shim for legacy imports.

Historically the project exposed `server.senses.SensesEngine` and accepted old
feature column names like `feat_eye_dist`. The current implementation lives in
`server.features_engine` with canonical names (`feat_eye`, `feat_ear`, ...).
This module preserves the old import path for tests, scripts, and diagnostics.
"""

from server.features_engine import FeaturesEngine, get_engine as get_features_engine
from server.features_engine import normalize_feature as _normalize_feature


LEGACY_DB_KEY_MAP = {
    "feat_eye_dist": "feat_eye",
    "feat_ear_zscore": "feat_ear",
    "feat_nose_sigmoid": "feat_nose",
    "feat_tongue_pct": "feat_tongue",
    "feat_body_roc": "feat_body",
}


class SensesEngine(FeaturesEngine):
    """Legacy alias for FeaturesEngine."""


def normalize_feature(raw_value, db_col):
    """Normalize both canonical and legacy feature names.

    Old tests/scripts still reference columns such as `feat_eye_dist`; map them
    onto the canonical v4 feature names before delegating.
    """
    canonical = LEGACY_DB_KEY_MAP.get(db_col, db_col)
    return _normalize_feature(raw_value, canonical)


def get_engine():
    """Legacy alias for the singleton features engine getter."""
    return get_features_engine()
