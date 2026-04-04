"""Heartbeat #207 - Data collection for analysis."""
import sqlite3, os, sys, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db = os.path.join(ROOT, 'data', 'market.db')
conn = sqlite3.connect(db)
c = conn.cursor()

# Counts
c.execute('SELECT COUNT(*) FROM raw_4h')
raw = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM features')
feat = c.fetchone()[0]

# BTC price
try:
    c.execute('SELECT * FROM close_prices')
    r = c.fetchone()
    btc = str(r) if r else '?'
except:
    btc = '?'

try:
    c.execute('SELECT close_price FROM raw_4h ORDER BY timestamp DESC LIMIT 1')
    r = c.fetchone()
    if r:
        d = json.loads(r[0])
        btc = d.get('price', d.get('close', d.get('BTC', '?')))
except:
    pass

# Schema
c.execute('PRAGMA table_info(features)')
cols = [r[1] for r in c.fetchall()]
exc = {'timestamp', 'regime', 'regime_label', 'close'}
feat_cols = [c for c in cols if c not in exc]

# Global sell stats
c.execute('SELECT COUNT(*), SUM(CASE WHEN sell_win=1 THEN 1 ELSE 0 END), AVG(sell_win) FROM features WHERE sell_win IS NOT NULL')
s = c.fetchone()
global_avg = round(s[2], 4) if s[2] else 0.5

# Recent 50/100
c.execute('SELECT sell_win FROM features WHERE sell_win IS NOT NULL ORDER BY timestamp DESC LIMIT 50')
r50 = c.fetchall()
w50 = sum(1 for x in r50 if x[0]==1)
r50_rate = w50/len(r50) if r50 else 0

c.execute('SELECT sell_win FROM features WHERE sell_win IS NOT NULL ORDER BY timestamp DESC LIMIT 100')
r100 = c.fetchall()
w100 = sum(1 for x in r100 if x[0]==1)
r100_rate = w100/len(r100) if r100 else 0

# Streak
c.execute('SELECT sell_win FROM features WHERE sell_win IS NOT NULL ORDER BY timestamp DESC')
all_sw = c.fetchall()
streak = 0
for x in all_sw:
    if x[0]==0: streak += 1
    else: break

# Regime
c.execute("SELECT regime_label, COUNT(*), AVG(sell_win) FROM features WHERE sell_win IS NOT NULL AND regime_label IS NOT NULL GROUP BY regime_label")
regime_stats = c.fetchall()

# NULL
c.execute("SELECT COUNT(*), AVG(sell_win) FROM features WHERE sell_win IS NOT NULL AND regime_label IS NULL")
null_r = c.fetchone()

conn.close()

# Output
out = {
    'raw': raw, 'features': feat, 'labels': s[0],
    'btc': str(btc), 'cols': feat_cols,
    'sell_global': s[0], 'sell_avg': global_avg,
    'recent_50_rate': round(r50_rate, 4),
    'recent_100_rate': round(r100_rate, 4),
    'streak': streak,
    'regimes': [(r[0], r[1], round(r[2],4)) for r in regime_stats],
    'null_count': null_r[0] if null_r else 0,
    'null_avg': round(null_r[1], 4) if null_r else 0,
}
print(json.dumps(out))
