#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from database.models import init_db, FeaturesNormalized, Labels
from model.predictor import _build_live_decision_profile, _decision_quality_scope_alerts, _recent_scope_pathology_summary

session = init_db(f"sqlite:///{ROOT / 'poly_trader.db'}")
rows = (
    session.query(
        FeaturesNormalized.timestamp,
        FeaturesNormalized.symbol,
        FeaturesNormalized.regime_label,
        FeaturesNormalized.feat_4h_bias200,
        FeaturesNormalized.feat_4h_bias50,
        FeaturesNormalized.feat_4h_bb_pct_b,
        FeaturesNormalized.feat_4h_dist_bb_lower,
        FeaturesNormalized.feat_4h_dist_swing_low,
        FeaturesNormalized.feat_nose,
        FeaturesNormalized.feat_pulse,
        FeaturesNormalized.feat_ear,
        Labels.simulated_pyramid_win,
        Labels.simulated_pyramid_pnl,
        Labels.simulated_pyramid_quality,
        Labels.simulated_pyramid_drawdown_penalty,
        Labels.simulated_pyramid_time_underwater,
    )
    .join(Labels, (FeaturesNormalized.timestamp == Labels.timestamp) & (FeaturesNormalized.symbol == Labels.symbol))
    .filter(Labels.horizon_minutes == 1440, Labels.simulated_pyramid_win.isnot(None))
    .order_by(FeaturesNormalized.timestamp.desc())
    .limit(5000)
    .all()
)

summarized = []
for row in rows:
    hist_features = {
        'regime_label': row.regime_label,
        'feat_4h_bias200': row.feat_4h_bias200,
        'feat_4h_bias50': row.feat_4h_bias50,
        'feat_4h_bb_pct_b': row.feat_4h_bb_pct_b,
        'feat_4h_dist_bb_lower': row.feat_4h_dist_bb_lower,
        'feat_4h_dist_swing_low': row.feat_4h_dist_swing_low,
        'feat_nose': row.feat_nose,
        'feat_pulse': row.feat_pulse,
        'feat_ear': row.feat_ear,
    }
    profile = _build_live_decision_profile(hist_features)
    summarized.append({
        'timestamp': row.timestamp,
        'symbol': row.symbol,
        'regime_label': row.regime_label,
        'regime_gate': profile.get('regime_gate'),
        'entry_quality_label': profile.get('entry_quality_label'),
        'simulated_pyramid_win': row.simulated_pyramid_win,
        'simulated_pyramid_pnl': row.simulated_pyramid_pnl,
        'simulated_pyramid_quality': row.simulated_pyramid_quality,
        'simulated_pyramid_drawdown_penalty': row.simulated_pyramid_drawdown_penalty,
        'simulated_pyramid_time_underwater': row.simulated_pyramid_time_underwater,
        'feat_4h_bb_pct_b': row.feat_4h_bb_pct_b,
        'feat_4h_dist_bb_lower': row.feat_4h_dist_bb_lower,
        'feat_4h_dist_swing_low': row.feat_4h_dist_swing_low,
    })

scopes = {
    'regime_gate+entry_quality_label': [r for r in summarized if r['regime_gate'] == 'ALLOW' and r['entry_quality_label'] == 'D'],
    'regime_gate': [r for r in summarized if r['regime_gate'] == 'ALLOW'],
    'entry_quality_label': [r for r in summarized if r['entry_quality_label'] == 'D'],
    'regime_label+entry_quality_label': [r for r in summarized if r['regime_label'] == 'bull' and r['entry_quality_label'] == 'D'],
    'regime_label': [r for r in summarized if r['regime_label'] == 'bull'],
    'global': summarized,
}

out = {}
for name, scope_rows in scopes.items():
    alerts = _decision_quality_scope_alerts(scope_rows) if scope_rows else []
    pathology = _recent_scope_pathology_summary(scope_rows) if scope_rows else {'applied': False}
    wins = [float(r['simulated_pyramid_win']) for r in scope_rows if r['simulated_pyramid_win'] is not None]
    pnl = [float(r['simulated_pyramid_pnl']) for r in scope_rows if r['simulated_pyramid_pnl'] is not None]
    quality = [float(r['simulated_pyramid_quality']) for r in scope_rows if r['simulated_pyramid_quality'] is not None]
    regime_counts = {}
    for r in scope_rows[:500]:
        regime_counts[r['regime_label'] or 'unknown'] = regime_counts.get(r['regime_label'] or 'unknown', 0) + 1
    out[name] = {
        'rows': len(scope_rows),
        'alerts': alerts,
        'win_rate': round(sum(wins)/len(wins), 4) if wins else None,
        'avg_pnl': round(sum(pnl)/len(pnl), 4) if pnl else None,
        'avg_quality': round(sum(quality)/len(quality), 4) if quality else None,
        'recent500_regime_counts': regime_counts,
        'recent_pathology': pathology,
    }

print(json.dumps(out, indent=2, default=str))
