"""Update ic_signs.json with fresh IC computed from DB"""
import sqlite3, json, numpy as np
from scipy import stats
from datetime import datetime

conn = sqlite3.connect(r"C:\Users\Kazuha\repo\Poly-Trader\poly_trader.db")

N = 5000
senses = {
    "eye":    "feat_eye_dist",
    "ear":    "feat_ear_zscore",
    "nose":   "feat_nose_sigmoid",
    "tongue": "feat_tongue_pct",
    "body":   "feat_body_roc",
    "pulse":  "feat_pulse",
    "aura":   "feat_aura",
    "mind":   "feat_mind",
}

results = {}
neg_ic_feats = []

for sense, col in senses.items():
    rows = conn.execute(
        f"SELECT f.{col}, l.label FROM features_normalized f "
        f"JOIN labels l ON f.timestamp = l.timestamp "
        f"WHERE l.horizon_hours = 4 ORDER BY f.timestamp DESC LIMIT {N}"
    ).fetchall()
    v = np.array([r[0] for r in rows], dtype=float)
    lb = np.array([r[1] for r in rows], dtype=float)
    ic, pval = stats.spearmanr(v, lb)
    results[sense] = {
        "ic": round(float(ic), 4),
        "pval": round(float(pval), 4),
        "n": len(rows),
        "sign": -1 if ic < 0 else 1
    }
    if ic < 0:
        neg_ic_feats.append(col)
    flag = "WARN" if abs(ic) < 0.05 else "OK"
    print(f"[{flag}] {sense}: IC={ic:.4f} p={pval:.4f} N={len(rows)}")

results["neg_ic_feats"] = neg_ic_feats
results["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M")
results["n_recent"] = N

out_path = r"C:\Users\Kazuha\repo\Poly-Trader\data\ic_signs.json"
with open(out_path, "w") as f:
    json.dump(results, f, indent=2)
print(f"\nUpdated {out_path}")

conn.close()
