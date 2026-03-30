"""
五感數據整合收集器
依次調用五感模組，將結果寫入 raw_market_data 表
"""

from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, Dict
import pandas as pd

from data_ingestion.body_defillama import get_body_feature
from data_ingestion.tongue_sentiment import get_tongue_feature
from data_ingestion.nose_futures import get_nose_feature
from data_ingestion.eye_binance import get_eye_feature
from data_ingestion.ear_polymarket import get_ear_feature
from database.models import RawMarketData, init_db
from utils.logger import setup_logger

logger = setup_logger(__name__)

def collect_all_senses(symbol: str = "BTCUSDT") -> Optional[Dict]:
    """
    執行完整的五感數據收集。
    Returns:
        整合後的數據字典，可用於寫入資料庫。
    """
    logger.info("開始五感數據收集...")

    # 分別獲取各感特徵
    body = get_body_feature() or {}
    tongue = get_tongue_feature() or {}
    nose = get_nose_feature() or {}
    eye = get_eye_feature() or {}
    ear = get_ear_feature() or {}

    # 組裝爲 RawMarketData 記錄
    record = RawMarketData(
        timestamp=datetime.utcnow(),
        symbol=symbol,
        close_price=eye.get("current_price"),
        volume=None,  # TODO: 從 eye 模組補充
        funding_rate=nose.get("funding_rate_raw"),
        fear_greed_index=tongue.get("fear_greed_index"),
        stablecoin_mcap=body.get("raw_roc"),  # 注意：這裡存的是 ROC，實際應存市值
        polymarket_prob=ear.get("prob")
    )
    logger.info(f"收集完成: {record.__dict__}")
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

if __name__ == "__main__":
    # 單元測試：初始化 DB 並執行一次收集
    from config import load_config
    cfg = load_config()
    db_url = cfg["database"]["url"]
    Session = init_db(db_url)
    session = Session()
    success = run_collection_and_save(session)
    session.close()
    if success:
        print("[SUCCESS] 数据收集完成")
    else:
        print("[FAIL] 数据收集失败")
