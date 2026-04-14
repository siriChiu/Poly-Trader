import json
import sqlite3
from pathlib import Path

import pandas as pd

from backtesting.model_leaderboard import MIN_TRAIN_SAMPLES, ModelLeaderboard
from server.routes.api import DB_PATH, load_model_leaderboard_frame

TOP_PCTS = [0.01, 0.02, 0.05, 0.10, 0.20]
MODELS = ["xgboost", "random_forest", "logistic_regression"]
OUT_PATH = Path("model/topk_walkforward_precision.json")


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
    df["regime_label"] = df["regime_label"].fillna("unknown").astype(str).str.lower()

    target_col = "simulated_pyramid_win" if "simulated_pyramid_win" in df.columns else "label_spot_long_win"
    df = df.dropna(subset=[target_col]).copy()
    df[target_col] = df[target_col].fillna(0).astype(int)
    return df, target_col


def summarize_subset(sub: pd.DataFrame, target_col: str) -> dict:
    wins = int(sub[target_col].sum())
    return {
        "n": int(len(sub)),
        "win_rate": round(float(sub[target_col].mean()), 4) if len(sub) else None,
        "avg_score": round(float(sub["score"].mean()), 4) if len(sub) else None,
        "wins": wins,
        "losses": int(len(sub) - wins),
        "regime_mix": {k: int(v) for k, v in sub["regime_label"].value_counts().to_dict().items()},
    }


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

        scored = test_df[["timestamp", "regime_label", target_col, "close_price"]].copy()
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
            for pct in [0.05, 0.10, 0.20]:
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
        for pct in [0.05, 0.10, 0.20]:
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
    result = {
        "target_col": target_col,
        "samples": int(len(data)),
        "models": {},
    }
    for model_name in MODELS:
        print(f"Evaluating {model_name}...")
        report = evaluate_model(data, target_col, model_name)
        if report is not None:
            result["models"][model_name] = report
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
