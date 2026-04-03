#!/usr/bin/env python3
"""Heartbeat #105 diagnostic: DB state, feature analysis"""
import sys, os
sys.path.insert(0, '/home/kazuha/Poly-Trader')

from database.models import init_db, FeaturesNormalized, Labels, RawMarketData
from sqlalchemy import inspect, asc, func, distinct

engine_url = "sqlite:////home/kazuha/Poly-Trader/poly_trader.db"
session = init_db(engine_url)

# Table names
tables = inspect(session.get_bind()).get_table_names()
print(f"Tables: {tables}")

# Counts
for cls in [RawMarketData, FeaturesNormalized, Labels]:
    cnt = session.query(cls).count()
    print(f"{cls.__tablename__}: {cnt}")

# Latest raw data 
raw_count = session.query(RawMarketData).count()
if raw_count > 0:
    oldest_raw = session.query(RawMarketData).order_by(asc(RawMarketData.timestamp)).first()
    newest_raw = session.query(RawMarketData).order_by(asc(RawMarketData.timestamp)).offset(raw_count-1).limit(1).first()
    print(f"\n=== MARKET STATE ===")
    if oldest_raw:
        print(f"  Oldest: ts={oldest_raw.timestamp}, close={oldest_raw.close_price}")
    if newest_raw:
        print(f"  Newest: ts={newest_raw.timestamp}, close={newest_raw.close_price}")
        print(f"  symbol={newest_raw.symbol}, vol={newest_raw.volume}")
        print(f"  funding={newest_raw.funding_rate}, fng={newest_raw.fear_greed_index}")
        print(f"  polymarket={newest_raw.polymarket_prob}")

# Label distribution
print("\n=== LABEL DISTRIBUTION ===")
for row in session.query(Labels.label_up, func.count()).group_by(Labels.label_up).all():
    print(f"  label_up={row[0]}: {row[1]} samples")

# Aura: check unique values
print("\n=== AURA (distinct values) ===")
all_aura_rows = session.query(FeaturesNormalized.feat_aura).all()
unique_aura = set()
for r in all_aura_rows:
    if r[0] is not None:
        unique_aura.add(r[0])
print(f"  Unique values: {sorted(unique_aura)[:20]}")
for val in sorted(unique_aura)[:10]:
    cnt = session.query(FeaturesNormalized).filter(FeaturesNormalized.feat_aura == val).count()
    print(f"    aura={val}: {cnt} samples")

# Check what funding_rate values look like (for Aura = fr_abs_norm)
print("\n=== FUNDING RATE STATS ===")
fr_stats = session.query(
    func.min(RawMarketData.funding_rate),
    func.max(RawMarketData.funding_rate),
    func.avg(RawMarketData.funding_rate),
    func.count(RawMarketData.funding_rate)
).filter(RawMarketData.funding_rate.isnot(None)).first()
if fr_stats:
    print(f"  min={fr_stats[0]}, max={fr_stats[1]}, avg={fr_stats[2]}, count={fr_stats[3]}")

# Check raw columns
print("\n=== RAW COLUMNS ===")
for col in inspect(session.get_bind()).get_columns('raw_market_data'):
    print(f"  {col['name']} ({col['type']})")

# Features: check a few recent rows
print("\n=== RECENT FEATURES (last 3) ===")
feat_count = session.query(FeaturesNormalized).count()
recent_feats = session.query(FeaturesNormalized).order_by(asc(FeaturesNormalized.timestamp)).offset(max(0, feat_count-3)).all()
for r in recent_feats:
    print(f"  ts={r.timestamp}")
    print(f"    eye={r.feat_eye:.4f} ear={r.feat_ear:.4f} nose={r.feat_nose:.4f} tongue={r.feat_tongue:.4f}")
    print(f"    body={r.feat_body:.4f} pulse={r.feat_pulse:.4f} aura={r.feat_aura:.4f} mind={r.feat_mind:.4f}")

session.close()
