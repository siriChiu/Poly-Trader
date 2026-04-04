"""Quick stats dump for heartbeat #202."""
import sqlite3

db_path = "./polling_results.db"
import os
if os.path.exists("poly_trader.db"):
    db_path = "poly_trader.db"
else:
    db_path = "data/poly_trader.db"

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Counts
cur.execute("SELECT COUNT(*) FROM raw_market_data")
raw = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM features_normalized")
features = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM labels")
labels = cur.fetchone()[0]

# Latest timestamps
cur.execute("SELECT MAX(timestamp) FROM raw_market_data")
raw_ts = cur.fetchone()[0]
cur.execute("SELECT MAX(timestamp) FROM features_normalized")
feat_ts = cur.fetchone()[0]
cur.execute("SELECT MAX(timestamp) FROM labels")
label_ts = cur.fetchone()[0]

print(f"Raw: {raw} | Latest: {raw_ts}")
print(f"Features: {features} | Latest: {feat_ts}")
print(f"Labels: {labels} | Latest: {label_ts}")

# sell_win stats
cur.execute("SELECT AVG(CAST(label_sell_win AS FLOAT)) FROM labels WHERE label_sell_win IS NOT NULL")
sell_win = cur.fetchone()[0]
print(f"Global sell_win: {sell_win:.3f}")

for n in [50, 100, 500]:
    cur.execute(f"SELECT AVG(CAST(label_sell_win AS FLOAT)) FROM labels WHERE label_sell_win IS NOT NULL ORDER BY rowid DESC LIMIT {n}")
    sw = cur.fetchone()[0]
    print(f"Recent sell_win (last {n}): {sw:.3f}")

# Regime sell_win - need to join with features_normalized
for regime in ["bear", "bull", "chop"]:
    cur.execute(
        f"SELECT AVG(CAST(l.label_sell_win AS FLOAT)) FROM labels l JOIN features_normalized f ON l.timestamp = f.timestamp WHERE l.label_sell_win IS NOT NULL AND f.regime_label = '{regime}'"
    )
    sw = cur.fetchone()[0]
    print(f"{regime.title()} sell_win: {sw:.3f}")

# BTC/FNG
cur.execute("SELECT close_price, fear_greed_index FROM raw_market_data ORDER BY rowid DESC LIMIT 1")
row = cur.fetchone()
print(f"BTC Price: ${row[0]:.0f}" if row else "BTC: N/A")
print(f"FNG: {row[1]}" if row else "FNG: N/A")

# VIX/DXY - check if columns exist
try:
    cur.execute("SELECT vix_value, dxy_value FROM raw_market_data ORDER BY rowid DESC LIMIT 1")
    row = cur.fetchone()
    if row:
        print(f"VIX: {row[0]:.2f}" if row[0] else "VIX: NULL")
        print(f"DXY: {row[1]:.2f}" if row[1] else "DXY: NULL")
    else:
        print("VIX/DXY: no row")
except:
    print("VIX/DXY columns not available")

conn.close()
