#!/usr/bin/env python3
"""Fix P0 #H381: Generate labels for missing feature timestamps, no pandas."""
import sqlite3
import math
from datetime import datetime, timedelta

DB = 'poly_trader.db'
SYMBOL = 'BTCUSDT'
HORIZON_HOURS = 4  # 240 minutes
THRESHOLD_PCT = 0.005

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# Get all raw data
raw_rows = conn.execute("""
    SELECT timestamp, close_price FROM raw_market_data 
    WHERE symbol=? AND close_price IS NOT NULL
    ORDER BY timestamp
""", (SYMBOL,)).fetchall()

# Parse timestamps and prices
raw_data = []
for r in raw_rows:
    ts_str = r['timestamp']
    # Handle various formats
    ts_str = ts_str.replace('T', ' ')
    for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S'):
        try:
            ts = datetime.strptime(ts_str, fmt)
            break
        except ValueError:
            continue
    else:
        continue
    
    if r['close_price'] is not None and r['close_price'] > 0:
        raw_data.append((ts, float(r['close_price'])))

raw_data.sort(key=lambda x: x[0])
print(f"Raw data points: {len(raw_data)}")
if raw_data:
    print(f"Range: {raw_data[0][0]} to {raw_data[-1][0]}")

# Get all feature timestamps
all_feat_ts = conn.execute("""
    SELECT DISTINCT timestamp FROM features_normalized ORDER BY timestamp
""").fetchall()

# Parse feature timestamps
feat_timestamps = []
for r in all_feat_ts:
    ts_str = r[0].replace('T', ' ')
    for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S'):
        try:
            ts = datetime.strptime(ts_str, fmt)
            feat_timestamps.append(ts)
            break
        except ValueError:
            continue

print(f"Total feature timestamps: {len(feat_timestamps)}")

# Get existing label timestamps
existing_label_ts = set()
for r in conn.execute("SELECT timestamp FROM labels"):
    ts_str = r[0].replace('T', ' ')
    for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S'):
        try:
            ts = datetime.strptime(ts_str, fmt)
            existing_label_ts.add(ts)
            break
        except ValueError:
            continue

print(f"Existing labeled timestamps: {len(existing_label_ts)}")
print(f"Feature timestamps without labels: {len(feat_timestamps) - len(existing_label_ts & set(feat_timestamps))}")

# Binary search helper for finding nearest timestamp
def find_nearest(data, target_ts, tolerance):
    """Find nearest price data point within tolerance."""
    best = None
    best_dist = None
    for ts, price in data:
        if abs((ts - target_ts).total_seconds()) <= tolerance.total_seconds():
            dist = abs((ts - target_ts).total_seconds())
            if best_dist is None or dist < best_dist:
                best = price
                best_dist = dist
    return best

# Generate labels for features without labels
tolerance_future = timedelta(minutes=60)
tolerance_current = timedelta(minutes=10)

generated = 0
skipped = 0
sell_win_count = 0
not_sell_win_count = 0

for feat_ts in feat_timestamps:
    if feat_ts in existing_label_ts:
        continue  # Already has a label
    
    future_ts = feat_ts + timedelta(hours=HORIZON_HOURS)
    
    # Check if we have future price data
    future_price = find_nearest(raw_data, future_ts, tolerance_future)
    if future_price is None:
        skipped += 1
        continue
    
    # Find current price
    current_price = find_nearest(raw_data, feat_ts, tolerance_current)
    if current_price is None or current_price == 0:
        skipped += 1
        continue
    
    ret_pct = (future_price - current_price) / current_price
    
    # sell_win = SHORT profitable (price goes down)
    if ret_pct < -THRESHOLD_PCT:
        sell_win = 1
        sell_win_count += 1
    elif ret_pct > THRESHOLD_PCT:
        sell_win = 0
        not_sell_win_count += 1
    else:
        sell_win = 0
        not_sell_win_count += 1
    
    ts_str = feat_ts.strftime('%Y-%m-%d %H:%M:%S.%f')
    
    # Check if this label exists in DB
    existing = conn.execute(
        "SELECT id, future_return_pct, label_sell_win FROM labels WHERE timestamp=? AND symbol=? AND horizon_minutes=?",
        (ts_str, SYMBOL, HORIZON_HOURS * 60)
    ).fetchone()
    
    if existing and existing[1] is None:
        conn.execute(
            "UPDATE labels SET future_return_pct=?, label_sell_win=?, label_up=? WHERE id=?",
            (ret_pct, sell_win, sell_win, existing[0])
        )
        generated += 1
    elif not existing:
        conn.execute(
            "INSERT INTO labels (timestamp, symbol, horizon_minutes, future_return_pct, label_sell_win, label_up) VALUES (?, ?, ?, ?, ?, ?)",
            (ts_str, SYMBOL, HORIZON_HOURS * 60, ret_pct, sell_win, sell_win)
        )
        generated += 1

conn.commit()

# Verify
new_total = conn.execute("SELECT COUNT(*) FROM labels WHERE label_sell_win IS NOT NULL").fetchone()[0]
new_latest = conn.execute("SELECT MAX(timestamp) FROM labels").fetchone()[0]
print(f"\n=== Results ===")
print(f"Generated/updated: {generated}")
print(f"Skipped (no future data): {skipped}")
print(f"sell_win distribution: {sell_win_count} wins, {not_sell_win_count} losses")
print(f"sell_win rate: {sell_win_count / max(1, sell_win_count + not_sell_win_count):.3f}")
print(f"Total labels: {new_total} (latest: {new_latest})")

conn.close()
