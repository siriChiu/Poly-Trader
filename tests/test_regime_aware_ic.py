import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'regime_aware_ic.py'
spec = importlib.util.spec_from_file_location('regime_aware_ic_test_module', MODULE_PATH)
regime_module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(regime_module)


def test_assign_regimes_falls_back_to_feature_regime_when_feat_mind_missing():
    rows = [
        {'feat_mind': -0.9, 'feature_regime': 'bear'},
        {'feat_mind': -0.8, 'feature_regime': 'bear'},
        {'feat_mind': 0.0, 'feature_regime': 'chop'},
        {'feat_mind': 0.8, 'feature_regime': 'bull'},
    ] * 30
    rows.extend([
        {'feat_mind': None, 'feature_regime': 'bear'},
        {'feat_mind': None, 'feature_regime': 'bull'},
        {'feat_mind': None, 'feature_regime': 'chop'},
        {'feat_mind': None, 'feature_regime': 'neutral'},
    ])

    meta = regime_module._assign_regimes(rows)

    assert meta['method'] == 'mind_tertiles_with_feature_regime_fallback'
    assert meta['fallback_rows'] == 4
    assert rows[-4]['regime'] == 'bear'
    assert rows[-3]['regime'] == 'bull'
    assert rows[-2]['regime'] == 'chop'
    assert rows[-1]['regime'] == 'neutral'


def test_assign_regimes_uses_feature_regime_only_when_not_enough_mind_values():
    rows = [
        {'feat_mind': None, 'feature_regime': 'bear'},
        {'feat_mind': None, 'feature_regime': 'bull'},
        {'feat_mind': None, 'feature_regime': 'chop'},
        {'feat_mind': None, 'feature_regime': 'neutral'},
    ]

    meta = regime_module._assign_regimes(rows)

    assert meta['method'] == 'feature_regime_only_fallback'
    assert meta['fallback_rows'] == 4
    assert [row['regime'] for row in rows] == ['bear', 'bull', 'chop', 'neutral']
