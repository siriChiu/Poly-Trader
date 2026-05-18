#!/usr/bin/env python3
"""Audit circuit-breaker trigger scope against canonical live horizon.

Produces a machine-readable artifact that compares:
1. legacy mixed-horizon breaker math (all labels ordered by timestamp)
2. canonical live-horizon breaker math (1440m only)

Heartbeat #1008 uses this to prove whether the live runtime blocker is real or a
false-positive caused by mixing 240m tail labels into a 1440m decision contract.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from model.predictor import (
    CIRCUIT_BREAKER_HORIZON_MINUTES,
    CIRCUIT_BREAKER_RECENT_WINRATE,
    CIRCUIT_BREAKER_STREAK,
    CIRCUIT_BREAKER_WINDOW,
    DEFAULT_TARGET_COL,
)

DB_PATH = PROJECT_ROOT / "poly_trader.db"
OUT_JSON = PROJECT_ROOT / "data" / "circuit_breaker_audit.json"
OUT_MD = PROJECT_ROOT / "docs" / "analysis" / "circuit_breaker_audit.md"


def _rows_to_series(conn: sqlite3.Connection, where_sql: str = "", params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    sql = f"""
    SELECT timestamp, horizon_minutes, {DEFAULT_TARGET_COL} AS target
    FROM labels
    WHERE {DEFAULT_TARGET_COL} IS NOT NULL
    {where_sql}
    ORDER BY timestamp DESC
    """
    return conn.execute(sql, params).fetchall()


def _first_streak(rows: list[sqlite3.Row]) -> dict[str, Any]:
    streak_rows: list[sqlite3.Row] = []
    for row in rows:
        if int(row["target"] or 0) == 0:
            streak_rows.append(row)
            continue
        break
    if not streak_rows:
        return {"count": 0, "start_timestamp": None, "end_timestamp": None, "horizons": {}, "rows": []}
    horizons: dict[str, int] = {}
    for row in streak_rows:
        key = str(row["horizon_minutes"])
        horizons[key] = horizons.get(key, 0) + 1
    return {
        "count": len(streak_rows),
        "start_timestamp": streak_rows[-1]["timestamp"],
        "end_timestamp": streak_rows[0]["timestamp"],
        "horizons": horizons,
        "rows": [
            {
                "timestamp": row["timestamp"],
                "horizon_minutes": row["horizon_minutes"],
                "target": int(row["target"] or 0),
            }
            for row in streak_rows[:15]
        ],
    }


def _window_summary(rows: list[sqlite3.Row], window_size: int) -> dict[str, Any]:
    window = rows[:window_size]
    wins = sum(int(row["target"] or 0) for row in window)
    actual_size = len(window)
    win_rate = (wins / actual_size) if actual_size else None
    horizons: dict[str, int] = {}
    for row in window:
        key = str(row["horizon_minutes"])
        horizons[key] = horizons.get(key, 0) + 1
    return {
        "window_size": actual_size,
        "wins": wins,
        "losses": actual_size - wins,
        "win_rate": win_rate,
        "trigger_floor": CIRCUIT_BREAKER_RECENT_WINRATE,
        "breaches_floor": bool(actual_size >= window_size and win_rate is not None and win_rate < CIRCUIT_BREAKER_RECENT_WINRATE),
        "horizons": horizons,
        "rows": [
            {
                "timestamp": row["timestamp"],
                "horizon_minutes": row["horizon_minutes"],
                "target": int(row["target"] or 0),
            }
            for row in window[:15]
        ],
    }


def _scope_audit(rows: list[sqlite3.Row], scope_name: str) -> dict[str, Any]:
    streak = _first_streak(rows)
    window = _window_summary(rows, CIRCUIT_BREAKER_WINDOW)
    triggered_by: list[str] = []
    if streak["count"] >= CIRCUIT_BREAKER_STREAK:
        triggered_by.append("streak")
    if window["breaches_floor"]:
        triggered_by.append("recent_win_rate")

    required_wins = int(CIRCUIT_BREAKER_RECENT_WINRATE * CIRCUIT_BREAKER_WINDOW)
    current_wins = int(window.get("wins") or 0)
    additional_wins_needed = max(0, required_wins - current_wins)
    current_win_rate = window.get("win_rate")
    release_condition = {
        "release_ready": not triggered_by,
        "blocked_by": triggered_by,
        "streak_release_ready": streak["count"] < CIRCUIT_BREAKER_STREAK,
        "recent_win_rate_release_ready": bool(current_win_rate is not None and current_win_rate >= CIRCUIT_BREAKER_RECENT_WINRATE),
        "streak_must_be_below": CIRCUIT_BREAKER_STREAK,
        "current_streak": streak["count"],
        "recent_window": CIRCUIT_BREAKER_WINDOW,
        "recent_win_rate_floor": CIRCUIT_BREAKER_RECENT_WINRATE,
        "current_recent_window_win_rate": current_win_rate,
        "current_recent_window_wins": current_wins,
        "required_recent_window_wins": required_wins,
        "additional_recent_window_wins_needed": additional_wins_needed,
    }
    tail_pathology = {
        "losses_in_recent_window": window.get("losses"),
        "wins_in_recent_window": current_wins,
        "loss_share": (
            round(float(window.get("losses") or 0) / float(window.get("window_size") or 1), 4)
            if window.get("window_size")
            else None
        ),
        "window_start_timestamp": rows[min(len(rows), CIRCUIT_BREAKER_WINDOW) - 1]["timestamp"] if rows[:CIRCUIT_BREAKER_WINDOW] else None,
        "window_end_timestamp": rows[0]["timestamp"] if rows else None,
        "latest_rows_preview": window.get("rows") or [],
    }
    return {
        "scope": scope_name,
        "rows_available": len(rows),
        "triggered": bool(triggered_by),
        "triggered_by": triggered_by,
        "release_ready": not triggered_by,
        "release_condition": release_condition,
        "tail_pathology": tail_pathology,
        "streak": {
            **streak,
            "threshold": CIRCUIT_BREAKER_STREAK,
            "breaches_threshold": streak["count"] >= CIRCUIT_BREAKER_STREAK,
        },
        "recent_window": window,
        "latest_timestamp": rows[0]["timestamp"] if rows else None,
        "oldest_timestamp": rows[-1]["timestamp"] if rows else None,
    }


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _compact_tail_pathology(tail_pathology: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(tail_pathology, dict):
        tail_pathology = {}
    return {
        "losses_in_recent_window": tail_pathology.get("losses_in_recent_window"),
        "wins_in_recent_window": tail_pathology.get("wins_in_recent_window"),
        "loss_share": tail_pathology.get("loss_share"),
        "window_start_timestamp": tail_pathology.get("window_start_timestamp"),
        "window_end_timestamp": tail_pathology.get("window_end_timestamp"),
    }


def _compact_canonical_scope(scope: dict[str, Any]) -> dict[str, Any]:
    release_condition = scope.get("release_condition") if isinstance(scope.get("release_condition"), dict) else {}
    tail_pathology = _compact_tail_pathology(scope.get("tail_pathology") if isinstance(scope.get("tail_pathology"), dict) else {})
    return {
        "scope": scope.get("scope"),
        "rows_available": scope.get("rows_available"),
        "triggered": scope.get("triggered"),
        "triggered_by": scope.get("triggered_by"),
        "release_ready": scope.get("release_ready"),
        "current_streak": release_condition.get("current_streak"),
        "streak_must_be_below": release_condition.get("streak_must_be_below"),
        "recent_window": release_condition.get("recent_window"),
        "recent_win_rate_floor": release_condition.get("recent_win_rate_floor"),
        "current_recent_window_win_rate": release_condition.get("current_recent_window_win_rate"),
        "current_recent_window_wins": release_condition.get("current_recent_window_wins"),
        "required_recent_window_wins": release_condition.get("required_recent_window_wins"),
        "additional_recent_window_wins_needed": release_condition.get("additional_recent_window_wins_needed"),
        "losses_in_recent_window": tail_pathology.get("losses_in_recent_window"),
        "loss_share": tail_pathology.get("loss_share"),
        "latest_timestamp": scope.get("latest_timestamp"),
        "oldest_timestamp": scope.get("oldest_timestamp"),
    }


def _format_win_rate(value: Any) -> str:
    if value is None:
        return "unknown"
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)


def _build_payload(
    *,
    mixed: dict[str, Any],
    aligned: dict[str, Any],
    heartbeat: str,
    generated_at: str | None = None,
) -> dict[str, Any]:
    if mixed.get("triggered") and not aligned.get("triggered"):
        verdict = "mixed_horizon_false_positive"
        summary = (
            f"混合 horizon breaker 會被 240m tail labels 觸發（streak={(mixed.get('streak') or {}).get('count')}，"
            f"recent50 win_rate={_format_win_rate((mixed.get('recent_window') or {}).get('win_rate'))}），"
            f"但 {CIRCUIT_BREAKER_HORIZON_MINUTES}m canonical live horizon 目前 release-ready。"
        )
        recommended_patch = f"將 circuit breaker 對齊 horizon_minutes={CIRCUIT_BREAKER_HORIZON_MINUTES} 的 canonical live contract。"
    elif aligned.get("triggered"):
        verdict = "canonical_breaker_active"
        summary = (
            f"{CIRCUIT_BREAKER_HORIZON_MINUTES}m canonical live horizon 仍觸發 breaker："
            f"{aligned.get('triggered_by')}。"
        )
        recommended_patch = "維持 breaker，改做 canonical tail root-cause / release-condition artifact。"
    else:
        verdict = "breaker_clear"
        summary = f"{CIRCUIT_BREAKER_HORIZON_MINUTES}m canonical live horizon 未觸發 breaker。"
        recommended_patch = "維持 horizon-aligned breaker，繼續追 live q15/q35 / support route。"

    release_condition = aligned.get("release_condition") if isinstance(aligned.get("release_condition"), dict) else {}
    tail_pathology = _compact_tail_pathology(aligned.get("tail_pathology") if isinstance(aligned.get("tail_pathology"), dict) else {})

    return {
        "generated_at": generated_at or _utc_now_iso(),
        "heartbeat": heartbeat,
        "target_col": DEFAULT_TARGET_COL,
        "canonical_horizon_minutes": CIRCUIT_BREAKER_HORIZON_MINUTES,
        "verdict": verdict,
        "summary": summary,
        "recommended_patch": recommended_patch,
        "release_condition": release_condition,
        "tail_pathology": tail_pathology,
        "canonical_scope": _compact_canonical_scope(aligned),
        "trigger_thresholds": {
            "horizon_minutes": CIRCUIT_BREAKER_HORIZON_MINUTES,
            "streak": CIRCUIT_BREAKER_STREAK,
            "recent_window": CIRCUIT_BREAKER_WINDOW,
            "recent_win_rate_floor": CIRCUIT_BREAKER_RECENT_WINRATE,
        },
        "mixed_scope": mixed,
        "aligned_scope": aligned,
        "root_cause": {
            "verdict": verdict,
            "summary": summary,
            "recommended_patch": recommended_patch,
        },
    }


def _markdown(payload: dict[str, Any]) -> str:
    mixed = payload["mixed_scope"]
    aligned = payload["aligned_scope"]
    root = payload["root_cause"]
    release_condition = payload.get("release_condition") or aligned.get("release_condition") or {}
    tail_pathology = payload.get("tail_pathology") or aligned.get("tail_pathology") or {}
    return "\n".join(
        [
            f"# Circuit Breaker Audit（Heartbeat #{payload['heartbeat']}）",
            f"_generated_at: {payload.get('generated_at')}_",
            "",
            "## 結論",
            f"- verdict: **{root['verdict']}**",
            f"- summary: {root['summary']}",
            f"- recommended_patch: {root['recommended_patch']}",
            f"- top_level_release: ready={release_condition.get('release_ready')} / recent wins={release_condition.get('current_recent_window_wins')}/{release_condition.get('recent_window')} / need={release_condition.get('required_recent_window_wins')} / gap={release_condition.get('additional_recent_window_wins_needed')}",
            "",
            "## Mixed scope（現況錯誤口徑）",
            f"- triggered: **{mixed['triggered']}** via {mixed['triggered_by']}",
            f"- streak: {mixed['streak']['count']} / threshold {mixed['streak']['threshold']}",
            f"- recent {CIRCUIT_BREAKER_WINDOW}: win_rate={mixed['recent_window']['win_rate']} wins={mixed['recent_window']['wins']} losses={mixed['recent_window']['losses']}",
            f"- streak horizons: {mixed['streak']['horizons']}",
            "",
            f"## Aligned scope（{CIRCUIT_BREAKER_HORIZON_MINUTES}m canonical live horizon）",
            f"- triggered: **{aligned['triggered']}** via {aligned['triggered_by']}",
            f"- release_ready: **{aligned['release_ready']}**",
            f"- streak: {aligned['streak']['count']} / threshold {aligned['streak']['threshold']}",
            f"- recent {CIRCUIT_BREAKER_WINDOW}: win_rate={aligned['recent_window']['win_rate']} wins={aligned['recent_window']['wins']} losses={aligned['recent_window']['losses']}",
            "",
            "## Release condition",
            f"- streak < {CIRCUIT_BREAKER_STREAK}",
            f"- recent {CIRCUIT_BREAKER_WINDOW} win_rate >= {CIRCUIT_BREAKER_RECENT_WINRATE:.0%}",
            f"- aligned_scope_now: streak={aligned['streak']['count']}, win_rate={aligned['recent_window']['win_rate']}",
            f"- additional recent-window wins needed: {release_condition.get('additional_recent_window_wins_needed')}",
            f"- tail pathology: losses={tail_pathology.get('losses_in_recent_window')} / wins={tail_pathology.get('wins_in_recent_window')} / loss_share={tail_pathology.get('loss_share')}",
        ]
    )


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        mixed_rows = _rows_to_series(conn)
        aligned_rows = _rows_to_series(conn, "AND horizon_minutes = ?", (CIRCUIT_BREAKER_HORIZON_MINUTES,))
        mixed = _scope_audit(mixed_rows, "mixed_all_horizons")
        aligned = _scope_audit(aligned_rows, f"horizon_{CIRCUIT_BREAKER_HORIZON_MINUTES}")

        payload = _build_payload(
            mixed=mixed,
            aligned=aligned,
            heartbeat=sys.argv[1] if len(sys.argv) > 1 else "adhoc",
        )
        OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        OUT_MD.parent.mkdir(parents=True, exist_ok=True)
        OUT_MD.write_text(_markdown(payload), encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
