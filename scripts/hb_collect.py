#!/usr/bin/env python3
"""Heartbeat Step 0 — 數據收集管線 v1.

Called at the start of every heartbeat BEFORE analysis.
Collects fresh market data from Binance + external sources,
runs the preprocessor to compute features, and generates labels.

Usage: python scripts/hb_collect.py
"""
import json, os, sys, logging
from datetime import datetime
from typing import Any, Dict, List

PROJECT = "/home/kazuha/Poly-Trader"
sys.path.insert(0, PROJECT)
os.chdir(PROJECT)

PYTHON = os.path.join(PROJECT, "venv", "bin", "python")
os.environ["PYTHONPATH"] = PROJECT

from config import load_config
from database.models import RawMarketData, FeaturesNormalized, Labels, init_db

SYMBOL = "BTCUSDT"
ACTIVE_HEARTBEAT_HORIZONS = {240, 1440}


def _coerce_dt(value):
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _max_raw_gap_hours_since(session, since_ts: datetime | None, symbol: str = SYMBOL) -> float | None:
    if since_ts is None:
        return None
    raw_rows = (
        session.query(RawMarketData.timestamp)
        .filter(RawMarketData.symbol == symbol, RawMarketData.timestamp >= since_ts)
        .order_by(RawMarketData.timestamp)
        .all()
    )
    if not raw_rows:
        return None
    max_gap = 0.0
    prev_ts = since_ts
    for (raw_ts,) in raw_rows:
        current_ts = _coerce_dt(raw_ts)
        if current_ts is None or prev_ts is None:
            continue
        max_gap = max(max_gap, (current_ts - prev_ts).total_seconds() / 3600)
        prev_ts = current_ts
    return round(max_gap, 2)


def summarize_label_horizons(
    session,
    symbol: str = SYMBOL,
    active_horizons: set[int] | None = None,
) -> List[Dict[str, Any]]:
    """Return per-horizon label freshness so active-vs-legacy horizons are not conflated.

    240m and 1440m are the heartbeat-maintained horizons. Older legacy horizons may still
    exist in the DB for diagnostics, but should not be surfaced as active pipeline blockers.
    """
    active_horizons = set(active_horizons or ACTIVE_HEARTBEAT_HORIZONS)
    latest_raw = session.query(RawMarketData.timestamp).filter(
        RawMarketData.symbol == symbol
    ).order_by(RawMarketData.timestamp.desc()).first()
    latest_raw_ts = _coerce_dt(latest_raw[0]) if latest_raw else None

    rows = session.execute(
        __import__('sqlalchemy').text(
            """
            SELECT horizon_minutes,
                   COUNT(*) AS total_rows,
                   SUM(CASE WHEN simulated_pyramid_win IS NOT NULL THEN 1 ELSE 0 END) AS target_rows,
                   MAX(CASE WHEN simulated_pyramid_win IS NOT NULL THEN timestamp END) AS latest_target_ts
            FROM labels
            WHERE symbol = :symbol
            GROUP BY horizon_minutes
            ORDER BY horizon_minutes
            """
        ),
        {"symbol": symbol},
    ).fetchall()

    summary = []
    for horizon_minutes, total_rows, target_rows, latest_target_ts in rows:
        horizon_minutes = int(horizon_minutes)
        latest_target_dt = _coerce_dt(latest_target_ts)
        lag_hours = None
        raw_gap_hours = _max_raw_gap_hours_since(session, latest_target_dt, symbol)
        freshness = "no_targets"
        expected_horizon_hours = horizon_minutes / 60.0
        tolerance_hours = max(2.0, expected_horizon_hours * 0.25)
        if latest_raw_ts and latest_target_dt:
            lag_hours = round((latest_raw_ts - latest_target_dt).total_seconds() / 3600, 2)
            freshness = "expected_horizon_lag" if lag_hours <= expected_horizon_hours + tolerance_hours else "stale"
            if (
                freshness == "stale"
                and horizon_minutes in active_horizons
                and raw_gap_hours is not None
                and raw_gap_hours > expected_horizon_hours + tolerance_hours
            ):
                freshness = "raw_gap_blocked"
        if horizon_minutes not in active_horizons:
            freshness = "inactive_horizon"
        summary.append(
            {
                "horizon_minutes": horizon_minutes,
                "total_rows": int(total_rows or 0),
                "target_rows": int(target_rows or 0),
                "latest_target_ts": latest_target_dt.isoformat(sep=' ') if latest_target_dt else None,
                "lag_hours_vs_raw": lag_hours,
                "latest_raw_gap_hours": raw_gap_hours,
                "freshness": freshness,
                "is_active": horizon_minutes in active_horizons,
            }
        )
    return summary


def print_label_horizon_summary(session, symbol: str = SYMBOL) -> None:
    print("\n🏷️  Label horizon freshness:")
    for row in summarize_label_horizons(session, symbol):
        lag = row["lag_hours_vs_raw"]
        lag_str = "n/a" if lag is None else f"{lag:.1f}h"
        raw_gap = row.get("latest_raw_gap_hours")
        raw_gap_str = "n/a" if raw_gap is None else f"{raw_gap:.1f}h"
        note = {
            "expected_horizon_lag": "expected due to lookahead horizon",
            "stale": "STALE — investigate collect/label pipeline",
            "raw_gap_blocked": "STALE — upstream raw gap exceeds this horizon; label path is blocked by missing raw continuity",
            "no_targets": "no non-null targets yet",
            "inactive_horizon": "legacy horizon present in DB but not maintained by heartbeat",
        }[row["freshness"]]
        print(
            f"  h={row['horizon_minutes']:>4}m | rows={row['total_rows']:<6} "
            f"target_rows={row['target_rows']:<6} latest_target={row['latest_target_ts'] or 'N/A'} "
            f"lag_vs_raw={lag_str} raw_gap={raw_gap_str} | {note}"
        )


def collect_raw_data(session):
    """Step 1: Collect fresh raw data from all sources."""
    from data_ingestion.collector import repair_recent_raw_continuity, run_collection_and_save

    repair_meta = repair_recent_raw_continuity(session, SYMBOL, return_details=True)
    repaired = int(repair_meta.get("inserted_total", 0))
    print(f"CONTINUITY_REPAIR_META: {json.dumps(repair_meta, ensure_ascii=False, sort_keys=True)}")
    if repaired:
        print(
            "🩹 Recent raw continuity repair inserted "
            f"{repaired} Binance continuity rows before live collect "
            f"(4h={repair_meta.get('coarse_inserted', 0)}, "
            f"1h={repair_meta.get('fine_inserted', 0)}, "
            f"bridge={repair_meta.get('bridge_inserted', 0)})"
        )
    if repair_meta.get("used_bridge"):
        print("⚠️  Interpolated bridge fallback was required to keep recent raw continuity alive")

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
    """Step 2: Compute features from ALL raw data (including continuity repairs)."""
    from feature_engine.preprocessor import backfill_missing_feature_rows, run_preprocessor

    result = run_preprocessor(session, SYMBOL)
    repaired = backfill_missing_feature_rows(session, SYMBOL)
    if repaired:
        print(f"🩹 Backfilled {repaired} missing feature rows from repaired raw continuity")
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

def generate_labels(session, horizon_hours=(4, 24)):
    """Step 4: Generate labels for the active heartbeat horizons.

    24h is the canonical heartbeat target used by IC/model scripts.
    4h is retained for legacy/diagnostic workflows.
    """
    from data_ingestion.labeling import generate_future_return_labels, save_labels_to_db

    if isinstance(horizon_hours, int):
        horizons = [horizon_hours]
    else:
        horizons = list(horizon_hours)

    total_generated = 0
    for horizon in horizons:
        labels_df = generate_future_return_labels(session, SYMBOL, horizon)
        if labels_df.empty:
            print(f"⚠️  Label generation produced empty results for horizon={horizon}h")
            continue

        # save_labels_to_db expects horizon_hours and converts to horizon_minutes internally.
        # Passing horizon_hours * 60 here created bogus 14400-minute labels from a 4-hour job.
        before = session.query(Labels).filter(Labels.horizon_minutes == horizon * 60).count()
        save_labels_to_db(session, labels_df, SYMBOL, horizon)
        after = session.query(Labels).filter(Labels.horizon_minutes == horizon * 60).count()
        total_generated += len(labels_df)
        print(
            f"✅ Label horizon {horizon}h complete "
            f"(generated={len(labels_df)}, db_rows={after}, delta={after - before:+d})"
        )

    count = session.query(Labels).count()
    print(f"✅ Label pipeline complete (total={count})")
    return total_generated

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

    print_label_horizon_summary(session)
    
    session.close()
    
    ts_end = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"  數據收集管線 complete {ts_end} UTC")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
