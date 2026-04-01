"""
Database models for Poly-Trader
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
    eye_dist = Column(Float, nullable=True)   # Eye 原始：價格與阻力/支撐距離
    ear_prob = Column(Float, nullable=True)   # Ear 原始：預測市場概率


class FeaturesNormalized(Base):
    """正規化特徵表"""
    __tablename__ = "features_normalized"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    feat_eye_dist = Column(Float)      # 眼：價格距離痛點比例
    feat_ear_zscore = Column(Float)    # 耳：市場共識 Z-score
    feat_nose_sigmoid = Column(Float)  # 鼻：資金費率 Sigmoid 壓縮
    feat_tongue_pct = Column(Float)    # 舌：情緒指數百分比
    feat_body_roc = Column(Float)
    feat_pulse = Column(Float)       # 脈: 波動率 z-score
    feat_aura = Column(Float)        # 磁: funding/OI 背離
    feat_mind = Column(Float)        # 知: BTC/ETH 成交量比      # 身：資金增長率


class TradeHistory(Base):
    """交易歷史表"""
    __tablename__ = "trade_history"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    action = Column(String, nullable=False)  # BUY / SELL
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
    label = Column(Integer)  # 1=上漲, 0=下跌


def init_db(db_url: str):
    """
    初始化資料庫並建立所有 tables。
    返回 Session 工廠。
    """
    engine = create_engine(db_url, echo=False, future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return SessionLocal()
