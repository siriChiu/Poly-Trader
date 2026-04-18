import pytest

from server.features_engine import ecdf_normalize
from server.routes.api import normalize_for_api


def test_soft_ecdf_normalize_preserves_separation_in_extremes():
    p_lo, p_hi = 10.0, 20.0

    low = ecdf_normalize(5.0, p_lo, p_hi)
    edge_low = ecdf_normalize(10.0, p_lo, p_hi)
    mid = ecdf_normalize(15.0, p_lo, p_hi)
    edge_high = ecdf_normalize(20.0, p_lo, p_hi)
    high = ecdf_normalize(25.0, p_lo, p_hi)

    assert 0.0 <= low < edge_low < mid < edge_high < high <= 1.0
    assert edge_low == pytest.approx(0.10)
    assert edge_high == pytest.approx(0.90)
    assert high < 0.99


def test_api_normalization_matches_soft_extreme_behavior():
    base = normalize_for_api(20.0, "feat_vix")
    high = normalize_for_api(35.0, "feat_vix")
    extreme = normalize_for_api(50.0, "feat_vix")

    assert base is not None and high is not None and extreme is not None
    assert base < high < extreme < 0.99
    assert high >= 0.89


def test_api_normalization_handles_transformed_sparse_source_ranges():
    fang_mid = normalize_for_api(-0.53, "feat_fang_pcr")
    fang_high = normalize_for_api(0.35, "feat_fang_pcr")
    claw_mid = normalize_for_api(-0.49, "feat_claw")
    claw_high = normalize_for_api(0.4, "feat_claw")

    assert fang_mid is not None and fang_high is not None
    assert claw_mid is not None and claw_high is not None
    assert 0.0 < fang_mid < fang_high < 1.0
    assert 0.0 < claw_mid < claw_high < 1.0
    assert fang_mid > 0.02
    assert claw_mid > 0.02
