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
from scripts.issues import (
    CURRENT_LIVE_BLOCKER_ISSUE_ID,
    IssueTracker,
    normalize_verify_steps,
)

CORE_FEATURES = [
    "feat_eye", "feat_ear", "feat_nose", "feat_tongue", "feat_body",
    "feat_pulse", "feat_aura", "feat_mind", "feat_vix", "feat_dxy",
    "feat_rsi14", "feat_macd_hist", "feat_atr_pct", "feat_vwap_dev", "feat_bb_pct_b",
]


CANONICAL_BREAKER_HORIZON_MINUTES = 1440


def _is_reference_only_patch_status(status: object) -> bool:
    return str(status or "").startswith("reference_only_")


def _table_has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(str(row[1]) == column for row in rows)



def _latest_zero_streak(
    conn: sqlite3.Connection,
    *,
    horizon_minutes: int | None = None,
    limit: int | None = None,
) -> int:
    sql = "SELECT simulated_pyramid_win FROM labels WHERE simulated_pyramid_win IS NOT NULL"
    params = []
    if horizon_minutes is not None:
        sql += " AND horizon_minutes = ?"
        params.append(horizon_minutes)

    if _table_has_column(conn, "labels", "timestamp"):
        # Keep breaker/streak math aligned with hb_circuit_breaker_audit.py.
        # Ordering by timestamp first avoids out-of-order backfill/update rows,
        # and removing the hard 200-row cap prevents truncating real streaks.
        sql += " ORDER BY timestamp DESC, id DESC"
    else:
        sql += " ORDER BY id DESC"

    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)

    losing_streak = 0
    for (value,) in conn.execute(sql, params):
        if int(value or 0) == 0:
            losing_streak += 1
        else:
            break
    return losing_streak



def check_db():
    conn = sqlite3.connect(str(ROOT / "poly_trader.db"))
    simulated_win = conn.execute(
        "SELECT AVG(simulated_pyramid_win) FROM labels WHERE simulated_pyramid_win IS NOT NULL"
    ).fetchone()[0]
    has_horizon_column = _table_has_column(conn, "labels", "horizon_minutes")
    all_horizon_losing_streak = _latest_zero_streak(conn)

    canonical_horizon_minutes = None
    losing_streak = all_horizon_losing_streak
    if has_horizon_column:
        canonical_rows = conn.execute(
            "SELECT COUNT(*) FROM labels WHERE simulated_pyramid_win IS NOT NULL AND horizon_minutes = ?",
            (CANONICAL_BREAKER_HORIZON_MINUTES,),
        ).fetchone()[0]
        if canonical_rows:
            canonical_horizon_minutes = CANONICAL_BREAKER_HORIZON_MINUTES
            losing_streak = _latest_zero_streak(conn, horizon_minutes=canonical_horizon_minutes)

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
        "all_horizon_losing_streak": all_horizon_losing_streak,
        "canonical_horizon_minutes": canonical_horizon_minutes,
        "raw_latest_age_min": round(age_min, 1) if age_min is not None else None,
    }


def upsert_issue(tracker, priority, issue_id, title, action="", status="open", summary=None, verify=None):
    """Update tracker metadata and overwrite machine-readable summary when provided."""
    tracker.add(priority, issue_id, title, action, status)
    issues = getattr(tracker, "issues", None)
    if not isinstance(issues, list):
        return
    for issue in issues:
        if issue.get("id") != issue_id:
            continue
        if summary is not None:
            issue["summary"] = summary
        if verify is not None:
            normalized_verify = normalize_verify_steps(verify)
            if normalized_verify in (None, "", []):
                issue.pop("verify", None)
            else:
                issue["verify"] = normalized_verify
        issue["updated_at"] = datetime.utcnow().isoformat()
        return


def resolve_legacy_issue_id(tracker, legacy_issue_id):
    """Resolve an exact legacy issue id without following alias rewrites.

    The structured tracker rewrites legacy ids (for example
    ``P0_circuit_breaker_active`` → ``P0_current_live_deployment_blocker``)
    on load/save. During migration we still need to close the legacy record
    without accidentally resolving the new canonical issue we just upserted.
    """
    issues = getattr(tracker, "issues", None)
    if not isinstance(issues, list):
        return False
    for issue in issues:
        if issue.get("id") != legacy_issue_id:
            continue
        issue["status"] = "resolved"
        issue["updated_at"] = datetime.utcnow().isoformat()
        return True
    return False



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


def _recent_drift_window_payload(report, key="primary_window"):
    payload = (report or {}).get(key) or {}
    summary = payload.get("summary") or {}
    return payload, summary


def _blocking_recent_drift_window(report):
    blocking, summary = _recent_drift_window_payload(report, "blocking_window")
    if blocking and summary:
        return blocking, summary

    def _severity(alerts):
        alerts = list(alerts or [])
        score = 0
        if "constant_target" in alerts:
            score += 4
        if "label_imbalance" in alerts:
            score += 3
        if "regime_concentration" in alerts:
            score += 2
        if "regime_shift" in alerts:
            score += 1
        return score

    candidates = []
    for window, summary in ((report or {}).get("windows") or {}).items():
        if not isinstance(summary, dict):
            continue
        interpretation = summary.get("drift_interpretation")
        if interpretation not in {"distribution_pathology", "regime_concentration"}:
            continue
        quality = summary.get("quality_metrics") or {}
        win_rate = summary.get("win_rate")
        avg_pnl = quality.get("avg_simulated_pnl")
        avg_quality = quality.get("avg_simulated_quality")
        spot_long_win = quality.get("spot_long_win_rate")
        negative = any(
            [
                isinstance(win_rate, (int, float)) and win_rate <= 0.25,
                isinstance(avg_pnl, (int, float)) and avg_pnl <= 0.0,
                isinstance(avg_quality, (int, float)) and avg_quality <= 0.0,
                isinstance(spot_long_win, (int, float)) and spot_long_win <= 0.20,
            ]
        )
        if not negative:
            continue
        negativity = max(0.0, 0.5 - float(win_rate or 0.5)) + max(0.0, -float(avg_pnl or 0.0)) + max(0.0, -float(avg_quality or 0.0))
        payload = {"window": str(window), "alerts": summary.get("alerts") or [], "summary": summary}
        candidates.append(((_severity(payload["alerts"]), negativity, int(summary.get("rows") or 0)), payload))

    if not candidates:
        return {}, {}
    payload = max(candidates, key=lambda item: item[0])[1]
    return payload, payload.get("summary") or {}


def load_live_predict_probe():
    path = ROOT / "data" / "live_predict_probe.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def load_leaderboard_candidate_probe():
    path = ROOT / "data" / "leaderboard_feature_profile_probe.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def load_q35_scaling_audit():
    path = ROOT / "data" / "q35_scaling_audit.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def issue_action_text(item):
    action = item.get("action")
    if isinstance(action, str) and action.strip():
        return action.strip()
    next_action = item.get("next_action")
    if isinstance(next_action, str) and next_action.strip():
        return next_action.strip()
    next_actions = item.get("next_actions")
    if isinstance(next_actions, list):
        steps = [str(step).strip() for step in next_actions if str(step).strip()]
        if steps:
            return "；".join(steps)
    if isinstance(next_actions, str) and next_actions.strip():
        return next_actions.strip()
    summary = item.get("summary")
    if isinstance(summary, dict):
        for key in ("recommended_action", "next_action"):
            value = summary.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def sync_current_state_governance_issues(
    tracker,
    leaderboard_probe,
    metrics_or_live_probe,
    maybe_metrics=None,
    q35_scaling_audit=None,
):
    """Keep current-state issue IDs aligned with the latest live bucket/governance facts."""
    if maybe_metrics is None:
        metrics = metrics_or_live_probe or {}
        live_predict_probe = {}
    else:
        live_predict_probe = metrics_or_live_probe or {}
        metrics = maybe_metrics or {}
    q35_scaling_audit = q35_scaling_audit or {}

    def _first_non_null(*values):
        for value in values:
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            return value
        return None

    def _as_int_or_none(value):
        try:
            if value is None:
                return None
            return int(value)
        except Exception:
            return None

    alignment = (leaderboard_probe or {}).get("alignment") or {}
    governance = alignment.get("governance_contract") or {}
    support_progress = governance.get("support_progress") or {}
    support_history = support_progress.get("history") or []
    history_bucket = (support_history[0] or {}).get("live_current_structure_bucket") if support_history else None
    live_current_bucket = (live_predict_probe or {}).get("current_live_structure_bucket")
    live_signal = str((live_predict_probe or {}).get("signal") or "").strip()
    live_blocker = str((live_predict_probe or {}).get("deployment_blocker") or "").strip()
    runtime_closure_state = str((live_predict_probe or {}).get("runtime_closure_state") or "").strip()
    live_blocker_details = (live_predict_probe or {}).get("deployment_blocker_details") or {}
    if not isinstance(live_blocker_details, dict):
        live_blocker_details = {}
    live_support_reason = " ".join(
        str(value or "")
        for value in [
            (live_predict_probe or {}).get("allowed_layers_reason"),
            (live_predict_probe or {}).get("execution_guardrail_reason"),
            (live_predict_probe or {}).get("deployment_blocker"),
            (live_predict_probe or {}).get("deployment_blocker_reason"),
        ]
    )
    circuit_breaker_active = (
        live_signal == "CIRCUIT_BREAKER"
        or live_blocker == "circuit_breaker_active"
        or runtime_closure_state == "circuit_breaker_active"
        or "circuit_breaker_blocks_trade" in live_support_reason
    )
    current_bucket = _first_non_null(
        live_current_bucket,
        None if circuit_breaker_active and not live_current_bucket else history_bucket,
        None if circuit_breaker_active and not live_current_bucket else (leaderboard_probe or {}).get("live_current_structure_bucket"),
    )
    current_rows = _first_non_null(
        _as_int_or_none((live_predict_probe or {}).get("current_live_structure_bucket_rows")),
        None if circuit_breaker_active and not live_current_bucket else _as_int_or_none(governance.get("live_current_structure_bucket_rows")),
        None if circuit_breaker_active and not live_current_bucket else _as_int_or_none(support_progress.get("current_rows")),
        0,
    )
    minimum_rows = _first_non_null(
        _as_int_or_none((live_predict_probe or {}).get("minimum_support_rows")),
        _as_int_or_none(governance.get("minimum_support_rows")),
        _as_int_or_none(support_progress.get("minimum_support_rows")),
        0,
    )
    support_route_verdict = _first_non_null(
        (live_predict_probe or {}).get("support_route_verdict"),
        live_blocker_details.get("support_route_verdict"),
        governance.get("support_route_verdict"),
        support_progress.get("support_route_verdict"),
    )
    support_governance_route = _first_non_null(
        (live_predict_probe or {}).get("support_governance_route"),
        live_blocker_details.get("support_governance_route"),
        governance.get("support_governance_route"),
        support_progress.get("support_governance_route"),
    )
    live_bucket_blocked = (
        "unsupported_exact_live_structure_bucket" in live_support_reason
        or "under_minimum_exact_live_structure_bucket" in live_support_reason
    )
    live_bucket_meets_minimum = bool(current_bucket) and minimum_rows > 0 and int(current_rows or 0) >= int(minimum_rows or 0)
    support_gap_markers = {
        "exact_live_bucket_present_but_below_minimum",
        "exact_bucket_present_but_below_minimum",
        "exact_bucket_missing_exact_lane_proxy_only",
        "exact_bucket_missing_proxy_reference_only",
        "no_support_proxy",
        "insufficient_support_everywhere",
    }
    route_indicates_support_gap = (
        support_route_verdict in support_gap_markers
        or support_governance_route in support_gap_markers
    )
    current_bucket_support_active = bool(current_bucket) and minimum_rows > 0 and (
        live_bucket_blocked
        or (int(current_rows or 0) < int(minimum_rows or 0) and (route_indicates_support_gap or not live_bucket_meets_minimum))
    )

    stale_q35_issue_ids = [
        "P1_q35_exact_support_under_minimum",
        "P1_current_q35_exact_support",
    ]
    if "q35" not in str(current_bucket or ""):
        for issue_id in stale_q35_issue_ids + ["P1_q35_redesign_support_blocked"]:
            tracker.resolve(issue_id)
    else:
        for issue_id in stale_q35_issue_ids:
            tracker.resolve(issue_id)

    support_progress_status = support_progress.get("status") or (
        "stalled_under_minimum" if int(current_rows or 0) <= 0 else "present_but_below_minimum"
    )
    support_issue_title = f"q15 exact support remains under minimum under breaker ({current_rows}/{minimum_rows})"
    support_issue_action = "Keep support_route_verdict/support_progress/minimum_support_rows/gap_to_minimum visible in probe/API/UI/docs even when circuit_breaker_active is the primary blocker."
    if support_progress_status == "regressed_under_minimum":
        support_state = "exact support regressed back under minimum"
        support_issue_title = f"q15 exact support regressed back under minimum under breaker ({current_rows}/{minimum_rows})"
        support_issue_action = (
            "Treat this as support regression, not ordinary stagnation: keep support_route_verdict/support_progress/"
            "minimum_support_rows/gap_to_minimum plus the last-supported reference visible in probe/API/UI/docs, "
            "and verify why the current bucket fell back under minimum."
        )
    elif int(current_rows or 0) <= 0:
        support_state = "exact support is missing"
    else:
        support_state = "support remains under minimum"
    if current_bucket_support_active:
        tracker.add(
            "P1",
            "#H_AUTO_CURRENT_BUCKET_SUPPORT",
            f"current live bucket {current_bucket} {support_state} ({current_rows}/{minimum_rows})",
            "以 current live structure bucket 為主追 exact support / governance route；不要沿用舊 q35 blocker 當成本輪主 blocker。",
        )
    else:
        tracker.resolve("#H_AUTO_CURRENT_BUCKET_SUPPORT")

    if current_bucket_support_active and "q15" in str(current_bucket or ""):
        upsert_issue(
            tracker,
            "P1",
            "P1_q15_exact_support_stalled_under_breaker",
            support_issue_title,
            support_issue_action,
            summary={
                "current_live_structure_bucket": current_bucket,
                "live_current_structure_bucket_rows": int(current_rows or 0),
                "minimum_support_rows": int(minimum_rows or 0),
                "gap_to_minimum": max(int(minimum_rows or 0) - int(current_rows or 0), 0),
                "support_route_verdict": support_route_verdict,
                "support_governance_route": support_governance_route,
                "support_progress_status": support_progress_status,
                "previous_rows": support_progress.get("previous_rows"),
                "delta_vs_previous": support_progress.get("delta_vs_previous"),
                "recent_supported_rows": support_progress.get("recent_supported_rows"),
                "recent_supported_heartbeat": support_progress.get("recent_supported_heartbeat"),
                "delta_vs_recent_supported": support_progress.get("delta_vs_recent_supported"),
                "leaderboard_selected_profile": alignment.get("leaderboard_selected_profile")
                or alignment.get("selected_feature_profile")
                or (leaderboard_probe or {}).get("selected_feature_profile"),
                "train_selected_profile": governance.get("production_profile") or governance.get("production_profile_name"),
                "governance_contract": governance.get("verdict"),
            },
        )
    else:
        tracker.resolve("P1_q15_exact_support_stalled_under_breaker")

    tracker.resolve("P1_q35_redesign_support_blocked")

    q35_scope = (q35_scaling_audit.get("scope_applicability") or {}) if isinstance(q35_scaling_audit, dict) else {}
    q35_current_live = (q35_scaling_audit.get("current_live") or {}) if isinstance(q35_scaling_audit, dict) else {}
    q35_component = (
        (q35_scaling_audit.get("deployment_grade_component_experiment") or {})
        if isinstance(q35_scaling_audit, dict)
        else {}
    )
    q35_redesign = (
        (q35_scaling_audit.get("base_stack_redesign_experiment") or {})
        if isinstance(q35_scaling_audit, dict)
        else {}
    )
    q35_scope_status = str(q35_scope.get("status") or "")
    q35_bucket = str(
        q35_current_live.get("structure_bucket")
        or q35_current_live.get("current_live_structure_bucket")
        or current_bucket
        or ""
    )
    q35_overall_verdict = str(q35_scaling_audit.get("overall_verdict") or "")
    q35_redesign_verdict = str(q35_redesign.get("verdict") or "")
    q35_gap_to_floor = q35_component.get("runtime_remaining_gap_to_floor")
    q35_entry_quality = q35_current_live.get("entry_quality")
    q35_audit_active = (
        "q35" in q35_bucket
        and q35_scope_status == "current_live_q35_lane_active"
        and q35_overall_verdict not in {"", "runtime_blocker_preempts_q35_scaling", "reference_only_current_bucket_outside_q35"}
        and q35_redesign_verdict != "base_stack_redesign_discriminative_reweight_crosses_trade_floor"
    )
    if q35_audit_active:
        q35_title = "q35 lane still needs formula review / base-stack redesign before deploy"
        q35_action = (
            "把 q35 scaling audit 的 overall_verdict / redesign verdict / gap-to-floor 同步到 docs/probe/issues；"
            "在 exact support 未就緒、且 redesign 仍無正 discrimination floor-cross 之前，禁止把 bias50 單點 uplift 或結構 uplift 當成 closure。"
        )
        recommended_action = q35_scaling_audit.get("recommended_action")
        if isinstance(recommended_action, str) and recommended_action.strip():
            q35_action = q35_action + " " + recommended_action.strip()
        upsert_issue(
            tracker,
            "P1",
            "P1_q35_scaling_no_deploy",
            q35_title,
            q35_action,
            summary={
                "current_live_structure_bucket": q35_bucket or current_bucket,
                "current_live_structure_bucket_rows": int(current_rows or 0),
                "minimum_support_rows": int(minimum_rows or 0),
                "gap_to_minimum": max(int(minimum_rows or 0) - int(current_rows or 0), 0),
                "support_route_verdict": support_route_verdict,
                "overall_verdict": q35_overall_verdict or None,
                "redesign_verdict": q35_redesign_verdict or None,
                "remaining_gap_to_floor": q35_gap_to_floor,
                "entry_quality": q35_entry_quality,
            },
        )
    else:
        tracker.resolve("P1_q35_scaling_no_deploy")

    pathology_summary = (live_predict_probe or {}).get("decision_quality_scope_pathology_summary") or {}
    recommended_patch = pathology_summary.get("recommended_patch") if isinstance(pathology_summary, dict) else None
    spillover_summary = pathology_summary.get("spillover") if isinstance(pathology_summary, dict) else None
    worst_extra_regime_gate = (
        spillover_summary.get("worst_extra_regime_gate")
        if isinstance(spillover_summary, dict)
        else None
    )
    actual_live_spillover_scope = (
        worst_extra_regime_gate.get("regime_gate") if isinstance(worst_extra_regime_gate, dict) else None
    )
    current_blocker_patch_summary = {}
    if isinstance(recommended_patch, dict) and recommended_patch.get("recommended_profile"):
        current_blocker_patch_summary = {
            "recommended_patch": recommended_patch.get("recommended_profile"),
            "recommended_patch_status": recommended_patch.get("status"),
            "recommended_patch_support_route": recommended_patch.get("support_route_verdict"),
            "reference_patch_scope": recommended_patch.get("reference_patch_scope")
            or recommended_patch.get("spillover_regime_gate"),
            "reference_source": recommended_patch.get("reference_source"),
        }

    patch_status = str(recommended_patch.get("status") or "") if isinstance(recommended_patch, dict) else ""
    if (
        isinstance(recommended_patch, dict)
        and recommended_patch.get("recommended_profile")
        and _is_reference_only_patch_status(patch_status)
    ):
        patch_profile = recommended_patch.get("recommended_profile")
        tracker.resolve("P1_reference_only_patch_visibility")
        reference_patch_scope = recommended_patch.get("reference_patch_scope") or recommended_patch.get("spillover_regime_gate")
        current_live_regime_gate = recommended_patch.get("current_live_regime_gate")
        if patch_status == "reference_only_non_current_live_scope":
            patch_title = (
                f"support-aware {patch_profile} patch must stay visible but reference-only outside current live scope"
            )
            patch_action = (
                "Keep the same recommended_patch summary across /api/status, /lab, hb_predict_probe.py, "
                "live_decision_quality_drilldown.py, and docs; the patch describes a spillover/broader lane rather than the current live scope, "
                "so do not promote it to a deployable runtime patch even though exact support is available."
            )
        else:
            patch_title = f"support-aware {patch_profile} patch must stay visible but reference-only"
            patch_action = (
                "Keep the same recommended_patch summary across /api/status, /lab, hb_predict_probe.py, live_decision_quality_drilldown.py, and docs; "
                "do not promote it from reference-only until current-live exact support reaches the minimum rows."
            )
        upsert_issue(
            tracker,
            "P1",
            "P1_bull_caution_spillover_patch_reference_only",
            patch_title,
            patch_action,
            summary={
                "actual_live_spillover_scope": actual_live_spillover_scope,
                "reference_patch_scope": reference_patch_scope,
                "current_live_regime_gate": current_live_regime_gate,
                "reference_only_cause": recommended_patch.get("reference_only_cause"),
                "exact_live_lane_rows": _as_int_or_none(((pathology_summary.get("exact_live_lane") or {}) if isinstance(pathology_summary, dict) else {}).get("rows")),
                "recommended_patch": patch_profile,
                "recommended_patch_status": recommended_patch.get("status"),
                "support_route_verdict": recommended_patch.get("support_route_verdict"),
                "current_live_structure_bucket": recommended_patch.get("current_live_structure_bucket") or current_bucket,
                "current_live_structure_bucket_rows": _as_int_or_none(recommended_patch.get("current_live_structure_bucket_rows")),
                "minimum_support_rows": _as_int_or_none(recommended_patch.get("minimum_support_rows")),
                "gap_to_minimum": _as_int_or_none(recommended_patch.get("gap_to_minimum")),
                "reference_source": recommended_patch.get("reference_source"),
                "collapse_features": recommended_patch.get("collapse_features") or [],
            },
        )
    else:
        tracker.resolve("P1_bull_caution_spillover_patch_reference_only")
        tracker.resolve("P1_reference_only_patch_visibility")

    if circuit_breaker_active:
        release_condition = (((live_predict_probe or {}).get("deployment_blocker_details") or {}).get("release_condition") or {})
        current_recent_wins = release_condition.get("current_recent_window_wins")
        required_recent_wins = release_condition.get("required_recent_window_wins")
        recent_window = release_condition.get("recent_window")
        additional_wins_needed = release_condition.get("additional_recent_window_wins_needed")
        streak_floor = release_condition.get("streak_must_be_below")
        release_text = (
            f"recent {recent_window} 需至少 {required_recent_wins} 勝，當前 {current_recent_wins} 勝，還差 {additional_wins_needed} 勝；"
            f"同時 streak 必須 < {streak_floor}。"
            if recent_window is not None and required_recent_wins is not None and current_recent_wins is not None and additional_wins_needed is not None and streak_floor is not None
            else "依 hb_circuit_breaker_audit / hb_predict_probe 的 release math 驗證解鎖條件。"
        )
        tracker.resolve("P0_q15_patch_active_but_execution_blocked")
        tracker.resolve("#H_AUTO_CURRENT_BUCKET_TOXICITY")
        breaker_title = (
            f"canonical circuit breaker active ({current_recent_wins}/{required_recent_wins} wins in recent {recent_window})"
            if recent_window is not None and required_recent_wins is not None and current_recent_wins is not None
            else "canonical circuit breaker active"
        )
        breaker_action = (
            "先把 current-live blocker 語義切回 circuit breaker release math；在 breaker 未解除前，不要把 q15/q35 support 或 floor-gap 當成本輪主 blocker。"
            f" {release_text}"
        )
        breaker_summary = {
            "deployment_blocker": (live_predict_probe or {}).get("deployment_blocker"),
            "horizon_minutes": (live_predict_probe or {}).get("horizon_minutes"),
            "recent_window": recent_window,
            "current_recent_window_wins": current_recent_wins,
            "required_recent_window_wins": required_recent_wins,
            "additional_recent_window_wins_needed": additional_wins_needed,
            "streak": (live_predict_probe or {}).get("streak"),
            "streak_must_be_below": streak_floor,
            "current_live_structure_bucket": current_bucket,
            "current_live_structure_bucket_rows": int(current_rows or 0),
            "minimum_support_rows": int(minimum_rows or 0),
            "gap_to_minimum": max(int(minimum_rows or 0) - int(current_rows or 0), 0),
            "support_route_verdict": support_route_verdict,
            "support_governance_route": support_governance_route,
            "runtime_closure_state": runtime_closure_state,
        }
        upsert_issue(
            tracker,
            "P0",
            "#H_AUTO_CIRCUIT_BREAKER",
            breaker_title,
            breaker_action,
            summary=breaker_summary,
        )
        upsert_issue(
            tracker,
            "P0",
            CURRENT_LIVE_BLOCKER_ISSUE_ID,
            "canonical circuit breaker remains the only current-live deployment blocker",
            breaker_action,
            summary=breaker_summary,
        )
        resolve_legacy_issue_id(tracker, "P0_circuit_breaker_active")
    else:
        tracker.resolve("#H_AUTO_CIRCUIT_BREAKER")
        if current_bucket_support_active and live_blocker in {
            "unsupported_exact_live_structure_bucket",
            "under_minimum_exact_live_structure_bucket",
        }:
            support_state = (
                "exact support is missing"
                if int(current_rows or 0) <= 0 or live_blocker == "unsupported_exact_live_structure_bucket"
                else "exact support remains under minimum"
            )
            upsert_issue(
                tracker,
                "P0",
                CURRENT_LIVE_BLOCKER_ISSUE_ID,
                f"current live bucket {current_bucket} {support_state} and remains the deployment blocker ({current_rows}/{minimum_rows})",
                "把 current-live blocker 語義切到 exact-support truth；在 current live bucket 補滿 minimum rows 前，不要把 proxy rows、reference patch、或 breaker 舊敘事誤當成已解除 blocker。",
                summary={
                    "deployment_blocker": live_blocker,
                    "current_live_structure_bucket": current_bucket,
                    "current_live_structure_bucket_rows": int(current_rows or 0),
                    "minimum_support_rows": int(minimum_rows or 0),
                    "gap_to_minimum": max(int(minimum_rows or 0) - int(current_rows or 0), 0),
                    "support_route_verdict": support_route_verdict,
                    "support_governance_route": support_governance_route,
                    "runtime_closure_state": runtime_closure_state,
                    **current_blocker_patch_summary,
                },
            )
            resolve_legacy_issue_id(tracker, "P0_circuit_breaker_active")
        elif live_blocker:
            upsert_issue(
                tracker,
                "P0",
                CURRENT_LIVE_BLOCKER_ISSUE_ID,
                f"current-live deployment blocker is {live_blocker}",
                "把 current-live blocker 真相維持在 API / UI / docs；不要讓舊 breaker / support 敘事覆蓋最新 runtime truth。",
                summary={
                    "deployment_blocker": live_blocker,
                    "current_live_structure_bucket": current_bucket,
                    "current_live_structure_bucket_rows": int(current_rows or 0),
                    "minimum_support_rows": int(minimum_rows or 0),
                    "gap_to_minimum": max(int(minimum_rows or 0) - int(current_rows or 0), 0),
                    "support_route_verdict": support_route_verdict,
                    "support_governance_route": support_governance_route,
                    "runtime_closure_state": runtime_closure_state,
                    **current_blocker_patch_summary,
                },
            )
            resolve_legacy_issue_id(tracker, "P0_circuit_breaker_active")
        else:
            tracker.resolve(CURRENT_LIVE_BLOCKER_ISSUE_ID)
            resolve_legacy_issue_id(tracker, "P0_circuit_breaker_active")

    toxic_blocker = str((live_predict_probe or {}).get("deployment_blocker") or "")
    toxic_current_bucket_active = bool(current_bucket) and (
        toxic_blocker == "exact_live_lane_toxic_sub_bucket_current_bucket"
        or "exact_live_lane_toxic_sub_bucket_current_bucket_blocks_trade" in live_support_reason
    )
    if toxic_current_bucket_active:
        tracker.add(
            "P0",
            "#H_AUTO_CURRENT_BUCKET_TOXICITY",
            f"current live bucket {current_bucket} is exact-lane toxic despite exact support ({current_rows} rows)",
            "把 current live bucket 視為 hold-only；維持 toxic sub-bucket blocker 在 runtime/docs 的 machine-read truth，直到 bucket-level win/quality 明顯改善。",
        )
    else:
        tracker.resolve("#H_AUTO_CURRENT_BUCKET_TOXICITY")

    alignment_issue_ids = ["P1_alignment_artifacts_need_refresh", "#H_AUTO_ALIGNMENT_GOVERNANCE"]
    legacy_alignment_issue_ids = ["P1_leaderboard_alignment_snapshot_stale"]
    for issue_id in legacy_alignment_issue_ids:
        tracker.resolve(issue_id)

    alignment_blocked = bool(alignment.get("current_alignment_inputs_stale")) or bool(governance.get("treat_as_parity_blocker"))
    if alignment_blocked:
        tracker.add(
            "P1",
            "#H_AUTO_ALIGNMENT_GOVERNANCE",
            f"alignment governance still blocked ({governance.get('current_closure') or 'unknown_closure'})",
            governance.get("recommended_action") or "刷新 alignment / leaderboard candidate probe，讓 current inputs 與治理結論一致。",
        )
    else:
        for issue_id in alignment_issue_ids:
            tracker.resolve(issue_id)

    leaderboard_current_state = (leaderboard_probe or {}).get("leaderboard_current_state") or {}
    leaderboard_count = _as_int_or_none((leaderboard_probe or {}).get("leaderboard_count"))
    top_model = (leaderboard_probe or {}).get("top_model") or {}
    comparable_count = _first_non_null(
        _as_int_or_none(leaderboard_current_state.get("comparable_count")),
        _as_int_or_none(top_model.get("comparable_count")),
    )
    placeholder_count = _first_non_null(
        _as_int_or_none(leaderboard_current_state.get("placeholder_count")),
        _as_int_or_none(top_model.get("placeholder_count")),
    )
    top_model_name = top_model.get("model_name")
    top_profile = _first_non_null(
        alignment.get("leaderboard_selected_profile"),
        alignment.get("selected_feature_profile"),
        top_model.get("selected_feature_profile"),
        top_model.get("feature_profile"),
    )
    top_deployment_profile = _first_non_null(
        top_model.get("selected_deployment_profile"),
        top_model.get("deployment_profile"),
    )
    if leaderboard_count is not None or comparable_count is not None or top_model_name:
        leaderboard_issue_title = (
            "leaderboard comparable rows are back; keep the recent-window contract stable and cron-safe"
            if (comparable_count or 0) > 0
            else "leaderboard comparable rows are missing; keep the recent-window contract honest"
        )
        leaderboard_issue_action = (
            "Keep /api/models/leaderboard and Strategy Lab aligned on latest bounded walk-forward plus the recent-two-year backtest policy; do not regress to placeholder-only or ambiguous backtest windows."
            if (comparable_count or 0) > 0
            else "Restore comparable leaderboard rows or keep placeholder-only state explicit; do not let Strategy Lab or docs imply a stable ranking when the recent-window contract is missing."
        )
        upsert_issue(
            tracker,
            "P1",
            "P1_leaderboard_recent_window_contract",
            leaderboard_issue_title,
            leaderboard_issue_action,
            summary={
                "leaderboard_count": leaderboard_count,
                "comparable_count": comparable_count,
                "placeholder_count": placeholder_count,
                "top_model": top_model_name,
                "top_profile": top_profile,
                "top_deployment_profile": top_deployment_profile,
                "governance_contract": governance.get("verdict"),
                "current_closure": governance.get("current_closure"),
                "leaderboard_payload_source": (leaderboard_probe or {}).get("leaderboard_payload_source"),
                "dual_profile_state": alignment.get("dual_profile_state"),
            },
            verify=[
                "browser /lab",
                "curl http://127.0.0.1:<active-backend>/api/models/leaderboard",
                "pytest tests/test_model_leaderboard.py tests/test_strategy_lab.py tests/test_frontend_decision_contract.py -q",
            ],
        )

    cv = metrics.get("cv_accuracy")
    cv_std = metrics.get("cv_std")
    cv_worst = metrics.get("cv_worst")
    stability_issue_ids = ["P1_model_accuracy_stability", "#H_AUTO_MODEL_STABILITY"]
    if isinstance(cv, (int, float)) and isinstance(cv_std, (int, float)):
        cv_worst_text = f"{cv_worst:.4f}" if isinstance(cv_worst, (int, float)) else "n/a"
        stability_issue = cv_std >= 0.10 or (isinstance(cv_worst, (int, float)) and cv_worst < 0.60)
        if stability_issue:
            upsert_issue(
                tracker,
                "P1",
                "#H_AUTO_MODEL_STABILITY",
                f"model stability still needs work (cv={cv:.4f}, cv_std={cv_std:.4f}, cv_worst={cv_worst_text})",
                "優先比較 support-aware / shrinkage profiles 與 current bucket robustness，避免把治理 blocker 誤當單純 parity 問題。",
                summary={
                    "cv_accuracy": cv,
                    "cv_std": cv_std,
                    "cv_worst": cv_worst,
                },
            )
            tracker.resolve("P1_model_accuracy_stability")
        else:
            for issue_id in stability_issue_ids:
                tracker.resolve(issue_id)


def summarize_recent_drift_window(primary):
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
        f", overlay_only:{feature_diag.get('overlay_only_count', 0)}"
        f", unexpected_frozen:{feature_diag.get('unexpected_frozen_count', 0)}"
        f", distinct:{feature_diag.get('low_distinct_count', 0)}"
        f", null_heavy:{feature_diag.get('null_heavy_count', 0)}"
    )
    low_variance_examples = feature_diag.get("low_variance_examples") or []
    low_distinct_examples = feature_diag.get("low_distinct_examples") or []
    frozen_examples = feature_diag.get("frozen_examples") or []
    compressed_examples = feature_diag.get("compressed_examples") or []
    expected_static_examples = feature_diag.get("expected_static_examples") or []
    overlay_only_examples = feature_diag.get("overlay_only_examples") or []
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
    if overlay_only_examples:
        example_bits.append(
            "overlay_only_examples=" + "/".join(
                f"{row.get('feature')}[{row.get('overlay_only_reason')}]"
                for row in overlay_only_examples[:3]
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
    adverse_streak = _select_adverse_target_streak(path_diag)
    recent_examples = path_diag.get("recent_examples") or []
    recent_examples_text = ""
    if recent_examples:
        recent_examples_text = ", recent_examples=" + "/".join(
            f"{row.get('timestamp')}:{row.get('target')}:{row.get('regime')}:{row.get('simulated_pyramid_quality')}"
            for row in recent_examples[-3:]
        )
    adverse_examples = adverse_streak.get("examples") or []
    adverse_examples_text = ""
    if adverse_examples:
        adverse_examples_text = ", adverse_examples=" + "/".join(
            f"{row.get('timestamp')}:{row.get('target')}:{row.get('regime')}:{row.get('simulated_pyramid_quality')}"
            for row in adverse_examples[-3:]
        )
    tail_text = ", " + _format_streak_fragment("tail_streak", tail_streak)
    adverse_text = ", " + _format_streak_fragment("adverse_streak", adverse_streak, default_target=0)
    reference = summary.get("reference_window_comparison") or {}
    reference_text = ""
    if reference:
        ref_quality = reference.get("reference_quality") or {}
        reference_text = (
            f", prev_win_rate={ref_quality.get('win_rate')}"
            f", delta_vs_prev={reference.get('win_rate_delta_vs_reference')}"
            f", prev_quality={ref_quality.get('avg_simulated_quality')}"
            f", quality_delta_vs_prev={reference.get('avg_simulated_quality_delta_vs_reference')}"
            f", prev_pnl={ref_quality.get('avg_simulated_pnl')}"
            f", pnl_delta_vs_prev={reference.get('avg_simulated_pnl_delta_vs_reference')}"
        )
        top_shift = reference.get("top_mean_shift_features") or []
        if top_shift:
            reference_text += ", top_shift_examples=" + "/".join(
                f"{row.get('feature')}({row.get('reference_mean')}→{row.get('current_mean')},Δσ={row.get('delta_vs_baseline_std')})"
                for row in top_shift[:3]
            )
        new_flags = []
        if reference.get("new_unexpected_frozen_features"):
            new_flags.append("new_frozen=" + "/".join(reference.get("new_unexpected_frozen_features")[:3]))
        if reference.get("new_unexpected_compressed_features"):
            new_flags.append("new_compressed=" + "/".join(reference.get("new_unexpected_compressed_features")[:3]))
        if reference.get("new_null_heavy_features"):
            new_flags.append("new_null_heavy=" + "/".join(reference.get("new_null_heavy_features")[:3]))
        if new_flags:
            reference_text += ", " + ", ".join(new_flags)
    examples_text = (", " + ", ".join(example_bits)) if example_bits else ""
    return (
        f"recent_window={window}, alerts={alerts}, win_rate={win_text}, "
        f"delta_vs_full={delta_text}, dominant_regime={dominant_regime}({share_text}), "
        f"interpretation={interpretation}, avg_pnl={pnl_text}, avg_quality={quality_text}, "
        f"avg_dd_penalty={dd_text}, spot_long_win_rate={spot_long_text}, {feature_summary}"
        f"{tail_text}{adverse_text}{reference_text}{examples_text}{recent_examples_text}{adverse_examples_text}"
    )


def _select_adverse_target_streak(path_diag):
    streak = dict((path_diag or {}).get("longest_zero_target_streak") or {})
    if streak.get("target") is None:
        streak["target"] = 0
    streak.setdefault("count", 0)
    streak.setdefault("start_timestamp", None)
    streak.setdefault("end_timestamp", None)
    streak.setdefault("examples", [])
    return streak


def _format_streak_fragment(name, streak, default_target=None):
    streak = dict(streak or {})
    target = streak.get("target")
    if target is None:
        target = default_target
    count = int(streak.get("count") or 0)
    target_text = "n/a" if target is None else str(target)
    text = f"{name}={count}x{target_text}"
    start = streak.get("start_timestamp")
    end = streak.get("end_timestamp")
    if start and end:
        text += f" since {start} -> {end}"
    return text


def summarize_recent_drift(report):
    primary, primary_summary = _recent_drift_window_payload(report, "primary_window")
    blocking, blocking_summary = _blocking_recent_drift_window(report)
    preferred = blocking if blocking and blocking_summary else primary
    summary = summarize_recent_drift_window(preferred)
    if blocking and primary and blocking.get("window") != primary.get("window"):
        latest_win = primary_summary.get("win_rate")
        latest_win_text = f"{latest_win:.4f}" if isinstance(latest_win, (int, float)) else "n/a"
        latest_interpretation = primary_summary.get("drift_interpretation") or "unknown"
        summary += (
            f", latest_window={primary.get('window')}, latest_interpretation={latest_interpretation}, "
            f"latest_win_rate={latest_win_text}, latest_alerts={primary.get('alerts') or []}"
        )
    return summary


def _format_recent_regime_counts(counts):
    if not counts:
        return ""
    parts = [f"{regime}:{count}" for regime, count in sorted(counts.items(), key=lambda item: (-int(item[1]), str(item[0])))]
    return "/".join(parts)


def summarize_live_predict_probe(report):
    if not report:
        return "live_predict_probe=missing"
    summary = report.get("decision_quality_recent_pathology_summary") or {}
    reference = summary.get("reference_window_comparison") or {}
    top_shifts = reference.get("top_mean_shift_features") or []
    top_shift_text = "/".join(
        f"{row.get('feature')}({row.get('reference_mean')}→{row.get('current_mean')})"
        for row in top_shifts[:3]
        if row.get("feature")
    )
    window = report.get("decision_quality_recent_pathology_window")
    alerts = report.get("decision_quality_recent_pathology_alerts") or []
    win_rate = report.get("expected_win_rate")
    quality = report.get("expected_pyramid_quality")
    pnl = report.get("expected_pyramid_pnl")
    scope = report.get("decision_quality_calibration_scope") or "unknown"
    label = report.get("decision_quality_label") or "unknown"
    layers_raw = report.get("allowed_layers_raw")
    layers = report.get("allowed_layers")
    regime = report.get("regime_label") or "unknown"
    gate = report.get("regime_gate") or "unknown"
    sample_size = report.get("decision_quality_sample_size")
    scope_diags = report.get("decision_quality_scope_diagnostics") or {}
    exact_scope_info = scope_diags.get("regime_label+regime_gate+entry_quality_label") or {}

    def _format_feature_contrast(contrast, prefix):
        if not contrast:
            return ""
        top_shift = contrast.get("top_mean_shift_features") or []
        if not top_shift:
            return ""
        shift_text = "/".join(
            f"{row.get('feature')}({row.get('reference_mean')}→{row.get('current_mean')},Δ={row.get('mean_delta')})"
            for row in top_shift[:4]
            if row.get("feature")
        )
        return f",{prefix}={shift_text}" if shift_text else ""

    def _format_feature_snapshot(snapshot, prefix):
        if not snapshot:
            return ""
        ordered_keys = [
            "feat_4h_bias200",
            "feat_4h_bb_pct_b",
            "feat_4h_dist_bb_lower",
            "feat_4h_dist_swing_low",
        ]
        bits = []
        for key in ordered_keys:
            row = snapshot.get(key) or {}
            if row.get("current_mean") is None and row.get("reference_mean") is None:
                continue
            bits.append(f"{key}({row.get('reference_mean')}→{row.get('current_mean')},Δ={row.get('mean_delta')})")
        if not bits:
            return ""
        return f",{prefix}={'/'.join(bits)}"

    def _format_gate_path_summary(summary, prefix):
        if not summary:
            return ""
        def _fmt_counts(counts):
            if not counts:
                return "none"
            return "/".join(f"{k}:{v}" for k, v in sorted(counts.items()))
        structure_dist = summary.get("structure_quality_distribution") or {}
        gate_bands = summary.get("structure_quality_gate_bands") or {}
        quantile_bits = []
        for key in ("min", "p25", "p50", "p75", "max"):
            if structure_dist.get(key) is not None:
                quantile_bits.append(f"{key}:{structure_dist.get(key)}")
        band_bits = []
        if gate_bands:
            band_bits = [
                f"block:{gate_bands.get('block_lt_0.15', 0)}",
                f"caution:{gate_bands.get('caution_0.15_to_0.35', 0)}",
                f"allow:{gate_bands.get('allow_ge_0.35', 0)}",
            ]
        quantile_text = f"|structure_q[{','.join(quantile_bits)}]" if quantile_bits else ""
        band_text = f"|structure_bands[{','.join(band_bits)}]" if band_bits else ""
        target_counts_text = f"|targets[{_fmt_counts(summary.get('target_counts') or {})}]"
        pnl_sign_text = f"|pnl_signs[{_fmt_counts(summary.get('pnl_sign_counts') or {})}]"
        quality_sign_text = f"|quality_signs[{_fmt_counts(summary.get('quality_sign_counts') or {})}]"
        true_negative_rows = summary.get("canonical_true_negative_rows")
        true_negative_share = summary.get("canonical_true_negative_share")
        true_negative_text = ""
        if true_negative_rows is not None:
            true_negative_text = f"|true_negative_rows={true_negative_rows}"
            if true_negative_share is not None:
                true_negative_text += f"@{true_negative_share}"
        return (
            f",{prefix}=final[{_fmt_counts(summary.get('final_gate_counts') or {})}]"
            f"|reason[{_fmt_counts(summary.get('final_reason_counts') or {})}]"
            f"|base[{_fmt_counts(summary.get('base_gate_counts') or {})}]"
            f"|avg_structure={summary.get('avg_structure_quality')}"
            f"{quantile_text}{band_text}{target_counts_text}{pnl_sign_text}{quality_sign_text}{true_negative_text}"
            f"|avg_bias200={summary.get('avg_bias200')}"
            f"|missing_rows={summary.get('missing_input_rows')}"
        )

    def _format_worst_spillover_pocket(spillover):
        pocket = spillover.get("worst_extra_regime_gate") or {}
        if not pocket.get("regime_gate"):
            return ""
        contrast_text = _format_feature_contrast(
            spillover.get("worst_extra_regime_gate_feature_contrast") or {},
            "spillover_feature_shift",
        )
        snapshot_text = _format_feature_snapshot(
            spillover.get("worst_extra_regime_gate_feature_snapshot") or {},
            "spillover_gate_inputs",
        )
        gate_path_text = _format_gate_path_summary(
            spillover.get("worst_extra_regime_gate_path_summary") or {},
            "spillover_gate_path",
        )
        ref_gate_path_text = _format_gate_path_summary(
            spillover.get("exact_live_gate_path_summary") or {},
            "exact_gate_path",
        )
        return (
            f",spillover_worst={pocket.get('regime_gate')}"
            f"(rows={pocket.get('rows')},wr={pocket.get('win_rate')},q={pocket.get('avg_quality')}"
            f",pnl={pocket.get('avg_pnl')},dd={pocket.get('avg_drawdown_penalty')}"
            f",tuw={pocket.get('avg_time_underwater')})"
            f"{contrast_text}{snapshot_text}{gate_path_text}{ref_gate_path_text}"
        )

    scope_bits = []
    for scope_name in (
        "regime_label+regime_gate+entry_quality_label",
        "regime_gate+entry_quality_label",
        "regime_label+entry_quality_label",
        "entry_quality_label",
    ):
        scope_info = scope_diags.get(scope_name) or {}
        if not scope_info:
            continue
        recent_regimes = _format_recent_regime_counts(scope_info.get("recent500_regime_counts") or {})
        recent_gates = _format_recent_regime_counts(scope_info.get("recent500_gate_counts") or {})
        recent_regime_gates = _format_recent_regime_counts(scope_info.get("recent500_regime_gate_counts") or {})
        dominant = scope_info.get("recent500_dominant_regime") or {}
        dominant_gate = scope_info.get("recent500_dominant_gate") or {}
        dominant_regime_gate = scope_info.get("recent500_dominant_regime_gate") or {}
        dominant_text = ""
        if dominant.get("regime"):
            dominant_text = f",recent500_dominant={dominant.get('regime')}@{dominant.get('share')}"
        dominant_gate_text = ""
        if dominant_gate.get("gate"):
            dominant_gate_text = f",recent500_gate_dominant={dominant_gate.get('gate')}@{dominant_gate.get('share')}"
        dominant_regime_gate_text = ""
        if dominant_regime_gate.get("regime_gate"):
            dominant_regime_gate_text = (
                f",recent500_regime_gate_dominant={dominant_regime_gate.get('regime_gate')}@{dominant_regime_gate.get('share')}"
            )
        recent_regime_text = f",recent500_regimes={recent_regimes}" if recent_regimes else ""
        recent_gate_text = f",recent500_gates={recent_gates}" if recent_gates else ""
        recent_regime_gate_text = f",recent500_regime_gates={recent_regime_gates}" if recent_regime_gates else ""
        spillover = scope_info.get("spillover_vs_exact_live_lane") or {}
        spillover_text = ""
        if spillover:
            spillover_gates = _format_recent_regime_counts(spillover.get("extra_gate_counts") or {})
            spillover_regime_gates = _format_recent_regime_counts(spillover.get("extra_regime_gate_counts") or {})
            spillover_dom_gate = spillover.get("extra_dominant_gate") or {}
            spillover_dom_regime_gate = spillover.get("extra_dominant_regime_gate") or {}
            spillover_dom_gate_text = ""
            if spillover_dom_gate.get("gate"):
                spillover_dom_gate_text = f",spillover_gate_dominant={spillover_dom_gate.get('gate')}@{spillover_dom_gate.get('share')}"
            spillover_dom_regime_gate_text = ""
            if spillover_dom_regime_gate.get("regime_gate"):
                spillover_dom_regime_gate_text = (
                    f",spillover_regime_gate_dominant={spillover_dom_regime_gate.get('regime_gate')}@{spillover_dom_regime_gate.get('share')}"
                )
            spillover_gates_text = f",spillover_gates={spillover_gates}" if spillover_gates else ""
            spillover_regime_gates_text = f",spillover_regime_gates={spillover_regime_gates}" if spillover_regime_gates else ""
            spillover_text = (
                f",spillover_rows={spillover.get('extra_rows')}"
                f",spillover_share={spillover.get('extra_row_share')}"
                f",spillover_wr_delta={spillover.get('win_rate_delta_vs_exact')}"
                f",spillover_q_delta={spillover.get('avg_quality_delta_vs_exact')}"
                f",spillover_pnl_delta={spillover.get('avg_pnl_delta_vs_exact')}"
                f"{spillover_dom_gate_text}{spillover_dom_regime_gate_text}"
                f"{spillover_gates_text}{spillover_regime_gates_text}"
                f"{_format_worst_spillover_pocket(spillover)}"
            )
        scope_bits.append(
            f"{scope_name}:rows={scope_info.get('rows')}"
            f",wr={scope_info.get('win_rate')}"
            f",q={scope_info.get('avg_quality')}"
            f",dd={scope_info.get('avg_drawdown_penalty')}"
            f",tuw={scope_info.get('avg_time_underwater')}"
            f",alerts={scope_info.get('alerts')}"
            f"{dominant_text}{dominant_gate_text}{dominant_regime_gate_text}"
            f"{recent_regime_text}{recent_gate_text}{recent_regime_gate_text}"
            f"{spillover_text}"
        )
    scope_matrix_text = f", scope_matrix={'; '.join(scope_bits)}" if scope_bits else ""

    consensus = scope_diags.get("pathology_consensus") or {}
    shared_shifts = consensus.get("shared_top_shift_features") or []
    shared_shift_text = "/".join(
        f"{row.get('feature')}[x{row.get('scope_count')}]"
        for row in shared_shifts[:3]
        if row.get("feature")
    )
    worst_scope = consensus.get("worst_pathology_scope") or {}
    worst_scope_text = ""
    if worst_scope.get("scope"):
        worst_scope_regimes = _format_recent_regime_counts(worst_scope.get("recent500_regime_counts") or {})
        worst_scope_gates = _format_recent_regime_counts(worst_scope.get("recent500_gate_counts") or {})
        worst_scope_regime_gates = _format_recent_regime_counts(worst_scope.get("recent500_regime_gate_counts") or {})
        worst_scope_dominant = worst_scope.get("recent500_dominant_regime") or {}
        worst_scope_dominant_gate = worst_scope.get("recent500_dominant_gate") or {}
        worst_scope_dominant_regime_gate = worst_scope.get("recent500_dominant_regime_gate") or {}
        dominant_suffix = ""
        if worst_scope_dominant.get("regime"):
            dominant_suffix = f",recent500_dominant={worst_scope_dominant.get('regime')}@{worst_scope_dominant.get('share')}"
        dominant_gate_suffix = ""
        if worst_scope_dominant_gate.get("gate"):
            dominant_gate_suffix = f",recent500_gate_dominant={worst_scope_dominant_gate.get('gate')}@{worst_scope_dominant_gate.get('share')}"
        dominant_regime_gate_suffix = ""
        if worst_scope_dominant_regime_gate.get("regime_gate"):
            dominant_regime_gate_suffix = (
                f",recent500_regime_gate_dominant={worst_scope_dominant_regime_gate.get('regime_gate')}@{worst_scope_dominant_regime_gate.get('share')}"
            )
        regime_suffix = f",recent500_regimes={worst_scope_regimes}" if worst_scope_regimes else ""
        gate_suffix = f",recent500_gates={worst_scope_gates}" if worst_scope_gates else ""
        regime_gate_suffix = f",recent500_regime_gates={worst_scope_regime_gates}" if worst_scope_regime_gates else ""
        spillover = worst_scope.get("spillover_vs_exact_live_lane") or {}
        spillover_text = ""
        if spillover:
            spillover_gates = _format_recent_regime_counts(spillover.get("extra_gate_counts") or {})
            spillover_regime_gates = _format_recent_regime_counts(spillover.get("extra_regime_gate_counts") or {})
            spillover_dom_gate = spillover.get("extra_dominant_gate") or {}
            spillover_dom_regime_gate = spillover.get("extra_dominant_regime_gate") or {}
            spillover_dom_gate_text = ""
            if spillover_dom_gate.get("gate"):
                spillover_dom_gate_text = f",spillover_gate_dominant={spillover_dom_gate.get('gate')}@{spillover_dom_gate.get('share')}"
            spillover_dom_regime_gate_text = ""
            if spillover_dom_regime_gate.get("regime_gate"):
                spillover_dom_regime_gate_text = (
                    f",spillover_regime_gate_dominant={spillover_dom_regime_gate.get('regime_gate')}@{spillover_dom_regime_gate.get('share')}"
                )
            spillover_gates_text = f",spillover_gates={spillover_gates}" if spillover_gates else ""
            spillover_regime_gates_text = f",spillover_regime_gates={spillover_regime_gates}" if spillover_regime_gates else ""
            spillover_text = (
                f",spillover_rows={spillover.get('extra_rows')}"
                f",spillover_share={spillover.get('extra_row_share')}"
                f",spillover_wr_delta={spillover.get('win_rate_delta_vs_exact')}"
                f",spillover_q_delta={spillover.get('avg_quality_delta_vs_exact')}"
                f",spillover_pnl_delta={spillover.get('avg_pnl_delta_vs_exact')}"
                f"{spillover_dom_gate_text}{spillover_dom_regime_gate_text}"
                f"{spillover_gates_text}{spillover_regime_gates_text}"
                f"{_format_worst_spillover_pocket(spillover)}"
            )
        worst_scope_text = (
            f", worst_scope={worst_scope.get('scope')}"
            f"(wr={worst_scope.get('win_rate')},q={worst_scope.get('avg_quality')},rows={worst_scope.get('rows')}"
            f",dd={worst_scope.get('avg_drawdown_penalty')},tuw={worst_scope.get('avg_time_underwater')}"
            f"{dominant_suffix}{dominant_gate_suffix}{dominant_regime_gate_suffix}"
            f"{regime_suffix}{gate_suffix}{regime_gate_suffix}{spillover_text})"
        )
    exact_gate_path_summary = (
        (exact_scope_info.get("spillover_vs_exact_live_lane") or {}).get("exact_live_gate_path_summary")
        or {}
    )
    if not exact_gate_path_summary:
        for candidate_scope in scope_diags.values():
            if not isinstance(candidate_scope, dict):
                continue
            candidate_summary = ((candidate_scope.get("spillover_vs_exact_live_lane") or {}).get("exact_live_gate_path_summary")) or {}
            if candidate_summary:
                exact_gate_path_summary = candidate_summary
                break
    exact_true_negative_rows = exact_gate_path_summary.get("canonical_true_negative_rows")
    exact_true_negative_share = exact_gate_path_summary.get("canonical_true_negative_share")
    exact_target_counts = exact_gate_path_summary.get("target_counts") or {}
    exact_scope_text = ""
    if exact_scope_info:
        exact_scope_bits = [
            f"rows={exact_scope_info.get('rows')}",
            f"wr={exact_scope_info.get('win_rate')}",
            f"q={exact_scope_info.get('avg_quality')}",
            f"dd={exact_scope_info.get('avg_drawdown_penalty')}",
            f"tuw={exact_scope_info.get('avg_time_underwater')}",
        ]
        if exact_scope_info.get("recent500_dominant_regime_gate"):
            dom = exact_scope_info.get("recent500_dominant_regime_gate") or {}
            exact_scope_bits.append(f"recent500_dom={dom.get('regime_gate')}@{dom.get('share')}")
        if exact_target_counts:
            exact_scope_bits.append(
                "targets=" + "/".join(f"{k}:{v}" for k, v in sorted(exact_target_counts.items()))
            )
        if exact_true_negative_rows is not None:
            exact_scope_bits.append(f"true_negative_rows={exact_true_negative_rows}@{exact_true_negative_share}")
        final_gate_counts = exact_gate_path_summary.get("final_gate_counts") or {}
        if final_gate_counts:
            exact_scope_bits.append(
                "final_gate=" + "/".join(f"{k}:{v}" for k, v in sorted(final_gate_counts.items()))
            )
        exact_scope_text = ", exact_live_lane=" + "(" + ",".join(exact_scope_bits) + ")"
        exact_rows = exact_scope_info.get("rows")
        exact_win_rate = exact_scope_info.get("win_rate")
        exact_quality = exact_scope_info.get("avg_quality")
        exact_toxic = (
            isinstance(exact_rows, (int, float)) and exact_rows >= 20
            and (
                (isinstance(exact_true_negative_share, (int, float)) and exact_true_negative_share >= 0.60)
                or (isinstance(exact_win_rate, (int, float)) and exact_win_rate <= 0.35)
                or (isinstance(exact_quality, (int, float)) and exact_quality < 0.0)
            )
        )
        if exact_toxic:
            exact_scope_text += ", exact_lane_status=toxic_allow_lane"

    shared_scope_text = f", shared_shifts={shared_shift_text}" if shared_shift_text else ""
    return (
        f"live_scope={scope}, regime={regime}/{gate}, label={label}, sample_size={sample_size}, "
        f"window={window}, alerts={alerts}, expected_win_rate={win_rate}, expected_pnl={pnl}, "
        f"expected_quality={quality}, layers={layers_raw}→{layers}, top_shifts={top_shift_text or 'n/a'}"
        f"{exact_scope_text}{scope_matrix_text}{shared_scope_text}{worst_scope_text}"
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
    recent_drift = load_recent_drift_report()
    drift_summary = summarize_recent_drift(recent_drift)
    live_predict_probe = load_live_predict_probe()
    leaderboard_candidate_probe = load_leaderboard_candidate_probe()
    q35_scaling_audit = load_q35_scaling_audit()
    live_predict_summary = summarize_live_predict_probe(live_predict_probe)
    drift_primary, drift_primary_summary = _recent_drift_window_payload(recent_drift, "primary_window")
    drift_blocking, drift_blocking_summary = _blocking_recent_drift_window(recent_drift)
    pathology_drift = drift_blocking or drift_primary
    pathology_drift_summary = drift_blocking_summary or drift_primary_summary
    pathology_drift_summary_text = summarize_recent_drift_window(pathology_drift)

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
    sync_current_state_governance_issues(
        tracker,
        leaderboard_candidate_probe,
        live_predict_probe,
        metrics,
        q35_scaling_audit,
    )

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
        canonical_horizon = db_stats.get("canonical_horizon_minutes")
        streak_title = (
            f"連續 {db_stats['losing_streak']} 筆 {canonical_horizon}m simulated_pyramid_win=0"
            if canonical_horizon
            else f"連續 {db_stats['losing_streak']} 筆 simulated_pyramid_win=0"
        )
        upsert_issue(
            tracker,
            "P0",
            "#H_AUTO_STREAK",
            streak_title,
            "檢查 recent canonical labels / regime breakdown / circuit breaker；必要時升級為 distribution-aware drift 調查",
            summary={
                "canonical_horizon_minutes": canonical_horizon,
                "losing_streak": db_stats["losing_streak"],
                "all_horizon_losing_streak": db_stats.get("all_horizon_losing_streak"),
            },
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
    pathology_interpretation = pathology_drift_summary.get("drift_interpretation")
    pathology_alerts = pathology_drift.get("alerts") or []
    pathology_window = pathology_drift.get("window")
    pathology_quality = pathology_drift_summary.get("quality_metrics") or {}
    pathology_avg_pnl = pathology_quality.get("avg_simulated_pnl")
    pathology_avg_quality = pathology_quality.get("avg_simulated_quality")
    pathology_spot_long_win = pathology_quality.get("spot_long_win_rate")
    drift_is_negative_pathology = (
        pathology_interpretation in {"distribution_pathology", "regime_concentration"}
        and any(alert in pathology_alerts for alert in ("constant_target", "label_imbalance", "regime_concentration", "regime_shift"))
        and (
            (isinstance(pathology_avg_pnl, (int, float)) and pathology_avg_pnl <= 0.0)
            or (isinstance(pathology_avg_quality, (int, float)) and pathology_avg_quality <= 0.0)
            or (isinstance(pathology_spot_long_win, (int, float)) and pathology_spot_long_win <= 0.20)
        )
    )
    if drift_is_negative_pathology:
        drift_feature_diag = pathology_drift_summary.get("feature_diagnostics") or {}
        drift_target_path = pathology_drift_summary.get("target_path_diagnostics") or {}
        drift_reference_comparison = pathology_drift_summary.get("reference_window_comparison") or {}
        tail_streak = drift_target_path.get("tail_target_streak") or {}
        top_shift_source = (
            pathology_drift_summary.get("top_mean_shift_features")
            or drift_reference_comparison.get("top_mean_shift_features")
            or []
        )
        top_shift_features = [
            item.get("feature") if isinstance(item, dict) else item
            for item in top_shift_source
            if (item.get("feature") if isinstance(item, dict) else item)
        ]
        new_compressed = pathology_drift_summary.get("new_compressed_features")
        if not isinstance(new_compressed, list) or not new_compressed:
            new_compressed = drift_reference_comparison.get("new_unexpected_compressed_features") or []
        if not isinstance(new_compressed, list) or not new_compressed:
            new_compressed = drift_feature_diag.get("new_unexpected_compressed_features") or []
        pathology_summary = {
            "window": pathology_window,
            "interpretation": pathology_interpretation,
            "win_rate": pathology_drift_summary.get("win_rate"),
            "dominant_regime": pathology_drift_summary.get("dominant_regime"),
            "dominant_regime_share": pathology_drift_summary.get("dominant_regime_share"),
            "avg_pnl": pathology_avg_pnl,
            "avg_quality": pathology_avg_quality,
            "avg_drawdown_penalty": pathology_quality.get("avg_drawdown_penalty"),
            "alerts": pathology_alerts,
            "top_shift_features": top_shift_features[:3],
            "new_compressed_feature": new_compressed[0] if new_compressed else None,
            "tail_streak": (
                f"{tail_streak.get('count')}x{tail_streak.get('target')}"
                if tail_streak.get("count") is not None and tail_streak.get("target") is not None
                else None
            ),
        }
        upsert_issue(
            tracker,
            "P0",
            "#H_AUTO_RECENT_PATHOLOGY",
            f"recent canonical window {pathology_window} rows = {pathology_interpretation or 'distribution_pathology'}",
            "直接對 recent canonical rows 做 feature variance / distinct-count / target-path drill-down；"
            "維持 decision-quality guardrails，並檢查 calibration scope 是否仍被病態 slice 稀釋。"
            f" {pathology_drift_summary_text}",
            summary=pathology_summary,
        )
    else:
        tracker.resolve("#H_AUTO_RECENT_PATHOLOGY")

    # Rule 7: live predictor runtime shows same-scope or narrowed-lane decision-quality pathology
    live_recent_pathology = bool(live_predict_probe.get("decision_quality_recent_pathology_applied"))
    live_expected_win = live_predict_probe.get("expected_win_rate")
    live_expected_pnl = live_predict_probe.get("expected_pyramid_pnl")
    live_expected_quality = live_predict_probe.get("expected_pyramid_quality")
    live_layers = live_predict_probe.get("allowed_layers")
    live_label = live_predict_probe.get("decision_quality_label")
    live_scope_diags = live_predict_probe.get("decision_quality_scope_diagnostics") or {}
    live_consensus = live_scope_diags.get("pathology_consensus") or {}
    worst_scope = live_consensus.get("worst_pathology_scope") or {}
    worst_scope_win = worst_scope.get("win_rate")
    worst_scope_quality = worst_scope.get("avg_quality")
    worst_scope_rows = worst_scope.get("rows")
    narrowed_scope_pathology = bool(worst_scope.get("scope")) and (
        (isinstance(worst_scope_win, (int, float)) and worst_scope_win <= 0.20)
        or (isinstance(worst_scope_quality, (int, float)) and worst_scope_quality < 0.0)
    ) and (
        not isinstance(worst_scope_rows, (int, float)) or worst_scope_rows >= 100
    )
    if (live_recent_pathology or narrowed_scope_pathology) and (
        (isinstance(live_expected_win, (int, float)) and live_expected_win <= 0.20)
        or (isinstance(live_expected_pnl, (int, float)) and live_expected_pnl < 0.0)
        or (isinstance(live_expected_quality, (int, float)) and live_expected_quality < 0.0)
        or live_layers == 0
        or live_label == "D"
        or narrowed_scope_pathology
    ):
        upsert_issue(
            tracker,
            "P1",
            "#H_AUTO_LIVE_DQ_PATHOLOGY",
            "live predictor decision-quality contract is runtime-blocked by recent pathology, a toxic exact live lane, or a severe narrowed pathology lane",
            "把 hb_predict_probe 納入每輪 heartbeat 驗證，對 exact live lane、當前 calibration scope 與 worst narrowed scope 做 root-cause drill-down；"
            "優先檢查 exact lane 是否仍是 ALLOW 但 canonical true-negative share 已偏高，並交叉比對 recent same-scope / narrowed-scope 4H shifts、scope selection、與 execution guardrail 是否只是正確地把壞 pocket 擋下。"
            f" {live_predict_summary}",
            summary={
                "live_scope": live_predict_probe.get("decision_quality_calibration_scope") or "unknown",
                "deployment_blocker": live_predict_probe.get("deployment_blocker"),
                "window": drift_window,
                "alerts": drift_alerts,
                "allowed_layers": live_layers,
            },
        )
    else:
        tracker.resolve("#H_AUTO_LIVE_DQ_PATHOLOGY")

    # Rule 8: TW-IC >> Global IC (regime-dependence indicator)
    if ic_stats["tw_pass"] > ic_stats["global_pass"] + 2:
        upsert_issue(
            tracker,
            "P1",
            "#H_AUTO_REGIME_DRIFT",
            f"TW-IC {ic_stats['tw_pass']} vs Global IC {ic_stats['global_pass']} — 信號強依賴近期資料",
            "市場 regime 可能已變化; 考慮 regime-gated feature weighting",
            summary={
                "global_pass": ic_stats["global_pass"],
                "tw_pass": ic_stats["tw_pass"],
                "total_features": ic_stats["total_features"],
            },
        )
    else:
        tracker.resolve("#H_AUTO_REGIME_DRIFT")

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
                print(f"    → {issue_action_text(item)}")

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
    print(f"📊 Live probe：{live_predict_summary}")
    print(f"📊 模型：Train={train:.1%}, CV={cv:.1%}" if train else "📊 模型：目前無資料")
    print(f"\n💾 已儲存至：{Path(__file__).parent.parent / 'issues.json'}")


if __name__ == "__main__":
    main()
