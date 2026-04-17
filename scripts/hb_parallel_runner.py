#!/usr/bin/env python3
"""Heartbeat Parallel Runner v8 — runs diagnostics concurrently and saves summary.

Usage:
  python scripts/hb_parallel_runner.py --hb N [--no-train] [--no-dw]
  python scripts/hb_parallel_runner.py --fast [--hb LABEL]
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
    "feature_group_ablation": 20,
    "bull_4h_pocket_ablation": 20,
    "hb_leaderboard_candidate_probe": 20,
    "hb_q15_support_audit": 20,
    "hb_q15_bucket_root_cause": 20,
    "hb_q15_boundary_replay": 20,
}

TASKS = [
    {"name": "full_ic", "label": "🔍 Full IC", "cmd": [PYTHON, "scripts/full_ic.py"]},
    {"name": "regime_ic", "label": "🏛️ Regime IC", "cmd": [PYTHON, "scripts/regime_aware_ic.py"]},
    {"name": "dynamic_window", "label": "📏 Dynamic Window", "cmd": [PYTHON, "scripts/dynamic_window_train.py"]},
    {"name": "train", "label": "🔨 Model Train", "cmd": [PYTHON, "model/train.py"]},
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
FEATURE_ABLATION_CMD = [PYTHON, "scripts/feature_group_ablation.py"]
BULL_4H_POCKET_ABLATION_CMD = [PYTHON, "scripts/bull_4h_pocket_ablation.py"]
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


def _artifact_timestamp_from_payload(payload: Dict[str, Any] | None, artifact_path: str | Path | None) -> datetime | None:
    payload = payload or {}
    for key in ("generated_at", "alignment_evaluated_at"):
        parsed = _safe_parse_datetime(payload.get(key))
        if parsed is not None:
            return parsed
    return _file_mtime(artifact_path)


def _artifact_is_newer_than_dependencies(
    artifact_time: datetime | None,
    dependency_paths: list[str | Path] | None,
) -> bool:
    if artifact_time is None:
        return False
    for dep in dependency_paths or []:
        dep_mtime = _file_mtime(dep)
        if dep_mtime is not None and dep_mtime > artifact_time:
            return False
    return True


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


def _latest_feature_timestamp() -> str | None:
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute("SELECT MAX(timestamp) FROM features_normalized").fetchone()
    finally:
        conn.close()
    return row[0] if row else None


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
    try:
        payload = json.loads(artifact_path.read_text())
    except Exception:
        return None
    artifact_time = _artifact_timestamp_from_payload(payload, artifact_path)
    dependency_paths = [
        Path(PROJECT_ROOT) / "scripts" / "hb_leaderboard_candidate_probe.py",
        Path(PROJECT_ROOT) / "model" / "last_metrics.json",
        Path(PROJECT_ROOT) / "data" / "feature_group_ablation.json",
        Path(PROJECT_ROOT) / "data" / "bull_4h_pocket_ablation.json",
        Path(PROJECT_ROOT) / "data" / "q15_support_audit.json",
        Path(PROJECT_ROOT) / "data" / "live_predict_probe.json",
    ]
    if not _artifact_is_newer_than_dependencies(artifact_time, dependency_paths):
        return None
    return {
        "artifact_path": str(artifact_path),
        "reason": "fresh_leaderboard_candidate_artifact_reused",
        "details": {
            "generated_at": payload.get("generated_at"),
            "selected_feature_profile": ((payload.get("top_model") or {}).get("selected_feature_profile")),
        },
    }


def _get_fast_serial_cache_hit(command_name: str) -> Dict[str, Any] | None:
    if not _CURRENT_HEARTBEAT_FAST_MODE:
        return None
    if command_name == "recent_drift_report":
        return _recent_drift_cache_hit()
    if command_name == "hb_q35_scaling_audit":
        return _q35_scaling_cache_hit()
    if command_name == "hb_leaderboard_candidate_probe":
        return _leaderboard_candidate_cache_hit()
    return None


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


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--hb", type=str, required=False, help="Heartbeat label. Required for full runs; optional in --fast mode.")
    parser.add_argument("--fast", action="store_true", help="Quick diagnostic mode for cron. If --hb is omitted, uses the label 'fast'.")
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


def run_task(task):
    try:
        result = _run_command_with_watchdog(task["cmd"], timeout=600)
        return (
            task["name"],
            result["success"],
            (result.get("stdout") or "").strip(),
            (result.get("stderr") or "").strip(),
        )
    except Exception as e:
        return (task["name"], False, "", str(e))


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
            timeout=600,
            progress={
                "run_label": effective_run_label,
                "stage": "collect",
                "label": "hb_collect",
                "details": {"command_kind": "collect"},
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
    return 600


def _run_serial_command(
    cmd: list[str],
    timeout: int | None = None,
    extra_env: Dict[str, str] | None = None,
    *,
    progress: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    command_name = Path(cmd[1]).stem if len(cmd) > 1 else Path(cmd[0]).stem
    cache_hit = _get_fast_serial_cache_hit(command_name) if timeout is None else None
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
    return _run_serial_command(BULL_4H_POCKET_ABLATION_CMD)


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
        "cached": bool(result.get("cached")),
        "cache_reason": result.get("cache_reason"),
        "cache_details": result.get("cache_details") or {},
        "stdout_preview": (result.get("stdout") or "")[:1200],
        "stderr_preview": (result.get("stderr") or "")[:800],
        "diagnostics_available": bool(diagnostics),
        "fallback_artifact_used": bool(result and not result.get("success", False) and bool(diagnostics) and artifact_exists),
        **artifact_snapshot,
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
    auto_propose_result=None,
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
        "auto_propose": {
            "attempted": (auto_propose_result or {}).get("attempted", False),
            "success": (auto_propose_result or {}).get("success", False),
            "returncode": (auto_propose_result or {}).get("returncode", 0),
            "stdout_preview": (auto_propose_result or {}).get("stdout", "")[:2000],
            "stderr_preview": (auto_propose_result or {}).get("stderr", "")[:1000],
        },
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
    target_path = summary.get("target_path_diagnostics") or {}
    tail_streak = target_path.get("tail_target_streak") or {}
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
        "deployment_blocker_details": payload.get("deployment_blocker_details") or {},
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

    live_context = payload.get("live_context") or {}
    support_summary = payload.get("support_pathology_summary") or {}
    return {
        "generated_at": payload.get("generated_at"),
        "target_col": payload.get("target_col"),
        "collapse_features": payload.get("collapse_features") or [],
        "collapse_thresholds": payload.get("collapse_thresholds") or {},
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
        "support_pathology_summary": {
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
        },
        "production_profile_role": {
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
        },
        "bull_all": _cohort_summary("bull_all"),
        "bull_collapse_q35": _cohort_summary("bull_collapse_q35"),
        "bull_exact_live_lane_proxy": _cohort_summary("bull_exact_live_lane_proxy"),
        "bull_live_exact_lane_bucket_proxy": _cohort_summary("bull_live_exact_lane_bucket_proxy"),
        "bull_supported_neighbor_buckets_proxy": _cohort_summary("bull_supported_neighbor_buckets_proxy"),
    }


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
    return {
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
    progress_path = write_progress(
        run_label,
        "collect",
        details={
            "mode": "fast" if args.fast else "full",
            "tasks_requested": [task["name"] for task in TASKS],
            "fast": bool(args.fast),
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

    needs_train = any(t["name"] == "train" for t in tasks)
    write_progress(
        run_label,
        "preflight",
        details={
            "task_names": [task["name"] for task in tasks],
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
    start = datetime.now()
    start_monotonic = time.monotonic()
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
        last_completion_at = start_monotonic
        watchdog_heartbeats = 0
        while pending_futures:
            done, pending_futures = concurrent.futures.wait(
                pending_futures,
                timeout=15,
                return_when=concurrent.futures.FIRST_COMPLETED,
            )
            if not done:
                watchdog_heartbeats += 1
                elapsed_seconds = round(time.monotonic() - start_monotonic, 1)
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
                _, ok, out, err = future.result()
                results[name] = {"success": ok, "stdout": out, "stderr": err}
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
                        "elapsed_seconds": round(time.monotonic() - start_monotonic, 1),
                        "watchdog": {
                            "heartbeat_count": watchdog_heartbeats,
                            "seconds_since_last_completion": 0.0,
                        },
                    },
                )
                print(f"  [{'✅' if ok else '❌'}] {name}")

    elapsed = (datetime.now() - start).total_seconds()
    passed = sum(1 for r in results.values() if r["success"])
    print(f"\n  {passed}/{len(results)} 通過（{elapsed:.1f}s）")

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
        try:
            drill_payload = json.loads(live_drilldown_result["stdout"])
            live_drilldown_summary = {
                "json": drill_payload.get("json"),
                "markdown": drill_payload.get("markdown"),
                "chosen_scope": drill_payload.get("chosen_scope"),
                "worst_pathology_scope": drill_payload.get("worst_pathology_scope"),
                "runtime_blocker": drill_payload.get("runtime_blocker"),
                "runtime_blocker_reason": drill_payload.get("runtime_blocker_reason"),
                "deployment_blocker": drill_payload.get("deployment_blocker"),
                "deployment_blocker_reason": drill_payload.get("deployment_blocker_reason"),
                "q15_exact_supported_component_patch_applied": drill_payload.get("q15_exact_supported_component_patch_applied"),
                "signal": drill_payload.get("signal"),
                "allowed_layers": drill_payload.get("allowed_layers"),
                "allowed_layers_reason": drill_payload.get("allowed_layers_reason"),
                "support_route_verdict": drill_payload.get("support_route_verdict"),
                "remaining_gap_to_floor": drill_payload.get("remaining_gap_to_floor"),
                "best_single_component": drill_payload.get("best_single_component"),
                "best_single_component_required_score_delta": drill_payload.get("best_single_component_required_score_delta"),
            }
        except Exception:
            live_drilldown_summary = {}
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

    if feature_ablation_result is None:
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
    if feature_ablation_summary:
        recommended = feature_ablation_summary.get("recommended_metrics") or {}
        current_full = feature_ablation_summary.get("current_full_metrics") or {}
        print(
            "📚 Feature shrinkage："
            f"recommended={feature_ablation_summary.get('recommended_profile')} "
            f"cv={recommended.get('cv_mean_accuracy')} "
            f"worst={recommended.get('cv_worst_accuracy')} "
            f"vs current_full={current_full.get('cv_mean_accuracy')}"
        )

    if bull_pocket_result is None:
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
    if bull_pocket_summary:
        collapse = bull_pocket_summary.get("bull_collapse_q35") or {}
        live_bucket = bull_pocket_summary.get("bull_live_exact_lane_bucket_proxy") or {}
        neighbors = bull_pocket_summary.get("bull_supported_neighbor_buckets_proxy") or {}
        live_context = bull_pocket_summary.get("live_context") or {}
        print(
            "🐂 Bull pocket："
            f"collapse_best={collapse.get('recommended_profile')} "
            f"live_bucket_rows={live_bucket.get('rows')} best={live_bucket.get('recommended_profile')} "
            f"neighbor_rows={neighbors.get('rows')} best={neighbors.get('recommended_profile')} "
            f"current_bucket_rows={live_context.get('current_live_structure_bucket_rows')}"
        )

    write_progress(run_label, "leaderboard_candidate_probe")
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

    summary, summary_path = save_summary(
        run_label,
        counts,
        source_blockers,
        collect_result,
        results,
        elapsed,
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
        auto_propose_result=auto_propose_result,
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
