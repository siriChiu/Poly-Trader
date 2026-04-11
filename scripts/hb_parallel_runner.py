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


def run_task(task):
    try:
        env = {**os.environ, "PYTHONPATH": PROJECT_ROOT}
        result = subprocess.run(
            task["cmd"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=600,
            env=env,
        )
        return (task["name"], result.returncode == 0, result.stdout.strip(), result.stderr.strip())
    except subprocess.TimeoutExpired:
        return (task["name"], False, "", "TIMEOUT after 600s")
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


def run_collect_step(skip: bool = False) -> Dict[str, Any]:
    if skip:
        return {
            "attempted": False,
            "success": True,
            "stdout": "",
            "stderr": "",
            "returncode": 0,
            "command": COLLECT_CMD,
        }

    env = {**os.environ, "PYTHONPATH": PROJECT_ROOT}
    try:
        result = subprocess.run(
            COLLECT_CMD,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=600,
            env=env,
        )
        return {
            "attempted": True,
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
            "command": COLLECT_CMD,
        }
    except subprocess.TimeoutExpired:
        return {
            "attempted": True,
            "success": False,
            "stdout": "",
            "stderr": "TIMEOUT after 600s",
            "returncode": -1,
            "command": COLLECT_CMD,
        }
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


def _run_serial_command(cmd: list[str], timeout: int = 600, extra_env: Dict[str, str] | None = None) -> Dict[str, Any]:
    env = {**os.environ, "PYTHONPATH": PROJECT_ROOT}
    if extra_env:
        env.update(extra_env)
    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return {
            "attempted": True,
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "command": cmd,
        }
    except subprocess.TimeoutExpired:
        return {
            "attempted": True,
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": f"TIMEOUT after {timeout}s",
            "command": cmd,
        }
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
    auto_propose_result=None,
):
    passed = sum(1 for r in results.values() if r["success"])
    total = len(results)
    continuity_repair = parse_collect_metadata(collect_result.get("stdout", ""))
    if continuity_repair:
        continuity_repair = {**continuity_repair, "heartbeat": run_label}
        continuity_repair["bridge_fallback_streak"] = compute_bridge_fallback_streak(continuity_repair)

    summary = {
        "heartbeat": run_label,
        "mode": "fast" if fast_mode else "full",
        "timestamp": datetime.now(timezone.utc).isoformat(),
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
        "auto_propose": {
            "attempted": (auto_propose_result or {}).get("attempted", False),
            "success": (auto_propose_result or {}).get("success", False),
            "returncode": (auto_propose_result or {}).get("returncode", 0),
            "stdout_preview": (auto_propose_result or {}).get("stdout", "")[:2000],
            "stderr_preview": (auto_propose_result or {}).get("stderr", "")[:1000],
        },
        "parallel_results": {},
        "stats": {"passed": passed, "total": total, "elapsed_seconds": round(elapsed, 1)},
    }

    for name, r in results.items():
        summary["parallel_results"][name] = {
            "success": r["success"],
            "stdout_preview": r["stdout"][:2000] if r.get("stdout") else "",
            "stderr_preview": r["stderr"][:1000] if r.get("stderr") else "",
        }

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
    return {
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
        },
    }


def print_source_blockers(source_blockers: Dict[str, Any]) -> None:
    blocked = source_blockers.get("blocked_features", [])
    print(
        "🚧 Source blockers: "
        f"{source_blockers.get('blocked_count', 0)} blocked features across "
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
    args = parse_args(argv)
    run_label = resolve_run_label(args)

    collect_result = run_collect_step(skip=args.no_collect)
    if collect_result.get("attempted"):
        print(
            f"🛰️ Pre-heartbeat collect: {'PASS' if collect_result['success'] else 'FAIL'} "
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
                "🩹 Continuity repair detail: "
                f"4h={continuity_repair.get('coarse_inserted', 0)}, "
                f"1h={continuity_repair.get('fine_inserted', 0)}, "
                f"bridge={continuity_repair.get('bridge_inserted', 0)}"
            )
            if continuity_repair.get("used_bridge"):
                print("⚠️  Interpolated bridge fallback triggered in this collect run")

    counts = quick_counts()
    source_blockers = collect_source_blockers()
    print(
        f"📊 DB Counts: Raw={counts['raw_market_data']}, Features={counts['features_normalized']}, "
        f"Labels={counts['labels']}, simulated_win={counts['simulated_pyramid_win_rate']}"
    )
    latest_raw_ts = counts.get('latest_raw_timestamp')
    for row in counts.get('label_horizons', []):
        print(
            f"   • labels[{row['horizon_minutes']}m]: rows={row['rows']} target_rows={row['target_rows']} "
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

    print(f"心跳 #{run_label} 平行执行 — {len(tasks)} tasks ({'fast' if args.fast else 'full'} mode)")
    start = datetime.now()
    results = {}
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(len(tasks), 5)) as ex:
        future_to_name = {ex.submit(run_task, t): t["name"] for t in tasks}
        for future in concurrent.futures.as_completed(future_to_name):
            name = future_to_name[future]
            _, ok, out, err = future.result()
            results[name] = {"success": ok, "stdout": out, "stderr": err}
            print(f"  [{'✅' if ok else '❌'}] {name}")

    elapsed = (datetime.now() - start).total_seconds()
    passed = sum(1 for r in results.values() if r["success"])
    print(f"\n  {passed}/{len(results)} PASS ({elapsed:.1f}s)")

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
            "\n📉 IC diagnostics: "
            f"Global={ic_diagnostics.get('global_pass')}/{ic_diagnostics.get('total_features')} | "
            f"TW-IC={ic_diagnostics.get('tw_pass')}/{ic_diagnostics.get('total_features')}"
        )

    drift_report_result = run_recent_drift_report()
    drift_diagnostics = collect_recent_drift_diagnostics()
    print(
        f"🧭 Recent drift report: {'PASS' if drift_report_result['success'] else 'FAIL'} "
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
        print(
            "🧭 Drift diagnostics: "
            f"window={drift_diagnostics.get('primary_window')} "
            f"alerts={drift_diagnostics.get('primary_alerts')} "
            f"win_rate={primary.get('win_rate')} "
            f"dominant_regime={primary.get('dominant_regime')}"
        )

    auto_propose_result = run_auto_propose(run_label)
    print(
        f"🛠️  Auto-propose: {'PASS' if auto_propose_result['success'] else 'FAIL'} "
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

    _, summary_path = save_summary(
        run_label,
        counts,
        source_blockers,
        collect_result,
        results,
        elapsed,
        args.fast,
        ic_diagnostics=ic_diagnostics,
        drift_diagnostics=drift_diagnostics,
        auto_propose_result=auto_propose_result,
    )
    print(f"\n📄 Summary saved: {os.path.relpath(summary_path, PROJECT_ROOT)}")


if __name__ == '__main__':
    main()
