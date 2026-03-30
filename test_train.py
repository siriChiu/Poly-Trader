"""
直接訓練腳本：用 pandas 讀取 + merge，確保 timestamp 對齊
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

import pandas as pd
from config import load_config
from database.models import init_db, FeaturesNormalized, Labels
from model.train import train_xgboost, save_model, FEATURE_COLS

cfg = load_config()
session = init_db(cfg["database"]["url"])

# 讀取特徵
feat_rows = session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp).all()
feat_df = pd.DataFrame([{
    "ts_hour": r.timestamp.replace(minute=0, second=0, microsecond=0),
    "feat_eye_dist": r.feat_eye_dist,
    "feat_ear_zscore": r.feat_ear_zscore,
    "feat_nose_sigmoid": r.feat_nose_sigmoid,
    "feat_tongue_pct": r.feat_tongue_pct,
    "feat_body_roc": r.feat_body_roc,
} for r in feat_rows])

# 讀取標籤
label_rows = session.query(Labels).order_by(Labels.timestamp).all()
label_df = pd.DataFrame([{
    "ts_hour": r.timestamp.replace(minute=0, second=0, microsecond=0),
    "label": r.label,
} for r in label_rows])

print(f"Features: {len(feat_df)}")
print(f"Labels: {len(label_df)}")

# 合併
merged = pd.merge(feat_df, label_df, on="ts_hour", how="inner")
merged.dropna(subset=FEATURE_COLS + ["label"], inplace=True)

print(f"Merged: {len(merged)}")
print(f"Positive labels: {merged['label'].sum()} / {len(merged)} ({merged['label'].mean():.2%})")
print(f"\nFeature stats:")
print(merged[FEATURE_COLS].describe())

if len(merged) >= 50:
    X = merged[FEATURE_COLS]
    y = merged["label"].astype(int)
    print(f"\nTraining XGBoost on {len(X)} samples...")
    model = train_xgboost(X, y)
    save_model(model)
    importances = dict(zip(FEATURE_COLS, model.feature_importances_.tolist()))
    print(f"\nFeature importances:")
    for k, v in sorted(importances.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v:.4f}")
    print("\nTraining SUCCESS!")
else:
    print("Not enough samples for training")

session.close()
