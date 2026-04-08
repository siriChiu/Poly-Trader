#!/usr/bin/env python3
"""HB #176 - Regime-aware IC analysis with regime_label column"""
import sqlite3, numpy as np
from collections import Counter

conn = sqlite3.connect('/home/kazuha/Poly-Trader/poly_trader.db')

# Derivatives: get latest row columns
raw_cols = [r[1] for r in conn.execute("PRAGMA table_info(raw_market_data)").fetchall()]
print("Raw cols:", raw_cols)

# Get latest market data
latest = conn.execute("""
    SELECT close_price, timestamp, funding_rate, fear_greed_index,
           volume FROM raw_market_data ORDER BY timestamp DESC LIMIT 1
""").fetchone()
print(f"\nLatest BTC: ${latest[0]:,.2f}" if latest[0] else "BTC: N/A")
print(f"Timestamp: {latest[1]}")
print(f"Funding rate: {latest[2]}")
print(f"FNG: {latest[3]}")
print(f"Volume 24h: {latest[4]}")

# Check for derivatives tables / additional columns
try:
    deriv = conn.execute("""
        SELECT volume, oi_roc, polymarket_prob, stablecoin_mcap
        FROM raw_market_data ORDER BY timestamp DESC LIMIT 1
    """).fetchone()
    print(f"OI: {deriv[0] if deriv[0] is not None else 'N/A'}")
    print(f"LSR: {deriv[1] if deriv[1] is not None else 'N/A'}")
    print(f"Taker ratio: {deriv[2] if deriv[2] is not None else 'N/A'}")
    print(f"GSR: {deriv[3] if deriv[3] is not None else 'N/A'}")
except Exception as e:
    print(f"Derivatives cols not all available: {e}")

# Regime-aware IC
joined = conn.execute("""
    SELECT f.feat_eye, f.feat_ear, f.feat_nose, f.feat_tongue,
           f.feat_body, f.feat_pulse, f.feat_aura, f.feat_mind,
           COALESCE(f.regime_label, 'Unknown') as regime,
           l.label_spot_long_win
    FROM features_normalized f 
    INNER JOIN labels l ON f.timestamp = l.timestamp 
    WHERE l.label_spot_long_win IS NOT NULL
    ORDER BY f.timestamp
""").fetchall()

regimes = Counter(r[8] for r in joined)
print(f"\nRegime distribution: {dict(regimes)}")

senses = ["Eye", "Ear", "Nose", "Tongue", "Body", "Pulse", "Aura", "Mind"]

for reg in sorted(set(r[8] for r in joined)):
    subset = [(r[:8], float(r[9])) for r in joined if r[8] == reg]
    if len(subset) < 50:
        continue
    arr = np.array([list(s) for s, l in subset])
    lbls = np.array([l for s, l in subset])
    print(f"\n{reg} regime (N={len(subset)}):")
    passing = 0
    for i, s in enumerate(senses):
        col = arr[:, i].astype(float)
        std = np.std(col)
        if std < 1e-10:
            ic = 0
        else:
            ic = np.corrcoef(col, lbls)[0, 1]
        status = "PASS" if abs(ic) >= 0.05 else "FAIL"
        if abs(ic) >= 0.05:
            passing += 1
        print(f"  {s:8s}: IC={ic:+.4f} {status}")
    print(f"  >> {passing}/8 passing for {reg}")

# Time-weighted IC
print("\n=== Time-Weighted IC ===")
all_data = np.array([[float(r[i]) for i in range(8)] for r in joined])
all_labels = np.array([float(r[9]) for r in joined])
N = len(all_labels)

for tau in [50, 100, 200, 500]:
    t = np.arange(N, dtype=float)
    weights = np.exp(-(N - 1 - t) / tau)
    weights /= weights.sum()
    print(f"\ntau={tau}:")
    for i, s in enumerate(senses):
        col = all_data[:, i]
        w_mean_x = np.average(col, weights=weights)
        w_mean_y = np.average(all_labels, weights=weights)
        w_std_x = np.sqrt(np.average((col - w_mean_x)**2, weights=weights))
        w_std_y = np.sqrt(np.average((all_labels - w_mean_y)**2, weights=weights))
        if w_std_x < 1e-10 or w_std_y < 1e-10:
            ic = 0
        else:
            ic = np.average((col - w_mean_x) * (all_labels - w_mean_y), weights=weights) / (w_std_x * w_std_y)
        status = "PASS" if abs(ic) >= 0.05 else "FAIL"
        print(f"  {s:8s}: IC={ic:+.4f} {status}")

conn.close()
