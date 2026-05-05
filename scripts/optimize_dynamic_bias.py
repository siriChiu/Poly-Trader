"""
4H 動態策略優化 — 熊市驗證 + 動態 Bias
======================================
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

print(f"Total candles: {len(all_ohlcv)}")
candles = {
    "timestamps": np.array([o[0] for o in all_ohlcv]),
    "opens": np.array([o[1] for o in all_ohlcv]),
    "highs": np.array([o[2] for o in all_ohlcv]),
    "lows": np.array([o[3] for o in all_ohlcv]),
    "closes": np.array([o[4] for o in all_ohlcv]),
    "volumes": np.array([o[5] for o in all_ohlcv]),
}
n = len(candles["closes"])
start_date = datetime.fromtimestamp(candles["timestamps"][0] / 1000).date()
end_date = datetime.fromtimestamp(candles["timestamps"][-1] / 1000).date()
print(f"Range: {start_date} → {end_date}")
print(f"Price: ${candles['closes'][0]:,.0f} → ${candles['closes'][-1]:,.0f}")

print("Computing indicators...")
ind = compute_4h_indicators(candles)
closes = candles["closes"]
highs = candles["highs"]
lows = candles["lows"]

def gv(name, i, default=0):
    arr = ind.get(name, [default] * n)
    v = arr[i] if 0 <= i < len(arr) else default
    return float(v) if isinstance(v, (int, float)) and np.isfinite(v) else float(default)

def backtest_signal(bull_low, bull_high, bull_rsi, bear_low, bear_high, bear_rsi, bb_min=0, horizon=6):
    """Test dynamic regime strategy across all data."""
    trades = []
    for i in range(200, n - horizon):
        b200 = gv('4h_bias200', i)
        b50 = gv('4h_bias50', i)
        macd_h = gv('4h_macd_hist', i)
        rsi_14 = gv('4h_rsi14', i)
        bb_pct = gv('4h_bb_pct_b', i)
        
        # Check MACD
        if macd_h >= 0:
            continue
        
        # Dynamic bias range based on regime
        if b200 > 0:  # Bull: conservative
            if not (bull_low <= b50 < bull_high):
                continue
            if not (rsi_14 < bull_rsi and bb_pct > bb_min):
                continue
        else:  # Bear: aggressive
            if not (bear_low <= b50 < bear_high):
                continue
            if not (rsi_14 < bear_rsi):
                continue
        
        entry = closes[i]
        exit_idx = i + horizon
        if exit_idx >= n:
            break
        exit_p = closes[exit_idx]
        
        # Max drawdown during hold
        max_dd = (min(lows[i:i+horizon+1]) - entry) / entry
        max_fe = (max(highs[i:i+horizon+1]) - entry) / entry
        
        ret = (exit_p - entry) / entry
        trades.append({
            "ret": ret,
            "max_dd": max_dd,
            "max_fe": max_fe,
            "win": 1 if ret < 0 else 0,
            "regime": "Bull" if b200 > 0 else "Bear",
        })
    
    if not trades:
        return None
    
    rets = np.array([t["ret"] for t in trades])
    wins = sum(t["win"] for t in trades)
    total = len(trades)
    wr = wins / total
    
    equity = np.cumsum(rets)
    peak = np.maximum.accumulate(equity)
    dd_curve = equity - peak
    max_dd_total = dd_curve.min() if len(dd_curve) > 0 else 0
    
    bull_wr = sum(t["win"] for t in trades if t["regime"] == "Bull") / max(1, sum(1 for t in trades if t["regime"] == "Bull"))
    bear_wr = sum(t["win"] for t in trades if t["regime"] == "Bear") / max(1, sum(1 for t in trades if t["regime"] == "Bear"))
    
    return {
        "total": total,
        "bull": sum(1 for t in trades if t["regime"] == "Bull"),
        "bear": sum(1 for t in trades if t["regime"] == "Bear"),
        "wr": wr,
        "bull_wr": bull_wr,
        "bear_wr": bear_wr,
        "total_ret": rets.sum(),
        "max_dd_avg": np.mean([t["max_dd"] for t in trades]),
        "max_fe_avg": np.mean([t["max_fe"] for t in trades]),
        "max_dd_total": max_dd_total,
    }

print("\n" + "=" * 70)
print("DYNAMIC REGIME SHORT STRATEGY")
print("=" * 70)
print("Bull = bias200>0 (conservative) | Bear = bias200<0 (aggressive)")
print()

all_results = []

for h, lbl in [(6, "24H"), (12, "48H"), (3, "12H")]:
    # Test different parameter sets
    params_list = [
        # Name, bull_lo, bull_hi, bull_rsi, bear_lo, bear_hi, bear_rsi, bb_min
        ("S1", 1.0, 3.0, 50, 0.0, 5.0, 55, 0.4),
        ("S2", 0.5, 3.0, 50, 0.0, 3.0, 55, 0.4),
        ("S3", 0.5, 2.0, 50, 0.0, 2.0, 50, 0.5),
        ("S4", 2.0, 5.0, 60, 0.0, 8.0, 55, 0.3),
        ("S5", 1.0, 5.0, 55, 0.0, 10.0, 55, 0.3),
        ("S6", 0.5, 1.5, 45, 0.0, 1.5, 45, 0.5),  # Very strict
    ]
    
    print(f"─── {lbl} Horizon ───")
    for name, bl, bh, br, el, eh, er, bb in params_list:
        r = backtest_signal(bl, bh, br, el, eh, er, bb, horizon=h)
        if r and r['total'] >= 30:
            all_results.append((f"{name}_{lbl}", r))
            print(f"  {name} | Total={r['total']:3d} (B={r['bull']} b={r['bear']}) "
                  f"WR={r['wr']:.1%} (Bull={r['bull_wr']:.1%}/Bear={r['bear_wr']:.1%}) "
                  f"Ret={r['total_ret']:+.4f} MaxDD={r['max_dd_total']:+.4f} AvgFE={r['max_fe_avg']:+.3f}")

# Baseline
print("\n── Baseline ──")
r_base_all = backtest_signal(-100, 100, 80, -100, 100, 80, 0, horizon=6)
print(f"  Always short (all setups): N={r_base_all['total']}, WR={r_base_all['wr']:.1%}")

# ── 6. Best Result & Summary ──
print("\n" + "=" * 70)
print("TOP 5 by WIN RATE (min 30 trades)")
print("=" * 70)
filtered = sorted(all_results, key=lambda x: -x[1]['wr'])
for i, (name, r) in enumerate(filtered[:5]):
    profit_factor = abs(r['total_ret'] / max(0.001, max(0, -sum(t for t in [1]) * 0.001)))
    # Simpler metric
    print(f"  #{i+1} {name}")
    print(f"    Win Rate:    {r['wr']:.1%} ({r['total']} trades: {r['bull']} bull, {r['bear']} bear)")
    print(f"    Regime WR:   Bull={r['bull_wr']:.1%} / Bear={r['bear_wr']:.1%}")
    print(f"    Total Ret:   {r['total_ret']:+.4f}")
    print(f"    Max DD:      {r['max_dd_total']:+.4f}")
    print(f"    Avg Adverse: {r['max_fe_avg']:+.3f}")
    print()
