import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))
from config import load_config
from database.models import init_db, FeaturesNormalized
from server.senses import SensesEngine

cfg = load_config()
session = init_db(cfg["database"]["url"])

engine = SensesEngine()
engine.set_db(session)

scores = engine.calculate_all_scores()
print(f"Scores: {scores}")

rec = engine.generate_advice(scores)
print(f"Recommendation: score={rec['score']}, action={rec['action']}")
print(f"Summary: {rec['summary']}")
for d in rec['descriptions']:
    print(f"  {d}")

# Check features in DB
row = session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp.desc()).first()
if row:
    print(f"\nLatest features: eye={row.feat_eye_dist}, ear={row.feat_ear_zscore}, nose={row.feat_nose_sigmoid}, tongue={row.feat_tongue_pct}, body={row.feat_body_roc}")

session.close()
