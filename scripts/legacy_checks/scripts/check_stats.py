#!/usr/bin/env python3
"""Quick stats check - latest market data and DB counts."""
import sys
sys.path.insert(0, '/home/kazuha/Poly-Trader')

from sqlalchemy import create_engine, text
import pandas as pd

engine = create_engine('sqlite:////home/kazuha/Poly-Trader/poly_trader.db')
with engine.connect() as conn:
    # Raw columns already known: close_price, not close
    r = conn.execute(text('SELECT timestamp, close_price, funding_rate, vix_value, dxy_value FROM raw_market_data ORDER BY timestamp DESC LIMIT 1')).fetchall()
    if r:
        print(f'Latest BTC: ${r[0][1]:.2f} at {r[0][0]}')
        print(f'Funding rate: {r[0][2]}')
        if r[0][3]: print(f'VIX: {r[0][3]:.2f}')
        if r[0][4]: print(f'DXY: {r[0][4]:.2f}')
    
    fc = conn.execute(text('SELECT COUNT(*) FROM features_normalized')).fetchone()[0]
    lc = conn.execute(text('SELECT COUNT(*) FROM labels')).fetchone()[0]
    rc = conn.execute(text('SELECT COUNT(*) FROM raw_market_data')).fetchone()[0]
    print(f'\nRaw: {rc}, Features: {fc}, Labels: {lc}')

    feat_cols = [r[1] for r in conn.execute(text('PRAGMA table_info(features_normalized)')).fetchall()]
    print(f'Feature columns: {len(feat_cols)}: {feat_cols}')

    labs = pd.read_sql('SELECT label_up FROM labels', engine)
    pos = labs['label_up'].sum()
    print(f'Labels balance: {pos}/{len(labs)} = {pos/len(labs)*100:.1f}% sell_win')
