"""
4H 即時預言 — 用最新 4H 指標預測接下來 4-24H 的走勢
==================================================
用法: cd /home/kazuha/Poly-Trader && source venv/bin/activate
      python scripts/predict_4h.py
"""
import numpy as np
import sys, ccxt, pickle, os
from datetime import datetime
sys.path.insert(0, '/home/kazuha/Poly-Trader')
from feature_engine.ohlcv_4h import compute_4h_indicators

FEATURES_4H = [
    "4h_bias50", "4h_bias20", "4h_bias200",
    "4h_rsi14", "4h_macd_hist", "4h_bb_pct_b",
    "4h_dist_bb_lower", "4h_dist_swing_low",
    "4h_ma_order",
]

def gv(ind, name, i, n, default=0):
    arr = ind.get(name, [default] * n)
    if i < 0 or i >= len(arr):
        return float(default)
    v = arr[i]
    return float(v) if isinstance(v, (int, float)) and np.isfinite(v) else float(default)

def main():
    print("=" * 60)
    print("4H 即時預測")
    print("=" * 60)
    
    # Fetch latest 4H data
    exchange = ccxt.binance({"enableRateLimit": True})
    ohlcv = exchange.fetch_ohlcv("BTC/USDT", "4h", limit=300)
    
    candles = {
        "timestamps": np.array([o[0] for o in ohlcv]),
        "opens": np.array([o[1] for o in ohlcv]),
        "highs": np.array([o[2] for o in ohlcv]),
        "lows": np.array([o[3] for o in ohlcv]),
        "closes": np.array([o[4] for o in ohlcv]),
        "volumes": np.array([o[5] for o in ohlcv]),
    }
    n = len(candles["closes"])
    current_price = candles["closes"][-1]
    
    # Compute indicators
    ind = compute_4h_indicators(candles)
    curr_ts = int(candles["timestamps"][-1])
    
    bias50 = gv(ind, '4h_bias50', n - 1, n)
    bias20 = gv(ind, '4h_bias20', n - 1, n)
    bias200 = gv(ind, '4h_bias200', n - 1, n)
    rsi = gv(ind, '4h_rsi14', n - 1, n)
    macd = gv(ind, '4h_macd_hist', n - 1, n)
    bb_pct = gv(ind, '4h_bb_pct_b', n - 1, n)
    dist_bb_lower = gv(ind, '4h_dist_bb_lower', n - 1, n)
    dist_sl = gv(ind, '4h_dist_swing_low', n - 1, n)
    ma_order = gv(ind, '4h_ma_order', n - 1, n)
    
    print(f"\nBTC/USDT: ${current_price:,.0f}")
    print(f"Timestamp: {datetime.fromtimestamp(curr_ts / 1000).isoformat()}")
    print(f"\n4H Indicators:")
    print(f"  Bias50:     {bias50:+.2f}%")
    print(f"  Bias20:     {bias20:+.2f}%")
    print(f"  Bias200:    {bias200:+.2f}%")
    print(f"  RSI(14):    {rsi:.1f}")
    print(f"  MACD Hist:  {macd:+.1f}")
    print(f"  BB %B:      {bb_pct:.2f}")
    print(f"  Dist BB↓:   {dist_bb_lower:+.2f}%")
    print(f"  Dist Swing: {dist_sl:+.2f}%")
    print(f"  MA Order:   {ma_order:+.1f} ({'多頭' if ma_order > 0 else '空頭' if ma_order < 0 else '中性'})")
    
    # Check if setup conditions are met
    short_setup = (0.5 <= bias50 <= 5.0 and macd < 0 and rsi < 55)
    
    print(f"\n{'─' * 60}")
    if short_setup:
        print("✅ Short setup condition MET!")
        print(f"   bias50 in [0.5, 5.0] + MACD<0 + RSI<55")
    else:
        print("❌ Short setup condition NOT met")
        reasons = []
        if not (0.5 <= bias50 <= 5.0):
            reasons.append(f"   bias50={bias50:.2f}% not in [0.5, 5.0]")
        if not (macd < 0):
            reasons.append(f"   MACD={macd:+.1f} not < 0")
        if not (rsi < 55):
            reasons.append(f"   RSI={rsi:.1f} not < 55")
        for r in reasons:
            print(r)
    
    # Model prediction
    model_path = '/home/kazuha/Poly-Trader/model_4h/xgb_4h.pkl'
    if os.path.exists(model_path):
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        model = model_data['model']
        
        features = {}
        for col in FEATURES_4H:
            features[col] = [gv(ind, col, n - 1, n)]
        import pandas as pd
        X = pd.DataFrame(features)
        pred_return = model.predict(X)[0]
        
        print(f"\n{'─' * 60}")
        print(f"Model predicted 24H return: {pred_return:+.4f}")
        
        if pred_return < 0:
            print(f"  → SELL signal: Expect price to drop")
            print(f"  → Target: ${(1 + pred_return) * current_price:,.0f}")
            if short_setup:
                print(f"  → Setup confirmed + Model agrees = Strong SELL")
        else:
            print(f"  → HOLD signal: Price may rise")
    else:
        print(f"\n  Model not found at {model_path}")
    
    print()

if __name__ == "__main__":
    main()
