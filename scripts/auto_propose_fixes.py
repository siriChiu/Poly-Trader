#!/usr/bin/env python3
"""
Auto-propose fixes based on current IC / sell_win / CV data.
Called by hb_parallel_runner.py or standalone.

Reads:
  model/ic_signs.json
  model/last_metrics.json
  poly_trader.db

Writes:
  issues.json (via IssueTracker)
"""
import sqlite3
import json
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
    sw = conn.execute("SELECT AVG(label_sell_win) FROM labels WHERE label_sell_win IS NOT NULL").fetchone()[0]
    rows = conn.execute("SELECT label_sell_win FROM labels WHERE label_sell_win IS NOT NULL ORDER BY id DESC LIMIT 200").fetchall()
    streak = 0
    for r in rows:
        if r[0] == 0: streak += 1
        else: break

    latest = conn.execute("SELECT timestamp FROM raw_market_data ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()

    latest_ts = latest[0] if latest else None
    age_min = None
    if latest_ts:
        from datetime import datetime as dt, timezone
        ts_str = str(latest_ts).replace(' ', 'T').split('.')[0]
        try:
            ts = dt.fromisoformat(ts_str)
            age_min = (dt.utcnow() - ts).total_seconds() / 60
        except Exception:
            pass

    return {
        "sell_win_avg": round(sw, 4) if sw else 0.5,
        "losing_streak": streak,
        "raw_latest_age_min": round(age_min, 1) if age_min is not None else None,
    }


def check_ic(ic_data):
    all_ics = ic_data.get("ic_global", {})
    tw_ics = ic_data.get("ic_tw", {})
    null_counts = ic_data.get("null_counts", {})
    ic_status = ic_data.get("ic_status", {})

    global_pass = sum(1 for c in CORE_FEATURES if abs(all_ics.get(c, 0)) >= 0.05)
    tw_pass = sum(1 for c in CORE_FEATURES if abs(tw_ics.get(c, 0)) >= 0.05)
    no_data = [c for c, s in null_counts.items() if s == 0]
    low_data = [c for c, s in null_counts.items() if s != 0 and ic_status.get(c) not in ("PASS", "FAIL")]

    return {
        "global_pass": global_pass,
        "tw_pass": tw_pass,
        "total_core": len(CORE_FEATURES),
        "no_data": no_data,
        "low_data": low_data,
        "best_ic": max(all_ics.items(), key=lambda x: abs(x[1])) if all_ics else (None, 0),
        "worst_ic": min(all_ics.items(), key=lambda x: abs(x[1])) if all_ics else ( None, 0),
    }


def check_metrics():
    mp = ROOT / "model" / "last_metrics.json"
    if mp.exists():
        with open(mp) as f:
            return json.load(f)
    return {}


def main():
    db_stats = check_db()
    ic_data = {}
    ic_path = ROOT / "model" / "ic_signs.json"
    if ic_path.exists():
        with open(ic_path) as f:
            ic_data = json.load(f)
    ic_stats = check_ic(ic_data)
    metrics = check_metrics()

    # Load existing issues
    tracker = IssueTracker.load()

    proposals = []

    # Rule 1: sell_win < 50%
    if db_stats["sell_win_avg"] < 0.50:
        tracker.add("P0", "#H_AUTO_SELLWIN",
            f"sell_win_rate={db_stats['sell_win_avg']:.4f} < 0.50 — 系統方向性錯誤",
            "檢查 labeling.py threshold; 檢查 recent regime sell_win; 考慮動態 threshold")

    # Rule 2: losing streak > 30
    if db_stats["losing_streak"] > 30:
        tracker.add("P0", "#H_AUTO_STREAK",
            f"連續 {db_stats['losing_streak']} 筆 sell_win=0",
            "Circuit Breaker 應持續生效; 檢查 label threshold; 考虑 regime-specific model")

    # Rule 3: Global IC 全滅
    if ic_stats["global_pass"] <= 2:
        tracker.add("P0", "#H_AUTO_IC_CRASH",
            f"全域 IC 僅 {ic_stats['global_pass']}/{ic_stats['total_core']} 通過",
            "TW-IC fusion 是唯一信號源; 考慮新外部數據 (VIX, DXY 已夠強但單一市場)")

    # Rule 4: New features not collecting data
    if ic_stats["no_data"]:
        tracker.add("P1", "#H_AUTO_NODATA",
            f"{len(ic_stats['no_data'])} 個特徵完全無數據",
            f"檢查 collector.py 是否調用新 modules: {', '.join(ic_stats['no_data'][:5])}")

    # Rule 5: Data not growing
    if db_stats["raw_latest_age_min"] and db_stats["raw_latest_age_min"] > 60:
        tracker.add("P0", "#H_AUTO_STALE",
            f"Raw 數據已 {db_stats['raw_latest_age_min']:.0f} 分鐘未更新",
            "檢查 main.py scheduler; 檢查 collector background process; 手動觸發 collect")

    # Rule 6: TW-IC >> Global IC (regime-dependence indicator)
    if ic_stats["tw_pass"] > ic_stats["global_pass"] + 2:
        tracker.add("P1", "#H_AUTO_REGIME_DRIFT",
            f"TW-IC {ic_stats['tw_pass']} vs Global IC {ic_stats['global_pass']} — 信號強依賴近期資料",
            "市場 regime 可能已變化; 考慮 regime-gated feature weighting")

    # Rule 7: CV gap > 15pp
    cv = metrics.get("cv_accuracy", 0)
    train = metrics.get("train_accuracy", 0)
    if train and cv:
        gap = (train - cv) * 100
        if gap > 15:
            tracker.add("P1", "#H_AUTO_GAP",
                f"Train-CV gap = {gap:.1f}pp ({train:.1%} vs {cv:.1%})",
                "更正則化: 增加 reg_alpha/reg_lambda; 減少 max_depth; 或減少特徵數")

    tracker.save()

    # Print report
    print(f"\n{'=' * 60}")
    print(f"🔧 Auto-Propose Fixes Report — {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'=' * 60}")

    for prio in ["P0", "P1", "P2"]:
        items = tracker.by_priority(prio)
        if items:
            print(f"\n{prio} Issues:")
            for item in items:
                print(f"  {item['id']}: {item['title']}")
                print(f"    → {item.get('action', '')}")

    print(f"\n📊 DB: sell_win={db_stats['sell_win_avg']:.4f}, streak={db_stats['losing_streak']}, age={db_stats['raw_latest_age_min']}")
    print(f"📊 IC: global={ic_stats['global_pass']}/{ic_stats['total_core']}, tw={ic_stats['tw_pass']}/{ic_stats['total_core']}")
    print(f"📊 Model: Train={train:.1%}, CV={cv:.1%}" if train else "📊 Model: no data")
    print(f"\n💾 Saved to: {Path(__file__).parent.parent / 'issues.json'}")


if __name__ == "__main__":
    main()
