"""
訂單管理模組：使用 CCXT 與交易所交互，支援 Dry Run 模式
"""

import ccxt
import time
from typing import Optional, Dict
from sqlalchemy.orm import Session
from database.models import TradeHistory, init_db
from utils.logger import setup_logger

logger = setup_logger(__name__)

class OrderManager:
    def __init__(self, config: Dict, db_session: Session):
        """
        config: 包含 exchange credentials 與 trading 配置
        db_session: SQLAlchemy Session
        """
        self.config = config
        self.session = db_session
        self.dry_run = config.get("trading", {}).get("dry_run", True)
        self.exchange = self._init_exchange()

    def _init_exchange(self) -> Optional[ccxt.Exchange]:
        binance_cfg = self.config.get("binance", {})
        api_key = binance_cfg.get("api_key", "")
        api_secret = binance_cfg.get("api_secret", "")

        if not api_key or not api_secret:
            logger.warning("未提供 Binance API Key，將使用 Dry Run 模式（無實際下單）")
            return None

        exchange = ccxt.binance({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {"defaultType": "spot"}
        })
        try:
            exchange.load_markets()
            logger.info("Binance 交易所連接成功")
            return exchange
        except Exception as e:
            logger.error(f"交易所連接失敗: {e}")
            return None

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        qty: float,
        price: Optional[float] = None,
        stop_loss_pct: float = 0.03
    ) -> Optional[Dict]:
        """
        下單主函數。
        Returns:
            訂單結果字典，包含 order_id、status、timestamp 等。
        """
        if self.dry_run or self.exchange is None:
            logger.info(f"[DRY RUN] 模擬下單: {side} {qty} {symbol} @ {price}")
            order_result = {
                "id": "dry_run_order_123",
                "status": "closed",
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "amount": qty,
                "price": price,
                "timestamp": time.time() * 1000,
                "dry_run": True
            }
            self._record_trade(order_result)
            return order_result

        try:
            params = {}
            if order_type == "limit":
                if price is None:
                    raise ValueError("limit 訂單需提供 price")
                order = self.exchange.create_limit_order(symbol, side, qty, price, params)
            elif order_type == "market":
                order = self.exchange.create_market_order(symbol, side, qty, params)
            else:
                raise ValueError(f"不支援的訂單類型: {order_type}")

            logger.info(f"下單成功: {order['id']} ({side} {qty} {symbol})")
            self._record_trade(order)
            return order
        except Exception as e:
            logger.exception(f"下單失敗: {e}")
            return None

    def _record_trade(self, order: Dict):
        """
        將下單記錄寫入資料庫。
        """
        try:
            trade = TradeHistory(
                action=order["side"].upper(),
                price=order["price"] if order["price"] else 0.0,
                amount=order["amount"],
                model_confidence=0.0,  # TODO: 由 predictor 傳入
                pnl=None
            )
            self.session.add(trade)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            logger.error(f"交易記錄保存失敗: {e}")

def run_order_manager(
    config: Dict,
    db_session: Session,
    symbol: str,
    side: str,
    qty: float,
    price: Optional[float] = None,
    confidence: float = 0.0,
    stop_loss_pct: float = 0.03
) -> Optional[Dict]:
    """
    便捷函數：初始化 OrderManager 並執行一次下單。
    """
    om = OrderManager(config, db_session)
    # 注入 confidence
    om.confidence = confidence  # 便于 record 使用
    return om.place_order(symbol, side, "limit" if price else "market", qty, price, stop_loss_pct)

if __name__ == "__main__":
    print("Order Manager 模組載入成功。")
