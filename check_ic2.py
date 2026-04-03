import sqlite3
import numpy as np
from scipy import stats

import os
_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "poly_trader.db")
conn = sqlite3.connect(_db_path)

senses = {
    "eye": "feat_eye",
    "ear": "feat_ear",
    "nose": "feat_nose",
    "tongue": "feat_tongue",
    "body": "feat_body",
    "pulse": "feat_pulse",
    "aura": "feat_aura",
    "mind": "feat_mind",
}

for sense, col in senses.items():
    rows = conn.execute(
        f"SELECT f.{col}, l.label_sell_win FROM features_normalized f "
        f"JOIN labels l ON f.timestamp = l.timestamp "
        f"WHERE l.label_sell_win IS NOT NULL ORDER BY f.timestamp DESC LIMIT 2000"
    ).fetchall()
    if not rows:
        rows = conn.execute(
            f"SELECT f.{col}, l.label_sell_win FROM features_normalized f "
            f"JOIN labels l ON f.timestamp = l.timestamp "
            f"ORDER BY f.timestamp DESC LIMIT 2000"
        ).fetchall()
    v = np.array([r[0] for r in rows], dtype=float)
    lb = np.array([r[1] for r in rows], dtype=float)
    # Filter NaN pairs
    valid = ~(np.isnan(v) | np.isnan(lb))
    v, lb = v[valid], lb[valid]
    if len(v) < 50:
        print(f"[WARN] {sense}: too few valid samples (N={len(v)})")
        continue
    ic, pval = stats.spearmanr(v, lb)
    flag = "WARN" if abs(ic) < 0.05 else "OK"
    print(f"[{flag}] {sense}: IC={ic:.4f} p={pval:.4f} N={len(v)}")

# Check distinct horizon values
horizons = conn.execute("SELECT DISTINCT horizon_minutes FROM labels").fetchall()
print(f"\nDistinct horizons: {horizons}")
conn.close()
