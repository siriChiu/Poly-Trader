#!/usr/bin/env python3
"""Heartbeat #232 — Full Sensory IC Analysis (Global + TW-IC + Regime-aware)"""
import sqlite3, json, math
from pathlib import Path

ROOT = Path(__file__).parent.parent
db = sqlite3.connect(str(ROOT / "poly_trader.db"))

SENSES = ['eye', 'ear', 'nose', 'tongue', 'body', 'pulse', 'aura', 'mind']

# Step 1: Get features with regime
feat_data = db.execute("""
    SELECT f.id, f.timestamp, f.symbol,
           f.feat_eye, f.feat_ear, f.feat_nose, f.feat_tongue,
           f.feat_body, f.feat_pulse, f.feat_aura, f.feat_mind,
           f.regime_label
    FROM features_normalized f
    ORDER BY f.id
""").fetchall()

print(f"Features rows: {len(feat_data)}")

# Check regime distribution
regime_counts = {}
for row in feat_data:
    r = row[11]
    regime_counts[r] = regime_counts.get(r, 0) + 1
print(f"Regime distribution: {regime_counts}")

# Step 2: Get labels
label_data = {}
for row in db.execute("SELECT id, timestamp, symbol, label_spot_long_win, future_return_pct FROM labels ORDER BY id"):
    key = (row[1], row[2])  # timestamp, symbol
    label_data[key] = row

print(f"Labels rows: {len(label_data)}")

# Step 3: Join
joined = []
for frow in feat_data:
    key = (frow[1], frow[2])
    if key in label_data:
        lbl = label_data[key]
        joined.append({
            'id': frow[0], 'timestamp': frow[1], 'symbol': frow[2],
            'eye': frow[3], 'ear': frow[4], 'nose': frow[5], 'tongue': frow[6],
            'body': frow[7], 'pulse': frow[8], 'aura': frow[9], 'mind': frow[10],
            'regime': frow[11],
            'label_spot_long_win': lbl[3], 'future_return_pct': lbl[4]
        })

n = len(joined)
print(f"Joined records: {n}")

# Helper: Pearson
def pearson(x, y):
    valid = [(a, b) for a, b in zip(x, y) 
             if a is not None and b is not None 
             and not math.isnan(a) and not math.isnan(b)]
    if len(valid) < 30:
        return None, 0
    x_vals, y_vals = zip(*valid)
    nv = len(x_vals)
    mx = sum(x_vals) / nv
    my = sum(y_vals) / nv
    sx = math.sqrt(sum((a - mx)**2 for a in x_vals) / nv)
    sy = math.sqrt(sum((b - my)**2 for b in y_vals) / nv)
    if sx < 1e-10 or sy < 1e-10:
        return 0.0, nv
    cov = sum((a - mx) * (b - my) for a, b in zip(x_vals, y_vals)) / nv
    return cov / (sx * sy), nv

# Helper: TW-IC
def tw_ic(x, y, tau=200):
    valid = [(a, b) for a, b in zip(x, y) 
             if a is not None and b is not None
             and not math.isnan(a) and not math.isnan(b)]
    if len(valid) < 30:
        return None, 0
    total = len(valid)
    x_vals = [a for a, b in valid]
    y_vals = [b for a, b in valid]
    w_list = [math.exp(j / tau) for j in range(total)]
    w_sum = sum(w_list)
    
    mx = sum(w * x for w, x in zip(w_list, x_vals)) / w_sum
    my = sum(w * y for w, y in zip(w_list, y_vals)) / w_sum
    sx = math.sqrt(sum(w * (x - mx)**2 for w, x in zip(w_list, x_vals)) / w_sum)
    sy = math.sqrt(sum(w * (y - my)**2 for w, y in zip(w_list, y_vals)) / w_sum)
    if sx < 1e-10 or sy < 1e-10:
        return 0.0, len(valid)
    cov = sum(w * (x - mx) * (y - my) 
              for w, x, y in zip(w_list, x_vals, y_vals)) / w_sum
    return cov / (sx * sy), len(valid)

# Extract arrays
sense_arrays = {s: [r[s] for r in joined] for s in SENSES}
labels_sw = [r['label_spot_long_win'] for r in joined]
regimes = [r['regime'] for r in joined]

# Valid labels only for global
valid_labels = [l for l in labels_sw if l is not None and not math.isnan(l)]
sw_avg = sum(valid_labels) / len(valid_labels) if valid_labels else None
print(f"\nSell Win (valid labels): {len(valid_labels)}, avg={sw_avg:.4f}" if sw_avg else "No valid labels")

# Consecutive losses from the END
streak = 0
for l in reversed(labels_sw):
    if l == 0.0 or l == 0:
        streak += 1
    elif l == 1.0 or l == 1:
        break
    else:
        break  # None or NaN
print(f"Consecutive losses from end: {streak}")

# === GLOBAL IC ===
print("\n=== Global IC (all joined data) ===")
global_ic = {}
for s in SENSES:
    ic, cnt = pearson(sense_arrays[s], labels_sw)
    if ic is not None:
        ic_val = round(ic, 4)
        global_ic[s] = ic_val
        status = "PASS" if abs(ic_val) >= 0.05 else "FAIL"
        print(f"  {s.capitalize():8}: {ic_val:+.4f} (n={cnt}) [{status}]")

gp = sum(1 for v in global_ic.values() if abs(v) >= 0.05)
print(f"  Global pass rate: {gp}/8")

# === TW-IC ===
print("\n=== Time-Weighted IC (tau=200) ===")
tw_ics = {}
for s in SENSES:
    ic, cnt = tw_ic(sense_arrays[s], labels_sw, tau=200)
    if ic is not None:
        ic_val = round(ic, 4)
        tw_ics[s] = ic_val
        status = "PASS" if abs(ic_val) >= 0.05 else "FAIL"
        marker = " ⚠️ REVERSE" if ic_val < -0.05 else ""
        print(f"  {s.capitalize():8}: {ic_val:+.4f} (n={cnt}) [{status}]{marker}")

tp = sum(1 for v in tw_ics.values() if abs(v) >= 0.05)
print(f"  TW-IC pass rate: {tp}/8")

# === REGIME-WISE IC (recent N=2000) ===
print("\n=== Regime-wise IC (recent N=2000) ===")
recent_n = min(2000, n)
start_idx = n - recent_n

for regime in ['bear', 'bull', 'chop', 'neutral']:
    indices = [i for i in range(start_idx, n) if joined[i]['regime'] == regime]
    if len(indices) < 30:
        print(f"\n  {regime}: N={len(indices)} (too few)")
        continue
    
    reg_labels = [joined[i]['label_spot_long_win'] for i in indices if joined[i]['label_spot_long_win'] is not None]
    reg_sw = sum(reg_labels) / len(reg_labels) if reg_labels else 0
    
    print(f"\n  {regime} (N_recent={len(indices)}, sell_win={reg_sw:.1%}):")
    for s in SENSES:
        reg_sense = [sense_arrays[s][i] for i in indices]
        ic, cnt = pearson(reg_sense, [joined[i]['label_spot_long_win'] for i in indices])
        if ic is not None:
            ic_val = round(ic, 4)
            status = "PASS" if abs(ic_val) >= 0.05 else "FAIL"
            print(f"    {s.capitalize():8}: {ic_val:+.4f} [{status}]")

# === Sense Stats ===
print("\n=== Sense Statistics (recent N=2000) ===")
for s in SENSES:
    vals = [v for v in sense_arrays[s][start_idx:] if v is not None and not math.isnan(v)]
    if vals:
        mean_v = sum(vals) / len(vals)
        std_v = math.sqrt(sum((v - mean_v)**2 for v in vals) / len(vals))
        rng = max(vals) - min(vals)
        uniq = len(set(round(v, 6) for v in vals))
        print(f"  {s.capitalize():8}: mean={mean_v:.4f}, std={std_v:.4f}, range={rng:.4f}, unique={uniq}")

# === SAVE ===
results = {
    "heartbeat": 232,
    "records_joined": n,
    "sell_win_avg": round(sw_avg, 4) if sw_avg else None,
    "consecutive_losses": streak,
    "global_ic": {k: round(v, 4) for k, v in global_ic.items()},
    "tw_ic": {k: round(v, 4) for k, v in tw_ics.items()},
    "global_pass": gp,
    "twic_pass": tp
}

with open(ROOT / "scripts" / "ic_results_232.json", "w") as f:
    json.dump(results, f, indent=2)
print(f"\n=== Saved to ic_results_232.json ===")

db.close()
