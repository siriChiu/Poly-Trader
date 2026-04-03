# -*- coding: utf-8 -*-
"""
Backfill v4 features — uses the live preprocessor to recompute ALL features.
Covers all 16 v4 feature columns in FeaturesNormalized.
"""
from __future__ import annotations
import sys, os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from datetime import datetime
import pandas as pd
from database.models import RawMarketData, FeaturesNormalized
from feature_engine.preprocessor import compute_features_from_raw
from server.dependencies import get_db

SYMBOL = "BTCUSDT"
BATCH = 1000
MIN_W = 10

FEAT_COLS = [
    "feat_eye", "feat_ear", "feat_nose", "feat_tongue", "feat_body",
    "feat_pulse", "feat_aura", "feat_mind",
    "feat_whisper", "feat_tone", "feat_chorus", "feat_hype",
    "feat_oracle", "feat_shock", "feat_tide", "feat_storm",
]


def load_raw_df(session):
    rows = (
        session.query(RawMarketData)
        .filter(RawMarketData.symbol == SYMBOL)
        .order_by(RawMarketData.timestamp.asc())
        .all()
    )
    if not rows:
        return pd.DataFrame()
    data = []
    for r in rows:
        data.append({
            "timestamp": r.timestamp,
            "symbol": r.symbol or SYMBOL,
            "close_price": r.close_price,
            "volume": r.volume,
            "funding_rate": r.funding_rate,
            "fear_greed_index": r.fear_greed_index,
            "stablecoin_mcap": r.stablecoin_mcap,
            "polymarket_prob": r.polymarket_prob,
        })
    return pd.DataFrame(data)


def main():
    print(f"\n{'='*60}")
    print(f"  Backfill v4  [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
    print(f"{'='*60}")

    session = get_db()
    df = load_raw_df(session)
    total = len(df)
    print(f"Raw records: {total}")
    if total < MIN_W:
        print("Insufficient data, skip")
        return

    saved = 0
    updated = 0
    batch = 0

    print(f"Backfilling {total - MIN_W + 1} rows...\n")

    for end_idx in range(MIN_W, total + 1):
        window = df.iloc[:end_idx]
        ts = window.iloc[-1]["timestamp"]

        feat = compute_features_from_raw(window)
        if not feat:
            continue

        existing = (
            session.query(FeaturesNormalized)
            .filter(FeaturesNormalized.timestamp == ts, FeaturesNormalized.symbol == SYMBOL)
            .first()
        )

        if existing:
            for k in FEAT_COLS:
                if feat.get(k) is not None:
                    setattr(existing, k, feat[k])
            existing.feature_version = feat.get("feature_version")
            existing.regime_label = feat.get("regime_label")
            updated += 1
        else:
            record = FeaturesNormalized(
                timestamp=ts,
                symbol=SYMBOL,
                **{k: feat.get(k) for k in FEAT_COLS},
                feature_version=feat.get("feature_version"),
                regime_label=feat.get("regime_label"),
            )
            session.add(record)
            saved += 1

        batch += 1
        if batch % BATCH == 0:
            session.commit()
            pct = end_idx / total * 100
            print(f"  {end_idx}/{total} ({pct:.0f}%) | new={saved} upd={updated}")

    session.commit()
    final_count = session.query(FeaturesNormalized).count()

    print(f"\n{'='*60}")
    print(f"  Complete! new={saved}, updated={updated}, total={final_count}")

    # Show latest row
    last = (
        session.query(FeaturesNormalized)
        .order_by(FeaturesNormalized.timestamp.desc())
        .first()
    )
    if last:
        print(f"\n  Latest (ts={last.timestamp}):")
        for k in FEAT_COLS:
            v = getattr(last, k, None)
            if v is not None:
                print(f"    {k}: {v:.6f}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
