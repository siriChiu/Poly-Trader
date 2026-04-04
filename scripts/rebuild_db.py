"""Step 1: Data collection — try to rebuild the database from collectors."""
import subprocess, os, sys

ROOT = '/home/kazuha/Poly-Trader'
os.chdir(ROOT)

# Check available scripts
scripts_dir = os.path.join(ROOT, 'scripts')
if os.path.exists(scripts_dir):
    print("Scripts available:")
    for f in sorted(os.listdir(scripts_dir)):
        if f.endswith('.py'):
            print(f"  {f}")

print("\n--- Trying collector scripts ---")
collector_dir = os.path.join(ROOT, 'data_ingestion')
if os.path.exists(collector_dir):
    print(f"Data ingestion modules:")
    for f in sorted(os.listdir(collector_dir)):
        if f.endswith('.py'):
            full = os.path.join(collector_dir, f)
            size = os.path.getsize(full)
            print(f"  {f} ({size} bytes)")

# Try to run the data ingestion / backfill
print("\n--- Checking labeling script ---")
for root, dirs, files in os.walk(ROOT):
    for f in files:
        if 'label' in f.lower() and f.endswith('.py'):
            full = os.path.join(root, f)
            print(f"  {full} ({os.path.getsize(full)} bytes)")

print("\n--- Checking database setup / init scripts ---")
for root, dirs, files in os.walk(ROOT):
    for f in files:
        if any(k in f.lower() for k in ['init', 'setup', 'migrate', 'backfill', 'ingest', 'collect']):
            if f.endswith('.py'):
                full = os.path.join(root, f)
                print(f"  {full} ({os.path.getsize(full)} bytes)")
