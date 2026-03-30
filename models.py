from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import Optional

Base = declarative_base()

class RawMarketData(Base):
    """原始市場數據表（包含五感原始輸出）"""
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
    # 新增：Eye/Ear 原始數據（供 preprocessor 計算特徵）
    eye_dist = Column(Float, nullable=True)   # eye: (resistance - price)/price 或 (price - support)/price (負數)
    ear_prob = Column(Float, nullable=True)   # ear: Polymarket 概率

class FeaturesNormalized(Base):
    """正規化特徵表"""
    __tablename__ = "features_normalized"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    feat_eye_dist = Column(Float)      # 眼：價格距離痛點比例
    feat_ear_zscore = Column(Float)    # 耳：市場共識 Z-score
    feat_nose_sigmoid = Column(Float)  # 鼻：資金費率 Sigmoid 壓縮
    feat_tongue_pct = Column(Float)    # 舌情緒指数百分比
    feat_body_roc = Column(Float)      # 身：資金增長率

class TradeHistory(Base):
    """交易歷史表"""
    __tablename__ = "trade_history"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    action = Column(String, nullable=False)  # BUY / SELL
    price = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    model_confidence = Column(Float, nullable=False)
    pnl = Column(Float, nullable=True)  # 損益，可後續更新

class Labels(Base):
    """標籤表：與 features_normalized 一一對應（by timestamp）"""
    __tablename__ = "labels"

    id = Column(Integer, primary_key=True)
    feature_timestamp = Column(DateTime, nullable=False, unique=True)  # 對應 features_normalized.timestamp
    label = Column(Integer, nullable=False)  # 0 或 1
    future_return_pct = Column(Float, nullable=False)

def init_db(db_url: str):
    """
    初始化資料庫並建立所有 tables。
    返回 Session 物件供後續使用。
    """
    from sqlalchemy import create_engine
    engine = create_engine(db_url, echo=False, future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return Session()
