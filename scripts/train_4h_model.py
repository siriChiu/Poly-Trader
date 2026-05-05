"""
純 4H 訓練流程: 用 OKX 歷史 4H 數據訓練模型並回測
========================================================
1. 從 OKX 抓 4H OHLCV (1000 根 = ~166 天)
2. 計算 4H 技術指標
3. 生成標籤 (未來 N 根 4H candle 的收益率)
4. 訓練 XGBoost (rolling window CV)
5. 回測驗證
"""
import numpy as np
import sys, ccxt
sys.path.insert(0, '/home/kazuha/Poly-Trader')
from feature_engine.ohlcv_4h import compute_4h_indicators
from datetime import datetime
from scipy import stats

import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.utils.class_weight import compute_sample_weight

print("=" * 70)
print("Pure 4H Model Training & Backtest")
print("=" * 70)

# Fetch data
exchange = ccxt.okx({"enableRateLimit": True})
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
print(f"Loaded {n} 4H candles")
print(f"Date range: {datetime.fromtimestamp(candles['timestamps'][0]/1000).isoformat()} → {datetime.fromtimestamp(candles['timestamps'][-1]/1000).isoformat()}")
print(f"Price: ${candles['closes'][0]:,.0f} → ${candles['closes'][-1]:,.0f}")

# Compute indicators
print("\nComputing 4H indicators...")
ind = compute_4h_indicators(candles)

# Feature columns (all 4H indicators)
FEATURE_COLS_4H = [
    "4h_bias50", "4h_bias20", "4h_bias200",
    "4h_rsi14", "4h_macd_hist", "4h_bb_pct_b",
    "4h_dist_bb_lower", "4h_dist_swing_low",
    "4h_ma_order", "4h_vol_ratio",
]

# Build feature matrix
X_list = []
y_return_list = []
y_label_list = []

# Use horizon = 6 candles (24H) for labeling
horizon = 6
min_idx = 200  # need 200 candles for MA200

for i in range(min_idx, n - horizon):
    features = {}
    valid = True
    for col in FEATURE_COLS_4H:
        val = ind.get(col, [0]*n)[i]
        if val is None or (isinstance(val, float) and not np.isfinite(val)):
            val = 0.0
        features[col] = float(val)
    
    # Future return
    entry = candles["closes"][i]
    exit_p = candles["closes"][i + horizon]
    ret = (exit_p - entry) / entry
    
    X_list.append(features)
    y_return_list.append(ret)
    # label_spot_long_win: 1 if price drops (short profitable)
    y_label_list.append(1 if ret < -0.001 else 0)  # 0.1% threshold

X = __import__('pandas').DataFrame(X_list)
y_return = np.array(y_return_list)
y_label = np.array(y_label_list)

print(f"\nDataset: {len(X)} samples, {X.shape[1]} features")
print(f"Return stats: mean={y_return.mean():.5f}, std={y_return.std():.5f}")
print(f"Label (sell_win) distribution: {y_label.sum()}/{len(y_label)} ({y_label.mean():.1%})")

# Feature correlations with return
print("\nFeature correlations with future return:")
for col in FEATURE_COLS_4H:
    corr = np.corrcoef(X[col].values, y_return)[0, 1]
    status = "✅" if abs(corr) > 0.05 else "❌"
    print(f"  {col:25s}: {corr:+.4f} {status}")

# ── Train XGBoost Regressor ──
print("\n" + "=" * 70)
print("Training XGBoost Regressor (predict future return)")
print("=" * 70)

model = xgb.XGBRegressor(
    n_estimators=200,
    max_depth=3,
    learning_rate=0.05,
    subsample=0.7,
    colsample_bytree=0.7,
    reg_alpha=2.0,
    reg_lambda=5.0,
    min_child_weight=10,
    random_state=42,
)
model.fit(X, y_return)

# Feature importance
print("\nFeature importance:")
for col, imp in sorted(zip(FEATURE_COLS_4H, model.feature_importances_), key=lambda x: -x[1]):
    print(f"  {col:25s}: {imp:.4f}")

# ── Rolling Window CV ──
print("\n" + "=" * 70)
print("Rolling Window CV")
print("=" * 70)

n_samples = len(X)
train_frac = 0.7
test_frac = 0.1
step_frac = 0.05

train_base = int(n_samples * train_frac)
test_size = max(int(n_samples * test_frac), 30)
step = max(int(n_samples * step_frac), 10)

reg_scores = []  # R²
mae_scores = []

start = train_base
fold = 0
while start + test_size <= n_samples:
    train_idx = list(range(0, start))
    test_idx = list(range(start, start + test_size))
    
    m = xgb.XGBRegressor(
        n_estimators=200, max_depth=3, learning_rate=0.05,
        subsample=0.7, colsample_bytree=0.7,
        reg_alpha=2.0, reg_lambda=5.0, min_child_weight=10,
        random_state=42,
    )
    m.fit(X.iloc[train_idx], y_return[train_idx])
    preds = m.predict(X.iloc[test_idx])
    actuals = y_return[test_idx]
    
    # R²
    ss_res = np.sum((actuals - preds) ** 2)
    ss_tot = np.sum((actuals - actuals.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    
    # MAE
    mae = np.mean(np.abs(actuals - preds))
    
    reg_scores.append(r2)
    mae_scores.append(mae)
    fold += 1
    start += step

print(f"R²: {np.mean(reg_scores):.4f} (range: {np.min(reg_scores):.4f} ~ {np.max(reg_scores):.4f})")
print(f"MAE: {np.mean(mae_scores):.5f}")

# ── Backtest using model predictions ──
# Use predictions to generate sell signals
print("\n" + "=" * 70)
print(f"Backtest: Sell when predicted return < threshold")
print(f"Horizon: {horizon * 4}H ({horizon} candles)")
print("=" * 70)

full_preds = model.predict(X)

for threshold in [-0.001, -0.003, -0.005, -0.008, -0.01]:
    sell_mask = full_preds < threshold
    n_trades = sell_mask.sum()
    if n_trades == 0:
        continue
    
    actual_returns = y_return[sell_mask]
    wins = (actual_returns < 0).sum()
    win_rate = wins / n_trades
    
    print(f"\n  Threshold < {threshold*100:.2f}%: {n_trades} trades")
    print(f"    Win rate: {win_rate:.1%} ({wins}/{n_trades})")
    print(f"    Avg return: {actual_returns.mean():.5f}")
    print(f"    Median return: {np.median(actual_returns):.5f}")
    print(f"    P&L (sum): {actual_returns.sum():.4f}")

# Compare to random
all_wins = (y_return < 0).sum()
print(f"\n  Baseline (all short): {len(y_return)} trades, win={all_wins/len(y_return):.1%}")
