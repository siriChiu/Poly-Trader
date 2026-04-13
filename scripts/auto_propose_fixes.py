#!/usr/bin/env python3
"""
Auto-propose fixes based on current IC / sell_win / CV data.
Called by hb_parallel_runner.py or standalone.

Reads:
  data/full_ic_result.json
  model/ic_signs.json
  model/last_metrics.json
  poly_trader.db

Writes:
  issues.json (via IssueTracker)
"""
import os
import sqlite3
import json
import re
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from scripts.issues import IssueTracker

CORE_FEATURES = [
    "feat_eye", "feat_ear", "feat_nose", "feat_tongue", "feat_body",
    "feat_pulse", "feat_aura", "feat_mind", "feat_vix", "feat_dxy",
    "feat_rsi14", "feat_macd_hist", "feat_atr_pct", "feat_vwap_dev", "feat_bb_pct_b",
]


def check_db():
    conn = sqlite3.connect(str(ROOT / "poly_trader.db"))
    simulated_win = conn.execute(
        "SELECT AVG(simulated_pyramid_win) FROM labels WHERE simulated_pyramid_win IS NOT NULL"
    ).fetchone()[0]
    rows = conn.execute(
        "SELECT simulated_pyramid_win FROM labels WHERE simulated_pyramid_win IS NOT NULL ORDER BY id DESC LIMIT 200"
    ).fetchall()
    losing_streak = 0
    for r in rows:
        if r[0] == 0:
            losing_streak += 1
        else:
            break

    latest = conn.execute("SELECT timestamp FROM raw_market_data ORDER BY timestamp DESC LIMIT 1").fetchone()
    conn.close()

    latest_ts = latest[0] if latest else None
    age_min = None
    if latest_ts:
        from datetime import datetime as dt
        ts_str = str(latest_ts).replace(' ', 'T').split('.')[0]
        try:
            ts = dt.fromisoformat(ts_str)
            age_min = (dt.utcnow() - ts).total_seconds() / 60
        except Exception:
            pass

    return {
        "simulated_win_avg": round(simulated_win, 4) if simulated_win is not None else 0.5,
        "losing_streak": losing_streak,
        "raw_latest_age_min": round(age_min, 1) if age_min is not None else None,
    }


def check_ic(ic_data, full_ic_data=None):
    all_ics = ic_data.get("ic_global", {})
    tw_ics = ic_data.get("ic_tw", {})
    null_counts = ic_data.get("null_counts", {})
    ic_status = ic_data.get("ic_status", {})

    if full_ic_data:
        all_ics = full_ic_data.get("global_ics", all_ics)
        tw_ics = full_ic_data.get("tw_ics", tw_ics)

    if full_ic_data and full_ic_data.get("global_pass") is not None and full_ic_data.get("tw_pass") is not None:
        global_pass = int(full_ic_data.get("global_pass", 0))
        tw_pass = int(full_ic_data.get("tw_pass", 0))
        total_features = int(full_ic_data.get("total_features", len(all_ics) or len(CORE_FEATURES)))
    else:
        global_pass = sum(1 for c in CORE_FEATURES if abs(all_ics.get(c, 0)) >= 0.05)
        tw_pass = sum(1 for c in CORE_FEATURES if abs(tw_ics.get(c, 0)) >= 0.05)
        total_features = len(CORE_FEATURES)
    no_data = [c for c, s in null_counts.items() if s == 0]
    low_data = [c for c, s in null_counts.items() if s != 0 and ic_status.get(c) not in ("PASS", "FAIL")]

    return {
        "global_pass": global_pass,
        "tw_pass": tw_pass,
        "total_core": len(CORE_FEATURES),
        "total_features": total_features,
        "no_data": no_data,
        "low_data": low_data,
        "best_ic": max(all_ics.items(), key=lambda x: abs(x[1])) if all_ics else (None, 0),
        "worst_ic": min(all_ics.items(), key=lambda x: abs(x[1])) if all_ics else (None, 0),
    }


def check_metrics():
    mp = ROOT / "model" / "last_metrics.json"
    if mp.exists():
        with open(mp) as f:
            return json.load(f)
    return {}


def load_full_ic_data():
    path = ROOT / "data" / "full_ic_result.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def load_recent_tw_history(limit=3, current_entry=None):
    history = []
    data_dir = ROOT / "data"

    if current_entry and current_entry.get("tw_pass") is not None:
        history.append(current_entry)

    def _sort_key(path: Path):
        match = re.search(r"heartbeat_(.+)_summary\.json$", path.name)
        label = match.group(1) if match else path.stem
        if str(label).isdigit():
            # Prefer numbered heartbeats over aliases like "fast" so the
            # drift issue compares against stable chronological runs instead of
            # anonymous helper summaries from ad-hoc fast checks.
            return (0, -int(label), "")
        return (1, 0, str(label))

    for path in sorted(data_dir.glob("heartbeat_*_summary.json"), key=_sort_key):
        try:
            payload = json.loads(path.read_text())
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        ic_diag = payload.get("ic_diagnostics") or {}
        if not isinstance(ic_diag, dict):
            ic_diag = {}
        tw_pass = ic_diag.get("tw_pass")
        total_features = ic_diag.get("total_features")
        if tw_pass is None:
            parallel_results = payload.get("parallel_results") or {}
            if not isinstance(parallel_results, dict):
                parallel_results = {}
            full_ic_result = parallel_results.get("full_ic") or {}
            if not isinstance(full_ic_result, dict):
                full_ic_result = {}
            preview = full_ic_result.get("stdout_preview", "")
            match = None
            if preview:
                match = re.search(r"TW-IC:\s*(\d+)/(\d+)\s+passing", preview)
            if match:
                tw_pass = int(match.group(1))
                total_features = int(match.group(2))
        if tw_pass is None:
            continue
        candidate = {
            "heartbeat": str(payload.get("heartbeat")),
            "tw_pass": tw_pass,
            "total_features": total_features,
        }
        if not any(existing.get("heartbeat") == candidate["heartbeat"] for existing in history):
            history.append(candidate)
        if len(history) >= limit:
            break
    return history


def load_recent_drift_report():
    path = ROOT / "data" / "recent_drift_report.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def summarize_recent_drift(report):
    primary = (report or {}).get("primary_window") or {}
    summary = primary.get("summary") or {}
    if not primary:
        return "drift_report=missing"
    window = primary.get("window")
    alerts = primary.get("alerts") or []
    dominant_regime = summary.get("dominant_regime") or "unknown"
    dominant_share = summary.get("dominant_regime_share")
    win_rate = summary.get("win_rate")
    delta = summary.get("win_rate_delta_vs_full")
    interpretation = summary.get("drift_interpretation") or "unknown"
    quality = summary.get("quality_metrics") or {}
    feature_diag = summary.get("feature_diagnostics") or {}
    avg_pnl = quality.get("avg_simulated_pnl")
    avg_quality = quality.get("avg_simulated_quality")
    avg_dd_penalty = quality.get("avg_drawdown_penalty")
    spot_long_win_rate = quality.get("spot_long_win_rate")
    share_text = f"{dominant_share:.2%}" if isinstance(dominant_share, (int, float)) else "n/a"
    delta_text = f"{delta:+.4f}" if isinstance(delta, (int, float)) else "n/a"
    win_text = f"{win_rate:.4f}" if isinstance(win_rate, (int, float)) else "n/a"
    pnl_text = f"{avg_pnl:+.4f}" if isinstance(avg_pnl, (int, float)) else "n/a"
    quality_text = f"{avg_quality:.4f}" if isinstance(avg_quality, (int, float)) else "n/a"
    dd_text = f"{avg_dd_penalty:.4f}" if isinstance(avg_dd_penalty, (int, float)) else "n/a"
    spot_long_text = f"{spot_long_win_rate:.4f}" if isinstance(spot_long_win_rate, (int, float)) else "n/a"
    feature_summary = (
        f"feature_diag=variance:{feature_diag.get('low_variance_count', 0)}/{feature_diag.get('feature_count', 0)}"
        f", frozen:{feature_diag.get('frozen_count', 0)}"
        f", compressed:{feature_diag.get('compressed_count', 0)}"
        f", expected_static:{feature_diag.get('expected_static_count', 0)}"
        f", unexpected_frozen:{feature_diag.get('unexpected_frozen_count', 0)}"
        f", distinct:{feature_diag.get('low_distinct_count', 0)}"
        f", null_heavy:{feature_diag.get('null_heavy_count', 0)}"
    )
    low_variance_examples = feature_diag.get("low_variance_examples") or []
    low_distinct_examples = feature_diag.get("low_distinct_examples") or []
    frozen_examples = feature_diag.get("frozen_examples") or []
    compressed_examples = feature_diag.get("compressed_examples") or []
    expected_static_examples = feature_diag.get("expected_static_examples") or []
    unexpected_frozen_examples = feature_diag.get("unexpected_frozen_examples") or []
    null_heavy_examples = feature_diag.get("null_heavy_examples") or []
    example_bits = []
    if frozen_examples:
        example_bits.append(
            "frozen_examples=" + "/".join(
                f"{row.get('feature')}({row.get('std_ratio')}/{row.get('recent_distinct')})"
                for row in frozen_examples[:3]
            )
        )
    if compressed_examples:
        example_bits.append(
            "compressed_examples=" + "/".join(
                f"{row.get('feature')}({row.get('std_ratio')}/{row.get('recent_distinct')})"
                for row in compressed_examples[:3]
            )
        )
    elif low_variance_examples:
        example_bits.append(
            "variance_examples=" + "/".join(
                f"{row.get('feature')}({row.get('std_ratio')})" for row in low_variance_examples[:3]
            )
        )
    if expected_static_examples:
        example_bits.append(
            "expected_static_examples=" + "/".join(
                f"{row.get('feature')}[{row.get('expected_static_reason')}]"
                for row in expected_static_examples[:3]
            )
        )
    if unexpected_frozen_examples:
        example_bits.append(
            "unexpected_frozen_examples=" + "/".join(
                f"{row.get('feature')}({row.get('std_ratio')}/{row.get('recent_distinct')})"
                for row in unexpected_frozen_examples[:3]
            )
        )
    if low_distinct_examples:
        example_bits.append(
            "distinct_examples=" + "/".join(
                f"{row.get('feature')}({row.get('recent_distinct')}/{row.get('baseline_distinct')})"
                for row in low_distinct_examples[:3]
            )
        )
    if null_heavy_examples:
        example_bits.append(
            "null_examples=" + "/".join(
                f"{row.get('feature')}({row.get('non_null_ratio')})" for row in null_heavy_examples[:3]
            )
        )
    path_diag = summary.get("target_path_diagnostics") or {}
    tail_streak = path_diag.get("tail_target_streak") or {}
    streak_target = tail_streak.get("target")
    streak_target_text = "n/a" if streak_target is None else str(streak_target)
    adverse_streak = {}
    if isinstance(win_rate, (int, float)):
        adverse_streak = path_diag.get("longest_zero_target_streak") if win_rate <= 0.5 else path_diag.get("longest_one_target_streak")
    adverse_streak = adverse_streak or {}
    adverse_target = adverse_streak.get("target")
    adverse_target_text = "n/a" if adverse_target is None else str(adverse_target)
    adverse_examples = adverse_streak.get("examples") or []
    recent_examples = path_diag.get("recent_examples") or []
    recent_examples_text = ""
    if recent_examples:
        recent_examples_text = ", recent_examples=" + "/".join(
            f"{row.get('timestamp')}:{row.get('target')}:{row.get('regime')}:{row.get('simulated_pyramid_quality')}"
            for row in recent_examples[-3:]
        )
    adverse_examples_text = ""
    if adverse_examples:
        adverse_examples_text = ", adverse_examples=" + "/".join(
            f"{row.get('timestamp')}:{row.get('target')}:{row.get('regime')}:{row.get('simulated_pyramid_quality')}"
            for row in adverse_examples[-3:]
        )
    tail_text = (
        f", tail_streak={tail_streak.get('count', 0)}x{streak_target_text}"
        f" since {tail_streak.get('start_timestamp')}"
        f" -> {tail_streak.get('end_timestamp')}"
    )
    adverse_text = (
        f", adverse_streak={adverse_streak.get('count', 0)}x{adverse_target_text}"
        f" since {adverse_streak.get('start_timestamp')}"
        f" -> {adverse_streak.get('end_timestamp')}"
    )
    examples_text = (", " + ", ".join(example_bits)) if example_bits else ""
    return (
        f"recent_window={window}, alerts={alerts}, win_rate={win_text}, "
        f"delta_vs_full={delta_text}, dominant_regime={dominant_regime}({share_text}), "
        f"interpretation={interpretation}, avg_pnl={pnl_text}, avg_quality={quality_text}, "
        f"avg_dd_penalty={dd_text}, spot_long_win_rate={spot_long_text}, {feature_summary}"
        f"{tail_text}{adverse_text}{examples_text}{recent_examples_text}{adverse_examples_text}"
    )


def main():
    db_stats = check_db()
    ic_data = {}
    ic_path = ROOT / "model" / "ic_signs.json"
    if ic_path.exists():
        with open(ic_path) as f:
            ic_data = json.load(f)
    full_ic_data = load_full_ic_data()
    ic_stats = check_ic(ic_data, full_ic_data=full_ic_data)
    current_label = os.getenv("HB_RUN_LABEL")
    current_entry = None
    if current_label and full_ic_data:
        current_entry = {
            "heartbeat": str(current_label),
            "tw_pass": full_ic_data.get("tw_pass"),
            "total_features": full_ic_data.get("total_features"),
        }
    tw_history = load_recent_tw_history(limit=3, current_entry=current_entry)
    drift_report = load_recent_drift_report()
    drift_summary = summarize_recent_drift(drift_report)
    drift_primary = (drift_report or {}).get("primary_window") or {}
    drift_primary_summary = drift_primary.get("summary") or {}
    drift_interpretation = drift_primary_summary.get("drift_interpretation")
    drift_alerts = drift_primary.get("alerts") or []
    drift_window = drift_primary.get("window")
    drift_quality = drift_primary_summary.get("quality_metrics") or {}
    drift_avg_pnl = drift_quality.get("avg_simulated_pnl")
    drift_avg_quality = drift_quality.get("avg_simulated_quality")
    drift_spot_long_win = drift_quality.get("spot_long_win_rate")
    metrics = check_metrics()

    # Load existing issues
    tracker = IssueTracker.load()

    # Rule 1: canonical simulated win collapses below random
    if db_stats["simulated_win_avg"] < 0.50:
        tracker.add(
            "P0",
            "#H_AUTO_SIMWIN",
            f"simulated_pyramid_win={db_stats['simulated_win_avg']:.4f} < 0.50 — canonical target edge inverted",
            "檢查 labeling.py canonical target path、recent regime breakdown、decision-quality calibration 與 target distribution drift",
        )

    # Rule 2: recent canonical loss streak > 30
    if db_stats["losing_streak"] > 30:
        tracker.add(
            "P0",
            "#H_AUTO_STREAK",
            f"連續 {db_stats['losing_streak']} 筆 simulated_pyramid_win=0",
            "檢查 recent canonical labels / regime breakdown / circuit breaker；必要時升級為 distribution-aware drift 調查",
        )
    else:
        tracker.resolve("#H_AUTO_STREAK")

    # Rule 3: Global IC crash on canonical feature set
    if ic_stats["global_pass"] <= 2:
        tracker.add(
            "P0",
            "#H_AUTO_IC_CRASH",
            f"全域 IC 僅 {ic_stats['global_pass']}/{ic_stats['total_features']} 通過",
            "先確認 join/target 沒漂移，再調查 feature coverage / target distribution；避免把 TW-IC 噪音當成主訊號",
        )

    # Rule 4: New features not collecting data
    if ic_stats["no_data"]:
        tracker.add(
            "P1",
            "#H_AUTO_NODATA",
            f"{len(ic_stats['no_data'])} 個特徵完全無數據",
            f"檢查 collector.py 是否調用新 modules: {', '.join(ic_stats['no_data'][:5])}",
        )

    # Rule 5: Data not growing
    if db_stats["raw_latest_age_min"] and db_stats["raw_latest_age_min"] > 60:
        tracker.add(
            "P0",
            "#H_AUTO_STALE",
            f"Raw 數據已 {db_stats['raw_latest_age_min']:.0f} 分鐘未更新",
            "檢查 main.py scheduler; 檢查 collector background process; 手動觸發 collect",
        )
    else:
        tracker.resolve("#H_AUTO_STALE")

    # Rule 6: recent canonical distribution pathology persists even when global/TW IC recover
    drift_is_negative_pathology = (
        drift_interpretation == "distribution_pathology"
        and any(alert in drift_alerts for alert in ("constant_target", "label_imbalance"))
        and (
            (isinstance(drift_avg_pnl, (int, float)) and drift_avg_pnl <= 0.0)
            or (isinstance(drift_avg_quality, (int, float)) and drift_avg_quality <= 0.0)
            or (isinstance(drift_spot_long_win, (int, float)) and drift_spot_long_win <= 0.20)
        )
    )
    if drift_is_negative_pathology:
        tracker.add(
            "P0",
            "#H_AUTO_RECENT_PATHOLOGY",
            f"recent canonical window {drift_window} rows = distribution_pathology",
            "直接對 recent canonical rows 做 feature variance / distinct-count / target-path drill-down；"
            "維持 decision-quality guardrails，並檢查 calibration scope 是否仍被病態 slice 稀釋。"
            f" {drift_summary}",
        )
    else:
        tracker.resolve("#H_AUTO_RECENT_PATHOLOGY")

    # Rule 7: TW-IC >> Global IC (regime-dependence indicator)
    if ic_stats["tw_pass"] > ic_stats["global_pass"] + 2:
        tracker.add(
            "P1",
            "#H_AUTO_REGIME_DRIFT",
            f"TW-IC {ic_stats['tw_pass']} vs Global IC {ic_stats['global_pass']} — 信號強依賴近期資料",
            "市場 regime 可能已變化; 考慮 regime-gated feature weighting",
        )

    # Rule 8: TW-IC degraded below the phase-16 floor across consecutive heartbeats
    tw_drift_triggered = len(tw_history) >= 2 and all((row.get("tw_pass") or 0) < 14 for row in tw_history[:2])
    if tw_drift_triggered:
        history_desc = " -> ".join(
            f"#{row['heartbeat']}={row['tw_pass']}/{row.get('total_features') or ic_stats['total_features']}"
            for row in tw_history[:2]
        )
        if drift_interpretation == "supported_extreme_trend":
            drift_action = (
                "近期視窗雖然 constant-target，但 path-quality 顯示這更像『真實極端趨勢口袋』，"
                "不是直接證明 label 壞掉；保留 distribution-aware calibration guardrail，"
                "並改查 recent feature variance / regime narrowness / calibration scope 是否讓 TW-IC 被真實單向行情稀釋。"
            )
        else:
            drift_action = (
                "停止沿用近期優勢敘事；升級為 distribution-aware / calibration drift 調查，"
                "檢查 recent label balance、regime mix、recent-window constant-target guardrail。"
            )
        tracker.add(
            "P0",
            "#H_AUTO_TW_DRIFT",
            f"TW-IC 連續低於 14/30：{history_desc}",
            f"{drift_action}{drift_summary}",
        )
    else:
        tracker.resolve("#H_AUTO_TW_DRIFT")

    # Rule 8: CV gap > 15pp
    cv = metrics.get("cv_accuracy", 0)
    train = metrics.get("train_accuracy", 0)
    if train and cv:
        gap = (train - cv) * 100
        if gap > 15:
            tracker.add(
                "P1",
                "#H_AUTO_GAP",
                f"Train-CV gap = {gap:.1f}pp ({train:.1%} vs {cv:.1%})",
                "更正則化: 增加 reg_alpha/reg_lambda; 減少 max_depth; 或減少特徵數",
            )

    tracker.save()

    # Print report
    print(f"\n{'=' * 60}")
    print(f"🔧 自動修復建議報告 — {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'=' * 60}")

    for prio in ["P0", "P1", "P2"]:
        items = tracker.by_priority(prio)
        if items:
            print(f"\n{prio} 問題：")
            for item in items:
                print(f"  {item['id']}: {item['title']}")
                print(f"    → {item.get('action', '')}")

    print(
        f"\n📊 資料庫：simulated_win={db_stats['simulated_win_avg']:.4f}, "
        f"streak={db_stats['losing_streak']}, age={db_stats['raw_latest_age_min']}"
    )
    print(
        f"📊 IC 概況：global={ic_stats['global_pass']}/{ic_stats['total_features']}, "
        f"tw={ic_stats['tw_pass']}/{ic_stats['total_features']}"
    )
    if tw_history:
        history_desc = ", ".join(
            f"#{row['heartbeat']}={row['tw_pass']}/{row.get('total_features') or ic_stats['total_features']}"
            for row in tw_history
        )
        print(f"📊 TW 歷史：{history_desc}")
    print(f"📊 漂移摘要：{drift_summary}")
    print(f"📊 模型：Train={train:.1%}, CV={cv:.1%}" if train else "📊 模型：目前無資料")
    print(f"\n💾 已儲存至：{Path(__file__).parent.parent / 'issues.json'}")


if __name__ == "__main__":
    main()
