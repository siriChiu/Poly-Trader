#!/usr/bin/env python3
"""Diagnose regime classification issues."""
import sqlite3, math

DB_PATH = '/home/kazuha/Poly-Trader/poly_trader.db'
conn = sqlite3.connect(DB_PATH)

# Check body_label distribution
print("=== body_label distribution (recent 2000) ===")
cur = conn.execute("""
    SELECT body_label, COUNT(*) as cnt 
    FROM raw_market_data 
    ORDER BY timestamp DESC
    LIMIT 2000
""")
# Need to re-query properly
cur = conn.execute("""
    SELECT body_label, COUNT(*) as cnt 
    FROM (
        SELECT body_label FROM raw_market_data ORDER BY timestamp DESC LIMIT 2000
    )
    GROUP BY body_label
""")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Check fear_greed_index distribution (recent 2000)
print("\n=== FNG distribution (recent 2000) ===")
cur2 = conn.execute("""
    SELECT 
        CASE WHEN fear_greed_index IS NULL THEN 'NULL'
             WHEN fear_greed_index < 20 THEN '0-19'
             WHEN fear_greed_index < 40 THEN '20-39'
             WHEN fear_greed_index < 60 THEN '40-59'
             WHEN fear_greed_index < 80 THEN '60-79'
             ELSE '80-100'
        END as bucket,
        COUNT(*) as cnt
    FROM (
        SELECT fear_greed_index FROM raw_market_data ORDER BY timestamp DESC LIMIT 2000
    )
    GROUP BY bucket
""")
for row in cur2.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Check regime_label in features_normalized table
print("\n=== regime_label in features_normalized ===")
cur3 = conn.execute("""
    SELECT regime_label, COUNT(*) as cnt
    FROM features_normalized
    GROUP BY regime_label
""")
for row in cur3.fetchall():
    print(f"  '{row[0]}': {row[1]}")
    break  # Just see if column exists

# Check if regime_label column exists and has data
try:
    cur4 = conn.execute("SELECT regime_label FROM features_normalized ORDER BY timestamp DESC LIMIT 10")
    rows = cur4.fetchall()
    print(f"\nLatest 10 regime_label values:")
    for r in rows:
        print(f"  '{r[0]}'")
except Exception as e:
    print(f"\nregime_label column error: {e}")

# What's the actual price range in data?
print("\n=== Price stats (recent 2000) ===")
cur5 = conn.execute("""
    SELECT MIN(close_price), MAX(close_price), AVG(close_price)
    FROM (
        SELECT close_price FROM raw_market_data ORDER BY timestamp DESC LIMIT 2000
    )
""")
row = cur5.fetchone()
print(f"  Min: ${row[0]:,.2f}, Max: ${row[1]:,.2f}, Avg: ${row[2]:,.2f}")

# Look at close price trend to determine actual regime
cur6 = conn.execute("""
    SELECT close_price FROM raw_market_data ORDER BY timestamp DESC LIMIT 2000
""")
prices = [r[0] for r in cur6.fetchall()]
if len(prices) > 100:
    avg_50 = sum(prices[:50]) / 50
    avg_200 = sum(prices[:200]) / 200
    avg_1000 = sum(prices[:1000]) / 1000
    current = prices[0]
    print(f"\n=== Price trend analysis ===")
    print(f"  Current: ${current:,.2f}")
    print(f"  50-bar avg: ${avg_50:,.2f} (vs current: {'above' if current > avg_50 else 'below'})")
    print(f"  200-bar avg: ${avg_200:,.2f} (vs current: {'above' if current > avg_200 else 'below'})")
    print(f"  1000-bar avg: ${avg_1000:,.2f} (vs current: {'above' if current > avg_1000 else 'below'})")

# Momentum calculation
momentum_20 = (prices[0] - prices[19]) / prices[19] * 100 if len(prices) > 19 else 0
momentum_50 = (prices[0] - prices[49]) / prices[49] * 100 if len(prices) > 49 else 0
momentum_100 = (prices[0] - prices[99]) / prices[99] * 100 if len(prices) > 99 else 0
print(f"  20-bar momentum: {momentum_20:+.2f}%")
print(f"  50-bar momentum: {momentum_50:+.2f}%")
print(f"  100-bar momentum: {momentum_100:+.2f}%")

conn.close()
