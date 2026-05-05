"""
4H Poly-Trader Signal — 完整停損/停利 + 動態倉位管理
====================================================
輸出: scripts/heartbeat_4h_result.json
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
    """Fetch latest OKX 4H data → compute indicators → generate signal."""
    exchange = ccxt.okx({"enableRateLimit": True})
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
    current_price = candles["closes"][-1]
    curr_ts = int(candles["timestamps"][-1])
    
    ind = compute_4h_indicators(candles)
    
    # ── 4H Indicators ──
    bias50 = gv(ind, '4h_bias50', n-1, n)
    bias20 = gv(ind, '4h_bias20', n-1, n)
    bias200 = gv(ind, '4h_bias200', n-1, n)
    rsi_14 = gv(ind, '4h_rsi14', n-1, n)
    macd_hist = gv(ind, '4h_macd_hist', n-1, n)
    bb_pct = gv(ind, '4h_bb_pct_b', n-1, n)
    ma_order = gv(ind, '4h_ma_order', n-1, n)
    dist_swing_low = gv(ind, '4h_dist_swing_low', n-1, n)
    dist_bb_lower = gv(ind, '4h_dist_bb_lower', n-1, n)
    
    regime = "BULL" if bias200 > 0 else "BEAR"
    
    # ── Dynamic Setup (from 2-year optimization) ──
    # S3 was best for bear: bear_bias=0~3, RSI<55
    # Bull uses conservative: bias=1~3, RSI<50, BB>0.4
    if regime == "BULL":
        setup_cond = (1.0 <= bias50 < 3.0 and macd_hist < 0 and rsi_14 < 50 and bb_pct > 0.4)
        regime_setup = "Conservative (bull)"
    else:
        setup_cond = (0.0 <= bias50 < 3.0 and macd_hist < 0 and rsi_14 < 55)
        regime_setup = "Aggressive (bear)"
    
    # ── Model Prediction ──
    predicted_return_24h = None
    model_predicted_sell = False
    model_available = False
    features_dict = {}
    
    model_path = '/home/kazuha/Poly-Trader/model_4h/xgb_4h.pkl'
    if os.path.exists(model_path):
        model_available = True
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        model = model_data['model']
        
        features_dict = {
            "4h_bias50": bias50,
            "4h_bias20": bias20,
            "4h_bias200": bias200,
            "4h_rsi14": rsi_14,
            "4h_macd_hist": macd_hist,
            "4h_bb_pct_b": bb_pct,
            "4h_dist_bb_lower": dist_bb_lower,
            "4h_dist_swing_low": dist_swing_low,
            "4h_ma_order": ma_order,
        }
        
        import pandas as pd
        X = pd.DataFrame([features_dict])
        predicted_return_24h = float(model.predict(X)[0])
        model_predicted_sell = predicted_return_24h < 0
    
    # ── Stop Loss / Take Profit (historical-based) ──
    # Use recent ATR proxy to set reasonable SL/TP levels
    # 4H ATR ≈ 0.5-2% for BTC
    # For short: SL = entry * (1 + ATR_pct), TP = entry * (1 - 2*ATR_pct)
    # SL/TP ratios based on optimization: AvgFE ~0.019 (adverse excursion)
    ATR_SL = 0.025   # 2.5% stop loss
    ATR_TP = 0.050   # 5.0% take profit (2:1 RR)
    
    sl_price = current_price * (1 + ATR_SL)
    tp_price = current_price * (1 - ATR_TP)
    
    base_kelly = 0.10  # conservative base
    
    # ── Position Sizing (Kelly-inspired) ──
    # Scale by setup+model agreement
    
    # ── Signal Determination ──
    if setup_cond and model_predicted_sell:
        signal = "SELL"
        confidence_level = "HIGH"
        position_size = min(0.30, base_kelly * 3)
    elif setup_cond:
        signal = "SELL"
        confidence_level = "MEDIUM"
        position_size = min(0.20, base_kelly * 2)
    elif model_predicted_sell:
        signal = "HOLD"
        confidence_level = "LOW"
        position_size = min(0.15, base_kelly * 1.5)
    else:
        signal = "HOLD"
        confidence_level = "NONE"
        position_size = 0
    
    reasons = []
    if setup_cond:
        pred_str = f"{predicted_return_24h:+.4f}" if predicted_return_24h is not None else "N/A"
        reasons.append(f"Setup=✅ (regime={regime}, b50={bias50:.1f}%, macd={macd_hist:+.0f}) | Model=✅ Sell (pred={pred_str})")
    else:
        if model_predicted_sell:
            pred_str = f"{predicted_return_24h:+.4f}" if predicted_return_24h is not None else "N/A"
            reasons.append(f"Setup=❌ | Model=✅ Sell (pred={pred_str})")
        else:
            reasons.append(f"Setup=❌ | Model=❌ (no edge)")
    
    result = {
        "timestamp": curr_ts,
        "datetime": datetime.fromtimestamp(curr_ts / 1000).isoformat(),
        "current_price": current_price,
        "regime": regime,
        "regime_setup": regime_setup,
        "bias50": round(bias50, 2),
        "bias200": round(bias200, 2),
        "rsi_14": round(rsi_14, 1),
        "macd_hist": round(macd_hist, 1),
        "bb_pct_b": round(bb_pct, 2),
        "setup_condition_met": setup_cond,
        "model_predicted_sell": model_predicted_sell,
        "predicted_return_24h": round(predicted_return_24h, 5) if predicted_return_24h is not None else None,
        "signal": signal,
        "confidence_level": confidence_level,
        "position_size_pct": round(position_size, 3),
        "leverage_x": round(position_size * 10, 1) if position_size > 0 else 0,
        "stop_loss": {
            "type": "percentage",
            "pct": ATR_SL,
            "price": round(sl_price, 2),
            "usd_loss_per_unit": round(sl_price - current_price, 2),
        },
        "take_profit": {
            "type": "percentage",
            "pct": ATR_TP,
            "price": round(tp_price, 2),
            "usd_profit_per_unit": round(current_price - tp_price, 2),
        },
        "rr_ratio": round(ATR_TP / ATR_SL, 1),
        "reason": " | ".join(reasons),
        "features": {k: round(v, 4) for k, v in features_dict.items()},
    }
    
    # Save
    output_path = os.path.join('/home/kazuha/Poly-Trader/scripts', 'heartbeat_4h_result.json')
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    return result


def print_report(result):
    """Formatted report for console."""
    print("=" * 60)
    print("🔮 4H Poly-Trader Signal")
    print("=" * 60)
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return
    
    print(f"BTC/USDT: ${result['current_price']:,.0f}")
    print(f"Time:     {result['datetime']}")
    print(f"\n📊 Regime: {result['regime']} ({result['regime_setup']})")
    print(f"  Bias200:  {result['bias200']:+.2f}%")
    print(f"  Bias50:   {result['bias50']:+.2f}%")
    print(f"  RSI(14):  {result['rsi_14']}")
    print(f"  MACD:     {result['macd_hist']:+.1f}")
    print(f"  BB %B:    {result['bb_pct_b']:.2f}")
    
    print(f"\n📍 Setup: {'✅ MET' if result['setup_condition_met'] else '❌ NOT MET'}")
    
    if result['predicted_return_24h'] is not None:
        pr = result['predicted_return_24h']
        print(f"  Predicted 24H Ret: {pr:+.4f}")
        target = result['current_price'] * (1 + pr)
        print(f"  Target Price: ${target:,.0f}")
    
    print(f"\n🚦 Signal: {result['signal']}")
    print(f"  Confidence: {result['confidence_level']}")
    print(f"  Position: {result['position_size_pct']:.1%} ({result['leverage_x']}x)")
    print(f"\n🛡️ Stop Loss: ${result['stop_loss']['price']:,.0f} ({result['stop_loss']['pct']*100:.1f}%)")
    print(f"🎯 Take Profit: ${result['take_profit']['price']:,.0f} ({result['take_profit']['pct']*100:.1f}%)")
    print(f"  Risk/Reward: 1:{result['rr_ratio']}")
    print(f"\n{result['reason']}")
    print()


if __name__ == "__main__":
    result = analyze_4h()
    print_report(result)
