#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backtesting.model_leaderboard import ModelLeaderboard
from backtesting.strategy_lab import (  # noqa: E402
    AUTO_STRATEGY_NAME_PREFIX,
    delete_strategy,
    load_all_strategies,
    run_hybrid_backtest,
)
from backtesting.strategy_param_search import expand_search_space, rank_param_search_results  # noqa: E402
from server.routes import api as api_module  # noqa: E402

OUTPUT_PATH = PROJECT_ROOT / "data" / "model_strategy_param_scan_latest.json"
DEFAULT_TOP_PER_MODEL = 2
DEFAULT_MODELS = list(getattr(ModelLeaderboard, "REFRESH_MODELS", []) or ["rule_baseline", "logistic_regression", "xgboost", "lightgbm", "catboost", "random_forest"])


def _timestamp_key(value: Any) -> str:
    text = str(value or "")
    if "T" in text:
        text = text.replace("T", " ")
    return text.replace("Z", "")[:19]


def _mean(values: Iterable[float]) -> float:
    rows = [float(v) for v in values if v is not None]
    return float(sum(rows) / len(rows)) if rows else 0.0


def _load_active_market_rows() -> Dict[str, Any]:
    rows = list(api_module._load_strategy_data())
    if not rows:
        raise RuntimeError("No active strategy rows available")

    timestamps = [_timestamp_key(row[0]) for row in rows]
    prices = [float(row[1]) for row in rows]
    bias50 = [float(row[2]) if len(row) > 2 and row[2] is not None else 0.0 for row in rows]
    bias200 = [float(row[3]) if len(row) > 3 and row[3] is not None else 0.0 for row in rows]
    nose = [float(row[4]) if len(row) > 4 and row[4] is not None else 0.5 for row in rows]
    pulse = [float(row[5]) if len(row) > 5 and row[5] is not None else 0.5 for row in rows]
    ear = [float(row[6]) if len(row) > 6 and row[6] is not None else 0.0 for row in rows]
    regimes = [str(row[7]).lower() if len(row) > 7 and row[7] else "unknown" for row in rows]
    bb_pct_b_4h = [float(row[8]) if len(row) > 8 and row[8] is not None else None for row in rows]
    dist_bb_lower_4h = [float(row[9]) if len(row) > 9 and row[9] is not None else None for row in rows]
    dist_swing_low_4h = [float(row[10]) if len(row) > 10 and row[10] is not None else None for row in rows]
    local_bottom_score = [float(row[11]) if len(row) > 11 and row[11] is not None else 0.0 for row in rows]
    local_top_score = [float(row[12]) if len(row) > 12 and row[12] is not None else 0.0 for row in rows]
    local_top_by_ts = {ts: local_top_score[idx] for idx, ts in enumerate(timestamps)}

    return {
        "timestamps": timestamps,
        "prices": prices,
        "bias50": bias50,
        "bias200": bias200,
        "nose": nose,
        "pulse": pulse,
        "ear": ear,
        "regimes": regimes,
        "bb_pct_b_4h": bb_pct_b_4h,
        "dist_bb_lower_4h": dist_bb_lower_4h,
        "dist_swing_low_4h": dist_swing_low_4h,
        "local_bottom_score": local_bottom_score,
        "local_top_score": local_top_score,
        "local_top_by_ts": local_top_by_ts,
        "row_count": len(rows),
    }


def _load_training_frame() -> Dict[str, Any]:
    train_df = api_module.load_model_leaderboard_frame(str(PROJECT_ROOT / "poly_trader.db"))
    if train_df.empty:
        raise RuntimeError("Model leaderboard frame is empty")
    target_col = "simulated_pyramid_win" if "simulated_pyramid_win" in train_df.columns else "label_spot_long_win"
    train_df = train_df.dropna(subset=[target_col]).copy()
    if train_df.empty:
        raise RuntimeError(f"No usable target rows for {target_col}")
    feature_cols = [col for col in train_df.columns if col.startswith("feat_")]
    if not feature_cols:
        raise RuntimeError("No feat_* columns available for model training")
    train_df["timestamp"] = train_df["timestamp"].map(_timestamp_key)
    return {
        "train_df": train_df,
        "target_col": target_col,
        "feature_cols": feature_cols,
    }


def _default_confidence_from_bias(bias50: List[float]) -> List[float]:
    return [max(0.0, min(1.0, 1.0 - float(b) / 20.0)) for b in bias50]


def _build_confidence_map(model_name: str, training_bundle: Dict[str, Any]) -> Dict[str, Any]:
    train_df = training_bundle["train_df"]
    target_col = training_bundle["target_col"]
    feature_cols = training_bundle["feature_cols"]
    lb = ModelLeaderboard(train_df.copy(), target_col=target_col)

    if model_name == "rule_baseline":
        confidence = [max(0.0, min(1.0, 1.0 - (float(v) + 5.0) / 15.0)) for v in train_df["feat_4h_bias50"].fillna(0.0).tolist()]
        return {
            "model_name": model_name,
            "timestamp_to_confidence": {ts: float(conf) for ts, conf in zip(train_df["timestamp"].tolist(), confidence)},
            "feature_count": 1,
            "target_col": target_col,
            "feature_importances": {},
        }

    model = lb._train_model(
        train_df[feature_cols].fillna(0).values,
        train_df[target_col].fillna(0).astype(int).values,
        model_name,
    )
    if model is None:
        raise RuntimeError(f"{model_name} returned None model")

    confidence = lb._get_confidence(model, train_df[feature_cols].fillna(0).values, model_name)
    confidence_map = {ts: float(conf) for ts, conf in zip(train_df["timestamp"].tolist(), confidence)}

    feature_importances: Dict[str, float] = {}
    if hasattr(model, "feature_importances_"):
        raw_values = getattr(model, "feature_importances_", None)
        values = list(raw_values) if raw_values is not None else []
        feature_importances = {
            feature_cols[idx]: round(float(values[idx]), 6)
            for idx in range(min(len(values), len(feature_cols)))
            if float(values[idx]) > 0
        }
    elif hasattr(model, "coef_"):
        coef = getattr(model, "coef_")
        try:
            flat = list(coef[0])
        except Exception:
            flat = []
        feature_importances = {
            feature_cols[idx]: round(abs(float(flat[idx])), 6)
            for idx in range(min(len(flat), len(feature_cols)))
            if abs(float(flat[idx])) > 0
        }

    top_features = dict(sorted(feature_importances.items(), key=lambda item: item[1], reverse=True)[:10])
    return {
        "model_name": model_name,
        "timestamp_to_confidence": confidence_map,
        "feature_count": len(feature_cols),
        "target_col": target_col,
        "feature_importances": top_features,
    }


def _base_strategy_params(model_name: str) -> Dict[str, Any]:
    return {
        "model_name": model_name,
        "entry": {
            "bias50_max": 1.0,
            "nose_max": 0.40,
            "pulse_min": 0.0,
            "confidence_min": 0.50,
            "entry_quality_min": 0.55,
            "top_k_percent": 0,
            "allowed_regimes": ["bull", "chop"],
        },
        "layers": [0.25, 0.25, 0.50],
        "stop_loss": -0.03,
        "take_profit_bias": 999.0,
        "take_profit_roi": 999.0,
        "turning_point": {
            "enabled": True,
            "bottom_score_min": 0.62,
            "top_score_take_profit": 0.80,
            "min_profit_pct": 0.0,
        },
        "editor_modules": ["turning_point"],
    }


def _search_space() -> Dict[str, List[Any]]:
    return {
        "entry.bias50_max": [0.0, 2.0, 3.0],
        "entry.confidence_min": [0.45, 0.55],
        "entry.entry_quality_min": [0.50, 0.55],
        "entry.allowed_regimes": [
            ["bull", "chop"],
            ["bull", "chop", "bear", "unknown"],
        ],
        "stop_loss": [-0.03, -0.05],
        "turning_point.bottom_score_min": [0.56, 0.62],
    }


def _apply_relative_bias_layers(params: Dict[str, Any]) -> Dict[str, Any]:
    variant = copy.deepcopy(params)
    entry = variant.setdefault("entry", {})
    bias50_max = float(entry.get("bias50_max", 0.0) or 0.0)
    entry["layer2_bias_max"] = round(bias50_max - 1.0, 4)
    entry["layer3_bias_max"] = round(bias50_max - 2.5, 4)
    return variant


def _summarize_result(result: Any, params: Dict[str, Any], active_bundle: Dict[str, Any], variant_label: str, model_name: str) -> Dict[str, Any]:
    trades = list(getattr(result, "trades", []) or [])
    local_top_by_ts = active_bundle["local_top_by_ts"]
    exit_local_scores = [
        float(local_top_by_ts.get(_timestamp_key(trade.get("timestamp")), 0.0))
        for trade in trades
    ]
    turning_point_exit_count = sum(1 for trade in trades if str(trade.get("reason") or "") == "tp_turning_point")
    avg_entry_quality = _mean(float(trade.get("entry_quality", 0.0) or 0.0) for trade in trades)
    avg_allowed_layers = _mean(float(trade.get("allowed_layers", 0.0) or 0.0) for trade in trades)

    return {
        "model_name": model_name,
        "variant": variant_label,
        "roi": round(float(getattr(result, "roi", 0.0) or 0.0), 4),
        "win_rate": round(float(getattr(result, "win_rate", 0.0) or 0.0), 4),
        "max_drawdown": round(float(getattr(result, "max_drawdown", 0.0) or 0.0), 4),
        "profit_factor": round(float(getattr(result, "profit_factor", 0.0) or 0.0), 4),
        "total_trades": int(getattr(result, "total_trades", 0) or 0),
        "total_pnl": round(float(getattr(result, "total_pnl", 0.0) or 0.0), 2),
        "avg_exit_local_top_score": round(_mean(exit_local_scores), 4),
        "turning_point_exit_count": int(turning_point_exit_count),
        "avg_entry_quality": round(avg_entry_quality, 4),
        "avg_allowed_layers": round(avg_allowed_layers, 4),
        "params": params,
    }


def _run_param_scan_for_model(model_name: str, confidence_bundle: Dict[str, Any], active_bundle: Dict[str, Any]) -> Dict[str, Any]:
    base_params = _base_strategy_params(model_name)
    variants = expand_search_space(base_params, _search_space())
    confidence_map = confidence_bundle["timestamp_to_confidence"]
    default_confidence = _default_confidence_from_bias(active_bundle["bias50"])

    rows: List[Dict[str, Any]] = []
    for variant in variants:
        params = _apply_relative_bias_layers(variant["params"])
        confidence = [
            float(confidence_map.get(ts, fallback))
            for ts, fallback in zip(active_bundle["timestamps"], default_confidence)
        ]
        result = run_hybrid_backtest(
            active_bundle["prices"],
            active_bundle["timestamps"],
            active_bundle["bias50"],
            active_bundle["bias200"],
            active_bundle["nose"],
            active_bundle["pulse"],
            active_bundle["ear"],
            confidence,
            params,
            regimes=active_bundle["regimes"],
            bb_pct_b_4h=active_bundle["bb_pct_b_4h"],
            dist_bb_lower_4h=active_bundle["dist_bb_lower_4h"],
            dist_swing_low_4h=active_bundle["dist_swing_low_4h"],
            local_bottom_score=active_bundle["local_bottom_score"],
            local_top_score=active_bundle["local_top_score"],
        )
        rows.append(_summarize_result(result, params, active_bundle, variant["variant"], model_name))

    ranked = rank_param_search_results(rows)
    best = ranked[0] if ranked else None
    return {
        "model_name": model_name,
        "feature_count": confidence_bundle["feature_count"],
        "target_col": confidence_bundle["target_col"],
        "feature_importances": confidence_bundle["feature_importances"],
        "variant_count": len(ranked),
        "best": best,
        "top_10": ranked[:10],
    }


def _purge_existing_auto_leaderboard_rows() -> List[str]:
    removed: List[str] = []
    for row in load_all_strategies(include_internal=True):
        name = str(row.get("name") or "")
        if name.startswith(AUTO_STRATEGY_NAME_PREFIX):
            if delete_strategy(name):
                removed.append(name)
    return removed


def _build_backtest_request(row: Dict[str, Any], *, rank_within_model: int) -> Dict[str, Any]:
    model_name = str(row.get("model_name") or "unknown")
    params = copy.deepcopy(row.get("params") or {})
    if model_name == "rule_baseline":
        strategy_type = "rule_based"
        strategy_name = f"{AUTO_STRATEGY_NAME_PREFIX}重掃 {model_name} #{rank_within_model:02d}"
    else:
        strategy_type = "hybrid"
        strategy_name = f"{AUTO_STRATEGY_NAME_PREFIX}重掃 {model_name} Hybrid #{rank_within_model:02d}"
    return {
        "name": strategy_name,
        "type": strategy_type,
        "initial_capital": 10000.0,
        "params": params,
    }


def _save_best_rows(scan_results: List[Dict[str, Any]], *, top_per_model: int) -> List[Dict[str, Any]]:
    saved: List[Dict[str, Any]] = []
    ordered = []
    for result in scan_results:
        ordered.extend((result.get("top_10") or [])[:top_per_model])

    for index, row in enumerate(ordered, start=1):
        model_name = str(row.get("model_name") or "unknown")
        model_rank = 1 + sum(1 for previous in ordered[: index - 1] if previous.get("model_name") == model_name)
        request = _build_backtest_request(row, rank_within_model=model_rank)
        payload = api_module._execute_strategy_run(request)
        if payload.get("error"):
            print(f"  跳過 {request['name']}：{payload.get('error')}")
            continue
        saved.append(
            {
                "name": request["name"],
                "model_name": model_name,
                "variant": row.get("variant"),
                "roi": row.get("roi"),
                "win_rate": row.get("win_rate"),
                "total_trades": row.get("total_trades"),
                "results": payload.get("results") or {},
            }
        )
    return saved


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="重新掃描所有模型，並以參數搜尋重建 Strategy Leaderboard。")
    parser.add_argument("--models", nargs="*", default=DEFAULT_MODELS, help="要掃描的模型名單")
    parser.add_argument("--top-per-model", type=int, default=DEFAULT_TOP_PER_MODEL, help="每個模型保留幾條最佳策略")
    parser.add_argument("--keep-existing-auto", action="store_true", help="保留既有 Auto Leaderboard 策略，不先清空")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    active_bundle = _load_active_market_rows()
    training_bundle = _load_training_frame()

    print(f"開始重掃模型：{', '.join(args.models)}")
    print(f"回測資料列數：{active_bundle['row_count']}，訓練 target：{training_bundle['target_col']}")

    scan_results: List[Dict[str, Any]] = []
    for model_name in args.models:
        print(f"\n[掃描] {model_name}")
        confidence_bundle = _build_confidence_map(model_name, training_bundle)
        result = _run_param_scan_for_model(model_name, confidence_bundle, active_bundle)
        best = result.get("best") or {}
        print(
            "  最佳：ROI={roi:+.2%} / PF={pf:.2f} / DD={dd:.2%} / trades={trades} / 參數={variant}".format(
                roi=float(best.get("roi", 0.0) or 0.0),
                pf=float(best.get("profit_factor", 0.0) or 0.0),
                dd=float(best.get("max_drawdown", 0.0) or 0.0),
                trades=int(best.get("total_trades", 0) or 0),
                variant=best.get("variant") or "n/a",
            )
        )
        scan_results.append(result)

    combined_ranked = rank_param_search_results([
        {**row, "model_name": result.get("model_name")}
        for result in scan_results
        for row in (result.get("top_10") or [])
    ])

    removed_auto = []
    if not args.keep_existing_auto:
        removed_auto = _purge_existing_auto_leaderboard_rows()
        print(f"\n已清除舊 Auto Leaderboard 策略：{len(removed_auto)} 筆")

    saved_rows = _save_best_rows(scan_results, top_per_model=max(1, int(args.top_per_model or 1)))
    payload = {
        "generated_at": api_module.datetime.utcnow().isoformat() + "Z",
        "models": args.models,
        "target_col": training_bundle["target_col"],
        "active_row_count": active_bundle["row_count"],
        "top_per_model": max(1, int(args.top_per_model or 1)),
        "removed_auto_strategies": removed_auto,
        "scan_results": scan_results,
        "combined_top_10": combined_ranked[:10],
        "saved_strategies": saved_rows,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n掃描完成，結果已寫入：{OUTPUT_PATH}")
    print(json.dumps({
        "saved_strategy_count": len(saved_rows),
        "saved_strategies": [
            {
                "name": row["name"],
                "model_name": row["model_name"],
                "roi": row["roi"],
                "win_rate": row["win_rate"],
                "total_trades": row["total_trades"],
            }
            for row in saved_rows
        ],
        "combined_top_5": combined_ranked[:5],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
