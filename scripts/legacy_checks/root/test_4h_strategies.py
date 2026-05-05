"""
全面回測: 比較不同 4H 做空策略的勝率
"""
import numpy as np, sys
sys.path.insert(0, '/home/kazuha/Poly-Trader')
from feature_engine.ohlcv_4h import compute_4h_indicators, backtest_4h_strategy

import ccxt
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
closes = candles["closes"]
indicators = compute_4h_indicators(candles)
n = len(closes)

print("=" * 70)
print(f"BTC/USDT 4H 策略回測 | {candles['timestamps'][0]} → {candles['timestamps'][-1]}")
print(f"價格: ${closes[0]:,.0f} → ${closes[-1]:,.0f} ({(closes[-1]/closes[0]-1)*100:+.1f}%)")
print("=" * 70)

def run_strategy(name, condition_fn, horizon=6):
    """Run a strategy with a signal condition and backtest."""
    signals = []
    for i in range(200, n - horizon):
        ok = condition_fn(indicators, i)
        if ok:
            signals.append((i, "SELL"))
    if not signals:
        print(f"\n{name}: No signals")
        return
    
    total = len(signals)
    wins = 0
    returns = []
    for idx, _ in signals:
        entry = closes[idx]
        exit_p = closes[min(idx + horizon, n - 1)]
        ret = (exit_p - entry) / entry
        returns.append(ret)
        if ret < 0:
            wins += 1
    
    ret_arr = np.array(returns)
    print(f"\n{name} ({total} trades, {horizon*4}H horizon):")
    print(f"  Win rate: {wins/total:.1%} ({wins}/{total})")
    print(f"  Avg return: {ret_arr.mean():.4f}")
    print(f"  Median return: {np.median(ret_arr):.4f}")
    print(f"  Best: {ret_arr.min():.4f} (best short)")
    print(f"  Worst: {ret_arr.max():.4f} (worst short)")

# Strategy 1: MA20 < MA50 (downtrend) + RSI < 50
def s1(ind, i):
    ma20 = ind.get("4h_ma20", [0]*n)
    ma50 = ind.get("4h_ma50", [0]*n)
    rsi = ind.get("4h_rsi14", [50]*n)
    return ma20[i] > 0 and ma50[i] > 0 and ma20[i] < ma50[i] and rsi[i] < 50
run_strategy("S1: MA20<MA50 + RSI<50", s1, horizon=6)

# Strategy 2: MACD < 0 + RSI < 50 + price < MA50 (bearish)
def s2(ind, i):
    rsi = ind.get("4h_rsi14", [50]*n)
    macd_h = ind.get("4h_macd_hist", [0]*n)
    bias50 = ind.get("4h_bias50", [0]*n)
    return macd_h[i] < 0 and rsi[i] < 50 and bias50[i] < 0
run_strategy("S2: MACD<0 + RSI<50 + price<MA50", s2, horizon=6)

# Strategy 3: 反彈到 MA20 但受阻 (price crosses above MA20 but MACD still < 0)
def s3(ind, i):
    ma20 = ind.get("4h_ma20", [0]*n)
    macd_h = ind.get("4h_macd_hist", [0]*n)
    closes_i = candles["closes"][i]
    if ma20[i] <= 0:
        return False
    # Price is within 0.5% of MA20 (near resistance)
    dist_to_ma20 = abs(closes_i - ma20[i]) / closes_i * 100
    return dist_to_ma20 < 1.0 and macd_h[i] < 0
run_strategy("S3: Price near MA20 ±1% + MACD<0", s3, horizon=6)

# Strategy 4: Strong downtrend (MA20<MA50 + MACD<0 + RSI<40)
def s4(ind, i):
    ma20 = ind.get("4h_ma20", [0]*n)
    ma50 = ind.get("4h_ma50", [0]*n)
    rsi = ind.get("4h_rsi14", [50]*n)
    macd_h = ind.get("4h_macd_hist", [0]*n)
    return (ma20[i] > 0 and ma50[i] > 0 and ma20[i] < ma50[i] and
            macd_h[i] < 0 and rsi[i] < 40)
run_strategy("S4: MA20<MA50 + MACD<0 + RSI<40", s4, horizon=6)

# Strategy 5: 乖離率極端負 (超賣反彈) — 這是做多策略但我們看做空的勝率
def s5(ind, i):
    bias50 = ind.get("4h_bias50", [0]*n)
    return bias50[i] < -5  # Price >5% below MA50
run_strategy("S5 (反例): bias50<-5% (超賣，做空危險)", s5, horizon=6)

# Strategy 6: 乖離率極端正 (遠離MA) — 做空應該贏
def s6(ind, i):
    bias50 = ind.get("4h_bias50", [0]*n)
    return bias50[i] > 5  # Price >5% above MA50
run_strategy("S6: bias50>+5% (遠離MA，做空優勢)", s6, horizon=6)

# Strategy 7: 布林通道觸及上軌 (壓力)
def s7(ind, i):
    bb_pct = ind.get("4h_bb_pct_b", [0.5]*n)
    return bb_pct[i] > 0.9  # Near upper band
run_strategy("S7: BB %B>0.9 (接近上軌壓力)", s7, horizon=6)

# Strategy 8: 布林觸及下軌 (支撐) — 做空應該輸
def s8(ind, i):
    bb_pct = ind.get("4h_bb_pct_b", [0.5]*n)
    return bb_pct[i] < 0.1  # Near lower band
run_strategy("S8 (反例): BB %B<0.1 (接近下軌支撐，做空危險)", s8, horizon=6)

print("\n" + "=" * 70)
print("Baseline: Random short (always sell)")
total = n - 200 - 6
wins_sum = sum(1 for i in range(200, n - 6) if closes[i + 6] < closes[i])
print(f"  Win rate: {wins_sum/total:.1%} ({wins_sum}/{total})")
print("=" * 70)
