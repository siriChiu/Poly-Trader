import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))
from config import load_config
from database.models import init_db, FeaturesNormalized
cfg = load_config()
session = init_db(cfg["database"]["url"])
latest = session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp.desc()).first()
if latest:
    print(f"Latest: {latest.timestamp}")
    print(f"  eye={latest.feat_eye_dist}, ear={latest.feat_ear_zscore}, nose={latest.feat_nose_sigmoid}")
    print(f"  tongue={latest.feat_tongue_pct}, body={latest.feat_body_roc}")
else:
    print("No features")
session.close()
