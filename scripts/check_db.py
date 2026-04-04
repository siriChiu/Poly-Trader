"""Heartbeat #207 - diagnostic script (Steps 1-2)"""
import sqlite3, os, json
import numpy as np
from datetime import datetime

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')

# Check which DB has data
market_db = os.path.join(BASE, 'data', 'market.db')
poly_db = os.path.join(BASE, 'data', 'poly_trader.db')

conn_market = sqlite3.connect(market_db)
cm = conn_market.cursor()
cm.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cm.fetchall()
print(f"Tables in market.db: {[t[0] for t in tables]}")

for t in tables:
    cm.execute(f"SELECT COUNT(*) FROM {t[0]}")
    print(f"  {t[0]}: {cm.fetchone()[0]} rows")

# Get table schemas
for t in tables:
    cm.execute(f"PRAGMA table_info({t[0]})")
    cols = [r[1] for r in cm.fetchall()]
    print(f"  {t[0]} columns: {cols}")

# Get the data - find raw/features/labels tables
raw_table = None
feat_table = None
label_table = None

for t_name in [t[0] for t in tables]:
    if 'raw' in t_name.lower(): raw_table = t_name
    if 'feature' in t_name.lower(): feat_table = t_name
    if 'label' in t_name.lower() or 'sell' in t_name.lower(): label_table = t_name

print(f"\nIdentified: raw={raw_table}, features={feat_table}, labels={label_table}")

# If no obvious names, use first table as features (most common in this codebase)
if not raw_table and not feat_table and tables:
    # Check if there are labels in a different way
    pass

# Get counts from all tables
data = {}
for t in tables:
    tname = t[0]
    cm.execute(f"SELECT COUNT(*) FROM {tname}")
    data[tname] = cm.fetchone()[0]

# Use market.db as the source - let's check the schema more carefully
# In Poly-Trader, market.db might have everything
# Let's check if there's a close price or BTC data
for tname in data.keys():
    cm.execute(f"SELECT * FROM {tname} LIMIT 1")
    row = cm.fetchone()
    print(f"\nSample row from {tname}: {row}")
    break

# Get close_prices from tables - find the BTC price
if 'close_prices' in data or 'close_price' in data:
    tname = 'close_prices' if 'close_prices' in data else 'close_price'
    cm.execute(f"SELECT * FROM {tname} ORDER BY timestamp DESC LIMIT 1")
    print(f"\nLatest {tname}: {cm.fetchone()}")

# If 'features' is a table, use it
if 'features' in data:
    cm.execute("SELECT * FROM features ORDER BY timestamp DESC LIMIT 3")
    for r in cm.fetchall():
        print(f"  features sample: {r}")

# If there's a labels table
if 'labels' in data:
    cm.execute("SELECT * FROM labels LIMIT 3")
    for r in cm.fetchall():
        print(f"  labels sample: {r}")

# Check for specific tables that might hold our data
for possible in ['market_data', 'ohlc', 'candles', 'trades', 'signals', 'predictions']:
    if possible in data:
        cm.execute(f"SELECT * FROM {possible} ORDER BY timestamp DESC LIMIT 1")
        print(f"\n{possible} latest: {cm.fetchone()}")

# Close market db
conn_market.close()

# Now check poly_trader.db (may be empty/unused)
conn_poly = sqlite3.connect(poly_db)
cp = conn_poly.cursor()
cp.execute("SELECT name FROM sqlite_master WHERE type='table'")
ptables = cp.fetchall()
print(f"\nTables in poly_trader.db: {ptables}")
conn_poly.close()

print("\n=== DONE ===")
print(json.dumps(data, indent=2))
