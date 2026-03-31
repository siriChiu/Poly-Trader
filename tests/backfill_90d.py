import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))
from data_ingestion.backfill_historical import run_backfill
r = run_backfill(days=90)
for k, v in r.items():
    print(f"{k}: {v}")
