#!/usr/bin/env python3
"""🧪 Post-Label-Fix Experiments

After fixing the inverted labels, test:
1. Standard retrain — Does AUC finally break 50%?
2. Regime Filtering — Training on Bear+Bull only (exclude Chop)
3. Feature Pruning — Auto-remove |IC| < 0.03
4. Threshold sweep — Compare different label thresholds
"""
import os, sys, json, time
import sqlite3
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

PROJECT = "/home/kazuha/Poly-Trader"
sys.path.insert(0, PROJECT)
os.chdir(PROJECT)

DB_PATH = os.path.join(PROJECT, "poly_trader.db")

FEATURE_COLS = [
    "feat_eye", "feat_ear", "feat_nose", "feat_tongue",
    "feat_body", "feat_pulse", "feat_aura", "feat_mind",
    "feat_vix", "feat_dxy",
    "feat_rsi14", "feat_macd_hist", "feat_atr_pct",
    "feat_vwap_dev", "feat_bb_pct_b",
    "feat_nq_return_1h", "feat_nq_return_24h",
    "feat_claw", "feat_claw_intensity", "feat_fang_pcr",
    "feat_fang_skew", "feat_fin_netflow",
    "feat_web_whale", "feat_scales_ssr", "feat_nest_pred",
]

from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, roc_auc_score, f1_score, precision_score, recall_score
from sklearn.utils.class_weight import compute_sample_weight
import xgboost as xgb


# ─── Data Loading ───
def load_data(include_regimes=None, drop_low_ic=0.0):
    """Load features + labels from DB, with optional regime filter and IC pruning."""
    conn = sqlite3.connect(DB_PATH)
    
    col_str = ", ".join([f"f.{c}" for c in FEATURE_COLS] + [
        "f.timestamp", "f.regime_label"
    ])
    query = f"SELECT {col_str} FROM features_normalized f ORDER BY f.timestamp"
    df = pd.read_sql_query(query, conn)
    
    labels = pd.read_sql_query(
        "SELECT timestamp, label_sell_win, future_return_pct FROM labels WHERE label_sell_win IS NOT NULL",
        conn
    )
    conn.close()
    
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="ISO8601")
    labels["timestamp"] = pd.to_datetime(labels["timestamp"], format="ISO8601")
    
    # Optional regime filter
    if include_regimes:
        df = df[df["regime_label"].isin(include_regimes)].copy()
        regimes_text = "+".join(include_regimes)
    else:
        regimes_text = "ALL"
    
    merged = pd.merge_asof(
        df.sort_values("timestamp"),
        labels.sort_values("timestamp"),
        on="timestamp",
        direction="nearest",
        tolerance=pd.Timedelta("10min"),
    )
    merged = merged.dropna(subset=["label_sell_win"]).copy()
    
    if len(merged) < 100:
        return None, None, None
    
    # Lag features
    LAG_STEPS = [12, 48, 144]
    all_cols = list(FEATURE_COLS)
    for col in FEATURE_COLS:
        for lag in LAG_STEPS:
            lag_col = f"{col}_lag{lag}"
            merged[lag_col] = merged[col].shift(lag)
            all_cols.append(lag_col)
    
    # Cross features
    merged["feat_vix_x_eye"] = merged["feat_vix"] * merged["feat_eye"]
    merged["feat_vix_x_mind"] = merged["feat_vix"] * merged["feat_mind"]
    merged["feat_mind_x_pulse"] = merged["feat_mind"] * merged["feat_pulse"]
    merged["feat_eye_x_ear"] = merged["feat_eye"] * merged["feat_ear"]
    merged["feat_mean_rev_proxy"] = merged["feat_mind"] - merged["feat_aura"]
    cross_cols = ["feat_vix_x_eye", "feat_vix_x_mind", "feat_mind_x_pulse", 
                  "feat_eye_x_ear", "feat_mean_rev_proxy"]
    all_cols.extend(cross_cols)
    
    for col in all_cols:
        merged[col] = pd.to_numeric(merged[col], errors='coerce')
    merged[all_cols] = merged[all_cols].fillna(0.0)
    
    # Compute IC for each feature
    y_arr = merged["label_sell_win"].astype(float).values
    ic_values = {}
    for col in all_cols:
        f_arr = merged[col].astype(float).values
        mask = ~(np.isnan(f_arr) | np.isnan(y_arr))
        if mask.sum() > 30:
            try:
                ic, _ = stats.spearmanr(f_arr[mask], y_arr[mask])
                ic_values[col] = float(ic) if ic is not None and np.isfinite(ic) else 0
            except:
                ic_values[col] = 0
    
    # Apply IC threshold pruning
    if drop_low_ic > 0:
        kept = set()
        for col in all_cols:
            base = col.replace("_lag12", "").replace("_lag48", "").replace("_lag144", "")
            if base not in FEATURE_COLS or abs(ic_values.get(col, 0)) > drop_low_ic:
                kept.add(col)
        all_cols = [c for c in all_cols if c in kept]
        print(f"  📉 Pruned to {len(all_cols)} features (|IC| > {drop_low_ic})")
    
    # Invert negative-IC features (for model training consistency)
    neg_ic_cols = set()
    for col in all_cols:
        if ic_values.get(col, 0) < 0:
            neg_ic_cols.add(col)
            merged[col] = -merged[col]
    
    X = merged[all_cols].copy()
    y = merged["label_sell_win"].astype(int).values
    
    print(f"  📊 {regimes_text}: {len(X)} samples, {X.shape[1]} features, y={y.mean():.4f}")
    if drop_low_ic > 0:
        print(f"  📉 Dropped {sum(1 for c in FEATURE_COLS if abs(ic_values.get(c, 0)) < drop_low_ic)} core cols")
    
    return X, y, {
        "regimes": regimes_text,
        "n_samples": len(X),
        "n_features": X.shape[1],
        "ic_values": ic_values,
        "neg_ic_cols": list(neg_ic_cols),
    }


def evaluate(X, y, name="", n_splits=5):
    """TimeSeriesSplit eval with OOF AUC."""
    tscv = TimeSeriesSplit(n_splits=n_splits)
    oof_pred = np.zeros(len(y))
    
    total_time = time.time()
    
    for fold_idx, (train_idx, test_idx) in enumerate(tscv.split(X)):
        X_tr = X.iloc[train_idx]
        X_te = X.iloc[test_idx]
        y_tr = y[train_idx]
        y_te = y[test_idx]
        
        if len(np.unique(y_tr)) < 2:
            continue
        
        model = xgb.XGBClassifier(
            n_estimators=500, max_depth=2, learning_rate=0.02,
            subsample=0.6, colsample_bytree=0.6, colsample_bylevel=0.7,
            reg_alpha=5.0, reg_lambda=10.0, min_child_weight=20, gamma=0.5,
            objective="binary:logistic", eval_metric="logloss",
            random_state=42, verbosity=0,
        )
        sw = compute_sample_weight("balanced", y_tr)
        model.fit(X_tr, y_tr, sample_weight=sw)
        
        try:
            proba = model.predict_proba(X_te)[:, 1]
        except:
            proba = model.predict_proba(X_te.values)[:, 1]
        
        oof_pred[test_idx] = proba
    
    elapsed = time.time() - total_time
    oof_class = (oof_pred >= 0.5).astype(int)
    
    oof_auc = roc_auc_score(y, oof_pred)
    oof_acc = accuracy_score(y, oof_class)
    oof_f1 = f1_score(y, oof_class, zero_division=0)
    oof_prec = precision_score(y, oof_class, zero_division=0)
    try:
        oof_ic = float(stats.spearmanr(oof_pred, y)[0])
    except:
        oof_ic = 0.0
    
    # Strategy simulation
    strategies = {}
    for t in [0.55, 0.60, 0.65]:
        mask = oof_pred >= t
        n = mask.sum()
        if n > 10:
            wr = y[mask].mean()
            returns = y[mask].astype(float) * 2 - 1
            sharpe = returns.mean() / (returns.std() + 1e-9)
            strategies[f"t{int(t*100)}"] = {
                "winrate": round(wr, 4),
                "trades": int(n),
                "sharpe": round(sharpe, 3),
            }
    
    result = {
        "name": name,
        "oof_auc": round(oof_auc, 4),
        "oof_accuracy": round(oof_acc, 4),
        "oof_f1": round(oof_f1, 4),
        "oof_precision": round(oof_prec, 4),
        "oof_ic": round(oof_ic, 4),
        "train_time": round(elapsed, 1),
        "n_samples": len(y),
        "n_features": X.shape[1],
        "strategies": strategies,
    }
    
    return result


def main():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{'='*60}")
    print(f"  🧪 Post-Label-Fix Experiments started {ts}")
    print(f"{'='*60}")
    
    all_results = []
    
    # ─── Experiment 1: Baseline (ALL regimes, full features) ───
    print(f"\n{'─'*40} Exp 1: Baseline (ALL regimes) {'─'*40}")
    X, y, meta = load_data()
    if X is not None:
        r = evaluate(X, y, "Baseline (ALL)")
        all_results.append(r)
        print(f"  AUC={r['oof_auc']:.4f} | Acc={r['oof_accuracy']:.4f} | F1={r['oof_f1']:.4f} | IC={r['oof_ic']:+.4f}")
        for k, v in r["strategies"].items():
            print(f"    Strategy {k}: WinRate={v['winrate']*100:.1f}% | Trades={v['trades']} | Sharpe={v['sharpe']:.3f}")
    
    # ─── Experiment 2: Bear + Bull only (exclude Chop) ───
    print(f"\n{'─'*40} Exp 2: Bear + Bull (exclude Chop) {'─'*40}")
    X, y, meta = load_data(include_regimes=["bear", "bull"])
    if X is not None:
        r = evaluate(X, y, "Bear+Bull (no Chop)")
        all_results.append(r)
        print(f"  AUC={r['oof_auc']:.4f} | Acc={r['oof_accuracy']:.4f} | F1={r['oof_f1']:.4f}")
        for k, v in r["strategies"].items():
            print(f"    Strategy {k}: WinRate={v['winrate']*100:.1f}% | Trades={v['trades']} | Sharpe={v['sharpe']:.3f}")
    
    # ─── Experiment 3: Bear only ───
    print(f"\n{'─'*40} Exp 3: Bear only ──{'─'*40}")
    X, y, meta = load_data(include_regimes=["bear"])
    if X is not None:
        r = evaluate(X, y, "Bear only")
        all_results.append(r)
        print(f"  AUC={r['oof_auc']:.4f} | Acc={r['oof_accuracy']:.4f} | F1={r['oof_f1']:.4f}")
        for k, v in r["strategies"].items():
            print(f"    Strategy {k}: WinRate={v['winrate']*100:.1f}% | Trades={v['trades']} | Sharpe={v['sharpe']:.3f}")
    
    # ─── Experiment 4: Feature Pruning (|IC| > 0.03) ───
    print(f"\n{'─'*40} Exp 4: Feature Pruning (|IC| > 0.03) {'─'*40}")
    X, y, meta = load_data(drop_low_ic=0.03)
    if X is not None:
        r = evaluate(X, y, "Pruned |IC|>0.03")
        all_results.append(r)
        print(f"  AUC={r['oof_auc']:.4f} | Acc={r['oof_accuracy']:.4f} | F1={r['oof_f1']:.4f}")
        for k, v in r["strategies"].items():
            print(f"    Strategy {k}: WinRate={v['winrate']*100:.1f}% | Trades={v['trades']} | Sharpe={v['sharpe']:.3f}")
    
    # ─── Experiment 5: Bear+Bull + Feature Pruning ───
    print(f"\n{'─'*40} Exp 5: Bear+Bull + Pruned (|IC|>0.03) {'─'*40}")
    X, y, meta = load_data(include_regimes=["bear", "bull"], drop_low_ic=0.03)
    if X is not None:
        r = evaluate(X, y, "Bear+Bull + Pruned")
        all_results.append(r)
        print(f"  AUC={r['oof_auc']:.4f} | Acc={r['oof_accuracy']:.4f} | F1={r['oof_f1']:.4f}")
        for k, v in r["strategies"].items():
            print(f"    Strategy {k}: WinRate={v['winrate']*100:.1f}% | Trades={v['trades']} | Sharpe={v['sharpe']:.3f}")
    
    # ─── Experiment 6: Per-regime models ───
    print(f"\n{'─'*40} Exp 6: Per-Regime Models (3 separate) {'─'*40}")
    per_regime_results = {}
    for regime in ["bear", "bull", "chop"]:
        X, y, meta = load_data(include_regimes=[regime])
        if X is not None and len(y) > 200:
            r = evaluate(X, y, f"{regime} only", n_splits=3)
            per_regime_results[regime] = r
            all_results.append(r)
            print(f"  {regime}:  n={len(y)}, AUC={r['oof_auc']:.4f} | Acc={r['oof_accuracy']:.4f}")
    
    # ─── Summary Table ───
    print(f"\n{'='*60}")
    print(f"  📊 總結比較表")
    print(f"{'='*60}")
    
    all_results.sort(key=lambda x: x["oof_auc"], reverse=True)
    
    header = f"{'實驗':<30} {'AUC':<8} {'Acc':<8} {'F1':<8} {'IC':<8} {'N':<7} {'t60 Win%':<10}"
    print(header)
    print("-" * 80)
    
    baseline_auc = all_results[0]["oof_auc"]  # First is highest AUC
    for r in all_results:
        t60 = r.get("strategies", {}).get("t60", {})
        wr = f"{t60.get('winrate', 0)*100:.1f}%" if t60.get("trades", 0) > 0 else "N/A"
        print(f"{r['name']:<30} {r['oof_auc']:.4f}   {r['oof_accuracy']:.4f}   {r['oof_f1']:.4f}   {r['oof_ic']:+.4f}   {r['n_samples']:<6} {wr}")
    
    # Best result
    best = all_results[0]
    print(f"\n🏆 Winner: {best['name']} — AUC={best['oof_auc']:.4f}")
    
    # Was this significantly better than the old baseline?
    old_auc = 0.502  # From previous benchmark
    improvement = best["oof_auc"] - old_auc
    if improvement > 0.01:
        print(f"✅ SIGNIFICANT improvement (+{improvement*100:.1f}pp vs old baseline {old_auc})")
    elif improvement > 0:
        print(f"⚠️  Marginal improvement (+{improvement*100:.1f}pp)")
    else:
        print(f"❌ No improvement ({improvement*100:.1f}pp)")
    
    # Save results
    os.makedirs("data", exist_ok=True)
    path = f"data/label_fix_experiment_{ts.replace(' ', '_').replace(':', '-')}.json"
    with open(path, "w") as f:
        json.dump({"timestamp": ts, "note": "After label flip fix", "results": all_results}, f, indent=2)
    print(f"\n💾 Results: {path}")


if __name__ == "__main__":
    main()
