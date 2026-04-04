#!/usr/bin/env python3
"""Full retraining and analysis for heartbeat #202."""
import sqlite3
import numpy as np
from collections import Counter
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score

DB = 'poly_trader.db'
conn = sqlite3.connect(DB)

query = '''
SELECT 
    f.feat_eye, f.feat_ear, f.feat_nose, f.feat_tongue, f.feat_body,
    f.feat_pulse, f.feat_aura, f.feat_mind,
    f.feat_vix, f.feat_dxy, f.feat_rsi14, f.feat_macd_hist, 
    f.feat_atr_pct, f.feat_vwap_dev, f.feat_bb_pct_b,
    l.label_sell_win, l.regime_label
FROM features_normalized f
JOIN labels l ON f.timestamp = l.timestamp AND f.symbol = l.symbol
WHERE l.label_sell_win IS NOT NULL
ORDER BY l.timestamp
'''

rows = conn.execute(query).fetchall()

features = np.array([[r[i] for i in range(15)] for r in rows], dtype=float)
labels = np.array([r[15] for r in rows], dtype=float)
regimes_str = [r[16] for r in rows]

n = len(labels)
print(f'Samples: {n}, sell_win rate: {labels.mean():.3f}')
print(f'sell_win=0: {int(sum(labels==0))}, sell_win=1: {int(sum(labels==1))}')
print(f'Regime distribution: {dict(Counter(regimes_str))}')

# 3-Feature LR
feat_indices = [1, 10, 14]  # Ear, RSI14, BB%p
X = features[:, feat_indices].copy()
X = np.nan_to_num(X, nan=0.0)

model = LogisticRegression(max_iter=1000, random_state=42)
cv_scores = cross_val_score(model, X, labels, cv=5, scoring='accuracy')
print(f'\n=== 3-Feature LR ===')
print(f'CV Accuracy: {cv_scores.mean():.3f} +/- {cv_scores.std():.3f}')
print(f'Scores: {[round(s*100,1) for s in cv_scores]}')
model.fit(X, labels)
train_acc = model.score(X, labels)
print(f'Train Acc: {train_acc:.3f}')
print(f'Overfit gap: {train_acc - cv_scores.mean():.4f}')
print(f'Coefs: Ear={model.coef_[0][0]:+.4f}, RSI14={model.coef_[0][1]:+.4f}, BB%p={model.coef_[0][2]:+.4f}')

# Regime-aware CV
print(f'\n=== Regime-aware CV ===')
for reg in ['bear', 'bull', 'chop']:
    mask = np.array([r == reg for r in regimes_str])
    if not mask.any():
        continue
    n_r = mask.sum()
    X_r = X[mask]
    y_r = labels[mask]
    if n_r < 100:
        print(f'  {reg}: n={n_r} (too small, sell_win={y_r.mean():.3f})')
        continue
    scores = cross_val_score(LogisticRegression(max_iter=1000, random_state=42), X_r, y_r, cv=5, scoring='accuracy')
    print(f'  {reg}: {scores.mean():.3f} +/- {scores.std():.3f} (n={n_r}, sell_win={y_r.mean():.3f})')

# Recent sell_win
for window in [50, 100, 500]:
    recent = labels[-window:].mean()
    print(f'sell_win (last {window}): {recent:.3f} (n={min(window, n)})')

# BTC price and market info
r = conn.execute('SELECT close_price FROM raw_market_data ORDER BY timestamp DESC LIMIT 1').fetchone()
fng = conn.execute('SELECT fear_greed_index FROM raw_market_data WHERE fear_greed_index IS NOT NULL ORDER BY timestamp DESC LIMIT 1').fetchone()
print(f'\nBTC: ${r[0]:.0f}' if r[0] else 'BTC: N/A')
print(f'FNG: {fng[0]}')

conn.close()
