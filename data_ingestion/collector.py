"""
五感數據整合收集器
依次調用五感模組，將結果寫入 raw_market_data 表
"""

from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, Dict

from data_ingestion.body_liquidation import get_body_feature
from data_ingestion.tongue_sentiment import get_tongue_feature
from data_ingestion.nose_futures import get_nose_feature
from data_ingestion.eye_binance import get_eye_feature
from data_ingestion.ear_polymarket import get_ear_feature
from database.models import RawMarketData
from utils.logger import setup_logger

logger = setup_logger(__name__)


def collect_all_senses(symbol: str = "BTCUSDT") -> Optional[Dict]:
    """
    執行完整的五感數據收集。
    Returns:
        整合後的數據字典，可用於寫入資料庫。
    """
    logger.info("開始五感數據收集...")

    body = get_body_feature() or {}
    tongue = get_tongue_feature() or {}
    nose = get_nose_feature() or {}
    eye = get_eye_feature() or {}
    ear = get_ear_feature() or {}

    # Eye: 取 feat_eye_up 或 feat_eye_down 作為 eye_dist
    eye_dist_val = eye.get("feat_eye_up") or eye.get("feat_eye_down")

    # Ear: 取 prob
    ear_prob_val = ear.get("prob")

    # Body: stablecoin_mcap 存原始 ROC（注意：非市值，而是變化率）
    stablecoin_roc = body.get("raw_roc")

    record = RawMarketData(
        timestamp=datetime.utcnow(),
        symbol=symbol,
        close_price=eye.get("current_price"),
        volume=None,
        funding_rate=nose.get("funding_rate_raw"),
        fear_greed_index=tongue.get("fear_greed_index"),
        stablecoin_mcap=stablecoin_roc,
        polymarket_prob=ear_prob_val,
        eye_dist=eye_dist_val,
        ear_prob=ear_prob_val,
    )
    logger.info(
        f"收集完成: price={eye.get('current_price')}, "
        f"eye_dist={eye_dist_val}, ear_prob={ear_prob_val}, "
        f"funding={nose.get('funding_rate_raw')}, "
        f"fng={tongue.get('fear_greed_index')}, "
        f"body_roc={stablecoin_roc}"
    )
    return record


def run_collection_and_save(session: Session, symbol: str = "BTCUSDT") -> bool:
    """
    執行收集並保存到資料庫。
    """
    try:
        record = collect_all_senses(symbol)
        if record is None:
            logger.error("收集失敗，無數據")
            return False
        session.add(record)
        session.commit()
        logger.info(f"Raw data 已保存，id={record.id}")
        return True
    except Exception as e:
        session.rollback()
        logger.exception(f"保存 raw data 失敗: {e}")
        return False
