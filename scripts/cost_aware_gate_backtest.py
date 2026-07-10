"""Cost-aware gate counterfactual backtest for Poly-Trader.

This script answers the operator question: does the new cost-aware readiness gate
actually improve historical paper/shadow candidates, or are we merely waiting?

Methodology:
- Reuse the same walk-forward splits, feature frame, and model confidence helpers
  as scripts/topk_walkforward_precision.py.
- For each fold, train on past data only.
- Calibrate forecast_edge_bps from the training window by sorting training rows by
  model score and computing the mean realized pyramid PnL of rows with score >=
  the tested row's score.  A minimum calibration cohort prevents one-row edge
  estimates.
- Compare baseline Top-K candidates with the same Top-K candidates filtered by
  forecast_edge_bps > configured fee+spread+slippage+buffer cost threshold.

The artifact is deliberately paper/shadow only.  It is not live deployment proof.
"""
from __future__ import annotations

import bisect
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backtesting.model_leaderboard import MIN_TRAIN_SAMPLES, ModelLeaderboard
from execution.config import resolve_cost_aware_edge_config
from scripts import topk_walkforward_precision as topk

OUT_PATH = PROJECT_ROOT / "data" / "cost_aware_gate_backtest.json"
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
TOP_PCTS = topk.TOP_PCTS
MODELS = topk.MODELS
DEFAULT_MIN_CALIBRATION_ROWS = 50
MAX_FOLDS = 4
SENSITIVITY_THRESHOLDS_BPS = [15.0, 50.0, 100.0, 150.0, 200.0, 250.0, 300.0]
EPSILON = 1e-9


def _load_yaml_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        import yaml

        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _round_or_none(value: Any, digits: int = 4) -> Optional[float]:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric) or math.isinf(numeric):
        return None
    return round(numeric, digits)


def _pnl_series(sub: pd.DataFrame, *, net_cost_per_trade: float = 0.0) -> pd.Series:
    if sub.empty:
        return pd.Series([], dtype=float)
    if "simulated_pyramid_pnl" in sub.columns:
        pnl = pd.to_numeric(sub["simulated_pyramid_pnl"], errors="coerce").fillna(0.0).astype(float)
    elif "future_return_pct" in sub.columns:
        pnl = pd.to_numeric(sub["future_return_pct"], errors="coerce").fillna(0.0).astype(float)
    else:
        pnl = pd.Series([0.0] * len(sub), dtype=float)
    if net_cost_per_trade:
        pnl = pnl - float(net_cost_per_trade)
    return pnl.reset_index(drop=True)


def _profit_factor(pnl: pd.Series) -> Optional[float]:
    if pnl.empty:
        return None
    gross_profit = float(pnl[pnl > 0].sum())
    gross_loss = abs(float(pnl[pnl < 0].sum()))
    if gross_loss <= 0:
        return 999.0 if gross_profit > 0 else 0.0
    return round(gross_profit / gross_loss, 4)


def _max_drawdown(pnl: pd.Series) -> Optional[float]:
    if pnl.empty:
        return None
    cumulative = pnl.cumsum()
    peak = cumulative.cummax()
    drawdown = peak - cumulative
    return round(float(drawdown.max()), 4)


def _worst_fold_roi(sub: pd.DataFrame, *, net_cost_per_trade: float) -> Optional[float]:
    if sub.empty or "fold" not in sub.columns:
        return None
    values: list[float] = []
    for _fold, fold_df in sub.groupby("fold"):
        pnl = _pnl_series(fold_df.sort_values("timestamp"), net_cost_per_trade=net_cost_per_trade)
        values.append(float(pnl.sum()))
    if not values:
        return None
    return round(min(values), 4)


def _metrics(sub: pd.DataFrame, target_col: str, *, net_cost_per_trade: float) -> dict[str, Any]:
    chronological = sub.sort_values("timestamp") if "timestamp" in sub.columns else sub
    pnl = _pnl_series(chronological, net_cost_per_trade=net_cost_per_trade)
    wins = int(pd.to_numeric(sub[target_col], errors="coerce").fillna(0).sum()) if target_col in sub.columns else 0
    trade_count = int(len(sub))
    avg_trade_net = float(pnl.mean()) if not pnl.empty else None
    forecast_edge = pd.to_numeric(sub.get("forecast_edge_bps", pd.Series([], dtype=float)), errors="coerce")
    return {
        "trade_count": trade_count,
        "wins": wins,
        "losses": max(trade_count - wins, 0),
        "win_rate": round(float(wins / trade_count), 4) if trade_count else None,
        "net_roi": _round_or_none(float(pnl.sum()) if not pnl.empty else None),
        "avg_trade_net_bps": _round_or_none(avg_trade_net * 10000.0 if avg_trade_net is not None else None),
        "profit_factor_net": _profit_factor(pnl),
        "max_drawdown_net": _max_drawdown(pnl),
        "worst_fold_net_roi": _worst_fold_roi(sub, net_cost_per_trade=net_cost_per_trade),
        "avg_forecast_edge_bps": _round_or_none(float(forecast_edge.mean()) if len(forecast_edge.dropna()) else None),
        "min_forecast_edge_bps": _round_or_none(float(forecast_edge.min()) if len(forecast_edge.dropna()) else None),
    }


def _calibrated_forecast_edges_bps(
    train_scores: Iterable[float],
    train_pnl: Iterable[float],
    test_scores: Iterable[float],
    *,
    min_calibration_rows: int = DEFAULT_MIN_CALIBRATION_ROWS,
) -> list[Optional[float]]:
    """Estimate ex-ante edge from the training score/PnL curve.

    For a test score S, use training rows with score >= S.  If the high-score
    cohort is smaller than min_calibration_rows, expand to the top
    min_calibration_rows training rows.  This keeps the estimate causal while
    avoiding fragile one-row top-score means.
    """

    calibration = pd.DataFrame({"score": list(train_scores), "pnl": list(train_pnl)})
    calibration = calibration.dropna(subset=["score", "pnl"]).copy()
    if calibration.empty:
        return [None for _ in test_scores]
    calibration = calibration.sort_values("score", ascending=False).reset_index(drop=True)
    scores_desc = calibration["score"].astype(float).tolist()
    # bisect works ascending, so store negative descending scores.
    neg_scores = [-s for s in scores_desc]
    pnl = calibration["pnl"].astype(float)
    cumulative_mean = pnl.expanding().mean().tolist()
    max_rows = len(cumulative_mean)
    min_rows = max(1, min(int(min_calibration_rows), max_rows))

    edges: list[Optional[float]] = []
    for raw_score in test_scores:
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            edges.append(None)
            continue
        if math.isnan(score) or math.isinf(score):
            edges.append(None)
            continue
        rows_at_or_above = bisect.bisect_right(neg_scores, -score)
        cohort_rows = max(rows_at_or_above, min_rows)
        cohort_rows = min(cohort_rows, max_rows)
        forecast_pnl = cumulative_mean[cohort_rows - 1]
        edges.append(round(float(forecast_pnl) * 10000.0, 4))
    return edges


def _train_and_score_fold(
    lb: ModelLeaderboard,
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    feature_cols: list[str],
    target_col: str,
    model_name: str,
    fold_idx: int,
) -> Optional[pd.DataFrame]:
    if model_name == "rule_baseline":
        train_score = (1.0 - (train_df["feat_4h_bias50"].fillna(0).values + 5) / 15.0).clip(0.0, 1.0)
        test_score = (1.0 - (test_df["feat_4h_bias50"].fillna(0).values + 5) / 15.0).clip(0.0, 1.0)
    else:
        model = lb._train_model(
            train_df[feature_cols].fillna(0).values,
            train_df[target_col].values,
            model_name,
        )
        if model is None:
            return None
        train_score = lb._get_confidence(model, train_df[feature_cols].fillna(0).values, model_name)
        test_score = lb._get_confidence(model, test_df[feature_cols].fillna(0).values, model_name)

    train_pnl = _pnl_series(train_df, net_cost_per_trade=0.0)
    forecast_edges = _calibrated_forecast_edges_bps(train_score, train_pnl, test_score)
    scored_cols = [
        col
        for col in [
            "timestamp",
            "regime_label",
            target_col,
            "close_price",
            "simulated_pyramid_pnl",
            "future_return_pct",
        ]
        if col in test_df.columns
    ]
    scored = test_df[scored_cols].copy()
    scored["score"] = test_score
    scored["forecast_edge_bps"] = forecast_edges
    scored["fold"] = fold_idx
    return scored


def evaluate_model(
    data: pd.DataFrame,
    target_col: str,
    model_name: str,
    *,
    required_edge_bps: float,
) -> dict[str, Any] | None:
    lb = ModelLeaderboard(data, target_col=target_col)
    splits = lb._get_walk_forward_splits()
    feature_cols = [c for c in data.columns if c.startswith("feat_")]
    all_test_rows: list[pd.DataFrame] = []
    fold_windows: list[dict[str, Any]] = []

    for fold_idx, (ts, te, test_s, test_e) in enumerate(splits[:MAX_FOLDS]):
        train_df = data[(data["timestamp"] >= ts) & (data["timestamp"] < te)].copy()
        test_df = data[(data["timestamp"] >= test_s) & (data["timestamp"] < test_e)].copy()
        if len(train_df) < MIN_TRAIN_SAMPLES or len(test_df) < 50:
            continue
        scored = _train_and_score_fold(lb, train_df, test_df, feature_cols, target_col, model_name, fold_idx)
        if scored is None:
            return None
        all_test_rows.append(scored)
        fold_windows.append(
            {
                "fold": fold_idx,
                "train_start": str(train_df["timestamp"].min()),
                "train_end": str(train_df["timestamp"].max()),
                "test_start": str(test_df["timestamp"].min()),
                "test_end": str(test_df["timestamp"].max()),
                "train_rows": int(len(train_df)),
                "test_rows": int(len(test_df)),
            }
        )

    if not all_test_rows:
        return None

    combined = pd.concat(all_test_rows, ignore_index=True).sort_values("score", ascending=False).reset_index(drop=True)
    net_cost_per_trade = float(required_edge_bps) / 10000.0
    top_rows: list[dict[str, Any]] = []
    threshold_sweep_rows: list[dict[str, Any]] = []
    for pct in TOP_PCTS:
        top_key = f"top_{int(pct * 100)}pct"
        n = max(1, int(len(combined) * pct))
        baseline = combined.iloc[:n].copy()
        cost_aware = baseline[pd.to_numeric(baseline["forecast_edge_bps"], errors="coerce") > required_edge_bps].copy()
        baseline_metrics = _metrics(baseline, target_col, net_cost_per_trade=net_cost_per_trade)
        cost_metrics = _metrics(cost_aware, target_col, net_cost_per_trade=net_cost_per_trade)
        net_delta = None
        if baseline_metrics.get("net_roi") is not None and cost_metrics.get("net_roi") is not None:
            net_delta = round(float(cost_metrics["net_roi"]) - float(baseline_metrics["net_roi"]), 4)
        dd_delta = None
        if baseline_metrics.get("max_drawdown_net") is not None and cost_metrics.get("max_drawdown_net") is not None:
            dd_delta = round(float(cost_metrics["max_drawdown_net"]) - float(baseline_metrics["max_drawdown_net"]), 4)
        avg_trade_delta = None
        if baseline_metrics.get("avg_trade_net_bps") is not None and cost_metrics.get("avg_trade_net_bps") is not None:
            avg_trade_delta = round(float(cost_metrics["avg_trade_net_bps"]) - float(baseline_metrics["avg_trade_net_bps"]), 4)
        win_rate_delta = None
        if baseline_metrics.get("win_rate") is not None and cost_metrics.get("win_rate") is not None:
            win_rate_delta = round(float(cost_metrics["win_rate"]) - float(baseline_metrics["win_rate"]), 4)

        if cost_metrics["trade_count"] == 0:
            verdict = "no_cost_aware_trades"
        elif (
            int(len(baseline) - len(cost_aware)) == 0
            and (net_delta is None or abs(net_delta) <= EPSILON)
            and (dd_delta is None or abs(dd_delta) <= EPSILON)
            and (avg_trade_delta is None or abs(avg_trade_delta) <= EPSILON)
        ):
            verdict = "no_effect_non_binding"
        elif (
            net_delta is not None
            and dd_delta is not None
            and net_delta > EPSILON
            and dd_delta <= EPSILON
        ):
            verdict = "improved_net_and_risk"
        elif (
            avg_trade_delta is not None
            and avg_trade_delta > EPSILON
            and (dd_delta is None or dd_delta <= EPSILON)
        ):
            verdict = "improved_quality_tradeoff"
        elif net_delta is not None and net_delta < -EPSILON and (dd_delta is None or dd_delta >= -EPSILON):
            verdict = "worse_or_not_supported"
        else:
            verdict = "mixed"

        top_rows.append(
            {
                "model": model_name,
                "top_k": top_key,
                "baseline": baseline_metrics,
                "cost_aware": cost_metrics,
                "filtered_out_trades": int(len(baseline) - len(cost_aware)),
                "filter_retention_rate": round(float(len(cost_aware) / len(baseline)), 4) if len(baseline) else None,
                "net_roi_delta": net_delta,
                "max_drawdown_delta": dd_delta,
                "avg_trade_net_bps_delta": avg_trade_delta,
                "win_rate_delta": win_rate_delta,
                "required_edge_bps": round(float(required_edge_bps), 4),
                "verdict": verdict,
            }
        )

    # Sensitivity sweep: keep realized transaction cost fixed at the configured
    # 15bps default, but vary the forecast-edge gate threshold to see when the
    # filter becomes binding.  This answers whether the current threshold is
    # merely diagnostic or actually improves candidate quality.
    for threshold_bps in SENSITIVITY_THRESHOLDS_BPS:
        for pct in TOP_PCTS:
            top_key = f"top_{int(pct * 100)}pct"
            n = max(1, int(len(combined) * pct))
            baseline = combined.iloc[:n].copy()
            selected = baseline[pd.to_numeric(baseline["forecast_edge_bps"], errors="coerce") > threshold_bps].copy()
            baseline_metrics = _metrics(baseline, target_col, net_cost_per_trade=net_cost_per_trade)
            selected_metrics = _metrics(selected, target_col, net_cost_per_trade=net_cost_per_trade)
            net_delta = None
            if baseline_metrics.get("net_roi") is not None and selected_metrics.get("net_roi") is not None:
                net_delta = round(float(selected_metrics["net_roi"]) - float(baseline_metrics["net_roi"]), 4)
            dd_delta = None
            if baseline_metrics.get("max_drawdown_net") is not None and selected_metrics.get("max_drawdown_net") is not None:
                dd_delta = round(float(selected_metrics["max_drawdown_net"]) - float(baseline_metrics["max_drawdown_net"]), 4)
            avg_trade_delta = None
            if baseline_metrics.get("avg_trade_net_bps") is not None and selected_metrics.get("avg_trade_net_bps") is not None:
                avg_trade_delta = round(float(selected_metrics["avg_trade_net_bps"]) - float(baseline_metrics["avg_trade_net_bps"]), 4)
            threshold_sweep_rows.append(
                {
                    "model": model_name,
                    "top_k": top_key,
                    "gate_threshold_bps": round(float(threshold_bps), 4),
                    "actual_cost_bps_subtracted": round(float(required_edge_bps), 4),
                    "baseline_trade_count": baseline_metrics.get("trade_count"),
                    "selected_trade_count": selected_metrics.get("trade_count"),
                    "filter_retention_rate": round(float(len(selected) / len(baseline)), 4) if len(baseline) else None,
                    "baseline_net_roi": baseline_metrics.get("net_roi"),
                    "selected_net_roi": selected_metrics.get("net_roi"),
                    "net_roi_delta": net_delta,
                    "baseline_max_drawdown_net": baseline_metrics.get("max_drawdown_net"),
                    "selected_max_drawdown_net": selected_metrics.get("max_drawdown_net"),
                    "max_drawdown_delta": dd_delta,
                    "baseline_avg_trade_net_bps": baseline_metrics.get("avg_trade_net_bps"),
                    "selected_avg_trade_net_bps": selected_metrics.get("avg_trade_net_bps"),
                    "avg_trade_net_bps_delta": avg_trade_delta,
                }
            )

    return {
        "model": model_name,
        "fold_windows": fold_windows,
        "total_oos_rows": int(len(combined)),
        "overall_oos_base_rate": round(float(combined[target_col].mean()), 4),
        "rows": top_rows,
        "threshold_sweep_rows": threshold_sweep_rows,
    }


def _row_rank_key(row: dict[str, Any]) -> tuple[float, float, float, float]:
    # Prefer objective net improvement, then average-trade quality, then lower drawdown.
    return (
        float(row.get("net_roi_delta") if row.get("net_roi_delta") is not None else -999.0),
        float(row.get("avg_trade_net_bps_delta") if row.get("avg_trade_net_bps_delta") is not None else -999.0),
        -float(row.get("max_drawdown_delta") if row.get("max_drawdown_delta") is not None else 999.0),
        float(row.get("cost_aware", {}).get("net_roi") or -999.0),
    )


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "verdict": "no_backtest_rows",
            "operator_summary": "沒有產生可比較的 OOS rows，不能判定改善。",
        }
    improved_net_and_risk = [row for row in rows if row.get("verdict") == "improved_net_and_risk"]
    improved_quality = [row for row in rows if row.get("verdict") == "improved_quality_tradeoff"]
    non_binding = [row for row in rows if row.get("verdict") == "no_effect_non_binding"]
    worse = [row for row in rows if row.get("verdict") == "worse_or_not_supported"]
    non_empty = [row for row in rows if row.get("cost_aware", {}).get("trade_count", 0) > 0]
    best = max(rows, key=_row_rank_key)
    deployable_claim_allowed = False

    if len(non_binding) == len(rows):
        verdict = "cost_gate_non_binding_on_topk"
        operator_summary = (
            "15bps cost-aware gate 對目前 OOS Top-K 完全沒有過濾力：所有高信念候選的訓練期校準 forecast edge 都高於成本門檻。"
            "這代表 paper/shadow 候選不是乾等，但不能宣稱此 gate 本身改善了 PnL；下一步要提高/動態化 edge 門檻或接 LOB 成本。"
        )
    elif improved_net_and_risk:
        verdict = "improved_for_paper_shadow"
        operator_summary = (
            "成本感知 gate 在至少一組 OOS Top-K 上同時改善 net ROI 且沒有增加回撤；"
            "可作為 paper/shadow 候選的下一步，不是 live 下單證明。"
        )
    elif improved_quality:
        verdict = "quality_tradeoff_not_total_roi"
        operator_summary = (
            "成本感知 gate 提升單筆期望或風險品質，但犧牲部分總 ROI/交易數；"
            "適合低頻高信念 paper/shadow，不足以宣稱 live 改善。"
        )
    elif non_empty and len(worse) < len(rows):
        verdict = "mixed_or_inconclusive"
        operator_summary = (
            "回測結果混合；成本感知 gate 沒有穩定改善所有 Top-K。"
            "應先補 runtime microstructure/LOB forecast，再做下一輪回測。"
        )
    else:
        verdict = "not_improved_or_no_evidence"
        operator_summary = (
            "目前 15bps cost-aware gate 未在 OOS Top-K 反事實中證明改善；"
            "不能把此改動當成收益改善，只能保留 fail-closed 診斷價值。"
        )

    return {
        "verdict": verdict,
        "operator_summary": operator_summary,
        "deployable_claim_allowed": deployable_claim_allowed,
        "row_count": len(rows),
        "rows_with_cost_aware_trades": len(non_empty),
        "non_binding_rows": len(non_binding),
        "improved_net_and_risk_rows": len(improved_net_and_risk),
        "improved_quality_tradeoff_rows": len(improved_quality),
        "worse_or_not_supported_rows": len(worse),
        "best_row": best,
    }


def _summarize_threshold_sweep(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"verdict": "no_threshold_sweep_rows"}
    binding = [
        row for row in rows
        if (row.get("selected_trade_count") or 0) > 0
        and (row.get("selected_trade_count") or 0) < (row.get("baseline_trade_count") or 0)
    ]
    positive_net = [row for row in binding if (row.get("net_roi_delta") or 0) > EPSILON]
    positive_quality = [
        row for row in binding
        if (row.get("avg_trade_net_bps_delta") or 0) > EPSILON
        and (row.get("max_drawdown_delta") is None or (row.get("max_drawdown_delta") or 0) <= EPSILON)
    ]
    best_binding = max(binding, key=_row_rank_key) if binding else None
    return {
        "verdict": "binding_thresholds_available" if binding else "no_binding_threshold_in_sweep",
        "sweep_row_count": len(rows),
        "binding_row_count": len(binding),
        "positive_net_binding_rows": len(positive_net),
        "positive_quality_binding_rows": len(positive_quality),
        "best_binding_row": best_binding,
    }


def main() -> None:
    config = _load_yaml_config()
    cost_components = resolve_cost_aware_edge_config(config)
    required_edge_bps = round(sum(float(v) for v in cost_components.values()), 4)
    data, target_col = topk.load_frame()
    generated_at = datetime.now(timezone.utc).isoformat()
    result: dict[str, Any] = {
        "generated_at": generated_at,
        "artifact": str(OUT_PATH.relative_to(PROJECT_ROOT)),
        "target_col": target_col,
        "samples": int(len(data)),
        "models_evaluated": MODELS,
        "top_k_grid": [f"top_{int(pct * 100)}pct" for pct in TOP_PCTS],
        "methodology": {
            "split_source": "ModelLeaderboard._get_walk_forward_splits first 4 folds; train windows strictly precede test windows",
            "baseline": "rank each model's OOS rows by confidence and take Top-K candidates",
            "cost_aware": "same Top-K candidates filtered by training-window calibrated forecast_edge_bps > required_edge_bps",
            "net_pnl": "realized simulated_pyramid_pnl minus required_edge_bps per selected trade",
            "forecast_edge_calibration": f"training rows sorted by score; mean pnl of rows with score >= test score; minimum cohort {DEFAULT_MIN_CALIBRATION_ROWS}",
            "live_scope": "paper_shadow_counterfactual_only_not_live_deployment_proof",
        },
        "cost_model": {
            "required_edge_bps": required_edge_bps,
            "cost_components_bps": cost_components,
        },
        "models": {},
        "rows": [],
        "threshold_sweep_rows": [],
    }

    for model_name in MODELS:
        print(f"Evaluating {model_name} with cost-aware counterfactual...")
        report = evaluate_model(data, target_col, model_name, required_edge_bps=required_edge_bps)
        if report is None:
            continue
        result["models"][model_name] = {
            "fold_windows": report["fold_windows"],
            "total_oos_rows": report["total_oos_rows"],
            "overall_oos_base_rate": report["overall_oos_base_rate"],
        }
        result["rows"].extend(report["rows"])
        result["threshold_sweep_rows"].extend(report.get("threshold_sweep_rows") or [])

    result["summary"] = _summarize(result["rows"])
    result["threshold_sweep_summary"] = _summarize_threshold_sweep(result["threshold_sweep_rows"])
    result["limitations"] = [
        "forecast_edge_bps is a historical training-window calibration, not a live LOB/microstructure forecast",
        "net_pnl subtracts the configured cost threshold per trade; it does not model variable spread/slippage by timestamp",
        "passing this artifact only supports paper/shadow observation; live buy/add remains blocked by current lane hard gates",
    ]
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2, allow_nan=False))
    print(json.dumps({"threshold_sweep_summary": result["threshold_sweep_summary"]}, ensure_ascii=False, indent=2, allow_nan=False))
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
