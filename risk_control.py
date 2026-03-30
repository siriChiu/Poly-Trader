"""
風險控制模組：確保單次下單金額、止損機制與整體部位控制
"""

from typing import Dict, Optional
from decimal import Decimal, ROUND_DOWN
from utils.logger import setup_logger

logger = setup_logger(__name__)

def check_position_size(
    account_balance: float,
    confidence: float,
    max_position_ratio: float = 0.05,
    min_position_ratio: float = 0.001
) -> float:
    """
    根據模型信心分數與帳戶餘額計算下單金額。
    策略：信心越高，部位越大（但不超過 max_position_ratio）。
    Returns: 建議下單金額（浮點數）。
    """
    if not (0 <= confidence <= 1):
        logger.warning(f"信心分數超出範圍: {confidence}，將clip到[0,1]")
        confidence = max(0.0, min(1.0, confidence))

    # 基礎部位為 max_position_ratio，按信心比例調整
    ratio = min_position_ratio + (max_position_ratio - min_position_ratio) * confidence
    position = account_balance * ratio
    logger.info(f"Account={account_balance}, Confidence={confidence:.2%} -> Position={position:.2f} (ratio={ratio:.2%})")
    return position

def round_down(amount: float, step: float) -> float:
    """
    將金額向下取整至 step 的倍數（適用於交易所最小交易單位）。
    """
    dec_amount = Decimal(str(amount))
    dec_step = Decimal(str(step))
    rounded = (dec_amount // dec_step) * dec_step
    return float(rounded)

def calculate_stop_loss(
    entry_price: float,
    stop_loss_pct: float = 0.03,
    side: str = "BUY"
) -> float:
    """
    計算硬止損價格。
    side: "BUY" (做多) 或 "SELL" (做空)
    """
    if side.upper() == "BUY":
        stop_price = entry_price * (1 - stop_loss_pct)
    elif side.upper() == "SELL":
        stop_price = entry_price * (1 + stop_loss_pct)
    else:
        raise ValueError(f"無效 side: {side}")
    return stop_price

def check_max_drawdown(
    current_pnl: float,
    max_allowable_drawdown: float = 0.2
) -> bool:
    """
    檢查當前虧損是否超過最大回撤限制。
    若超過，應停止交易並平倉。
    """
    if current_pnl < 0 and abs(current_pnl) > max_allowable_drawdown:
        logger.warning(f"最大回撤超出：current_pnl={current_pnl}, threshold={max_allowable_drawdown}")
        return False
    return True

def validate_order(
    symbol: str,
    amount: float,
    price: float,
    balance: float,
    confidence: float,
    config: Dict
) -> Optional[Dict]:
    """
    綜合風險檢查：決定是否允許下單。
    Returns:
        若通過，返回訂單參數字典；否則返回 None。
    """
    max_position_ratio = config.get("trading", {}).get("max_position_ratio", 0.05)
    dry_run = config.get("trading", {}).get("dry_run", True)

    # 1. 檢查部位大小
    position = check_position_size(balance, confidence, max_position_ratio)
    if position <= 0:
        logger.warning("部位大小為零，不執行下單")
        return None

    # 2. 根據价格計算數量（假设是用 USDT 计价，buy amount in quote）
    # 暂时简化：amount = position / price
    qty = position / price
    # TODO: 根据交易所最小交易单位 rounding
    qty = round_down(qty, 0.001)  # 示例 step

    if qty <= 0:
        logger.warning("計算數量為零，不執行下單")
        return None

    # 3. checks passed
    return {
        "symbol": symbol,
        "side": "buy" if confidence > 0.5 else "sell",  # 简化：高confidence做多
        "order_type": "limit",
        "qty": qty,
        "price": price,
        "dry_run": dry_run,
        "stop_loss_pct": 0.03
    }

if __name__ == "__main__":
    # 簡單單元測試
    pos = check_position_size(10000, 0.8)
    print(f"Test position: {pos}")
    stop = calculate_stop_loss(50000, 0.03, "BUY")
    print(f"Test stop loss: {stop}")
