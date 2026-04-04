#!/usr/bin/env python3
"""Heartbeat #163: CV Test against label_sell_win using features_normalized"""
import sqlite3, numpy as np
conn = sqlite3.connect('/home/kazuha/Poly-Trader/poly_trader.db')
cursor = conn.cursor()

# 8 core senses
feat_cols = ['feat_eye', 'feat_ear', 'feat_nose', 'feat_tongue', 'feat_body', 'feat_pulse', 'feat_aura', 'feat_mind']
col_str = ', '.join(feat_cols)

cursor.execute(f"SELECT timestamp, {col_str} FROM features_normalized ORDER BY timestamp")
feat_rows = cursor.fetchall()

# Get labels as dict keyed by timestamp
cursor.execute("SELECT timestamp, label_sell_win FROM labels ORDER BY timestamp")
label_rows = cursor.fetchall()
label_map = {r[0]: r[1] for r in label_rows if r[0] is not None and r[1] is not None}
conn.close()

# Build matched feature/label pairs
feats, labels = [], []
for row in feat_rows:
    ts = row[0]
    feat_vals = row[1:]
    if ts in label_map and all(x is not None for x in feat_vals):
        feats.append(feat_vals)
        labels.append(label_map[ts])

feats = np.array(feats)
labels = np.array(labels)

print(f'Matched samples: {feats.shape[0]}')
print(f'Feature shape: {feats.shape}')
print(f'Label distribution: {labels.sum()}/{len(labels)} ({labels.mean():.1%} pos)')

from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
feats_scaled = scaler.fit_transform(feats)

lr = LogisticRegression(random_state=42, max_iter=1000)
lr_scores = cross_val_score(lr, feats_scaled, labels, cv=5, scoring='roc_auc')
print(f'LR CV AUC: {lr_scores.mean():.4f} (+/-{lr_scores.std():.4f})')

try:
    from xgboost import XGBClassifier
    xgb = XGBClassifier(random_state=42, eval_metric='auc', n_estimators=100)
    xgb_scores = cross_val_score(xgb, feats_scaled, labels, cv=5, scoring='roc_auc')
    print(f'XGB CV AUC: {xgb_scores.mean():.4f} (+/-{xgb_scores.std():.4f})')
except Exception as e:
    print(f'XGB error: {e}')
