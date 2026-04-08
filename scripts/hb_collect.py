#!/usr/bin/env python3
"""Heartbeat Step 0 — 數據收集管線 v1.

Called at the start of every heartbeat BEFORE analysis.
Collects fresh market data from Binance + external sources,
runs the preprocessor to compute features, and generates labels.

Usage: python scripts/hb_collect.py
"""
import os, sys, logging
from datetime import datetime

PROJECT = "/home/kazuha/Poly-Trader"
sys.path.insert(0, PROJECT)
os.chdir(PROJECT)

PYTHON = os.path.join(PROJECT, "venv", "bin", "python")
os.environ["PYTHONPATH"] = PROJECT

from config import load_config
from database.models import RawMarketData, FeaturesNormalized, Labels, init_db

SYMBOL = "BTCUSDT"

def collect_raw_data(session):
    """Step 1: Collect fresh raw data from all sources."""
    from data_ingestion.collector import collect_all_senses, run_collection_and_save
    
    success = run_collection_and_save(session, SYMBOL)
    if success:
        count = session.query(RawMarketData).count()
        print(f"✅ Raw data collection success (total={count})")
    else:
        print("❌ Raw data collection FAILED")
    
    # Fallback: minimal Binance price check if collector fails
    if not success:
        try:
            import requests
            r = requests.get(
                "https://api.binance.com/api/v3/ticker/price",
                params={"symbol": "BTCUSDT"},
                timeout=15
            )
            if r.status_code == 200:
                price = float(r.json()["price"])
                rec = RawMarketData(
                    timestamp=datetime.utcnow(),
                    symbol=SYMBOL,
                    close_price=price,
                )
                session.add(rec)
                session.commit()
                print(f"⚠️  Fallback raw data saved: BTC=${price:.2f}")
        except Exception as e:
            print(f"❌ Fallback also failed: {e}")
            return False
    
    return True

def preprocess_features(session):
    """Step 2: Compute features from ALL raw data (including new entry)."""
    from feature_engine.preprocessor import run_preprocessor
    result = run_preprocessor(session, SYMBOL)
    if result:
        count = session.query(FeaturesNormalized).count()
        print(f"✅ Feature engineering success (total={count})")
    else:
        print("❌ Feature engineering FAILED")
    return result is not None

def update_regime_labels(session):
    """Step 3: Assign regime labels to features that have NULL.
    
    P0 fix: Features created by the old preprocessor have regime_label=NULL.
    We need to retroactively assign them based on the market data at that time.
    
    Simple regime rules:
    - bull:   close > SMA(144) AND FNG >= 30
    - bear:   close < SMA(144) AND FNG < 30
    - chop:   abs(close - SMA(144)) / SMA(144) < 0.03 (within 3% of SMA)
    - neutral: fallback
    """
    print("\n🏛️  Assigning regime labels...")

    null_count = session.query(FeaturesNormalized).filter(
        FeaturesNormalized.regime_label == None
    ).count()
    if null_count == 0:
        total_count = session.query(FeaturesNormalized).count()
        print(f"  ✅ All features already have regime labels (total={total_count})")
        return 0
    
    # Get all raw data ordered by timestamp for SMA calculation
    raw_rows = session.query(RawMarketData).filter(
        RawMarketData.symbol == SYMBOL
    ).order_by(RawMarketData.timestamp).all()
    
    # Build close price series
    close_prices = [(r.timestamp, r.close_price) for r in raw_rows if r.close_price is not None]
    print(f"  Using {len(close_prices)} price points for regime assignment")
    
    if len(close_prices) == 0:
        print("  ❌ No price data for regime assignment")
        return 0
    
    # Build FNG series for additional signal
    fng_map = {r.timestamp: r.fear_greed_index for r in raw_rows if r.fear_greed_index is not None}
    
    # Count NULL regime features
    null_count = session.query(FeaturesNormalized).filter(
        FeaturesNormalized.regime_label == None
    ).count()
    
    total_count = session.query(FeaturesNormalized).count()
    has_count = session.query(FeaturesNormalized).filter(
        FeaturesNormalized.regime_label != None
    ).count()
    
    print(f"  Features: total={total_count}, with_regime={has_count}, null_regime={null_count}")
    
    if null_count == 0:
        print("  ✅ All features already have regime labels")
        return 0
    
    import numpy as np
    closes = np.array([p[1] for p in close_prices])
    
    # Precompute SMA(144) for every point
    SMA_WINDOW = 144
    sma_144 = np.full(len(closes), np.nan)
    for i in range(SMA_WINDOW, len(closes)):
        sma_144[i] = np.mean(closes[i-SMA_WINDOW:i])
    
    timestamps = [p[0] for p in close_prices]
    
    # Map feature timestamps to the closest raw data index
    updated = 0
    null_features = session.query(FeaturesNormalized).filter(
        FeaturesNormalized.regime_label == None
    ).order_by(FeaturesNormalized.timestamp).all()
    
    # Build a timestamp->close_index map for quick lookup
    from datetime import timedelta
    ts_to_idx = {str(ts): i for i, ts in enumerate(timestamps)}
    
    for feat in null_features:
        ts_str = str(feat.timestamp)
        
        # Try exact match first
        idx = ts_to_idx.get(ts_str)
        
        # If not found, find closest within ±10min
        if idx is None:
            best_idx = None
            best_diff = timedelta(minutes=10)
            for i, ts in enumerate(timestamps):
                diff = abs(feat.timestamp - ts)
                if diff < best_diff:
                    best_diff = diff
                    best_idx = i
            idx = best_idx
        
        if idx is None or sma_144[idx] is None or np.isnan(sma_144[idx]):
            # Can't compute SMA — use simple rule
            close_val = closes[idx] if idx is not None else None
            if close_val:
                # Fallback: use shorter moving average
                if idx >= 24:
                    sma = np.mean(closes[max(0,idx-24):idx])
                    dev = (close_val - sma) / sma
                else:
                    dev = 0
            else:
                dev = 0
        else:
            dev = (closes[idx] - sma_144[idx]) / sma_144[idx]
        
        # Regime classification
        fng_val = None
        if idx is not None:
            # Find closest FNG
            ts_at_idx = timestamps[idx]
            closest_fng = None
            closest_fng_diff = timedelta(hours=6)
            for fng_ts, fng_v in fng_map.items():
                diff = abs(fng_ts - ts_at_idx)
                if diff < closest_fng_diff:
                    closest_fng_diff = diff
                    closest_fng = fng_v
            fng_val = closest_fng
        
        abs_dev = abs(dev)
        
        if abs_dev < 0.02:
            # Within 2% of SMA → chop (sideways)
            regime = "chop"
        elif dev > 0 and fng_val is not None and fng_val >= 30:
            # Above SMA + FNG >= 30 → bull
            regime = "bull"
        elif dev > 0 and fng_val is None:
            # Above SMA, no FNG data → use deviation threshold
            regime = "bull" if dev > 0.05 else "chop"
        elif dev < 0:
            # Below SMA → bear
            regime = "bear"
        else:
            regime = "neutral"
        
        feat.regime_label = regime
        updated += 1
    
    session.commit()
    print(f"  ✅ Updated {updated} features with regime labels")
    return updated

def generate_labels(session, horizon_hours=4):
    """Step 4: Generate labels for features that don't yet have them."""
    from data_ingestion.labeling import generate_future_return_labels, save_labels_to_db
    
    labels_df = generate_future_return_labels(session, SYMBOL, horizon_hours)
    if labels_df.empty:
        print("❌ Label generation produced empty results")
        return 0
    
    # Labeling.py uses horizon_minutes internally in the Labels model
    save_labels_to_db(session, labels_df, SYMBOL, horizon_hours * 60)
    count = session.query(Labels).count()
    print(f"✅ Label pipeline complete (total={count})")
    return len(labels_df)

def main():
    ts_start = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{'='*60}")
    print(f"  數據收集管線 v1 started {ts_start} UTC")
    print(f"{'='*60}")
    
    cfg = load_config()
    session = init_db(cfg["database"]["url"])
    
    # Pre-check counts
    raw_before = session.query(RawMarketData).count()
    feat_before = session.query(FeaturesNormalized).count()
    labels_before = session.query(Labels).count()
    
    print(f"\n📊 Before: Raw={raw_before}, Features={feat_before}, Labels={labels_before}")
    
    success = True
    
    # Step 1: Collect raw data
    print(f"\n{'─'*40} Step 1: Data Collection {'─'*40}")
    if not collect_raw_data(session):
        print("⚠️  Data collection failed, continuing with existing data")
        success = False
    
    # Step 2: Preprocess features
    print(f"\n{'─'*40} Step 2: Feature Engineering {'─'*40}")
    feat_ok = preprocess_features(session)
    if not feat_ok:
        print("⚠️  Feature engineering failed")
    
    # Step 3: Fix NULL regime labels
    print(f"\n{'─'*40} Step 3: Regime Assignment {'─'*40}")
    updated_regimes = update_regime_labels(session)
    
    # Step 4: Generate labels
    print(f"\n{'─'*40} Step 4: Label Generation {'─'*40}")
    generate_labels(session)
    
    # Post-check counts
    raw_after = session.query(RawMarketData).count()
    feat_after = session.query(FeaturesNormalized).count()
    labels_after = session.query(Labels).count()
    
    def delta_str(after, before):
        if after > before:
            return f"+{after - before}"
        return "持平"
    
    print(f"\n📊 After:  Raw={raw_after} ({delta_str(raw_after, raw_before)}), "
          f"Features={feat_after} ({delta_str(feat_after, feat_before)}), "
          f"Labels={labels_after} ({delta_str(labels_after, labels_before)})")
    
    # Summary
    if raw_after > raw_before:
        print(f"\n✅ 管線恢復：+{raw_after - raw_before} raw, +{feat_after - feat_before} features, "
              f"+{labels_after - labels_before} labels")
    else:
        print(f"\n⚠️  管線未增長 — 可能需要修復源頭")
        
        # Check latest timestamps
        latest_raw = session.query(RawMarketData.timestamp).order_by(RawMarketData.timestamp.desc()).first()
        latest_feat = session.query(FeaturesNormalized.timestamp).order_by(FeaturesNormalized.timestamp.desc()).first()
        print(f"  Latest raw: {latest_raw[0] if latest_raw else 'N/A'}")
        print(f"  Latest feat: {latest_feat[0] if latest_feat else 'N/A'}")
    
    # Regime distribution
    regimes = session.query(
        FeaturesNormalized.regime_label, 
        __import__('sqlalchemy').func.count(FeaturesNormalized.id)
    ).group_by(FeaturesNormalized.regime_label).all()
    print(f"\n🏛️  Regime distribution:")
    for r, c in regimes:
        print(f"  {r or 'NULL'}: {c}")
    
    session.close()
    
    ts_end = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"  數據收集管線 complete {ts_end} UTC")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
