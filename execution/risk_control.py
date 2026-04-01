"""
風險控制模組：部位控制、止損（固定 + ATR 追蹤）、回撤控制
"""

from typing import Dict, Optional, List
from decimal import Decimal, ROUND_DOWN
import numpy as np
from utils.logger import setup_logger

logger = setup_logger(__name__)


def check_position_size(
    account_balance: float,
    confidence: float,
    max_position_ratio: float = 0.05,
    min_position_ratio: float = 0.001,
) -> float:
    """根據信心分數計算下單金額。"""
    if not (0 <= confidence <= 1):
        confidence = max(0.0, min(1.0, confidence))
    ratio = min_position_ratio + (max_position_ratio - min_position_ratio) * confidence
    position = account_balance * ratio
    logger.info(f"Position: {position:.2f} (ratio={ratio:.2%}, confidence={confidence:.2%})")
    return position


def round_down(amount: float, step: float) -> float:
    """向下取整至 step 的倍數。"""
    dec_amount = Decimal(str(amount))
    dec_step = Decimal(str(step))
    return float((dec_amount // dec_step) * dec_step)


def calculate_stop_loss(
    entry_price: float,
    stop_loss_pct: float = 0.03,
    side: str = "BUY",
) -> float:
    """固定百分比止損。"""
    if side.upper() == "BUY":
        return entry_price * (1 - stop_loss_pct)
    elif side.upper() == "SELL":
        return entry_price * (1 + stop_loss_pct)
    else:
        raise ValueError(f"無效 side: {side}")


def calculate_atr(prices: List[float], period: int = 14) -> Optional[float]:
    """
    計算 ATR (Average True Range)。
    簡化版：使用高點-低點的滾動平均（若無 high/low，用 close 的絕對變化）。
    """
    if len(prices) < period + 1:
        return None
    true_ranges = []
    for i in range(1, len(prices)):
        tr = abs(prices[i] - prices[i - 1])
        true_ranges.append(tr)
    if len(true_ranges) < period:
        return None
    return float(np.mean(true_ranges[-period:]))


def calculate_atr_stop_loss(
    entry_price: float,
    prices: List[float],
    atr_multiplier: float = 2.0,
    side: str = "BUY",
    period: int = 14,
) -> Optional[float]:
    """
    ATR 止損：止損距離 = ATR * multiplier。
    比固定百分比更適應市場波動。
    """
    atr = calculate_atr(prices, period)
    if atr is None or atr <= 0:
        logger.warning("ATR 計算失敗，退回固定百分比止損")
        return calculate_stop_loss(entry_price, 0.03, side)

    if side.upper() == "BUY":
        stop = entry_price - atr * atr_multiplier
    elif side.upper() == "SELL":
        stop = entry_price + atr * atr_multiplier
    else:
        raise ValueError(f"無效 side: {side}")

    logger.info(f"ATR Stop: entry={entry_price:.2f}, atr={atr:.2f}, "
                f"multiplier={atr_multiplier}, stop={stop:.2f}")
    return stop


def update_trailing_stop(
    current_price: float,
    entry_price: float,
    current_stop: float,
    side: str = "BUY",
    trailing_pct: float = 0.02,
) -> float:
    """
    追蹤止損：價格有利移動時，同步上移止損。
    只移動止損，不回退。
    """
    if side.upper() == "BUY":
        # 多單：止損跟隨價格上移
        new_stop = current_price * (1 - trailing_pct)
        if new_stop > current_stop:
            logger.info(f"Trailing stop moved up: {current_stop:.2f} -> {new_stop:.2f}")
            return new_stop
    elif side.upper() == "SELL":
        # 空單：止損跟隨價格下移
        new_stop = current_price * (1 + trailing_pct)
        if new_stop < current_stop:
            logger.info(f"Trailing stop moved down: {current_stop:.2f} -> {new_stop:.2f}")
            return new_stop
    return current_stop


def check_max_drawdown(current_pnl: float, max_allowable_drawdown: float = 0.2) -> bool:
    """檢查是否超過最大回撤。"""
    if current_pnl < 0 and abs(current_pnl) > max_allowable_drawdown:
        logger.warning(f"Max drawdown exceeded: pnl={current_pnl:.4f}")
        return False
    return True


def validate_order(
    symbol: str,
    amount: float,
    price: float,
    balance: float,
    confidence: float,
    config: Dict,
    price_history: Optional[List[float]] = None,
) -> Optional[Dict]:
    """綜合風控檢查。"""
    max_position_ratio = config.get("trading", {}).get("max_position_ratio", 0.05)
    dry_run = config.get("trading", {}).get("dry_run", True)
    atr_multiplier = config.get("trading", {}).get("atr_multiplier", 2.0)

    position = check_position_size(balance, confidence, max_position_ratio)
    if position <= 0:
        return None

    qty = round_down(position / price, 0.001)
    if qty <= 0:
        return None

    side = "buy" if confidence > 0.5 else "sell"

    # 止損：優先 ATR，備用固定百分比
    if price_history and len(price_history) >= 14:
        stop_price = calculate_atr_stop_loss(price, price_history, atr_multiplier, side)
        stop_type = "atr"
    else:
        stop_price = calculate_stop_loss(price, 0.03, side)
        stop_type = "fixed"

    return {
        "symbol": symbol,
        "side": side,
        "order_type": "limit",
        "qty": qty,
        "price": price,
        "dry_run": dry_run,
        "stop_loss_price": stop_price,
        "stop_loss_type": stop_type,
    }


if __name__ == "__main__":
    pos = check_position_size(10000, 0.8)
    print(f"Position: {pos}")
    stop = calculate_stop_loss(50000, 0.03, "BUY")
    print(f"Fixed stop: {stop}")
    prices = [50000 + i * 100 + (i % 3) * 50 for i in range(20)]
    atr_stop = calculate_atr_stop_loss(51000, prices, 2.0, "BUY")
    print(f"ATR stop: {atr_stop}")
    trailing = update_trailing_stop(51500, 51000, 50500, "BUY")
    print(f"Trailing stop: {trailing}")
