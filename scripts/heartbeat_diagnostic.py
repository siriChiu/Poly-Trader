"""Full Heartbeat #207 Diagnostic - Data Collection + IC Analysis."""
import sqlite3
import os
import sys
import json
import numpy as np

# Setup paths
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
db_path = os.path.abspath(os.path.join(ROOT, 'data', 'market.db'))
out_path = os.path.abspath(os.path.join(ROOT, 'data', '_heartbeat_207.json'))

# Connect
conn = sqlite3.connect(db_path)
c = conn.cursor()

print(f"DB: {db_path}")
print(f"Output: {out_path}\n")

# ---- COUNTS ----
c.execute('SELECT COUNT(*) FROM raw_4h')
raw_count = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM features')
feat_count = c.fetchone()[0]

# BTC price - check multiple sources
try:
    c.execute('SELECT price_24h FROM close_prices LIMIT 1')
    cp = c.fetchone()
    btc_price = cp[0] if cp else '?'
    print(f"BTC close_prices price_24h: ${btc_price}")
except:
    try:
        c.execute('SELECT * FROM close_prices LIMIT 1')
        cp = c.fetchone()
        print(f"close_prices columns: {c.description}")
        print(f"close_prices data: {cp}")
        btc_price = '?'
    except:
        btc_price = '?'
        print("No close_prices data")

try:
    c.execute('SELECT close_price FROM raw_4h ORDER BY timestamp DESC LIMIT 1')
    r = c.fetchone()
    close_data = json.loads(r[0]) if r else {}
    print(f"Latest raw close: {close_data}")
except:
    pass

# ---- FEATURE SCHEMA ----
c.execute('PRAGMA table_info(features)')
all_cols = [r[1] for r in c.fetchall()]
# Exclude metadata columns
exclude = {'timestamp', 'regime', 'regime_label', 'close'}
feat_cols = [col for col in all_cols if col not in exclude]
print(f"\nFeature columns ({len(feat_cols)}): {feat_cols}")

# ---- SELL_STATS ----
c.execute("SELECT COUNT(*), SUM(CASE WHEN sell_win=1 THEN 1 ELSE 0 END), AVG(sell_win) FROM features WHERE sell_win IS NOT NULL")
sell = c.fetchone()
global_avg = sell[2] if sell[2] is not None else 0.5
print(f"\nGlobal sell_win: n={sell[0]}, wins={sell[1]}, avg={sell[2]:.4f}")

# Recent 50
c.execute("SELECT sell_win FROM features WHERE sell_win IS NOT NULL ORDER BY timestamp DESC LIMIT 50")
r50 = c.fetchall()
w50 = sum(1 for r in r50 if r[0]==1)
print(f"Recent 50: {w50}/{len(r50)} = {w50/len(r50):.4f}")

# Recent 100
c.execute("SELECT sell_win FROM features WHERE sell_win IS NOT NULL ORDER BY timestamp DESC LIMIT 100")
r100 = c.fetchall()
w100 = sum(1 for r in r100 if r[0]==1)
print(f"Recent 100: {w100}/{len(r100)} = {w100/len(r100):.4f}")

# Streak
c.execute("SELECT sell_win FROM features WHERE sell_win IS NOT NULL ORDER BY timestamp DESC")
all_sw = c.fetchall()
streak = 0
for r in all_sw:
    if r[0] == 0: streak += 1
    else: break
print(f"Current sell-win=0 streak: {streak}")

# Regime stats
c.execute("SELECT regime_label, COUNT(*), AVG(sell_win) FROM features WHERE sell_win IS NOT NULL AND regime_label IS NOT NULL GROUP BY regime_label")
regime_stats = c.fetchall()
regime_info = {}
for r in regime_stats:
    regime_info[r[0]] = {'n': r[1], 'sell_win': r[2]}
    print(f"  Regime {r[0]}: n={r[1]}, sell_win={r[2]:.4f}")

# NULL regime
c.execute("SELECT COUNT(*), SUM(CASE WHEN sell_win=1 THEN 1 ELSE 0 END), AVG(sell_win) FROM features WHERE sell_win IS NOT NULL AND regime_label IS NULL")
null_r = c.fetchone()
print(f"  NULL regime: n={null_r[0]}, wins={null_r[1]}, avg={null_r[2]:.4f}")

# ---- GLOBAL IC ANALYSIS ----
print(f"\n{'='*60}")
print(f"SENSORY IC ANALYSIS (against sell_win, threshold=0.05)")
print(f"{'='*60}")

# Get aligned data - features and labels share same table
c.execute(f"SELECT {','.join(feat_cols)} FROM features WHERE sell_win IS NOT NULL ORDER BY timestamp")
feat_data = c.fetchall()

c.execute("SELECT sell_win, COALESCE(regime_label, 'NULL') FROM features WHERE sell_win IS NOT NULL ORDER BY timestamp")
label_data = c.fetchall()

ic_results = {}
for idx, col in enumerate(feat_cols):
    vals = []
    tgts = []
    for i, row in enumerate(feat_data):
        val = row[idx]
        if val is None or i >= len(label_data):
            continue
        vals.append(float(val))
        tgts.append(float(label_data[i][0]))
    
    n = len(vals)
    if n < 100:
        ic_results[col] = {'ic': None, 'std': None, 'n': n, 'status': 'SKIP'}
        print(f"  {col}: SKIP (n={n} < 100)")
        continue
    
    vals_arr = np.array(vals)
    tgts_arr = np.array(tgts)
    
    std_val = float(np.std(vals_arr))
    if std_val < 1e-10:
        ic_results[col] = {'ic': 0.0, 'std': 0.0, 'n': n, 'status': 'STD_ZERO'}
        print(f"  {col}: IC=0.0000, std=0.0000, n={n} ⚠️ STD=0")
        continue
    
    ic_val = float(np.corrcoef(vals_arr, tgts_arr)[0, 1])
    passed = abs(ic_val) >= 0.05
    status = "PASS" if passed else "FAIL"
    near = "⚠️ NEAR" if (not passed and abs(ic_val) >= 0.04) else ""
    
    ic_results[col] = {'ic': round(ic_val, 4), 'std': round(std_val, 4), 'n': n, 'status': status}
    icon = "✅" if passed else ("⚠️" if near else "❌")
    print(f"  {col}: IC={ic_val:+.4f}, std={std_val:.4f}, n={n} {icon} {status}")

pass_count = sum(1 for v in ic_results.values() if v['status'] == 'PASS')
print(f"\nGlobal: {pass_count}/{len(ic_results)} passing IC>=0.05")

# Save results
result = {
    'raw': raw_count,
    'features': feat_count,
    'labels': sell[0],
    'btc_price': str(btc_price),
    'sell_global': {'n': sell[0], 'avg': round(global_avg, 4)},
    'recent_50': f'{w50}/{len(r50)}',
    'recent_100': f'{w100}/{len(r100)}',
    'streak': streak,
    'regime_stats': regime_info,
    'null_regime': {'n': null_r[0], 'avg': round(null_r[2] or 0, 4)},
    'ic_results': ic_results,
    'pass_count': pass_count,
    'total_ics': len(ic_results),
}

os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, 'w') as f:
    json.dump(result, f, indent=2)

print(f"\nResults saved to {out_path}")
conn.close()
