"""
回測績效指標計算 module v3
新增 sell-win rate 與交易分解，避免把 classification accuracy 當交易勝率。
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
    metrics = {}

    if periods_per_year is None:
        periods_per_year = 365 * 24 * (60 // freq_minutes)

    if equity_curve is None or len(equity_curve) < 2:
        return {
            "total_return": 0.0, "annual_return": 0.0, "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0, "max_drawdown": 0.0, "calmar_ratio": 0.0,
            "alpha_vs_benchmark": 0.0, "total_trades": 0, "win_rate": 0.0,
            "sell_win_rate": 0.0, "profit_factor": 0.0, "avg_win": 0.0,
            "avg_loss": 0.0, "n_wins": 0, "n_losses": 0, "n_draws": 0,
            "expectancy": 0.0, "max_consecutive_losses": 0,
        }

    start_eq = float(equity_curve.iloc[0])
    end_eq = float(equity_curve.iloc[-1])
    total_return = (end_eq - start_eq) / start_eq if start_eq != 0 else 0.0
    metrics["total_return"] = total_return

    n_periods = len(equity_curve) - 1
    annual_return = (1 + total_return) ** (periods_per_year / n_periods) - 1 if n_periods > 0 else 0.0
    metrics["annual_return"] = annual_return

    returns = equity_curve.pct_change().dropna()
    if len(returns) > 0:
        excess_returns = returns - (risk_free_rate / periods_per_year)
        sharpe = np.sqrt(periods_per_year) * excess_returns.mean() / excess_returns.std() if excess_returns.std() > 0 else 0.0
        metrics["sharpe_ratio"] = sharpe
        downside = returns[returns < 0]
        downside_std = downside.std() * np.sqrt(periods_per_year) if len(downside) > 0 else 0.0
        sortino = (annual_return - risk_free_rate) / abs(downside_std) if abs(downside_std) > 0 else 0.0
        metrics["sortino_ratio"] = sortino
    else:
        metrics["sharpe_ratio"] = 0.0
        metrics["sortino_ratio"] = 0.0

    running_max = equity_curve.expanding().max()
    drawdown = (equity_curve - running_max) / running_max
    max_dd = drawdown.min()
    metrics["max_drawdown"] = max_dd
    metrics["calmar_ratio"] = annual_return / abs(max_dd) if abs(max_dd) > 0 else float("inf")
    metrics["alpha_vs_benchmark"] = total_return - (benchmark_return / 100.0) if benchmark_return else 0.0

    if trade_log is not None and not trade_log.empty and "pnl" in trade_log.columns:
        sells = trade_log[trade_log.get("action") == "SELL"].copy() if "action" in trade_log.columns else trade_log.copy()
        if sells.empty:
            sells = trade_log[pd.notna(trade_log["pnl"])].copy()

        n_trades = len(sells)
        wins = sells[sells["pnl"] > 0]
        losses = sells[sells["pnl"] < 0]
        draws = sells[sells["pnl"] == 0]
        win_rate = len(wins) / n_trades if n_trades > 0 else 0

        metrics["total_trades"] = n_trades
        metrics["win_rate"] = win_rate
        metrics["sell_win_rate"] = win_rate
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
        metrics.update({
            "total_trades": 0, "win_rate": 0.0, "sell_win_rate": 0.0,
            "profit_factor": 0.0, "avg_win": 0.0, "avg_loss": 0.0,
            "n_wins": 0, "n_losses": 0, "n_draws": 0,
            "expectancy": 0.0, "max_consecutive_losses": 0,
        })

    return metrics
