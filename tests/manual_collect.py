import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))
from config import load_config
from database.models import init_db
from data_ingestion.collector import run_collection_and_save
from feature_engine.preprocessor import run_preprocessor

cfg = load_config()
session = init_db(cfg["database"]["url"])
print("Collecting...")
ok = run_collection_and_save(session, cfg["trading"]["symbol"])
print(f"Collection: {ok}")
if ok:
    feat = run_preprocessor(session, cfg["trading"]["symbol"])
    print(f"Features: {feat}")
session.close()
