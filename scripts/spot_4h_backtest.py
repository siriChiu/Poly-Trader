"""
4H 現貨做多策略 — 乖離率 + 支撐線 + 金字塔加碼
================================================

策略邏輯:
1. 乖離率越負 = 價格越遠離 MA50 = 越接近支撐 = 買點
2. 支撐線: MA50, MA200, 布林下軌
3. 金字塔: 分批買入, 越跌買越多
   - 第 1 層: 20% 資金 (初始價)
   - 第 2 層: 30% 資金 (跌 2%)
   - 第 3 層: 50% 資金 (跌 5%)
"""
import numpy as np, sys, ccxt
sys.path.insert(0, '/home/kazuha/Poly-Trader')
from feature_engine.ohlcv_4h import compute_4h_indicators
from datetime import datetime

print("Fetching 4H data...")
exchange = ccxt.okx({"enableRateLimit": True})
all_ohlcv = []
for i in range(10):
    if not all_ohlcv:
        ohlcv = exchange.fetch_ohlcv("BTC/USDT", "4h", limit=1000)
    else:
        oldest = all_ohlcv[0][0]
        ohlcv = exchange.fetch_ohlcv("BTC/USDT", "4h", limit=1000, params={"until": oldest})
    if not ohlcv or len(ohlcv) < 10:
        break
    merged = all_ohlcv + ohlcv
    seen = set()
    all_ohlcv = [c for c in merged if not (c[0] in seen or seen.add(c[0]))]
    all_ohlcv.sort(key=lambda x: x[0])
    if len(ohlcv) < 900:
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
closes = candles["closes"]
lows = candles["lows"]
highs = candles["highs"]

print(f"Candles: {n}")
print(f"Range: {datetime.fromtimestamp(candles['timestamps'][0]/1000).date()} → {datetime.fromtimestamp(candles['timestamps'][-1]/1000).date()}")
print(f"Price: ${closes[0]:,.0f} → ${closes[-1]:,.0f}")

# Compute indicators
print("Computing indicators...")
import warnings
warnings.filterwarnings("ignore")
ind = compute_4h_indicators(candles)


def gv(name, i, default=0):
    arr = ind.get(name, [default] * n)
    return float(arr[i]) if 0 <= i < len(arr) and isinstance(arr[i], (int, float)) and np.isfinite(arr[i]) else float(default)


def backtest_pyramid(name, condition_fn, horizon=12, initial_capital=10000.0):
    """
    金字塔做多回測
    """
    trades = []
    equity = initial_capital

    for i in range(200, n - horizon - 1):
        if not condition_fn(i):
            continue
        
        entry_price = closes[i]
        min_price = min(lows[i:i+horizon+1])
        
        # 金字塔加碼
        level1 = 0.20
        level2 = 0.30 if min_price / entry_price <= 0.98 else 0
        level3 = 0.50 if min_price / entry_price <= 0.95 else 0
        total_fill = level1 + level2 + level3
        
        if total_fill == 0:
            continue
        
        exit_price = closes[i + horizon]
        ret = (exit_price - entry_price) / entry_price
        
        trades.append({
            "ret": ret,
            "win": 1 if ret > 0 else 0,
            "fill": total_fill,
        })
    
    if not trades:
        print(f"  {name} ({horizon*4}H): no trades")
        return
    
    total = len(trades)
    wins = sum(t["win"] for t in trades)
    wr = wins / total
    rets = np.array([t["ret"] for t in trades])
    
    # Simple equity (no overlap compounding)
    total_ret = rets.sum()
    
    print(f"  {name} ({horizon*4}H | N={total:4d}): "
          f"WR={wr:5.1%}({wins}/{total}) "
          f"Ret={total_ret:+.4f} "
          f"AvgRet={rets.mean():+.4f} "
          f"Fill={(np.mean([t['fill'] for t in trades])*100):.0f}%")


print("\n" + "=" * 70)
print("4H 現貨做多 — 乖離率買點回測")
print("=" * 70)

# 乖離率區間測試
print("\n── 乖離率 (bias50) 單因子測試 ──")
for lo, hi in [
    (-20, -10), (-10, -7), (-7, -5), (-5, -3),
    (-3, -1), (-1, 0), (0, 1), (1, 3), (3, 5),
]:
    backtest_pyramid(f"bias50∈[{lo},{hi})",
                     lambda i, lo=lo, hi=hi: lo <= gv('4h_bias50', i) < hi,
                     horizon=12)


# 支撐線 + 過濾測試
print("\n── 乖離率 + 過濾 條件 ──")

filters = [
    ("偏離 MA50 < -1%",
     lambda i: gv('4h_bias50', i) < -1),
    
    ("偏離 MA50 < -3%",
     lambda i: gv('4h_bias50', i) < -3),
    
    ("偏離 MA50 < -3% + MACD<0 (空頭動能)",
     lambda i: gv('4h_bias50', i) < -3 and gv('4h_macd_hist', i) < 0),
    
    ("偏離 MA50 < -3% + RSI<40 (超賣)",
     lambda i: gv('4h_bias50', i) < -3 and gv('4h_rsi14', i) < 40),
    
    ("偏離 MA50 < -5% + RSI<30",
     lambda i: gv('4h_bias50', i) < -5 and gv('4h_rsi14', i) < 30),
    
    ("布林 %B < 0.1 (接近下軌)",
     lambda i: gv('4h_bb_pct_b', i) < 0.1),
    
    ("布林 %B < 0.1 + RSI<35",
     lambda i: gv('4h_bb_pct_b', i) < 0.1 and gv('4h_rsi14', i) < 35),
    
    ("偏離 MA50 < -1% + 成交量放大 > 1.5x",
     lambda i: gv('4h_bias50', i) < -1 and gv('4h_vol_ratio', i) > 1.5),
    
    ("MA200 下方 < 5%",
     lambda i: -5 < gv('4h_bias200', i) < 0),
    
    ("最嚴: 乖離率< -5% + RSI<35 + MACD<0 + BB<0.2",
     lambda i: gv('4h_bias50', i) < -5 and gv('4h_rsi14', i) < 35 and gv('4h_macd_hist', i) < 0 and gv('4h_bb_pct_b', i) < 0.2),
]

for name, cond_fn in filters:
    backtest_pyramid(name, cond_fn, horizon=12)


# 不同持有期測試
print("\n── 最佳策略 不同持有期 ──")
best_cond = lambda i: gv('4h_bias50', i) < -1
for h in [1, 3, 6, 12, 18, 24]:
    backtest_pyramid(f"bias50 < -1%", best_cond, horizon=h)


# Baseline
print(f"\n─ Baseline ─")
baseline_n = n - 200 - 6
baseline_wins = sum(1 for i in range(200, n - 6) if closes[i + 6] > closes[i])
print(f"  永遠做多 (hold 24H): N={baseline_n}, WR={baseline_wins/baseline_n:.1%}")

# Buy & Hold
bh_ret = (closes[-1] - closes[200]) / closes[200]
print(f"  Buy & Hold (整段): Ret={bh_ret:+.1%}")
