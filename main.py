"""
Poly-Trader 主程式：排程器與閉環執行管線
"""

import time
import yaml
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import init_db
from feature_engine.preprocessor import run_preprocessor
from model.predictor import predict, DummyPredictor
from execution.risk_control import validate_order
from execution.order_manager import OrderManager, run_order_manager
from utils.logger import setup_logger

logger = setup_logger(__name__)

def load_config(config_path: str = None) -> dict:
    from config import load_config as _load
    return _load(config_path)

def trading_cycle(
    session,
    config: dict,
    symbol: str,
    confidence_threshold: float = 0.7
):
    """
    單一交易循環：數據採集 -> 特徵 -> 預測 -> 執行
    此處簡化：假設五感模組已將結果寫入 raw_market_data 表。
    """
    logger.info(f"=== 開始交易循環 [{datetime.utcnow().isoformat()}] ===")

    # 1. 特徵工程
    features = run_preprocessor(session, symbol)
    if not features:
        logger.error("特徵計算失敗，本輪跳過")
        return

    # 2. 模型預測
    pred = predict(session)
    if not pred:
        logger.error("預測失敗，本輪跳過")
        return
    confidence = pred["confidence"]

    # 3. 風險檢查與下單
    if confidence < confidence_threshold:
        logger.info(f"信心分數 {confidence:.3f} 低於閾值 {confidence_threshold}，不執行下單")
        return

    # 獲取當前價格（模擬：從特徵或 mercado 取，暫時用固定值）
    current_price = features.get("current_price")  # Eye模組會提供
    if current_price is None:
        # 若無，則 placeholder
        current_price = 50000.0

    # 檢查可下單部位
    account_balance = 10000.0  # placeholder：需從交易所 API 獲取
    order_params = validate_order(
        symbol=symbol,
        amount=0.0,  # 由 risk_control 自行計算
        price=current_price,
        balance=account_balance,
        confidence=confidence,
        config=config
    )
    if not order_params:
        logger.warning("風險檢查未通過，不執行下單")
        return

    # 4. 執行下單
    result = run_order_manager(
        config=config,
        db_session=session,
        symbol=symbol,
        side=order_params["side"],
        qty=order_params["qty"],
        price=order_params["price"],
        confidence=confidence,
        stop_loss_pct=order_params["stop_loss_pct"]
    )
    if result:
        logger.info(f"下單結果: {result}")
    else:
        logger.error("下單失敗")

    logger.info("=== 交易循環結束 ===\n")

def main():
    cfg = load_config()
    db_url = cfg["database"]["url"]

    # 初始化 DB session
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    # 排程器：每小時的第 01 分執行
    scheduler = BackgroundScheduler()
    interval_minutes = 60
    scheduler.add_job(
        func=lambda: trading_cycle(session, cfg, cfg["trading"]["symbol"], cfg["trading"]["confidence_threshold"]),
        trigger='cron',
        minute='1',
        id='trading_cycle_job'
    )
    scheduler.start()
    logger.info(f"Poly-Trader 主程式已啟動，排程：每小時第 1 分執行一次")

    try:
        # 保持主執行緒存活
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        session.close()
        logger.info("Poly-Trader 已停止")

if __name__ == "__main__":
    main()
