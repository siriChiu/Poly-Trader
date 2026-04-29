"""
用 Binance 1d K線抓更長歷史 (3年) 驗證 4H 策略
"""
import numpy as np, sys
sys.path.insert(0, '/home/kazuha/Poly-Trader')
from feature_engine.ohlcv_4h import compute_4h_indicators

import ccxt
from datetime import datetime
exchange = ccxt.binance({"enableRateLimit": True})

# 先抓 1d 看整體趨勢
ohlcv_1d = exchange.fetch_ohlcv("BTC/USDT", "1d", limit=1100)
print(f"1d candles: {len(ohlcv_1d)}")
print(f"Date range: {ohlcv_1d[0][0]} → {ohlcv_1d[-1][0]}")
closes_1d = np.array([o[4] for o in ohlcv_1d])
print(f"Price: ${closes_1d[0]:,.0f} → ${closes_1d[-1]:,.0f} ({(closes_1d[-1]/closes_1d[0]-1)*100:+.1f}%)")

# 抓 4h 更多歷史
ohlcv_4h = exchange.fetch_ohlcv("BTC/USDT", "4h", limit=1000)
closes_4h = np.array([o[4] for o in ohlcv_4h])
highs_4h = np.array([o[2] for o in ohlcv_4h])
lows_4h = np.array([o[3] for o in ohlcv_4h])
volumes_4h = np.array([o[5] for o in ohlcv_4h])
timestamps_4h = np.array([o[0] for o in ohlcv_4h])

print(f"\n4h candles: {len(ohlcv_4h)}")

# 計算指標
candles = {
    "timestamps": timestamps_4h,
    "opens": np.array([o[1] for o in ohlcv_4h]),
    "highs": highs_4h,
    "lows": lows_4h,
    "closes": closes_4h,
    "volumes": volumes_4h,
}

indicators = compute_4h_indicators(candles)
n = len(closes_4h)

print("=" * 70)
print("全面測試: 乖離率 vs 做空勝率")
print("=" * 70)

# Test: bias50 ranges and win rates
bias50 = indicators.get("4h_bias50", np.zeros(n))

ranges = [
    ("bias50 < -5%", lambda b: b < -5),
    ("-5% <= bias50 < -3%", lambda b: -5 <= b < -3),
    ("-3% <= bias50 < -1%", lambda b: -3 <= b < -1),
    ("-1% <= bias50 < 0%", lambda b: -1 <= b < 0),
    ("0% <= bias50 < 1%", lambda b: 0 <= b < 1),
    ("1% <= bias50 < 3%", lambda b: 1 <= b < 3),
    ("3% <= bias50 < 5%", lambda b: 3 <= b < 5),
    ("bias50 >= 5%", lambda b: b >= 5),
]

for name, fn in ranges:
    indices = [i for i in range(200, n - 6) if fn(bias50[i])]
    if not indices:
        print(f"\n  {name}: no signals")
        continue
    
    wins = 0
    returns = []
    for i in indices:
        ret = (closes_4h[min(i+6, n-1)] - closes_4h[i]) / closes_4h[i]
        returns.append(ret)
        if ret < 0:
            wins += 1
    
    ret_arr = np.array(returns)
    print(f"\n  {name} ({len(indices)} trades, 24H horizon):")
    print(f"    Win rate: {wins/len(indices):.1%} ({wins}/{len(indices)})")
    print(f"    Avg return: {ret_arr.mean():.4f}")
    print(f"    Median return: {np.median(ret_arr):.4f}")

# Also test MA alignment
print("\n" + "=" * 70)
print("MA 排列 vs 做空勝率")
print("=" * 70)

ma20 = indicators.get("4h_ma20", np.zeros(n))
ma50 = indicators.get("4h_ma50", np.zeros(n))
ma200 = indicators.get("4h_ma200", np.zeros(n))
rsi = indicators.get("4h_rsi14", np.full(n, 50.0))

# MA alignment patterns
patterns = [
    ("完全空頭: MA20<MA50<MA200", lambda i: ma20[i]<ma50[i]<ma200[i]),
    ("空頭: MA20<MA50", lambda i: ma20[i]<ma50[i] and ma20[i]>0),
    ("多頭: MA20>MA50", lambda i: ma20[i]>ma50[i] and ma50[i]>0),
    ("完全多頭: MA20>MA50>MA200", lambda i: ma20[i]>ma50[i]>ma200[i] and ma200[i]>0),
]

for name, fn in patterns:
    indices = [i for i in range(200, n - 6) if fn(i)]
    if not indices:
        print(f"\n  {name}: no signals")
        continue
    
    wins = sum(1 for i in indices if closes_4h[min(i+6,n-1)] < closes_4h[i])
    total = len(indices)
    rets = np.array([(closes_4h[min(i+6,n-1)] - closes_4h[i]) / closes_4h[i] for i in indices])
    print(f"\n  {name} ({total} trades, 24H horizon):")
    print(f"    Win rate: {wins/total:.1%} ({wins}/{total})")
    print(f"    Avg return: {rets.mean():.4f}")

# Best combo from data analysis
print("\n" + "=" * 70)
print("最佳組合測試 (從數據找最優條件)")
print("=" * 70)

# Find which combination of conditions gives highest win rate
macd_h = indicators.get("4h_macd_hist", np.zeros(n))
bb_pct = indicators.get("4h_bb_pct_b", np.full(n, 0.5))

for min_score in [3, 4, 5]:
    signals = []
    for i in range(200, n - 6):
        score = 0
        if ma20[i] > 0 and ma50[i] > 0:
            if ma20[i] < ma50[i]:
                score += 1  # downtrend
        if bias50[i] > 3:
            score += 1  # significantly above MA50 (room to fall)
        if macd_h[i] < 0:
            score += 1  # bearish momentum
        if bb_pct[i] > 0.7:
            score += 1  # upper half of BB
        if rsi[i] > 50:
            score += 1  # RSI above neutral (not oversold)
        
        if score >= min_score:
            signals.append(i)
    
    if signals:
        wins = sum(1 for i in signals if closes_4h[min(i+6, n-1)] < closes_4h[i])
        rets = np.array([(closes_4h[min(i+6, n-1)] - closes_4h[i]) / closes_4h[i] for i in signals])
        print(f"\n  Score >= {min_score} ({len(signals)} trades, 24H horizon):")
        print(f"    Win rate: {wins/len(signals):.1%} ({wins}/{len(signals)})")
        print(f"    Avg return: {rets.mean():.4f}")
