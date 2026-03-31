import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))
from config import load_config
from database.models import init_db, FeaturesNormalized
cfg = load_config()
session = init_db(cfg["database"]["url"])
count = session.query(FeaturesNormalized).count()
print(f"Total features: {count}")
latest = session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp.desc()).limit(5).all()
for f in latest:
    print(f"  {f.timestamp}: e={f.feat_eye_dist}, er={f.feat_ear_zscore}, n={f.feat_nose_sigmoid}, t={f.feat_tongue_pct}, b={f.feat_body_roc}")
session.close()
