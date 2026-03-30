"""
參數優化模組：網格搜索最佳策略參數
"""

import itertools
import pandas as pd
from typing import List, Dict, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from backtesting.engine import run_backtest
from backtesting.metrics import calculate_metrics
from utils.logger import setup_logger

logger = setup_logger(__name__)

def grid_search(
    session: Session,
    confidence_thresholds: List[float],
    max_position_ratios: List[float],
    stop_loss_pcts: List[float],
    start_date: datetime,
    end_date: datetime,
    initial_capital: float = 10000.0,
    symbol: str = "BTC/USDT"
) -> pd.DataFrame:
    """
    對給定的參數組合進行網格搜索。
    Returns:
        DataFrame 包含每組參數的關鍵指標
    """
    results = []
    param_combinations = list(itertools.product(confidence_thresholds, max_position_ratios, stop_loss_pcts))
    total = len(param_combinations)
    logger.info(f"開始參數優化：{total} 種組合")

    for i, (conf_thresh, max_pos_ratio, stop_loss) in enumerate(param_combinations, 1):
        logger.debug(f"測試組合 {i}/{total}: conf={conf_thresh}, max_pos={max_pos_ratio}, stop={stop_loss}")
        res = run_backtest(
            session=session,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            confidence_threshold=conf_thresh,
            max_position_ratio=max_pos_ratio,
            stop_loss_pct=stop_loss,
            symbol=symbol
        )
        if res is None:
            continue

        equity_curve = res["equity_curve"]["equity"]
        trade_log = res["trade_log"]
        metrics = calculate_metrics(equity_curve, trade_log)

        results.append({
            "confidence_threshold": conf_thresh,
            "max_position_ratio": max_pos_ratio,
            "stop_loss_pct": stop_loss,
            "total_return": metrics["total_return"],
            "sharpe_ratio": metrics["sharpe_ratio"],
            "max_drawdown": metrics["max_drawdown"],
            "win_rate": metrics.get("win_rate", 0),
            "profit_factor": metrics.get("profit_factor", 0),
            "total_trades": metrics.get("total_trades", 0)
        })

    df = pd.DataFrame(results)
    return df

def find_best_params(results_df: pd.DataFrame, metric: str = "sharpe_ratio") -> Dict:
    """
    從結果 DataFrame 中找出最佳參數組合。
    """
    if results_df.empty:
        return {}
    best_idx = results_df[metric].idxmax()
    return results_df.loc[best_idx].to_dict()

if __name__ == "__main__":
    # 示例：手動測試
    print("Optimizer loaded.")
