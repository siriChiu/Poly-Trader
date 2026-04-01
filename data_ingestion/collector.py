"""
多感官數據整合收集器 v3
包含 Binance 衍生品數據 (LSR, GSR, Taker, OI)
"""

import sys
from pathlib import Path
_PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import time
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, Dict

from data_ingestion.body_liquidation import get_body_feature
from data_ingestion.tongue_sentiment import get_tongue_feature
from data_ingestion.nose_futures import get_nose_feature
from data_ingestion.eye_binance import get_eye_feature
from data_ingestion.ear_polymarket import get_ear_feature
from data_ingestion.binance_derivatives import get_derivatives_features
from database.models import RawMarketData
from utils.logger import setup_logger

logger = setup_logger(__name__)


def collect_all_senses(symbol: str = "BTCUSDT") -> Optional[Dict]:
    """執行完整多感官數據收集（含衍生品）。"""
    logger.info("開始多感官數據收集 v3...")

    body = get_body_feature() or {}
    tongue = get_tongue_feature() or {}
    nose = get_nose_feature() or {}
    eye = get_eye_feature() or {}
    ear = get_ear_feature() or {}
    time.sleep(0.5)
    derivatives = get_derivatives_features(symbol) or {}

    # Eye
    eye_dist_val = eye.get("feat_eye_up") or eye.get("feat_eye_down")
    # Ear
    ear_prob_val = ear.get("prob")
    # Body
    stablecoin_roc = body.get("raw_roc")
    body_label = body.get("body_label")
    oi_roc = body.get("oi_roc")
    # Tongue
    tongue_sentiment = tongue.get("feat_tongue_sentiment")
    volatility = tongue.get("volatility")

    record = RawMarketData(
        timestamp=datetime.utcnow(),
        symbol=symbol,
        close_price=eye.get("current_price"),
        volume=eye.get("volume"),
        funding_rate=nose.get("funding_rate_raw"),
        fear_greed_index=tongue.get("fear_greed_index"),
        stablecoin_mcap=stablecoin_roc,
        polymarket_prob=ear_prob_val,
        eye_dist=eye_dist_val,
        ear_prob=ear_prob_val,
        tongue_sentiment=tongue_sentiment,
        volatility=volatility,
        oi_roc=oi_roc,
        body_label=body_label,
    )
    
    # Store derivatives in the record as extra attributes (for preprocessor)
    record._derivatives = derivatives
    
    logger.info(
        f"收集完成 v3: price={eye.get('current_price')}, "
        f"LSR={derivatives.get('lsr_ratio')}, GSR={derivatives.get('gsr_ratio')}, "
        f"Taker={derivatives.get('taker_ratio')}, OI={derivatives.get('oi_value')}"
    )
    return record


def run_collection_and_save(session: Session, symbol: str = "BTCUSDT") -> bool:
    """執行收集並保存到資料庫。"""
    try:
        record = collect_all_senses(symbol)
        if record is None:
            logger.error("收集失敗")
            return False
        
        derivatives = getattr(record, '_derivatives', {})
        
        session.add(record)
        session.commit()
        logger.info(f"Raw data 已保存，id={record.id}")

        # NOTE: Feature engineering is handled by trading_cycle after collection.
        # Do not call run_preprocessor here to avoid duplicate computation.
        return True
    except Exception as e:
        session.rollback()
        logger.exception(f"保存 raw data 失敗: {e}")
        return False
