#!/usr/bin/env python3
"""P0/P1 repair utility for Poly-Trader.

Actions:
1. Backfill NULL feature symbols to the trading symbol.
2. Deduplicate features on (timestamp, symbol), keeping the newest row.
3. Regenerate 24h labels with the new path-aware spot-long definition.
4. Print a compact quality report.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import load_config
from database.models import FeaturesNormalized, Labels, RawMarketData, init_db
from data_ingestion.labeling import generate_future_return_labels, save_labels_to_db


def backfill_feature_symbols(session, symbol: str) -> int:
    rows = (
        session.query(FeaturesNormalized)
        .filter(FeaturesNormalized.symbol.is_(None))
        .order_by(FeaturesNormalized.timestamp)
        .all()
    )
    count = 0
    for row in rows:
        row.symbol = symbol
        count += 1
    session.commit()
    return count


def dedupe_features(session, symbol: str) -> int:
    rows = (
        session.query(FeaturesNormalized)
        .filter(FeaturesNormalized.symbol == symbol)
        .order_by(FeaturesNormalized.timestamp.asc(), FeaturesNormalized.id.asc())
        .all()
    )
    buckets = defaultdict(list)
    for row in rows:
        buckets[(row.timestamp, row.symbol)].append(row)

    deleted = 0
    for _, dup_rows in buckets.items():
        if len(dup_rows) <= 1:
            continue
        keep = dup_rows[-1]
        for row in dup_rows[:-1]:
            if row.id == keep.id:
                continue
            session.delete(row)
            deleted += 1
    session.commit()
    return deleted


def quality_report(session, symbol: str) -> dict:
    raw_count = session.query(RawMarketData).filter(RawMarketData.symbol == symbol).count()
    feat_count = session.query(FeaturesNormalized).filter(FeaturesNormalized.symbol == symbol).count()
    null_symbol_count = session.query(FeaturesNormalized).filter(FeaturesNormalized.symbol.is_(None)).count()
    label_count = (
        session.query(Labels)
        .filter(Labels.symbol == symbol, Labels.horizon_minutes == 1440)
        .count()
    )
    positive_count = (
        session.query(Labels)
        .filter(Labels.symbol == symbol, Labels.horizon_minutes == 1440, Labels.label_spot_long_win == 1)
        .count()
    )
    simulated_win_count = (
        session.query(Labels)
        .filter(Labels.symbol == symbol, Labels.horizon_minutes == 1440, Labels.simulated_pyramid_win == 1)
        .count()
    )
    simulated_quality_avg = session.query(Labels.simulated_pyramid_quality).filter(
        Labels.symbol == symbol,
        Labels.horizon_minutes == 1440,
        Labels.simulated_pyramid_quality.isnot(None),
    ).all()
    latest_raw = (
        session.query(RawMarketData.timestamp)
        .filter(RawMarketData.symbol == symbol)
        .order_by(RawMarketData.timestamp.desc())
        .first()
    )
    latest_feat = (
        session.query(FeaturesNormalized.timestamp)
        .filter(FeaturesNormalized.symbol == symbol)
        .order_by(FeaturesNormalized.timestamp.desc())
        .first()
    )
    latest_label = (
        session.query(Labels.timestamp)
        .filter(Labels.symbol == symbol, Labels.horizon_minutes == 1440, Labels.future_return_pct.isnot(None))
        .order_by(Labels.timestamp.desc())
        .first()
    )
    sim_quality_values = [row[0] for row in simulated_quality_avg if row[0] is not None]
    return {
        "raw": raw_count,
        "features": feat_count,
        "labels": label_count,
        "positive_ratio": round(positive_count / label_count, 4) if label_count else None,
        "simulated_win_ratio": round(simulated_win_count / label_count, 4) if label_count else None,
        "simulated_quality_avg": round(sum(sim_quality_values) / len(sim_quality_values), 4) if sim_quality_values else None,
        "null_feature_symbol": null_symbol_count,
        "latest_raw": str(latest_raw[0]) if latest_raw else None,
        "latest_feature": str(latest_feat[0]) if latest_feat else None,
        "latest_label": str(latest_label[0]) if latest_label else None,
    }


def main() -> int:
    cfg = load_config()
    symbol = cfg["trading"].get("symbol", "BTCUSDT")
    session = init_db(cfg["database"]["url"])
    try:
        print(f"[P0] Backfilling NULL feature symbols -> {symbol}")
        backfilled = backfill_feature_symbols(session, symbol)
        print(f"  backfilled: {backfilled}")

        print("[P0] Deduplicating features on (timestamp, symbol)")
        deleted = dedupe_features(session, symbol)
        print(f"  deleted duplicates: {deleted}")

        print("[P1] Regenerating 24h path-aware labels")
        labels_df = generate_future_return_labels(session, symbol=symbol, horizon_hours=24)
        save_labels_to_db(session, labels_df, symbol=symbol, horizon_hours=24, force_update_all=True)
        print(f"  regenerated labels: {len(labels_df)}")

        report = quality_report(session, symbol)
        print("[REPORT]")
        for key, value in report.items():
            print(f"  {key}: {value}")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
