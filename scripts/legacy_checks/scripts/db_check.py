import sqlite3, os, json

# Check poly_trader.db
path1 = '/home/kazuha/Poly-Trader/data/poly_trader.db'
path2 = '/home/kazuha/Poly-Trader/data/market.db'
path3 = '/home/kazuha/Poly-Trader/data/stock.db'

for p in [path1, path2, path3]:
    print(f"\n{p}")
    print(f"  Exists: {os.path.exists(p)}")
    print(f"  Size: {os.path.getsize(p)} bytes")

# Check if collectors exist
print("\n--- Collectors ---")
ingestion_dir = '/home/kazuha/Poly-Trader/data_ingestion'
if os.path.exists(ingestion_dir):
    for f in os.listdir(ingestion_dir):
        print(f"  {f}")

# Check labeling
print("\n--- Labeling ---")
for root, dirs, files in os.walk('/home/kazuha/Poly-Trader'):
    for f in files:
        if 'label' in f.lower() and f.endswith('.py'):
            print(f"  {os.path.join(root, f)}")
