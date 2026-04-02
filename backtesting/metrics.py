"""
回測績效指標計算 module v2
新增：Sortino、最大連續虧損、平均持倉時間、市場參與率
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional

def calculate_metrics(
    equity_curve: pd.Series,
    trade_log: pd.DataFrame,
    risk_free_rate: float = 0.0,
    benchmark_return: float = 0.0,
    periods_per_year: Optional[int] = None,
    freq_minutes: int = 5
) -> Dict:
    """
    計算回測績效指標。

    Args:
        equity_curve: 權益曲線（時間序列 Series，index 為時間）
        trade_log: 交易日誌 DataFrame，需包含 'pnl' / 'timestamp' 欄位
        risk_free_rate: 無風險利率（年化）
        benchmark_return: 基準回報 (Buy & Hold %)
        freq_minutes: 資料頻率（分鐘），用於自動計算 periods_per_year

    Returns:
        指標字典
    """
    metrics = {}

    # 自動計算 periods_per_year
    if periods_per_year is None:
        periods_per_year = 365 * 24 * (60 // freq_minutes)

    # 1. 總回報率
    start_eq = equity_curve.iloc[0]
    end_eq = equity_curve.iloc[-1]
    total_return = (end_eq - start_eq) / start_eq
    metrics["total_return"] = total_return

    # 2. 年化收益率
    n_periods = len(equity_curve) - 1
    if n_periods > 0:
        annual_return = (1 + total_return) ** (periods_per_year / n_periods) - 1
    else:
        annual_return = 0.0
    metrics["annual_return"] = annual_return

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

    # 4. 索提諾比率（Sortino）
    if len(returns) > 0:
        downside = returns[returns < 0]
        if len(downside) > 0 and downside.std() > 0:
            downside_std = downside.std() * np.sqrt(periods_per_year)
            sortino = (annual_return - risk_free_rate) / abs(downside_std) if abs(downside_std) > 0 else 0.0
        else:
            sortino = 0.0
        metrics["sortino_ratio"] = sortino
    else:
        metrics["sortino_ratio"] = 0.0

    # 5. 最大回撤
    running_max = equity_curve.expanding().max()
    drawdown = (equity_curve - running_max) / running_max
    max_dd = drawdown.min()
    metrics["max_drawdown"] = max_dd

    # 6. 卡爾瑪比率
    calmar = annual_return / abs(max_dd) if abs(max_dd) > 0 else float("inf")
    metrics["calmar_ratio"] = calmar

    # Alpha vs benchmark
    metrics["alpha_vs_benchmark"] = total_return - (benchmark_return / 100.0) if benchmark_return else 0.0

    # 7. 交易相關指標
    if trade_log is not None and not trade_log.empty and "pnl" in trade_log.columns:
        sells = trade_log[trade_log.get("action") == "SELL"].copy() if "action" in trade_log.columns else trade_log
        if sells.empty:
            sells = trade_log[pd.notna(trade_log["pnl"])]

        n_trades = len(sells)
        wins = sells[sells["pnl"] > 0]
        losses = sells[sells["pnl"] < 0]
        draws = sells[sells["pnl"] == 0]
        win_rate = len(wins) / n_trades if n_trades > 0 else 0

        metrics["total_trades"] = n_trades
        metrics["win_rate"] = win_rate
        metrics["n_wins"] = len(wins)
        metrics["n_losses"] = len(losses)
        metrics["n_draws"] = len(draws)

        avg_win = wins["pnl"].mean() if len(wins) > 0 else 0
        avg_loss = abs(losses["pnl"].mean()) if len(losses) > 0 else 1
        pnl_ratio = abs(losses["pnl"].sum())
        profit_factor = wins["pnl"].sum() / pnl_ratio if pnl_ratio > 0 else (float("inf") if wins["pnl"].sum() > 0 else 0)
        metrics["profit_factor"] = profit_factor
        metrics["avg_win"] = avg_win
        metrics["avg_loss"] = avg_loss
        metrics["expectancy"] = (wins["pnl"].sum() - pnl_ratio) / n_trades if n_trades > 0 else 0

        # 最大連續虧損
        pnl_series = sells["pnl"].values
        max_consec_loss = 0
        current_streak = 0
        for p in pnl_series:
            if p < 0:
                current_streak += 1
                max_consec_loss = max(max_consec_loss, current_streak)
            else:
                current_streak = 0
        metrics["max_consecutive_losses"] = max_consec_loss

        # 平均持倉時間 (如果有 timestamp)
        if "timestamp" in sells.columns and len(sells) > 1:
            try:
                timestamps = pd.to_datetime(sells["timestamp"])
                if len(timestamps) > 1:
                    avg_duration = timestamps.diff().mean()
                    metrics["avg_trade_duration"] = str(avg_duration)
                    metrics["avg_trade_duration_minutes"] = avg_duration.total_seconds() / 60
            except Exception:
                pass
    else:
        metrics["total_trades"] = 0
        metrics["win_rate"] = 0.0
        metrics["profit_factor"] = 0.0
        metrics["avg_win"] = 0.0
        metrics["avg_loss"] = 0.0
        metrics["n_wins"] = 0
        metrics["n_losses"] = 0
        metrics["n_draws"] = 0
        metrics["expectancy"] = 0.0
        metrics["max_consecutive_losses"] = 0

    return metrics


if __name__ == "__main__":
    eq = pd.Series([10000, 10200, 10100, 10500, 11000],
                    index=pd.date_range("2025-01-01", periods=5, freq="H"))
    trades = pd.DataFrame({
        "action": ["SELL", "SELL", "SELL", "SELL"],
        "pnl": [200, -100, 400, -100],
        "timestamp": pd.date_range("2025-01-01", periods=4, freq="H"),
    })
    m = calculate_metrics(eq, trades, freq_minutes=60)
    print("Metrics v2 test:")
    for k, v in m.items():
        print(f"  {k}: {v}")
