import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))
from config import load_config
from database.models import init_db
from analysis.sense_validator import validate_senses

cfg = load_config()
session = init_db(cfg["database"]["url"])
r = validate_senses(session, "BTCUSDT")
print(f"Status: {r['status']}")
print(f"Samples: {r['sample_count']}")
for col, d in r["details"].items():
    ic = f"{d['ic']:.4f}" if d['ic'] is not None else 'N/A'
    print(f"  {d['name']}: IC={ic}, null={d['null_ratio']:.0%}, status={d['status']}")
if r["issues"]:
    print("Issues:")
    for issue in r["issues"]:
        print(f"  {issue}")
else:
    print("No issues!")
session.close()
