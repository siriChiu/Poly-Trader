"""
直接訓練腳本：呼叫新版 run_training，確保 model payload 包含 calibration。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from config import load_config
from database.models import init_db
from model.train import run_training

cfg = load_config()
session = init_db(cfg["database"]["url"])

print("Starting calibrated training...")
ok = run_training(session)
print(f"Training result: {ok}")
session.close()
