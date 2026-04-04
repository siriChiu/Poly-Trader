import sqlite3
db = sqlite3.connect('/home/kazuha/Poly-Trader/poly_trader.db')
cursor = db.cursor()
cursor.execute("PRAGMA table_info(features_normalized)")
columns = cursor.fetchall()
print("features_normalized columns:")
for c in columns:
    print(f"  {c[1]:30s} {c[2]:10s} nullable={c[3]==0}")

# Get values
col_names = [c[1] for c in columns]
ear_col = [c for c in col_names if 'ear' in c.lower()]
tongue_col = [c for c in col_names if 'tongue' in c.lower()]
print(f"\nEar columns: {ear_col}")
print(f"Tongue columns: {tongue_col}")

for col in ear_col[:2]:
    cursor.execute(f"SELECT DISTINCT {col} FROM features_normalized ORDER BY {col}")
    vals = [r[0] for r in cursor.fetchall()]
    print(f"\n{col}: {len(vals)} unique values: {vals[:20]}")

db.close()
