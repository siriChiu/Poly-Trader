"""
Debug: Why is XGBoost not learning anything?
"""
import numpy as np, sys, ccxt
sys.path.insert(0, '/home/kazuha/Poly-Trader')
from feature_engine.ohlcv_4h import compute_4h_indicators
from datetime import datetime

import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit

exchange = ccxt.binance({"enableRateLimit": True})
ohlcv = exchange.fetch_ohlcv("BTC/USDT", "4h", limit=1000)

candles = {
    "timestamps": np.array([o[0] for o in ohlcv]),
    "opens": np.array([o[1] for o in ohlcv]),
    "highs": np.array([o[2] for o in ohlcv]),
    "lows": np.array([o[3] for o in ohlcv]),
    "closes": np.array([o[4] for o in ohlcv]),
    "volumes": np.array([o[5] for o in ohlcv]),
}

n = len(candles["closes"])
ind = compute_4h_indicators(candles)

FEATURE_COLS = [
    "4h_bias50", "4h_bias20", "4h_bias200",
    "4h_rsi14", "4h_macd_hist", "4h_bb_pct_b",
    "4h_dist_bb_lower", "4h_dist_swing_low",
    "4h_ma_order", "4h_vol_ratio",
]

horizon = 6
min_idx = 200

import pandas as pd
X_list = []
y_return = []

for i in range(min_idx, n - horizon):
    features = {}
    for col in FEATURE_COLS:
        val = ind.get(col, [0]*n)[i]
        if not np.isfinite(val):
            val = 0.0
        features[col] = float(val)
    ret = (candles["closes"][i + horizon] - candles["closes"][i]) / candles["closes"][i]
    X_list.append(features)
    y_return.append(ret)

X = pd.DataFrame(X_list)
y = np.array(y_return)

print(f"Dataset: {X.shape}")
print(f"Target: mean={y.mean():.5f}, std={y.std():.5f}")
print(f"X column stats:")
for col in X.columns:
    v = X[col].values
    print(f"  {col:25s}: mean={v.mean():.4f}, std={v.std():.4f}, range=[{v.min():.2f}, {v.max():.2f}]")

# Test 1: Simple linear regression
from sklearn.linear_model import Ridge
lr = Ridge(alpha=1.0)
lr.fit(X, y)
print(f"\nRidge regression:")
for c, coef in zip(X.columns, lr.coef_):
    sign = "+" if coef >= 0 else ""
    print(f"  {c:25s}: {sign}{coef:.6f}")
preds = lr.predict(X)
r2_train = 1 - np.sum((y - preds)**2) / np.sum((y - y.mean())**2)
print(f"  Train R²: {r2_train:.4f}")

# Test 2: XGBoost with minimal regularization
for depth in [2, 3, 5]:
    for reg_a in [0.0, 0.1, 1.0]:
        m = xgb.XGBRegressor(
            n_estimators=100, max_depth=depth, learning_rate=0.1,
            reg_alpha=reg_a, reg_lambda=1.0,
            min_child_weight=1, subsample=0.8,
            random_state=42, verbosity=0
        )
        m.fit(X, y)
        preds = m.predict(X)
        r2 = 1 - np.sum((y - preds)**2) / np.sum((y - y.mean())**2)
        imp = m.feature_importances_
        feat_used = sum(1 for v in imp if v > 0)
        if feat_used > 0:
            print(f"\nXGB depth={depth} alpha={reg_a}: Train R²={r2:.4f}, features_used={feat_used}")
            top = sorted(zip(X.columns, imp), key=lambda x: -x[1])[:5]
            for nm, v in top:
                print(f"  {nm}: {v:.4f}")

# Test 3: TimeSeriesSplit with minimal model
print("\n" + "="*60)
print("TimeSeriesSplit CV (5 folds)")
print("="*60)
tscv = TimeSeriesSplit(n_splits=5)
for fold, (tr_idx, te_idx) in enumerate(tscv.split(X)):
    m = xgb.XGBRegressor(
        n_estimators=50, max_depth=2, learning_rate=0.1,
        reg_alpha=0.0, reg_lambda=1.0,
        min_child_weight=1, random_state=42, verbosity=0
    )
    m.fit(X.iloc[tr_idx], y[tr_idx])
    preds = m.predict(X.iloc[te_idx])
    actuals = y[te_idx]
    ss_res = np.sum((actuals - preds)**2)
    ss_tot = np.sum((actuals - actuals.mean())**2)
    r2 = 1 - ss_res/ss_tot if ss_tot > 0 else 0
    sell_mask = preds < 0
    if sell_mask.sum() > 0:
        actual_sel = actuals[sell_mask]
        wr = (actual_sel < 0).sum() / len(actual_sel)
    else:
        wr = 0
    print(f"  Fold {fold}: n_test={len(te_idx)}, R²={r2:.4f}, "
          f"sell_trades={sell_mask.sum()}, sell_wr={wr:.1%}")
