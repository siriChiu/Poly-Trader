import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))
from config import load_config
from database.models import init_db
from model.train import run_training, load_training_data, FEATURE_COLS
import numpy as np

cfg = load_config()
session = init_db(cfg["database"]["url"])
loaded = load_training_data(session, min_samples=50)
if loaded:
    X, y = loaded
    print(f"Training: {len(X)} samples, {y.mean():.2%} positive")
    for col in FEATURE_COLS:
        vals = X[col].dropna()
        print(f"  {col}: mean={vals.mean():.4f}, std={vals.std():.4f}")
    ok = run_training(session)
    print(f"\nResult: {ok}")
else:
    print("Not enough data")
session.close()
