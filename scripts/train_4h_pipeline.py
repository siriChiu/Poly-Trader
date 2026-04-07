"""
4H 管道式訓練系統 — 完整的特徵計算 + 標籤生成 + 模型訓練 + 回測
================================================================
用法:
  cd /home/kazuha/Poly-Trader && source venv/bin/activate
  python scripts/train_4h_pipeline.py             # 從 Binance 訓練
  python scripts/train_4h_pipeline.py --backtest   # 只做回測
"""
import numpy as np
import sys, ccxt, json, os
sys.path.insert(0, '/home/kazuha/Poly-Trader')
from feature_engine.ohlcv_4h import compute_4h_indicators
from datetime import datetime

import xgboost as xgb
from sklearn.utils.class_weight import compute_sample_weight

# ===== 參數 =====
HORIZON_HOURS = [4, 8, 12, 24]   # 測試多個出場 horizon
BIAS_LOWER = 0.5   # bias50 下限 (%)
BIAS_UPPER = 5.0   # bias50 上限 (%)
FEATURES_4H = [
    "4h_bias50", "4h_bias20", "4h_bias200",
    "4h_rsi14", "4h_macd_hist", "4h_bb_pct_b",
    "4h_dist_bb_lower", "4h_dist_swing_low",
    "4h_ma_order",
]

def gv(ind, name, i, n, default=0):
    """Safe indicator value getter."""
    arr = ind.get(name, [default] * n)
    if i < 0 or i >= len(arr):
        return float(default)
    v = arr[i]
    return float(v) if isinstance(v, (int, float)) and np.isfinite(v) else float(default)


def main():
    print("=" * 70)
    print("4H Pipeline — Support Line + Bias Strategy Model")
    print("=" * 70)
    
    # ── Step 1: Fetch 4H data ──
    print("\n[1/5] Fetching 4H OHLCV from Binance...")
    exchange = ccxt.binance({"enableRateLimit": True})
    all_ohlcv = []
    for _ in range(5):
        if not all_ohlcv:
            ohlcv = exchange.fetch_ohlcv("BTC/USDT", "4h", limit=1000)
        else:
            oldest = all_ohlcv[0][0]
            ohlcv = exchange.fetch_ohlcv("BTC/USDT", "4h", limit=1000,
                                         params={"until": oldest})
        if not ohlcv or len(ohlcv) < 2:
            break
        merged = all_ohlcv + ohlcv
        seen = set()
        all_ohlcv = [c for c in merged if not (c[0] in seen or seen.add(c[0]))]
        all_ohlcv.sort(key=lambda x: x[0])
        print(f"  {len(all_ohlcv)} candles")
        if len(ohlcv) < 500:
            break
    
    candles = {
        "timestamps": np.array([o[0] for o in all_ohlcv]),
        "opens": np.array([o[1] for o in all_ohlcv]),
        "highs": np.array([o[2] for o in all_ohlcv]),
        "lows": np.array([o[3] for o in all_ohlcv]),
        "closes": np.array([o[4] for o in all_ohlcv]),
        "volumes": np.array([o[5] for o in all_ohlcv]),
    }
    n = len(candles["closes"])
    print(f"\n  Range: {datetime.fromtimestamp(candles['timestamps'][0]/1000).date()} → "
          f"{datetime.fromtimestamp(candles['timestamps'][-1]/1000).date()}")
    print(f"  Price: ${candles['closes'][0]:,.0f} → ${candles['closes'][-1]:,.0f}")
    
    # ── Step 2: Compute 4H indicators ──
    print("\n[2/5] Computing 4H indicators...")
    ind = compute_4h_indicators(candles)
    
    # ── Step 3: Build training data ──
    print("\n[3/5] Building training data (short setup at support)...")
    
    X_list = []
    y_multi = {}  # horizon -> y_list
    metadata = []
    
    min_idx = 200  # need MA200
    horizons = {1: 4, 2: 8, 3: 12, 6: 24}  # candles -> hours
    
    for i in range(min_idx, n - max(horizons.keys())):
        # === 做空信號條件 ===
        bias50 = gv(ind, '4h_bias50', i, n)
        bias20 = gv(ind, '4h_bias20', i, n)
        macd_h = gv(ind, '4h_macd_hist', i, n)
        rsi_14 = gv(ind, '4h_rsi14', i, n)
        bb_pct = gv(ind, '4h_bb_pct_b', i, n)
        
        # 只做 "反彈到支撐附近受阻" 的做空:
        # bias50 在 0~2% = 價格剛好在 MA50 附近或稍上方
        # macd_hist < 0 = 動能轉弱
        # rsi < 55 = 不過熱
        is_setup = (BIAS_LOWER <= bias50 <= BIAS_UPPER and
                    macd_h < 0 and rsi_14 < 55)
        
        if not is_setup:
            continue
        
        entry = candles["closes"][i]
        
        # Features
        features = {}
        for col in FEATURES_4H:
            features[col] = gv(ind, col, i, n)
        X_list.append(features)
        
        # Labels for each horizon
        for ncandles, hours in horizons.items():
            exit_idx = i + ncandles
            if exit_idx >= n:
                continue
            exit_p = candles["closes"][exit_idx]
            ret = (exit_p - entry) / entry
            y_multi.setdefault(ncandles, []).append(ret)
        
        metadata.append({
            "ts": int(candles["timestamps"][i]),
            "entry": float(entry),
            "bias50": round(bias50, 2),
            "macd": round(macd_h, 1),
            "rsi": round(rsi_14, 1),
        })
    
    print(f"  Setup signals found: {len(X_list)}")
    print(f"  Feature columns: {len(FEATURES_4H)}")
    
    if not X_list:
        print("  No signals found! Exiting.")
        return
    
    # ── Step 4: Train and backtest ──
    print("\n[4/5] Training XGBoost + Rolling CV...")
    
    import pandas as pd
    X = pd.DataFrame(X_list)
    
    # Train final model on all data
    model = xgb.XGBRegressor(
        n_estimators=200, max_depth=3, learning_rate=0.05,
        subsample=0.7, colsample_bytree=0.7,
        reg_alpha=0.5, reg_lambda=3.0, min_child_weight=5,
        random_state=42,
    )
    model.fit(X, y_multi[6])  # 24H horizon for training
    
    # Feature importance
    print("\n  Feature importance:")
    for col, imp in sorted(zip(FEATURES_4H, model.feature_importances_),
                           key=lambda x: -x[1]):
        print(f"    {col:25s}: {imp:.4f}")
    
    # Rolling CV
    n_samples = len(X)
    cv_scores_r2 = []
    cv_scores_wr = {}
    for ncandles in horizons:
        cv_scores_wr[ncandles] = []
    
    train_frac = 0.6
    test_frac = 0.15
    step_frac = 0.05
    train_base = int(n_samples * train_frac)
    test_size = max(int(n_samples * test_frac), 30)
    step = max(int(n_samples * step_frac), 5)
    
    start = train_base
    fold = 0
    while start + test_size <= n_samples:
        tr_idx = list(range(0, start))
        te_idx = list(range(start, start + test_size))
        
        for ncandles in horizons:
            if ncandles not in y_multi or len(y_multi[ncandles]) <= start + test_size:
                continue
            y_arr = np.array(y_multi[ncandles])
            m = xgb.XGBRegressor(
                n_estimators=200, max_depth=3, learning_rate=0.05,
                subsample=0.7, colsample_bytree=0.7,
                reg_alpha=0.5, reg_lambda=3.0, min_child_weight=5,
                random_state=42,
            )
            m.fit(X.iloc[tr_idx], y_arr[tr_idx])
            preds = m.predict(X.iloc[te_idx])
            actuals = y_arr[te_idx]
            
            # Win rate: sell when predicted < 0
            sell_mask = preds < 0
            if sell_mask.sum() > 5:
                actual_sell = actuals[sell_mask]
                wr = (actual_sell < 0).sum() / len(actual_sell)
                cv_scores_wr[ncandles].append((wr, int(sell_mask.sum())))
            
            # R²
            ss_res = np.sum((actuals - preds) ** 2)
            ss_tot = np.sum((actuals - actuals.mean()) ** 2)
            cv_scores_r2.append(1 - ss_res / ss_tot if ss_tot > 0 else 0)
        
        fold += 1
        start += step
    
    # ── Step 5: Report ──
    print(f"\n[5/5] Results ({n_samples} setup signals)")
    print("=" * 70)
    
    print(f"\n  Rolling CV R²: {np.mean(cv_scores_r2):.4f} (range: "
          f"{np.min(cv_scores_r2):.4f} ~ {np.max(cv_scores_r2):.4f})")
    
    for ncandles, hours in sorted(horizons.items()):
        if ncandles in cv_scores_wr and cv_scores_wr[ncandles]:
            score_list = cv_scores_wr[ncandles]
            avg_wr = np.mean([s[0] for s in score_list])
            total_trades = sum(s[1] for s in score_list)
            print(f"\n  Horizon {hours}H ({ncandles} candles):")
            print(f"    Folds: {len(score_list)}")
            print(f"    Mean fold WR: {avg_wr:.1%}")
            print(f"    Total trades across folds: {total_trades}")
    
    # Full data backtest
    print(f"\n{'─' * 70}")
    print(f"Full data backtest (all {n_samples} signals):")
    print(f"{'─' * 70}")
    
    preds_full = model.predict(X)
    
    for ncandles, hours in sorted(horizons.items()):
        y_arr = np.array(y_multi[ncandles])[:len(preds_full)]
        sell_mask = preds_full < 0
        total = sell_mask.sum()
        if total < 5:
            continue
        actual_sell = y_arr[sell_mask]
        wins = (actual_sell < 0).sum()
        wr = wins / total
        print(f"\n  {hours}H horizon (sell when predicted<0):")
        print(f"    Trades: {total}")
        print(f"    Win rate: {wr:.1%} ({wins}/{total})")
        print(f"    Avg return: {actual_sell.mean():.5f}")
        print(f"    P&L (sum): {actual_sell.sum():.4f}")
    
    # Baseline
    baseline_wr = np.mean([
        np.mean((np.array(y_multi[ncandles]) < 0).astype(float))
        for ncandles in horizons
        if ncandles in y_multi
    ])
    print(f"\n  Baseline (sell on ALL setups): WR={baseline_wr:.1%}")
    
    # Save model
    model_dir = '/home/kazuha/Poly-Trader/model_4h'
    os.makedirs(model_dir, exist_ok=True)
    import pickle
    with open(os.path.join(model_dir, 'xgb_4h.pkl'), 'wb') as f:
        pickle.dump({
            'model': model,
            'features': FEATURES_4H,
            'params': {'bias_lower': BIAS_LOWER, 'bias_upper': BIAS_UPPER},
        }, f)
    print(f"\n  Model saved to {model_dir}/xgb_4h.pkl")


if __name__ == "__main__":
    main()
