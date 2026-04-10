"""
Database models for Poly-Trader v5 — multi-sense, sell-win aware, SQLite migration tolerant
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, Tuple

from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Text, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

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
    vix_value = Column(Float, nullable=True)
    dxy_value = Column(Float, nullable=True)
    nq_value = Column(Float, nullable=True)
    claw_liq_ratio = Column(Float, nullable=True)
    claw_liq_total = Column(Float, nullable=True)
    fang_pcr = Column(Float, nullable=True)
    fang_iv_skew = Column(Float, nullable=True)
    fin_etf_netflow = Column(Float, nullable=True)
    fin_etf_trend = Column(Float, nullable=True)
    web_whale_pressure = Column(Float, nullable=True)
    web_large_trades_count = Column(Integer, nullable=True)
    scales_ssr = Column(Float, nullable=True)
    nest_pred = Column(Float, nullable=True)


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
    # P1 #H370: Removed 8 placeholder features (whisper/tone/chorus/hype/oracle/shock/tide/storm)
    # They were NULL/unique=1/stdev=0 across all 8770 rows — pure noise dimensions
    # regime_label, TI features, and valid features remain
    regime_label = Column(String, nullable=True)
    feature_version = Column(String, nullable=True)
    feat_vix = Column(Float, nullable=True)
    feat_dxy = Column(Float, nullable=True)
    # P0 #H161: Technical indicators — IC-validated features
    feat_rsi14 = Column(Float, nullable=True)
    feat_macd_hist = Column(Float, nullable=True)
    feat_atr_pct = Column(Float, nullable=True)
    feat_vwap_dev = Column(Float, nullable=True)
    feat_bb_pct_b = Column(Float, nullable=True)
    feat_nq_return_1h = Column(Float, nullable=True)
    feat_nq_return_24h = Column(Float, nullable=True)
    feat_claw = Column(Float, nullable=True)
    feat_claw_intensity = Column(Float, nullable=True)
    feat_fang_pcr = Column(Float, nullable=True)
    feat_fang_skew = Column(Float, nullable=True)
    feat_fin_netflow = Column(Float, nullable=True)
    feat_web_whale = Column(Float, nullable=True)
    feat_scales_ssr = Column(Float, nullable=True)
    feat_nest_pred = Column(Float, nullable=True)

    # --- 4H timeframe features (support line + bias strategy) ---
    feat_4h_bias50 = Column(Float, nullable=True)       # 4H 乖離率 (價格 vs MA50, %)
    feat_4h_bias20 = Column(Float, nullable=True)       # 4H 乖離率 (價格 vs MA20, %)
    feat_4h_bias200 = Column(Float, nullable=True)      # 4H 乖離率 (價格 vs MA200, %)
    feat_4h_rsi14 = Column(Float, nullable=True)        # 4H RSI 14
    feat_4h_macd_hist = Column(Float, nullable=True)    # 4H MACD histogram
    feat_4h_bb_pct_b = Column(Float, nullable=True)     # 4H Bollinger %B
    feat_4h_dist_bb_lower = Column(Float, nullable=True)  # 4H 距布林下軌距離 (%)
    feat_4h_ma_order = Column(Float, nullable=True)     # 4H MA alignment (+1=多頭/-1=空頭)
    feat_4h_dist_swing_low = Column(Float, nullable=True)  # 4H 距最近 swing low 距離 (%)
    feat_4h_vol_ratio = Column(Float, nullable=True)    # 4H 相對量能 (volume / vol_ma20)

    # --- Backward-compatible aliases for legacy callers/tests ---
    @property
    def feat_eye_dist(self):
        return self.feat_eye

    @feat_eye_dist.setter
    def feat_eye_dist(self, value):
        self.feat_eye = value

    @property
    def feat_ear_zscore(self):
        return self.feat_ear

    @feat_ear_zscore.setter
    def feat_ear_zscore(self, value):
        self.feat_ear = value

    @property
    def feat_nose_sigmoid(self):
        return self.feat_nose

    @feat_nose_sigmoid.setter
    def feat_nose_sigmoid(self, value):
        self.feat_nose = value

    @property
    def feat_tongue_pct(self):
        return self.feat_tongue

    @feat_tongue_pct.setter
    def feat_tongue_pct(self, value):
        self.feat_tongue = value

    @property
    def feat_body_roc(self):
        return self.feat_body

    @feat_body_roc.setter
    def feat_body_roc(self, value):
        self.feat_body = value


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
    # Canonical target for the spot long pyramiding strategy.
    label_spot_long_win = Column(Integer)
    label_spot_long_tp_hit = Column(Integer, nullable=True)
    label_spot_long_quality = Column(Float, nullable=True)
    simulated_pyramid_win = Column(Integer, nullable=True)
    simulated_pyramid_pnl = Column(Float, nullable=True)
    simulated_pyramid_quality = Column(Float, nullable=True)
    # Legacy compatibility fields — kept for older scripts and reports.
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
        ("feat_vix", "REAL"),
        ("feat_dxy", "REAL"),
        ("feat_rsi14", "REAL"),
        ("feat_macd_hist", "REAL"),
        ("feat_atr_pct", "REAL"),
        ("feat_vwap_dev", "REAL"),
        ("feat_bb_pct_b", "REAL"),
        ("feat_nq_return_1h", "REAL"),
        ("feat_nq_return_24h", "REAL"),
        ("feat_claw", "REAL"),
        ("feat_claw_intensity", "REAL"),
        ("feat_fang_pcr", "REAL"),
        ("feat_fang_skew", "REAL"),
        ("feat_fin_netflow", "REAL"),
        ("feat_web_whale", "REAL"),
        ("feat_scales_ssr", "REAL"),
        ("feat_nest_pred", "REAL"),
        # 4H timeframe features
        ("feat_4h_bias50", "REAL"),
        ("feat_4h_bias20", "REAL"),
        ("feat_4h_bias200", "REAL"),
        ("feat_4h_rsi14", "REAL"),
        ("feat_4h_macd_hist", "REAL"),
        ("feat_4h_bb_pct_b", "REAL"),
        ("feat_4h_dist_bb_lower", "REAL"),
        ("feat_4h_ma_order", "REAL"),
        ("feat_4h_dist_swing_low", "REAL"),
        ("feat_4h_vol_ratio", "REAL"),
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
        ("label_spot_long_win", "INTEGER"),
        ("label_spot_long_tp_hit", "INTEGER"),
        ("label_spot_long_quality", "REAL"),
        ("simulated_pyramid_win", "INTEGER"),
        ("simulated_pyramid_pnl", "REAL"),
        ("simulated_pyramid_quality", "REAL"),
        ("label_sell_win", "INTEGER"),
        ("label_up", "INTEGER"),
        ("regime_label", "TEXT"),
    ),
    "raw_market_data": (
        ("vix_value", "REAL"),
        ("dxy_value", "REAL"),
        ("nq_value", "REAL"),
        ("claw_liq_ratio", "REAL"),
        ("claw_liq_total", "REAL"),
        ("fang_pcr", "REAL"),
        ("fang_iv_skew", "REAL"),
        ("fin_etf_netflow", "REAL"),
        ("fin_etf_trend", "REAL"),
        ("web_whale_pressure", "REAL"),
        ("web_large_trades_count", "INTEGER"),
        ("scales_ssr", "REAL"),
        ("nest_pred", "REAL"),
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
