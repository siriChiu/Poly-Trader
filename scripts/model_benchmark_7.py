#!/usr/bin/env python3
"""🧪 Model Benchmark — 7 模型六色帽比較

公平比較 7 個二分類器在同一訓練集上的表現：
1. XGBoost (baseline)
2. LightGBM
3. CatBoost
4. Logistic Regression
5. Random Forest
6. Gradient Boosting (sklearn)
7. HistGradientBoosting (sklearn)

評估指標:
- CV Accuracy (TimeSeriesSplit, 5-fold)
- CV AUC (TimeSeriesSplit)
- Sell-Win Rate (預測 sell-win=1 且實際也為 1 的比例)
- Correlation IC (預測概率 vs 真實 label 的 Spearman IC)
- Sharpe-like score (勝率 - 敗率) / 波動
- 訓練時間

用法: python scripts/model_benchmark_7.py
"""
import os, sys, json, time, traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List

import numpy as np
import pandas as pd
from scipy import stats

PROJECT = "/home/kazuha/Poly-Trader"
sys.path.insert(0, PROJECT)
os.chdir(PROJECT)

DB_PATH = os.path.join(PROJECT, "poly_trader.db")

# ─── Models ───
from sklearn.model_selection import TimeSeriesSplit, cross_val_score, cross_val_predict
from sklearn.metrics import accuracy_score, roc_auc_score, precision_score, recall_score, f1_score, brier_score_loss
from sklearn.utils.class_weight import compute_sample_weight

MODEL_REGISTRY: Dict[str, dict] = {}

def register_model(name: str, model_fn, params: dict, category: str):
    MODEL_REGISTRY[name] = {"fn": model_fn, "params": params, "category": category}

# 1. XGBoost (baseline)
try:
    import xgboost as xgb
    register_model("XGBoost", xgb.XGBClassifier, {
        "n_estimators": 500, "max_depth": 2, "learning_rate": 0.02,
        "subsample": 0.6, "colsample_bytree": 0.6, "colsample_bylevel": 0.7,
        "reg_alpha": 5.0, "reg_lambda": 10.0, "min_child_weight": 20,
        "gamma": 0.5, "objective": "binary:logistic", "eval_metric": "logloss",
        "random_state": 42, "verbosity": 0,
    }, "Gradient Boosting")
except ImportError:
    print("❌ XGBoost not available")

# 2. LightGBM
try:
    import lightgbm as lgb
    register_model("LightGBM", lgb.LGBMClassifier, {
        "n_estimators": 500, "max_depth": 2, "learning_rate": 0.02,
        "subsample": 0.6, "colsample_bytree": 0.6,
        "reg_alpha": 5.0, "reg_lambda": 10.0, "min_child_weight": 20,
        "random_state": 42, "verbosity": -1,
    }, "Gradient Boosting")
except ImportError:
    print("❌ LightGBM not available")

# 3. CatBoost
try:
    import catboost as cb
    register_model("CatBoost", cb.CatBoostClassifier, {
        "iterations": 500, "depth": 2, "learning_rate": 0.02,
        "l2_leaf_reg": 10.0, "subsample": 0.6,
        "min_data_in_leaf": 20, "random_seed": 42,
        "logging_level": "Silent", "loss_function": "Logloss",
    }, "Gradient Boosting")
except ImportError:
    print("❌ CatBoost not available")

# 4. Logistic Regression
from sklearn.linear_model import LogisticRegression
register_model("Logistic Regression", LogisticRegression, {
    "C": 0.1, "max_iter": 1000, "penalty": "l2", "solver": "lbfgs",
    "random_state": 42, "class_weight": "balanced",
}, "Linear")

# 5. Random Forest
from sklearn.ensemble import RandomForestClassifier
register_model("Random Forest", RandomForestClassifier, {
    "n_estimators": 500, "max_depth": 3,
    "min_samples_leaf": 20, "min_samples_split": 10,
    "random_state": 42, "class_weight": "balanced", "n_jobs": -1,
}, "Ensemble")

# 6. Gradient Boosting (sklearn)
from sklearn.ensemble import GradientBoostingClassifier
register_model("Gradient Boosting", GradientBoostingClassifier, {
    "n_estimators": 200, "max_depth": 2, "learning_rate": 0.02,
    "subsample": 0.6, "min_samples_leaf": 20,
    "random_state": 42,
}, "Gradient Boosting")

# 7. HistGradientBoosting (sklearn — fastest)
from sklearn.ensemble import HistGradientBoostingClassifier
register_model("HistGradientBoosting", HistGradientBoostingClassifier, {
    "max_iter": 500, "max_depth": 2, "learning_rate": 0.02,
    "l2_regularization": 10.0, "min_samples_leaf": 20,
    "random_state": 42, "class_weight": "balanced",
}, "Gradient Boosting")

# ─── Data Loading ───
import sqlite3

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

def load_data():
    """Load features + labels from SQLite, merge on timestamp, return X, y, metadata."""
    conn = sqlite3.connect(DB_PATH)
    
    # Load features
    col_str = ", ".join([f"f.{c}" for c in FEATURE_COLS] + [
        "f.timestamp", "f.regime_label", "f.symbol"
    ])
    feat_query = f"SELECT {col_str} FROM features_normalized f ORDER BY f.timestamp"
    df = pd.read_sql_query(feat_query, conn)
    
    # Load labels
    label_query = """SELECT timestamp, label_sell_win, future_return_pct, regime_label 
                     FROM labels WHERE label_sell_win IS NOT NULL"""
    labels = pd.read_sql_query(label_query, conn)
    
    conn.close()
    
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="ISO8601")
    labels["timestamp"] = pd.to_datetime(labels["timestamp"], format="ISO8601")
    
    # Merge features with labels
    merged = pd.merge_asof(
        df.sort_values("timestamp"),
        labels[["timestamp", "label_sell_win", "future_return_pct", "regime_label"]].sort_values("timestamp"),
        on="timestamp",
        direction="nearest",
        tolerance=pd.Timedelta("10min"),
    )
    
    # Keep only matched pairs
    merged = merged.dropna(subset=["label_sell_win"]).copy()
    
    if len(merged) < 100:
        print(f"❌ Not enough matched samples: {len(merged)}")
        return None, None, None
    
    # Lag features
    LAG_STEPS = [12, 48, 144]
    all_cols = list(FEATURE_COLS)
    lag_cols = []
    for col in FEATURE_COLS:
        for lag in LAG_STEPS:
            lag_col = f"{col}_lag{lag}"
            merged[lag_col] = merged[col].shift(lag)
            lag_cols.append(lag_col)
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
    
    # Coerce to numeric and fillna
    for col in all_cols:
        merged[col] = pd.to_numeric(merged[col], errors='coerce')
    merged[all_cols] = merged[all_cols].fillna(0.0)
    
    # Invert negative-IC features
    neg_ic_cols = {"feat_nose", "feat_ear", "feat_mind", "feat_tongue", 
                   "feat_pulse", "feat_aura"}
    for col in all_cols:
        base = col.replace("_lag12", "").replace("_lag48", "").replace("_lag144", "")
        if base in neg_ic_cols:
            merged[col] = -merged[col]
    
    X = merged[all_cols].copy()
    y = merged["label_sell_win"].astype(int).values
    
    meta = merged[["timestamp", "regime_label_x", "regime_label_y", "future_return_pct"]].copy()
    
    print(f"📊 Data: {X.shape[0]} samples, {X.shape[1]} features")
    print(f"   Class distribution: sell_win=0: {(y==0).sum()}, sell_win=1: {(y==1).sum()}")
    print(f"   sell_win rate: {y.mean():.4f}")
    print(f"   Timestamp range: {meta['timestamp'].min()} → {meta['timestamp'].max()}")
    
    return X, y, meta


def evaluate_model(model, X: pd.DataFrame, y: np.ndarray, name: str, n_splits: int = 5) -> dict:
    """Evaluate a single model with TimeSeriesSplit, return comprehensive metrics."""
    print(f"\n{'='*60}")
    print(f"🧪 Evaluating: {name}")
    print(f"{'='*60}")
    
    t_start = time.time()
    
    tscv = TimeSeriesSplit(n_splits=n_splits)
    
    fold_metrics = []
    oof_pred = np.zeros(len(y))  # Out-of-fold predictions
    
    for fold_idx, (train_idx, test_idx) in enumerate(tscv.split(X)):
        X_tr, X_te = X.iloc[train_idx], X.iloc[test_idx]
        y_tr, y_te = y[train_idx], y[test_idx]
        
        if len(np.unique(y_tr)) < 2:
            continue
        
        # Calculate sample weights
        sample_weight = compute_sample_weight("balanced", y_tr)
        
        # Create fresh model instance
        m_params = model.get_params() if hasattr(model, 'get_params') else {}
        try:
            m = type(model)(**{k: v for k, v in m_params.items()})
        except TypeError:
            # Some models don't support get_params() → use direct copy
            import copy
            m = copy.deepcopy(model)
        
        # Train
        fold_train_start = time.time()
        try:
            m.fit(X_tr, y_tr, sample_weight=sample_weight)
        except TypeError:
            # CatBoost uses different parameter name
            try:
                m.fit(X_tr, y_tr)
            except:
                m.fit(X_tr.values, y_tr, sample_weight=sample_weight)
        fold_train_time = time.time() - fold_train_start
        
        # Predict
        try:
            pred_proba = m.predict_proba(X_te)[:, 1]
        except Exception:
            try:
                pred_proba = m.predict_proba(X_te.values)[:, 1]
            except:
                pred_proba = np.zeros(len(y_te))
        
        pred_class = (pred_proba >= 0.5).astype(int)
        oof_pred[test_idx] = pred_proba
        
        # Metrics
        acc = accuracy_score(y_te, pred_class)
        try:
            auc = roc_auc_score(y_te, pred_proba)
        except:
            auc = 0.5
        
        # Sell-Win Rate: for predictions with high confidence (sell signal)
        sell_signal_mask = pred_proba < 0.4  # High confidence = predict price down = sell
        if sell_signal_mask.sum() > 0:
            sw_rate = y_te[sell_signal_mask].mean()  # Lower = better for short
            # Invert: for short, we want actual price to go down
            # sell_win=1 means price went down (profitable short)
            sell_win_precision = pred_class[sell_signal_mask].mean() if pred_class[sell_signal_mask].sum() > 0 else 0
        else:
            sw_rate = -1
            sell_win_precision = -1
        
        # Overall sell_win rate (how well does the model predict sell_wins?)
        overall_sw = pred_class.mean()  # Predicted sell-win rate
        actual_sw = y_te.mean()
        
        # IC = Spearman correlation between predicted probability and actual label
        try:
            ic, _ = stats.spearmanr(pred_proba, y_te)
            if ic is None or not np.isfinite(ic):
                ic = 0
        except:
            ic = 0
        
        # For SHORT strategy: we predict sell when probability of price DOWN is high
        # sell_win=1 means price went DOWN
        # So a good model for SHORT has high accuracy in predicting sell_win
        # But actually: sell_win=1 is what we WANT for a short to profit
        # Model predicts P(sell_win=1) = high → means price will go down → good for short
        # sell_win_rate = P(actual=sell_win=1 | model predict sell_win=1)
        sell_precision = precision_score(y_te, pred_class, zero_division=0)
        sell_recall = recall_score(y_te, pred_class, zero_division=0)
        sell_f1 = f1_score(y_te, pred_class, zero_division=0)
        
        brier = brier_score_loss(y_te, pred_proba)
        
        fold_metrics.append({
            "fold": fold_idx,
            "accuracy": acc,
            "auc": auc,
            "ic": ic,
            "sell_precision": sell_precision,
            "sell_recall": sell_recall,
            "sell_f1": sell_f1,
            "brier": brier,
            "actual_sw_rate": actual_sw,
            "pred_sw_rate": overall_sw,
            "train_time": fold_train_time,
        })
        
        print(f"  Fold {fold_idx}: Acc={acc:.4f} | AUC={auc:.4f} | IC={ic:.4f} | "
              f"Precision={sell_precision:.4f} | Recall={sell_recall:.4f} | F1={sell_f1:.4f}")
    
    total_time = time.time() - t_start
    
    # Aggregate metrics
    agg = {}
    for key in ["accuracy", "auc", "ic", "sell_precision", "sell_recall", "sell_f1", "brier"]:
        vals = [m[key] for m in fold_metrics]
        agg[f"{key}_mean"] = float(np.mean(vals))
        agg[f"{key}_std"] = float(np.std(vals))
    
    # OOF metrics
    oof_class = (oof_pred >= 0.5).astype(int)
    try:
        agg["oof_auc"] = float(roc_auc_score(y, oof_pred))
    except:
        agg["oof_auc"] = 0.5
    agg["oof_accuracy"] = float(accuracy_score(y, oof_class))
    agg["oof_f1"] = float(f1_score(y, oof_class, zero_division=0))
    
    # OOF IC
    try:
        oof_ic, _ = stats.spearmanr(oof_pred, y)
        agg["oof_ic"] = float(oof_ic) if oof_ic is not None and np.isfinite(oof_ic) else 0.0
    except:
        agg["oof_ic"] = 0.0
    
    # Strategy simulation: if model predicts sell_win with high confidence, take a SHORT
    # For each prediction where P(sell_win=1) > threshold, simulate SHORT
    for threshold in [0.55, 0.60, 0.65, 0.70]:
        trade_mask = oof_pred >= threshold
        n_trades = trade_mask.sum()
        if n_trades > 10:
            # Among trades taken, what % were actually sell_wins (profitable shorts)?
            strategy_win_rate = y[trade_mask].mean()
            agg[f"strategy_t{int(threshold*100)}_winrate"] = float(strategy_win_rate)
            agg[f"strategy_t{int(threshold*100)}_ntrades"] = int(n_trades)
            
            # Sharpe-like: (win_rate - 0.5) / std
            returns = y[trade_mask].astype(float) * 2 - 1  # +1 for win, -1 for loss
            agg[f"strategy_t{int(threshold*100)}_sharpe"] = float(returns.mean() / (returns.std() + 1e-9))
        else:
            agg[f"strategy_t{int(threshold*100)}_winrate"] = 0.0
            agg[f"strategy_t{int(threshold*100)}_ntrades"] = 0
            agg[f"strategy_t{int(threshold*100)}_sharpe"] = 0.0
    
    agg["train_time_total"] = total_time
    agg["n_folds"] = len(fold_metrics)
    
    print(f"\n  ⏱️  Total: {total_time:.1f}s")
    print(f"  📈 OOF AUC: {agg['oof_auc']:.4f} | OOF Acc: {agg['oof_accuracy']:.4f} | OOF IC: {agg['oof_ic']:.4f}")
    
    for t in [55, 60, 65, 70]:
        wr = agg.get(f"strategy_t{t}_winrate", 0)
        nt = agg.get(f"strategy_t{t}_ntrades", 0)
        sh = agg.get(f"strategy_t{t}_sharpe", 0)
        if nt > 0:
            print(f"  🎯 Strategy t{t/100:.2f}: WinRate={wr*100:.1f}% | Trades={nt} | Sharpe={sh:.3f}")
    
    return agg


def six_hats_meeting(results: dict) -> str:
    """六色帽會議分析."""
    
    print(f"\n{'='*60}")
    print("🎩 六色帽會議：模型評審")
    print(f"{'='*60}")
    
    # Score each model on multiple dimensions
    scores = {}
    for name, metrics in results.items():
        score = 0
        reasoning = []
        
        # White Hat (Facts/Data)
        oof_auc = metrics.get("oof_auc", 0)
        oof_ic = metrics.get("oof_ic", 0)
        sell_prec = metrics.get("sell_precision_mean", 0)
        reasoning.append(f"⬜ OOF AUC={oof_auc:.4f}, IC={oof_ic:.4f}, Precision={sell_prec:.4f}")
        
        # Red Hat (Intuition/Feeling)
        # If close to random (50%), feel bad
        if oof_auc < 0.52:
            reasoning.append("🔴 感覺不可靠 — 接近隨機")
        elif oof_auc > 0.58:
            reasoning.append("🔴 感覺不錯 — 有一定預測力")
        
        # Black Hat (Risks/Caveats)
        auc_std = metrics.get("auc_std", 0)
        time_taken = metrics.get("train_time_total", 0)
        if auc_std > 0.05:
            reasoning.append(f"⚫ 風險: 高變異 (std={auc_std:.4f}), 穩定性差")
        if time_taken > 30:
            reasoning.append(f"⚫ 風險: 訓練慢 ({time_taken:.1f}s), 不適合 5-min heartbeat")
        
        # Yellow Hat (Benefits)
        strategy_wr = metrics.get("strategy_t60_winrate", 0)
        strategy_n = metrics.get("strategy_t60_ntrades", 0)
        if strategy_wr > 0.45:
            reasoning.append(f"🟡 優勢: t=0.60 策略勝率 {strategy_wr*100:.1f}%")
        if strategy_wr > 0.50:
            reasoning.append(f"🟡 優勢: t=0.60 超過 50%! 可獲利")
        
        # Green Hat (Creativity/Potential)
        category = MODEL_REGISTRY.get(name, {}).get("category", "Unknown")
        reasoning.append(f"🟢 {category} 類型 — {'可做 ensemble' if category == 'Linear' else '原生特徵選擇' if category == 'Ensemble' else '梯度提升主幹'}")
        
        # Blue Hat (Meta/Decision)
        # Composite score
        composite = (oof_auc * 0.3 + 
                    max(oof_ic, 0) * 2.0 + 
                    sell_prec * 0.2 + 
                    max(strategy_wr, 0) * 0.3 +
                    (-auc_std * 2.0) + 
                    max(0, 1.0 - time_taken/60) * 0.1)
        
        reasoning.append(f"🔵 Composite Score: {composite:.4f}")
        
        scores[name] = {"composite": composite, "reasoning": reasoning}
    
    # Ranking
    ranked = sorted(scores.items(), key=lambda x: x[1]["composite"], reverse=True)
    
    print("\n📊 最終排名:")
    print(f"{'排名':<4} {'模型':<25} {'Score':<10}")
    print("-" * 40)
    for rank, (name, info) in enumerate(ranked, 1):
        print(f"{rank:<4} {name:<25} {info['composite']:.4f}")
    
    print(f"\n📝 詳細分析:")
    for rank, (name, info) in enumerate(ranked, 1):
        print(f"\n  #{rank} {name}:")
        for r in info["reasoning"]:
            print(f"    {r}")
    
    # Recommendation
    top = ranked[0][0]
    print(f"\n🏆 推薦導入: {top}")
    
    return top


def main():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{'='*60}")
    print(f"  🧪 Model Benchmark — 7 模型比較 started {ts}")
    print(f"{'='*60}")
    
    # Load data
    print("\n📥 Loading data...")
    X, y, meta = load_data()
    if X is None:
        print("❌ Data loading failed")
        return
    
    # Evaluate all models
    results = {}
    for name, info in MODEL_REGISTRY.items():
        try:
            model = info["fn"](**info["params"])
            metrics = evaluate_model(model, X, y, name)
            results[name] = metrics
        except Exception as e:
            print(f"\n❌ {name} FAILED: {e}")
            traceback.print_exc()
            results[name] = {"error": str(e)}
    
    # Save results
    os.makedirs("data", exist_ok=True)
    result_path = f"data/benchmark_{ts.replace(' ', '_').replace(':', '-')}.json"
    with open(result_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n💾 Results saved to {result_path}")
    
    # Six Hat Meeting
    top_model = six_hats_meeting(results)
    
    # Print summary table
    print(f"\n{'='*60}")
    print("  📊 總結比較表")
    print(f"{'='*60}")
    
    header = f"{'模型':<25} {'OOF AUC':<9} {'OOF IC':<9} {'F1':<9} {'t=60 WR':<10} {'Time':<8}"
    print(header)
    print("-" * len(header))
    
    for name, metrics in sorted(results.items(), 
                                  key=lambda x: x[1].get("oof_auc", 0), 
                                  reverse=True):
        if "error" in metrics:
            print(f"{name:<25} {'ERROR':<9}")
            continue
        aur = metrics.get("oof_auc", 0)
        ic = metrics.get("oof_ic", 0)
        f1 = metrics.get("oof_f1", 0)
        wr = metrics.get("strategy_t60_winrate", 0)
        nt = metrics.get("strategy_t60_ntrades", 0)
        time_ = metrics.get("train_time_total", 0)
        print(f"{name:<25} {aur:.4f}    {ic:+.4f}   {f1:.4f}   {wr*100:.1f}%({nt}) {time_:.1f}s")
    
    # Check if Poly-Trader should adopt a new model
    current_xgb = results.get("XGBoost", {})
    if current_xgb and top_model != "XGBoost" and "error" not in current_xgb:
        current_auc = current_xgb.get("oof_auc", 0)
        new_auc = results.get(top_model, {}).get("oof_auc", 0)
        if new_auc > current_auc + 0.01:
            print(f"\n📢 {top_model} beats XGBoost by {new_auc - current_auc:.4f} AUC points")
            print(f"   Ready to import! ✅")
        else:
            print(f"\n⚠️  {top_model} only marginally better than XGBoost ({new_auc - current_auc:+.4f})")
            print(f"   May not justify switching — ensemble could help")


if __name__ == "__main__":
    main()
