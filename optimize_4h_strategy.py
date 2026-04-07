"""
策略優化: 用 4H 規則式策略,調參數找最優條件組合
=====================================================
目標: 找出最高勝率的做空入場條件
"""
import numpy as np, sys, ccxt
sys.path.insert(0, '/home/kazuha/Poly-Trader')
from feature_engine.ohlcv_4h import compute_4h_indicators
from datetime import datetime

# 抓更長期的 4H 數據
print("Fetching 4H OHLCV from Binance...")
exchange = ccxt.binance({"enableRateLimit": True})
all_ohlcv = []
for _ in range(5):
    if not all_ohlcv:
        ohlcv = exchange.fetch_ohlcv("BTC/USDT", "4h", limit=1000)
    else:
        oldest = all_ohlcv[0][0]
        ohlcv = exchange.fetch_ohlcv("BTC/USDT", "4h", limit=1000, params={"until": oldest})
    if not ohlcv or len(ohlcv) < 2:
        break
    merged = all_ohlcv + ohlcv
    seen = set()
    all_ohlcv = [c for c in merged if not (c[0] in seen or seen.add(c[0]))]
    all_ohlcv.sort(key=lambda x: x[0])
    print(f"  Batch: {len(all_ohlcv)} total")
    if len(ohlcv) < 500:
        break

print(f"Total 4H candles: {len(all_ohlcv)}")

candles = {
    "timestamps": np.array([o[0] for o in all_ohlcv]),
    "opens": np.array([o[1] for o in all_ohlcv]),
    "highs": np.array([o[2] for o in all_ohlcv]),
    "lows": np.array([o[3] for o in all_ohlcv]),
    "closes": np.array([o[4] for o in all_ohlcv]),
    "volumes": np.array([o[5] for o in all_ohlcv]),
}

n = len(candles["closes"])
print(f"Date: {datetime.fromtimestamp(candles['timestamps'][0]/1000).isoformat()} → {datetime.fromtimestamp(candles['timestamps'][-1]/1000).isoformat()}")
print(f"Price: ${candles['closes'][0]:,.0f} → ${candles['closes'][-1]:,.0f} ({(candles['closes'][-1]/candles['closes'][0]-1)*100:+.1f}%)")

ind = compute_4h_indicators(candles)
closes = candles["closes"]

def gv(name, i, default=0):
    """Get value at index i from indicator array."""
    arr = ind.get(name, [default] * n)
    v = arr[i] if i < len(arr) else default
    return float(v) if isinstance(v, (int, float)) and np.isfinite(v) else float(default)

def test_strategy(name, condition_fn, horizon=6):
    """Test strategy signal win rate."""
    signals = []
    for i in range(200, n - horizon):
        if condition_fn(i):
            signals.append(i)
    if not signals:
        return None
    wins = 0
    returns = []
    for i in signals:
        ret = (closes[min(i + horizon, n - 1)] - closes[i]) / closes[i]
        returns.append(ret)
        if ret < 0:
            wins += 1
    ret_arr = np.array(returns)
    total = len(signals)
    wr = wins / total
    print(f"  {name}: {total} trades, WR={wr:.1%}({wins}/{total}), avg_ret={ret_arr.mean():.5f}, median={np.median(ret_arr):.5f}, PnL={ret_arr.sum():.4f}")
    return wr, total, ret_arr.sum()

results = []

# ════ 乖離率 (bias50) 區間測試 ════
print("\n─ Bias50 ranges ─")
for lo, hi in [(-100, -5), (-5, -3), (-3, -1), (-1, 0), (0, 0.5), (0.5, 1), (1, 2), (2, 3), (3, 5), (5, 100)]:
    r = test_strategy(f"bias50∈[{lo},{hi})", lambda i, lo=lo, hi=hi: lo <= gv('4h_bias50', i) < hi)
    if r:
        results.append(("bias50", lo, hi, r[0], r[1], r[2]))

# ════ bias50 + MACD ════
print("\n─ Bias50 + MACD ─")
for lo, hi in [(0, 3), (1, 3), (2, 3), (1, 5), (2, 5), (3, 5)]:
    r = test_strategy(f"bias50∈[{lo},{hi})+MACD<0",
        lambda i, lo=lo, hi=hi: lo <= gv('4h_bias50', i) < hi and gv('4h_macd_hist', i) < 0)
    if r: results.append(("bias+macd", lo, hi, r[0], r[1], r[2]))

# ════ bias50 + RSI ════
print("\n─ Bias50 + RSI ─")
for lo, hi in [(1, 3), (1, 5), (2, 3), (2, 5)]:
    for rsi_max in [40, 50, 55, 60]:
        r = test_strategy(f"bias50∈[{lo},{hi})+RSI<{rsi_max}",
            lambda i, lo=lo, hi=hi, rm=rsi_max: lo <= gv('4h_bias50', i) < hi and gv('4h_rsi14', i) < rm)
        if r: results.append((f"bias+rsi<{rsi_max}", lo, hi, r[0], r[1], r[2]))

# ════ 多條件組合 ════
print("\n─ Multi-condition combos ─")
# bias50 > 0 + MACD < 0 + RSI < 50 + bb > 0.3
for bb_min in [0.2, 0.3, 0.4, 0.5]:
    def cond(i, bm=bb_min):
        return (0 <= gv('4h_bias50', i) < 5 and
                gv('4h_macd_hist', i) < 0 and
                gv('4h_rsi14', i) < 50 and
                gv('4h_bb_pct_b', i) > bm)
    r = test_strategy(f"bias50 0~5%+MACD<0+RSI<50+bb%b>{bb_min}", cond)

# bias50 > 0 + MACD < 0 + bb > 0.4
r = test_strategy("bias50>0+MACD<0+bb>0.4",
    lambda i: gv('4h_bias50', i) > 0 and gv('4h_macd_hist', i) < 0 and gv('4h_bb_pct_b', i) > 0.4)

# bias50 1~3% + MACD < 0 + RSI < 50 + bb > 0.3
r = test_strategy("bias1-3+MACD<0+RSI<50+bb>0.3",
    lambda i: 1 <= gv('4h_bias50', i) < 3 and gv('4h_macd_hist', i) < 0 and gv('4h_rsi14', i) < 50 and gv('4h_bb_pct_b', i) > 0.3)

# ════ 不同 horizon 測試 ════
print("\n─ Best combo across horizons ─")
best_cond = lambda i: 1 <= gv('4h_bias50', i) < 5 and gv('4h_macd_hist', i) < 0 and gv('4h_rsi14', i) < 50
for h in [1, 2, 3, 6, 12]:
    test_strategy(f"Best combo @ {h*4}H", best_cond, horizon=h)

# Baseline
total_b = n - 200 - 6
wins_b = sum(1 for i in range(200, n - 6) if closes[i + 6] < closes[i])
print(f"\n  Baseline (all short): {total_b} trades, WR={wins_b/total_b:.1%}")

# ════ 排序結果 ════
print("\n" + "=" * 70)
print("TOP RESULTS (by win rate, min 30 trades)")
print("=" * 70)
filtered = [(name, lo, hi, wr, total, pnl) for name, lo, hi, wr, total, pnl in results if total >= 30]
filtered.sort(key=lambda x: -x[3])
for name, lo, hi, wr, total, pnl in filtered[:15]:
    print(f"  {name}: WR={wr:.1%} ({total} trades, PnL={pnl:.4f})")
