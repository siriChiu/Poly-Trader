#!/usr/bin/env python3
"""模型Benchmark 平台 — 自動跑多種模型 → 產生 Leaderboard

用法:
  python scripts/model_benchmark.py                          # 預設: 全部模型
  python scripts/model_benchmark.py --models xgb,rf,gbm     # 指定模型
  python scripts/model_benchmark.py --task classification   # 分類 (預設)
  python scripts/model_benchmark.py --task regression        # 回歸
  python scripts/model_benchmark.py --horizon 1440          # 24h 標籤 (預設 720=12h)
  python scripts/model_benchmark.py --splits 5              # TimeSeriesSplit 数量
  python scripts/model_benchmark.py --regime bull           # 只跑牛市資料
  python scripts/model_benchmark.py --features core         # 只跑核心 8 特徵
  python scripts/model_benchmark.py --features all          # 全部 22 特徵 (預設)
  python scripts/model_benchmark.py --features 4h           # 只跑 4H 特徵

輸出:
  data/model_leaderboard.json  — 完整 Leaderboard (JSON)
  終端機印出美觀排行榜
"""
import sys
import os
import json
import time
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.chdir(Path(__file__).parent.parent)

import numpy as np
import pandas as pd
import sqlite3
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, roc_auc_score, mean_squared_error, f1_score
from sklearn.preprocessing import StandardScaler

DB_PATH = 'poly_trader.db'


# ──────────────────────────────
# 模型工廠
# ──────────────────────────────

def get_model(name: str, random_state: int = 42):
    """建立模型實例。回傳 (name, model_instance, needs_scaling)"""
    if name == 'xgb':
        import xgboost as xgb
        return 'XGBClassifier', xgb.XGBClassifier(
            n_estimators=300, max_depth=5, learning_rate=0.03,
            colsample_bytree=0.6, subsample=0.8,
            reg_alpha=0.1, reg_lambda=1.0,
            eval_metric='logloss', random_state=random_state, verbosity=0
        ), False

    elif name == 'xgb_deep':
        import xgboost as xgb
        return 'XGB-Deep', xgb.XGBClassifier(
            n_estimators=500, max_depth=8, learning_rate=0.01,
            colsample_bytree=0.4, subsample=0.7,
            min_child_weight=5, reg_alpha=0.5, reg_lambda=2.0,
            eval_metric='logloss', random_state=random_state, verbosity=0
        ), False

    elif name == 'rf':
        from sklearn.ensemble import RandomForestClassifier
        return 'RandomForest', RandomForestClassifier(
            n_estimators=300, max_depth=12, min_samples_leaf=50,
            class_weight='balanced', random_state=random_state, n_jobs=-1
        ), False

    elif name == 'gbm':
        from sklearn.ensemble import GradientBoostingClassifier
        return 'GradientBoost', GradientBoostingClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.05,
            min_samples_leaf=30, subsample=0.7,
            random_state=random_state
        ), False

    elif name == 'lr':
        from sklearn.linear_model import LogisticRegression
        return 'LogisticReg', LogisticRegression(
            C=0.1, max_iter=2000, random_state=random_state
        ), True

    elif name == 'svm':
        from sklearn.svm import SVC
        return 'SVC', SVC(
            C=0.1, kernel='rbf', probability=True, random_state=random_state
        ), True

    elif name == 'catboost':
        try:
            from catboost import CatBoostClassifier
            return 'CatBoost', CatBoostClassifier(
                iterations=300, depth=6, learning_rate=0.03,
                l2_leaf_reg=1.0, verbose=0, random_state=random_state
            ), False
        except ImportError:
            return None, None, False

    elif name == 'lightgbm':
        try:
            import lightgbm as lgb
            return 'LightGBM', lgb.LGBMClassifier(
                n_estimators=300, max_depth=6, learning_rate=0.03,
                colsample_bytree=0.6, subsample=0.8,
                reg_alpha=0.1, reg_lambda=1.0,
                random_state=random_state, verbose=-1
            ), False
        except ImportError:
            return None, None, False

    elif name == 'ridge':
        from sklearn.linear_model import RidgeClassifier
        return 'Ridge', RidgeClassifier(
            alpha=1.0, random_state=random_state
        ), True

    return None, None, False


# ──────────────────────────────
# 資料載入
# ──────────────────────────────

def load_data(feature_set: str = 'all', horizon: int = 720, regime: str = None):
    """載入訓練資料。

    feature_set: 'core' (8), 'all' (22), '4h' (只用 4H 特徵)
    horizon: 標籤 horizon_minutes
    regime: 'bull', 'bear', None (全部)
    """
    # 特徵定義
    CORE_FEATURES = [
        'feat_eye', 'feat_ear', 'feat_nose', 'feat_tongue',
        'feat_body', 'feat_pulse', 'feat_aura', 'feat_mind',
    ]

    TECH_FEATURES = [
        'feat_vix', 'feat_dxy',
        'feat_rsi14', 'feat_macd_hist', 'feat_atr_pct',
        'feat_vwap_dev', 'feat_bb_pct_b',
    ]

    F4H_FEATURES = [
        'feat_4h_bias50', 'feat_4h_bias20',
        'feat_4h_rsi14', 'feat_4h_macd_hist',
        'feat_4h_bb_pct_b', 'feat_4h_ma_order',
        'feat_4h_dist_swing_low',
    ]

    P0_FEATURES = [
        'feat_nq_return_1h', 'feat_nq_return_24h',
        'feat_claw', 'feat_claw_intensity',
        'feat_fang_pcr', 'feat_fang_skew',
        'feat_fin_netflow', 'feat_web_whale',
        'feat_scales_ssr', 'feat_nest_pred',
    ]

    if feature_set == 'core':
        feature_cols = CORE_FEATURES
    elif feature_set == '4h':
        feature_cols = F4H_FEATURES
    elif feature_set == '4h_core':
        feature_cols = CORE_FEATURES + F4H_FEATURES
    else:  # all
        feature_cols = CORE_FEATURES + TECH_FEATURES + F4H_FEATURES

    all_feat_str = ','.join(feature_cols)

    sql = f"""
        SELECT {all_feat_str}, l.label_sell_win,
               l.future_return_pct, l.future_max_drawdown,
               f.regime_label
        FROM features_normalized f
        JOIN labels l ON l.timestamp = f.timestamp AND l.symbol = f.symbol
        WHERE l.label_sell_win IS NOT NULL AND l.horizon_minutes = ?
        ORDER BY f.timestamp
    """

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(sql, conn, params=(horizon,))
    conn.close()

    if df.empty:
        print(f"  ❌ 無資料 (horizon={horizon})")
        return None, None, None

    # 過濾 regime
    if regime:
        if regime == 'bull':
            df = df[df['regime_label'] == 'bull']
        elif regime == 'bear':
            df = df[df['regime_label'] == 'bear']
        elif regime == 'chop':
            df = df[df['regime_label'] == 'chop']

    # 過濾掉全 0 或全 NaN 的特徵
    valid_cols = []
    dropped = []
    for col in feature_cols:
        if col not in df.columns:
            dropped.append(col)
            continue
        non_zero = (df[col] != 0).sum()
        if non_zero < len(df) * 0.1:  # 少於 10% 非零 → 刪除
            dropped.append(col)
        else:
            valid_cols.append(col)

    if dropped:
        print(f"  ⚠️  刪除無效特徵 ({len(dropped)}): {', '.join(dropped)}")

    X = df[valid_cols].fillna(0).values.astype(np.float32)
    y = df['label_sell_win'].values.astype(int)

    print(f"  資料: {len(X)} 筆 | 特徵: {len(valid_cols)} | 勝率: {y.mean():.1%}")
    print(f"  時間: {df.index[0]} ~ {df.index[-1]}")

    return X, y, valid_cols


# ──────────────────────────────
# Benchmark 引擎
# ──────────────────────────────

def run_benchmark(models: list, task: str, feature_set: str,
                   horizon: int, regime: str, n_splits: int,
                   random_state: int = 42):
    """跑多個模型 → 回傳 Leaderboard"""

    print(f"\n{'='*65}")
    print(f"  🧪 Model Benchmark Platform")
    print(f"{'='*65}")
    print(f"  任務: {task}  |  特徵: {feature_set}  |  Horizon: {horizon}min")
    if regime:
        print(f"  市場狀態: {regime}  |  ", end='')
    print(f"TimeSeriesSplit: {n_splits}")
    print(f"  隨機種子: {random_state}")

    # 載入資料
    print(f"\n📥 載入資料...")
    X, y, feature_cols = load_data(feature_set, horizon, regime)
    if X is None:
        return []

    # 跑每個模型
    results = []
    total_start = time.time()

    for model_key in models:
        model_name, model, needs_scale = get_model(model_key, random_state)
        if model_name is None:
            print(f"  ⏭️  跳過 {model_key} (未安裝)")
            continue

        print(f"\n{'─'*65}")
        print(f"  🤖 {model_name}")
        print(f"{'─'*65}")

        fold_accs, fold_aucs, fold_f1s = [], [], []
        fold_feature_imp = {}
        importances_per_fold = []

        tscv = TimeSeriesSplit(n_splits=n_splits)
        fold_start = time.time()

        for fold_i, (tr_idx, te_idx) in enumerate(tscv.split(X)):
            X_tr, X_te = X[tr_idx], X[te_idx]
            y_tr, y_te = y[tr_idx], y[te_idx]

            # 縮放
            scaler = None
            if needs_scale:
                scaler = StandardScaler()
                X_tr = scaler.fit_transform(X_tr)
                X_te = scaler.transform(X_te)

            # 訓練
            m = type(model)(**model.get_params())
            m.fit(X_tr, y_tr)

            # 預測
            preds = m.predict(X_te)
            acc = accuracy_score(y_te, preds)
            fold_accs.append(acc)

            try:
                if hasattr(m, 'predict_proba'):
                    probs = m.predict_proba(X_te)[:, 1]
                else:
                    # RidgeClassifier etc. use decision_function
                    logits = m.decision_function(X_te)
                    # Convert to probs via sigmoid
                    probs = 1 / (1 + np.exp(-np.clip(logits, -500, 500)))
                auc = roc_auc_score(y_te, probs)
                fold_aucs.append(auc)
            except (ValueError, IndexError, AttributeError):
                fold_aucs.append(0.5)

            fold_f1 = f1_score(y_te, preds)
            fold_f1s.append(fold_f1)

            # 特徵重要度
            imp = None
            try:
                imp = m.feature_importances_
            except AttributeError:
                try:
                    coef = m.coef_
                    # Ridge/Logistic: coef_ can be 1D or 2D
                    if coef.ndim == 2:
                        imp = np.abs(coef[0])
                    else:
                        imp = np.abs(coef)
                except (AttributeError, IndexError, AttributeError):
                    pass
            
            if imp is not None and len(imp) >= len(feature_cols):
                imp = imp[:len(feature_cols)]  # safety trim
                importances_per_fold.append(imp)
                for fi, col in enumerate(feature_cols):
                    if col not in fold_feature_imp:
                        fold_feature_imp[col] = []
                    fold_feature_imp[col].append(float(imp[fi]))

            top3_idx = np.argsort(imp)[-3:][::-1] if imp is not None and len(imp) >= 3 else []
            top3 = [feature_cols[i] for i in top3_idx] if len(top3_idx) >= 3 else []
            print(f"    Fold {fold_i + 1}: acc={acc:.4f}  auc={fold_aucs[-1]:.4f}  f1={fold_f1:.4f}  top3={top3}")

        fold_time = time.time() - fold_start

        # Final model: train on all data
        final_scaler = None
        final_X = X
        if needs_scale:
            final_scaler = StandardScaler()
            final_X = final_scaler.fit_transform(X)

        final_model = type(model)(**model.get_params())
        final_model.fit(final_X, y)

        # 平均特徵重要度
        avg_imp = {}
        for col, vals in fold_feature_imp.items():
            avg_imp[col] = round(float(np.mean(vals)), 6)

        # Top 5 features overall
        top5 = sorted(avg_imp.items(), key=lambda x: -x[1])[:5]
        top5_str = ', '.join([f"{c.replace('feat_', '')}={v:.3f}" for c, v in top5])

        # 計算 cross-val 標準差
        mean_acc = float(np.mean(fold_accs))
        std_acc = float(np.std(fold_accs))
        mean_auc = float(np.mean(fold_aucs))
        std_auc = float(np.std(fold_aucs))
        mean_f1 = float(np.mean(fold_f1s))
        std_f1 = float(np.std(fold_f1s))

        result = {
            'rank': 0,
            'model': model_name,
            'model_key': model_key,
            'task': task,
            'feature_set': feature_set,
            'horizon': horizon,
            'regime': regime or 'all',
            'n_samples': len(X),
            'n_features': len(feature_cols),
            'accuracy': round(mean_acc, 4),
            'acc_std': round(std_acc, 4),
            'auc': round(mean_auc, 4),
            'auc_std': round(std_auc, 4),
            'f1': round(mean_f1, 4),
            'f1_std': round(std_f1, 4),
            'fold_time': round(fold_time, 1),
            'feature_importance': avg_imp,
            'top_features': top5_str,
            'timestamp': datetime.now().isoformat(),
        }
        results.append(result)

    total_time = time.time() - total_start

    # 排序
    results.sort(key=lambda x: -x['auc'])
    for i, r in enumerate(results):
        r['rank'] = i + 1

    # 印出 Leaderboard
    print(f"\n\n{'='*65}")
    print(f"  🏆 Model Leaderboard")
    print(f"{'='*65}")
    print(f"  {'#':>2s} | {'Model':15s} | {'Acc':>7s} | {'AUC':>7s} | {'F1':>7s} | {'Time':>5s} | Top Feature")
    print(f"  {'─'*2} | {'─'*15} | {'─'*7} | {'─'*7} | {'─'*7} | {'─'*5} | {'─'*20}")

    for r in results:
        medal = '🥇' if r['rank'] == 1 else '🥈' if r['rank'] == 2 else '🥉' if r['rank'] == 3 else ' '
        top_feat = r['top_features'].split(',')[0] if r['top_features'] else '-'
        print(f"  {medal}{r['rank']} | {r['model']:15s} | {r['accuracy']:.4f}±{r['acc_std']:.3f}"
              f" | {r['auc']:.4f}±{r['auc_std']:.3f} | {r['f1']:.4f}  | {r['fold_time']:.0f}s"
              f" | {top_feat}")

    print(f"\n{'='*65}")
    print(f"  總時間: {total_time:.1f}s | 最佳模型: {results[0]['model']} (AUC={results[0]['auc']:.4f})")
    print(f"{'='*65}")

    # 儲存 Leaderboard
    os.makedirs('data', exist_ok=True)
    lb_path = 'data/model_leaderboard.json'

    # 累加而不是覆蓋
    if os.path.exists(lb_path):
        with open(lb_path, 'r') as f:
            existing = json.load(f)
    else:
        existing = {"experiments": []}

    # 加入實驗
    existing["experiments"].append({
        "id": f"exp_{len(existing['experiments']) + 1}",
        "timestamp": datetime.now().isoformat(),
        "config": {
            "models": models,
            "task": task,
            "feature_set": feature_set,
            "horizon": horizon,
            "regime": regime or "all",
            "n_splits": n_splits,
        },
        "models": results,
    })

    # 只保留最近 20 次實驗
    if len(existing["experiments"]) > 20:
        existing["experiments"] = existing["experiments"][-20:]

    with open(lb_path, 'w') as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    print(f"  📁 Leaderboard saved to {lb_path}")

    return results


# ──────────────────────────────
# CLI 介面
# ──────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description='Model Benchmark Platform')
    p.add_argument('--models', type=str, default='xgb,xgb_deep,rf,gbm,lr,svm,ridge',
                   help='Comma-separated model keys (xgb,rf,gbm,lr,svm,catboost,lightgbm,ridge)')
    p.add_argument('--task', type=str, default='classification',
                   choices=['classification', 'regression'])
    p.add_argument('--features', type=str, default='all',
                   choices=['core', 'all', '4h', '4h_core'],
                   help='Feature set to use')
    p.add_argument('--horizon', type=int, default=240,
                   help='Label horizon in minutes (default 240 = 4h)')
    p.add_argument('--regime', type=str, default=None,
                   choices=['bull', 'bear', 'chop'],
                   help='Filter by regime')
    p.add_argument('--splits', type=int, default=5)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--json', action='store_true',
                   help='Output only JSON, no human-readable output')
    return p.parse_args()


if __name__ == '__main__':
    args = parse_args()
    model_list = [m.strip() for m in args.models.split(',')]

    results = run_benchmark(
        models=model_list,
        task=args.task,
        feature_set=args.features,
        horizon=args.horizon,
        regime=args.regime,
        n_splits=args.splits,
        random_state=args.seed,
    )

    if args.json and results:
        print("\n---JSON_OUTPUT_START---")
        print(json.dumps(results, indent=2, ensure_ascii=False))
        print("---JSON_OUTPUT_END---")
