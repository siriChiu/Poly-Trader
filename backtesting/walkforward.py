"""
Walk-Forward Validation — 滑動窗口回測驗證
防止參數過擬合：在不同時間段測試參數穩健性
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backtesting.engine import run_backtest
from backtesting.metrics import calculate_metrics
from utils.logger import setup_logger

logger = setup_logger(__name__)


def run_walk_forward(
    session: Session,
    best_params: Dict,
    train_days: int = 30,
    test_days: int = 10,
    n_windows: int = 5,
    initial_capital: float = 10000.0,
    symbol: str = "BTC/USDT"
) -> Dict:
    """
    滑動窗口 Walk-Forward 驗證。

    原理：
    - 用 train_days 的歷史找最佳參數
    - 用後 test_days 進行 out-of-sample 驗證
    - 滑動 test_days，重複 n_windows 次
    - 最終評估 out-of-sample 表現是否穩健

    Args:
        session: DB session
        best_params: 要測試的參數字典（已從 optimizer 或手動設定）
        train_days: 訓練窗口長度（天）
        test_days: 測試窗口長度（天）
        n_windows: 滑動次數
        initial_capital: 初始資金
        symbol: 交易對

    Returns:
        {
            "windows": [每窗口結果...],
            "oos_returns": [...],
            "oos_sharpes": [...],
            "stability_score": float,  # 穩健性分數 0~1
            "summary": {...}
        }
    """
    now = datetime.utcnow()
    total_days = train_days + test_days * n_windows
    start_all = now - timedelta(days=total_days)

    logger.info(
        f"Walk-Forward: train={train_days}d, test={test_days}d, windows={n_windows}"
    )

    window_results = []

    for i in range(n_windows):
        test_start = start_all + timedelta(days=train_days + i * test_days)
        test_end = test_start + timedelta(days=test_days)

        logger.info(f"Window {i+1}/{n_windows}: test {test_start.date()} ~ {test_end.date()}")

        result = run_backtest(
            session=session,
            start_date=test_start,
            end_date=test_end,
            initial_capital=initial_capital,
            symbol=symbol,
            **best_params
        )

        if result is None or result["equity_curve"].empty:
            window_results.append({
                "window": i + 1, "test_start": test_start, "test_end": test_end,
                "total_return": 0.0, "sharpe_ratio": 0.0, "max_drawdown": 0.0,
                "total_trades": 0, "win_rate": 0.0,
                "buy_hold_return": result.get("buy_hold_return", 0) if result else 0,
                "alpha": 0.0, "status": "no_data"
            })
            continue

        eq = result["equity_curve"]["equity"]
        metrics = calculate_metrics(
            eq, result["trade_log"],
            benchmark_return=result.get("buy_hold_return", 0),
            freq_minutes=5
        )

        window_results.append({
            "window": i + 1,
            "test_start": test_start.strftime("%Y-%m-%d"),
            "test_end": test_end.strftime("%Y-%m-%d"),
            "total_return": metrics["total_return"],
            "sharpe_ratio": metrics.get("sharpe_ratio", 0),
            "sortino_ratio": metrics.get("sortino_ratio", 0),
            "max_drawdown": metrics.get("max_drawdown", 0),
            "total_trades": metrics.get("total_trades", 0),
            "win_rate": metrics.get("win_rate", 0),
            "profit_factor": metrics.get("profit_factor", 0),
            "buy_hold_return": result.get("buy_hold_return", 0),
            "alpha": result.get("alpha", 0),
            "total_trading_cost": result.get("total_trading_cost", 0),
            "status": "ok"
        })

    if not window_results:
        return {"windows": [], "summary": {"error": "no data"}}

    df = pd.DataFrame(window_results)
    ok_windows = df[df["status"] == "ok"]

    # 穩健性分數：多少窗口有正 Alpha
    if len(ok_windows) > 0:
        pct_positive_alpha = (ok_windows["alpha"] > 0).mean()
        pct_positive_return = (ok_windows["total_return"] > 0).mean()
        stability_score = (pct_positive_alpha * 0.6 + pct_positive_return * 0.4)
    else:
        stability_score = 0.0

    summary = {
        "n_windows": len(window_results),
        "n_ok": len(ok_windows),
        "avg_oos_return": ok_windows["total_return"].mean() if len(ok_windows) > 0 else 0,
        "avg_sharpe": ok_windows["sharpe_ratio"].mean() if len(ok_windows) > 0 else 0,
        "avg_max_drawdown": ok_windows["max_drawdown"].mean() if len(ok_windows) > 0 else 0,
        "pct_profitable_windows": float(ok_windows["total_return"].gt(0).mean()) if len(ok_windows) > 0 else 0,
        "pct_beat_bh": float(ok_windows["alpha"].gt(0).mean()) if len(ok_windows) > 0 else 0,
        "stability_score": stability_score,
        "verdict": "STABLE" if stability_score >= 0.6 else "UNSTABLE"
    }

    logger.info(f"WF done: stability={stability_score:.2f}, verdict={summary['verdict']}")

    return {
        "windows": window_results,
        "windows_df": df,
        "summary": summary,
    }


if __name__ == "__main__":
    print("WalkForward module loaded OK")
