"""
Database models for Poly-Trader v3 — IC-validated features
"""

from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import Optional

Base = declarative_base()


class RawMarketData(Base):
    """原始市場數據表"""
    __tablename__ = "raw_market_data"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
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
    """正規化特徵表 (v3 — IC-validated features)
    
    8 個感官，每個對應一個 IC-validated 特徵：
    1. Eye:   feat_eye_dist     — 72h funding MA (IC=-0.172) 反向
    2. Ear:   feat_ear_zscore   — 48h momentum (IC=-0.094) 反向
    3. Nose:  feat_nose_sigmoid — 48h autocorrelation (IC=-0.071) 反向
    4. Tongue: feat_tongue_pct  — 24h volatility (IC=-0.056) 反向
    5. Body:  feat_body_roc     — 24h range position (IC=+0.024)
    6. Pulse: feat_pulse        — funding trend (IC=-0.067) 反向
    7. Aura:  feat_aura         — vol×autocorr interaction (IC=-0.061)
    8. Mind:  feat_mind         — 24h funding z-score (IC=+0.062)
    """
    __tablename__ = "features_normalized"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    feat_eye_dist = Column(Float)      # funding_ma72 (IC=-0.172)
    feat_ear_zscore = Column(Float)    # momentum_48h (IC=-0.094)
    feat_nose_sigmoid = Column(Float)  # autocorr_48h (IC=-0.071)
    feat_tongue_pct = Column(Float)    # volatility_24h (IC=-0.056)
    feat_body_roc = Column(Float)      # range_pos_24h (IC=+0.024)
    feat_pulse = Column(Float)         # funding_trend (IC=-0.067)
    feat_aura = Column(Float)          # vol×autocorr (IC=-0.061)
    feat_mind = Column(Float)          # funding_z_24 (IC=+0.062)


class TradeHistory(Base):
    """交易歷史表"""
    __tablename__ = "trade_history"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    action = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    model_confidence = Column(Float, nullable=False)
    pnl = Column(Float, nullable=True)


class Labels(Base):
    """未來收益率標籤表"""
    __tablename__ = "labels"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    symbol = Column(String, nullable=False)
    horizon_hours = Column(Integer, nullable=False)
    future_return_pct = Column(Float)
    label = Column(Integer)


def init_db(db_url: str):
    engine = create_engine(db_url, echo=False, future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return SessionLocal()
