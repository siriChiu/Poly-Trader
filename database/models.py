"""
Database models for Poly-Trader v5 — multi-sense, sell-win aware, SQLite migration tolerant
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, Tuple

from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Text, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class RawEvent(Base):
    __tablename__ = "raw_events"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    source = Column(String, nullable=False, index=True)
    entity = Column(String, nullable=False, index=True)
    subtype = Column(String, nullable=True)
    value = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    quality_score = Column(Float, nullable=True)
    language = Column(String, nullable=True)
    region = Column(String, nullable=True)
    payload_json = Column(Text, nullable=True)
    ingested_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class RawMarketData(Base):
    __tablename__ = "raw_market_data"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    symbol = Column(String, index=True, nullable=False)
    close_price = Column(Float)
    volume = Column(Float)
    funding_rate = Column(Float)
    fear_greed_index = Column(Float)
    stablecoin_mcap = Column(Float)
    polymarket_prob = Column(Float)
    eye_dist = Column(Float, nullable=True)
    ear_prob = Column(Float, nullable=True)
    tongue_sentiment = Column(Float, nullable=True)
    volatility = Column(Float, nullable=True)
    oi_roc = Column(Float, nullable=True)
    body_label = Column(String, nullable=True)


class FeaturesNormalized(Base):
    __tablename__ = "features_normalized"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    symbol = Column(String, nullable=True, index=True)
    feat_eye = Column(Float)
    feat_ear = Column(Float)
    feat_nose = Column(Float)
    feat_tongue = Column(Float)
    feat_body = Column(Float)
    feat_pulse = Column(Float)
    feat_aura = Column(Float)
    feat_mind = Column(Float)
    feat_whisper = Column(Float)
    feat_tone = Column(Float)
    feat_chorus = Column(Float)
    feat_hype = Column(Float)
    feat_oracle = Column(Float)
    feat_shock = Column(Float)
    feat_tide = Column(Float)
    feat_storm = Column(Float)
    regime_label = Column(String, nullable=True)
    feature_version = Column(String, nullable=True)


class TradeHistory(Base):
    __tablename__ = "trade_history"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    action = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    model_confidence = Column(Float, nullable=False)
    pnl = Column(Float, nullable=True)
    gross_pnl = Column(Float, nullable=True)
    commission_slippage = Column(Float, nullable=True)
    reason = Column(String, nullable=True)
    regime_label = Column(String, nullable=True)
    sell_win = Column(Integer, nullable=True)


class Labels(Base):
    __tablename__ = "labels"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    horizon_minutes = Column(Integer, nullable=False)
    future_return_pct = Column(Float)
    future_max_drawdown = Column(Float)
    future_max_runup = Column(Float)
    label_sell_win = Column(Integer)
    label_up = Column(Integer)
    regime_label = Column(String, nullable=True)


_SQLITE_MIGRATIONS: Dict[str, Tuple[Tuple[str, str], ...]] = {
    "features_normalized": (
        ("symbol", "TEXT"),
        ("feat_eye", "REAL"),
        ("feat_ear", "REAL"),
        ("feat_nose", "REAL"),
        ("feat_tongue", "REAL"),
        ("feat_body", "REAL"),
        ("feat_pulse", "REAL"),
        ("feat_aura", "REAL"),
        ("feat_mind", "REAL"),
        ("feat_whisper", "REAL"),
        ("feat_tone", "REAL"),
        ("feat_chorus", "REAL"),
        ("feat_hype", "REAL"),
        ("feat_oracle", "REAL"),
        ("feat_shock", "REAL"),
        ("feat_tide", "REAL"),
        ("feat_storm", "REAL"),
        ("regime_label", "TEXT"),
        ("feature_version", "TEXT"),
    ),
    "trade_history": (
        ("gross_pnl", "REAL"),
        ("commission_slippage", "REAL"),
        ("reason", "TEXT"),
        ("regime_label", "TEXT"),
        ("sell_win", "INTEGER"),
    ),
    "labels": (
        ("horizon_minutes", "INTEGER"),
        ("future_max_drawdown", "REAL"),
        ("future_max_runup", "REAL"),
        ("label_sell_win", "INTEGER"),
        ("label_up", "INTEGER"),
        ("regime_label", "TEXT"),
    ),
    "raw_events": (
        ("source", "TEXT"),
        ("entity", "TEXT"),
        ("subtype", "TEXT"),
        ("value", "REAL"),
        ("confidence", "REAL"),
        ("quality_score", "REAL"),
        ("language", "TEXT"),
        ("region", "TEXT"),
        ("payload_json", "TEXT"),
        ("ingested_at", "DATETIME"),
    ),
}


def _sqlite_add_missing_columns(engine) -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    dialect_name = engine.dialect.name
    if dialect_name != "sqlite":
        return

    with engine.begin() as conn:
        for table, cols in _SQLITE_MIGRATIONS.items():
            if table not in existing_tables:
                continue
            existing_cols = {c["name"] for c in inspector.get_columns(table)}
            for col_name, col_type in cols:
                if col_name in existing_cols:
                    continue
                try:
                    conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {col_name} {col_type}'))
                except Exception:
                    # If a column already exists due to race/partial migration, keep going.
                    pass


def init_db(db_url: str):
    engine = create_engine(db_url, echo=False, future=True)
    Base.metadata.create_all(engine)
    _sqlite_add_missing_columns(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return SessionLocal()
