"""
回填 4H 特徵到 features_normalized
===================================
從 Binance 抓 4H OHLCV → 計算指標 → 匹配到最接近的 DB feature row
"""
import numpy as np
import sys, ccxt
from datetime import datetime
sys.path.insert(0, '/home/kazuha/Poly-Trader')

from feature_engine.ohlcv_4h import compute_4h_indicators
from database.models import init_db, FeaturesNormalized

print("=" * 60)
print("4H Feature Backfill")
print("=" * 60)

# Fetch 4H data
exchange = ccxt.binance({"enableRateLimit": True})
ohlcv = exchange.fetch_ohlcv("BTC/USDT", "4h", limit=1000)
print(f"Fetched {len(ohlcv)} 4H candles from Binance")

candles = {
    "timestamps": np.array([o[0] for o in ohlcv]),
    "opens": np.array([o[1] for o in ohlcv]),
    "highs": np.array([o[2] for o in ohlcv]),
    "lows": np.array([o[3] for o in ohlcv]),
    "closes": np.array([o[4] for o in ohlcv]),
    "volumes": np.array([o[5] for o in ohlcv]),
}

# Compute all 4H indicators
print("Computing 4H indicators...")
indicators = compute_4h_indicators(candles)
n = len(candles["closes"])

# Connect to DB
db = init_db('sqlite:///./poly_trader.db')
feat_rows = db.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp).all()
print(f"Feature rows in DB: {len(feat_rows)}")

# For each 4H candle, find all feature rows that fall within its 4H window
# and update the latest one in that window
candle_4h_ms = 4 * 60 * 60 * 1000  # 4 hours in milliseconds

updated = 0
matched = 0
for i in range(n):
    candle_start_ms = candles["timestamps"][i]
    candle_end_ms = candle_start_ms + candle_4h_ms
    
    candle_start_dt = datetime.fromtimestamp(candle_start_ms / 1000)
    candle_end_dt = datetime.fromtimestamp(candle_end_ms / 1000)
    
    # Find feature rows within this 4H window
    window_rows = [r for r in feat_rows
                   if r.timestamp is not None and candle_start_dt <= r.timestamp < candle_end_dt]
    
    if not window_rows:
        continue
    
    # Update the last row in the window (closest to candle close)
    target = window_rows[-1]
    matched += 1
    
    # Get indicator values
    bias50 = indicators.get("4h_bias50", [0]*n)[i]
    bias20 = indicators.get("4h_bias20", [0]*n)[i]
    rsi_14 = indicators.get("4h_rsi14", [50]*n)[i]
    macd_h = indicators.get("4h_macd_hist", [0]*n)[i]
    bb_pct = indicators.get("4h_bb_pct_b", [0.5]*n)[i]
    ma_order = indicators.get("4h_ma_order", [0]*n)[i]
    dist_sl = indicators.get("4h_dist_swing_low", [0]*n)[i]
    
    target.feat_4h_bias50 = float(bias50)
    target.feat_4h_bias20 = float(bias20)
    target.feat_4h_rsi14 = float(rsi_14)
    target.feat_4h_macd_hist = float(macd_h)
    target.feat_4h_bb_pct_b = float(bb_pct)
    target.feat_4h_ma_order = float(ma_order)
    target.feat_4h_dist_swing_low = float(dist_sl)
    updated += 1

db.commit()
db.close()

print(f"\nMatched: {matched} 4H candles to feature windows")
print(f"Updated: {updated} feature rows with 4H indicators")
print(f"Unmatched: {n - matched} 4H candles (outside DB time range)")
print("\nDone!")
