import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))
from config import load_config
from database.models import init_db, FeaturesNormalized

cfg = load_config()
session = init_db(cfg["database"]["url"])

# Check feat_ear
all_ears = session.query(FeaturesNormalized.feat_ear).filter(FeaturesNormalized.feat_ear.isnot(None)).all()
ear_values = [float(e[0]) for e in all_ears if e[0] is not None]
print(f"=== feat_ear ===")
print(f"  Count: {len(ear_values)}")
print(f"  Unique: {len(set(ear_values))}")
print(f"  Mean: {np.mean(ear_values):.8f}")
print(f"  Std:  {np.std(ear_values):.8f}")
print(f"  Min:  {np.min(ear_values):.8f}")
print(f"  Max:  {np.max(ear_values):.8f}")

# Check if values are quasi-discrete (few unique values when rounded)
rounded = [round(v, 4) for v in ear_values]
print(f"  Unique (rounded 4dp): {len(set(rounded))}")
rounded2 = [round(v, 6) for v in ear_values]
print(f"  Unique (rounded 6dp): {len(set(rounded2))}")

# Print first 10 unique sorted
sorted_ears = sorted(set(ear_values))
print(f"\n  First 15 unique values:")
for v in sorted_ears[:15]:
    print(f"    {v}")

# Check feat_tongue
all_tongues = session.query(FeaturesNormalized.feat_tongue).filter(FeaturesNormalized.feat_tongue.isnot(None)).all()
tongue_values = [float(t[0]) for t in all_tongues if t[0] is not None]
print(f"\n=== feat_tongue ===")
print(f"  Count: {len(tongue_values)}")
print(f"  Unique: {len(set(tongue_values))}")
print(f"  Mean: {np.mean(tongue_values):.8f}")
print(f"  Std:  {np.std(tongue_values):.8f}")
print(f"  Min:  {np.min(tongue_values):.8f}")
print(f"  Max:  {np.max(tongue_values):.8f}")

rounded = [round(v, 4) for v in tongue_values]
print(f"  Unique (rounded 4dp): {len(set(rounded))}")

sorted_tongues = sorted(set(tongue_values))
print(f"\n  First 15 unique values:")
for v in sorted_tongues[:15]:
    print(f"    {v}")
print(f"\n  Last 15 unique values:")
for v in sorted_tongues[-15:]:
    print(f"    {v}")

session.close()
