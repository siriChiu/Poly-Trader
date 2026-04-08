#!/usr/bin/env python3
"""HB#191 - Get latest market metrics"""
import sqlite3, os
os.chdir('/home/kazuha/Poly-Trader')
db = sqlite3.connect('poly_trader.db')

# Latest raw record
r = db.execute('SELECT close_price, funding_rate, fear_greed_index, volume, oi_roc, vix_value, dxy_value FROM raw_market_data ORDER BY timestamp DESC LIMIT 1').fetchone()
if r:
    close, fr, fng, vol, oi_roc, vix, dxy = r
    print(f'BTC close: ${close:,.0f}')
    print(f'FNG: {fng}')
    print(f'Funding rate: {fr:.6f}')
    print(f'Volume: {vol:.4f}')
    print(f'OI ROC: {oi_roc:.6f}')
    print(f'VIX: {vix:.2f}')
    print(f'DXY: {dxy:.2f}')

# Derivatives from polymarket/stablecoin data
r2 = db.execute('SELECT stablecoin_mcap, polymarket_prob FROM raw_market_data ORDER BY timestamp DESC LIMIT 1').fetchone()
if r2:
    print(f'Stablecoin mcap: {r2[0]:.4f}')
    print(f'Polymarket prob: {r2[1]:.4f}')

# Time since last entry
r3 = db.execute('SELECT timestamp FROM raw_market_data ORDER BY timestamp DESC LIMIT 1').fetchone()
from datetime import datetime
if r3:
    print(f'Latest record timestamp: {r3[0]}')
    print(f'Current time: {datetime.utcnow()}')

# Sell win overall and recent
r4 = db.execute('SELECT AVG(label_spot_long_win) FROM labels WHERE label_spot_long_win IS NOT NULL').fetchone()
print(f'\nGlobal sell_win rate: {r4[0]:.4f}')

r5 = db.execute('SELECT AVG(label_spot_long_win) FROM (SELECT label_spot_long_win FROM labels WHERE label_spot_long_win IS NOT NULL ORDER BY id DESC LIMIT 500)').fetchone()
print(f'Recent sell_win (500): {r5[0]:.4f}')

r6 = db.execute('SELECT AVG(label_spot_long_win) FROM (SELECT label_spot_long_win FROM labels WHERE label_spot_long_win IS NOT NULL ORDER BY id DESC LIMIT 100)').fetchone()
print(f'Recent sell_win (100): {r6[0]:.4f}')

# Count
r7 = db.execute('SELECT COUNT(*) FROM labels WHERE label_spot_long_win IS NOT NULL').fetchone()
print(f'Total labels: {r7[0]}')
r8 = db.execute('SELECT COUNT(*) FROM features_normalized').fetchone()
print(f'Total features: {r8[0]}')
r9 = db.execute('SELECT COUNT(*) FROM raw_market_data').fetchone()
print(f'Total raw: {r9[0]}')

# Check ear feature uniqueness from features_normalized (std=0.0008, unique=5 in test)
r10 = db.execute('SELECT COUNT(DISTINCT feat_ear), feat_ear FROM features_normalized GROUP BY feat_ear ORDER BY COUNT(*) DESC').fetchall()
print(f'\nfeat_ear unique values count: {len(r10)}')
print(f'  top 5: {[(round(x[1], 6), x[0]) for x in r10[:5]]}')

# Similarly for tongue
r11 = db.execute('SELECT COUNT(DISTINCT feat_tongue), feat_tongue FROM features_normalized GROUP BY feat_tongue ORDER BY COUNT(*) DESC').fetchall()
print(f'\nfeat_tongue unique values count: {len(r11)}')
print(f'  top 5: {[(round(x[1], 6), x[0]) for x in r11[:5]]}')

db.close()
