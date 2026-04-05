#!/usr/bin/env python3
"""Compute TW-IC, regime IC, sell_win rates, and latest market data."""
import sqlite3, math, json

DB_PATH = '/home/kazuha/Poly-Trader/poly_trader.db'
conn = sqlite3.connect(DB_PATH)

# ========== Time-Weighted IC (exponential decay) ==========
def tw_ic(data, tau=200):
    """Time-weighted IC with exponential decay."""
    n = len(data)
    if n < 10:
        return None, n
    
    # Weights: recent data gets higher weight
    weights = [math.exp(-(n-1-i)/tau) for i in range(n)]
    
    # Weighted means
    w_sum = sum(weights)
    mean_x = sum(w * x for w, (x, y) in zip(weights, data)) / w_sum
    mean_y = sum(w * y for w, (x, y) in zip(weights, data)) / w_sum
    
    # Weighted Pearson
    num = sum(w * (x - mean_x) * (y - mean_y) for w, (x, y) in zip(weights, data))
    den_x = sum(w * (x - mean_x) ** 2 for w, (x, y) in zip(weights, data))
    den_y = sum(w * (y - mean_y) ** 2 for w, (x, y) in zip(weights, data))
    
    if den_x < 1e-30 or den_y < 1e-30:
        return None, n
    return num / (math.sqrt(den_x) * math.sqrt(den_y)), n

# Get features + labels with timestamps
cur = conn.execute("""
    SELECT f.timestamp, 
           f.feat_eye, f.feat_ear, f.feat_nose, f.feat_tongue, 
           f.feat_body, f.feat_pulse, f.feat_aura, f.feat_mind,
           l.label_up
    FROM features_normalized f
    JOIN labels l ON f.timestamp = l.timestamp
    WHERE l.label_up IS NOT NULL
    ORDER BY f.timestamp
""")
rows = cur.fetchall()
print(f"Matched rows: {len(rows)}")

sensory_cols = {
    'Eye': 1, 'Ear': 2, 'Nose': 3, 'Tongue': 4,
    'Body': 5, 'Pulse': 6, 'Aura': 7, 'Mind': 8
}
label_col = 9

print("\n=== TW-IC (tau=200) ===")
tw_results = {}
for sense, col_idx in sensory_cols.items():
    data = [(row[col_idx], row[label_col]) for row in rows if row[col_idx] is not None]
    ic, n = tw_ic(data, tau=200)
    status = "✅" if ic is not None and abs(ic) >= 0.05 else "❌"
    print(f"  {sense:8s}: TW-IC={ic:+.4f} (n={n}) {status}")
    tw_results[sense] = ic

# ========== Regime-aware IC ==========
print("\n=== Regime-aware IC (recent N=2000) ===")
# Get regime info from raw_market_data
cur2 = conn.execute("""
    SELECT m.body_label, m.close_price, m.fear_greed_index,
           f.feat_eye, f.feat_ear, f.feat_nose, f.feat_tongue,
           f.feat_body, f.feat_pulse, f.feat_aura, f.feat_mind,
           l.label_up
    FROM features_normalized f
    JOIN labels l ON f.timestamp = l.timestamp
    LEFT JOIN raw_market_data m ON m.timestamp = f.timestamp
    WHERE l.label_up IS NOT NULL
    ORDER BY f.timestamp DESC
    LIMIT 2000
""")
recent_rows = cur2.fetchall()

def pearson(x, y):
    n = len(x)
    if n < 5:
        return None
    mx = sum(x)/n
    my = sum(y)/n
    num = sum((xi-mx)*(yi-my) for xi, yi in zip(x, y))
    dx = sum((xi-mx)**2 for xi in x)
    dy = sum((yi-my)**2 for yi in y)
    if dx < 1e-30 or dy < 1e-30:
        return None
    return num / (math.sqrt(dx) * math.sqrt(dy))

# Classify regime
def classify_regime(row):
    # Use volatility + price trend proxy
    body_label = row[0] or ""
    fng = row[2]
    price = row[1]
    
    if body_label and "偏空" in body_label and (fng is not None and fng < 20):
        return "bear"
    elif body_label and "偏多" in body_label and (fng is not None and fng > 40):
        return "bull"
    elif price is not None:
        # Use price position relative to recent
        return "chop"
    return "neutral"

regimes = {"bear": [], "bull": [], "chop": [], "neutral": []}
for row in recent_rows:
    r = classify_regime(row)
    regimes[r].append(row)

print("\n--- Regime distribution (recent 2000) ---")
for regime, rows_list in regimes.items():
    print(f"  {regime}: {len(rows_list)}")

feat_indices = {'Eye': 3, 'Ear': 4, 'Nose': 5, 'Tongue': 6, 'Body': 7, 'Pulse': 8, 'Aura': 9, 'Mind': 10}
label_idx = 11

print("\n--- Regime IC ---")
regime_pass = {}
for regime, rows_list in regimes.items():
    if len(rows_list) < 10:
        print(f"  {regime}: N={len(rows_list)} (too small)")
        continue
    
    pass_count = 0
    for sense, col_idx in feat_indices.items():
        x = [r[col_idx] for r in rows_list if r[col_idx] is not None]
        y = [r[label_idx] for r in rows_list if r[col_idx] is not None]
        ic = pearson(x, y)
        status = "✅" if ic is not None and abs(ic) >= 0.05 else "❌"
        if ic is not None and abs(ic) >= 0.05:
            pass_count += 1
        print(f"    {regime:8s} {sense:8s}: IC={ic:+.4f} {status}")
    regime_pass[regime] = pass_count

# ========== Sell Win Rates ==========
print("\n=== Sell Win Rate Analysis ===")
cur3 = conn.execute("""
    SELECT label_up FROM labels WHERE label_up IS NOT NULL ORDER BY rowid DESC
""")
all_labels = [r[0] for r in cur3.fetchall()]

# Overall sell_win (this is what label_up represents - 1 = up = sell win if selling)
total = len(all_labels)
wins = sum(all_labels)
rate = wins/total * 100 if total > 0 else 0
print(f"  Overall sell_win: {wins}/{total} = {rate:.2f}%")

# Recent 100
recent_100 = all_labels[:100]
r100_wins = sum(recent_100)
r100_rate = r100_wins/len(recent_100)*100
print(f"  Recent 100: {r100_wins}/100 = {r100_rate:.2f}%")

# Consecutive losses
max_consec_loss = 0
cur_consec = 0
for val in all_labels:
    if val == 0:  # loss
        cur_consec += 1
        max_consec_loss = max(max_consec_loss, cur_consec)
    else:
        cur_consec = 0
print(f"  Max consecutive losses: {max_consec_loss}")

# ========== Latest Market Data ==========
print("\n=== Latest Market Data ===")
cur4 = conn.execute("""
    SELECT timestamp, close_price, fear_greed_index, funding_rate, 
           oi_roc, volume, polymarket_prob, vix_value, dxy_value,
           eye_dist, ear_prob, tongue_sentiment, body_label
    FROM raw_market_data ORDER BY timestamp DESC LIMIT 1
""")
row = cur4.fetchone()
if row:
    print(f"  Timestamp: {row[0]}")
    print(f"  BTC Price: ${row[1]:,.2f}")
    print(f"  FNG: {row[2]}")
    print(f"  Funding Rate: {row[3]:.6f}")
    print(f"  OI ROC: {row[4]:.4f}")
    print(f"  Volume: {row[5]:.2f}")
    print(f"  Polymarket: {row[6]:.4f}")
    print(f"  VIX: {row[7]:.2f}")
    print(f"  DXY: {row[8]:.2f}")
    print(f"  Body Label: {row[12]}")

# Data counts
print("\n=== Data Counts ===")
for table in ['raw_market_data', 'features_normalized', 'labels']:
    cur5 = conn.execute(f"SELECT COUNT(*) FROM {table}")
    print(f"  {table}: {cur5.fetchone()[0]} rows")

# Count raw_events
cur6 = conn.execute("SELECT COUNT(*) FROM raw_events")
print(f"  raw_events: {cur6.fetchone()[0]} rows")

conn.close()
