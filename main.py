"""
Poly-Trader 主程式：排程器與閉環執行管線
"""

import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import load_config
from database.models import init_db
from data_ingestion.collector import run_collection_and_save
from feature_engine.preprocessor import run_preprocessor
from model.predictor import predict
from execution.risk_control import validate_order
from execution.order_manager import OrderManager
from utils.logger import setup_logger

logger = setup_logger(__name__)


def trading_cycle(session, config: dict, symbol: str, confidence_threshold: float = 0.7):
    """
    單一交易循環：數據採集 → 特徵工程 → 模型預測 → 風控 → 執行
    """
    logger.info(f"=== 開始交易循環 [{datetime.utcnow().isoformat()}] ===")

    # Step 1: 數據採集（多感官收集並寫入 raw_market_data）
    collected = run_collection_and_save(session, symbol)
    if not collected:
        logger.warning("本輪數據採集失敗，跳過後續步驟")
        return

    # Step 2: 特徵工程
    features = run_preprocessor(session, symbol)
    if not features:
        logger.error("特徵計算失敗，本輪跳過")
        return

    # Step 3: 模型預測
    pred = predict(session)
    if not pred:
        logger.error("預測失敗，本輪跳過")
        return

    confidence = pred["confidence"]
    logger.info(f"預測結果: confidence={confidence:.4f}, signal={pred['signal']}")

    # Step 4: 信心分數檢查
    if confidence < confidence_threshold:
        logger.info(
            f"信心分數 {confidence:.3f} 低於閾值 {confidence_threshold}，觀望不執行"
        )
        return

    # Step 5: 風控檢查
    current_price = features.get("current_price", 50000.0)
    account_balance = 10000.0  # TODO: 從交易所 API 獲取

    order_params = validate_order(
        symbol=symbol,
        amount=0.0,
        price=current_price,
        balance=account_balance,
        confidence=confidence,
        config=config,
    )
    if not order_params:
        logger.warning("風險檢查未通過，不執行下單")
        return

    # Step 6: 執行下單
    om = OrderManager(config, session)
    result = om.place_order(
        symbol=order_params["symbol"],
        side=order_params["side"],
        order_type=order_params["order_type"],
        qty=order_params["qty"],
        price=order_params["price"],
        stop_loss_pct=order_params["stop_loss_pct"],
    )
    if result:
        logger.info(f"下單結果: id={result.get('id')}, status={result.get('status')}")
    else:
        logger.error("下單失敗")

    logger.info("=== 交易循環結束 ===\n")


def main():
    cfg = load_config()
    db_url = cfg["database"]["url"]

    # 初始化 DB
    SessionLocal = init_db(db_url)
    session = SessionLocal

    # 排程器：每 5 分鐘執行（提高數據收集頻率）
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=lambda: trading_cycle(
            session,
            cfg,
            cfg["trading"]["symbol"],
            cfg["trading"]["confidence_threshold"],
        ),
        trigger="interval",
        minutes=5,
        id="trading_cycle_job",
    )
    scheduler.start()
    logger.info("Poly-Trader 已啟動，排程：每 5 分鐘執行")

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        session.close()
        logger.info("Poly-Trader 已停止")


if __name__ == "__main__":
    main()
