import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))
from config import load_config
from database.models import init_db, Labels, FeaturesNormalized

cfg = load_config()
session = init_db(cfg["database"]["url"])

total_labels = session.query(Labels).count()
pos_labels = session.query(Labels).filter(Labels.label_sell_win == 1).count()
total_feats = session.query(FeaturesNormalized).count()

print(f"Total labels: {total_labels}")
print(f"Positive labels: {pos_labels}")
print(f"Total features: {total_feats}")

# Check timestamp alignment
labels = session.query(Labels).limit(3).all()
feats = session.query(FeaturesNormalized).limit(3).all()

print("\nSample labels:")
for l in labels:
    print(f"  ts={l.timestamp}, sell_win={l.label_sell_win}")

print("\nSample features:")
for f in feats:
    print(f"  ts={f.timestamp}, eye={f.feat_eye}")

# Check join
from sqlalchemy import text
joined = session.execute(text(
    "SELECT COUNT(*) FROM features_normalized f "
    "INNER JOIN labels l ON f.timestamp = l.timestamp"
)).scalar()
print(f"\nJoined count (exact timestamp match): {joined}")

session.close()
