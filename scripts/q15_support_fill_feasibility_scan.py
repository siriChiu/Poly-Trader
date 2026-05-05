#!/usr/bin/env python3
"""Scan whether the current q15 support gap can be filled by history/backfill.

Purpose:
- distinguish a true raw-data/support harvest gap from a semantic/window gap
- keep deployment fail-closed when older/proxy rows have enough count but do not
  match the current support identity (especially calibration_window)

Inputs:
- poly_trader.db (features_normalized + labels)
- data/live_predict_probe.json
- data/q15_support_audit.json (optional context)

Outputs:
- data/q15_support_fill_feasibility.json
- docs/analysis/q15_support_fill_feasibility.md
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "poly_trader.db"
PROBE_PATH = PROJECT_ROOT / "data" / "live_predict_probe.json"
Q15_AUDIT_PATH = PROJECT_ROOT / "data" / "q15_support_audit.json"
OUT_JSON = PROJECT_ROOT / "data" / "q15_support_fill_feasibility.json"
OUT_MD = PROJECT_ROOT / "docs" / "analysis" / "q15_support_fill_feasibility.md"

BUCKET_SEMANTIC_SIGNATURE = "live_structure_bucket:q15_support_identity:v2"
DEFAULT_TARGET_COL = "simulated_pyramid_win"
DEFAULT_HORIZON_MINUTES = 1440
DEFAULT_MINIMUM_SUPPORT_ROWS = 50
SCAN_WINDOWS = (100, 200, 600, 1000, 5000)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


def _round_optional(value: Any, digits: int = 4) -> float | None:
    try:
        if value is None:
            return None
        return round(float(value), digits)
    except Exception:
        return None


def _avg(rows: Iterable[dict[str, Any]], key: str) -> float | None:
    values: list[float] = []
    for row in rows:
        value = row.get(key)
        if value is None:
            continue
        try:
            values.append(float(value))
        except Exception:
            continue
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def _metric_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    wins = [row.get("simulated_pyramid_win") for row in rows if row.get("simulated_pyramid_win") is not None]
    return {
        "rows": len(rows),
        "win_rate": _avg(rows, "simulated_pyramid_win"),
        "target_counts": dict(Counter(str(int(v)) for v in wins)) if wins else {},
        "avg_pnl": _avg(rows, "simulated_pyramid_pnl"),
        "avg_quality": _avg(rows, "simulated_pyramid_quality"),
        "avg_drawdown_penalty": _avg(rows, "simulated_pyramid_drawdown_penalty"),
        "avg_time_underwater": _avg(rows, "simulated_pyramid_time_underwater"),
    }


def support_identity_from_artifacts(
    probe: dict[str, Any],
    q15_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the current support identity from the live probe, with q15 audit fallback."""

    q15_audit = q15_audit or {}
    current_live = q15_audit.get("current_live") if isinstance(q15_audit.get("current_live"), dict) else {}
    audit_route = q15_audit.get("support_route") if isinstance(q15_audit.get("support_route"), dict) else {}
    audit_identity = audit_route.get("support_identity") if isinstance(audit_route.get("support_identity"), dict) else {}
    blocker = probe.get("deployment_blocker_details") if isinstance(probe.get("deployment_blocker_details"), dict) else {}

    current_bucket = (
        probe.get("current_live_structure_bucket")
        or blocker.get("structure_bucket")
        or current_live.get("current_live_structure_bucket")
        or audit_identity.get("current_live_structure_bucket")
    )
    return {
        "target_col": probe.get("target_col") or audit_identity.get("target_col") or DEFAULT_TARGET_COL,
        "horizon_minutes": _as_int(
            probe.get("horizon_minutes")
            or current_live.get("decision_quality_horizon_minutes")
            or audit_identity.get("horizon_minutes"),
            DEFAULT_HORIZON_MINUTES,
        ),
        "current_live_structure_bucket": current_bucket,
        "regime_label": probe.get("regime_label") or current_live.get("regime_label") or audit_identity.get("regime_label"),
        "regime_gate": probe.get("regime_gate") or current_live.get("regime_gate") or audit_identity.get("regime_gate"),
        "entry_quality_label": (
            probe.get("entry_quality_label")
            or current_live.get("entry_quality_label")
            or audit_identity.get("entry_quality_label")
        ),
        "calibration_window": _as_int(
            probe.get("decision_quality_calibration_window")
            or current_live.get("decision_quality_calibration_window")
            or audit_identity.get("calibration_window"),
            0,
        ),
        "bucket_semantic_signature": audit_identity.get("bucket_semantic_signature") or BUCKET_SEMANTIC_SIGNATURE,
    }


def fetch_db_meta(db_path: Path = DB_PATH) -> dict[str, Any]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    meta: dict[str, Any] = {}
    for table in ("features_normalized", "labels", "raw_market_data"):
        try:
            row = conn.execute(
                f"SELECT COUNT(*) AS count, MIN(timestamp) AS min_ts, MAX(timestamp) AS max_ts FROM {table}"
            ).fetchone()
        except sqlite3.Error:
            continue
        meta[table] = dict(row) if row is not None else {}
    conn.close()
    return meta


def fetch_labeled_decision_rows(
    *,
    db_path: Path = DB_PATH,
    horizon_minutes: int = DEFAULT_HORIZON_MINUTES,
) -> list[dict[str, Any]]:
    """Return production-style historical live-decision rows, newest first."""

    # Lazy import keeps unit tests for pure summarization helpers independent of the app DB/model stack.
    from model.predictor import _build_live_decision_profile

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    query = """
        SELECT
            f.timestamp,
            f.symbol,
            f.regime_label,
            f.feat_4h_bias200,
            f.feat_4h_bias50,
            f.feat_4h_bb_pct_b,
            f.feat_4h_dist_bb_lower,
            f.feat_4h_dist_swing_low,
            f.feat_nose,
            f.feat_pulse,
            f.feat_ear,
            l.simulated_pyramid_win,
            l.simulated_pyramid_pnl,
            l.simulated_pyramid_quality,
            l.simulated_pyramid_drawdown_penalty,
            l.simulated_pyramid_time_underwater
        FROM features_normalized f
        JOIN labels l ON f.timestamp = l.timestamp AND f.symbol = l.symbol
        WHERE l.horizon_minutes = ?
          AND l.simulated_pyramid_win IS NOT NULL
        ORDER BY f.timestamp DESC
    """
    raw_rows = conn.execute(query, (horizon_minutes,)).fetchall()
    conn.close()

    summarized_rows: list[dict[str, Any]] = []
    for row in raw_rows:
        # This mirrors model.predictor._infer_live_decision_quality_contract: historical rows are
        # re-bucketed through the same live decision-profile logic before support diagnostics count them.
        hist_features = {
            "regime_label": row["regime_label"],
            "feat_4h_bias200": row["feat_4h_bias200"],
            "feat_4h_bias50": row["feat_4h_bias50"],
            "feat_4h_bb_pct_b": row["feat_4h_bb_pct_b"],
            "feat_4h_dist_bb_lower": row["feat_4h_dist_bb_lower"],
            "feat_4h_dist_swing_low": row["feat_4h_dist_swing_low"],
            "feat_nose": row["feat_nose"],
            "feat_pulse": row["feat_pulse"],
            "feat_ear": row["feat_ear"],
        }
        profile = _build_live_decision_profile(hist_features)
        summarized_rows.append(
            {
                "timestamp": row["timestamp"],
                "symbol": row["symbol"],
                "regime_label": profile.get("regime_label"),
                "regime_gate": profile.get("regime_gate"),
                "entry_quality_label": profile.get("entry_quality_label"),
                "structure_bucket": profile.get("structure_bucket"),
                "simulated_pyramid_win": row["simulated_pyramid_win"],
                "simulated_pyramid_pnl": row["simulated_pyramid_pnl"],
                "simulated_pyramid_quality": row["simulated_pyramid_quality"],
                "simulated_pyramid_drawdown_penalty": row["simulated_pyramid_drawdown_penalty"],
                "simulated_pyramid_time_underwater": row["simulated_pyramid_time_underwater"],
            }
        )
    return summarized_rows


def _matches_exact_identity(row: dict[str, Any], identity: dict[str, Any]) -> bool:
    return (
        row.get("regime_label") == identity.get("regime_label")
        and row.get("regime_gate") == identity.get("regime_gate")
        and row.get("entry_quality_label") == identity.get("entry_quality_label")
    )


def _matches_exact_bucket(row: dict[str, Any], identity: dict[str, Any]) -> bool:
    return _matches_exact_identity(row, identity) and row.get("structure_bucket") == identity.get(
        "current_live_structure_bucket"
    )


def build_feasibility_report(
    *,
    rows: list[dict[str, Any]],
    support_identity: dict[str, Any],
    db_meta: dict[str, Any] | None = None,
    q15_audit: dict[str, Any] | None = None,
    source_artifacts: dict[str, Any] | None = None,
    generated_at: str | None = None,
    windows: Iterable[int] = SCAN_WINDOWS,
    minimum_support_rows: int = DEFAULT_MINIMUM_SUPPORT_ROWS,
) -> dict[str, Any]:
    """Summarize whether exact-bucket support can be closed by historical data."""

    q15_audit = q15_audit or {}
    calibration_window = _as_int(support_identity.get("calibration_window"), 0)
    normalized_windows = sorted({int(w) for w in windows if int(w) > 0} | ({calibration_window} if calibration_window > 0 else set()))
    if rows:
        normalized_windows.append(len(rows))

    window_scan: dict[str, Any] = {}
    for window in normalized_windows:
        scoped_rows = rows[: min(window, len(rows))]
        exact_identity_rows = [row for row in scoped_rows if _matches_exact_identity(row, support_identity)]
        exact_bucket_rows = [row for row in exact_identity_rows if _matches_exact_bucket(row, support_identity)]
        same_regime_bucket_rows = [
            row
            for row in scoped_rows
            if row.get("regime_label") == support_identity.get("regime_label")
            and row.get("structure_bucket") == support_identity.get("current_live_structure_bucket")
        ]
        any_scope_bucket_rows = [
            row for row in scoped_rows if row.get("structure_bucket") == support_identity.get("current_live_structure_bucket")
        ]
        window_key = str(window) if window != len(rows) else "all"
        same_calibration_identity = window == calibration_window
        support_ready_by_count = len(exact_bucket_rows) >= minimum_support_rows
        bucket_counts = Counter(str(row.get("structure_bucket")) for row in exact_identity_rows if row.get("structure_bucket"))
        window_scan[window_key] = {
            "calibration_window": window,
            "scope_rows": len(scoped_rows),
            "exact_identity_rows": len(exact_identity_rows),
            "exact_bucket_rows": len(exact_bucket_rows),
            "same_regime_bucket_rows": len(same_regime_bucket_rows),
            "any_scope_bucket_rows": len(any_scope_bucket_rows),
            "rows_needed_to_minimum": max(minimum_support_rows - len(exact_bucket_rows), 0),
            "support_ready_by_count": support_ready_by_count,
            "same_calibration_identity_as_current": same_calibration_identity,
            "deployment_promotable_under_current_identity": bool(support_ready_by_count and same_calibration_identity),
            "evidence_role": "current_support_identity" if same_calibration_identity else "reference_only_calibration_window_mismatch",
            "semantic_mismatched_fields_vs_current": [] if same_calibration_identity else ["calibration_window"],
            "exact_bucket_metrics": _metric_summary(exact_bucket_rows),
            "exact_lane_bucket_counts": dict(bucket_counts.most_common(8)),
            "latest_exact_bucket_timestamp": exact_bucket_rows[0].get("timestamp") if exact_bucket_rows else None,
            "oldest_exact_bucket_timestamp": exact_bucket_rows[-1].get("timestamp") if exact_bucket_rows else None,
        }

    current_key = str(calibration_window) if str(calibration_window) in window_scan else None
    current_scan = window_scan.get(current_key or "", {})
    reference_candidates = [
        {"window_key": key, **scan}
        for key, scan in window_scan.items()
        if not scan.get("same_calibration_identity_as_current")
    ]
    best_reference = max(reference_candidates, key=lambda item: int(item.get("exact_bucket_rows") or 0), default={})
    full_scan = window_scan.get("all") or (list(window_scan.values())[-1] if window_scan else {})
    current_rows = int(current_scan.get("exact_bucket_rows") or 0)
    joined_rows = len(rows)
    current_window_filled = bool(calibration_window > 0 and joined_rows >= calibration_window)

    if current_rows >= minimum_support_rows:
        classification = "current_identity_support_ready"
        can_backfill_close_current_identity = False
        reason = "current support_identity already has enough exact-bucket rows; deployment should depend on the remaining live/execution gates."
    elif not current_window_filled:
        classification = "current_calibration_window_data_gap"
        can_backfill_close_current_identity = True
        reason = "current calibration window is not fully populated with labeled rows; historical/label backfill may add rows before semantic rebaseline is considered."
    elif int(best_reference.get("exact_bucket_rows") or 0) >= minimum_support_rows:
        classification = "semantic_window_gap_not_raw_backfill_gap"
        can_backfill_close_current_identity = False
        reason = (
            "older calibration windows have enough exact-bucket rows by count, but they mismatch the current "
            "support_identity on calibration_window; they are reference-only unless governance deliberately rebaselines the identity."
        )
    elif int(full_scan.get("exact_bucket_rows") or 0) > 0:
        classification = "true_support_under_minimum"
        can_backfill_close_current_identity = False
        reason = "current identity is missing support and full history also remains under minimum; collect forward exact rows or redesign the bucket."
    else:
        classification = "no_exact_bucket_history"
        can_backfill_close_current_identity = False
        reason = "no exact-bucket rows were found under current bucket semantics; this is a support-harvest/design gap, not a backtest-results gap."

    q15_route = q15_audit.get("support_route") if isinstance(q15_audit.get("support_route"), dict) else {}
    active_repair = q15_audit.get("active_repair_plan") if isinstance(q15_audit.get("active_repair_plan"), dict) else {}
    verdict = {
        "classification": classification,
        "reason": reason,
        "can_historical_backfill_close_current_identity": can_backfill_close_current_identity,
        "can_count_reference_windows_as_deployable": False,
        "current_calibration_window": calibration_window,
        "current_exact_bucket_rows": current_rows,
        "minimum_support_rows": minimum_support_rows,
        "gap_to_minimum": max(minimum_support_rows - current_rows, 0),
        "best_reference_window": best_reference.get("window_key"),
        "best_reference_exact_bucket_rows": best_reference.get("exact_bucket_rows"),
        "best_reference_evidence_role": best_reference.get("evidence_role"),
        "q15_support_route_verdict": q15_route.get("verdict"),
        "q15_support_governance_route": q15_route.get("support_governance_route"),
        "q15_active_repair_phase": active_repair.get("phase"),
        "live_exposure_allowed": bool(active_repair.get("live_exposure_allowed", False)),
        "shadow_or_paper_allowed": bool(active_repair.get("shadow_or_paper_allowed", True)),
    }

    actions = [
        {
            "id": "keep_deployment_fail_closed",
            "priority": "P0",
            "description": "維持 unsupported_exact_live_structure_bucket / allowed_layers=0；reference windows 不可直接算作 deployment support。",
            "success_condition": "current support_identity exact rows >= minimum 且 live/execution gates 同步通過。",
        },
        {
            "id": "collect_forward_exact_current_identity_rows",
            "priority": "P0",
            "description": "繼續收集與 current calibration_window=100、regime/gate/entry_label/bucket 完全一致的真實 labeled rows。",
            "success_condition": f"current_exact_bucket_rows >= {minimum_support_rows}",
            "current_rows": current_rows,
            "rows_needed": max(minimum_support_rows - current_rows, 0),
        },
        {
            "id": "semantic_rebaseline_if_using_older_windows",
            "priority": "P1",
            "description": "若要採用 600/all 等舊窗口的足量 rows，必須先改 support_identity / calibration_window policy，重跑 OOS、Top-K、support audit、API/trade guardrail，而不是把舊 rows 直接補進 current identity。",
            "success_condition": "新 identity 全欄位一致且重新驗證後仍 rows>=minimum、risk metrics 合格。",
            "reference_window": best_reference.get("window_key"),
            "reference_rows": best_reference.get("exact_bucket_rows"),
        },
    ]

    return {
        "generated_at": generated_at or _utc_now_iso(),
        "artifact": "q15_support_fill_feasibility",
        "source_artifacts": source_artifacts or {},
        "support_identity": support_identity,
        "data_coverage": {
            "joined_labeled_rows": joined_rows,
            "current_calibration_window_filled": current_window_filled,
            "db_meta": db_meta or {},
        },
        "verdict": verdict,
        "window_scan": window_scan,
        "recommended_actions": actions,
    }


def markdown(report: dict[str, Any]) -> str:
    verdict = report.get("verdict") or {}
    identity = report.get("support_identity") or {}
    coverage = report.get("data_coverage") or {}
    source_artifacts = report.get("source_artifacts") or {}
    lines = [
        "# q15 support-fill feasibility scan",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- source live probe generated_at: `{source_artifacts.get('live_predict_probe_generated_at')}`",
        f"- source q15 audit generated_at: `{source_artifacts.get('q15_support_audit_generated_at')}`",
        f"- classification: **{verdict.get('classification')}**",
        f"- reason: {verdict.get('reason')}",
        f"- current rows: **{verdict.get('current_exact_bucket_rows')}/{verdict.get('minimum_support_rows')}**",
        f"- gap_to_minimum: **{verdict.get('gap_to_minimum')}**",
        f"- historical backfill can close current identity: **{verdict.get('can_historical_backfill_close_current_identity')}**",
        f"- reference windows deployable by count alone: **{verdict.get('can_count_reference_windows_as_deployable')}**",
        "",
        "## Scanned q15 support identity",
        "",
        "This section is the q15 identity captured by the source artifacts above. Re-check `/api/status` before treating it as the latest live bucket.",
        "",
    ]
    for key in (
        "target_col",
        "horizon_minutes",
        "current_live_structure_bucket",
        "regime_label",
        "regime_gate",
        "entry_quality_label",
        "calibration_window",
        "bucket_semantic_signature",
    ):
        lines.append(f"- {key}: `{identity.get(key)}`")

    lines.extend([
        "",
        "## Data coverage",
        "",
        f"- joined labeled rows: **{coverage.get('joined_labeled_rows')}**",
        f"- current calibration window filled: **{coverage.get('current_calibration_window_filled')}**",
    ])
    db_meta = coverage.get("db_meta") or {}
    for table, meta in db_meta.items():
        lines.append(
            f"- {table}: count={meta.get('count')}, range=`{meta.get('min_ts')}` → `{meta.get('max_ts')}`"
        )

    lines.extend([
        "",
        "## Window scan",
        "",
        "| window | exact identity rows | exact bucket rows | role | promotable | latest exact bucket | metrics |",
        "| --- | ---: | ---: | --- | --- | --- | --- |",
    ])
    for key, scan in (report.get("window_scan") or {}).items():
        metrics = scan.get("exact_bucket_metrics") or {}
        metrics_text = (
            f"win={metrics.get('win_rate')}, pnl={metrics.get('avg_pnl')}, "
            f"quality={metrics.get('avg_quality')}"
        )
        lines.append(
            "| "
            f"{key} | {scan.get('exact_identity_rows')} | {scan.get('exact_bucket_rows')} | "
            f"{scan.get('evidence_role')} | {scan.get('deployment_promotable_under_current_identity')} | "
            f"{scan.get('latest_exact_bucket_timestamp')} | {metrics_text} |"
        )

    lines.extend(["", "## Recommended actions", ""])
    for action in report.get("recommended_actions") or []:
        lines.append(f"- **{action.get('id')}** ({action.get('priority')}): {action.get('description')}")
        lines.append(f"  - success: {action.get('success_condition')}")

    lines.extend([
        "",
        "## Operator conclusion",
        "",
        "舊窗口 / full-history rows 可以當治理參考與 rebaseline 候選，但在 `calibration_window` 不吻合前，不能把它們直接補成 current deployment support rows。",
    ])
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    probe = _load_json(PROBE_PATH)
    q15_audit = _load_json(Q15_AUDIT_PATH)
    identity = support_identity_from_artifacts(probe, q15_audit)
    rows = fetch_labeled_decision_rows(
        db_path=DB_PATH,
        horizon_minutes=_as_int(identity.get("horizon_minutes"), DEFAULT_HORIZON_MINUTES),
    )
    report = build_feasibility_report(
        rows=rows,
        support_identity=identity,
        db_meta=fetch_db_meta(DB_PATH),
        q15_audit=q15_audit,
        source_artifacts={
            "live_predict_probe_path": str(PROBE_PATH.relative_to(PROJECT_ROOT)),
            "live_predict_probe_generated_at": probe.get("generated_at"),
            "q15_support_audit_path": str(Q15_AUDIT_PATH.relative_to(PROJECT_ROOT)),
            "q15_support_audit_generated_at": q15_audit.get("generated_at"),
        },
        minimum_support_rows=_as_int(
            probe.get("minimum_support_rows")
            or (q15_audit.get("support_route") or {}).get("minimum_support_rows"),
            DEFAULT_MINIMUM_SUPPORT_ROWS,
        ),
    )
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(markdown(report), encoding="utf-8")
    verdict = report["verdict"]
    print(
        "q15 support-fill feasibility: "
        f"{verdict['classification']} rows={verdict['current_exact_bucket_rows']}/"
        f"{verdict['minimum_support_rows']} best_reference="
        f"{verdict.get('best_reference_window')}:{verdict.get('best_reference_exact_bucket_rows')}"
    )


if __name__ == "__main__":
    main()
