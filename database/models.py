"""
Database models for Poly-Trader v4 — multi-sense, sell-win aware
"""

from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

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
    symbol = Column(String, nullable=False, index=True)
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


def init_db(db_url: str):
    engine = create_engine(db_url, echo=False, future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return SessionLocal()
