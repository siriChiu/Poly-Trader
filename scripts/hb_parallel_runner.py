#!/usr/bin/env python3
"""Heartbeat Parallel Runner v8 — runs diagnostics concurrently and saves summary.

Usage:
  python scripts/hb_parallel_runner.py --hb N [--no-train] [--no-dw]
  python scripts/hb_parallel_runner.py --fast [--hb LABEL]
  python scripts/hb_parallel_runner.py --fast --fast-refresh-candidates [--hb LABEL]
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = '/home/kazuha/Poly-Trader'
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from feature_engine.feature_history_policy import (
    build_source_blocker_summary,
    compute_sqlite_feature_coverage,
)
from scripts.hb_collect import summarize_label_horizons
from scripts.issues import IssueTracker, normalize_verify_steps

PYTHON = os.path.join(PROJECT_ROOT, 'venv', 'bin', 'python')
DB_PATH = os.path.join(PROJECT_ROOT, 'poly_trader.db')
_CURRENT_HEARTBEAT_RUN_LABEL: str | None = None
_CURRENT_HEARTBEAT_FAST_MODE = False
FAST_SERIAL_TIMEOUTS = {
    "recent_drift_report": 30,
    "hb_q35_scaling_audit": 20,
    "hb_predict_probe": 20,
    "live_decision_quality_drilldown": 20,
    "hb_circuit_breaker_audit": 20,
    "feature_group_ablation": 45,
    "bull_4h_pocket_ablation": 20,
    "hb_leaderboard_candidate_probe": 20,
    "hb_q15_support_audit": 20,
    "hb_q15_bucket_root_cause": 20,
    "hb_q15_boundary_replay": 20,
}
FULL_SERIAL_TIMEOUTS = {
    # Candidate-evaluation lanes can become silent for many minutes when the
    # training set grows. Full heartbeat runs still need to finish inside the
    # 10-minute cron/tool budget, so fail closed and reuse the latest bounded
    # governance artifact instead of letting one lane consume the whole run.
    "feature_group_ablation": 60,
    "bull_4h_pocket_ablation": 45,
    "hb_leaderboard_candidate_probe": 45,
}
FAST_PARALLEL_TASK_TIMEOUTS = {
    "full_ic": 90,
    "regime_ic": 90,
}
FULL_PARALLEL_TASK_TIMEOUTS = {
    "full_ic": 120,
    "regime_ic": 120,
    "dynamic_window": 180,
    # Global train + rolling CV is the deployable artifact refresh path and now
    # skips optional regime grid search; current dataset still needs >180s on
    # slower cron lanes, so keep an explicit budget that remains within the
    # 10-minute full-heartbeat envelope.
    "train": 300,
    "tests": 180,
}
COLLECT_TIMEOUT_SECONDS = 180
FAST_CACHE_REUSE_MAX_LABEL_DELTA = 12
FAST_CACHE_REUSE_MAX_LABEL_TIME_DRIFT_SECONDS = 6 * 3600
FAST_HEARTBEAT_CRON_BUDGET_SECONDS = 240
CANDIDATE_REFRESH_LANES = (
    "feature_group_ablation",
    "bull_4h_pocket_ablation",
    "hb_leaderboard_candidate_probe",
)
CANDIDATE_ARTIFACT_STALE_FALLBACK_ISSUE_ID = "P1_candidate_governance_artifact_stale_fallback"

TASKS = [
    {"name": "full_ic", "label": "🔍 Full IC", "cmd": [PYTHON, "scripts/full_ic.py"]},
    {"name": "regime_ic", "label": "🏛️ Regime IC", "cmd": [PYTHON, "scripts/regime_aware_ic.py"]},
    {"name": "dynamic_window", "label": "📏 Dynamic Window", "cmd": [PYTHON, "scripts/dynamic_window_train.py"]},
    # Cron heartbeat must refresh the deployable global model/metrics without letting
    # optional per-regime grid search consume the 10-minute heartbeat budget.
    {"name": "train", "label": "🔨 Model Train", "cmd": [PYTHON, "model/train.py", "--skip-regime-models"]},
    {"name": "tests", "label": "🧪 Comprehensive Tests", "cmd": [PYTHON, "tests/comprehensive_test.py"]},
]
COLLECT_CMD = [PYTHON, "scripts/hb_collect.py"]
AUTO_PROPOSE_CMD = [PYTHON, "scripts/auto_propose_fixes.py"]
DRIFT_REPORT_CMD = [PYTHON, "scripts/recent_drift_report.py"]
PREDICT_PROBE_CMD = [PYTHON, "scripts/hb_predict_probe.py"]
LIVE_DQ_DRILLDOWN_CMD = [PYTHON, "scripts/live_decision_quality_drilldown.py"]
Q35_SCALING_AUDIT_CMD = [PYTHON, "scripts/hb_q35_scaling_audit.py"]
Q15_SUPPORT_AUDIT_CMD = [PYTHON, "scripts/hb_q15_support_audit.py"]
Q15_BUCKET_ROOT_CAUSE_CMD = [PYTHON, "scripts/hb_q15_bucket_root_cause.py"]
Q15_BOUNDARY_REPLAY_CMD = [PYTHON, "scripts/hb_q15_boundary_replay.py"]
CIRCUIT_BREAKER_AUDIT_CMD = [PYTHON, "scripts/hb_circuit_breaker_audit.py"]
FEATURE_ABLATION_CMD = [PYTHON, "scripts/feature_group_ablation.py", "--bounded-refresh"]
BULL_4H_POCKET_ABLATION_CMD = [PYTHON, "scripts/bull_4h_pocket_ablation.py"]
BULL_4H_POCKET_ABLATION_REFRESH_CMD = [PYTHON, "scripts/bull_4h_pocket_ablation.py", "--refresh-live-context"]
LEADERBOARD_CANDIDATE_PROBE_CMD = [PYTHON, "scripts/hb_leaderboard_candidate_probe.py"]


def _safe_parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        try:
            parsed = datetime.fromisoformat(normalized.replace(" ", "T"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _file_mtime(path: str | Path | None) -> datetime | None:
    if not path:
        return None
    try:
        return datetime.fromtimestamp(Path(path).stat().st_mtime, tz=timezone.utc)
    except Exception:
        return None


def collect_current_state_docs_sync_status() -> Dict[str, Any]:
    root = Path(PROJECT_ROOT)
    doc_paths = {
        "ISSUES.md": root / "ISSUES.md",
        "ROADMAP.md": root / "ROADMAP.md",
    }
    reference_paths = [
        ("issues.json", root / "issues.json"),
        ("data/live_predict_probe.json", root / "data" / "live_predict_probe.json"),
        ("data/live_decision_quality_drilldown.json", root / "data" / "live_decision_quality_drilldown.json"),
    ]

    reference_mtimes = {
        label: _file_mtime(path)
        for label, path in reference_paths
    }
    available_reference_mtimes = [mtime for mtime in reference_mtimes.values() if mtime is not None]
    latest_reference_mtime = max(available_reference_mtimes) if available_reference_mtimes else None

    docs: Dict[str, Any] = {}
    stale_docs: list[str] = []
    for label, path in doc_paths.items():
        mtime = _file_mtime(path)
        docs[label] = {
            "path": str(path),
            "mtime": mtime.isoformat() if mtime is not None else None,
            "exists": mtime is not None,
        }
        if latest_reference_mtime is not None and (mtime is None or mtime < latest_reference_mtime):
            stale_docs.append(label)

    return {
        "ok": not stale_docs,
        "stale_docs": stale_docs,
        "reference_artifacts": [label for label, mtime in reference_mtimes.items() if mtime is not None],
        "latest_reference_mtime": latest_reference_mtime.isoformat() if latest_reference_mtime is not None else None,
        "references": {
            label: {
                "path": str(path),
                "mtime": reference_mtimes[label].isoformat() if reference_mtimes[label] is not None else None,
                "exists": reference_mtimes[label] is not None,
            }
            for label, path in reference_paths
        },
        "docs": docs,
    }


def collect_historical_coverage_confirmation(
    db_path: str | Path | None = None,
    *,
    symbol: str = "BTCUSDT",
    lookback_days: int = 730,
) -> Dict[str, Any]:
    target_db = str(db_path or DB_PATH)
    summary: Dict[str, Any] = {
        "symbol": symbol,
        "db_path": target_db,
        "lookback_days": int(lookback_days),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tables": {},
    }

    now = datetime.now(timezone.utc)
    cutoff = now.timestamp() - max(int(lookback_days), 1) * 86400
    cutoff_dt = datetime.fromtimestamp(cutoff, tz=timezone.utc)
    table_specs = {
        "raw_market_data": "SELECT MIN(timestamp), MAX(timestamp), COUNT(*) FROM raw_market_data WHERE symbol = ?",
        "features_normalized": "SELECT MIN(timestamp), MAX(timestamp), COUNT(*) FROM features_normalized WHERE symbol = ?",
        "labels": "SELECT MIN(timestamp), MAX(timestamp), COUNT(*) FROM labels WHERE symbol = ?",
    }

    try:
        conn = sqlite3.connect(target_db)
    except Exception as exc:
        summary["error"] = str(exc)
        summary["ok"] = False
        summary["covers_two_years"] = False
        return summary

    try:
        covers_two_years = True
        for table_name, query in table_specs.items():
            row = conn.execute(query, (symbol,)).fetchone() or (None, None, 0)
            start_dt = _safe_parse_datetime(row[0])
            end_dt = _safe_parse_datetime(row[1])
            count = int(row[2] or 0)
            span_days = None
            if start_dt and end_dt:
                span_days = round((end_dt - start_dt).total_seconds() / 86400.0, 2)
            older_than_cutoff = bool(start_dt and start_dt <= cutoff_dt)
            summary["tables"][table_name] = {
                "start": start_dt.isoformat() if start_dt else None,
                "end": end_dt.isoformat() if end_dt else None,
                "count": count,
                "span_days": span_days,
                "older_than_two_year_cutoff": older_than_cutoff,
            }
            if not older_than_cutoff:
                covers_two_years = False
        summary["cutoff_timestamp"] = cutoff_dt.isoformat()
        summary["covers_two_years"] = covers_two_years
        summary["ok"] = True
        return summary
    finally:
        conn.close()


def _format_local_timestamp_for_docs(value: datetime | None = None) -> str:
    current = value or datetime.now().astimezone()
    return current.strftime("%Y-%m-%d %H:%M:%S %Z")


def _format_pct_for_docs(value: Any, digits: int = 1) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "—"
    return f"{numeric * 100:.{digits}f}%"


def _format_number_for_docs(value: Any, digits: int = 4, signed: bool = False) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "—"
    prefix = "+" if signed and numeric > 0 else ""
    return f"{prefix}{numeric:.{digits}f}"


def _current_support_bucket(
    live_predictor_diagnostics: Dict[str, Any] | None,
    q15_support_audit: Dict[str, Any] | None,
) -> str:
    live_predictor_diagnostics = live_predictor_diagnostics or {}
    q15_support_audit = q15_support_audit or {}

    bucket = live_predictor_diagnostics.get("current_live_structure_bucket")
    if bucket:
        return str(bucket)

    current_live = q15_support_audit.get("current_live") or {}
    if isinstance(current_live, dict):
        bucket = current_live.get("current_live_structure_bucket") or current_live.get("structure_bucket")
        if bucket:
            return str(bucket)

    support_route = q15_support_audit.get("support_route") or {}
    support_progress = support_route.get("support_progress") or {}
    history = support_progress.get("history") or []
    if history and isinstance(history[0], dict):
        bucket = history[0].get("live_current_structure_bucket")
        if bucket:
            return str(bucket)

    return ""


def _q15_support_audit_bucket(q15_support_audit: Dict[str, Any] | None) -> str:
    q15_support_audit = q15_support_audit or {}

    current_live = q15_support_audit.get("current_live") or {}
    if isinstance(current_live, dict):
        bucket = current_live.get("current_live_structure_bucket") or current_live.get("structure_bucket")
        if bucket:
            return str(bucket)

    support_route = q15_support_audit.get("support_route") or {}
    support_progress = support_route.get("support_progress") or {}
    history = support_progress.get("history") or []
    for row in history:
        if not isinstance(row, dict):
            continue
        bucket = row.get("live_current_structure_bucket")
        if bucket:
            return str(bucket)

    return ""


def _support_truth_context(
    live_predictor_diagnostics: Dict[str, Any] | None,
    q15_support_audit: Dict[str, Any] | None,
) -> Dict[str, Any]:
    live_predictor_diagnostics = live_predictor_diagnostics or {}
    q15_support_audit = q15_support_audit or {}

    current_bucket = _current_support_bucket(live_predictor_diagnostics, q15_support_audit)
    context: Dict[str, Any] = {
        "current_bucket": current_bucket,
        "current_rows": live_predictor_diagnostics.get("current_live_structure_bucket_rows"),
        "minimum_rows": live_predictor_diagnostics.get("minimum_support_rows"),
        "gap_to_minimum": live_predictor_diagnostics.get("current_live_structure_bucket_gap_to_minimum"),
        "support_route_verdict": live_predictor_diagnostics.get("support_route_verdict"),
        "support_governance_route": live_predictor_diagnostics.get("support_governance_route"),
        "source": "live_predictor",
    }

    audit_bucket = _q15_support_audit_bucket(q15_support_audit)
    use_q15_support_audit = "q15" in str(current_bucket or "") and (
        not audit_bucket or audit_bucket == current_bucket
    )
    if use_q15_support_audit:
        support_route = q15_support_audit.get("support_route") or {}
        support_progress = support_route.get("support_progress") or {}
        if support_progress.get("current_rows") is not None:
            context["current_rows"] = support_progress.get("current_rows")
        if support_progress.get("minimum_support_rows") is not None:
            context["minimum_rows"] = support_progress.get("minimum_support_rows")
        if support_progress.get("gap_to_minimum") is not None:
            context["gap_to_minimum"] = support_progress.get("gap_to_minimum")
        if support_route.get("verdict") is not None:
            context["support_route_verdict"] = support_route.get("verdict")
        if support_route.get("support_governance_route") is not None:
            context["support_governance_route"] = support_route.get("support_governance_route")
        if support_progress.get("status") is not None:
            context["support_progress_status"] = support_progress.get("status")
        if support_progress.get("regression_basis") is not None:
            context["support_progress_regression_basis"] = support_progress.get("regression_basis")
        if support_progress.get("legacy_supported_reference") is not None:
            context["legacy_supported_reference"] = support_progress.get("legacy_supported_reference")
        context["source"] = "q15_support_audit"

    if context.get("gap_to_minimum") in (None, ""):
        try:
            current_rows = int(context.get("current_rows"))
            minimum_rows = int(context.get("minimum_rows"))
        except (TypeError, ValueError):
            pass
        else:
            context["gap_to_minimum"] = max(minimum_rows - current_rows, 0)

    return context


def _support_scope_label(current_bucket: str | None) -> str:
    bucket = str(current_bucket or "").strip()
    if "q15" in bucket:
        return "q15 current-live bucket"
    return "current live bucket"


def _support_truth_label(current_bucket: str | None) -> str:
    bucket = str(current_bucket or "").strip()
    if "q15" in bucket:
        return "current live q15 truth"
    return "current live bucket support truth"


def _support_goal_success_line(
    support_scope_label: str,
    support_route_verdict: Any,
    support_current_rows: Any,
    support_minimum_rows: Any,
    deployment_blocker: str,
) -> str:
    verdict = str(support_route_verdict or "—")
    try:
        current_rows = int(support_current_rows)
        minimum_rows = int(support_minimum_rows)
    except (TypeError, ValueError):
        current_rows = None
        minimum_rows = None

    support_met = verdict == "exact_bucket_supported"
    if not support_met and current_rows is not None and minimum_rows is not None:
        support_met = current_rows >= minimum_rows

    if support_met:
        blocker = deployment_blocker or "latest runtime blocker"
        return (
            f"- probe / drilldown / `/api/status` / `/execution/status` / `/lab` / docs 全都承認 "
            f"{support_scope_label} exact support 已達 minimum rows；deployment blocker 仍以 `{blocker}` 為準，"
            "不可把 support closure 誤讀成 deployment closure；recommended patch 若存在也只能作治理 / 訓練參考。"
        )

    return (
        f"- probe / drilldown / `/api/status` / `/execution/status` / `/lab` / docs 全都承認 "
        f"{support_scope_label} exact support 未達 minimum rows，recommended patch 只能作治理 / 訓練參考。"
    )


def _format_legacy_supported_reference(reference: Any) -> str:
    if not isinstance(reference, dict) or not reference:
        return "—"
    rows = reference.get("live_current_structure_bucket_rows")
    minimum = reference.get("minimum_support_rows")
    heartbeat = reference.get("heartbeat") or reference.get("timestamp") or "unknown"
    if rows is None and minimum is None:
        return str(heartbeat)
    return f"{rows if rows is not None else '—'}/{minimum if minimum is not None else '—'}@{heartbeat}"


def _support_progress_docs_line(support_context: Dict[str, Any] | None) -> str:
    support_context = support_context or {}
    status = support_context.get("support_progress_status")
    regression_basis = support_context.get("support_progress_regression_basis")
    legacy_ref = support_context.get("legacy_supported_reference")
    if status in (None, "") and regression_basis in (None, "") and not legacy_ref:
        return ""
    return (
        f"support progress：`status={status or '—'}` / "
        f"`regression_basis={regression_basis or '—'}` / "
        f"`legacy_supported_reference={_format_legacy_supported_reference(legacy_ref)}`"
    )


_PATCH_EMPTY_DOC_MARKERS = {"", "-", "—", "none", "null", "n/a", "na"}


def _normalize_patch_truth_value(value: Any) -> str:
    if value is None:
        return "—"
    text = str(value).strip()
    if not text:
        return "—"
    if text.lower() in _PATCH_EMPTY_DOC_MARKERS:
        return "—"
    return text


def _patch_truth_doc_context(
    patch_profile: Any,
    patch_status: Any,
    patch_reference_scope: Any,
) -> Dict[str, Any]:
    profile = _normalize_patch_truth_value(patch_profile)
    status = _normalize_patch_truth_value(patch_status)
    reference_scope = _normalize_patch_truth_value(patch_reference_scope)
    has_patch = any(item != "—" for item in (profile, status, reference_scope))
    reference_only = has_patch and status.startswith("reference_only_")
    patch_label = "reference-only patch" if reference_only else ("recommended patch" if has_patch else "")
    docs_line = f"`recommended_patch={profile}` / `status={status}` / `reference_scope={reference_scope}`"
    if not has_patch:
        docs_line += "（本輪無 active recommended patch）"
    return {
        "profile": profile,
        "status": status,
        "reference_scope": reference_scope,
        "has_patch": has_patch,
        "reference_only": reference_only,
        "patch_label": patch_label,
        "priority_focus_phrase": f"support / {patch_label}" if has_patch else "support truth / blocker truth",
        "goal_title_suffix": f"support + {patch_label} 真相" if has_patch else "support truth 與 deployment closure 邊界",
        "docs_line": docs_line,
    }


def _find_source_blocker(source_blockers: Dict[str, Any] | None, blocker_key: str) -> Dict[str, Any] | None:
    for blocker in (source_blockers or {}).get("blocked_features") or []:
        if isinstance(blocker, dict) and blocker.get("key") == blocker_key:
            return blocker
    return None


def _sync_live_issue_summaries(
    issues: list[Dict[str, Any]],
    source_blockers: Dict[str, Any] | None,
) -> bool:
    fin_blocker = _find_source_blocker(source_blockers, "fin_netflow")
    if not fin_blocker:
        return False

    updated = False
    fin_summary = {
        "feature": "fin_netflow",
        "quality_flag": fin_blocker.get("quality_flag"),
        "latest_status": fin_blocker.get("raw_snapshot_latest_status"),
        "forward_archive_rows": fin_blocker.get("raw_snapshot_events"),
        "archive_window_coverage_pct": fin_blocker.get("archive_window_coverage_pct"),
    }
    for issue in issues:
        if issue.get("id") != "P1_fin_netflow_auth_blocked":
            continue
        current_summary = dict(issue.get("summary") or {})
        if any(current_summary.get(key) != value for key, value in fin_summary.items()):
            issue["summary"] = {**current_summary, **fin_summary}
            issue["updated_at"] = datetime.utcnow().isoformat()
            updated = True
        break
    return updated


def _save_open_current_state_issues(issues: list[Dict[str, Any]]) -> None:
    issues_path = Path(PROJECT_ROOT) / "issues.json"
    issues_path.write_text(
        json.dumps({"issues": issues}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _load_open_current_state_issues() -> list[Dict[str, Any]]:
    issues_path = Path(PROJECT_ROOT) / "issues.json"
    payload = _read_json_file(issues_path) or {}
    issues = payload.get("issues") or []
    filtered: list[Dict[str, Any]] = []
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        if issue.get("status", "open") != "open":
            continue
        issue_id = str(issue.get("id") or "")
        if issue_id.startswith("#H_AUTO_"):
            continue
        filtered.append(issue)
    priority_rank = {"P0": 0, "P1": 1, "P2": 2}
    filtered.sort(
        key=lambda item: (
            priority_rank.get(str(item.get("priority") or "P9"), 9),
            str(item.get("id") or ""),
        )
    )
    return filtered


def _normalize_serial_result_for_docs(
    name: str,
    payload: Dict[str, Any] | None,
    *,
    now: datetime | None = None,
) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    if isinstance(payload.get("result"), dict):
        return _build_serial_result_summary(
            name,
            payload.get("result") or {},
            diagnostics=payload.get("diagnostics") if isinstance(payload.get("diagnostics"), dict) else {},
            artifact_path=payload.get("artifact_path"),
            now=now,
        )
    if payload.get("name") or any(
        key in payload
        for key in (
            "attempted",
            "success",
            "returncode",
            "timed_out",
            "fallback_artifact_used",
            "cached",
        )
    ):
        return {"name": name, **payload}
    return {}


def _format_candidate_lane_status_for_docs(lane: Dict[str, Any]) -> str:
    name = lane.get("name") or "unknown"
    if lane.get("cached"):
        status = "cached"
    elif lane.get("skipped"):
        status = "skipped"
    elif lane.get("timed_out"):
        status = "timeout"
    elif lane.get("success"):
        status = "fresh"
    else:
        status = "failed"
    if lane.get("fallback_artifact_used"):
        status += "→fallback"
    age_seconds = lane.get("artifact_age_seconds")
    if isinstance(age_seconds, (int, float)):
        status += f"({round(age_seconds / 3600, 1)}h)"
    return f"{name}={status}"


def _candidate_artifact_refresh_context(
    serial_results: Dict[str, Dict[str, Any]] | None,
    *,
    now: datetime | None = None,
) -> Dict[str, Any]:
    lane_summaries: list[Dict[str, Any]] = []
    timed_out_lanes: list[str] = []
    stale_fallback_lanes: list[str] = []
    artifact_age_hours_by_lane: Dict[str, float] = {}
    for name in CANDIDATE_REFRESH_LANES:
        summary = _normalize_serial_result_for_docs(name, (serial_results or {}).get(name), now=now)
        if not summary:
            continue
        timed_out = bool(summary.get("timed_out")) or (
            summary.get("returncode") == -1
            and "TIMEOUT after" in str(summary.get("stderr_preview") or summary.get("stderr") or "")
        )
        fallback_used = bool(summary.get("fallback_artifact_used"))
        lane = {
            **summary,
            "name": name,
            "timed_out": timed_out,
            "fallback_artifact_used": fallback_used,
        }
        lane_summaries.append(lane)
        if timed_out:
            timed_out_lanes.append(name)
        if timed_out and fallback_used:
            stale_fallback_lanes.append(name)
            age_seconds = lane.get("artifact_age_seconds")
            if isinstance(age_seconds, (int, float)):
                artifact_age_hours_by_lane[name] = round(age_seconds / 3600, 2)
    return {
        "candidate_lanes": lane_summaries,
        "timed_out_lanes": timed_out_lanes,
        "stale_fallback_lanes": stale_fallback_lanes,
        "artifact_age_hours_by_lane": artifact_age_hours_by_lane,
        "has_stale_fallback": bool(stale_fallback_lanes),
        "docs_line": " / ".join(_format_candidate_lane_status_for_docs(lane) for lane in lane_summaries),
    }


def _sync_candidate_artifact_refresh_issue(
    issues: list[Dict[str, Any]],
    context: Dict[str, Any],
    *,
    run_label: str,
) -> bool:
    issue_id = CANDIDATE_ARTIFACT_STALE_FALLBACK_ISSUE_ID
    stale_lanes = context.get("stale_fallback_lanes") or []
    now_iso = datetime.utcnow().isoformat()
    existing_index = next((idx for idx, issue in enumerate(issues) if issue.get("id") == issue_id), None)
    if not stale_lanes:
        if existing_index is not None:
            del issues[existing_index]
            return True
        return False

    summary = {
        "heartbeat": run_label,
        "timed_out_lanes": context.get("timed_out_lanes") or [],
        "stale_fallback_lanes": stale_lanes,
        "artifact_age_hours_by_lane": context.get("artifact_age_hours_by_lane") or {},
        "refresh_required": True,
    }
    issue = {
        "id": issue_id,
        "priority": "P1",
        "status": "open",
        "title": "candidate governance artifacts fell back after refresh timeouts",
        "summary": summary,
        "action": (
            "把 feature shrinkage / bull pocket candidate refresh 從 silent full rebuild 改成可完成的 bounded/live-context-only lane；"
            "在刷新完成前，leaderboard / training governance 必須把 stale fallback 標成 reference-only，不可當成 fresh production truth。"
        ),
        "next_action": (
            "先讓下一輪 full heartbeat 的 feature_group_ablation 與 bull_4h_pocket_ablation 不再 timeout；"
            "若仍超時，必須在 docs/API summary 明確標示 fallback artifact age 與 non-authoritative status。"
        ),
        "verify": [
            "source venv/bin/activate && python -m pytest tests/test_hb_parallel_runner.py -q",
            "python scripts/hb_parallel_runner.py --hb <next_full_run>",
            "check data/heartbeat_<run>_summary.json serial_results candidate lanes",
        ],
        "updated_at": now_iso,
    }
    if existing_index is None:
        issue["created_at"] = now_iso
        issues.append(issue)
    else:
        existing = issues[existing_index]
        issue["created_at"] = existing.get("created_at") or now_iso
        issues[existing_index] = {**existing, **issue}
    return True


def _verification_lines(issue: Dict[str, Any]) -> list[str]:
    verify = normalize_verify_steps(issue.get("verify") or [])
    if isinstance(verify, list):
        return [str(item).strip() for item in verify if str(item).strip()]
    if isinstance(verify, str) and verify.strip():
        return [verify.strip()]
    return []


def _issue_action_text(issue: Dict[str, Any]) -> str:
    action = issue.get("action") or issue.get("next_action")
    if isinstance(action, str) and action.strip():
        return action.strip()
    return "待補 current-state action"


def _generic_issue_current_lines(issue: Dict[str, Any]) -> list[str]:
    summary = issue.get("summary") or {}
    if not isinstance(summary, dict) or not summary:
        return []
    parts: list[str] = []
    for key, value in summary.items():
        if isinstance(value, list):
            rendered = ", ".join(str(item) for item in value[:4])
            if len(value) > 4:
                rendered += f" … (+{len(value) - 4})"
        else:
            rendered = str(value)
        parts.append(f"`{key}={rendered}`")
        if len(parts) >= 6:
            break
    if not parts:
        return []
    return ["目前真相：" + " / ".join(parts)]


def _has_recent_pathology_truth(summary: Dict[str, Any] | None, *, window: Any = None, alerts: Any = None) -> bool:
    if not isinstance(summary, dict):
        summary = {}
    checks = [
        window,
        alerts,
        summary.get("window"),
        summary.get("rows"),
        summary.get("win_rate"),
        summary.get("dominant_regime"),
        summary.get("dominant_regime_share"),
        summary.get("avg_quality"),
        summary.get("avg_pnl"),
        summary.get("avg_drawdown_penalty"),
        summary.get("top_shift_features"),
        summary.get("new_compressed_feature"),
        summary.get("tail_streak"),
        summary.get("target_path_diagnostics"),
        summary.get("interpretation"),
    ]
    return any(value not in (None, "", [], {}, ()) for value in checks)


def _format_target_tail_streak_for_docs(summary: Dict[str, Any] | None) -> str:
    if not isinstance(summary, dict):
        return "—"
    flat_tail = summary.get("tail_streak")
    if flat_tail not in (None, "", [], {}, ()):
        return str(flat_tail)
    target_path = summary.get("target_path_diagnostics") or {}
    if not isinstance(target_path, dict):
        return "—"
    tail_streak = target_path.get("tail_target_streak") or {}
    if not isinstance(tail_streak, dict):
        return "—"
    count = tail_streak.get("count")
    target = tail_streak.get("target")
    if count is None or target is None:
        return "—"
    return f"{count}x{target}"


def _issue_current_lines(
    issue: Dict[str, Any],
    *,
    counts: Dict[str, Any] | None,
    source_blockers: Dict[str, Any] | None,
    drift_diagnostics: Dict[str, Any] | None,
    live_predictor_diagnostics: Dict[str, Any] | None,
    live_decision_drilldown: Dict[str, Any] | None,
    q15_support_audit: Dict[str, Any] | None,
    circuit_breaker_audit: Dict[str, Any] | None,
    leaderboard_candidate_diagnostics: Dict[str, Any] | None,
) -> list[str]:
    issue_id = str(issue.get("id") or "")
    counts = counts or {}
    source_blockers = source_blockers or {}
    drift_diagnostics = drift_diagnostics or {}
    live_predictor_diagnostics = live_predictor_diagnostics or {}
    live_decision_drilldown = live_decision_drilldown or {}
    q15_support_audit = q15_support_audit or {}
    circuit_breaker_audit = circuit_breaker_audit or {}
    leaderboard_candidate_diagnostics = leaderboard_candidate_diagnostics or {}
    governance_contract = leaderboard_candidate_diagnostics.get("governance_contract") or {}
    governance_verdict = governance_contract.get("verdict") if isinstance(governance_contract, dict) else governance_contract
    governance_current_closure = (
        leaderboard_candidate_diagnostics.get("governance_current_closure")
        or (governance_contract.get("current_closure") if isinstance(governance_contract, dict) else None)
    )
    support_context = _support_truth_context(live_predictor_diagnostics, q15_support_audit)
    support_current_rows = support_context.get("current_rows", "—")
    support_minimum_rows = support_context.get("minimum_rows", "—")
    support_gap = support_context.get("gap_to_minimum", "—")
    support_route_verdict = support_context.get("support_route_verdict") or "—"
    support_governance_route = support_context.get("support_governance_route") or "—"
    support_progress_line = _support_progress_docs_line(support_context)
    support_progress_lines = [support_progress_line] if support_progress_line else []
    support_aware_profile = (
        leaderboard_candidate_diagnostics.get("support_aware_production_profile")
        or leaderboard_candidate_diagnostics.get("train_selected_profile")
        or (governance_contract.get("production_profile") if isinstance(governance_contract, dict) else None)
    )

    if issue_id in {"P0_current_live_deployment_blocker", "P0_circuit_breaker_active"}:
        release = (live_predictor_diagnostics.get("deployment_blocker_details") or {}).get("release_condition") or {}
        deployment_blocker = str(live_predictor_diagnostics.get("deployment_blocker") or "")
        if deployment_blocker == "circuit_breaker_active":
            return [
                "目前真相："
                f"`deployment_blocker={live_predictor_diagnostics.get('deployment_blocker') or '—'}` / "
                f"`streak={live_predictor_diagnostics.get('streak')}` / "
                f"`recent {release.get('recent_window') or live_predictor_diagnostics.get('window_size') or '—'} wins="
                f"{release.get('current_recent_window_wins', live_predictor_diagnostics.get('recent_window_wins', '—'))}/"
                f"{release.get('recent_window', live_predictor_diagnostics.get('window_size', '—'))}` / "
                f"`additional_recent_window_wins_needed={release.get('additional_recent_window_wins_needed', '—')}`",
                "same-bucket truth："
                f"`bucket={live_predictor_diagnostics.get('current_live_structure_bucket') or '—'}` / "
                f"`support={support_current_rows}/{support_minimum_rows}` / "
                f"`support_route_verdict={support_route_verdict}` / "
                f"`support_governance_route={support_governance_route}`",
                *support_progress_lines,
            ]
        summary = issue.get("summary") if isinstance(issue.get("summary"), dict) else {}
        patch_context = _patch_truth_doc_context(
            summary.get("recommended_patch") or live_decision_drilldown.get("recommended_patch_profile"),
            summary.get("recommended_patch_status") or live_decision_drilldown.get("recommended_patch_status"),
            summary.get("reference_patch_scope")
            or summary.get("recommended_patch_reference_scope")
            or live_decision_drilldown.get("recommended_patch_reference_scope"),
        )
        return [
            "目前真相："
            f"`deployment_blocker={live_predictor_diagnostics.get('deployment_blocker') or '—'}` / "
            f"`bucket={live_predictor_diagnostics.get('current_live_structure_bucket') or '—'}` / "
            f"`support={support_current_rows}/{support_minimum_rows}` / "
            f"`gap={support_gap}` / "
            f"`runtime_closure_state={live_predictor_diagnostics.get('runtime_closure_state') or '—'}`",
            "same-bucket truth："
            f"`support_route_verdict={support_route_verdict}` / "
            f"`support_governance_route={support_governance_route}` / "
            f"`recommended_patch={patch_context['profile']}` / "
            f"`recommended_patch_status={patch_context['status']}` / "
            f"`reference_scope={patch_context['reference_scope']}`",
            *support_progress_lines,
        ]

    if issue_id == "P0_recent_distribution_pathology":
        latest_summary = drift_diagnostics.get("primary_summary") or {}
        latest_window = drift_diagnostics.get("primary_window") or latest_summary.get("window") or "—"
        latest_alerts = drift_diagnostics.get("primary_alerts") or []
        drift_blocking_summary = drift_diagnostics.get("blocking_summary") or {}
        drift_blocking_window = drift_diagnostics.get("blocking_window")
        drift_blocking_alerts = drift_diagnostics.get("blocking_alerts") or []
        if not _has_recent_pathology_truth(
            drift_blocking_summary,
            window=drift_blocking_window,
            alerts=drift_blocking_alerts,
        ):
            drift_blocking_summary = {}
            drift_blocking_window = None
            drift_blocking_alerts = []
        issue_summary = issue.get("summary") if isinstance(issue.get("summary"), dict) else {}
        blocker_summary = drift_blocking_summary or issue_summary
        blocker_window = drift_blocking_window or blocker_summary.get("window") or latest_window
        blocker_alerts = drift_blocking_alerts or blocker_summary.get("alerts") or latest_alerts
        latest_signature = (
            str(latest_window),
            latest_summary.get("win_rate"),
            latest_summary.get("dominant_regime"),
            latest_summary.get("dominant_regime_share"),
            latest_summary.get("avg_quality"),
            latest_summary.get("avg_pnl"),
            tuple(str(item) for item in latest_alerts),
        )
        blocker_signature = (
            str(blocker_window),
            blocker_summary.get("win_rate", latest_summary.get("win_rate")),
            blocker_summary.get("dominant_regime", latest_summary.get("dominant_regime")),
            blocker_summary.get("dominant_regime_share", latest_summary.get("dominant_regime_share")),
            blocker_summary.get("avg_quality", latest_summary.get("avg_quality")),
            blocker_summary.get("avg_pnl", latest_summary.get("avg_pnl")),
            tuple(str(item) for item in blocker_alerts),
        )
        blocker_top_shifts = blocker_summary.get("top_shift_features") or []
        if isinstance(blocker_top_shifts, list):
            blocker_top_shift_text = ",".join(str(item) for item in blocker_top_shifts[:3]) or "—"
        else:
            blocker_top_shift_text = str(blocker_top_shifts)
        lines = [
            "目前真相："
            + _format_recent_pathology_docs_line(
                "window",
                window=blocker_window,
                win_rate=blocker_summary.get("win_rate", latest_summary.get("win_rate")),
                dominant_regime=blocker_summary.get("dominant_regime", latest_summary.get("dominant_regime")),
                dominant_regime_share=blocker_summary.get("dominant_regime_share", latest_summary.get("dominant_regime_share")),
                avg_quality=blocker_summary.get("avg_quality", latest_summary.get("avg_quality")),
                avg_pnl=blocker_summary.get("avg_pnl", latest_summary.get("avg_pnl")),
                alerts=blocker_alerts,
            )
        ]
        if blocker_signature != latest_signature:
            lines.append(
                "latest diagnostics："
                + _format_recent_pathology_docs_line(
                    "latest_window",
                    window=latest_window,
                    win_rate=latest_summary.get("win_rate"),
                    dominant_regime=latest_summary.get("dominant_regime"),
                    dominant_regime_share=latest_summary.get("dominant_regime_share"),
                    avg_quality=latest_summary.get("avg_quality"),
                    avg_pnl=latest_summary.get("avg_pnl"),
                    alerts=latest_alerts,
                )
            )
        lines.append(
            "病態切片："
            f"`alerts={','.join(str(item) for item in blocker_alerts) or '—'}` / "
            f"`tail_streak={_format_target_tail_streak_for_docs(blocker_summary)}` / "
            f"`top_shift={blocker_top_shift_text or '—'}` / "
            f"`new_compressed={blocker_summary.get('new_compressed_feature', '—')}`"
        )
        return lines

    if issue_id == "P1_leaderboard_recent_window_contract":
        return [
            "目前真相："
            f"`leaderboard_count={leaderboard_candidate_diagnostics.get('leaderboard_count', '—')}` / "
            f"`selected_feature_profile={leaderboard_candidate_diagnostics.get('selected_feature_profile') or '—'}` / "
            f"`support_aware_profile={support_aware_profile or '—'}` / "
            f"`governance_contract={governance_verdict or '—'}` / "
            f"`current_closure={governance_current_closure or '—'}`",
        ]

    if issue_id == "P1_execution_venue_readiness_unverified":
        return [
            "目前真相："
            "`binance=config enabled + public-only + metadata OK` / "
            "`okx=config disabled + public-only + metadata OK` / "
            "`missing_runtime_proof=live exchange credential, order ack lifecycle, fill lifecycle`",
        ]

    if issue_id == "P1_fin_netflow_auth_blocked":
        fin_blocker = None
        for blocker in source_blockers.get("blocked_features") or []:
            if isinstance(blocker, dict) and blocker.get("key") == "fin_netflow":
                fin_blocker = blocker
                break
        if fin_blocker:
            return [
                "目前真相："
                f"`quality_flag={fin_blocker.get('quality_flag')}` / "
                f"`latest_status={fin_blocker.get('raw_snapshot_latest_status')}` / "
                f"`forward_archive_rows={fin_blocker.get('raw_snapshot_events')}` / "
                f"`archive_window_coverage_pct={fin_blocker.get('archive_window_coverage_pct')}`",
            ]

    if issue_id == "P1_q15_exact_support_stalled_under_breaker":
        summary = issue.get("summary") or {}
        breaker_context = summary.get("breaker_context") or ("circuit_breaker_active" if live_predictor_diagnostics.get("deployment_blocker") == "circuit_breaker_active" else "breaker_clear")
        return [
            "目前真相："
            f"`bucket={support_context.get('current_bucket') or live_predictor_diagnostics.get('current_live_structure_bucket') or '—'}` / "
            f"`support={support_current_rows}/{support_minimum_rows}` / "
            f"`gap={support_gap}` / "
            f"`support_route_verdict={support_route_verdict}` / "
            f"`governance_route={support_governance_route}` / "
            f"`breaker_context={breaker_context}`",
            *support_progress_lines,
        ]

    if issue_id == "P1_bull_caution_spillover_patch_reference_only":
        summary = issue.get("summary") or {}
        summary_bucket = summary.get("current_live_structure_bucket") or live_predictor_diagnostics.get("current_live_structure_bucket") or "—"
        summary_rows = summary.get("current_live_structure_bucket_rows", support_current_rows)
        summary_minimum = summary.get("minimum_support_rows", support_minimum_rows)
        summary_gap = summary.get("gap_to_minimum", support_gap)
        summary_verdict = summary.get("support_route_verdict") or support_route_verdict
        summary_governance = summary.get("support_governance_route") or support_governance_route
        return [
            "目前真相："
            f"`bucket={summary_bucket}` / "
            f"`support={summary_rows}/{summary_minimum}` / "
            f"`gap={summary_gap}` / "
            f"`support_route_verdict={summary_verdict}` / "
            f"`governance_route={summary_governance}`",
            *support_progress_lines,
        ]

    if issue_id == "P1_q35_scaling_no_deploy":
        summary = issue.get("summary") or {}
        summary_bucket = summary.get("current_live_structure_bucket") or live_predictor_diagnostics.get("current_live_structure_bucket") or "—"
        summary_rows = summary.get("current_live_structure_bucket_rows", support_current_rows)
        summary_minimum = summary.get("minimum_support_rows", support_minimum_rows)
        summary_gap = summary.get("gap_to_minimum", support_gap)
        summary_verdict = summary.get("support_route_verdict") or support_route_verdict
        q35_doc_line = _q35_scaling_doc_line(issue)
        lines = [
            "目前真相："
            f"`bucket={summary_bucket}` / "
            f"`support={summary_rows}/{summary_minimum}` / "
            f"`gap={summary_gap}` / "
            f"`support_route_verdict={summary_verdict}` / "
            f"`overall_verdict={summary.get('overall_verdict') or '—'}` / "
            f"`redesign_verdict={summary.get('redesign_verdict') or '—'}` / "
            f"`runtime_gap_to_floor={summary.get('runtime_remaining_gap_to_floor', summary.get('remaining_gap_to_floor', '—'))}`",
        ]
        if q35_doc_line:
            lines.append(q35_doc_line)
        return lines

    return _generic_issue_current_lines(issue)


def _find_open_issue(issues: list[Dict[str, Any]], issue_id: str) -> Dict[str, Any] | None:
    for issue in issues:
        if issue.get("id") == issue_id and issue.get("status", "open") == "open":
            return issue
    return None


def _q35_scaling_doc_line(issue: Dict[str, Any] | None) -> str | None:
    if not isinstance(issue, dict):
        return None
    summary = issue.get("summary") or {}
    if not isinstance(summary, dict) or not summary:
        return None
    runtime_gap = summary.get("runtime_remaining_gap_to_floor", summary.get("remaining_gap_to_floor"))
    intro = "q35 scaling audit 已指出目前不是單點 bias50 closure："
    parts = [
        f"`overall_verdict={summary.get('overall_verdict') or '—'}`",
        f"`redesign_verdict={summary.get('redesign_verdict') or '—'}`",
        f"`runtime_gap_to_floor={runtime_gap if runtime_gap is not None else '—'}`",
    ]
    if summary.get("redesign_entry_quality") is not None:
        parts.append(f"`redesign_entry_quality={summary.get('redesign_entry_quality')}`")
    if summary.get("redesign_allowed_layers_after") is not None:
        parts.append(f"`redesign_allowed_layers={summary.get('redesign_allowed_layers_after')}`")
    if summary.get("redesign_positive_discriminative_gap") is not None:
        parts.append(f"`positive_discriminative_gap={summary.get('redesign_positive_discriminative_gap')}`")
    if summary.get("redesign_execution_blocked_after_floor_cross") is not None:
        parts.append(
            f"`execution_blocked_after_floor_cross={summary.get('redesign_execution_blocked_after_floor_cross')}`"
        )
    return f"{intro} " + " / ".join(parts)



def _format_recent_pathology_docs_line(
    window_label: str,
    *,
    window: Any,
    win_rate: Any,
    dominant_regime: Any,
    dominant_regime_share: Any,
    avg_quality: Any,
    avg_pnl: Any,
    alerts: list[Any] | None,
) -> str:
    return (
        f"`{window_label}={window if window not in (None, '') else '—'}` / "
        f"`win_rate={_format_pct_for_docs(win_rate, 1)}` / "
        f"`dominant_regime={dominant_regime or '—'}({_format_pct_for_docs(dominant_regime_share, 1)})` / "
        f"`avg_quality={_format_number_for_docs(avg_quality, 4, signed=True)}` / "
        f"`avg_pnl={_format_number_for_docs(avg_pnl, 4, signed=True)}` / "
        f"`alerts={','.join(str(item) for item in (alerts or [])) or '—'}`"
    )



def _docs_value_missing(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {} or value == ()



def _leaderboard_docs_context(
    leaderboard_candidate_diagnostics: Dict[str, Any] | None,
    issues: list[Dict[str, Any]],
) -> Dict[str, Any]:
    """Return docs-ready leaderboard governance truth.

    Docs overwrite can be called by focused verification/debug lanes that do not
    rerun the leaderboard candidate probe. In that case, keep current-state docs
    productized by falling back to the latest persisted probe artifact and then
    to the machine-readable issue summary instead of writing misleading `—`
    placeholders for the P1 leaderboard contract.
    """

    context: Dict[str, Any] = dict(leaderboard_candidate_diagnostics or {})
    needs_fallback = any(
        _docs_value_missing(context.get(key))
        for key in ("leaderboard_count", "selected_feature_profile")
    ) or (
        _docs_value_missing(context.get("governance_contract"))
        and _docs_value_missing(context.get("governance_current_closure"))
    )
    if needs_fallback and not context:
        try:
            artifact_context = collect_leaderboard_candidate_diagnostics()
        except Exception:
            artifact_context = {}
        if isinstance(artifact_context, dict):
            for key, value in artifact_context.items():
                if _docs_value_missing(context.get(key)) and not _docs_value_missing(value):
                    context[key] = value

    issue = _find_open_issue(issues, "P1_leaderboard_recent_window_contract")
    summary = issue.get("summary") if isinstance(issue, dict) else None
    if isinstance(summary, dict):
        fallback_fields = {
            "leaderboard_count": summary.get("leaderboard_count"),
            "selected_feature_profile": summary.get("selected_feature_profile") or summary.get("top_profile"),
            "support_aware_production_profile": summary.get("support_aware_profile")
            or summary.get("support_aware_production_profile")
            or summary.get("train_selected_profile"),
            "train_selected_profile": summary.get("train_selected_profile"),
            "governance_contract": summary.get("governance_contract"),
            "governance_current_closure": summary.get("current_closure")
            or summary.get("governance_current_closure"),
            "dual_profile_state": summary.get("dual_profile_state"),
            "leaderboard_payload_source": summary.get("leaderboard_payload_source"),
        }
        for key, value in fallback_fields.items():
            if _docs_value_missing(context.get(key)) and not _docs_value_missing(value):
                context[key] = value

    return context



def overwrite_current_state_docs(
    run_label: str,
    counts: Dict[str, Any] | None,
    source_blockers: Dict[str, Any] | None,
    drift_diagnostics: Dict[str, Any] | None,
    live_predictor_diagnostics: Dict[str, Any] | None,
    live_decision_drilldown: Dict[str, Any] | None,
    q15_support_audit: Dict[str, Any] | None,
    circuit_breaker_audit: Dict[str, Any] | None,
    leaderboard_candidate_diagnostics: Dict[str, Any] | None,
    *,
    run_mode: str | None = None,
    collect_attempted: bool = True,
    serial_results: Dict[str, Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    counts = counts or {}
    source_blockers = source_blockers or {}
    drift_diagnostics = drift_diagnostics or {}
    live_predictor_diagnostics = live_predictor_diagnostics or {}
    live_decision_drilldown = live_decision_drilldown or {}
    q15_support_audit = q15_support_audit or {}
    circuit_breaker_audit = circuit_breaker_audit or {}
    leaderboard_candidate_diagnostics = leaderboard_candidate_diagnostics or {}
    issues = _load_open_current_state_issues()
    leaderboard_candidate_diagnostics = _leaderboard_docs_context(leaderboard_candidate_diagnostics, issues)
    candidate_refresh_context = _candidate_artifact_refresh_context(serial_results)
    issues_changed = False
    if _sync_live_issue_summaries(issues, source_blockers):
        issues_changed = True
    if _sync_candidate_artifact_refresh_issue(issues, candidate_refresh_context, run_label=run_label):
        issues_changed = True
    if issues_changed:
        _save_open_current_state_issues(issues)

    updated_at = _format_local_timestamp_for_docs()
    normalized_run_mode = str(run_mode or "fast").strip().lower()
    heartbeat_mode_label = {
        "fast": "fast heartbeat",
        "full": "full heartbeat",
    }.get(normalized_run_mode, "heartbeat")
    completion_phrase = (
        "已完成 collect + diagnostics refresh"
        if collect_attempted
        else "已完成 diagnostics refresh（collect skipped）"
    )
    orid_completion_phrase = (
        "collect + diagnostics refresh 完成"
        if collect_attempted
        else "diagnostics refresh 完成（collect skipped）"
    )
    release = (live_predictor_diagnostics.get("deployment_blocker_details") or {}).get("release_condition") or {}
    primary_summary = drift_diagnostics.get("primary_summary") or {}
    primary_window = drift_diagnostics.get("primary_window") or primary_summary.get("window") or "—"
    governance_contract = leaderboard_candidate_diagnostics.get("governance_contract") or {}
    governance_verdict = governance_contract.get("verdict") if isinstance(governance_contract, dict) else governance_contract
    governance_current_closure = (
        leaderboard_candidate_diagnostics.get("governance_current_closure")
        or (governance_contract.get("current_closure") if isinstance(governance_contract, dict) else None)
    )
    support_aware_profile = (
        leaderboard_candidate_diagnostics.get("support_aware_production_profile")
        or leaderboard_candidate_diagnostics.get("train_selected_profile")
        or (governance_contract.get("production_profile") if isinstance(governance_contract, dict) else None)
    )
    q35_scaling_issue = _find_open_issue(issues, "P1_q35_scaling_no_deploy")
    q35_scaling_doc_line = _q35_scaling_doc_line(q35_scaling_issue)
    current_support_bucket = _current_support_bucket(live_predictor_diagnostics, q15_support_audit)
    support_scope_label = _support_scope_label(current_support_bucket)
    support_truth_label = _support_truth_label(current_support_bucket)
    support_context = _support_truth_context(live_predictor_diagnostics, q15_support_audit)
    support_current_rows = support_context.get(
        "current_rows",
        live_predictor_diagnostics.get("current_live_structure_bucket_rows", "—"),
    )
    support_minimum_rows = support_context.get(
        "minimum_rows",
        live_predictor_diagnostics.get("minimum_support_rows", "—"),
    )
    support_gap = support_context.get(
        "gap_to_minimum",
        live_predictor_diagnostics.get("current_live_structure_bucket_gap_to_minimum", "—"),
    )
    support_route_verdict = support_context.get("support_route_verdict") or "—"
    support_progress_line = _support_progress_docs_line(support_context)
    support_progress_doc_lines = [support_progress_line] if support_progress_line else []

    counts_line = (
        f"`Raw={counts.get('raw_market_data', '—')} / "
        f"Features={counts.get('features_normalized', '—')} / "
        f"Labels={counts.get('labels', '—')}`"
    )
    history_confirmation = collect_historical_coverage_confirmation(DB_PATH)
    history_tables = history_confirmation.get("tables") if isinstance(history_confirmation, dict) else {}
    raw_history = history_tables.get("raw_market_data") if isinstance(history_tables, dict) else {}
    feature_history = history_tables.get("features_normalized") if isinstance(history_tables, dict) else {}
    label_history = history_tables.get("labels") if isinstance(history_tables, dict) else {}
    history_line = (
        f"`2y_backfill_ok={history_confirmation.get('covers_two_years')}` / "
        f"`raw_start={raw_history.get('start') or '—'}` / "
        f"`features_start={feature_history.get('start') or '—'}` / "
        f"`labels_start={label_history.get('start') or '—'}`"
    )
    blocker_line = (
        f"`deployment_blocker={live_predictor_diagnostics.get('deployment_blocker') or '—'}` / "
        f"`streak={live_predictor_diagnostics.get('streak', '—')}` / "
        f"`recent_window_wins={release.get('current_recent_window_wins', live_predictor_diagnostics.get('recent_window_wins', '—'))}/"
        f"{release.get('recent_window', live_predictor_diagnostics.get('window_size', '—'))}` / "
        f"`additional_recent_window_wins_needed={release.get('additional_recent_window_wins_needed', '—')}`"
    )
    support_line = (
        f"`current_live_structure_bucket={live_predictor_diagnostics.get('current_live_structure_bucket') or '—'}` / "
        f"`support={support_current_rows}/{support_minimum_rows}` / "
        f"`gap={support_gap}` / "
        f"`support_route_verdict={support_route_verdict}`"
    )
    primary_alerts = drift_diagnostics.get("primary_alerts") or []
    pathology_line = _format_recent_pathology_docs_line(
        "latest_window",
        window=primary_window,
        win_rate=primary_summary.get("win_rate"),
        dominant_regime=primary_summary.get("dominant_regime"),
        dominant_regime_share=primary_summary.get("dominant_regime_share"),
        avg_quality=primary_summary.get("avg_quality"),
        avg_pnl=primary_summary.get("avg_pnl"),
        alerts=primary_alerts,
    )
    blocking_pathology_line = None
    recent_pathology_issue = _find_open_issue(issues, "P0_recent_distribution_pathology")
    drift_blocking_summary = drift_diagnostics.get("blocking_summary") or {}
    drift_blocking_window = drift_diagnostics.get("blocking_window")
    drift_blocking_alerts = drift_diagnostics.get("blocking_alerts") or []
    if not _has_recent_pathology_truth(
        drift_blocking_summary,
        window=drift_blocking_window,
        alerts=drift_blocking_alerts,
    ):
        drift_blocking_summary = {}
        drift_blocking_window = None
        drift_blocking_alerts = []
    recent_pathology_summary = drift_blocking_summary
    if not recent_pathology_summary and recent_pathology_issue:
        recent_pathology_summary = recent_pathology_issue.get("summary") or {}
    blocker_alerts = drift_blocking_alerts or recent_pathology_summary.get("alerts") or []
    blocker_window = drift_blocking_window or recent_pathology_summary.get("window")
    if recent_pathology_summary:
        latest_signature = (
            str(primary_window),
            primary_summary.get("win_rate"),
            primary_summary.get("dominant_regime"),
            primary_summary.get("dominant_regime_share"),
            primary_summary.get("avg_quality"),
            primary_summary.get("avg_pnl"),
            tuple(str(item) for item in primary_alerts),
        )
        blocker_signature = (
            str(blocker_window or "—"),
            recent_pathology_summary.get("win_rate"),
            recent_pathology_summary.get("dominant_regime"),
            recent_pathology_summary.get("dominant_regime_share"),
            recent_pathology_summary.get("avg_quality"),
            recent_pathology_summary.get("avg_pnl"),
            tuple(str(item) for item in blocker_alerts),
        )
        if blocker_signature != latest_signature:
            blocking_pathology_line = _format_recent_pathology_docs_line(
                "blocking_window",
                window=blocker_window,
                win_rate=recent_pathology_summary.get("win_rate"),
                dominant_regime=recent_pathology_summary.get("dominant_regime"),
                dominant_regime_share=recent_pathology_summary.get("dominant_regime_share"),
                avg_quality=recent_pathology_summary.get("avg_quality"),
                avg_pnl=recent_pathology_summary.get("avg_pnl"),
                alerts=blocker_alerts,
            )
    leaderboard_line = (
        f"`leaderboard_count={leaderboard_candidate_diagnostics.get('leaderboard_count', '—')}` / "
        f"`selected_feature_profile={leaderboard_candidate_diagnostics.get('selected_feature_profile') or '—'}` / "
        f"`support_aware_profile={support_aware_profile or '—'}` / "
        f"`governance_contract={governance_verdict or '—'}` / "
        f"`current_closure={governance_current_closure or '—'}`"
    )
    governance_text = f"{governance_verdict or ''} {governance_current_closure or ''}".lower()
    if "single" in governance_text:
        leaderboard_fact_heading = "- **leaderboard / governance 已收斂為 single-role alignment**"
        leaderboard_governance_label = "leaderboard single-role governance"
    elif "dual" in governance_text or "split" in governance_text:
        leaderboard_fact_heading = "- **leaderboard / governance 仍維持 dual-role contract**"
        leaderboard_governance_label = "leaderboard dual-role governance"
    else:
        leaderboard_fact_heading = "- **leaderboard / governance current-state 已刷新**"
        leaderboard_governance_label = "leaderboard governance"
    fin_blocker = None
    for blocker in source_blockers.get("blocked_features") or []:
        if isinstance(blocker, dict) and blocker.get("key") == "fin_netflow":
            fin_blocker = blocker
            break
    fin_line = (
        f"`quality_flag={fin_blocker.get('quality_flag')}` / "
        f"`latest_status={fin_blocker.get('raw_snapshot_latest_status')}` / "
        f"`forward_archive_rows={fin_blocker.get('raw_snapshot_events')}` / "
        f"`archive_window_coverage_pct={fin_blocker.get('archive_window_coverage_pct')}`"
        if fin_blocker
        else "`fin_netflow` blocker 資訊暫缺"
    )
    candidate_refresh_line = candidate_refresh_context.get("docs_line") or "—"
    candidate_refresh_fact_lines = []
    candidate_refresh_goal_lines = []
    if candidate_refresh_context.get("has_stale_fallback"):
        candidate_refresh_fact_lines = [
            "- **candidate governance refresh 仍有 stale fallback 風險**",
            f"  - `{candidate_refresh_line}`",
        ]
        candidate_refresh_goal_lines = [
            "- candidate refresh："
            f"`{candidate_refresh_line}`（fallback artifact 只能作 reference-only governance，不可當成 fresh production truth）"
        ]
    patch_context = _patch_truth_doc_context(
        live_decision_drilldown.get("recommended_patch_profile"),
        live_decision_drilldown.get("recommended_patch_status"),
        live_decision_drilldown.get("recommended_patch_reference_scope"),
    )
    patch_profile = patch_context["profile"]
    patch_status = patch_context["status"]
    patch_reference_scope = patch_context["reference_scope"]
    current_priority_line3 = (
        f"3. **守住 {support_scope_label} {patch_context['priority_focus_phrase']}、"
        f"{leaderboard_governance_label}、venue/source blockers 可見性**"
    )
    goal_c_title = f"### 目標 C：守住 {support_scope_label} {patch_context['goal_title_suffix']}"
    next_gate_line3 = (
        f"3. **守住 {support_scope_label} {patch_context['priority_focus_phrase']}、"
        "leaderboard governance、venue/source blockers 與 docs automation 閉環**"
    )
    next_gate_line3_blocker = (
        "   - 升級 blocker：若 patch 被誤升級成 deployable truth、排行榜 drift 成 placeholder-only、venue/source blocker 消失、或 docs 再次落後 latest artifacts"
        if patch_context["has_patch"]
        else "   - 升級 blocker：若 support closure 被誤讀成 deployment closure、排行榜 drift 成 placeholder-only、venue/source blocker 消失、或 docs 再次落後 latest artifacts"
    )
    if patch_context["has_patch"]:
        orid_support_action_clause = f"並把 {support_scope_label} support 與 {patch_context['patch_label']} 持續顯示清楚"
        orid_support_fail_clause = f"或把 {patch_context['patch_label']} 誤包裝成可部署 truth"
        if patch_context["reference_only"]:
            support_orid_insight_line = (
                f"1. **support truth ≠ deployment closure**：`support={support_current_rows}/{support_minimum_rows}` 且 "
                f"`support_route_verdict={support_route_verdict}` 只代表治理前進，還不能把 {patch_context['patch_label']} 升級成 runtime patch。"
            )
        else:
            support_orid_insight_line = (
                f"1. **support truth ≠ deployment closure**：`support={support_current_rows}/{support_minimum_rows}` 且 "
                f"`support_route_verdict={support_route_verdict}` 只代表 same-bucket support / patch 治理真相，不能跳過 runtime verify。"
            )
    else:
        orid_support_action_clause = f"並把 {support_scope_label} support truth 與 deployment closure 邊界持續顯示清楚"
        orid_support_fail_clause = "或把 support closure 誤讀成 deployment closure"
        support_orid_insight_line = (
            f"1. **support truth ≠ deployment closure**：`support={support_current_rows}/{support_minimum_rows}` 且 "
            f"`support_route_verdict={support_route_verdict}` 只代表 same-bucket support 狀態，真正 deployment blocker 仍由 latest runtime truth 決定。"
        )
    deployment_blocker = str(live_predictor_diagnostics.get("deployment_blocker") or "—")
    breaker_root_cause = str(((circuit_breaker_audit.get("root_cause") or {}).get("verdict")) or "")
    breaker_is_primary = deployment_blocker == "circuit_breaker_active" or breaker_root_cause in {
        "canonical_breaker_active",
        "breaker_active",
    }
    if breaker_is_primary:
        facts_blocker_heading = "- **canonical current-live blocker 仍是 breaker-first truth**"
        current_priority_line1 = f"1. **維持 breaker-first truth，同時保留 {support_scope_label} support rows 可 machine-read**"
        goal_a_title = "### 目標 A：維持 breaker release math 作為唯一 current-live blocker"
        goal_a_success = "- `/`、`/execution`、`/execution/status`、`/lab`、probe、drilldown、docs 都把 breaker release math 視為唯一 current-live deployment blocker；`/execution` 在 `/api/status` 初次同步前也不得開放買入 / 減碼 / 啟用自動模式。"
        next_gate_line1 = f"1. **維持 breaker-first truth + {support_scope_label} visibility across API / UI / docs**"
        next_gate_line1_blocker = f"   - 升級 blocker：若 breaker release math 被 support / floor-gap / venue 話題覆蓋，或 {support_scope_label} rows 再次從 top-level surfaces 消失"
        success_primary_line = "- current-live blocker 清楚且唯一：**breaker release math**"
        orid_reflection_line = (
            f"- 這輪最需要防止的誤讀，是把 `{support_current_rows}/{support_minimum_rows}` 的 same-bucket support 或 `{patch_reference_scope}` 參考 patch 誤讀成已可部署；breaker 仍是唯一 current-live blocker。"
        )
        orid_insight2 = "2. **真正主 blocker 仍是 breaker + recent pathological slice**：目前該追的是 release math 與 recent canonical pathology，不是把 q15/q35 support 或 venue 話題誤升級成唯一根因。"
        orid_action_line = f"- **Action**：維持 breaker-first truth，{orid_support_action_clause}；下一步沿 recent pathological slice 與 release math 繼續追根因。"
        orid_fail_line = f"- **If fail**：只要 docs / UI 再次隱藏 breaker-first truth、漏掉 {support_scope_label} rows，{orid_support_fail_clause}，就把 heartbeat 升級回 current-state governance blocker。"
    elif deployment_blocker in {"unsupported_exact_live_structure_bucket", "under_minimum_exact_live_structure_bucket"}:
        facts_blocker_heading = "- **canonical current-live blocker 已切到 current-live exact-support truth**"
        current_priority_line1 = f"1. **維持 current-live exact-support blocker truth，同時保留 {support_scope_label} support rows 可 machine-read**"
        goal_a_title = "### 目標 A：維持 current-live exact-support blocker 作為唯一 current-live blocker"
        goal_a_success = (
            f"- `/`、`/execution`、`/execution/status`、`/lab`、probe、drilldown、docs 都把 `{deployment_blocker}` 視為唯一 current-live deployment blocker，且不再誤回退成 breaker-first 舊敘事；`/execution` 在 `/api/status` 初次同步前也不得開放買入 / 減碼 / 啟用自動模式。"
        )
        next_gate_line1 = f"1. **維持 current-live exact-support blocker + {support_scope_label} visibility across API / UI / docs**"
        next_gate_line1_blocker = (
            f"   - 升級 blocker：若 current-live blocker 被 breaker 舊敘事 / venue 話題覆蓋，或 {support_scope_label} rows 再次從 top-level surfaces 消失"
        )
        success_primary_line = f"- current-live blocker 清楚且唯一：**{deployment_blocker}**"
        orid_reflection_line = (
            f"- 這輪最需要防止的誤讀，是把 `{support_current_rows}/{support_minimum_rows}` 的 same-bucket support 或 `{patch_reference_scope}` 參考 patch 誤讀成已可部署；目前 live blocker 已切到 `{deployment_blocker}`。"
        )
        orid_insight2 = (
            f"2. **真正主 blocker 已切到 {support_scope_label} exact-support shortage**：recent pathological slice 仍是造成 `{deployment_blocker}` 的根因切片，不能再沿用 breaker-first 舊敘事。"
        )
        orid_action_line = f"- **Action**：維持 current-live exact-support truth，{orid_support_action_clause}；下一步沿 recent pathological slice 與 exact-support accumulation 繼續追根因。"
        orid_fail_line = (
            f"- **If fail**：只要 docs / UI 再次把 `{deployment_blocker}` 誤寫成 breaker-first、漏掉 {support_scope_label} rows，{orid_support_fail_clause}，就把 heartbeat 升級回 current-state governance blocker。"
        )
    else:
        facts_blocker_heading = "- **canonical current-live blocker 以 latest runtime truth 為主**"
        current_priority_line1 = f"1. **維持 current-live blocker truth（{deployment_blocker}），同時保留 {support_scope_label} support rows 可 machine-read**"
        goal_a_title = "### 目標 A：維持 latest runtime blocker 作為唯一 current-live blocker"
        goal_a_success = (
            f"- `/`、`/execution`、`/execution/status`、`/lab`、probe、drilldown、docs 都把 `{deployment_blocker}` 視為唯一 current-live deployment blocker；`/execution` 在 `/api/status` 初次同步前也不得開放買入 / 減碼 / 啟用自動模式。"
        )
        next_gate_line1 = f"1. **維持 latest runtime blocker（{deployment_blocker}）+ {support_scope_label} visibility across API / UI / docs**"
        next_gate_line1_blocker = (
            f"   - 升級 blocker：若 current-live blocker 再被舊 breaker / support 敘事覆蓋，或 {support_scope_label} rows 再次從 top-level surfaces 消失"
        )
        success_primary_line = f"- current-live blocker 清楚且唯一：**{deployment_blocker}**"
        orid_reflection_line = f"- 這輪最需要防止的誤讀，是讓舊 blocker 敘事覆蓋最新 `{deployment_blocker}` runtime truth。"
        orid_insight2 = f"2. **真正主 blocker 以 latest runtime truth 為準**：目前 deployment blocker 是 `{deployment_blocker}`，後續 root-cause 與 docs 必須跟著這條 lane 收斂。"
        orid_action_line = f"- **Action**：維持 latest runtime blocker truth，{orid_support_action_clause}；下一步沿對應 runtime lane 繼續追根因。"
        orid_fail_line = f"- **If fail**：只要 docs / UI 再次把 `{deployment_blocker}` 蓋回舊 blocker 敘事、漏掉 {support_scope_label} rows，{orid_support_fail_clause}，就把 heartbeat 升級回 current-state governance blocker。"

    issues_lines = [
        "# ISSUES.md — Current State Only",
        "",
        f"_最後更新：{updated_at}_",
        "",
        "只保留目前有效問題；由 heartbeat runner overwrite sync，避免 current-state markdown 落後 issues.json / live artifacts。",
        "",
        "---",
        "",
        "## 當前主線事實",
        f"- **最新 {heartbeat_mode_label} #{run_label} {completion_phrase}**",
        f"  - {counts_line}",
        f"  - 歷史覆蓋確認：{history_line}",
        f"  - `simulated_pyramid_win={_format_pct_for_docs(counts.get('simulated_pyramid_win_rate'), 2)}`",
        facts_blocker_heading,
        f"  - {blocker_line}",
        f"  - {support_line}",
        *[f"  - {line}" for line in support_progress_doc_lines],
        "- **recent canonical diagnostics 已刷新**",
        f"  - {pathology_line}",
        *([f"  - {blocking_pathology_line}"] if blocking_pathology_line else []),
        leaderboard_fact_heading,
        f"  - {leaderboard_line}",
        *candidate_refresh_fact_lines,
        "- **source / venue blockers 仍開啟**",
        f"  - `blocked_sparse_features={source_blockers.get('blocked_count', '—')}` / `{source_blockers.get('counts_by_history_class', {})}`",
        f"  - fin_netflow：{fin_line}",
        "  - venue：`live exchange credential / order ack lifecycle / fill lifecycle` 尚未有 runtime-backed proof",
        "- **Execution Console 快捷操作已 fail-closed（同步中 + blocker）**",
        "  - `manual_trade=paused_when_status_syncing_or_deployment_blocked` / `automation_enable=paused_when_status_syncing_or_deployment_blocked`；`/api/status` 初次同步前與阻塞期間都只保留查看阻塞原因與重新整理入口",
        "- **heartbeat current-state docs overwrite sync 已自動化**",
        "  - `scripts/hb_parallel_runner.py` 現在會在 `auto_propose_fixes.py` 後自動覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`",
        "  - 目的：避免 markdown docs 落後 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json`，讓 cron 心跳真正完成 docs overwrite 閉環",
        "",
        "---",
        "",
        "## Open Issues",
        "",
    ]

    for issue in issues:
        issues_lines.append(f"### {issue.get('priority', 'P?')}. {issue.get('title')}")
        for line in _issue_current_lines(
            issue,
            counts=counts,
            source_blockers=source_blockers,
            drift_diagnostics=drift_diagnostics,
            live_predictor_diagnostics=live_predictor_diagnostics,
            live_decision_drilldown=live_decision_drilldown,
            q15_support_audit=q15_support_audit,
            circuit_breaker_audit=circuit_breaker_audit,
            leaderboard_candidate_diagnostics=leaderboard_candidate_diagnostics,
        ):
            issues_lines.append(f"- {line}")
        issues_lines.append(f"- 下一步：{_issue_action_text(issue)}")
        verify_lines = _verification_lines(issue)
        if verify_lines:
            issues_lines.append("- 驗證：")
            issues_lines.extend([f"  - {item}" for item in verify_lines])
        issues_lines.append("")

    issues_lines.extend(
        [
            "---",
            "",
            "## Current Priority",
            current_priority_line1,
            "2. **持續沿 recent canonical pathological slice 追根因，不要 generic 化 blocker**",
            current_priority_line3,
            "4. **讓 heartbeat 自動 overwrite sync current-state docs，不再把 docs drift 留給人工補寫**",
            "",
        ]
    )

    support_success_status = patch_status
    support_success_verdict = support_route_verdict
    support_truth_ratio = f"{support_current_rows}/{support_minimum_rows}"

    roadmap_lines = [
        "# ROADMAP.md — Current Plan Only",
        "",
        f"_最後更新：{updated_at}_",
        "",
        "只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。",
        "",
        "---",
        "",
        "## 已完成",
        f"- **{heartbeat_mode_label} #{run_label} {completion_phrase}**",
        f"  - {counts_line}",
        f"  - 歷史覆蓋確認：{history_line}",
        f"  - {blocker_line}",
        f"  - {pathology_line}",
        *([f"  - {blocking_pathology_line}"] if blocking_pathology_line else []),
        "- **current-state docs overwrite sync 已自動化**",
        "  - heartbeat runner 會在 `auto_propose_fixes.py` 後直接覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`",
        "  - 這條 lane 的目的不是美化文件，而是避免 `issues.json / live artifacts` 已更新、markdown docs 卻仍停在舊 truth 的治理裂縫",
        "- **Execution Console 快捷操作已 fail-closed（同步中 + blocker）**",
        "  - `/api/status` 初次同步前或 deployment blocker 存在時，買入 / 減碼 / 啟用自動模式快捷操作都顯示暫停並保持 disabled，只留下查看阻塞原因與重新整理",
        "- **本輪 current-state docs 已同步到最新 artifacts**",
        "  - docs 與 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json` 的 current-state truth 已對齊",
        "",
        "---",
        "",
        "## 主目標",
        "",
        goal_a_title,
        "**目前真相**",
        f"- {blocker_line}",
        f"- {support_line}",
        *support_progress_doc_lines,
        "**成功標準**",
        goal_a_success,
        f"- {support_scope_label} truth (`bucket / rows / minimum / gap / support route`) 仍在 top-level surfaces 可 machine-read。",
        "",
        "### 目標 B：持續把 recent canonical blocker pocket 當成 current blocker 根因來鑽",
        "**目前真相**",
        f"- {pathology_line}",
        *([f"- {blocking_pathology_line}"] if blocking_pathology_line else []),
        "**成功標準**",
        "- drift / probe / docs 能同時指出 latest recent-window diagnostics 與 current blocker pocket，而不是退回 generic leaderboard / venue 摘要。",
        "",
        goal_c_title,
        "**目前真相**",
        f"- {support_line}",
        *support_progress_doc_lines,
        f"- {patch_context['docs_line']}",
        *([f"- {q35_scaling_doc_line}"] if q35_scaling_doc_line else []),
        "**成功標準**",
        _support_goal_success_line(
            support_scope_label,
            support_route_verdict,
            support_current_rows,
            support_minimum_rows,
            deployment_blocker,
        ),
        "",
        "### 目標 D：維持 leaderboard、venue/source blockers 與 docs automation 一致 product truth",
        "**目前真相**",
        f"- {leaderboard_line}",
        *candidate_refresh_goal_lines,
        f"- fin_netflow：{fin_line}",
        "- venue blockers：`live exchange credential / order ack lifecycle / fill lifecycle` 仍未驗證",
        "- docs automation：markdown docs 不再允許落後 live artifacts",
        "**成功標準**",
        "- Strategy Lab 不回退 placeholder-only；venue/source blockers 在 operator-facing surfaces 維持可見；docs automation 每輪心跳都自動完成 overwrite sync。",
        "",
        "---",
        "",
        "## 下一輪 gate",
        next_gate_line1,
        "   - 驗證：browser `/`、browser `/execution`（含初次同步時買入 / 減碼 / 自動模式暫停）、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`",
        next_gate_line1_blocker,
        "2. **持續鑽 recent canonical pathological slice，而不是 generic 化 root cause**",
        "   - 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`",
        "   - 升級 blocker：若 drift artifact 再失去 target-path / adverse-streak / top-shift 證據",
        next_gate_line3,
        "   - 驗證：browser `/lab`、`curl http://127.0.0.1:<active-backend>/api/models/leaderboard`（依 `/health` 選 8000/8001 健康 lane，不要硬綁單一 port）、`data/q15_support_audit.json`、`data/execution_metadata_smoke.json`、下輪 heartbeat docs sync status",
        next_gate_line3_blocker,
        "",
        "---",
        "",
        "## 成功標準",
        success_primary_line,
        f"- {support_truth_label} 維持：**{support_truth_ratio} + {support_success_verdict} + {support_success_status}**",
        "- recent canonical diagnostics 與 current blocker pocket 需同步可見，不被 generic 問題稀釋",
        f"- {leaderboard_governance_label} 維持；venue/source blockers 持續可見",
        "- heartbeat runner 每輪自動完成：**issue 對齊 → patch/automation lane → verify artifacts → docs overwrite sync**",
        "",
    ]

    live_regime = live_predictor_diagnostics.get("regime_label") or "—"
    live_gate = live_predictor_diagnostics.get("regime_gate") or "—"
    live_bucket = live_predictor_diagnostics.get("current_live_structure_bucket") or "—"
    docs_sync_line = "current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth；`/execution` 快捷列已補上 `/api/status` 初次同步 fail-closed，避免 current-live truth 未到前送出買入 / 減碼 / 啟用自動模式"

    orid_lines = [
        "# ORID_DECISIONS.md — Current ORID Only",
        "",
        f"_最後更新：{updated_at}_",
        "",
        "---",
        "",
        f"## 心跳 #{run_label} ORID",
        "",
        "### O｜客觀事實",
        f"- {orid_completion_phrase}：{counts_line}；歷史覆蓋確認：{history_line}；`simulated_pyramid_win={_format_pct_for_docs(counts.get('simulated_pyramid_win_rate'), 2)}`。",
        f"- current-live blocker：{blocker_line}。",
        f"- {support_scope_label} truth：{support_line}。",
        *[f"- {line}。" for line in support_progress_doc_lines],
        f"- latest recent-window diagnostics：{pathology_line}。",
        *([f"- current blocking pathological pocket：{blocking_pathology_line}。"] if blocking_pathology_line else []),
        f"- leaderboard / governance：{leaderboard_line}。",
        f"- source / venue blockers：`blocked_sparse_features={source_blockers.get('blocked_count', '—')}`；fin_netflow={fin_line}；venue proof 仍缺 credential / order ack / fill lifecycle。",
        *([f"- {q35_scaling_doc_line}。"] if q35_scaling_doc_line else []),
        f"- 本輪產品化前進：{docs_sync_line}；`recommended_patch={patch_profile}` / `status={patch_status}` / `reference_scope={patch_reference_scope}`。",
        "",
        "### R｜感受直覺",
        orid_reflection_line,
        f"- current live 已落在 `{live_regime}/{live_gate}/{live_bucket}`；如果 UI / docs 沒同步 latest artifacts，operator 很容易把 spillover pocket、舊 bucket，或 `/api/status` 尚未返回的 loading 狀態誤讀成可操作 runtime 真相。",
        "",
        "### I｜意義洞察",
        support_orid_insight_line,
        orid_insight2,
        f"3. **docs overwrite sync 的角色是護欄，不是主 blocker**：{docs_sync_line} 讓 operator-facing surfaces 與 machine-readable artifacts 保持同輪收斂。",
        "",
        "### D｜決策行動",
        "- **Owner**：current-live runtime / governance lane",
        orid_action_line.rstrip("。") + "；`/execution` 操作入口在 syncing / blocked 兩種狀態都必須 fail-closed。",
        "- **Artifacts**：`ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md`、`data/live_predict_probe.json`、`data/live_decision_quality_drilldown.json`、`data/recent_drift_report.json`。",
        "- **Verify**：browser `/`、browser `/execution`（同步中 / blocked 快捷操作 fail-closed）、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、`python scripts/recent_drift_report.py`。",
        orid_fail_line,
        "",
    ]

    docs_to_write = {
        Path(PROJECT_ROOT) / "ISSUES.md": "\n".join(issues_lines).rstrip() + "\n",
        Path(PROJECT_ROOT) / "ROADMAP.md": "\n".join(roadmap_lines).rstrip() + "\n",
        Path(PROJECT_ROOT) / "ORID_DECISIONS.md": "\n".join(orid_lines).rstrip() + "\n",
    }

    written_docs: list[str] = []
    errors: list[str] = []
    for path, content in docs_to_write.items():
        try:
            path.write_text(content, encoding="utf-8")
            written_docs.append(path.name)
        except Exception as exc:
            errors.append(f"{path.name}: {exc}")

    return {
        "success": not errors,
        "written_docs": written_docs,
        "errors": errors,
    }


def _artifact_timestamp_from_payload(payload: Dict[str, Any] | None, artifact_path: str | Path | None) -> datetime | None:
    payload = payload or {}
    for key in ("generated_at", "alignment_evaluated_at"):
        parsed = _safe_parse_datetime(payload.get(key))
        if parsed is not None:
            return parsed
    return _file_mtime(artifact_path)


def _stale_dependency_paths(
    artifact_time: datetime | None,
    dependency_paths: list[str | Path] | None,
) -> list[Path]:
    if artifact_time is None:
        return [Path(dep) for dep in (dependency_paths or [])]
    stale: list[Path] = []
    for dep in dependency_paths or []:
        dep_path = Path(dep)
        dep_mtime = _file_mtime(dep_path)
        if dep_mtime is not None and dep_mtime > artifact_time:
            stale.append(dep_path)
    return stale



def _artifact_is_newer_than_dependencies(
    artifact_time: datetime | None,
    dependency_paths: list[str | Path] | None,
) -> bool:
    return not _stale_dependency_paths(artifact_time, dependency_paths)



def _refresh_leaderboard_candidate_alignment_snapshot(
    artifact_path: Path,
    *,
    allow_rebuild: bool = True,
) -> Dict[str, Any] | None:
    try:
        from scripts import hb_leaderboard_candidate_probe as leaderboard_probe
    except Exception:
        leaderboard_probe = None

    if leaderboard_probe is not None:
        try:
            rebuilt = leaderboard_probe.build_probe_result(allow_rebuild=allow_rebuild)
        except Exception:
            rebuilt = None
        if rebuilt:
            artifact_path.write_text(json.dumps(rebuilt, ensure_ascii=False, indent=2), encoding="utf-8")
            return rebuilt

    payload = _read_json_file(artifact_path)
    if not payload:
        return None
    top_model = payload.get("top_model") or {}
    if not isinstance(top_model, dict) or not top_model:
        return None
    if leaderboard_probe is None:
        return None

    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        alignment = leaderboard_probe._build_alignment(
            top_model,
            leaderboard_snapshot_created_at=payload.get("leaderboard_snapshot_created_at"),
            alignment_evaluated_at=now_iso,
        )
    except Exception:
        return None

    payload["generated_at"] = now_iso
    payload["alignment"] = alignment
    artifact_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload



def _current_canonical_label_signature() -> Dict[str, Any]:
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            """
            SELECT COUNT(*) AS row_count, MAX(timestamp) AS latest_timestamp
            FROM labels
            WHERE horizon_minutes = ?
              AND simulated_pyramid_win IS NOT NULL
            """,
            (1440,),
        ).fetchone()
    finally:
        conn.close()
    row_count = int(row[0] or 0) if row else 0
    latest_timestamp = row[1] if row else None
    return {
        "label_rows": row_count,
        "latest_label_timestamp": latest_timestamp,
    }


def _bounded_canonical_label_drift(
    source_meta: Dict[str, Any] | None,
    current_signature: Dict[str, Any] | None,
) -> Dict[str, Any] | None:
    source_meta = source_meta or {}
    current_signature = current_signature or {}
    if source_meta.get("horizon_minutes") != 1440:
        return None
    if source_meta.get("target_col") != "simulated_pyramid_win":
        return None

    try:
        source_rows = int(source_meta.get("label_rows") or 0)
        current_rows = int(current_signature.get("label_rows") or 0)
    except (TypeError, ValueError):
        return None

    row_delta = current_rows - source_rows
    if row_delta < 0 or row_delta > FAST_CACHE_REUSE_MAX_LABEL_DELTA:
        return None

    source_ts = _safe_parse_datetime(source_meta.get("latest_label_timestamp"))
    current_ts = _safe_parse_datetime(current_signature.get("latest_label_timestamp"))
    if source_ts is None or current_ts is None or current_ts < source_ts:
        return None

    time_delta_seconds = (current_ts - source_ts).total_seconds()
    if time_delta_seconds > FAST_CACHE_REUSE_MAX_LABEL_TIME_DRIFT_SECONDS:
        return None

    return {
        "row_delta": row_delta,
        "time_delta_seconds": round(time_delta_seconds, 1),
        "source_label_rows": source_rows,
        "current_label_rows": current_rows,
        "source_latest_label_timestamp": source_meta.get("latest_label_timestamp"),
        "current_latest_label_timestamp": current_signature.get("latest_label_timestamp"),
    }


def _bull_pocket_semantic_signature_from_live_context(live_context: Dict[str, Any] | None) -> Dict[str, Any] | None:
    live_context = live_context or {}
    if not isinstance(live_context, dict):
        return None
    current_live_structure_bucket = live_context.get("current_live_structure_bucket")
    regime_gate = live_context.get("regime_gate")
    entry_quality_label = live_context.get("entry_quality_label")
    if current_live_structure_bucket is None and regime_gate is None and entry_quality_label is None:
        return None

    exact_scope_metrics = live_context.get("exact_scope_metrics") or {}
    exact_scope_rows = live_context.get("exact_scope_rows")
    if exact_scope_rows is None and isinstance(exact_scope_metrics, dict):
        exact_scope_rows = exact_scope_metrics.get("rows")

    current_live_structure_bucket_rows = int(live_context.get("current_live_structure_bucket_rows") or 0)
    exact_scope_rows_int = int(exact_scope_rows or 0)
    if current_live_structure_bucket_rows == 0 and exact_scope_rows_int == 0:
        entry_quality_label = None

    return {
        "regime_label": live_context.get("regime_label"),
        "regime_gate": regime_gate,
        "entry_quality_label": entry_quality_label,
        "decision_quality_label": live_context.get("decision_quality_label"),
        "current_live_structure_bucket": current_live_structure_bucket,
        "current_live_structure_bucket_rows": current_live_structure_bucket_rows,
        "exact_scope_rows": exact_scope_rows_int,
        "execution_guardrail_reason": live_context.get("execution_guardrail_reason"),
        "decision_quality_calibration_scope": live_context.get("decision_quality_calibration_scope"),
    }


def _current_bull_pocket_semantic_signature() -> Dict[str, Any] | None:
    live_probe = _read_json_file(Path(PROJECT_ROOT) / "data" / "live_predict_probe.json")
    if not live_probe:
        return None
    exact_scope = (live_probe.get("decision_quality_scope_diagnostics") or {}).get(
        "regime_label+regime_gate+entry_quality_label"
    ) or {}
    return _bull_pocket_semantic_signature_from_live_context(
        {
            "regime_label": live_probe.get("regime_label"),
            "regime_gate": live_probe.get("regime_gate"),
            "entry_quality_label": live_probe.get("entry_quality_label"),
            "decision_quality_label": live_probe.get("decision_quality_label"),
            "current_live_structure_bucket": live_probe.get("current_live_structure_bucket") or live_probe.get("structure_bucket"),
            "current_live_structure_bucket_rows": live_probe.get("current_live_structure_bucket_rows"),
            "exact_scope_rows": exact_scope.get("rows"),
            "execution_guardrail_reason": live_probe.get("execution_guardrail_reason"),
            "decision_quality_calibration_scope": live_probe.get("decision_quality_calibration_scope"),
        }
    )


def _recent_drift_cache_hit() -> Dict[str, Any] | None:
    artifact_path = Path(PROJECT_ROOT) / "data" / "recent_drift_report.json"
    if not artifact_path.exists():
        return None
    try:
        payload = json.loads(artifact_path.read_text())
    except Exception:
        return None
    source_meta = payload.get("source_meta") or {}
    current_signature = _current_canonical_label_signature()
    if source_meta != current_signature:
        return None
    artifact_time = _artifact_timestamp_from_payload(payload, artifact_path)
    dependency_paths = [
        Path(PROJECT_ROOT) / "scripts" / "recent_drift_report.py",
    ]
    if not _artifact_is_newer_than_dependencies(artifact_time, dependency_paths):
        return None
    return {
        "artifact_path": str(artifact_path),
        "reason": "fresh_recent_drift_artifact_reused",
        "details": current_signature,
    }


def _artifact_cache_hit_from_dependencies(
    *,
    artifact_relpath: str,
    reason: str,
    dependency_paths: list[str | Path],
    detail_builder=None,
) -> Dict[str, Any] | None:
    artifact_path = Path(PROJECT_ROOT) / artifact_relpath
    if not artifact_path.exists():
        return None
    try:
        payload = json.loads(artifact_path.read_text())
    except Exception:
        return None
    artifact_time = _artifact_timestamp_from_payload(payload, artifact_path)
    if not _artifact_is_newer_than_dependencies(artifact_time, dependency_paths):
        return None
    details = detail_builder(payload) if callable(detail_builder) else {}
    return {
        "artifact_path": str(artifact_path),
        "reason": reason,
        "details": details or {},
    }


def _latest_feature_timestamp() -> str | None:
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute("SELECT MAX(timestamp) FROM features_normalized").fetchone()
    finally:
        conn.close()
    return row[0] if row else None


def _read_json_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text())
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _leaderboard_candidate_semantic_signature(payload: Dict[str, Any]) -> Dict[str, Any] | None:
    alignment = payload.get("alignment") or {}
    if not isinstance(alignment, dict) or alignment.get("current_alignment_inputs_stale"):
        return None
    return {
        "global_recommended_profile": alignment.get("global_recommended_profile"),
        "train_selected_profile": alignment.get("train_selected_profile"),
        "train_selected_profile_source": alignment.get("train_selected_profile_source"),
        "support_governance_route": alignment.get("support_governance_route"),
        "minimum_support_rows": int(alignment.get("minimum_support_rows") or 0),
        "live_current_structure_bucket": alignment.get("live_current_structure_bucket"),
        "live_current_structure_bucket_rows": int(alignment.get("live_current_structure_bucket_rows") or 0),
        "live_execution_guardrail_reason": alignment.get("live_execution_guardrail_reason"),
        "live_regime_gate": alignment.get("live_regime_gate"),
        "live_entry_quality_label": alignment.get("live_entry_quality_label"),
    }



def _current_leaderboard_candidate_semantic_signature() -> Dict[str, Any]:
    data_dir = Path(PROJECT_ROOT) / "data"
    model_dir = Path(PROJECT_ROOT) / "model"
    feature_ablation = _read_json_file(data_dir / "feature_group_ablation.json")
    bull_pocket = _read_json_file(data_dir / "bull_4h_pocket_ablation.json")
    q15_support = _read_json_file(data_dir / "q15_support_audit.json")
    live_probe = _read_json_file(data_dir / "live_predict_probe.json")
    last_metrics = _read_json_file(model_dir / "last_metrics.json")
    live_context = bull_pocket.get("live_context") or {}
    support_route = q15_support.get("support_route") or {}
    current_live = q15_support.get("current_live") or {}
    deployment_blocker_details = live_probe.get("deployment_blocker_details") or {}
    feature_profile_source = last_metrics.get("feature_profile_source") or (last_metrics.get("feature_profile_meta") or {}).get("source")

    live_current_structure_bucket = (
        live_probe.get("current_live_structure_bucket")
        or live_probe.get("structure_bucket")
        or live_context.get("current_live_structure_bucket")
        or current_live.get("current_live_structure_bucket")
    )
    live_current_structure_bucket_rows = live_probe.get("current_live_structure_bucket_rows")
    if live_current_structure_bucket_rows is None:
        live_current_structure_bucket_rows = live_context.get("current_live_structure_bucket_rows")
    if live_current_structure_bucket_rows is None:
        live_current_structure_bucket_rows = current_live.get("current_live_structure_bucket_rows")

    minimum_support_rows = live_probe.get("minimum_support_rows")
    if minimum_support_rows is None:
        minimum_support_rows = deployment_blocker_details.get("minimum_support_rows")
    if minimum_support_rows is None:
        minimum_support_rows = live_context.get("minimum_support_rows")
    if minimum_support_rows is None:
        minimum_support_rows = support_route.get("minimum_support_rows")

    support_governance_route = (
        live_probe.get("support_governance_route")
        or deployment_blocker_details.get("support_governance_route")
        or support_route.get("support_governance_route")
    )

    return {
        "global_recommended_profile": feature_ablation.get("recommended_profile"),
        "train_selected_profile": last_metrics.get("feature_profile"),
        "train_selected_profile_source": feature_profile_source,
        "support_governance_route": support_governance_route,
        "minimum_support_rows": int(minimum_support_rows or 0),
        "live_current_structure_bucket": live_current_structure_bucket,
        "live_current_structure_bucket_rows": int(live_current_structure_bucket_rows or 0),
        "live_execution_guardrail_reason": live_probe.get("execution_guardrail_reason"),
        "live_regime_gate": live_probe.get("regime_gate"),
        "live_entry_quality_label": live_probe.get("entry_quality_label"),
    }


def _q35_scaling_cache_hit() -> Dict[str, Any] | None:
    artifact_path = Path(PROJECT_ROOT) / "data" / "q35_scaling_audit.json"
    if not artifact_path.exists():
        return None
    try:
        payload = json.loads(artifact_path.read_text())
    except Exception:
        return None
    current_live = payload.get("current_live") or {}
    if current_live.get("timestamp") != _latest_feature_timestamp():
        return None
    artifact_time = _artifact_timestamp_from_payload(payload, artifact_path)
    dependency_paths = [
        Path(PROJECT_ROOT) / "scripts" / "hb_q35_scaling_audit.py",
        Path(PROJECT_ROOT) / "model" / "predictor.py",
        Path(PROJECT_ROOT) / "model" / "q35_bias50_calibration.py",
    ]
    if not _artifact_is_newer_than_dependencies(artifact_time, dependency_paths):
        return None
    return {
        "artifact_path": str(artifact_path),
        "reason": "fresh_q35_scaling_artifact_reused",
        "details": {
            "current_feature_timestamp": current_live.get("timestamp"),
            "structure_bucket": current_live.get("structure_bucket"),
        },
    }


def _leaderboard_candidate_cache_hit() -> Dict[str, Any] | None:
    artifact_path = Path(PROJECT_ROOT) / "data" / "leaderboard_feature_profile_probe.json"
    if not artifact_path.exists():
        return None
    payload = _read_json_file(artifact_path)
    if not payload:
        return None

    current_signature = _current_leaderboard_candidate_semantic_signature()
    artifact_signature = _leaderboard_candidate_semantic_signature(payload)
    dependency_paths = [
        Path(PROJECT_ROOT) / "scripts" / "hb_leaderboard_candidate_probe.py",
        Path(PROJECT_ROOT) / "server" / "routes" / "api.py",
        Path(PROJECT_ROOT) / "backtesting" / "model_leaderboard.py",
    ]
    cache_reason = "fresh_leaderboard_candidate_artifact_reused"
    refresh_applied = False

    def _attempt_refresh(*, allow_rebuild: bool = False) -> None:
        nonlocal payload, artifact_signature, cache_reason, refresh_applied
        try:
            refreshed_payload = _refresh_leaderboard_candidate_alignment_snapshot(
                artifact_path,
                allow_rebuild=allow_rebuild,
            )
        except TypeError:
            # Some tests monkeypatch the older one-argument helper shape.
            refreshed_payload = _refresh_leaderboard_candidate_alignment_snapshot(artifact_path)
        if refreshed_payload:
            payload = refreshed_payload
            artifact_signature = _leaderboard_candidate_semantic_signature(payload)
            refresh_applied = True
            cache_reason = "refreshed_leaderboard_candidate_artifact_reused"

    if artifact_signature != current_signature:
        _attempt_refresh()
    if artifact_signature is None or artifact_signature != current_signature:
        return None

    artifact_time = _artifact_timestamp_from_payload(payload, artifact_path)
    stale_dependencies = _stale_dependency_paths(artifact_time, dependency_paths)
    if stale_dependencies:
        _attempt_refresh()
        artifact_time = _artifact_timestamp_from_payload(payload, artifact_path)
        stale_dependencies = _stale_dependency_paths(artifact_time, dependency_paths)
    if stale_dependencies:
        return None

    return {
        "artifact_path": str(artifact_path),
        "reason": cache_reason,
        "details": {
            "generated_at": payload.get("generated_at"),
            "selected_feature_profile": ((payload.get("top_model") or {}).get("selected_feature_profile")),
            "semantic_signature": artifact_signature,
            "refresh_applied": refresh_applied,
            "leaderboard_payload_source": payload.get("leaderboard_payload_source"),
            "leaderboard_payload_updated_at": payload.get("leaderboard_payload_updated_at"),
        },
    }


def _feature_group_ablation_cache_hit() -> Dict[str, Any] | None:
    artifact_path = Path(PROJECT_ROOT) / "data" / "feature_group_ablation.json"
    if not artifact_path.exists():
        return None
    try:
        payload = json.loads(artifact_path.read_text())
    except Exception:
        return None

    source_meta = payload.get("source_meta") or {}
    current_signature = _current_canonical_label_signature()
    if source_meta:
        label_drift = _bounded_canonical_label_drift(source_meta, current_signature)
        expected_signature = {
            "label_rows": current_signature.get("label_rows"),
            "latest_label_timestamp": current_signature.get("latest_label_timestamp"),
            "horizon_minutes": 1440,
            "target_col": "simulated_pyramid_win",
        }
        if source_meta != expected_signature and label_drift is None:
            return None
        dependency_paths = [
            Path(PROJECT_ROOT) / "scripts" / "feature_group_ablation.py",
            Path(PROJECT_ROOT) / "model" / "train.py",
            Path(PROJECT_ROOT) / "database" / "models.py",
        ]
        artifact_time = _artifact_timestamp_from_payload(payload, artifact_path)
        if not _artifact_is_newer_than_dependencies(artifact_time, dependency_paths):
            return None
        return {
            "artifact_path": str(artifact_path),
            "reason": (
                "fresh_feature_group_ablation_artifact_reused"
                if source_meta == expected_signature
                else "bounded_label_drift_feature_group_ablation_artifact_reused"
            ),
            "details": {
                "generated_at": payload.get("generated_at"),
                "recommended_profile": payload.get("recommended_profile"),
                "recent_rows": payload.get("recent_rows"),
                "source_meta": source_meta,
                "label_drift": label_drift,
            },
        }

    return _artifact_cache_hit_from_dependencies(
        artifact_relpath="data/feature_group_ablation.json",
        reason="fresh_feature_group_ablation_artifact_reused",
        dependency_paths=[
            Path(PROJECT_ROOT) / "scripts" / "feature_group_ablation.py",
            Path(PROJECT_ROOT) / "model" / "train.py",
            Path(PROJECT_ROOT) / "database" / "models.py",
            Path(DB_PATH),
        ],
        detail_builder=lambda legacy_payload: {
            "generated_at": legacy_payload.get("generated_at"),
            "recommended_profile": legacy_payload.get("recommended_profile"),
            "recent_rows": legacy_payload.get("recent_rows"),
        },
    )


def _bull_4h_pocket_cache_hit() -> Dict[str, Any] | None:
    artifact_path = Path(PROJECT_ROOT) / "data" / "bull_4h_pocket_ablation.json"
    if not artifact_path.exists():
        return None

    payload = _read_json_file(artifact_path)
    if payload:
        source_meta = payload.get("source_meta") or {}
        artifact_live_signature = _bull_pocket_semantic_signature_from_live_context(payload.get("live_context") or {})
        current_live_signature = _current_bull_pocket_semantic_signature()
        current_signature = _current_canonical_label_signature()
        expected_signature = {
            "label_rows": current_signature.get("label_rows"),
            "latest_label_timestamp": current_signature.get("latest_label_timestamp"),
            "horizon_minutes": 1440,
            "target_col": "simulated_pyramid_win",
        }
        label_drift = _bounded_canonical_label_drift(source_meta, current_signature) if source_meta else None
        dependency_paths = [
            Path(PROJECT_ROOT) / "scripts" / "bull_4h_pocket_ablation.py",
            Path(PROJECT_ROOT) / "scripts" / "feature_group_ablation.py",
            Path(PROJECT_ROOT) / "model" / "predictor.py",
            Path(PROJECT_ROOT) / "model" / "train.py",
        ]
        artifact_time = _artifact_timestamp_from_payload(payload, artifact_path)
        can_reuse_semantically = (
            source_meta
            and artifact_live_signature is not None
            and current_live_signature is not None
            and artifact_live_signature == current_live_signature
            and (source_meta == expected_signature or label_drift is not None)
            and _artifact_is_newer_than_dependencies(artifact_time, dependency_paths)
        )
        if can_reuse_semantically:
            return {
                "artifact_path": str(artifact_path),
                "reason": (
                    "fresh_bull_4h_pocket_artifact_reused"
                    if source_meta == expected_signature
                    else "bounded_label_drift_bull_4h_pocket_artifact_reused"
                ),
                "details": {
                    "generated_at": payload.get("generated_at"),
                    "feature_timestamp": ((payload.get("live_context") or {}).get("feature_timestamp")),
                    "current_live_structure_bucket": ((payload.get("live_context") or {}).get("current_live_structure_bucket")),
                    "source_meta": source_meta,
                    "label_drift": label_drift,
                    "semantic_signature": artifact_live_signature,
                },
            }

        current_regime = str((current_live_signature or {}).get("regime_label") or "").strip().lower()
        if (
            current_regime
            and current_regime != "bull"
            and source_meta
            and (source_meta == expected_signature or label_drift is not None)
            and _artifact_is_newer_than_dependencies(artifact_time, dependency_paths)
        ):
            return {
                "artifact_path": str(artifact_path),
                "reason": (
                    "fresh_non_bull_live_regime_reference_only_bull_4h_pocket_artifact_reused"
                    if source_meta == expected_signature
                    else "bounded_label_drift_non_bull_live_regime_reference_only_bull_4h_pocket_artifact_reused"
                ),
                "details": {
                    "generated_at": payload.get("generated_at"),
                    "feature_timestamp": ((payload.get("live_context") or {}).get("feature_timestamp")),
                    "current_live_structure_bucket": ((payload.get("live_context") or {}).get("current_live_structure_bucket")),
                    "source_meta": source_meta,
                    "label_drift": label_drift,
                    "semantic_signature": artifact_live_signature,
                    "current_live_signature": current_live_signature,
                    "reference_only": True,
                    "reason": "current live regime is not bull, so keep bull 4H pocket ablation as reference-only instead of forcing a fast-mode rerun.",
                },
            }

    return _artifact_cache_hit_from_dependencies(
        artifact_relpath="data/bull_4h_pocket_ablation.json",
        reason="fresh_bull_4h_pocket_artifact_reused",
        dependency_paths=[
            Path(PROJECT_ROOT) / "scripts" / "bull_4h_pocket_ablation.py",
            Path(PROJECT_ROOT) / "scripts" / "feature_group_ablation.py",
            Path(PROJECT_ROOT) / "model" / "predictor.py",
            Path(PROJECT_ROOT) / "model" / "train.py",
            Path(PROJECT_ROOT) / "data" / "feature_group_ablation.json",
            Path(PROJECT_ROOT) / "data" / "live_predict_probe.json",
            Path(DB_PATH),
        ],
        detail_builder=lambda payload: {
            "generated_at": payload.get("generated_at"),
            "feature_timestamp": ((payload.get("live_context") or {}).get("feature_timestamp")),
            "current_live_structure_bucket": ((payload.get("live_context") or {}).get("current_live_structure_bucket")),
        },
    )


def _q15_support_cache_hit() -> Dict[str, Any] | None:
    return _artifact_cache_hit_from_dependencies(
        artifact_relpath="data/q15_support_audit.json",
        reason="fresh_q15_support_artifact_reused",
        dependency_paths=[
            Path(PROJECT_ROOT) / "scripts" / "hb_q15_support_audit.py",
            Path(PROJECT_ROOT) / "data" / "live_predict_probe.json",
            Path(PROJECT_ROOT) / "data" / "live_decision_quality_drilldown.json",
            Path(PROJECT_ROOT) / "data" / "bull_4h_pocket_ablation.json",
            Path(PROJECT_ROOT) / "data" / "leaderboard_feature_profile_probe.json",
        ],
        detail_builder=lambda payload: {
            "generated_at": payload.get("generated_at"),
            "current_live_structure_bucket": ((payload.get("current_live") or {}).get("current_live_structure_bucket")),
            "support_route_verdict": ((payload.get("support_route") or {}).get("verdict")),
        },
    )


def _q15_bucket_root_cause_cache_hit() -> Dict[str, Any] | None:
    return _artifact_cache_hit_from_dependencies(
        artifact_relpath="data/q15_bucket_root_cause.json",
        reason="fresh_q15_bucket_root_cause_artifact_reused",
        dependency_paths=[
            Path(PROJECT_ROOT) / "scripts" / "hb_q15_bucket_root_cause.py",
            Path(PROJECT_ROOT) / "scripts" / "feature_group_ablation.py",
            Path(PROJECT_ROOT) / "scripts" / "bull_4h_pocket_ablation.py",
            Path(PROJECT_ROOT) / "data" / "live_predict_probe.json",
            Path(PROJECT_ROOT) / "data" / "live_decision_quality_drilldown.json",
            Path(PROJECT_ROOT) / "data" / "bull_4h_pocket_ablation.json",
        ],
        detail_builder=lambda payload: {
            "generated_at": payload.get("generated_at"),
            "verdict": payload.get("verdict"),
            "candidate_patch_feature": payload.get("candidate_patch_feature"),
        },
    )


def _q15_boundary_replay_cache_hit() -> Dict[str, Any] | None:
    return _artifact_cache_hit_from_dependencies(
        artifact_relpath="data/q15_boundary_replay.json",
        reason="fresh_q15_boundary_replay_artifact_reused",
        dependency_paths=[
            Path(PROJECT_ROOT) / "scripts" / "hb_q15_boundary_replay.py",
            Path(PROJECT_ROOT) / "data" / "live_predict_probe.json",
            Path(PROJECT_ROOT) / "data" / "q15_support_audit.json",
            Path(PROJECT_ROOT) / "data" / "q15_bucket_root_cause.json",
        ],
        detail_builder=lambda payload: {
            "generated_at": payload.get("generated_at"),
            "verdict": payload.get("verdict"),
            "replay_bucket": ((payload.get("boundary_replay") or {}).get("replay_bucket")),
        },
    )


def _get_serial_cache_hit(command_name: str) -> Dict[str, Any] | None:
    # Candidate-evaluation artifacts are intentionally reusable outside fast mode
    # when their semantic source signature is still current or within the bounded
    # label-drift guardrail. This keeps full heartbeat training preflight from
    # stalling the whole run on expensive candidate scans that would reproduce
    # the same governance input.
    if command_name == "feature_group_ablation":
        return _feature_group_ablation_cache_hit()
    if command_name == "bull_4h_pocket_ablation":
        return _bull_4h_pocket_cache_hit()
    if command_name == "hb_leaderboard_candidate_probe":
        return _leaderboard_candidate_cache_hit()

    if not _CURRENT_HEARTBEAT_FAST_MODE:
        return None
    if command_name == "recent_drift_report":
        return _recent_drift_cache_hit()
    if command_name == "hb_q35_scaling_audit":
        return _q35_scaling_cache_hit()
    if command_name == "hb_q15_support_audit":
        return _q15_support_cache_hit()
    if command_name == "hb_q15_bucket_root_cause":
        return _q15_bucket_root_cause_cache_hit()
    if command_name == "hb_q15_boundary_replay":
        return _q15_boundary_replay_cache_hit()
    return None


def _get_fast_serial_cache_hit(command_name: str) -> Dict[str, Any] | None:
    if not _CURRENT_HEARTBEAT_FAST_MODE:
        return None
    return _get_serial_cache_hit(command_name)


def _build_cached_serial_result(command_name: str, cache_hit: Dict[str, Any]) -> Dict[str, Any]:
    artifact_path = cache_hit.get("artifact_path")
    return {
        "attempted": False,
        "success": True,
        "returncode": 0,
        "stdout": "",
        "stderr": "",
        "command": [command_name],
        "cached": True,
        "cache_reason": cache_hit.get("reason"),
        "cache_details": cache_hit.get("details") or {},
        "artifact_path": artifact_path,
    }


def _build_skipped_serial_result(
    command_name: str,
    *,
    reason: str,
    artifact_path: str | Path | None = None,
) -> Dict[str, Any]:
    return {
        "attempted": False,
        "success": True,
        "returncode": None,
        "stdout": "",
        "stderr": "",
        "command": [command_name],
        "skipped": True,
        "skip_reason": reason,
        "artifact_path": str(artifact_path) if artifact_path else None,
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--hb", type=str, required=False, help="Heartbeat label. Required for full runs; optional in --fast mode.")
    parser.add_argument("--fast", action="store_true", help="Quick diagnostic mode for cron. If --hb is omitted, uses the label 'fast'.")
    parser.add_argument(
        "--fast-refresh-candidates",
        action="store_true",
        help=(
            "In fast mode, also rerun candidate-evaluation lanes "
            "(feature_group_ablation / bull_4h_pocket_ablation / hb_leaderboard_candidate_probe). "
            "Default fast mode reuses existing candidate artifacts instead."
        ),
    )
    parser.add_argument("--no-train", action="store_true")
    parser.add_argument("--no-dw", action="store_true")
    parser.add_argument("--no-collect", action="store_true", help="Skip heartbeat data collection before diagnostics.")
    args = parser.parse_args(argv)
    if not args.fast and not args.hb:
        parser.error("--hb is required unless --fast is used")
    return args


def resolve_run_label(args) -> str:
    return args.hb or "fast"


def _tail_lines(lines: list[str], limit: int = 5) -> list[str]:
    if limit <= 0:
        return []
    return [line for line in lines[-limit:] if line.strip()]


class _StreamCollector(threading.Thread):
    def __init__(self, stream, sink: list[str]):
        super().__init__(daemon=True)
        self._stream = stream
        self._sink = sink

    def run(self) -> None:
        try:
            for line in iter(self._stream.readline, ""):
                if line == "":
                    break
                self._sink.append(line)
        finally:
            try:
                self._stream.close()
            except Exception:
                pass


def _run_command_with_watchdog(
    cmd: list[str],
    *,
    timeout: int = 600,
    extra_env: Dict[str, str] | None = None,
    progress: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    env = {**os.environ, "PYTHONPATH": PROJECT_ROOT}
    if extra_env:
        env.update(extra_env)

    heartbeat_interval = int((progress or {}).get("heartbeat_interval_seconds", 15))
    poll_interval = float((progress or {}).get("poll_interval_seconds", 1.0))
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    start_monotonic = time.monotonic()
    next_heartbeat_at = start_monotonic + heartbeat_interval
    last_output_timestamp = start_monotonic
    last_output_count = 0
    heartbeat_count = 0

    process = subprocess.Popen(
        cmd,
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        bufsize=1,
    )
    stdout_thread = _StreamCollector(process.stdout, stdout_lines)
    stderr_thread = _StreamCollector(process.stderr, stderr_lines)
    stdout_thread.start()
    stderr_thread.start()

    try:
        while True:
            now = time.monotonic()
            returncode = process.poll()
            elapsed = round(now - start_monotonic, 1)
            total_output_count = len(stdout_lines) + len(stderr_lines)
            if total_output_count > last_output_count:
                last_output_timestamp = now
                last_output_count = total_output_count
            if returncode is not None:
                break
            if elapsed >= timeout:
                process.kill()
                stdout_thread.join(timeout=1)
                stderr_thread.join(timeout=1)
                stdout = "".join(stdout_lines).strip()
                stderr = "".join(stderr_lines).strip()
                return {
                    "attempted": True,
                    "success": False,
                    "returncode": -1,
                    "stdout": stdout,
                    "stderr": (stderr + "\n" if stderr else "") + f"TIMEOUT after {timeout}s",
                    "command": cmd,
                }

            if progress and now >= next_heartbeat_at:
                heartbeat_count += 1
                seconds_since_output = round(max(0.0, now - last_output_timestamp), 1)
                write_progress(
                    progress["run_label"],
                    progress["stage"],
                    details={
                        **(progress.get("details") or {}),
                        "command": cmd,
                        "pid": process.pid,
                        "elapsed_seconds": elapsed,
                        "heartbeat_count": heartbeat_count,
                        "stdout_line_count": len(stdout_lines),
                        "stderr_line_count": len(stderr_lines),
                        "stdout_tail": _tail_lines(stdout_lines),
                        "stderr_tail": _tail_lines(stderr_lines),
                        "seconds_since_new_output": seconds_since_output,
                    },
                )
                print(
                    f"⏱️  {progress.get('label', progress['stage'])} 執行中："
                    f"elapsed={elapsed}s pid={process.pid} "
                    f"stdout={len(stdout_lines)} stderr={len(stderr_lines)} "
                    f"silence={seconds_since_output}s"
                )
                next_heartbeat_at = now + heartbeat_interval
            time.sleep(poll_interval)
    finally:
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)

    stdout = "".join(stdout_lines).strip()
    stderr = "".join(stderr_lines).strip()
    return {
        "attempted": True,
        "success": process.returncode == 0,
        "returncode": process.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "command": cmd,
    }


def _resolve_parallel_task_timeout(task_name: str, *, fast_mode: bool | None = None) -> int:
    if fast_mode is None:
        fast_mode = _CURRENT_HEARTBEAT_FAST_MODE
    timeout_map = FAST_PARALLEL_TASK_TIMEOUTS if fast_mode else FULL_PARALLEL_TASK_TIMEOUTS
    return int(timeout_map.get(task_name, 180 if fast_mode else 240))


def run_task(task):
    try:
        timeout_seconds = int(task.get("timeout_seconds") or _resolve_parallel_task_timeout(task["name"]))
        result = _run_command_with_watchdog(task["cmd"], timeout=timeout_seconds)
        return (
            task["name"],
            result["success"],
            (result.get("stdout") or "").strip(),
            (result.get("stderr") or "").strip(),
            result.get("returncode"),
        )
    except Exception as e:
        return (task["name"], False, "", str(e), -1)


def quick_counts():
    conn = sqlite3.connect(DB_PATH)
    results = {}
    for t in ['raw_market_data', 'features_normalized', 'labels']:
        results[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    target_rate = conn.execute(
        "SELECT AVG(CAST(simulated_pyramid_win AS FLOAT)) FROM labels WHERE simulated_pyramid_win IS NOT NULL"
    ).fetchone()[0]
    results['simulated_pyramid_win_rate'] = round(target_rate, 4) if target_rate else 0
    results['latest_raw_timestamp'] = conn.execute("SELECT MAX(timestamp) FROM raw_market_data").fetchone()[0]
    conn.close()

    from config import load_config
    from database.models import init_db

    orm_session = init_db(load_config()["database"]["url"])
    try:
        results['label_horizons'] = [
            {
                'horizon_minutes': row['horizon_minutes'],
                'rows': row['total_rows'],
                'target_rows': row['target_rows'],
                'latest_target_timestamp': row['latest_target_ts'],
                'freshness': row['freshness'],
                'is_active': row['is_active'],
                'latest_raw_gap_hours': row['latest_raw_gap_hours'],
            }
            for row in summarize_label_horizons(orm_session)
        ]
    finally:
        orm_session.close()
    return results


def run_collect_step(skip: bool = False, run_label: str | None = None) -> Dict[str, Any]:
    if skip:
        return {
            "attempted": False,
            "success": True,
            "stdout": "",
            "stderr": "",
            "returncode": 0,
            "command": COLLECT_CMD,
        }

    try:
        effective_run_label = run_label or _CURRENT_HEARTBEAT_RUN_LABEL or "adhoc"
        return _run_command_with_watchdog(
            COLLECT_CMD,
            timeout=COLLECT_TIMEOUT_SECONDS,
            progress={
                "run_label": effective_run_label,
                "stage": "collect",
                "label": "hb_collect",
                "details": {"command_kind": "collect", "timeout_seconds": COLLECT_TIMEOUT_SECONDS},
            },
        )
    except Exception as exc:
        return {
            "attempted": True,
            "success": False,
            "stdout": "",
            "stderr": str(exc),
            "returncode": -1,
            "command": COLLECT_CMD,
        }


def collect_source_blockers() -> Dict[str, Any]:
    coverage_payload = compute_sqlite_feature_coverage(DB_PATH)
    blocker_summary = build_source_blocker_summary(coverage_payload)
    blocker_summary["coverage_rows_total"] = coverage_payload["rows_total"]
    blocker_summary["coverage_hidden_count"] = coverage_payload["hidden_count"]
    blocker_summary["coverage_usable_count"] = coverage_payload["usable_count"]
    return blocker_summary


def collect_ic_diagnostics() -> Dict[str, Any]:
    result_path = Path(PROJECT_ROOT) / "data" / "full_ic_result.json"
    if not result_path.exists():
        return {}
    try:
        payload = json.loads(result_path.read_text())
    except Exception:
        return {}
    return {
        "n": payload.get("n"),
        "global_pass": payload.get("global_pass"),
        "tw_pass": payload.get("tw_pass"),
        "total_features": payload.get("total_features"),
    }


def _resolve_serial_timeout(cmd: list[str], timeout: int | None) -> int:
    if timeout is not None:
        return timeout
    command_name = Path(cmd[1]).stem if len(cmd) > 1 else Path(cmd[0]).stem
    if _CURRENT_HEARTBEAT_FAST_MODE:
        return FAST_SERIAL_TIMEOUTS.get(command_name, 600)
    return FULL_SERIAL_TIMEOUTS.get(command_name, 600)


def _run_serial_command(
    cmd: list[str],
    timeout: int | None = None,
    extra_env: Dict[str, str] | None = None,
    *,
    progress: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    command_name = Path(cmd[1]).stem if len(cmd) > 1 else Path(cmd[0]).stem
    cache_hit = _get_serial_cache_hit(command_name) if timeout is None else None
    if cache_hit is not None:
        return _build_cached_serial_result(command_name, cache_hit)
    effective_timeout = _resolve_serial_timeout(cmd, timeout)
    effective_progress = progress
    if effective_progress is None and _CURRENT_HEARTBEAT_RUN_LABEL:
        effective_progress = {
            "run_label": _CURRENT_HEARTBEAT_RUN_LABEL,
            "stage": command_name,
            "label": command_name,
            "details": {
                "command_kind": "serial_command",
                "timeout_seconds": effective_timeout,
                "fast_mode_timeout": bool(_CURRENT_HEARTBEAT_FAST_MODE and timeout is None),
            },
        }
    try:
        return _run_command_with_watchdog(
            cmd,
            timeout=effective_timeout,
            extra_env=extra_env,
            progress=effective_progress,
        )
    except Exception as exc:
        return {
            "attempted": True,
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(exc),
            "command": cmd,
        }


def run_recent_drift_report() -> Dict[str, Any]:
    return _run_serial_command(DRIFT_REPORT_CMD)


def run_predict_probe() -> Dict[str, Any]:
    return _run_serial_command(PREDICT_PROBE_CMD)


def run_live_decision_quality_drilldown() -> Dict[str, Any]:
    return _run_serial_command(LIVE_DQ_DRILLDOWN_CMD)


def run_q35_scaling_audit() -> Dict[str, Any]:
    return _run_serial_command(Q35_SCALING_AUDIT_CMD)


def run_q15_support_audit() -> Dict[str, Any]:
    return _run_serial_command(Q15_SUPPORT_AUDIT_CMD)


def run_q15_bucket_root_cause() -> Dict[str, Any]:
    return _run_serial_command(Q15_BUCKET_ROOT_CAUSE_CMD)


def run_q15_boundary_replay() -> Dict[str, Any]:
    return _run_serial_command(Q15_BOUNDARY_REPLAY_CMD)


def run_circuit_breaker_audit(run_label: str) -> Dict[str, Any]:
    return _run_serial_command(CIRCUIT_BREAKER_AUDIT_CMD + [run_label])


def run_feature_group_ablation() -> Dict[str, Any]:
    return _run_serial_command(FEATURE_ABLATION_CMD)


def run_bull_4h_pocket_ablation() -> Dict[str, Any]:
    # Heartbeat cron runs use the bounded live-context refresh lane in both fast
    # and full modes. Full rebuild remains available by invoking
    # scripts/bull_4h_pocket_ablation.py manually, but the project-driver
    # heartbeat must not spend the whole budget on silent candidate grids.
    return _run_serial_command(BULL_4H_POCKET_ABLATION_REFRESH_CMD)


def refresh_train_prerequisites(needs_train: bool) -> Dict[str, Any]:
    """Refresh ablation artifacts before training so train.py consumes current governance inputs.

    Root cause fixed in Heartbeat #744: running train in parallel *before* refreshing
    feature-group / bull-pocket artifacts causes model/train.py to keep selecting a
    support-aware stale profile even after the exact-supported live bucket has recovered.
    """
    if not needs_train:
        return {}

    feature_ablation_result = run_feature_group_ablation()
    feature_ablation_summary = collect_feature_ablation_diagnostics()
    bull_pocket_result = run_bull_4h_pocket_ablation()
    bull_pocket_summary = collect_bull_4h_pocket_diagnostics()
    return {
        "feature_ablation_result": feature_ablation_result,
        "feature_ablation_summary": feature_ablation_summary,
        "bull_pocket_result": bull_pocket_result,
        "bull_pocket_summary": bull_pocket_summary,
    }


def run_leaderboard_candidate_probe(run_label: str | None = None) -> Dict[str, Any]:
    extra_env = {"HB_RUN_LABEL": str(run_label)} if run_label is not None else None
    return _run_serial_command(LEADERBOARD_CANDIDATE_PROBE_CMD, extra_env=extra_env)


def run_auto_propose(run_label: str | None = None) -> Dict[str, Any]:
    extra_env = {"HB_RUN_LABEL": str(run_label)} if run_label is not None else None
    return _run_serial_command(AUTO_PROPOSE_CMD, extra_env=extra_env)


def parse_collect_metadata(stdout: str) -> Dict[str, Any]:
    match = re.search(r"CONTINUITY_REPAIR_META:\s*(\{.*\})", stdout or "")
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}


def compute_bridge_fallback_streak(current_meta: Dict[str, Any], summaries_dir: str | None = None) -> int:
    if not current_meta.get("used_bridge"):
        return 0

    summaries_path = Path(summaries_dir or (Path(PROJECT_ROOT) / "data"))
    summary_files = sorted(summaries_path.glob("heartbeat_*_summary.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    streak = 1
    current_name = f"heartbeat_{current_meta.get('heartbeat', '')}_summary.json"
    for path in summary_files:
        if path.name == current_name:
            continue
        try:
            payload = json.loads(path.read_text())
        except Exception:
            continue
        prev_meta = (payload.get("collect_result") or {}).get("continuity_repair") or {}
        if prev_meta.get("used_bridge"):
            streak += 1
            continue
        break
    return streak


def progress_artifact_path(run_label: str) -> Path:
    return Path(PROJECT_ROOT) / "data" / f"heartbeat_{run_label}_progress.json"


def write_progress(
    run_label: str,
    stage: str,
    *,
    status: str = "running",
    details: Dict[str, Any] | None = None,
) -> Path:
    path = progress_artifact_path(run_label)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "heartbeat": run_label,
        "stage": stage,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pid": os.getpid(),
        "details": details or {},
    }
    path.write_text(json.dumps(payload, indent=2, default=str))
    return path


def _artifact_recency_snapshot(
    artifact_path: str | Path | None,
    diagnostics: Dict[str, Any] | None = None,
    *,
    now: datetime | None = None,
) -> Dict[str, Any]:
    if not artifact_path:
        return {}
    path = Path(artifact_path)
    snapshot: Dict[str, Any] = {
        "artifact_path": str(path),
        "artifact_exists": path.exists(),
    }
    generated_at = None
    diagnostics = diagnostics or {}
    if isinstance(diagnostics, dict):
        generated_at = diagnostics.get("generated_at")
    if generated_at:
        snapshot["artifact_generated_at"] = generated_at
        try:
            generated_dt = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
            ref_now = now or datetime.now(timezone.utc)
            if generated_dt.tzinfo is None:
                generated_dt = generated_dt.replace(tzinfo=timezone.utc)
            snapshot["artifact_age_seconds"] = round(max((ref_now - generated_dt).total_seconds(), 0.0), 1)
        except Exception:
            pass
    if path.exists():
        try:
            snapshot["artifact_mtime"] = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
        except Exception:
            pass
    return snapshot


def _build_serial_result_summary(
    name: str,
    result: Dict[str, Any] | None,
    *,
    diagnostics: Dict[str, Any] | None = None,
    artifact_path: str | Path | None = None,
    now: datetime | None = None,
) -> Dict[str, Any]:
    result = result or {}
    diagnostics = diagnostics or {}
    effective_artifact_path = artifact_path or result.get("artifact_path")
    timed_out = result.get("returncode") == -1 and "TIMEOUT after" in str(result.get("stderr") or "")
    artifact_snapshot = _artifact_recency_snapshot(effective_artifact_path, diagnostics, now=now)
    artifact_exists = artifact_snapshot.get("artifact_exists", False)
    return {
        "name": name,
        "attempted": result.get("attempted", False),
        "success": result.get("success", False),
        "returncode": result.get("returncode"),
        "timed_out": timed_out,
        "skipped": bool(result.get("skipped")),
        "skip_reason": result.get("skip_reason"),
        "cached": bool(result.get("cached")),
        "cache_reason": result.get("cache_reason"),
        "cache_details": result.get("cache_details") or {},
        "stdout_preview": (result.get("stdout") or "")[:1200],
        "stderr_preview": (result.get("stderr") or "")[:800],
        "diagnostics_available": bool(diagnostics),
        "fallback_artifact_used": bool(result and not result.get("success", False) and bool(diagnostics) and artifact_exists),
        **artifact_snapshot,
    }


def sync_fast_heartbeat_timeout_issue(
    run_label: str,
    *,
    fast_mode: bool,
    elapsed_seconds: float,
    collect_result: Dict[str, Any] | None,
    parallel_results: Dict[str, Dict[str, Any]] | None,
    serial_results: Dict[str, Dict[str, Any]] | None,
) -> Dict[str, Any]:
    issue_id = "P1_fast_heartbeat_timeout_regression"
    if not fast_mode:
        return {"issue_id": issue_id, "status": "skipped_non_fast"}

    completed_lanes: list[str] = []
    if (collect_result or {}).get("attempted") or (collect_result or {}).get("success"):
        completed_lanes.append("hb_collect")

    for name, result in (parallel_results or {}).items():
        if isinstance(result, dict) and any(key in result for key in ("success", "stdout", "stderr", "returncode")):
            completed_lanes.append(name)

    timed_out_lanes: list[str] = []
    skipped_lanes: list[str] = []
    for name, payload in (serial_results or {}).items():
        if isinstance(payload, dict) and isinstance(payload.get("result"), dict):
            result_payload = payload.get("result") or {}
        elif isinstance(payload, dict):
            result_payload = payload
        else:
            continue
        if result_payload.get("skipped"):
            skipped_lanes.append(name)
            continue
        if result_payload.get("attempted") or result_payload.get("cached") or result_payload.get("success") or result_payload.get("returncode") is not None:
            completed_lanes.append(name)
        if result_payload.get("returncode") == -1 and "TIMEOUT after" in str(result_payload.get("stderr") or ""):
            timed_out_lanes.append(name)

    completed_lanes = list(dict.fromkeys(completed_lanes))
    skipped_lanes = list(dict.fromkeys(skipped_lanes))
    elapsed_seconds = round(float(elapsed_seconds or 0.0), 1)
    within_budget = elapsed_seconds <= FAST_HEARTBEAT_CRON_BUDGET_SECONDS

    tracker = IssueTracker.load()
    if within_budget and not timed_out_lanes:
        tracker.resolve(issue_id)
        tracker.save()
        return {
            "issue_id": issue_id,
            "status": "resolved",
            "elapsed_seconds": elapsed_seconds,
            "within_budget": True,
            "completed_lanes": completed_lanes,
            "skipped_lanes": skipped_lanes,
            "timed_out_lanes": [],
        }

    tracker.add(
        "P1",
        issue_id,
        "fast heartbeat still overruns cron budget when candidate-eval lane wakes up",
        "Keep --fast bounded to collect/drift/probe/docs lanes; move leaderboard or candidate evaluation behind a stricter timeout / opt-in refresh path.",
    )
    summary = {
        "reproduced": True,
        "heartbeat": run_label,
        "elapsed_seconds": elapsed_seconds,
        "timed_out_before_completion": bool(timed_out_lanes) or not within_budget,
        "completed_lanes_before_timeout": completed_lanes,
        "skipped_lanes": skipped_lanes,
        "timed_out_lanes": timed_out_lanes,
        "cron_budget_seconds": FAST_HEARTBEAT_CRON_BUDGET_SECONDS,
        "timeout_reason": (
            f"serial lanes exceeded watchdog: {', '.join(timed_out_lanes)}"
            if timed_out_lanes
            else f"fast runner completed in {elapsed_seconds}s which exceeds the {FAST_HEARTBEAT_CRON_BUDGET_SECONDS}s cron budget"
        ),
    }
    if not within_budget:
        summary["elapsed_seconds_greater_than"] = FAST_HEARTBEAT_CRON_BUDGET_SECONDS

    for issue in getattr(tracker, "issues", []):
        if issue.get("id") != issue_id:
            continue
        issue["hb_detected"] = run_label
        issue["summary"] = summary
        issue["updated_at"] = datetime.utcnow().isoformat()
        break
    tracker.save()
    return {
        "issue_id": issue_id,
        "status": "open",
        "elapsed_seconds": elapsed_seconds,
        "within_budget": within_budget,
        "completed_lanes": completed_lanes,
        "skipped_lanes": skipped_lanes,
        "timed_out_lanes": timed_out_lanes,
    }


def save_summary(
    run_label,
    counts,
    source_blockers,
    collect_result,
    results,
    elapsed,
    fast_mode,
    ic_diagnostics=None,
    drift_diagnostics=None,
    live_predictor_diagnostics=None,
    live_decision_drilldown=None,
    q35_scaling_audit=None,
    q15_support_audit=None,
    q15_bucket_root_cause=None,
    q15_boundary_replay=None,
    circuit_breaker_audit=None,
    feature_ablation=None,
    bull_4h_pocket_ablation=None,
    leaderboard_candidate_diagnostics=None,
    q15_runtime_resync=None,
    auto_propose_result=None,
    docs_sync=None,
    progress_path=None,
    serial_results=None,
):
    passed = sum(1 for r in results.values() if r["success"])
    total = len(results)
    continuity_repair = parse_collect_metadata(collect_result.get("stdout", ""))
    if continuity_repair:
        continuity_repair = {**continuity_repair, "heartbeat": run_label}
        continuity_repair["bridge_fallback_streak"] = compute_bridge_fallback_streak(continuity_repair)

    runtime_progress_snapshot = {}
    if progress_path:
        try:
            runtime_progress_snapshot = json.loads(Path(progress_path).read_text())
        except Exception:
            runtime_progress_snapshot = {}

    summary_now = datetime.now(timezone.utc)
    historical_coverage_confirmation = collect_historical_coverage_confirmation(DB_PATH)
    summary = {
        "heartbeat": run_label,
        "mode": "fast" if fast_mode else "full",
        "timestamp": summary_now.isoformat(),
        "collect_result": {
            "attempted": collect_result.get("attempted", False),
            "success": collect_result.get("success", False),
            "returncode": collect_result.get("returncode", 0),
            "stdout_preview": collect_result.get("stdout", "")[:2000],
            "stderr_preview": collect_result.get("stderr", "")[:1000],
            "continuity_repair": continuity_repair,
        },
        "db_counts": counts,
        "historical_coverage_confirmation": historical_coverage_confirmation,
        "source_blockers": source_blockers,
        "ic_diagnostics": ic_diagnostics or {},
        "drift_diagnostics": drift_diagnostics or {},
        "live_predictor_diagnostics": live_predictor_diagnostics or {},
        "live_decision_drilldown": live_decision_drilldown or {},
        "q35_scaling_audit": q35_scaling_audit or {},
        "q15_support_audit": q15_support_audit or {},
        "q15_bucket_root_cause": q15_bucket_root_cause or {},
        "q15_boundary_replay": q15_boundary_replay or {},
        "circuit_breaker_audit": circuit_breaker_audit or {},
        "feature_ablation": feature_ablation or {},
        "bull_4h_pocket_ablation": bull_4h_pocket_ablation or {},
        "leaderboard_candidate_diagnostics": leaderboard_candidate_diagnostics or {},
        "q15_runtime_resync": q15_runtime_resync or {"triggered": False, "reason": None, "message": None},
        "auto_propose": {
            "attempted": (auto_propose_result or {}).get("attempted", False),
            "success": (auto_propose_result or {}).get("success", False),
            "returncode": (auto_propose_result or {}).get("returncode", 0),
            "stdout_preview": (auto_propose_result or {}).get("stdout", "")[:2000],
            "stderr_preview": (auto_propose_result or {}).get("stderr", "")[:1000],
        },
        "docs_sync": docs_sync or {"ok": True, "stale_docs": [], "reference_artifacts": []},
        "runtime_progress": {
            "path": str(progress_path) if progress_path else None,
            "snapshot": runtime_progress_snapshot,
        },
        "parallel_results": {},
        "serial_results": {},
        "stats": {"passed": passed, "total": total, "elapsed_seconds": round(elapsed, 1)},
    }

    for name, r in results.items():
        summary["parallel_results"][name] = {
            "success": r["success"],
            "returncode": r.get("returncode"),
            "timed_out": bool(
                r.get("timed_out")
                or (r.get("returncode") == -1 and "TIMEOUT after" in str(r.get("stderr") or ""))
            ),
            "stdout_preview": r["stdout"][:2000] if r.get("stdout") else "",
            "stderr_preview": r["stderr"][:1000] if r.get("stderr") else "",
        }

    serial_results = serial_results or {}
    for name, payload in serial_results.items():
        if isinstance(payload, dict) and "result" in payload:
            result_payload = payload.get("result")
            diagnostics_payload = payload.get("diagnostics")
            artifact_path = payload.get("artifact_path")
        else:
            result_payload = payload
            diagnostics_payload = None
            artifact_path = None
        summary["serial_results"][name] = _build_serial_result_summary(
            name,
            result_payload,
            diagnostics=diagnostics_payload,
            artifact_path=artifact_path,
            now=summary_now,
        )

    summary_path = os.path.join(PROJECT_ROOT, 'data', f'heartbeat_{run_label}_summary.json')
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2, default=str)

    return summary, summary_path


def collect_recent_drift_diagnostics() -> Dict[str, Any]:
    result_path = Path(PROJECT_ROOT) / "data" / "recent_drift_report.json"
    if not result_path.exists():
        return {}
    try:
        payload = json.loads(result_path.read_text())
    except Exception:
        return {}
    primary = payload.get("primary_window") or {}
    summary = primary.get("summary") or {}
    quality_metrics = summary.get("quality_metrics") or {}
    target_path = summary.get("target_path_diagnostics") or {}
    tail_streak = target_path.get("tail_target_streak") or {}
    blocking = payload.get("blocking_window") or {}
    blocking_summary = blocking.get("summary") or {}
    blocking_quality = blocking_summary.get("quality_metrics") or {}
    blocking_reference = blocking_summary.get("reference_window_comparison") or {}
    blocking_target_path = blocking_summary.get("target_path_diagnostics") or {}
    blocking_tail_streak = blocking_target_path.get("tail_target_streak") or {}
    blocking_target_path_payload = {}
    if blocking_tail_streak.get("count") is not None and blocking_tail_streak.get("target") is not None:
        blocking_target_path_payload = {
            "tail_target_streak": {
                "target": blocking_tail_streak.get("target"),
                "count": blocking_tail_streak.get("count"),
                "start_timestamp": blocking_tail_streak.get("start_timestamp"),
                "end_timestamp": blocking_tail_streak.get("end_timestamp"),
                "regime_counts": blocking_tail_streak.get("regime_counts") or {},
            }
        }
    blocking_top_shift_source = blocking_summary.get("top_mean_shift_features") or blocking_reference.get("top_mean_shift_features") or []
    blocking_new_compressed = blocking_summary.get("new_compressed_features")
    if not isinstance(blocking_new_compressed, list) or not blocking_new_compressed:
        blocking_new_compressed = blocking_reference.get("new_unexpected_compressed_features") or []
    blocking_window = blocking.get("window")
    blocking_alerts = blocking.get("alerts") or []
    blocking_summary_payload = {
        "rows": blocking_summary.get("rows"),
        "win_rate": blocking_summary.get("win_rate"),
        "win_rate_delta_vs_full": blocking_summary.get("win_rate_delta_vs_full"),
        "dominant_regime": blocking_summary.get("dominant_regime"),
        "dominant_regime_share": blocking_summary.get("dominant_regime_share"),
        "drift_interpretation": blocking_summary.get("drift_interpretation"),
        "avg_pnl": blocking_summary.get("avg_pnl", blocking_quality.get("avg_simulated_pnl")),
        "avg_quality": blocking_summary.get("avg_quality", blocking_quality.get("avg_simulated_quality")),
        "avg_drawdown_penalty": blocking_summary.get("avg_drawdown_penalty", blocking_quality.get("avg_drawdown_penalty")),
        "top_shift_features": [
            item.get("feature") if isinstance(item, dict) else item
            for item in blocking_top_shift_source
            if (item.get("feature") if isinstance(item, dict) else item)
        ][:3],
        "new_compressed_feature": blocking_new_compressed[0] if blocking_new_compressed else None,
        "target_path_diagnostics": blocking_target_path_payload,
    }
    if not _has_recent_pathology_truth(
        blocking_summary_payload,
        window=blocking_window,
        alerts=blocking_alerts,
    ):
        blocking_window = None
        blocking_alerts = []
        blocking_summary_payload = {}
    return {
        "generated_at": payload.get("generated_at"),
        "target_col": payload.get("target_col"),
        "horizon_minutes": payload.get("horizon_minutes"),
        "full_sample": payload.get("full_sample") or {},
        "primary_window": primary.get("window"),
        "primary_alerts": primary.get("alerts") or [],
        "primary_summary": {
            "rows": summary.get("rows"),
            "win_rate": summary.get("win_rate"),
            "win_rate_delta_vs_full": summary.get("win_rate_delta_vs_full"),
            "dominant_regime": summary.get("dominant_regime"),
            "dominant_regime_share": summary.get("dominant_regime_share"),
            "drift_interpretation": summary.get("drift_interpretation"),
            "avg_pnl": summary.get("avg_pnl", quality_metrics.get("avg_simulated_pnl")),
            "avg_quality": summary.get("avg_quality", quality_metrics.get("avg_simulated_quality")),
            "avg_drawdown_penalty": summary.get("avg_drawdown_penalty", quality_metrics.get("avg_drawdown_penalty")),
            "feature_diagnostics": summary.get("feature_diagnostics") or {},
            "target_path_diagnostics": {
                "window_start_timestamp": target_path.get("window_start_timestamp"),
                "window_end_timestamp": target_path.get("window_end_timestamp"),
                "latest_target": target_path.get("latest_target"),
                "tail_target_streak": {
                    "target": tail_streak.get("target"),
                    "count": tail_streak.get("count"),
                    "start_timestamp": tail_streak.get("start_timestamp"),
                    "end_timestamp": tail_streak.get("end_timestamp"),
                    "regime_counts": tail_streak.get("regime_counts") or {},
                },
                "target_regime_breakdown": target_path.get("target_regime_breakdown") or {},
                "recent_examples": target_path.get("recent_examples") or [],
            },
        },
        "blocking_window": blocking_window,
        "blocking_alerts": blocking_alerts,
        "blocking_summary": blocking_summary_payload,
    }


def _persist_live_predictor_probe(stdout: str) -> Path | None:
    if not stdout:
        return None
    try:
        payload = json.loads(stdout)
    except Exception:
        return None
    out_path = Path(PROJECT_ROOT) / "data" / "live_predict_probe.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str))
    return out_path


def collect_live_predictor_diagnostics(probe_result: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = None
    stdout = (probe_result or {}).get("stdout") if probe_result else None
    if stdout:
        try:
            payload = json.loads(stdout)
        except Exception:
            payload = None
    if payload is None:
        result_path = Path(PROJECT_ROOT) / "data" / "live_predict_probe.json"
        if not result_path.exists():
            return {}
        try:
            payload = json.loads(result_path.read_text())
        except Exception:
            return {}
    deployment_blocker_details = payload.get("deployment_blocker_details") or {}
    support_progress = payload.get("support_progress")
    if not isinstance(support_progress, dict):
        support_progress = deployment_blocker_details.get("support_progress") or {}
    return {
        "target_col": payload.get("target_col"),
        "used_model": payload.get("used_model"),
        "model_type": payload.get("model_type"),
        "signal": payload.get("signal"),
        "confidence": payload.get("confidence"),
        "should_trade": payload.get("should_trade"),
        "reason": payload.get("reason"),
        "streak": payload.get("streak"),
        "win_rate": payload.get("win_rate"),
        "recent_window_win_rate": payload.get("recent_window_win_rate"),
        "recent_window_wins": payload.get("recent_window_wins"),
        "window_size": payload.get("window_size"),
        "triggered_by": payload.get("triggered_by") or [],
        "horizon_minutes": payload.get("horizon_minutes"),
        "runtime_blocker": "circuit_breaker" if payload.get("signal") == "CIRCUIT_BREAKER" or payload.get("model_type") == "circuit_breaker" else None,
        "regime_label": payload.get("regime_label"),
        "model_route_regime": payload.get("model_route_regime"),
        "regime_gate": payload.get("regime_gate"),
        "current_live_structure_bucket": payload.get("current_live_structure_bucket") or payload.get("structure_bucket"),
        "current_live_structure_bucket_rows": payload.get("current_live_structure_bucket_rows"),
        "q15_exact_supported_component_patch_applied": payload.get("q15_exact_supported_component_patch_applied"),
        "runtime_closure_state": payload.get("runtime_closure_state"),
        "runtime_closure_summary": payload.get("runtime_closure_summary"),
        "entry_quality_label": payload.get("entry_quality_label"),
        "entry_quality_components": payload.get("entry_quality_components") or {},
        "allowed_layers_raw": payload.get("allowed_layers_raw"),
        "allowed_layers_raw_reason": payload.get("allowed_layers_raw_reason") or payload.get("allowed_layers_reason"),
        "allowed_layers": payload.get("allowed_layers"),
        "allowed_layers_reason": payload.get("allowed_layers_reason"),
        "execution_guardrail_applied": payload.get("execution_guardrail_applied"),
        "execution_guardrail_reason": payload.get("execution_guardrail_reason"),
        "deployment_blocker": payload.get("deployment_blocker"),
        "deployment_blocker_reason": payload.get("deployment_blocker_reason"),
        "deployment_blocker_source": payload.get("deployment_blocker_source"),
        "deployment_blocker_details": deployment_blocker_details,
        "support_route_verdict": payload.get("support_route_verdict") or deployment_blocker_details.get("support_route_verdict"),
        "support_route_deployable": payload.get("support_route_deployable") if payload.get("support_route_deployable") is not None else deployment_blocker_details.get("support_route_deployable"),
        "support_governance_route": payload.get("support_governance_route") or deployment_blocker_details.get("support_governance_route"),
        "support_progress": support_progress,
        "minimum_support_rows": payload.get("minimum_support_rows") if payload.get("minimum_support_rows") is not None else deployment_blocker_details.get("minimum_support_rows"),
        "current_live_structure_bucket_gap_to_minimum": payload.get("current_live_structure_bucket_gap_to_minimum") if payload.get("current_live_structure_bucket_gap_to_minimum") is not None else deployment_blocker_details.get("current_live_structure_bucket_gap_to_minimum"),
        "decision_quality_calibration_scope": payload.get("decision_quality_calibration_scope"),
        "decision_quality_calibration_window": payload.get("decision_quality_calibration_window"),
        "decision_quality_sample_size": payload.get("decision_quality_sample_size"),
        "decision_quality_scope_diagnostics": payload.get("decision_quality_scope_diagnostics") or {},
        "decision_quality_guardrail_applied": payload.get("decision_quality_guardrail_applied"),
        "decision_quality_guardrail_reason": payload.get("decision_quality_guardrail_reason"),
        "decision_quality_recent_pathology_applied": payload.get("decision_quality_recent_pathology_applied"),
        "decision_quality_recent_pathology_window": payload.get("decision_quality_recent_pathology_window"),
        "decision_quality_recent_pathology_alerts": payload.get("decision_quality_recent_pathology_alerts") or [],
        "decision_quality_recent_pathology_reason": payload.get("decision_quality_recent_pathology_reason"),
        "decision_quality_exact_live_lane_bucket_verdict": payload.get("decision_quality_exact_live_lane_bucket_verdict"),
        "decision_quality_exact_live_lane_bucket_reason": payload.get("decision_quality_exact_live_lane_bucket_reason"),
        "decision_quality_exact_live_lane_toxic_bucket": payload.get("decision_quality_exact_live_lane_toxic_bucket") or {},
        "decision_quality_exact_live_lane_bucket_diagnostics": payload.get("decision_quality_exact_live_lane_bucket_diagnostics") or {},
        "decision_quality_label": payload.get("decision_quality_label"),
        "decision_quality_score": payload.get("decision_quality_score"),
        "expected_win_rate": payload.get("expected_win_rate"),
        "expected_pyramid_pnl": payload.get("expected_pyramid_pnl"),
        "expected_pyramid_quality": payload.get("expected_pyramid_quality"),
        "expected_drawdown_penalty": payload.get("expected_drawdown_penalty"),
        "expected_time_underwater": payload.get("expected_time_underwater"),
        "non_null_4h_feature_count": payload.get("non_null_4h_feature_count"),
        "non_null_4h_lag_count": payload.get("non_null_4h_lag_count"),
        "decision_quality_recent_pathology_summary": payload.get("decision_quality_recent_pathology_summary") or {},
        "decision_quality_pathology_consensus": ((payload.get("decision_quality_scope_diagnostics") or {}).get("pathology_consensus") or {}),
    }


def collect_live_decision_quality_drilldown_diagnostics(
    drilldown_result: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    payload = None
    stdout = (drilldown_result or {}).get("stdout") if drilldown_result else None
    if stdout:
        try:
            payload = json.loads(stdout)
        except Exception:
            payload = None
    if payload is None:
        result_path = Path(PROJECT_ROOT) / "data" / "live_decision_quality_drilldown.json"
        if not result_path.exists():
            return {}
        try:
            payload = json.loads(result_path.read_text())
        except Exception:
            return {}

    recommended_patch = payload.get("recommended_patch") if isinstance(payload.get("recommended_patch"), dict) else {}
    return {
        "json": payload.get("json"),
        "markdown": payload.get("markdown"),
        "chosen_scope": payload.get("chosen_scope"),
        "worst_pathology_scope": payload.get("worst_pathology_scope"),
        "runtime_blocker": payload.get("runtime_blocker"),
        "runtime_blocker_reason": payload.get("runtime_blocker_reason"),
        "deployment_blocker": payload.get("deployment_blocker"),
        "deployment_blocker_reason": payload.get("deployment_blocker_reason"),
        "q15_exact_supported_component_patch_applied": payload.get("q15_exact_supported_component_patch_applied"),
        "runtime_closure_state": payload.get("runtime_closure_state"),
        "runtime_closure_summary": payload.get("runtime_closure_summary"),
        "signal": payload.get("signal"),
        "allowed_layers": payload.get("allowed_layers"),
        "allowed_layers_reason": payload.get("allowed_layers_reason"),
        "support_route_verdict": payload.get("support_route_verdict"),
        "recommended_patch_profile": payload.get("recommended_patch_profile") or recommended_patch.get("recommended_profile"),
        "recommended_patch_status": payload.get("recommended_patch_status") or recommended_patch.get("status"),
        "recommended_patch_reference_scope": payload.get("recommended_patch_reference_scope") or recommended_patch.get("reference_patch_scope"),
        "recommended_patch_reference_source": payload.get("recommended_patch_reference_source") or recommended_patch.get("reference_source"),
        "remaining_gap_to_floor": payload.get("remaining_gap_to_floor"),
        "best_single_component": payload.get("best_single_component"),
        "best_single_component_required_score_delta": payload.get("best_single_component_required_score_delta"),
    }


def _q15_post_audit_runtime_resync_reason(
    live_predictor_diagnostics: Dict[str, Any] | None,
    q15_support_summary: Dict[str, Any] | None,
) -> str | None:
    live_predictor_diagnostics = live_predictor_diagnostics or {}
    q15_support_summary = q15_support_summary or {}
    if not live_predictor_diagnostics or not q15_support_summary:
        return None

    current_bucket = str(live_predictor_diagnostics.get("current_live_structure_bucket") or "")
    if "q15" not in current_bucket:
        return None

    scope = q15_support_summary.get("scope_applicability") or {}
    support_route = q15_support_summary.get("support_route") or {}
    floor = q15_support_summary.get("floor_cross_legality") or {}
    component_experiment = q15_support_summary.get("component_experiment") or {}
    machine_read = component_experiment.get("machine_read_answer") or {}
    support_progress = support_route.get("support_progress") if isinstance(support_route.get("support_progress"), dict) else {}

    if scope.get("status") != "current_live_q15_lane_active" or not scope.get("active_for_current_live_row"):
        return None
    audit_bucket = str(scope.get("current_structure_bucket") or "")
    if audit_bucket and audit_bucket != current_bucket:
        return None

    live_support_route_verdict = live_predictor_diagnostics.get("support_route_verdict")
    live_support_governance_route = live_predictor_diagnostics.get("support_governance_route")
    live_support_progress = live_predictor_diagnostics.get("support_progress") or {}

    if bool(live_predictor_diagnostics.get("q15_exact_supported_component_patch_applied")):
        return None

    if bool(
        support_route.get("verdict") == "exact_bucket_supported"
        and support_route.get("deployable")
        and floor.get("verdict") == "legal_component_experiment_after_support_ready"
        and floor.get("legal_to_relax_runtime_gate")
        and component_experiment.get("verdict") == "exact_supported_component_experiment_ready"
        and component_experiment.get("feature") == "feat_4h_bias50"
        and machine_read.get("support_ready")
        and machine_read.get("entry_quality_ge_0_55")
        and machine_read.get("allowed_layers_gt_0")
        and machine_read.get("preserves_positive_discrimination")
    ):
        return "patch_ready_probe_unpatched"

    if support_route.get("verdict") and support_route.get("verdict") != live_support_route_verdict:
        return "support_truth_changed_under_breaker"
    if support_route.get("support_governance_route") and support_route.get("support_governance_route") != live_support_governance_route:
        return "support_truth_changed_under_breaker"
    for key in ("status", "current_rows", "minimum_support_rows", "gap_to_minimum"):
        audit_value = support_progress.get(key)
        if audit_value is None:
            continue
        if live_support_progress.get(key) != audit_value:
            return "support_truth_changed_under_breaker"

    return None



def _needs_q15_post_audit_runtime_resync(
    live_predictor_diagnostics: Dict[str, Any] | None,
    q15_support_summary: Dict[str, Any] | None,
) -> bool:
    return _q15_post_audit_runtime_resync_reason(
        live_predictor_diagnostics,
        q15_support_summary,
    ) is not None



def _format_q15_post_audit_runtime_resync_message(reason: str | None) -> str:
    if reason == "support_truth_changed_under_breaker":
        return (
            "🔄 Q15 runtime resync：support truth 已更新（route / governance / progress 與先前 live probe 不一致）；"
            "重跑 probe + drilldown 以鎖定最終 current-live truth。"
        )
    if reason == "patch_ready_probe_unpatched":
        return (
            "🔄 Q15 runtime resync：support audit 已確認 patch-ready，但先前 live probe 尚未套用；"
            "重跑 probe + drilldown 以鎖定最終 current-live truth。"
        )
    return "🔄 Q15 runtime resync：重跑 probe + drilldown 以鎖定最終 current-live truth。"


def collect_feature_ablation_diagnostics() -> Dict[str, Any]:
    result_path = Path(PROJECT_ROOT) / "data" / "feature_group_ablation.json"
    if not result_path.exists():
        return {}
    try:
        payload = json.loads(result_path.read_text())
    except Exception:
        return {}
    profiles = payload.get("profiles") or {}
    recommended = payload.get("recommended_profile")
    recommended_metrics = profiles.get(recommended) or {}
    current_full = profiles.get("current_full") or {}
    return {
        "generated_at": payload.get("generated_at"),
        "target_col": payload.get("target_col"),
        "recent_rows": payload.get("recent_rows"),
        "n_splits": payload.get("n_splits"),
        "xgb_n_estimators": payload.get("xgb_n_estimators"),
        "refresh_mode": payload.get("refresh_mode") or "full_rebuild",
        "profile_metrics_fresh": payload.get("profile_metrics_fresh", True),
        "profiles_evaluated": payload.get("profiles_evaluated") or list(profiles.keys()),
        "recommended_profile": recommended,
        "recommended_metrics": recommended_metrics,
        "current_full_metrics": current_full,
        "profile_role": {
            "profile": recommended,
            "role": "global_shrinkage_winner" if recommended else None,
            "source": "feature_group_ablation.recommended_profile" if recommended else None,
            "reason": "global 最近視窗的 shrinkage / CV 穩定度最佳 profile。" if recommended else None,
        },
        "bull_collapse_4h_features": payload.get("bull_collapse_4h_features") or [],
        "stable_4h_features": payload.get("stable_4h_features") or [],
    }


def collect_q35_scaling_audit_diagnostics() -> Dict[str, Any]:
    result_path = Path(PROJECT_ROOT) / "data" / "q35_scaling_audit.json"
    if not result_path.exists():
        return {}
    try:
        payload = json.loads(result_path.read_text())
    except Exception:
        return {}
    current_live = payload.get("current_live") or {}
    baseline_current = payload.get("baseline_current_live") or payload.get("legacy_current_live") or {}
    calibration_runtime_current = payload.get("calibration_runtime_current") or {}
    current_features = current_live.get("raw_features") or {}
    current_entry_components = current_live.get("entry_quality_components") or {}
    current_bias50_calibration = current_entry_components.get("bias50_calibration") or {}
    baseline_features = baseline_current.get("raw_features") or {}
    scope_applicability = payload.get("scope_applicability") or {}
    piecewise_preview = payload.get("piecewise_runtime_preview") or {}
    counterfactuals = payload.get("counterfactuals") or {}
    deployment_experiment = payload.get("deployment_grade_component_experiment") or {}
    joint_experiment = payload.get("joint_component_experiment") or {}
    exact_supported_bias50_experiment = payload.get("exact_supported_bias50_component_experiment") or {}
    base_mix_experiment = payload.get("base_mix_component_experiment") or {}
    redesign_experiment = payload.get("base_stack_redesign_experiment") or {}
    exact_lane = payload.get("exact_lane_summary") or {}
    broader_bull = payload.get("broader_bull_cohorts") or {}
    segmented = payload.get("segmented_calibration") or {}
    return {
        "generated_at": payload.get("generated_at"),
        "target_col": payload.get("target_col"),
        "overall_verdict": payload.get("overall_verdict"),
        "structure_scaling_verdict": payload.get("structure_scaling_verdict"),
        "verdict_reason": payload.get("verdict_reason"),
        "recommended_action": payload.get("recommended_action"),
        "current_live": {
            "regime_label": current_live.get("regime_label"),
            "regime_gate": current_live.get("regime_gate"),
            "base_gate": current_live.get("base_gate"),
            "gate_reason": current_live.get("gate_reason"),
            "structure_bucket": current_live.get("structure_bucket"),
            "structure_quality": current_live.get("structure_quality"),
            "entry_quality": current_live.get("entry_quality"),
            "entry_quality_label": current_live.get("entry_quality_label"),
            "allowed_layers_raw": current_live.get("allowed_layers_raw"),
            "allowed_layers_reason": current_live.get("allowed_layers_reason"),
            "feat_4h_bias50": current_features.get("feat_4h_bias50"),
            "feat_4h_bias200": current_features.get("feat_4h_bias200"),
            "bias50_calibration": current_bias50_calibration,
            "q35_discriminative_redesign_applied": current_live.get("q35_discriminative_redesign_applied"),
            "runtime_source": current_live.get("source"),
            "probe_alignment": current_live.get("probe_alignment") or {},
        },
        "baseline_current_live": {
            "regime_label": baseline_current.get("regime_label"),
            "regime_gate": baseline_current.get("regime_gate"),
            "structure_bucket": baseline_current.get("structure_bucket"),
            "entry_quality": baseline_current.get("entry_quality"),
            "entry_quality_label": baseline_current.get("entry_quality_label"),
            "allowed_layers_raw": baseline_current.get("allowed_layers_raw"),
            "allowed_layers_reason": baseline_current.get("allowed_layers_reason"),
            "feat_4h_bias50": baseline_features.get("feat_4h_bias50"),
            "feat_4h_bias200": baseline_features.get("feat_4h_bias200"),
        },
        "calibration_runtime_current": {
            "entry_quality": calibration_runtime_current.get("entry_quality"),
            "entry_quality_label": calibration_runtime_current.get("entry_quality_label"),
            "allowed_layers_raw": calibration_runtime_current.get("allowed_layers_raw"),
            "allowed_layers_reason": calibration_runtime_current.get("allowed_layers_reason"),
            "source": calibration_runtime_current.get("source"),
        },
        "scope_applicability": {
            "status": scope_applicability.get("status"),
            "active_for_current_live_row": scope_applicability.get("active_for_current_live_row"),
            "current_structure_bucket": scope_applicability.get("current_structure_bucket"),
            "target_structure_bucket": scope_applicability.get("target_structure_bucket"),
            "reason": scope_applicability.get("reason"),
        },
        "exact_lane_summary": {
            "rows": exact_lane.get("rows"),
            "win_rate": exact_lane.get("win_rate"),
            "current_bias50_percentile": exact_lane.get("current_bias50_percentile"),
            "bias50_distribution": exact_lane.get("bias50_distribution") or {},
            "structure_quality_distribution": exact_lane.get("structure_quality_distribution") or {},
            "entry_quality_distribution": exact_lane.get("entry_quality_distribution") or {},
        },
        "broader_bull_cohorts": {
            "same_gate_same_quality": broader_bull.get("same_gate_same_quality") or {},
            "same_bucket": broader_bull.get("same_bucket") or {},
            "bull_all": broader_bull.get("bull_all") or {},
        },
        "segmented_calibration": {
            "status": segmented.get("status"),
            "recommended_mode": segmented.get("recommended_mode"),
            "reason": segmented.get("reason"),
            "runtime_contract_status": segmented.get("runtime_contract_status"),
            "runtime_contract_reason": segmented.get("runtime_contract_reason"),
            "exact_lane": segmented.get("exact_lane") or {},
            "reference_cohort": segmented.get("reference_cohort") or {},
            "broader_bull_cohorts": segmented.get("broader_bull_cohorts") or {},
        },
        "piecewise_runtime_preview": {
            "applied": piecewise_preview.get("applied"),
            "score": piecewise_preview.get("score"),
            "legacy_score": piecewise_preview.get("legacy_score"),
            "score_delta_vs_legacy": piecewise_preview.get("score_delta_vs_legacy"),
            "mode": piecewise_preview.get("mode"),
            "segment": piecewise_preview.get("segment"),
            "reference_cohort": piecewise_preview.get("reference_cohort"),
            "reason": piecewise_preview.get("reason"),
            "exact_p90": piecewise_preview.get("exact_p90"),
            "reference_p90": piecewise_preview.get("reference_p90"),
            "extension_share": piecewise_preview.get("extension_share"),
        },
        "deployment_grade_component_experiment": {
            "verdict": deployment_experiment.get("verdict"),
            "baseline_entry_quality": deployment_experiment.get("baseline_entry_quality"),
            "calibration_runtime_entry_quality": deployment_experiment.get("calibration_runtime_entry_quality"),
            "runtime_entry_quality": deployment_experiment.get("runtime_entry_quality"),
            "calibration_runtime_delta_vs_legacy": deployment_experiment.get("calibration_runtime_delta_vs_legacy"),
            "entry_quality_delta_vs_legacy": deployment_experiment.get("entry_quality_delta_vs_legacy"),
            "baseline_allowed_layers_raw": deployment_experiment.get("baseline_allowed_layers_raw"),
            "calibration_runtime_allowed_layers_raw": deployment_experiment.get("calibration_runtime_allowed_layers_raw"),
            "runtime_allowed_layers_raw": deployment_experiment.get("runtime_allowed_layers_raw"),
            "runtime_trade_floor": deployment_experiment.get("runtime_trade_floor"),
            "runtime_remaining_gap_to_floor": deployment_experiment.get("runtime_remaining_gap_to_floor"),
            "machine_read_answer": deployment_experiment.get("machine_read_answer") or {},
            "runtime_source": deployment_experiment.get("runtime_source"),
            "q35_discriminative_redesign_applied": deployment_experiment.get("q35_discriminative_redesign_applied"),
            "probe_alignment": deployment_experiment.get("probe_alignment") or {},
            "next_patch_target": deployment_experiment.get("next_patch_target"),
            "verify_next": deployment_experiment.get("verify_next"),
        },
        "joint_component_experiment": {
            "verdict": joint_experiment.get("verdict"),
            "reason": joint_experiment.get("reason"),
            "machine_read_answer": joint_experiment.get("machine_read_answer") or {},
            "best_scenario": joint_experiment.get("best_scenario") or {},
            "verify_next": joint_experiment.get("verify_next"),
        },
        "exact_supported_bias50_component_experiment": {
            "verdict": exact_supported_bias50_experiment.get("verdict"),
            "reason": exact_supported_bias50_experiment.get("reason"),
            "machine_read_answer": exact_supported_bias50_experiment.get("machine_read_answer") or {},
            "best_scenario": exact_supported_bias50_experiment.get("best_scenario") or {},
            "verify_next": exact_supported_bias50_experiment.get("verify_next"),
        },
        "base_mix_component_experiment": {
            "verdict": base_mix_experiment.get("verdict"),
            "reason": base_mix_experiment.get("reason"),
            "machine_read_answer": base_mix_experiment.get("machine_read_answer") or {},
            "best_scenario": base_mix_experiment.get("best_scenario") or {},
            "verify_next": base_mix_experiment.get("verify_next"),
        },
        "base_stack_redesign_experiment": {
            "verdict": redesign_experiment.get("verdict"),
            "reason": redesign_experiment.get("reason"),
            "rows": redesign_experiment.get("rows"),
            "wins": redesign_experiment.get("wins"),
            "losses": redesign_experiment.get("losses"),
            "machine_read_answer": redesign_experiment.get("machine_read_answer") or {},
            "best_discriminative_candidate": redesign_experiment.get("best_discriminative_candidate") or {},
            "best_floor_candidate": redesign_experiment.get("best_floor_candidate") or {},
            "unsafe_floor_cross_candidate": redesign_experiment.get("unsafe_floor_cross_candidate"),
            "verify_next": redesign_experiment.get("verify_next"),
        },
        "counterfactuals": {
            "entry_if_gate_allow_only": counterfactuals.get("entry_if_gate_allow_only"),
            "layers_if_gate_allow_only": counterfactuals.get("layers_if_gate_allow_only"),
            "gate_allow_only_changes_layers": counterfactuals.get("gate_allow_only_changes_layers"),
            "entry_if_bias50_fully_relaxed": counterfactuals.get("entry_if_bias50_fully_relaxed"),
            "layers_if_bias50_fully_relaxed": counterfactuals.get("layers_if_bias50_fully_relaxed"),
            "bias50_score_current": counterfactuals.get("bias50_score_current"),
            "trade_floor": counterfactuals.get("trade_floor"),
            "needed_entry_gain_to_cross_floor": counterfactuals.get("needed_entry_gain_to_cross_floor"),
            "needed_base_gain_to_cross_floor": counterfactuals.get("needed_base_gain_to_cross_floor"),
            "needed_bias50_score_for_floor": counterfactuals.get("needed_bias50_score_for_floor"),
            "required_bias50_cap_for_floor": counterfactuals.get("required_bias50_cap_for_floor"),
            "current_bias50_value": counterfactuals.get("current_bias50_value"),
        },
    }


def collect_q15_support_audit_diagnostics() -> Dict[str, Any]:
    result_path = Path(PROJECT_ROOT) / "data" / "q15_support_audit.json"
    if not result_path.exists():
        return {}
    try:
        payload = json.loads(result_path.read_text())
    except Exception:
        return {}
    current_live = payload.get("current_live") or {}
    scope_applicability = payload.get("scope_applicability") or {}
    support_route = payload.get("support_route") or {}
    floor = payload.get("floor_cross_legality") or {}
    component_experiment = payload.get("component_experiment") or {}
    return {
        "generated_at": payload.get("generated_at"),
        "target_col": payload.get("target_col"),
        "current_live": current_live,
        "scope_applicability": scope_applicability,
        "support_route": support_route,
        "floor_cross_legality": floor,
        "component_experiment": component_experiment,
        "next_action": payload.get("next_action"),
    }


def collect_q15_bucket_root_cause_diagnostics() -> Dict[str, Any]:
    result_path = Path(PROJECT_ROOT) / "data" / "q15_bucket_root_cause.json"
    if not result_path.exists():
        return {}
    try:
        payload = json.loads(result_path.read_text())
    except Exception:
        return {}
    return {
        "generated_at": payload.get("generated_at"),
        "target_col": payload.get("target_col"),
        "current_live": payload.get("current_live") or {},
        "exact_live_lane": payload.get("exact_live_lane") or {},
        "verdict": payload.get("verdict"),
        "candidate_patch_type": payload.get("candidate_patch_type"),
        "candidate_patch_feature": payload.get("candidate_patch_feature"),
        "candidate_patch": payload.get("candidate_patch") or {},
        "reason": payload.get("reason"),
        "verify_next": payload.get("verify_next"),
        "carry_forward": payload.get("carry_forward") or [],
    }


def collect_q15_boundary_replay_diagnostics() -> Dict[str, Any]:
    result_path = Path(PROJECT_ROOT) / "data" / "q15_boundary_replay.json"
    if not result_path.exists():
        return {}
    try:
        payload = json.loads(result_path.read_text())
    except Exception:
        return {}
    return {
        "generated_at": payload.get("generated_at"),
        "target_col": payload.get("target_col"),
        "current_live": payload.get("current_live") or {},
        "boundary_replay": payload.get("boundary_replay") or {},
        "component_counterfactual": payload.get("component_counterfactual") or {},
        "verdict": payload.get("verdict"),
        "reason": payload.get("reason"),
        "next_action": payload.get("next_action"),
        "verify_next": payload.get("verify_next"),
        "carry_forward": payload.get("carry_forward") or [],
    }


def collect_circuit_breaker_audit_diagnostics() -> Dict[str, Any]:
    result_path = Path(PROJECT_ROOT) / "data" / "circuit_breaker_audit.json"
    if not result_path.exists():
        return {}
    try:
        payload = json.loads(result_path.read_text())
    except Exception:
        return {}
    mixed = payload.get("mixed_scope") or {}
    aligned = payload.get("aligned_scope") or {}
    thresholds = payload.get("trigger_thresholds") or {}
    root = payload.get("root_cause") or {}
    return {
        "target_col": payload.get("target_col"),
        "trigger_thresholds": thresholds,
        "root_cause": root,
        "mixed_scope": {
            "triggered": mixed.get("triggered"),
            "triggered_by": mixed.get("triggered_by") or [],
            "rows_available": mixed.get("rows_available"),
            "latest_timestamp": mixed.get("latest_timestamp"),
            "streak": mixed.get("streak") or {},
            "recent_window": mixed.get("recent_window") or {},
            "release_condition": mixed.get("release_condition") or {},
            "tail_pathology": mixed.get("tail_pathology") or {},
        },
        "aligned_scope": {
            "triggered": aligned.get("triggered"),
            "triggered_by": aligned.get("triggered_by") or [],
            "release_ready": aligned.get("release_ready"),
            "rows_available": aligned.get("rows_available"),
            "latest_timestamp": aligned.get("latest_timestamp"),
            "streak": aligned.get("streak") or {},
            "recent_window": aligned.get("recent_window") or {},
            "release_condition": aligned.get("release_condition") or {},
            "tail_pathology": aligned.get("tail_pathology") or {},
        },
    }



def collect_bull_4h_pocket_diagnostics() -> Dict[str, Any]:
    result_path = Path(PROJECT_ROOT) / "data" / "bull_4h_pocket_ablation.json"
    if not result_path.exists():
        return {}
    try:
        payload = json.loads(result_path.read_text())
    except Exception:
        return {}

    cohorts = payload.get("cohorts") or {}

    def _cohort_summary(name: str) -> Dict[str, Any]:
        cohort = cohorts.get(name) or {}
        return {
            "rows": cohort.get("rows"),
            "base_win_rate": cohort.get("base_win_rate"),
            "recommended_profile": cohort.get("recommended_profile"),
            "recommended_metrics": ((cohort.get("profiles") or {}).get(cohort.get("recommended_profile")) or {}),
        }

    artifact_live_context = payload.get("live_context") or {}
    support_summary = payload.get("support_pathology_summary") or {}
    refresh_mode = str(payload.get("refresh_mode") or "")
    live_specific_profiles_fresh = bool(payload.get("live_specific_profiles_fresh", True))
    artifact_live_signature = _bull_pocket_semantic_signature_from_live_context(artifact_live_context)
    current_live_signature = _current_bull_pocket_semantic_signature()
    semantic_mismatch = bool(
        artifact_live_signature
        and current_live_signature
        and artifact_live_signature != current_live_signature
    )
    live_context = artifact_live_context
    live_specific_reference_only = refresh_mode == "live_context_only" and not live_specific_profiles_fresh

    if semantic_mismatch and current_live_signature:
        live_context = {
            **artifact_live_context,
            "regime_label": current_live_signature.get("regime_label"),
            "regime_gate": current_live_signature.get("regime_gate"),
            "entry_quality_label": current_live_signature.get("entry_quality_label"),
            "decision_quality_label": current_live_signature.get("decision_quality_label"),
            "current_live_structure_bucket": current_live_signature.get("current_live_structure_bucket"),
            "current_live_structure_bucket_rows": current_live_signature.get("current_live_structure_bucket_rows"),
            "exact_scope_rows": current_live_signature.get("exact_scope_rows"),
            "execution_guardrail_reason": current_live_signature.get("execution_guardrail_reason"),
            "decision_quality_calibration_scope": current_live_signature.get("decision_quality_calibration_scope"),
        }
        live_specific_reference_only = True

    production_profile_role = {
        "profile": (cohorts.get("bull_all") or {}).get("recommended_profile"),
        "role": "bull_exact_supported_production_profile" if support_summary.get("exact_bucket_root_cause") == "exact_bucket_supported" else "support_aware_production_profile",
        "source": (
            "bull_4h_pocket_ablation.exact_supported_profile"
            if support_summary.get("exact_bucket_root_cause") == "exact_bucket_supported"
            else "bull_4h_pocket_ablation.support_aware_profile"
        ),
        "support_cohort": "bull_all" if support_summary.get("exact_bucket_root_cause") == "exact_bucket_supported" else support_summary.get("preferred_support_cohort"),
        "support_rows": (cohorts.get("bull_all") or {}).get("rows") if support_summary.get("exact_bucket_root_cause") == "exact_bucket_supported" else ((cohorts.get(support_summary.get("preferred_support_cohort") or "") or {}).get("rows")),
        "exact_live_bucket_rows": live_context.get("current_live_structure_bucket_rows"),
        "reason": (
            "exact live bucket 已達 minimum support，production 應以 bull exact-supported lane 作為治理與訓練語義。"
            if support_summary.get("exact_bucket_root_cause") == "exact_bucket_supported"
            else "exact bucket 尚未充分支持，production 仍需保留 support-aware lane 作為治理語義。"
        ),
    }
    if live_specific_reference_only:
        if refresh_mode == "live_context_only" and not semantic_mismatch:
            production_profile_role.update({
                "role": "current_bucket_refresh_reference_only",
                "source": "bull_4h_pocket_ablation.live_context_refresh",
                "support_cohort": None,
                "support_rows": None,
                "reason": "fast heartbeat 已用 current-bucket refresh lane 更新 current live support truth；bull_all / bull_collapse_q35 仍可作 reference-only patch，但 live-specific proxy cohorts 本輪不提供可部署治理語義。",
            })
        else:
            production_profile_role.update({
                "role": "reference_only_stale_live_context",
                "source": "bull_4h_pocket_ablation.reference_only",
                "support_cohort": None,
                "support_rows": None,
                "reason": "bull 4H pocket artifact 的 live context 已和目前 live probe 脫節；本輪僅保留 bull_all / bull_collapse_q35 作為 reference-only，不能把 live-specific proxy cohorts 當成 current truth。",
            })

    support_summary_payload = {
        "blocker_state": support_summary.get("blocker_state"),
        "preferred_support_cohort": support_summary.get("preferred_support_cohort"),
        "minimum_support_rows": support_summary.get("minimum_support_rows"),
        "current_live_structure_bucket_gap_to_minimum": support_summary.get("current_live_structure_bucket_gap_to_minimum"),
        "exact_bucket_root_cause": support_summary.get("exact_bucket_root_cause"),
        "bucket_comparison_takeaway": support_summary.get("bucket_comparison_takeaway"),
        "proxy_boundary_verdict": support_summary.get("proxy_boundary_verdict"),
        "proxy_boundary_reason": support_summary.get("proxy_boundary_reason"),
        "proxy_boundary_diagnostics": support_summary.get("proxy_boundary_diagnostics") or {},
        "bucket_evidence_comparison": support_summary.get("bucket_evidence_comparison") or {},
        "exact_lane_bucket_verdict": support_summary.get("exact_lane_bucket_verdict"),
        "exact_lane_bucket_reason": support_summary.get("exact_lane_bucket_reason"),
        "exact_lane_toxic_bucket": support_summary.get("exact_lane_toxic_bucket") or {},
        "exact_lane_bucket_diagnostics": support_summary.get("exact_lane_bucket_diagnostics") or {},
        "recommended_action": support_summary.get("recommended_action"),
    }
    if live_specific_reference_only:
        if refresh_mode == "live_context_only" and not semantic_mismatch:
            support_summary_payload.update({
                "blocker_state": "current_bucket_refresh_reference_only",
                "preferred_support_cohort": None,
                "recommended_action": "Fast heartbeat 已更新 current live bucket / support truth；live-specific proxy cohorts 需等 full bull_4h_pocket_ablation.py rebuild，當前僅保留 bull_collapse_q35 reference patch 可見性。",
            })
        else:
            support_summary_payload.update({
                "blocker_state": "reference_only_stale_live_context",
                "preferred_support_cohort": None,
                "exact_bucket_root_cause": None,
                "bucket_comparison_takeaway": None,
                "proxy_boundary_verdict": None,
                "proxy_boundary_reason": "artifact live context is stale against current live probe; skip live-specific proxy diagnostics until bull_4h_pocket_ablation.py is rebuilt for the current live bucket.",
                "proxy_boundary_diagnostics": {},
                "bucket_evidence_comparison": {},
                "exact_lane_bucket_verdict": None,
                "exact_lane_bucket_reason": None,
                "exact_lane_toxic_bucket": {},
                "exact_lane_bucket_diagnostics": {},
                "recommended_action": "Keep bull_collapse_q35 reference patch visible, but do not treat stale live-specific proxy cohorts as current runtime truth.",
            })

    return {
        "generated_at": payload.get("generated_at"),
        "target_col": payload.get("target_col"),
        "collapse_features": payload.get("collapse_features") or [],
        "collapse_thresholds": payload.get("collapse_thresholds") or {},
        "semantic_alignment": {
            "aligned": not semantic_mismatch,
            "artifact_live_signature": artifact_live_signature or {},
            "current_live_signature": current_live_signature or {},
            "live_specific_reference_only": live_specific_reference_only,
            "refresh_mode": refresh_mode or "full_rebuild",
            "live_specific_profiles_fresh": live_specific_profiles_fresh,
        },
        "live_context": {
            "regime_label": live_context.get("regime_label"),
            "regime_gate": live_context.get("regime_gate"),
            "entry_quality_label": live_context.get("entry_quality_label"),
            "execution_guardrail_reason": live_context.get("execution_guardrail_reason"),
            "current_live_structure_bucket": live_context.get("current_live_structure_bucket"),
            "current_live_structure_bucket_rows": live_context.get("current_live_structure_bucket_rows"),
            "supported_neighbor_buckets": live_context.get("supported_neighbor_buckets") or [],
            "collapse_feature_snapshot": live_context.get("collapse_feature_snapshot") or {},
        },
        "support_pathology_summary": support_summary_payload,
        "production_profile_role": production_profile_role,
        "bull_all": _cohort_summary("bull_all"),
        "bull_collapse_q35": _cohort_summary("bull_collapse_q35"),
        "bull_exact_live_lane_proxy": {} if live_specific_reference_only else _cohort_summary("bull_exact_live_lane_proxy"),
        "bull_live_exact_lane_bucket_proxy": {} if live_specific_reference_only else _cohort_summary("bull_live_exact_lane_bucket_proxy"),
        "bull_supported_neighbor_buckets_proxy": {} if live_specific_reference_only else _cohort_summary("bull_supported_neighbor_buckets_proxy"),
    }


def _current_leaderboard_support_progress() -> Dict[str, Any]:
    data_dir = Path(PROJECT_ROOT) / "data"
    live_probe = _read_json_file(data_dir / "live_predict_probe.json")
    q15_support = _read_json_file(data_dir / "q15_support_audit.json")
    current_signature = _current_leaderboard_candidate_semantic_signature() or {}
    current_bucket = current_signature.get("live_current_structure_bucket")

    deployment_blocker_details = live_probe.get("deployment_blocker_details") or {}
    probe_progress = live_probe.get("support_progress")
    if not isinstance(probe_progress, dict) or not probe_progress:
        probe_progress = deployment_blocker_details.get("support_progress") or {}
    probe_progress = dict(probe_progress) if isinstance(probe_progress, dict) else {}
    probe_timestamp = _safe_parse_datetime(
        live_probe.get("feature_timestamp")
        or deployment_blocker_details.get("feature_timestamp")
        or live_probe.get("generated_at")
    )

    support_route = q15_support.get("support_route") or {}
    current_live = q15_support.get("current_live") or {}
    q15_progress = support_route.get("support_progress")
    q15_progress = dict(q15_progress) if isinstance(q15_progress, dict) else {}
    q15_timestamp = _safe_parse_datetime(
        current_live.get("feature_timestamp")
        or q15_support.get("generated_at")
        or current_live.get("generated_at")
    )
    if (
        current_bucket
        and current_bucket == current_live.get("current_live_structure_bucket")
        and q15_progress
    ):
        if not probe_progress:
            return q15_progress

        progress_mismatch = (
            probe_progress.get("status") != q15_progress.get("status")
            or probe_progress.get("delta_vs_previous") != q15_progress.get("delta_vs_previous")
            or probe_progress.get("current_rows") != q15_progress.get("current_rows")
        )

        if q15_timestamp and probe_timestamp:
            if q15_timestamp >= probe_timestamp:
                return q15_progress
            return probe_progress if progress_mismatch else q15_progress
        if q15_timestamp and probe_timestamp is None:
            return q15_progress
        if probe_timestamp and q15_timestamp is None:
            return probe_progress
        return probe_progress if progress_mismatch else q15_progress

    return probe_progress



def _overlay_current_leaderboard_candidate_truth(diag: Dict[str, Any]) -> Dict[str, Any]:
    diag = dict(diag or {})
    current_signature = _current_leaderboard_candidate_semantic_signature() or {}
    current_progress = _current_leaderboard_support_progress()

    def _as_int(value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _sync_governance_contract(progress_override: Dict[str, Any] | None = None) -> None:
        governance_contract = dict(diag.get("governance_contract") or {})
        support_route = diag.get("support_governance_route")
        minimum_rows = _as_int(diag.get("minimum_support_rows"))
        live_rows = _as_int(diag.get("live_current_structure_bucket_rows"))
        gap_to_minimum = diag.get("live_current_structure_bucket_gap_to_minimum")
        if gap_to_minimum is None and minimum_rows is not None and live_rows is not None:
            gap_to_minimum = max(minimum_rows - live_rows, 0)
        support_progress = progress_override
        if support_progress is None:
            raw_progress = diag.get("support_progress")
            support_progress = raw_progress if isinstance(raw_progress, dict) and raw_progress else None

        if support_route:
            governance_contract["support_governance_route"] = support_route
        if minimum_rows is not None:
            governance_contract["minimum_support_rows"] = minimum_rows
        if live_rows is not None:
            governance_contract["live_current_structure_bucket_rows"] = live_rows
        if gap_to_minimum is not None:
            governance_contract["live_current_structure_bucket_gap_to_minimum"] = gap_to_minimum
        if support_progress:
            governance_contract["support_progress"] = support_progress
        if governance_contract:
            diag["governance_contract"] = governance_contract

    if not current_signature and not current_progress:
        _sync_governance_contract()
        return diag

    current_bucket = current_signature.get("live_current_structure_bucket")
    current_rows = _as_int(current_signature.get("live_current_structure_bucket_rows"))
    current_minimum = _as_int(current_signature.get("minimum_support_rows"))
    current_route = current_signature.get("support_governance_route")
    has_current_live_truth = any(
        value is not None and value != ""
        for value in (
            current_bucket,
            current_route,
            current_signature.get("live_regime_gate"),
            current_signature.get("live_entry_quality_label"),
            current_signature.get("live_execution_guardrail_reason"),
        )
    ) or bool((current_rows or 0) > 0 or (current_minimum or 0) > 0)
    if not has_current_live_truth:
        current_signature = {}
        current_bucket = None
        current_rows = None
        current_minimum = None
        current_route = None

    diag_progress = diag.get("support_progress") if isinstance(diag.get("support_progress"), dict) else {}
    progress_mismatch = bool(current_progress) and (
        not diag_progress
        or _as_int(diag_progress.get("current_rows")) != _as_int(current_progress.get("current_rows"))
        or diag_progress.get("status") != current_progress.get("status")
        or _as_int(diag_progress.get("delta_vs_previous")) != _as_int(current_progress.get("delta_vs_previous"))
    )
    live_truth_mismatch = bool(current_signature) and (
        diag.get("live_current_structure_bucket") != current_bucket
        or _as_int(diag.get("live_current_structure_bucket_rows")) != current_rows
        or (current_minimum is not None and _as_int(diag.get("minimum_support_rows")) != current_minimum)
        or (current_route and diag.get("support_governance_route") != current_route)
        or (
            current_signature.get("live_regime_gate") is not None
            and diag.get("live_regime_gate") != current_signature.get("live_regime_gate")
        )
        or (
            current_signature.get("live_entry_quality_label") is not None
            and diag.get("live_entry_quality_label") != current_signature.get("live_entry_quality_label")
        )
        or (
            current_signature.get("live_execution_guardrail_reason") is not None
            and diag.get("live_execution_guardrail_reason") != current_signature.get("live_execution_guardrail_reason")
        )
    )
    if not live_truth_mismatch and not progress_mismatch:
        _sync_governance_contract(current_progress)
        return diag

    recency = dict(diag.get("current_alignment_recency") or {})
    recency["inputs_current"] = False
    recency["live_truth_overlay_applied"] = True
    if live_truth_mismatch:
        recency["source_live_current_structure_bucket"] = diag.get("live_current_structure_bucket")
        recency["source_live_current_structure_bucket_rows"] = diag.get("live_current_structure_bucket_rows")
        recency["source_support_governance_route"] = diag.get("support_governance_route")
        diag["current_alignment_inputs_stale"] = True

    if current_signature:
        if current_bucket is not None:
            diag["live_current_structure_bucket"] = current_bucket
        if current_rows is not None:
            diag["live_current_structure_bucket_rows"] = current_rows
        if current_minimum is not None:
            diag["minimum_support_rows"] = current_minimum
        if current_route:
            diag["support_governance_route"] = current_route
        if current_signature.get("live_regime_gate") is not None:
            diag["live_regime_gate"] = current_signature.get("live_regime_gate")
        if current_signature.get("live_entry_quality_label") is not None:
            diag["live_entry_quality_label"] = current_signature.get("live_entry_quality_label")
        if current_signature.get("live_execution_guardrail_reason") is not None:
            diag["live_execution_guardrail_reason"] = current_signature.get("live_execution_guardrail_reason")

    minimum_rows = _as_int(diag.get("minimum_support_rows")) or 0
    live_rows = _as_int(diag.get("live_current_structure_bucket_rows")) or 0
    diag["live_current_structure_bucket_gap_to_minimum"] = max(minimum_rows - live_rows, 0)
    diag["current_alignment_recency"] = recency

    if current_progress:
        diag["support_progress"] = current_progress

    _sync_governance_contract(current_progress)

    return diag



def collect_leaderboard_candidate_diagnostics() -> Dict[str, Any]:
    result_path = Path(PROJECT_ROOT) / "data" / "leaderboard_feature_profile_probe.json"
    if not result_path.exists():
        return {}
    try:
        payload = json.loads(result_path.read_text())
    except Exception:
        return {}

    top_model = payload.get("top_model") or {}
    alignment = payload.get("alignment") or {}
    blocked_candidates = alignment.get("blocked_candidate_profiles") or []
    governance_contract = alignment.get("governance_contract") or {}
    diag = {
        "generated_at": payload.get("generated_at"),
        "target_col": payload.get("target_col"),
        "leaderboard_count": payload.get("leaderboard_count"),
        "selected_feature_profile": top_model.get("selected_feature_profile"),
        "selected_feature_profile_source": top_model.get("selected_feature_profile_source"),
        "selected_feature_profile_blocker_applied": top_model.get("selected_feature_profile_blocker_applied"),
        "selected_feature_profile_blocker_reason": top_model.get("selected_feature_profile_blocker_reason"),
        "dual_profile_state": alignment.get("dual_profile_state"),
        "profile_split": alignment.get("profile_split") or {},
        "governance_contract": governance_contract,
        "support_governance_route": alignment.get("support_governance_route") or governance_contract.get("support_governance_route"),
        "governance_current_closure": governance_contract.get("current_closure"),
        "governance_recommended_action": governance_contract.get("recommended_action"),
        "exact_bucket_root_cause": alignment.get("exact_bucket_root_cause"),
        "support_blocker_state": alignment.get("support_blocker_state"),
        "proxy_boundary_verdict": alignment.get("proxy_boundary_verdict"),
        "leaderboard_snapshot_created_at": alignment.get("leaderboard_snapshot_created_at"),
        "leaderboard_payload_source": payload.get("leaderboard_payload_source"),
        "leaderboard_payload_updated_at": payload.get("leaderboard_payload_updated_at"),
        "leaderboard_payload_cache_age_sec": payload.get("leaderboard_payload_cache_age_sec"),
        "leaderboard_payload_stale": payload.get("leaderboard_payload_stale"),
        "leaderboard_payload_error": payload.get("leaderboard_payload_error"),
        "alignment_evaluated_at": alignment.get("alignment_evaluated_at"),
        "current_alignment_inputs_stale": alignment.get("current_alignment_inputs_stale"),
        "current_alignment_recency": alignment.get("current_alignment_recency") or {},
        "artifact_recency": alignment.get("artifact_recency") or {},
        "global_recommended_profile": alignment.get("global_recommended_profile"),
        "train_selected_profile": alignment.get("train_selected_profile"),
        "train_selected_profile_source": alignment.get("train_selected_profile_source"),
        "train_support_cohort": alignment.get("train_support_cohort"),
        "train_support_rows": alignment.get("train_support_rows"),
        "train_exact_live_bucket_rows": alignment.get("train_exact_live_bucket_rows"),
        "live_regime_gate": alignment.get("live_regime_gate"),
        "live_entry_quality_label": alignment.get("live_entry_quality_label"),
        "live_execution_guardrail_reason": alignment.get("live_execution_guardrail_reason"),
        "live_current_structure_bucket": alignment.get("live_current_structure_bucket"),
        "live_current_structure_bucket_rows": alignment.get("live_current_structure_bucket_rows"),
        "minimum_support_rows": alignment.get("minimum_support_rows"),
        "live_current_structure_bucket_gap_to_minimum": alignment.get("live_current_structure_bucket_gap_to_minimum"),
        "support_progress": alignment.get("support_progress") or {},
        "supported_neighbor_buckets": alignment.get("supported_neighbor_buckets") or [],
        "bull_support_aware_profile": alignment.get("bull_support_aware_profile"),
        "bull_support_neighbor_rows": alignment.get("bull_support_neighbor_rows"),
        "bull_exact_live_bucket_proxy_rows": alignment.get("bull_exact_live_bucket_proxy_rows"),
        "blocked_candidate_profiles": blocked_candidates,
    }
    return _overlay_current_leaderboard_candidate_truth(diag)


def print_source_blockers(source_blockers: Dict[str, Any]) -> None:
    blocked = source_blockers.get("blocked_features", [])
    print(
        "🚧 Source blockers："
        f"{source_blockers.get('blocked_count', 0)} 個 blocked features，分布於 "
        f"{source_blockers.get('counts_by_history_class', {})}"
    )
    for row in blocked[:5]:
        archive_note = ""
        if row.get("raw_snapshot_events"):
            archive_note = (
                f" | forward_archive={row['raw_snapshot_events']}/"
                f"{row.get('forward_archive_ready_min_events', 10)}"
                f" ({row.get('forward_archive_status', 'missing')})"
            )
            if row.get("raw_snapshot_latest_age_min") is not None:
                archive_note += f" age={row['raw_snapshot_latest_age_min']:.1f}m"
        archive_window_note = ""
        if row.get("archive_window_started"):
            aw_cov = row.get("archive_window_coverage_pct")
            if aw_cov is None:
                archive_window_note = f" | archive_window=0/{row.get('archive_window_rows', 0)}"
            else:
                archive_window_note = (
                    f" | archive_window={aw_cov}%"
                    f" ({row.get('archive_window_non_null', 0)}/{row.get('archive_window_rows', 0)})"
                )
        status_note = ""
        if row.get("raw_snapshot_latest_status") and row.get("raw_snapshot_latest_status") != "ok":
            status_note = f" | latest_status={row['raw_snapshot_latest_status']}"
            if row.get("raw_snapshot_latest_message"):
                status_note += f" ({row['raw_snapshot_latest_message']})"
        print(
            f"   - {row['key']}: {row['history_class']} | "
            f"coverage={row.get('coverage_pct', 0)}%{archive_note}{archive_window_note}{status_note} | {row['recommended_action']}"
        )
    if len(blocked) > 5:
        print(f"   - ... {len(blocked) - 5} more blocked sparse features")


def main(argv=None):
    global _CURRENT_HEARTBEAT_RUN_LABEL, _CURRENT_HEARTBEAT_FAST_MODE
    args = parse_args(argv)
    run_label = resolve_run_label(args)
    _CURRENT_HEARTBEAT_RUN_LABEL = run_label
    _CURRENT_HEARTBEAT_FAST_MODE = bool(args.fast)
    run_start_monotonic = time.monotonic()
    progress_path = write_progress(
        run_label,
        "collect",
        details={
            "mode": "fast" if args.fast else "full",
            "tasks_requested": [task["name"] for task in TASKS],
            "fast": bool(args.fast),
            "fast_refresh_candidates": bool(getattr(args, "fast_refresh_candidates", False)),
            "no_collect": bool(args.no_collect),
            "no_train": bool(args.no_train),
            "no_dw": bool(args.no_dw),
        },
    )

    collect_result = run_collect_step(skip=args.no_collect)
    if collect_result.get("attempted"):
        print(
            f"🛰️ 心跳前 collect：{'通過' if collect_result['success'] else '失敗'} "
            f"(rc={collect_result['returncode']})"
        )
        if collect_result.get("stdout"):
            lines = collect_result["stdout"].split("\n")
            preview = "\n".join(lines[:40])
            if len(lines) > 40:
                preview += "\n...\n" + "\n".join(lines[-20:])
            print(f"\n--- hb_collect ---\n{preview}")
        if collect_result.get("stderr"):
            print(f"\n--- hb_collect stderr ---\n{collect_result['stderr']}")
        continuity_repair = parse_collect_metadata(collect_result.get("stdout", ""))
        if continuity_repair:
            print(
                "🩹 連續性修復明細："
                f"4h={continuity_repair.get('coarse_inserted', 0)}, "
                f"1h={continuity_repair.get('fine_inserted', 0)}, "
                f"bridge={continuity_repair.get('bridge_inserted', 0)}"
            )
            if continuity_repair.get("used_bridge"):
                print("⚠️  本輪 collect 觸發了插值 bridge fallback")

    write_progress(
        run_label,
        "counts_and_source_blockers",
        details={
            "collect_attempted": collect_result.get("attempted", False),
            "collect_success": collect_result.get("success", False),
        },
    )
    counts = quick_counts()
    source_blockers = collect_source_blockers()
    print(
        f"📊 DB 計數：Raw={counts['raw_market_data']}, Features={counts['features_normalized']}, "
        f"Labels={counts['labels']}, simulated_win={counts['simulated_pyramid_win_rate']}"
    )
    latest_raw_ts = counts.get('latest_raw_timestamp')
    for row in counts.get('label_horizons', []):
        print(
            f"   • labels[{row['horizon_minutes']}m]：rows={row['rows']} target_rows={row['target_rows']} "
            f"latest_target={row['latest_target_timestamp']} vs raw={latest_raw_ts}"
        )
    print_source_blockers(source_blockers)

    tasks = TASKS.copy()
    if args.no_train:
        tasks = [t for t in tasks if t["name"] != "train"]
    if args.no_dw:
        tasks = [t for t in tasks if t["name"] != "dynamic_window"]
    if args.fast:
        tasks = [t for t in tasks if t["name"] in ["full_ic", "regime_ic"]]
    tasks = [
        {
            **task,
            "timeout_seconds": _resolve_parallel_task_timeout(task["name"], fast_mode=bool(args.fast)),
        }
        for task in tasks
    ]

    needs_train = any(t["name"] == "train" for t in tasks)
    write_progress(
        run_label,
        "preflight",
        details={
            "task_names": [task["name"] for task in tasks],
            "task_timeouts": {task["name"]: task.get("timeout_seconds") for task in tasks},
            "needs_train": needs_train,
        },
    )
    preflight = refresh_train_prerequisites(needs_train)
    feature_ablation_result = preflight.get("feature_ablation_result")
    feature_ablation_summary = preflight.get("feature_ablation_summary") or {}
    bull_pocket_result = preflight.get("bull_pocket_result")
    bull_pocket_summary = preflight.get("bull_pocket_summary") or {}

    if feature_ablation_result is not None:
        print(
            f"📚 訓練前 Feature-group ablation：{'通過' if feature_ablation_result['success'] else '失敗'} "
            f"(rc={feature_ablation_result['returncode']})"
        )
        if feature_ablation_summary:
            recommended = feature_ablation_summary.get("recommended_metrics") or {}
            print(
                "📚 訓練前 shrinkage："
                f"mode={feature_ablation_summary.get('refresh_mode')} "
                f"profiles={len(feature_ablation_summary.get('profiles_evaluated') or [])} "
                f"recommended={feature_ablation_summary.get('recommended_profile')} "
                f"cv={recommended.get('cv_mean_accuracy')}"
            )
    if bull_pocket_result is not None:
        print(
            f"🐂 訓練前 Bull 4H pocket ablation：{'通過' if bull_pocket_result['success'] else '失敗'} "
            f"(rc={bull_pocket_result['returncode']})"
        )
        if bull_pocket_summary:
            live_context = bull_pocket_summary.get("live_context") or {}
            print(
                "🐂 訓練前 Bull pocket："
                f"current_bucket_rows={live_context.get('current_live_structure_bucket_rows')} "
                f"blocker={bull_pocket_summary.get('support_pathology_summary', {}).get('blocker_state')}"
            )

    print(f"心跳 #{run_label} 平行執行 — {len(tasks)} 個 tasks（{'fast' if args.fast else 'full'} 模式）")
    parallel_start = datetime.now()
    parallel_start_monotonic = time.monotonic()
    results = {}
    task_names = [task["name"] for task in tasks]
    write_progress(
        run_label,
        "parallel_tasks",
        details={
            "task_names": task_names,
            "completed": [],
            "pending": task_names,
            "passed": 0,
            "failed": 0,
            "elapsed_seconds": 0.0,
        },
    )
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(len(tasks), 5)) as ex:
        future_to_name = {ex.submit(run_task, t): t["name"] for t in tasks}
        pending_futures = set(future_to_name)
        last_completion_at = parallel_start_monotonic
        watchdog_heartbeats = 0
        while pending_futures:
            done, pending_futures = concurrent.futures.wait(
                pending_futures,
                timeout=15,
                return_when=concurrent.futures.FIRST_COMPLETED,
            )
            if not done:
                watchdog_heartbeats += 1
                elapsed_seconds = round(time.monotonic() - run_start_monotonic, 1)
                since_last_completion = round(time.monotonic() - last_completion_at, 1)
                pending_names = [future_to_name[future] for future in pending_futures]
                write_progress(
                    run_label,
                    "parallel_tasks",
                    details={
                        "task_names": task_names,
                        "completed": list(results.keys()),
                        "pending": pending_names,
                        "passed": sum(1 for result in results.values() if result["success"]),
                        "failed": sum(1 for result in results.values() if not result["success"]),
                        "elapsed_seconds": elapsed_seconds,
                        "watchdog": {
                            "heartbeat_count": watchdog_heartbeats,
                            "seconds_since_last_completion": since_last_completion,
                            "pending_tasks": pending_names,
                        },
                    },
                )
                print(
                    "⏱️  parallel watchdog："
                    f"elapsed={elapsed_seconds}s pending={','.join(pending_names)} "
                    f"since_last_completion={since_last_completion}s"
                )
                continue
            for future in done:
                name = future_to_name[future]
                task_result = future.result()
                if len(task_result) >= 5:
                    _, ok, out, err, returncode = task_result[:5]
                else:
                    _, ok, out, err = task_result
                    returncode = 0 if ok else 1
                timed_out = returncode == -1 and "TIMEOUT after" in str(err or "")
                results[name] = {
                    "success": ok,
                    "stdout": out,
                    "stderr": err,
                    "returncode": returncode,
                    "timed_out": timed_out,
                }
                last_completion_at = time.monotonic()
                completed = list(results.keys())
                write_progress(
                    run_label,
                    "parallel_tasks",
                    details={
                        "task_names": task_names,
                        "completed": completed,
                        "pending": [future_to_name[pending] for pending in pending_futures],
                        "passed": sum(1 for result in results.values() if result["success"]),
                        "failed": sum(1 for result in results.values() if not result["success"]),
                        "last_completed_task": name,
                        "last_completed_success": ok,
                        "elapsed_seconds": round(time.monotonic() - run_start_monotonic, 1),
                        "watchdog": {
                            "heartbeat_count": watchdog_heartbeats,
                            "seconds_since_last_completion": 0.0,
                        },
                    },
                )
                print(f"  [{'✅' if ok else '❌'}] {name}")

    run_elapsed_seconds = round(time.monotonic() - run_start_monotonic, 1)
    passed = sum(1 for r in results.values() if r["success"])
    print(f"\n  {passed}/{len(results)} 通過（{run_elapsed_seconds:.1f}s）")

    for name, r in results.items():
        if r.get("stdout"):
            lines = r['stdout'].split('\n')
            display = '\n'.join(lines[:50])
            if len(lines) > 50:
                display += '\n...\n' + '\n'.join(lines[-30:])
            print(f"\n--- {name} ---\n{display}")
        if r.get("stderr"):
            stderr_lines = r['stderr'].strip().split('\n')
            errors = [
                line for line in stderr_lines
                if line.strip() and not line.startswith('Deprecation') and not line.startswith('FutureWarning')
            ]
            if errors:
                print(f"\n--- {name} stderr ---\n" + '\n'.join(errors[:20]))

    ic_diagnostics = collect_ic_diagnostics()
    if ic_diagnostics:
        print(
            "\n📉 IC 診斷："
            f"Global={ic_diagnostics.get('global_pass')}/{ic_diagnostics.get('total_features')} | "
            f"TW-IC={ic_diagnostics.get('tw_pass')}/{ic_diagnostics.get('total_features')}"
        )

    write_progress(run_label, "recent_drift_report")
    drift_report_result = run_recent_drift_report()
    drift_diagnostics = collect_recent_drift_diagnostics()
    print(
        f"🧭 近期漂移報告：{'通過' if drift_report_result['success'] else '失敗'} "
        f"(rc={drift_report_result['returncode']})"
    )
    if drift_report_result.get("stdout"):
        lines = drift_report_result["stdout"].split("\n")
        preview = "\n".join(lines[:20])
        if len(lines) > 20:
            preview += "\n...\n" + "\n".join(lines[-8:])
        print(f"\n--- recent_drift_report ---\n{preview}")
    if drift_report_result.get("stderr"):
        print(f"\n--- recent_drift_report stderr ---\n{drift_report_result['stderr']}")
    if drift_diagnostics:
        primary = drift_diagnostics.get("primary_summary") or {}
        feature_diag = primary.get("feature_diagnostics") or {}
        path_diag = primary.get("target_path_diagnostics") or {}
        tail_streak = path_diag.get("tail_target_streak") or {}
        print(
            "🧭 漂移診斷："
            f"window={drift_diagnostics.get('primary_window')} "
            f"alerts={drift_diagnostics.get('primary_alerts')} "
            f"win_rate={primary.get('win_rate')} "
            f"dominant_regime={primary.get('dominant_regime')} "
            f"feature_diag=variance:{feature_diag.get('low_variance_count', 0)}/{feature_diag.get('feature_count', 0)} "
            f"frozen:{feature_diag.get('frozen_count', 0)} compressed:{feature_diag.get('compressed_count', 0)} "
            f"distinct:{feature_diag.get('low_distinct_count', 0)} null_heavy:{feature_diag.get('null_heavy_count', 0)} "
            f"tail_streak={tail_streak.get('count', 0)}x{tail_streak.get('target')} since {tail_streak.get('start_timestamp')}"
        )

    # Heartbeat #fast carry-forward fix:
    # run q35 audit BEFORE the public live probe so the audit can establish the latest
    # current-row runtime truth first. Otherwise the runner can snapshot a pre-audit
    # probe state and leak stale q35 redesign fields into the heartbeat summary.
    write_progress(run_label, "q35_scaling_audit")
    q35_scaling_result = run_q35_scaling_audit()
    q35_scaling_summary: Dict[str, Any] = collect_q35_scaling_audit_diagnostics()
    print(
        f"🧮 Q35 scaling audit：{'通過' if q35_scaling_result['success'] else '失敗'} "
        f"(rc={q35_scaling_result['returncode']})"
    )
    if q35_scaling_result.get("stdout"):
        lines = q35_scaling_result["stdout"].split("\n")
        preview = "\n".join(lines[:20])
        if len(lines) > 20:
            preview += "\n...\n" + "\n".join(lines[-8:])
        print(f"\n--- hb_q35_scaling_audit ---\n{preview}")
    if q35_scaling_result.get("stderr"):
        print(f"\n--- hb_q35_scaling_audit stderr ---\n{q35_scaling_result['stderr']}")
    if q35_scaling_summary:
        broader_bull = q35_scaling_summary.get("broader_bull_cohorts") or {}
        bull_all = broader_bull.get("bull_all") or {}
        segmented = q35_scaling_summary.get('segmented_calibration') or {}
        reference = segmented.get('reference_cohort') or {}
        applicability = q35_scaling_summary.get('scope_applicability') or {}
        deployment_experiment = q35_scaling_summary.get('deployment_grade_component_experiment') or {}
        joint_experiment = q35_scaling_summary.get('joint_component_experiment') or {}
        exact_supported_bias50_experiment = q35_scaling_summary.get('exact_supported_bias50_component_experiment') or {}
        redesign_experiment = q35_scaling_summary.get('base_stack_redesign_experiment') or {}
        machine_read = deployment_experiment.get('machine_read_answer') or {}
        joint_machine_read = joint_experiment.get('machine_read_answer') or {}
        exact_supported_machine_read = exact_supported_bias50_experiment.get('machine_read_answer') or {}
        redesign_machine_read = redesign_experiment.get('machine_read_answer') or {}
        joint_best = joint_experiment.get('best_scenario') or {}
        exact_supported_best = exact_supported_bias50_experiment.get('best_scenario') or {}
        redesign_best = redesign_experiment.get('best_discriminative_candidate') or {}
        baseline_current = q35_scaling_summary.get('baseline_current_live') or {}
        calibration_runtime = q35_scaling_summary.get('calibration_runtime_current') or {}
        deployed_current = q35_scaling_summary.get('current_live') or {}
        print(
            "🧮 Q35 結論："
            f"verdict={q35_scaling_summary.get('overall_verdict')} "
            f"structure={q35_scaling_summary.get('structure_scaling_verdict')} "
            f"applicability={applicability.get('status')} "
            f"segment_status={segmented.get('status')} "
            f"runtime_status={segmented.get('runtime_contract_status')} "
            f"reference={reference.get('cohort')} "
            f"exact_bias50_pct={((q35_scaling_summary.get('exact_lane_summary') or {}).get('current_bias50_percentile'))} "
            f"bull_all_bias50_pct={bull_all.get('current_bias50_percentile')} "
            f"gate_only_changes_layers={((q35_scaling_summary.get('counterfactuals') or {}).get('gate_allow_only_changes_layers'))} "
            f"baseline_eq={baseline_current.get('entry_quality')} "
            f"calibration_eq={calibration_runtime.get('entry_quality')} "
            f"runtime_eq={deployment_experiment.get('runtime_entry_quality')} "
            f"runtime_gap={deployment_experiment.get('runtime_remaining_gap_to_floor')} "
            f"runtime_source={deployment_experiment.get('runtime_source')} "
            f"redesign_applied={deployment_experiment.get('q35_discriminative_redesign_applied')} "
            f"eq_ge_0.55={machine_read.get('entry_quality_ge_0_55')} "
            f"layers_gt_0={machine_read.get('allowed_layers_gt_0')} "
            f"runtime_layers={deployed_current.get('allowed_layers_raw')} "
            f"joint_verdict={joint_experiment.get('verdict')} "
            f"joint_best={joint_best.get('scenario')} "
            f"joint_eq={joint_best.get('entry_quality_after')} "
            f"joint_gap={joint_best.get('remaining_gap_to_floor')} "
            f"joint_layers_gt_0={joint_machine_read.get('allowed_layers_gt_0')} "
            f"bias50_exact_verdict={exact_supported_bias50_experiment.get('verdict')} "
            f"bias50_exact_best={exact_supported_best.get('scenario')} "
            f"bias50_exact_eq={exact_supported_best.get('entry_quality_after')} "
            f"bias50_exact_gap={exact_supported_best.get('remaining_gap_to_floor')} "
            f"bias50_exact_layers_gt_0={exact_supported_machine_read.get('allowed_layers_gt_0')} "
            f"redesign_verdict={redesign_experiment.get('verdict')} "
            f"redesign_eq={redesign_best.get('current_entry_quality_after')} "
            f"redesign_gap={redesign_best.get('remaining_gap_to_floor')} "
            f"redesign_pos_gap={redesign_machine_read.get('positive_discriminative_gap')}"
        )

    write_progress(run_label, "live_predict_probe")
    predict_probe_result = run_predict_probe()
    _persist_live_predictor_probe(predict_probe_result.get("stdout", ""))
    live_predictor_diagnostics = collect_live_predictor_diagnostics(predict_probe_result)
    print(
        f"🧪 Live predictor probe：{'通過' if predict_probe_result['success'] else '失敗'} "
        f"(rc={predict_probe_result['returncode']})"
    )
    if predict_probe_result.get("stdout"):
        lines = predict_probe_result["stdout"].split("\n")
        preview = "\n".join(lines[:40])
        if len(lines) > 40:
            preview += "\n...\n" + "\n".join(lines[-12:])
        print(f"\n--- hb_predict_probe ---\n{preview}")
    if predict_probe_result.get("stderr"):
        print(f"\n--- hb_predict_probe stderr ---\n{predict_probe_result['stderr']}")
    if live_predictor_diagnostics:
        consensus = live_predictor_diagnostics.get("decision_quality_pathology_consensus") or {}
        shared = consensus.get("shared_top_shift_features") or []
        shared_text = "/".join(
            f"{row.get('feature')}[x{row.get('scope_count')}]"
            for row in shared[:2]
            if row.get("feature")
        )
        worst_scope = consensus.get("worst_pathology_scope") or {}
        extra = ""
        if shared_text:
            extra += f" shared={shared_text}"
        if worst_scope.get("scope"):
            extra += (
                f" worst_scope={worst_scope.get('scope')}"
                f"(wr={worst_scope.get('win_rate')},q={worst_scope.get('avg_quality')})"
            )
        blocker_extra = ""
        if live_predictor_diagnostics.get("deployment_blocker"):
            blocker_extra = f" deployment_blocker={live_predictor_diagnostics.get('deployment_blocker')}"
        print(
            "🧪 Live 決策品質："
            f"scope={live_predictor_diagnostics.get('decision_quality_calibration_scope')} "
            f"win={live_predictor_diagnostics.get('expected_win_rate')} "
            f"quality={live_predictor_diagnostics.get('expected_pyramid_quality')} "
            f"label={live_predictor_diagnostics.get('decision_quality_label')} "
            f"layers={live_predictor_diagnostics.get('allowed_layers_raw')}→{live_predictor_diagnostics.get('allowed_layers')} "
            f"recent_pathology={live_predictor_diagnostics.get('decision_quality_recent_pathology_applied')}"
            f"{blocker_extra}"
            f"{extra}"
        )

    write_progress(run_label, "live_decision_drilldown")
    live_drilldown_result = run_live_decision_quality_drilldown()
    live_drilldown_summary: Dict[str, Any] = {}
    print(
        f"🧭 Live DQ drilldown：{'通過' if live_drilldown_result['success'] else '失敗'} "
        f"(rc={live_drilldown_result['returncode']})"
    )
    if live_drilldown_result.get("stdout"):
        lines = live_drilldown_result["stdout"].split("\n")
        preview = "\n".join(lines[:20])
        if len(lines) > 20:
            preview += "\n...\n" + "\n".join(lines[-8:])
        print(f"\n--- live_decision_quality_drilldown ---\n{preview}")
    live_drilldown_summary = collect_live_decision_quality_drilldown_diagnostics(live_drilldown_result)
    if live_drilldown_result.get("stderr"):
        print(f"\n--- live_decision_quality_drilldown stderr ---\n{live_drilldown_result['stderr']}")

    q15_support_result: Dict[str, Any] = {}
    q15_support_summary: Dict[str, Any] = {}
    q15_boundary_replay_result: Dict[str, Any] = {}
    q15_boundary_replay_summary: Dict[str, Any] = {}

    write_progress(run_label, "circuit_breaker_audit")
    circuit_breaker_audit_result = run_circuit_breaker_audit(run_label)
    circuit_breaker_audit_summary: Dict[str, Any] = collect_circuit_breaker_audit_diagnostics()
    print(
        f"🛑 Circuit breaker audit：{'通過' if circuit_breaker_audit_result['success'] else '失敗'} "
        f"(rc={circuit_breaker_audit_result['returncode']})"
    )
    if circuit_breaker_audit_result.get("stdout"):
        lines = circuit_breaker_audit_result["stdout"].split("\n")
        preview = "\n".join(lines[:20])
        if len(lines) > 20:
            preview += "\n...\n" + "\n".join(lines[-8:])
        print(f"\n--- hb_circuit_breaker_audit ---\n{preview}")
    if circuit_breaker_audit_result.get("stderr"):
        print(f"\n--- hb_circuit_breaker_audit stderr ---\n{circuit_breaker_audit_result['stderr']}")
    if circuit_breaker_audit_summary:
        root = circuit_breaker_audit_summary.get("root_cause") or {}
        mixed_scope = circuit_breaker_audit_summary.get("mixed_scope") or {}
        aligned_scope = circuit_breaker_audit_summary.get("aligned_scope") or {}
        print(
            "🛑 Breaker 根因："
            f"verdict={root.get('verdict')} "
            f"mixed={mixed_scope.get('triggered_by')} streak={((mixed_scope.get('streak') or {}).get('count'))} "
            f"aligned={aligned_scope.get('triggered_by')} release_ready={aligned_scope.get('release_ready')}"
        )

    refresh_candidate_eval_lanes = (not args.fast) or bool(getattr(args, "fast_refresh_candidates", False))

    if feature_ablation_result is None:
        if refresh_candidate_eval_lanes:
            feature_ablation_result = run_feature_group_ablation()
            feature_ablation_summary = collect_feature_ablation_diagnostics()
            print(
                f"📚 Feature-group ablation：{'通過' if feature_ablation_result['success'] else '失敗'} "
                f"(rc={feature_ablation_result['returncode']})"
            )
            if feature_ablation_result.get("stdout"):
                lines = feature_ablation_result["stdout"].split("\n")
                preview = "\n".join(lines[:20])
                if len(lines) > 20:
                    preview += "\n...\n" + "\n".join(lines[-8:])
                print(f"\n--- feature_group_ablation ---\n{preview}")
            if feature_ablation_result.get("stderr"):
                print(f"\n--- feature_group_ablation stderr ---\n{feature_ablation_result['stderr']}")
        else:
            artifact_path = Path(PROJECT_ROOT) / "data" / "feature_group_ablation.json"
            feature_ablation_result = _build_skipped_serial_result(
                "feature_group_ablation",
                reason="fast_mode_candidate_refresh_disabled",
                artifact_path=artifact_path,
            )
            feature_ablation_summary = collect_feature_ablation_diagnostics()
            write_progress(
                run_label,
                "feature_group_ablation",
                status="skipped",
                details={
                    "skip_reason": "fast_mode_candidate_refresh_disabled",
                    "artifact_path": str(artifact_path),
                    "refresh_with": "--fast --fast-refresh-candidates",
                },
            )
            print(
                "⏭️  Feature-group ablation：fast mode 預設跳過 candidate refresh；"
                "沿用既有 artifact 做 docs/governance 摘要。"
            )
    if feature_ablation_summary:
        recommended = feature_ablation_summary.get("recommended_metrics") or {}
        current_full = feature_ablation_summary.get("current_full_metrics") or {}
        print(
            "📚 Feature shrinkage："
            f"mode={feature_ablation_summary.get('refresh_mode')} "
            f"profiles={len(feature_ablation_summary.get('profiles_evaluated') or [])} "
            f"recommended={feature_ablation_summary.get('recommended_profile')} "
            f"cv={recommended.get('cv_mean_accuracy')} "
            f"worst={recommended.get('cv_worst_accuracy')} "
            f"vs current_full={current_full.get('cv_mean_accuracy')}"
        )

    if bull_pocket_result is None:
        if refresh_candidate_eval_lanes:
            bull_pocket_result = run_bull_4h_pocket_ablation()
            bull_pocket_summary = collect_bull_4h_pocket_diagnostics()
            print(
                f"🐂 Bull 4H pocket ablation：{'通過' if bull_pocket_result['success'] else '失敗'} "
                f"(rc={bull_pocket_result['returncode']})"
            )
            if bull_pocket_result.get("stdout"):
                lines = bull_pocket_result["stdout"].split("\n")
                preview = "\n".join(lines[:20])
                if len(lines) > 20:
                    preview += "\n...\n" + "\n".join(lines[-8:])
                print(f"\n--- bull_4h_pocket_ablation ---\n{preview}")
            if bull_pocket_result.get("stderr"):
                print(f"\n--- bull_4h_pocket_ablation stderr ---\n{bull_pocket_result['stderr']}")
        else:
            artifact_path = Path(PROJECT_ROOT) / "data" / "bull_4h_pocket_ablation.json"
            bull_pocket_result = _build_skipped_serial_result(
                "bull_4h_pocket_ablation",
                reason="fast_mode_candidate_refresh_disabled",
                artifact_path=artifact_path,
            )
            bull_pocket_summary = collect_bull_4h_pocket_diagnostics()
            write_progress(
                run_label,
                "bull_4h_pocket_ablation",
                status="skipped",
                details={
                    "skip_reason": "fast_mode_candidate_refresh_disabled",
                    "artifact_path": str(artifact_path),
                    "refresh_with": "--fast --fast-refresh-candidates",
                },
            )
            print(
                "⏭️  Bull 4H pocket ablation：fast mode 預設跳過 candidate refresh；"
                "沿用既有 artifact 做 live-support governance 摘要。"
            )
    if bull_pocket_summary:
        collapse = bull_pocket_summary.get("bull_collapse_q35") or {}
        live_bucket = bull_pocket_summary.get("bull_live_exact_lane_bucket_proxy") or {}
        neighbors = bull_pocket_summary.get("bull_supported_neighbor_buckets_proxy") or {}
        live_context = bull_pocket_summary.get("live_context") or {}
        semantic_alignment = bull_pocket_summary.get("semantic_alignment") or {}
        semantic_note = ""
        if semantic_alignment.get("live_specific_reference_only"):
            semantic_note = f" {semantic_alignment.get('refresh_mode') or 'reference_only'}"
        print(
            "🐂 Bull pocket："
            f"collapse_best={collapse.get('recommended_profile')} "
            f"live_bucket_rows={live_bucket.get('rows')} best={live_bucket.get('recommended_profile')} "
            f"neighbor_rows={neighbors.get('rows')} best={neighbors.get('recommended_profile')} "
            f"current_bucket_rows={live_context.get('current_live_structure_bucket_rows')}"
            f"{semantic_note}"
        )

    leaderboard_artifact_path = Path(PROJECT_ROOT) / "data" / "leaderboard_feature_profile_probe.json"
    write_progress(run_label, "leaderboard_candidate_probe")
    if refresh_candidate_eval_lanes:
        leaderboard_probe_result = run_leaderboard_candidate_probe(run_label)
        leaderboard_candidate_diagnostics = collect_leaderboard_candidate_diagnostics()
        print(
            f"🏁 Leaderboard candidate probe：{'通過' if leaderboard_probe_result['success'] else '失敗'} "
            f"(rc={leaderboard_probe_result['returncode']})"
        )
        if leaderboard_probe_result.get("stdout"):
            lines = leaderboard_probe_result["stdout"].split("\n")
            preview = "\n".join(lines[:20])
            if len(lines) > 20:
                preview += "\n...\n" + "\n".join(lines[-8:])
            print(f"\n--- hb_leaderboard_candidate_probe ---\n{preview}")
        if leaderboard_probe_result.get("stderr"):
            print(f"\n--- hb_leaderboard_candidate_probe stderr ---\n{leaderboard_probe_result['stderr']}")
    else:
        alignment_refresh_payload = None
        alignment_refresh_applied = False
        if leaderboard_artifact_path.exists():
            alignment_refresh_payload = _refresh_leaderboard_candidate_alignment_snapshot(
                leaderboard_artifact_path,
                allow_rebuild=False,
            )
            alignment_refresh_applied = alignment_refresh_payload is not None

        leaderboard_probe_result = _build_skipped_serial_result(
            "hb_leaderboard_candidate_probe",
            reason=(
                "fast_mode_alignment_refresh_only"
                if alignment_refresh_applied
                else "fast_mode_candidate_refresh_disabled"
            ),
            artifact_path=leaderboard_artifact_path,
        )
        if alignment_refresh_applied:
            leaderboard_probe_result["alignment_refresh_only"] = True
            leaderboard_probe_result["refresh_applied"] = True
            leaderboard_probe_result["generated_at"] = alignment_refresh_payload.get("generated_at")
        leaderboard_candidate_diagnostics = collect_leaderboard_candidate_diagnostics()
        write_progress(
            run_label,
            "leaderboard_candidate_probe",
            status="skipped",
            details={
                "skip_reason": (
                    "fast_mode_alignment_refresh_only"
                    if alignment_refresh_applied
                    else "fast_mode_candidate_refresh_disabled"
                ),
                "artifact_path": str(leaderboard_artifact_path),
                "alignment_refresh_only": alignment_refresh_applied,
                "refresh_with": "--fast --fast-refresh-candidates",
            },
        )
        if alignment_refresh_applied:
            print(
                "⏭️  Leaderboard candidate probe：fast mode 僅刷新 current-live alignment snapshot；"
                "沿用既有 leaderboard payload 並更新 governance 對齊時間戳。"
            )
        else:
            print(
                "⏭️  Leaderboard candidate probe：fast mode 預設跳過 candidate refresh；"
                "沿用既有 artifact 做 governance 摘要。"
            )
    if leaderboard_candidate_diagnostics:
        blocked = leaderboard_candidate_diagnostics.get("blocked_candidate_profiles") or []
        blocked_text = ",".join(
            f"{row.get('feature_profile')}:{row.get('blocker_reason')}"
            for row in blocked[:2]
            if row.get("feature_profile")
        )
        current_alignment = leaderboard_candidate_diagnostics.get("current_alignment_recency") or {}
        support_progress = leaderboard_candidate_diagnostics.get("support_progress") or {}
        print(
            "🏁 Candidate 對齊："
            f"leaderboard={leaderboard_candidate_diagnostics.get('selected_feature_profile')} "
            f"train={leaderboard_candidate_diagnostics.get('train_selected_profile')} "
            f"global={leaderboard_candidate_diagnostics.get('global_recommended_profile')} "
            f"state={leaderboard_candidate_diagnostics.get('dual_profile_state')} "
            f"route={leaderboard_candidate_diagnostics.get('support_governance_route')} "
            f"governance={((leaderboard_candidate_diagnostics.get('governance_contract') or {}).get('verdict'))} "
            f"closure={leaderboard_candidate_diagnostics.get('governance_current_closure')} "
            f"support={support_progress.get('status')} Δ={support_progress.get('delta_vs_previous')} "
            f"runtime_inputs_current={current_alignment.get('inputs_current')} "
            f"payload_source={leaderboard_candidate_diagnostics.get('leaderboard_payload_source')} "
            f"snapshot_stale={(leaderboard_candidate_diagnostics.get('artifact_recency') or {}).get('alignment_snapshot_stale')} "
            f"live_bucket_rows={leaderboard_candidate_diagnostics.get('live_current_structure_bucket_rows')}"
            f" blocked={blocked_text or 'none'}"
        )

    write_progress(run_label, "q15_support_audit")
    q15_support_result = run_q15_support_audit()
    q15_support_summary = collect_q15_support_audit_diagnostics()
    print(
        f"🧩 Q15 support audit：{'通過' if q15_support_result['success'] else '失敗'} "
        f"(rc={q15_support_result['returncode']})"
    )
    if q15_support_result.get("stdout"):
        lines = q15_support_result["stdout"].split("\n")
        preview = "\n".join(lines[:20])
        if len(lines) > 20:
            preview += "\n...\n" + "\n".join(lines[-8:])
        print(f"\n--- hb_q15_support_audit ---\n{preview}")
    if q15_support_result.get("stderr"):
        print(f"\n--- hb_q15_support_audit stderr ---\n{q15_support_result['stderr']}")
    if q15_support_summary:
        scope = q15_support_summary.get("scope_applicability") or {}
        support = q15_support_summary.get("support_route") or {}
        floor = q15_support_summary.get("floor_cross_legality") or {}
        experiment = q15_support_summary.get("component_experiment") or {}
        experiment_answer = experiment.get("machine_read_answer") or {}
        print(
            "🧩 Q15 治理："
            f"scope={scope.get('status')} active={scope.get('active_for_current_live_row')} "
            f"support={support.get('verdict')} deployable={support.get('deployable')} "
            f"floor={floor.get('verdict')} legal={floor.get('legal_to_relax_runtime_gate')} "
            f"best={floor.get('best_single_component')} gap={floor.get('remaining_gap_to_floor')} "
            f"experiment={experiment.get('verdict')} "
            f"entry55={experiment_answer.get('entry_quality_ge_0_55')} "
            f"layers>0={experiment_answer.get('allowed_layers_gt_0')}"
        )

    q15_runtime_resync = {"triggered": False, "reason": None, "message": None}
    resync_reason = _q15_post_audit_runtime_resync_reason(live_predictor_diagnostics, q15_support_summary)
    if resync_reason:
        resync_message = _format_q15_post_audit_runtime_resync_message(resync_reason)
        q15_runtime_resync = {
            "triggered": True,
            "reason": resync_reason,
            "message": resync_message,
        }
        print(resync_message)
        write_progress(run_label, "q15_runtime_resync_probe")
        predict_probe_result = run_predict_probe()
        _persist_live_predictor_probe(predict_probe_result.get("stdout", ""))
        live_predictor_diagnostics = collect_live_predictor_diagnostics(predict_probe_result)
        print(
            f"🧪 Q15 resynced live probe：{'通過' if predict_probe_result['success'] else '失敗'} "
            f"(rc={predict_probe_result['returncode']})"
        )
        if predict_probe_result.get("stdout"):
            lines = predict_probe_result["stdout"].split("\n")
            preview = "\n".join(lines[:20])
            if len(lines) > 20:
                preview += "\n...\n" + "\n".join(lines[-8:])
            print(f"\n--- hb_predict_probe (resynced) ---\n{preview}")
        if predict_probe_result.get("stderr"):
            print(f"\n--- hb_predict_probe (resynced) stderr ---\n{predict_probe_result['stderr']}")

        write_progress(run_label, "q15_runtime_resync_drilldown")
        live_drilldown_result = run_live_decision_quality_drilldown()
        live_drilldown_summary = collect_live_decision_quality_drilldown_diagnostics(live_drilldown_result)
        print(
            f"🧭 Q15 resynced drilldown：{'通過' if live_drilldown_result['success'] else '失敗'} "
            f"(rc={live_drilldown_result['returncode']})"
        )
        if live_drilldown_result.get("stdout"):
            lines = live_drilldown_result["stdout"].split("\n")
            preview = "\n".join(lines[:20])
            if len(lines) > 20:
                preview += "\n...\n" + "\n".join(lines[-8:])
            print(f"\n--- live_decision_quality_drilldown (resynced) ---\n{preview}")
        if live_drilldown_result.get("stderr"):
            print(f"\n--- live_decision_quality_drilldown (resynced) stderr ---\n{live_drilldown_result['stderr']}")

    if leaderboard_artifact_path.exists():
        _refresh_leaderboard_candidate_alignment_snapshot(
            leaderboard_artifact_path,
            allow_rebuild=False,
        )
        refreshed_leaderboard_candidate_diagnostics = collect_leaderboard_candidate_diagnostics()
        if refreshed_leaderboard_candidate_diagnostics:
            leaderboard_candidate_diagnostics = refreshed_leaderboard_candidate_diagnostics

    write_progress(run_label, "q15_bucket_root_cause")
    q15_bucket_root_cause_result = run_q15_bucket_root_cause()
    q15_bucket_root_cause_summary = collect_q15_bucket_root_cause_diagnostics()
    print(
        f"🪣 Q15 root-cause：{'通過' if q15_bucket_root_cause_result['success'] else '失敗'} "
        f"(rc={q15_bucket_root_cause_result['returncode']})"
    )
    if q15_bucket_root_cause_result.get("stdout"):
        lines = q15_bucket_root_cause_result["stdout"].split("\n")
        preview = "\n".join(lines[:20])
        if len(lines) > 20:
            preview += "\n...\n" + "\n".join(lines[-8:])
        print(f"\n--- hb_q15_bucket_root_cause ---\n{preview}")
    if q15_bucket_root_cause_result.get("stderr"):
        print(f"\n--- hb_q15_bucket_root_cause stderr ---\n{q15_bucket_root_cause_result['stderr']}")
    if q15_bucket_root_cause_summary:
        lane = q15_bucket_root_cause_summary.get("exact_live_lane") or {}
        print(
            "🪣 Q15 根因："
            f"verdict={q15_bucket_root_cause_summary.get('verdict')} "
            f"patch={q15_bucket_root_cause_summary.get('candidate_patch_type')}:{q15_bucket_root_cause_summary.get('candidate_patch_feature')} "
            f"neighbor={lane.get('dominant_neighbor_bucket')} rows={lane.get('dominant_neighbor_rows')} "
            f"near_boundary_rows={lane.get('near_boundary_rows')}"
        )

    write_progress(run_label, "q15_boundary_replay")
    q15_boundary_replay_result = run_q15_boundary_replay()
    q15_boundary_replay_summary = collect_q15_boundary_replay_diagnostics()
    print(
        f"🔁 Q15 boundary replay：{'通過' if q15_boundary_replay_result['success'] else '失敗'} "
        f"(rc={q15_boundary_replay_result['returncode']})"
    )
    if q15_boundary_replay_result.get("stdout"):
        lines = q15_boundary_replay_result["stdout"].split("\n")
        preview = "\n".join(lines[:20])
        if len(lines) > 20:
            preview += "\n...\n" + "\n".join(lines[-8:])
        print(f"\n--- hb_q15_boundary_replay ---\n{preview}")
    if q15_boundary_replay_result.get("stderr"):
        print(f"\n--- hb_q15_boundary_replay stderr ---\n{q15_boundary_replay_result['stderr']}")
    if q15_boundary_replay_summary:
        replay = q15_boundary_replay_summary.get("boundary_replay") or {}
        counterfactual = q15_boundary_replay_summary.get("component_counterfactual") or {}
        print(
            "🔁 Q15 replay："
            f"verdict={q15_boundary_replay_summary.get('verdict')} "
            f"replay_bucket={replay.get('replay_bucket')} rows={replay.get('replay_scope_bucket_rows')} "
            f"generated_only={replay.get('generated_rows_via_boundary_only')} "
            f"counterfactual={counterfactual.get('verdict')} "
            f"layers_after={counterfactual.get('allowed_layers_after')}"
        )

    write_progress(run_label, "auto_propose")
    auto_propose_result = run_auto_propose(run_label)
    print(
        f"🛠️  自動修復建議：{'通過' if auto_propose_result['success'] else '失敗'} "
        f"(rc={auto_propose_result['returncode']})"
    )
    if auto_propose_result.get("stdout"):
        lines = auto_propose_result["stdout"].split("\n")
        preview = "\n".join(lines[:25])
        if len(lines) > 25:
            preview += "\n...\n" + "\n".join(lines[-10:])
        print(f"\n--- auto_propose_fixes ---\n{preview}")
    if auto_propose_result.get("stderr"):
        print(f"\n--- auto_propose_fixes stderr ---\n{auto_propose_result['stderr']}")

    serial_result_payload = {
        "recent_drift_report": {
            "result": drift_report_result,
            "diagnostics": drift_diagnostics,
            "artifact_path": Path(PROJECT_ROOT) / "data" / "recent_drift_report.json",
        },
        "hb_q35_scaling_audit": {
            "result": q35_scaling_result,
            "diagnostics": q35_scaling_summary,
            "artifact_path": Path(PROJECT_ROOT) / "data" / "q35_scaling_audit.json",
        },
        "hb_predict_probe": {
            "result": predict_probe_result,
            "diagnostics": live_predictor_diagnostics,
            "artifact_path": Path(PROJECT_ROOT) / "data" / "live_predict_probe.json",
        },
        "live_decision_quality_drilldown": {
            "result": live_drilldown_result,
            "diagnostics": live_drilldown_summary,
            "artifact_path": (live_drilldown_summary or {}).get("json") or (Path(PROJECT_ROOT) / "data" / "live_decision_quality_drilldown.json"),
        },
        "hb_circuit_breaker_audit": {
            "result": circuit_breaker_audit_result,
            "diagnostics": circuit_breaker_audit_summary,
            "artifact_path": Path(PROJECT_ROOT) / "data" / f"circuit_breaker_audit_{run_label}.json",
        },
        "feature_group_ablation": {
            "result": feature_ablation_result,
            "diagnostics": feature_ablation_summary,
            "artifact_path": Path(PROJECT_ROOT) / "data" / "feature_group_ablation.json",
        },
        "bull_4h_pocket_ablation": {
            "result": bull_pocket_result,
            "diagnostics": bull_pocket_summary,
            "artifact_path": Path(PROJECT_ROOT) / "data" / "bull_4h_pocket_ablation.json",
        },
        "hb_leaderboard_candidate_probe": {
            "result": leaderboard_probe_result,
            "diagnostics": leaderboard_candidate_diagnostics,
            "artifact_path": Path(PROJECT_ROOT) / "data" / "leaderboard_feature_profile_probe.json",
        },
        "hb_q15_support_audit": {
            "result": q15_support_result,
            "diagnostics": q15_support_summary,
            "artifact_path": Path(PROJECT_ROOT) / "data" / "q15_support_audit.json",
        },
        "hb_q15_bucket_root_cause": {
            "result": q15_bucket_root_cause_result,
            "diagnostics": q15_bucket_root_cause_summary,
            "artifact_path": Path(PROJECT_ROOT) / "data" / "q15_bucket_root_cause.json",
        },
        "hb_q15_boundary_replay": {
            "result": q15_boundary_replay_result,
            "diagnostics": q15_boundary_replay_summary,
            "artifact_path": Path(PROJECT_ROOT) / "data" / "q15_boundary_replay.json",
        },
        "auto_propose_fixes": {
            "result": auto_propose_result,
            "artifact_path": Path(PROJECT_ROOT) / "issues.json",
        },
    }
    fast_timeout_issue_sync = sync_fast_heartbeat_timeout_issue(
        run_label,
        fast_mode=args.fast,
        elapsed_seconds=run_elapsed_seconds,
        collect_result=collect_result,
        parallel_results=results,
        serial_results=serial_result_payload,
    )
    if args.fast:
        if fast_timeout_issue_sync.get("status") == "resolved":
            print(
                "✅ Fast heartbeat cron budget："
                f"completed in {fast_timeout_issue_sync.get('elapsed_seconds')}s within "
                f"{FAST_HEARTBEAT_CRON_BUDGET_SECONDS}s budget; cleared stale timeout regression issue."
            )
        elif fast_timeout_issue_sync.get("status") == "open":
            print(
                "⚠️  Fast heartbeat cron budget："
                f"elapsed={fast_timeout_issue_sync.get('elapsed_seconds')}s "
                f"timed_out_lanes={fast_timeout_issue_sync.get('timed_out_lanes') or []}"
            )

    docs_sync_write = overwrite_current_state_docs(
        run_label,
        counts,
        source_blockers,
        drift_diagnostics,
        live_predictor_diagnostics,
        live_drilldown_summary,
        q15_support_summary,
        circuit_breaker_audit_summary,
        leaderboard_candidate_diagnostics,
        run_mode="fast" if args.fast else "full",
        collect_attempted=bool(collect_result.get("attempted", False)),
        serial_results=serial_result_payload,
    )
    docs_sync = collect_current_state_docs_sync_status()
    docs_sync["auto_synced"] = docs_sync_write.get("success", False)
    docs_sync["written_docs"] = docs_sync_write.get("written_docs") or []
    if docs_sync_write.get("errors"):
        docs_sync["errors"] = docs_sync_write.get("errors")
    if docs_sync_write.get("success"):
        written_docs_text = ", ".join(docs_sync_write.get("written_docs") or []) or "none"
        print(f"📝 current-state docs：已 overwrite sync {written_docs_text}")
    if not docs_sync.get("ok", True):
        stale_docs_text = ", ".join(docs_sync.get("stale_docs") or []) or "unknown"
        reference_text = ", ".join(docs_sync.get("reference_artifacts") or []) or "none"
        print(
            "⚠️  current-state docs stale："
            f"{stale_docs_text} older than latest artifacts ({reference_text})；"
            "請先 overwrite sync docs 再 commit。"
        )

    summary, summary_path = save_summary(
        run_label,
        counts,
        source_blockers,
        collect_result,
        results,
        elapsed=run_elapsed_seconds,
        fast_mode=args.fast,
        ic_diagnostics=ic_diagnostics,
        drift_diagnostics=drift_diagnostics,
        live_predictor_diagnostics=live_predictor_diagnostics,
        live_decision_drilldown=live_drilldown_summary,
        q35_scaling_audit=q35_scaling_summary,
        q15_support_audit=q15_support_summary,
        q15_bucket_root_cause=q15_bucket_root_cause_summary,
        q15_boundary_replay=q15_boundary_replay_summary,
        circuit_breaker_audit=circuit_breaker_audit_summary,
        feature_ablation=feature_ablation_summary,
        bull_4h_pocket_ablation=bull_pocket_summary,
        leaderboard_candidate_diagnostics=leaderboard_candidate_diagnostics,
        q15_runtime_resync=q15_runtime_resync,
        auto_propose_result=auto_propose_result,
        docs_sync=docs_sync,
        progress_path=progress_path,
        serial_results=serial_result_payload,
    )
    final_status = "success"
    serial_results = [
        drift_report_result,
        q35_scaling_result,
        predict_probe_result,
        live_drilldown_result,
        circuit_breaker_audit_result,
        leaderboard_probe_result,
        q15_support_result,
        q15_bucket_root_cause_result,
        q15_boundary_replay_result,
        auto_propose_result,
    ]
    if not collect_result.get("success", True):
        final_status = "failed"
    elif any(not result.get("success") for result in results.values()):
        final_status = "completed_with_failures"
    elif any(not result.get("success", True) for result in serial_results if result is not None):
        final_status = "completed_with_failures"
    write_progress(
        run_label,
        "finished",
        status=final_status,
        details={
            "summary_path": str(summary_path),
            "mode": summary.get("mode"),
            "stats": summary.get("stats") or {},
            "collect_success": collect_result.get("success", False),
        },
    )
    _CURRENT_HEARTBEAT_RUN_LABEL = None
    print(f"\n📄 摘要已儲存：{os.path.relpath(summary_path, PROJECT_ROOT)}")


if __name__ == '__main__':
    main()
