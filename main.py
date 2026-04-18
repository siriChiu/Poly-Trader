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
from data_ingestion.labeling import generate_future_return_labels, save_labels_to_db
from feature_engine.preprocessor import run_preprocessor
from model.predictor import predict
from execution.risk_control import validate_order
from execution.execution_service import ExecutionService
from utils.logger import setup_logger

logger = setup_logger(__name__)


def trading_cycle(session, config: dict, symbol: str, confidence_threshold: float = 0.7):
    """單一交易循環：數據採集 → 特徵工程 → 模型預測 → 風控 → 執行"""
    logger.info(f"=== 開始交易循環 [{datetime.utcnow().isoformat()}] ===")

    collected = run_collection_and_save(session, symbol)
    if not collected:
        logger.warning("本輪數據採集失敗，跳過後續步驟")
        return

    features = run_preprocessor(session, symbol)
    if not features:
        logger.error("特徵計算失敗，本輪跳過")
        return

    try:
        labels_df = generate_future_return_labels(session, symbol=symbol, horizon_hours=24, threshold_pct=0.020)
        if not labels_df.empty:
            save_labels_to_db(session, labels_df, symbol=symbol, horizon_hours=24, force_update_all=True)
            logger.info(f"標籤更新完成: {len(labels_df)} 筆")
    except Exception as e:
        logger.warning(f"標籤更新失敗（非致命）: {e}")

    pred = predict(session)
    if not pred:
        logger.error("預測失敗，本輪跳過")
        return

    confidence = pred["confidence"]
    logger.info(f"預測結果: confidence={confidence:.4f}, signal={pred['signal']}")
    if confidence < confidence_threshold:
        logger.info(f"信心分數 {confidence:.3f} 低於閾值 {confidence_threshold}，觀望不執行")
        return

    execution = ExecutionService(config, db_session=session)
    account_balance = execution.get_account_balance() or 10000.0
    current_price = features.get("current_price", 50000.0)

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

    result = execution.submit_order(
        symbol=order_params["symbol"],
        side=order_params["side"],
        order_type=order_params["order_type"],
        qty=order_params["qty"],
        price=order_params["price"],
        venue=(config.get("execution", {}) or {}).get("venue") or config.get("trading", {}).get("venue"),
        reason=f"heartbeat_signal:{pred.get('signal')}",
        model_confidence=confidence,
    )
    logger.info(f"下單結果: {result}")
    logger.info("=== 交易循環結束 ===\n")


def _job_wrapper(db_url, cfg):
    """P0 #H353 fix: create a fresh session per job to avoid stale session bugs."""
    engine = create_engine(db_url, echo=False, future=True)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        trading_cycle(session, cfg, cfg["trading"]["symbol"], cfg["trading"]["confidence_threshold"])
    except Exception as e:
        logger.error(f"交易循環異常: {e}")
    finally:
        session.close()


def main():
    cfg = load_config()
    db_url = cfg["database"]["url"]
    _ = init_db(db_url)
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=_job_wrapper, args=[db_url, cfg], trigger="interval", minutes=5, id="trading_cycle_job")
    scheduler.start()
    logger.info("Poly-Trader 已啟動，排程：每 5 分鐘執行")

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Poly-Trader 已停止")


if __name__ == "__main__":
    main()
