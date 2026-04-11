#!/usr/bin/env python3
"""Recent distribution-aware drift report for canonical simulated_pyramid_win.

Purpose:
- explain TW-IC decay with recent label balance / regime mix facts
- provide machine-readable output for heartbeat summaries + auto-propose

Output:
- data/recent_drift_report.json
"""
from __future__ import annotations

import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "poly_trader.db"
OUT_PATH = PROJECT_ROOT / "data" / "recent_drift_report.json"
TARGET_COL = "simulated_pyramid_win"
CANONICAL_HORIZON_MINUTES = 1440
WINDOWS = [100, 250, 500, 1000]


def _pct(numerator: int, denominator: int) -> float | None:
    if not denominator:
        return None
    return round(numerator / denominator, 4)


def _round(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 4)


def _counter_to_dict(counter: Counter) -> dict[str, int]:
    return {str(k): int(v) for k, v in counter.items()}


def _window_summary(rows: list[sqlite3.Row], baseline_win_rate: float, baseline_regimes: Counter) -> dict[str, Any]:
    total = len(rows)
    wins = sum(int(r["target"]) for r in rows)
    losses = total - wins
    regime_counts = Counter((r["regime"] or "unknown") for r in rows)
    dominant_regime, dominant_count = regime_counts.most_common(1)[0] if regime_counts else (None, 0)
    win_rate = wins / total if total else None
    unique_targets = sorted({int(r["target"]) for r in rows}) if rows else []
    dominant_share = dominant_count / total if total else None
    baseline_dominant_share = (baseline_regimes.get(dominant_regime, 0) / sum(baseline_regimes.values())) if total and dominant_regime else 0.0

    alerts = []
    if len(unique_targets) <= 1:
        alerts.append("constant_target")
    elif win_rate is not None and (win_rate >= 0.8 or win_rate <= 0.2):
        alerts.append("label_imbalance")
    if dominant_share is not None and dominant_share >= 0.9:
        alerts.append("regime_concentration")
    if dominant_share is not None and baseline_dominant_share is not None and dominant_share - baseline_dominant_share >= 0.2:
        alerts.append("regime_shift")

    return {
        "rows": total,
        "wins": wins,
        "losses": losses,
        "win_rate": _round(win_rate),
        "win_rate_delta_vs_full": _round((win_rate - baseline_win_rate) if win_rate is not None else None),
        "unique_targets": unique_targets,
        "constant_target": len(unique_targets) <= 1,
        "dominant_regime": dominant_regime,
        "dominant_regime_share": _round(dominant_share),
        "dominant_regime_delta_vs_full": _round((dominant_share - baseline_dominant_share) if dominant_share is not None else None),
        "regime_counts": _counter_to_dict(regime_counts),
        "regime_pct": {k: _pct(v, total) for k, v in _counter_to_dict(regime_counts).items()},
        "alerts": alerts,
    }


def _find_primary_window(window_summaries: dict[str, dict[str, Any]]) -> tuple[str | None, dict[str, Any] | None]:
    def score(item: tuple[str, dict[str, Any]]) -> tuple[int, float, int]:
        _, summary = item
        alerts = summary.get("alerts", [])
        severity = 0
        if "constant_target" in alerts:
            severity += 4
        if "label_imbalance" in alerts:
            severity += 3
        if "regime_concentration" in alerts:
            severity += 2
        if "regime_shift" in alerts:
            severity += 1
        delta = abs(summary.get("win_rate_delta_vs_full") or 0.0)
        rows = -int(summary.get("rows") or 0)
        return (severity, delta, rows)

    if not window_summaries:
        return None, None
    label, summary = max(window_summaries.items(), key=score)
    return label, summary


def build_report() -> dict[str, Any]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        f"""
        SELECT
            l.timestamp,
            l.symbol,
            l.{TARGET_COL} AS target,
            COALESCE(NULLIF(f.regime_label, ''), NULLIF(l.regime_label, ''), 'unknown') AS regime
        FROM labels l
        LEFT JOIN features_normalized f
          ON f.timestamp = l.timestamp AND f.symbol = l.symbol
        WHERE l.horizon_minutes = ?
          AND l.{TARGET_COL} IS NOT NULL
        ORDER BY l.timestamp
        """,
        (CANONICAL_HORIZON_MINUTES,),
    ).fetchall()
    conn.close()

    total = len(rows)
    baseline_regimes = Counter((r["regime"] or "unknown") for r in rows)
    baseline_win_rate = (sum(int(r["target"]) for r in rows) / total) if total else 0.0

    window_summaries: dict[str, dict[str, Any]] = {}
    for window in WINDOWS:
        if total < window:
            continue
        window_rows = rows[-window:]
        window_summaries[str(window)] = _window_summary(window_rows, baseline_win_rate, baseline_regimes)

    primary_window, primary_summary = _find_primary_window(window_summaries)
    primary_alerts = list((primary_summary or {}).get("alerts", []))

    report = {
        "target_col": TARGET_COL,
        "horizon_minutes": CANONICAL_HORIZON_MINUTES,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "full_sample": {
            "rows": total,
            "win_rate": _round(baseline_win_rate),
            "regime_counts": _counter_to_dict(baseline_regimes),
            "regime_pct": {k: _pct(v, total) for k, v in _counter_to_dict(baseline_regimes).items()},
        },
        "windows": window_summaries,
        "primary_window": {
            "window": primary_window,
            "alerts": primary_alerts,
            "summary": primary_summary or {},
        },
    }
    return report


def main() -> int:
    report = build_report()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(report, indent=2, default=str))

    primary = report.get("primary_window", {})
    primary_window = primary.get("window")
    summary = primary.get("summary", {})
    alerts = primary.get("alerts", [])

    print("Recent Drift Report")
    print("=" * 70)
    full = report["full_sample"]
    print(
        f"Full sample: rows={full['rows']} win_rate={full['win_rate']:.4f} "
        f"regimes={full['regime_pct']}"
    )
    for window, row in report["windows"].items():
        print(
            f"  last {window}: win_rate={row['win_rate']:.4f} delta={row['win_rate_delta_vs_full']:+.4f} "
            f"dominant_regime={row['dominant_regime']} ({row['dominant_regime_share']:.2%}) alerts={row['alerts']}"
        )
    if primary_window:
        print(
            f"Primary drift window: last {primary_window} rows | win_rate={summary.get('win_rate', 0):.4f} "
            f"dominant_regime={summary.get('dominant_regime')} ({(summary.get('dominant_regime_share') or 0):.2%}) "
            f"alerts={alerts}"
        )
    print(f"Saved to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
