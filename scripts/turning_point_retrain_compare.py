#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import os
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backtesting.model_leaderboard import ModelLeaderboard, MIN_TRAIN_SAMPLES

DB_PATH = PROJECT_ROOT / "poly_trader.db"
MODELS = ["xgboost", "random_forest", "logistic_regression"]
TARGETS = [
    ("label_local_bottom", "local_bottom"),
    ("label_local_top", "local_top"),
    ("turning_point_hot", "turning_point_hot"),
]
TOP_PCTS = [0.05, 0.10, 0.20]


def load_frame() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    try:
        feature_cols = [
            'feat_eye','feat_ear','feat_nose','feat_tongue','feat_body','feat_pulse','feat_aura','feat_mind',
            'feat_vix','feat_dxy','feat_rsi14','feat_macd_hist','feat_atr_pct','feat_vwap_dev','feat_bb_pct_b',
            'feat_nw_width','feat_nw_slope','feat_adx','feat_choppiness','feat_donchian_pos',
            'feat_4h_bias50','feat_4h_bias20','feat_4h_bias200','feat_4h_rsi14','feat_4h_macd_hist',
            'feat_4h_bb_pct_b','feat_4h_dist_bb_lower','feat_4h_ma_order','feat_4h_dist_swing_low','feat_4h_vol_ratio',
            'feat_local_bottom_score','feat_local_top_score','feat_turning_point_score','feat_wick_rejection',
            'feat_volume_exhaustion','feat_tunnel_distance','feat_dist_swing_high'
        ]
        fselect = ', '.join(['timestamp'] + feature_cols)
        features_df = pd.read_sql(f"SELECT {fselect} FROM features_normalized WHERE symbol='BTCUSDT' ORDER BY timestamp", conn)
        raw_df = pd.read_sql("SELECT timestamp, close_price FROM raw_market_data WHERE symbol='BTCUSDT' AND close_price IS NOT NULL ORDER BY timestamp", conn)
        labels_df = pd.read_sql(
            """
            SELECT timestamp, horizon_minutes, label_local_bottom, label_local_top, turning_point_score,
                   simulated_pyramid_win, label_spot_long_win
            FROM labels
            WHERE horizon_minutes=1440
            ORDER BY timestamp
            """,
            conn,
        )
    finally:
        conn.close()

    for df in (features_df, raw_df, labels_df):
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed')
        df.sort_values('timestamp', inplace=True)

    merged = pd.merge_asof(features_df, raw_df, on='timestamp', direction='nearest')
    merged = pd.merge_asof(merged, labels_df, on='timestamp', direction='nearest')
    merged = merged.dropna(subset=['close_price']).reset_index(drop=True)
    merged['turning_point_hot'] = (pd.to_numeric(merged['turning_point_score'], errors='coerce').fillna(0.0) >= 0.75).astype(int)
    return merged


def evaluate_target(data: pd.DataFrame, target_col: str, label: str) -> dict:
    data = data.dropna(subset=[target_col]).copy()
    payload = {
        'target_col': target_col,
        'label': label,
        'rows': int(len(data)),
        'positive_ratio': round(float(pd.to_numeric(data[target_col], errors='coerce').fillna(0).mean()), 4) if len(data) else None,
        'models': [],
    }
    if len(data) < MIN_TRAIN_SAMPLES:
        payload['error'] = 'insufficient_rows'
        return payload

    lb = ModelLeaderboard(data, target_col=target_col)
    splits = lb._get_walk_forward_splits()
    feat_cols = [c for c in data.columns if c.startswith('feat_')]

    for model_name in MODELS:
        fold_rows = []
        for fold_idx, (train_start, train_end, test_start, test_end) in enumerate(splits, start=1):
            train_mask = (data['timestamp'] >= pd.Timestamp(train_start)) & (data['timestamp'] < pd.Timestamp(train_end))
            test_mask = (data['timestamp'] >= pd.Timestamp(test_start)) & (data['timestamp'] < pd.Timestamp(test_end))
            train_df = data.loc[train_mask].copy()
            test_df = data.loc[test_mask].copy()
            if len(train_df) < MIN_TRAIN_SAMPLES or len(test_df) < 50:
                continue
            y_train = pd.to_numeric(train_df[target_col], errors='coerce').fillna(0).astype(int)
            y_test = pd.to_numeric(test_df[target_col], errors='coerce').fillna(0).astype(int)
            if y_train.nunique() < 2 or y_test.nunique() < 2:
                continue
            model = lb._train_model(train_df[feat_cols].fillna(0).values, y_train.values, model_name)
            if model is None:
                continue
            proba = lb._get_confidence(model, test_df[feat_cols].fillna(0).values, model_name)
            pred = (proba >= 0.5).astype(int)
            acc = float((pred == y_test.values).mean())
            row = {
                'fold': fold_idx,
                'accuracy': acc,
                'test_rows': int(len(test_df)),
                'avg_turning_point_score_all': float(pd.to_numeric(test_df['turning_point_score'], errors='coerce').fillna(0.0).mean()),
            }
            for pct in TOP_PCTS:
                n = max(1, int(math.ceil(len(test_df) * pct)))
                order = np.argsort(proba)[-n:]
                selected = test_df.iloc[order]
                row[f'top_{int(pct*100)}_win_rate'] = float(pd.to_numeric(selected[target_col], errors='coerce').fillna(0).mean())
                row[f'top_{int(pct*100)}_avg_turning_score'] = float(pd.to_numeric(selected['turning_point_score'], errors='coerce').fillna(0.0).mean())
            fold_rows.append(row)

        if not fold_rows:
            payload['models'].append({'model_name': model_name, 'error': 'no_valid_folds'})
            continue

        fr = pd.DataFrame(fold_rows)
        payload['models'].append({
            'model_name': model_name,
            'folds': int(len(fr)),
            'cv_accuracy_mean': round(float(fr['accuracy'].mean()), 4),
            'cv_accuracy_std': round(float(fr['accuracy'].std(ddof=0)), 4),
            'top_5_win_rate': round(float(fr['top_5_win_rate'].mean()), 4),
            'top_10_win_rate': round(float(fr['top_10_win_rate'].mean()), 4),
            'top_20_win_rate': round(float(fr['top_20_win_rate'].mean()), 4),
            'top_5_avg_turning_score': round(float(fr['top_5_avg_turning_score'].mean()), 4),
            'top_10_avg_turning_score': round(float(fr['top_10_avg_turning_score'].mean()), 4),
            'top_20_avg_turning_score': round(float(fr['top_20_avg_turning_score'].mean()), 4),
            'baseline_avg_turning_score': round(float(fr['avg_turning_point_score_all'].mean()), 4),
        })

    payload['models'] = sorted(
        payload['models'],
        key=lambda m: (
            m.get('top_10_avg_turning_score', -1),
            m.get('top_10_win_rate', -1),
            m.get('cv_accuracy_mean', -1),
        ),
        reverse=True,
    )
    return payload


def main() -> int:
    data = load_frame()
    results = [evaluate_target(data, target_col, label) for target_col, label in TARGETS]
    out_path = PROJECT_ROOT / 'data' / 'turning_point_retrain_comparison.json'
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f'\nSaved to {out_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
