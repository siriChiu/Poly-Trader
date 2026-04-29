import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from backtesting.model_leaderboard import MIN_TRAIN_SAMPLES, ModelLeaderboard
from server.routes.api import DB_PATH, load_model_leaderboard_frame

TOP_PCTS = [0.01, 0.02, 0.05, 0.10]
MODELS = ["xgboost", "random_forest", "logistic_regression"]
OUT_PATH = Path("data/high_conviction_topk_oos_matrix.json")
LEGACY_OUT_PATH = Path("model/topk_walkforward_precision.json")
MINIMUM_DEPLOYMENT_GATES = {
    "min_trades": 50,
    "min_win_rate": 0.60,
    "max_drawdown": 0.08,
    "min_profit_factor": 1.50,
    "worst_fold": "non_negative_or_above_baseline",
    "support_route": "deployable",
}
LIVE_GUARDRAIL_FAILURES = {"support_route_not_deployable", "deployment_blocker_active"}


def _round_or_none(value: Any, digits: int = 4) -> Optional[float]:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(numeric):
        return None
    return round(numeric, digits)


def _safe_profit_factor(pnl: pd.Series) -> Optional[float]:
    if pnl.empty:
        return None
    gross_profit = float(pnl[pnl > 0].sum())
    gross_loss = abs(float(pnl[pnl < 0].sum()))
    if gross_loss <= 0:
        return 999.0 if gross_profit > 0 else 0.0
    return round(gross_profit / gross_loss, 4)


def _max_drawdown_from_pnl(pnl: pd.Series) -> Optional[float]:
    if pnl.empty:
        return None
    cumulative = pnl.cumsum()
    peak = cumulative.cummax()
    drawdown = peak - cumulative
    return round(float(drawdown.max()), 4)


def _pnl_series_for_subset(sub: pd.DataFrame) -> pd.Series:
    for col in ["simulated_pyramid_pnl", "future_return_pct"]:
        if col in sub.columns:
            return pd.to_numeric(sub[col], errors="coerce").fillna(0.0).astype(float)
    return pd.Series([], dtype=float)


def _load_support_context() -> dict:
    """Load current-live support/blocker truth so top-k candidates fail closed."""
    probe_path = Path("data/live_predict_probe.json")
    if not probe_path.exists():
        return {
            "support_route_verdict": "not_evaluated",
            "deployment_blocker": "unknown",
        }
    try:
        probe = json.loads(probe_path.read_text(encoding="utf-8"))
    except Exception:
        return {
            "support_route_verdict": "not_evaluated",
            "deployment_blocker": "unreadable_live_probe",
        }
    keys = [
        "support_route_verdict",
        "support_governance_route",
        "support_route_deployable",
        "deployment_blocker",
        "runtime_closure_state",
        "current_live_structure_bucket",
        "current_live_structure_bucket_rows",
        "minimum_support_rows",
        "allowed_layers",
        "signal",
    ]
    context = {key: probe.get(key) for key in keys if key in probe}
    context.setdefault("support_route_verdict", "not_evaluated")
    context.setdefault("deployment_blocker", None)
    return context


def _coalesce_regime_label(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize merge/asof suffix variants into one lower-case regime_label column."""
    df = df.copy()
    candidates = [col for col in ["regime_label", "regime_label_y", "regime_label_x"] if col in df.columns]
    if not candidates:
        df["regime_label"] = "unknown"
        return df
    regime = df[candidates[0]]
    for col in candidates[1:]:
        regime = regime.combine_first(df[col])
    df["regime_label"] = regime.fillna("unknown").astype(str).str.lower()
    for col in ["regime_label_x", "regime_label_y"]:
        if col in df.columns:
            df = df.drop(columns=[col])
    return df


def load_frame() -> tuple[pd.DataFrame, str]:
    df = load_model_leaderboard_frame(DB_PATH)
    if df.empty:
        raise RuntimeError("empty leaderboard frame")

    conn = sqlite3.connect(DB_PATH)
    regime_df = pd.read_sql_query(
        "SELECT timestamp, COALESCE(regime_label, 'unknown') as regime_label FROM features_normalized",
        conn,
    )
    conn.close()
    regime_df["timestamp"] = pd.to_datetime(regime_df["timestamp"], format="mixed", utc=False)
    regime_df = regime_df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp")

    df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed", utc=False)
    df = df.sort_values("timestamp")
    df = pd.merge_asof(df, regime_df, on="timestamp", direction="nearest", tolerance=pd.Timedelta("10min"))
    df = _coalesce_regime_label(df)

    target_col = "simulated_pyramid_win" if "simulated_pyramid_win" in df.columns else "label_spot_long_win"
    df = df.dropna(subset=[target_col]).copy()
    df[target_col] = df[target_col].fillna(0).astype(int)
    return df, target_col


def summarize_subset(sub: pd.DataFrame, target_col: str) -> dict:
    wins = int(sub[target_col].sum())
    chronological = sub.sort_values("timestamp") if "timestamp" in sub.columns else sub
    pnl = _pnl_series_for_subset(chronological)
    oos_roi = _round_or_none(float(pnl.sum())) if not pnl.empty else None
    profit_factor = _safe_profit_factor(pnl)
    max_drawdown = _max_drawdown_from_pnl(pnl)
    regime_mix = {}
    if "regime_label" in sub.columns:
        regime_mix = {k: int(v) for k, v in sub["regime_label"].value_counts().to_dict().items()}
    return {
        "n": int(len(sub)),
        "trade_count": int(len(sub)),
        "win_rate": round(float(sub[target_col].mean()), 4) if len(sub) else None,
        "avg_score": round(float(sub["score"].mean()), 4) if len(sub) else None,
        "oos_roi": oos_roi,
        "profit_factor": profit_factor,
        "max_drawdown": max_drawdown,
        "wins": wins,
        "losses": int(len(sub) - wins),
        "regime_mix": regime_mix,
    }


def _support_route_is_deployable(support_context: dict) -> bool:
    route = str(support_context.get("support_route_verdict") or "").lower()
    explicit = support_context.get("support_route_deployable")
    if explicit is not None:
        return bool(explicit)
    return route in {"deployable", "exact_bucket_supported", "support_route_deployable"}


def _deployment_blocker_active(support_context: dict) -> bool:
    blocker = support_context.get("deployment_blocker")
    if blocker is None:
        blocker = support_context.get("runtime_closure_state")
    text = str(blocker or "").strip().lower()
    return text not in {"", "none", "no_deployment_blocker", "breaker_clear", "support_closed_trade_floor_hold_only"}


def _gate_failures(metrics: dict, worst_fold: Optional[float], support_context: dict, gates: dict) -> list[str]:
    failures: list[str] = []
    trade_count = int(metrics.get("trade_count", metrics.get("n", 0)) or 0)
    win_rate = metrics.get("win_rate")
    max_drawdown = metrics.get("max_drawdown")
    profit_factor = metrics.get("profit_factor")

    if trade_count < int(gates.get("min_trades", 50)):
        failures.append("min_trades_not_met")
    if win_rate is None or float(win_rate) < float(gates.get("min_win_rate", 0.60)):
        failures.append("min_win_rate_not_met")
    if max_drawdown is None or float(max_drawdown) > float(gates.get("max_drawdown", 0.08)):
        failures.append("max_drawdown_too_high")
    if profit_factor is None or float(profit_factor) < float(gates.get("min_profit_factor", 1.50)):
        failures.append("profit_factor_too_low")
    if worst_fold is None:
        failures.append("worst_fold_missing")
    elif str(gates.get("worst_fold", "")).startswith("non_negative") and float(worst_fold) < 0:
        failures.append("worst_fold_negative")
    if not _support_route_is_deployable(support_context):
        failures.append("support_route_not_deployable")
    if _deployment_blocker_active(support_context):
        failures.append("deployment_blocker_active")
    return failures


def _fold_slice_metrics(report: dict, top_key: str, regime: str) -> list[dict]:
    metrics: list[dict] = []
    for fold in report.get("folds", []) or []:
        if regime == "all":
            item = (fold.get("top_slices") or {}).get(top_key)
        else:
            item = ((fold.get("regime_top_slices") or {}).get(regime) or {}).get(top_key)
        if isinstance(item, dict):
            metrics.append(item)
    return metrics


def _worst_fold_roi(report: dict, top_key: str, regime: str) -> Optional[float]:
    values = [
        float(item["oos_roi"])
        for item in _fold_slice_metrics(report, top_key, regime)
        if item.get("oos_roi") is not None
    ]
    if not values:
        return None
    return round(min(values), 4)


def build_high_conviction_oos_matrix_rows(
    model_name: str,
    report: dict,
    support_context: Optional[dict] = None,
    feature_profile: str = "current_full",
    gates: Optional[dict] = None,
) -> list[dict]:
    """Flatten aggregate/fold top-k evidence into deployment-gated matrix rows."""
    support_context = dict(support_context or {"support_route_verdict": "not_evaluated"})
    gates = dict(gates or MINIMUM_DEPLOYMENT_GATES)
    rows: list[dict] = []

    def _append_row(regime: str, top_key: str, metrics: dict) -> None:
        worst_fold = _worst_fold_roi(report, top_key, regime)
        failures = _gate_failures(metrics, worst_fold, support_context, gates)
        live_gate_failures = [failure for failure in failures if failure in LIVE_GUARDRAIL_FAILURES]
        model_gate_failures = [failure for failure in failures if failure not in LIVE_GUARDRAIL_FAILURES]
        oos_gate_passed = not model_gate_failures
        blocked_only_by_live_guardrails = bool(failures) and oos_gate_passed and bool(live_gate_failures)
        deployable_verdict = "deployable" if not failures else "not_deployable"
        if deployable_verdict == "deployable":
            deployment_candidate_tier = "deployable"
        elif blocked_only_by_live_guardrails:
            deployment_candidate_tier = "runtime_blocked_oos_pass"
        else:
            deployment_candidate_tier = "research_oos_gate_failed"
        rows.append(
            {
                "model": model_name,
                "feature_profile": feature_profile,
                "regime": regime,
                "top_k": top_key,
                "oos_roi": _round_or_none(metrics.get("oos_roi")),
                "win_rate": _round_or_none(metrics.get("win_rate")),
                "profit_factor": _round_or_none(metrics.get("profit_factor")),
                "max_drawdown": _round_or_none(metrics.get("max_drawdown")),
                "worst_fold": _round_or_none(worst_fold),
                "trade_count": int(metrics.get("trade_count", metrics.get("n", 0)) or 0),
                "avg_score": _round_or_none(metrics.get("avg_score")),
                "wins": int(metrics.get("wins", 0) or 0),
                "losses": int(metrics.get("losses", 0) or 0),
                "regime_mix": dict(metrics.get("regime_mix") or {}),
                "support_route": support_context.get("support_route_verdict", "not_evaluated"),
                "support_governance_route": support_context.get("support_governance_route"),
                "deployment_blocker": support_context.get("deployment_blocker"),
                "runtime_closure_state": support_context.get("runtime_closure_state"),
                "current_live_structure_bucket": support_context.get("current_live_structure_bucket"),
                "minimum_deployment_gates": gates,
                "deployable_verdict": deployable_verdict,
                "deployment_candidate_tier": deployment_candidate_tier,
                "gate_failures": failures,
                "model_gate_failures": model_gate_failures,
                "live_gate_failures": live_gate_failures,
                "oos_gate_passed": oos_gate_passed,
                "blocked_only_by_live_guardrails": blocked_only_by_live_guardrails,
            }
        )

    for top_key, metrics in (report.get("aggregate_top_slices") or {}).items():
        _append_row("all", top_key, metrics)
    for regime, slices in (report.get("aggregate_regime_top_slices") or {}).items():
        for top_key, metrics in (slices or {}).items():
            _append_row(str(regime), top_key, metrics)
    return rows


def evaluate_model(data: pd.DataFrame, target_col: str, model_name: str) -> dict | None:
    lb = ModelLeaderboard(data, target_col=target_col)
    splits = lb._get_walk_forward_splits()
    feature_cols = [c for c in data.columns if c.startswith("feat_")]

    fold_reports = []
    all_test_rows = []
    for i, (ts, te, test_s, test_e) in enumerate(splits[:4]):
        train_df = data[(data["timestamp"] >= ts) & (data["timestamp"] < te)].copy()
        test_df = data[(data["timestamp"] >= test_s) & (data["timestamp"] < test_e)].copy()
        if len(train_df) < MIN_TRAIN_SAMPLES or len(test_df) < 50:
            continue

        if model_name == "rule_baseline":
            score = (1.0 - (test_df["feat_4h_bias50"].fillna(0).values + 5) / 15.0).clip(0.0, 1.0)
        else:
            model = lb._train_model(
                train_df[feature_cols].fillna(0).values,
                train_df[target_col].values,
                model_name,
            )
            if model is None:
                return None
            score = lb._get_confidence(model, test_df[feature_cols].fillna(0).values, model_name)

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
        scored["score"] = score
        scored = scored.sort_values("score", ascending=False).reset_index(drop=True)
        scored["fold"] = i
        all_test_rows.append(scored)

        top_slices = {}
        for pct in TOP_PCTS:
            n = max(1, int(len(scored) * pct))
            top_slices[f"top_{int(pct * 100)}pct"] = summarize_subset(scored.iloc[:n], target_col)

        regime_slices = {}
        for regime in sorted(scored["regime_label"].unique()):
            reg_df = scored[scored["regime_label"] == regime].reset_index(drop=True)
            if len(reg_df) < 20:
                continue
            regime_slices[regime] = {}
            for pct in TOP_PCTS:
                n = max(1, int(len(reg_df) * pct))
                regime_slices[regime][f"top_{int(pct * 100)}pct"] = summarize_subset(reg_df.iloc[:n], target_col)

        fold_reports.append(
            {
                "fold": i,
                "train_start": str(train_df["timestamp"].min()),
                "train_end": str(train_df["timestamp"].max()),
                "test_start": str(test_df["timestamp"].min()),
                "test_end": str(test_df["timestamp"].max()),
                "train_rows": int(len(train_df)),
                "test_rows": int(len(test_df)),
                "top_slices": top_slices,
                "regime_top_slices": regime_slices,
            }
        )

    if not fold_reports:
        return None

    combined = pd.concat(all_test_rows, ignore_index=True).sort_values("score", ascending=False).reset_index(drop=True)
    aggregate_top = {}
    for pct in TOP_PCTS:
        n = max(1, int(len(combined) * pct))
        aggregate_top[f"top_{int(pct * 100)}pct"] = summarize_subset(combined.iloc[:n], target_col)

    aggregate_regime = {}
    for regime in sorted(combined["regime_label"].unique()):
        reg_df = combined[combined["regime_label"] == regime].reset_index(drop=True)
        if len(reg_df) < 20:
            continue
        aggregate_regime[regime] = {}
        for pct in TOP_PCTS:
            n = max(1, int(len(reg_df) * pct))
            aggregate_regime[regime][f"top_{int(pct * 100)}pct"] = summarize_subset(reg_df.iloc[:n], target_col)

    return {
        "folds": fold_reports,
        "aggregate_top_slices": aggregate_top,
        "aggregate_regime_top_slices": aggregate_regime,
        "overall_oos_base_rate": round(float(combined[target_col].mean()), 4),
        "total_oos_rows": int(len(combined)),
    }


def main() -> None:
    data, target_col = load_frame()
    support_context = _load_support_context()
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_col": target_col,
        "samples": int(len(data)),
        "top_k_grid": [f"top_{int(pct * 100)}pct" for pct in TOP_PCTS],
        "minimum_deployment_gates": MINIMUM_DEPLOYMENT_GATES,
        "support_context": support_context,
        "artifact": str(OUT_PATH),
        "rows": [],
        "models": {},
    }
    for model_name in MODELS:
        print(f"Evaluating {model_name}...")
        report = evaluate_model(data, target_col, model_name)
        if report is not None:
            result["models"][model_name] = report
            result["rows"].extend(build_high_conviction_oos_matrix_rows(model_name, report, support_context=support_context))
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    LEGACY_OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    LEGACY_OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
