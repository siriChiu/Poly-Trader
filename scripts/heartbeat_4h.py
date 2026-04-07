"""
4H 預測整合到 Poly-Trader Heartbeat
=====================================
修改:
1. heartbeat 腳本讀取 4H 最新資料
2. XGBoost 模型生成信號
3. 動態 bias 過濾 (牛市嚴格,熊市寬鬆)
"""
import numpy as np
import sys, ccxt, pickle, json, os
from datetime import datetime
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

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
    v = arr[i] if 0 <= i < len(arr) else default
    return float(v) if isinstance(v, (int, float)) and np.isfinite(v) else float(default)


def analyze_4h():
    """Fetch latest Binance data and return 4H analysis."""
    exchange = ccxt.binance({"enableRateLimit": True})
    try:
        ohlcv = exchange.fetch_ohlcv("BTC/USDT", "4h", limit=300)
    except Exception as e:
        return {"error": f"Failed to fetch data: {e}"}
    
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
    current_price = candles["closes"][-1]
    curr_ts = int(candles["timestamps"][-1])
    
    # Key 4H indicators
    bias50 = gv(ind, '4h_bias50', n-1, n)
    bias20 = gv(ind, '4h_bias20', n-1, n)
    bias200 = gv(ind, '4h_bias200', n-1, n)
    rsi_14 = gv(ind, '4h_rsi14', n-1, n)
    macd_hist = gv(ind, '4h_macd_hist', n-1, n)
    bb_pct = gv(ind, '4h_bb_pct_b', n-1, n)
    ma_order = gv(ind, '4h_ma_order', n-1, n)
    dist_swing_low = gv(ind, '4h_dist_swing_low', n-1, n)
    
    # Determine regime
    regime = "BULL" if bias200 > 0 else "BEAR"
    
    # Dynamic condition check (from optimization results)
    # Bull: bias50 1.0~3.0 + MACD<0 + RSI<50 + BB>0.4
    # Bear: bias50 0.0~5.0 + MACD<0 + RSI<55
    if regime == "BULL":
        setup = (1.0 <= bias50 < 3.0 and macd_hist < 0 and rsi_14 < 50 and bb_pct > 0.4)
        regime_note = "Conservative"
    else:
        setup = (0.0 <= bias50 < 5.0 and macd_hist < 0 and rsi_14 < 55)
        regime_note = "Aggressive"
    
    # Feature vector for model
    features_dict = {
        "4h_bias50": bias50,
        "4h_bias20": bias20,
        "4h_bias200": bias200,
        "4h_rsi14": rsi_14,
        "4h_macd_hist": macd_hist,
        "4h_bb_pct_b": bb_pct,
        "4h_dist_bb_lower": gv(ind, '4h_dist_bb_lower', n-1, n),
        "4h_dist_swing_low": dist_swing_low,
        "4h_ma_order": ma_order,
    }
    
    # Model prediction (if model exists)
    model_predicted_sell = False
    predicted_return = None
    conf = 0.5
    
    model_path = '/home/kazuha/Poly-Trader/model_4h/xgb_4h.pkl'
    if os.path.exists(model_path):
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        model = model_data['model']
        
        import pandas as pd
        X = pd.DataFrame([features_dict])
        predicted_return = float(model.predict(X)[0])
        model_predicted_sell = predicted_return < 0
        
        # Confidence: how far from 0
        conf = min(0.95, max(0.05, 0.5 - predicted_return * 10))
    else:
        model_status = "NOT_FOUND"
    
    # Final signal
    if setup and model_predicted_sell:
        signal = "SELL"
        confidence = "HIGH"
    elif setup and not model_predicted_sell:
        signal = "SELL"
        confidence = "MEDIUM"
    elif not setup and model_predicted_sell:
        signal = "HOLD"
        confidence = "LOW"
    else:
        signal = "HOLD"
        confidence = "NONE"
    
    result = {
        "timestamp": curr_ts,
        "datetime": datetime.fromtimestamp(curr_ts / 1000).isoformat(),
        "current_price": current_price,
        "regime": regime,
        "regime_note": regime_note,
        "bias50": round(bias50, 2),
        "bias200": round(bias200, 2),
        "rsi_14": round(rsi_14, 1),
        "macd_hist": round(macd_hist, 1),
        "bb_pct_b": round(bb_pct, 2),
        "ma_order": round(ma_order, 1),
        "setup_condition_met": setup,
        "model_predicted_sell": model_predicted_sell,
        "predicted_return_24h": round(predicted_return, 5) if predicted_return else None,
        "signal": signal,
        "confidence": confidence,
        "features": {k: round(v, 4) for k, v in features_dict.items()},
    }
    
    # Save result for heartbeat consumption
    output_dir = '/home/kazuha/Poly-Trader/scripts'
    output_path = os.path.join(output_dir, 'heartbeat_4h_result.json')
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    return result


def print_report(result):
    """Formatted report for console."""
    print("=" * 60)
    print("🔮 4H Poly-Trader Analysis")
    print("=" * 60)
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return
    
    print(f"BTC/USDT: ${result['current_price']:,.0f}")
    print(f"Time:     {result['datetime']}")
    print(f"\n📊 Regime: {result['regime']} ({result['regime_note']})")
    print(f"  Bias200:  {result['bias200']:+.2f}%")
    print(f"  Bias50:   {result['bias50']:+.2f}%")
    print(f"  RSI(14):  {result['rsi_14']}")
    print(f"  MACD:     {result['macd_hist']:+.1f}")
    print(f"  BB %B:    {result['bb_pct_b']:.2f}")
    print(f"  MA Order: {result['ma_order']:+.1f}")
    
    print(f"\n📍 Setup: {'✅ MET' if result['setup_condition_met'] else '❌ NOT MET'}")
    
    if result['predicted_return_24h'] is not None:
        pr = result['predicted_return_24h']
        print(f"  Predicted 24H Ret: {pr:+.4f} ({'↓ Bearish' if pr < 0 else '↑ Bullish'})")
        target = result['current_price'] * (1 + pr)
        print(f"  Target Price: ${target:,.0f}")
    
    print(f"\n🚦 Signal: {result['signal']}")
    print(f"  Confidence: {result['confidence']}")
    print(f"  Reason: Setup={'✅' if result['setup_condition_met'] else '❌'}, "
          f"Model={'✅ Sell' if result['model_predicted_sell'] else '❌'}")
    print()


if __name__ == "__main__":
    result = analyze_4h()
    print_report(result)
