#!/usr/bin/env python3
"""Heartbeat diagnostic: collect current system state data."""
import sqlite3, os, sys, json

try:
    db_path = os.path.expanduser('~/.poly_trader/data/poly_trader.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Counts
    c.execute('SELECT COUNT(*) FROM raw')
    raw = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM features')
    feat = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM labels')
    labels = c.fetchone()[0]
    print(f"Raw: {raw}, Features: {feat}, Labels: {labels}")

    # Latest candles
    c.execute('SELECT close, timestamp, open, high, low, volume, funding_rate FROM raw ORDER BY rowid DESC LIMIT 5')
    rows = c.fetchall()
    for r in rows:
        print(f"  candle: ts={r[1]} close={r[0]} vol={r[5]} fund={r[6]}")

    # Derivatives data from features
    try:
        c.execute('SELECT feat_lsr, feat_gsr, feat_taker, feat_oi FROM features ORDER BY rowid DESC LIMIT 3')
        derivs = c.fetchall()
        for r in derivs:
            print(f"  deriv: LSR={r[0]} GSR={r[1]} Taker={r[2]} OI={r[3]}")
    except Exception as e:
        print(f"  derivatives error: {e}")

    # Get column names for features
    c.execute('PRAGMA table_info(features)')
    feat_cols = [r[1] for r in c.fetchall()]
    print(f"Feature columns ({len(feat_cols)}): {feat_cols}")

    conn.close()
except Exception as e:
    print(f"DB error: {e}")
    sys.exit(1)

# Fetch Fear & Greed Index
try:
    import urllib.request
    url = "https://api.alternative.me/fng/?limit=2"
    req = urllib.request.urlopen(url, timeout=10)
    fng_data = json.loads(req.read())
    print(f"FNG: {fng_data}")
except Exception as e:
    print(f"FNG error: {e}")
