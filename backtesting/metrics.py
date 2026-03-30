"""
回測績效指標計算 module
"""

import pandas as pd
import numpy as np
from typing import Dict

def calculate_metrics(
    equity_curve: pd.Series,
    trade_log: pd.DataFrame,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 365 * 24  # 假設每小時資料
) -> Dict:
    """
    計算回測績效指標。

    Args:
        equity_curve: 權益曲線（時間序列 Series，index 為時間）
        trade_log: 交易日誌 DataFrame，需包含 'pnl' 欄位
        risk_free_rate: 無風險利率（年化）
        periods_per_year: 每年期間數（用於年化）

    Returns:
        指標字典
    """
    metrics = {}

    # 1. 總回報率
    start = equity_curve.iloc[0]
    end = equity_curve.iloc[-1]
    total_return = (end - start) / start
    metrics["total_return"] = total_return

    # 2. 年化收益率
    n_periods = len(equity_curve) - 1
    if n_periods > 0:
        annual_return = (1 + total_return) ** (periods_per_year / n_periods) - 1
        metrics["annual_return"] = annual_return
    else:
        metrics["annual_return"] = 0.0

    # 3. 夏普比率
    returns = equity_curve.pct_change().dropna()
    if len(returns) > 0:
        excess_returns = returns - (risk_free_rate / periods_per_year)
        if excess_returns.std() > 0:
            sharpe = np.sqrt(periods_per_year) * excess_returns.mean() / excess_returns.std()
        else:
            sharpe = 0.0
        metrics["sharpe_ratio"] = sharpe
    else:
        metrics["sharpe_ratio"] = 0.0

    # 4. 最大回撤
    running_max = equity_curve.expanding().max()
    drawdown = (equity_curve - running_max) / running_max
    max_dd = drawdown.min()
    metrics["max_drawdown"] = max_dd

    # 5. 卡爾瑪比率
    if abs(max_dd) > 0:
        calmar = annual_return / abs(max_dd)
    else:
        calmar = np.inf
    metrics["calmar_ratio"] = calmar

    # 6. 交易相關指標
    if trade_log is not None and not trade_log.empty:
        trades = trade_log.copy()
        # 假設 pnl 欄位存在
        if "pnl" in trades.columns:
            winning_trades = trades[trades["pnl"] > 0]
            losing_trades = trades[trades["pnl"] < 0]
            n_trades = len(trades)
            win_rate = len(winning_trades) / n_trades if n_trades > 0 else 0
            metrics["total_trades"] = n_trades
            metrics["win_rate"] = win_rate

            # 盈虧比
            avg_win = winning_trades["pnl"].mean() if len(winning_trades) > 0 else 0
            avg_loss = abs(losing_trades["pnl"].mean()) if len(losing_trades) > 0 else 1
            if avg_loss > 0:
                profit_factor = winning_trades["pnl"].sum() / abs(losing_trades["pnl"].sum())
            else:
                profit_factor = np.inf if winning_trades["pnl"].sum() > 0 else 0
            metrics["profit_factor"] = profit_factor
            metrics["avg_win"] = avg_win
            metrics["avg_loss"] = avg_loss
    else:
        metrics["total_trades"] = 0
        metrics["win_rate"] = 0.0
        metrics["profit_factor"] = 0.0
        metrics["avg_win"] = 0.0
        metrics["avg_loss"] = 0.0

    return metrics

if __name__ == "__main__":
    # 單元測試數據
    eq = pd.Series([10000, 10200, 10100, 10500, 11000], index=pd.date_range("2025-01-01", periods=5, freq="H"))
    trades = pd.DataFrame({
        "pnl": [200, -100, 400, -100]
    })
    m = calculate_metrics(eq, trades)
    print("Metrics test:")
    for k, v in m.items():
        print(f"  {k}: {v}")
