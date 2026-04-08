#!/usr/bin/env python3
"""Heartbeat #210: Streak analysis fixed"""
import sqlite3
import pandas as pd
import numpy as np
from collections import Counter

db = sqlite3.connect('/home/kazuha/Poly-Trader/poly_trader.db')
feat = pd.read_sql('SELECT * FROM features_normalized', db)
label = pd.read_sql('SELECT * FROM labels', db)
merged = feat.merge(label, on=['id','timestamp','symbol'], how='inner')

# Find regime column
regime_col = None
for c in merged.columns:
    if 'regime' in c.lower():
        regime_col = c
        break
print(f"Regime column: {regime_col}")

sw = merged['label_spot_long_win'].astype(int).values
rl = merged[regime_col] if regime_col else None

print(f"Global sell_win: {sw.mean():.3f}")

# Max consecutive 0s
max_streak = 0
current = 0
for v in sw:
    if v == 0:
        current += 1
        max_streak = max(max_streak, current)
    else:
        current = 0
print(f"Max consecutive 0s: {max_streak}")

# Streak lengths
streak_lengths = []
current = 0
for v in sw:
    if v == 0:
        current += 1
    else:
        if current > 0:
            streak_lengths.append(current)
        current = 0
if current > 0:
    streak_lengths.append(current)

print(f"Zero streaks: {len(streak_lengths)}")
c = Counter(streak_lengths)
print(f"Longest: {max(streak_lengths) if streak_lengths else 0}")
print(f"Top 5 longest: {sorted(streak_lengths)[-5:]}")

# Regime-specific
if rl is not None:
    for r in sorted(rl.dropna().unique()):
        mask = (rl == r).values
        rsw = sw[mask]
        print(f"  {r}: sell_win={rsw.mean():.3f}, n={len(rsw)}")

# Recent sell_win
for wn in [10, 20, 30, 50, 100, 200, 500]:
    rsw = sw[-wn:]
    print(f"  Last {wn}: {rsw.mean():.3f} ({rsw.sum()}/{len(rsw)})")

# Check: what's the sell_win trend?
# Last 100 split into 4 quarters of 25
for i in range(4):
    chunk = sw[-100 + i*25 : -100 + (i+1)*25]
    print(f"  Last 100 Q{i+1}: {chunk.mean():.3f}")

db.close()
