#!/usr/bin/env python
"""Find database paths"""
import sqlite3, os, glob

print("=== Finding databases ===\n")

# Check various possible locations
candidates = [
    "/home/kazuha/.hermes/poly_trader/data/market.db",
    "/home/kazuha/Poly-Trader/poly_trader.db",
    "/home/kazuha/Poly-Trader/data/market.db",
    "/home/kazuha/Poly-Trader/database/market.db",
    "/home/kazuha/Poly-Trader/database/poly_trader.db",
    "/home/kazuha/.hermes/poly_trader/poly_trader.db",
]

for path in candidates:
    if os.path.exists(path):
        print(f"FOUND: {path}")
        # Get table names and counts
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in cursor.fetchall()]
        print(f"  Tables: {tables}")
        for t in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {t}")
            count = cursor.fetchone()[0]
            print(f"    {t}: {count} rows")
        conn.close()
    else:
        print(f"NOT FOUND: {path}")

# Also check config
print("\n=== Checking config ===")
config_paths = [
    "/home/kazuha/Poly-Trader/config.json",
    "/home/kazuha/Poly-Trader/config.py",
    "/home/kazuha/Poly-Trader/config.yaml",
]
for p in config_paths:
    if os.path.exists(p):
        print(f"  {p}:")
        with open(p) as f:
            content = f.read()[:500]
            for line in content.split('\n')[:20]:
                if 'db' in line.lower() or 'database' in line.lower() or 'sqlite' in line.lower() or 'path' in line.lower():
                    print(f"    {line.strip()}")

# List .db files in project
print("\n=== .db files ===")
for p in glob.glob("/home/kazuha/Poly-Trader/**/*.db", recursive=True):
    print(f"  {p} ({os.path.getsize(p):,} bytes)")

# List .db files in .hermes
for p in glob.glob("/home/kazuha/.hermes/**/*.db", recursive=True):
    print(f"  {p} ({os.path.getsize(p):,} bytes)")
