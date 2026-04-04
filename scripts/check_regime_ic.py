import sqlite3
import pandas as pd

DB_PATH = "/home/kazuha/Poly-Trader/poly_trader.db"
conn = sqlite3.connect(DB_PATH)

features = pd.read_sql_query("SELECT * FROM features_normalized ORDER BY id", conn)
labels = pd.read_sql_query("SELECT * FROM labels ORDER BY id", conn)
conn.close()

# Merge on id (features.id <-> labels.feature_id or labels.id)
if 'feature_id' in labels.columns:
    merged = features.merge(labels, left_on='id', right_on='feature_id', how='inner', suffixes=('_feat', '_label'))
else:
    merged = features.merge(labels, on=['id', 'timestamp'], how='inner', suffixes=('_feat', '_label'))

print(f"Merged: {len(merged)}, columns: {list(merged.columns[:15])}")

# Find regime and label
regime_col = 'regime_label_feat' if 'regime_label_feat' in merged.columns else 'regime_label_label'
# Check both
for c in ['regime_label_label', 'regime_label_feat', 'regime_label']:
    if c in merged.columns:
        print(f"Found {c}: {merged[c].value_counts().to_dict()}")
        regime_col = c

label_col = 'label_sell_win_label' if 'label_sell_win_label' in merged.columns else 'label_sell_win'
senses_map = {
    'eye': 'feat_eye', 'ear': 'feat_ear', 'nose': 'feat_nose',
    'tongue': 'feat_tongue', 'body': 'feat_body', 'pulse': 'feat_pulse',
    'aura': 'feat_aura', 'mind': 'feat_mind'
}
label = merged[label_col].astype(float)

print(f"\n=== Regime-Aware IC ===")
for regime in ['bear', 'bull', 'chop']:
    reg_mask = merged[regime_col].astype(str).str.strip().str.lower() == regime
    regime_passed = 0
    regime_passing = []
    for sname, col_name in senses_map.items():
        if col_name not in merged.columns:
            continue
        col = merged[col_name].astype(float)
        mask = reg_mask & col.notna() & label.notna()
        if mask.sum() > 10:
            ic = col[mask].corr(label[mask])
            if abs(ic) >= 0.05:
                regime_passed += 1
                regime_passing.append(f"{sname}({ic:+.4f})")
    print(f"  {regime.capitalize()}: {regime_passed}/8 - {regime_passing}")
