from collections import Counter

from scripts import dynamic_window_train


def test_build_distribution_summary_flags_constant_target_and_regime_concentration():
    rows = [
        {
            dynamic_window_train.TARGET_COL: 1,
            'regime_label': 'chop',
        }
        for _ in range(100)
    ]

    summary = dynamic_window_train.build_distribution_summary(rows, Counter({'chop': 500, 'bear': 100}))

    assert summary['constant_target'] is True
    assert 'constant_target' in summary['alerts']
    assert 'regime_concentration' in summary['alerts']
    assert summary['dominant_regime'] == 'chop'
    assert summary['dominant_regime_share'] == 1.0


def test_merge_recent_drift_marks_guardrail_from_external_report():
    analysis = {
        'alerts': ['label_imbalance'],
    }
    drift_report = {
        'windows': {
            '400': {
                'alerts': ['regime_concentration'],
                'win_rate': 0.9975,
                'win_rate_delta_vs_full': 0.35,
                'dominant_regime': 'chop',
                'dominant_regime_share': 1.0,
            }
        }
    }

    merged = dynamic_window_train.merge_recent_drift(analysis, drift_report, 400)

    assert merged['distribution_guardrail'] is True
    assert merged['alerts'] == ['label_imbalance', 'regime_concentration']
    assert merged['external_drift_summary']['dominant_regime'] == 'chop'


def test_choose_best_windows_ignores_guardrailed_candidates():
    results = {
        100: {
            'ics': {feat: 0.1 for feat in dynamic_window_train.CORE_FEATURES},
            'distribution_guardrail': True,
        },
        600: {
            'ics': {feat: 0.1 if i < 4 else 0.0 for i, feat in enumerate(dynamic_window_train.CORE_FEATURES)},
            'distribution_guardrail': False,
        },
        1000: {
            'ics': {feat: 0.1 if i < 3 else 0.0 for i, feat in enumerate(dynamic_window_train.CORE_FEATURES)},
            'distribution_guardrail': False,
        },
    }

    raw_best, recommended_best = dynamic_window_train.choose_best_windows(results)

    assert raw_best == (100, 8)
    assert recommended_best == (600, 4)
