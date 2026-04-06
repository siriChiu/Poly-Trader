#!/usr/bin/env python3
"""hb_parallel_runner.py — Multi-process parallel heartbeat runner for Poly-Trader.

Runs full IC, regime-aware IC, dynamic window, model training, and tests in parallel.
"""
import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "poly_trader.db")
PYTHON = os.path.join(PROJECT_ROOT, "venv", "bin", "python")


def get_db_counts():
    """Quick DB counts using sqlite3 (no CLI dependency)."""
    counts = {}
    try:
        conn = sqlite3.connect(DB_PATH)
        for table in ["raw_market_data", "features_normalized", "labels"]:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            counts[table] = count
        # sell_win rate
        sw = conn.execute(
            "SELECT COUNT(*) FROM labels WHERE label_sell_win IS NOT NULL"
        ).fetchone()[0]
        total = sw
        wins = conn.execute(
            "SELECT COUNT(*) FROM labels WHERE label_sell_win = 1"
        ).fetchone()[0]
        counts["sell_win_rate"] = wins / total if total > 0 else None
        conn.close()
    except Exception as e:
        counts["error"] = str(e)
    return counts


def run_single_script(script_rel, timeout=180):
    """Run one script and capture output. Safe for ProcessPoolExecutor."""
    os.environ["PYTHONPATH"] = PROJECT_ROOT
    os.chdir(PROJECT_ROOT)
    script_path = os.path.join(PROJECT_ROOT, script_rel)
    if not os.path.exists(script_path):
        return {
            "script": script_rel,
            "status": "MISSING",
            "stdout": "",
            "stderr": f"File not found: {script_path}",
            "runtime_s": 0,
        }
    t0 = time.time()
    try:
        result = subprocess.run(
            [PYTHON, script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=PROJECT_ROOT,
            env={**os.environ, "PYTHONPATH": PROJECT_ROOT},
        )
        rt = round(time.time() - t0, 1)
        return {
            "script": script_rel,
            "status": "PASS" if result.returncode == 0 else "FAIL",
            "stdout": result.stdout[-4000:],
            "stderr": result.stderr[-2000:],
            "returncode": result.returncode,
            "runtime_s": rt,
        }
    except FileNotFoundError:
        return {
            "script": script_rel,
            "status": "ERROR",
            "stdout": "",
            "stderr": f"Python not found at {PYTHON}",
            "runtime_s": round(time.time() - t0, 1),
        }
    except subprocess.TimeoutExpired:
        return {
            "script": script_rel,
            "status": "TIMEOUT",
            "stdout": "",
            "stderr": f"Timed out after {timeout}s",
            "runtime_s": timeout,
        }
    except Exception as e:
        return {
            "script": script_rel,
            "status": "ERROR",
            "stdout": "",
            "stderr": str(e),
            "runtime_s": round(time.time() - t0, 1),
        }


def parse_ic_results(script_result, label="IC"):
    """Parse a script's stdout for key IC/metrics lines."""
    lines = script_result.get("stdout", "").split("\n")
    key_lines = []
    for line in lines:
        stripped = line.strip()
        if any(k in stripped.upper() for k in ["IC:", "PASSED", "PASSED", "GLOBAL", "REGIME", "ACCURACY", "TRAIN", "CV", "PASS", "FAIL", "SUMMARY"]):
            key_lines.append(stripped[:200])
    return key_lines[:30]


def main():
    parser = argparse.ArgumentParser(description="Parallel Heartbeat Runner")
    parser.add_argument(
        "--hb", type=int, default=0, help="Heartbeat number (ignored, used for reporting)"
    )
    parser.add_argument(
        "--no-train", action="store_true", help="Skip model training"
    )
    parser.add_argument(
        "--no-dw", action="store_true", help="Skip dynamic window"
    )
    parser.add_argument(
        "--no-tests", action="store_true", help="Skip tests"
    )
    parser.add_argument(
        "--quick", action="store_true", help="Only run IC scripts, skip training and tests"
    )
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  Poly-Trader 心跳 #{args.hb or 'N'}: Parallel Runner")
    print(f"  Started: {datetime.now().isoformat()}")
    print(f"{'='*60}\n")

    # Step 0: Quick DB counts
    print("[0/5] Quick DB counts...")
    counts = get_db_counts()
    for k, v in counts.items():
        print(f"  {k}: {v}")

    # Step 1: Build task list
    tasks = [
        ("scripts/full_ic.py", "Full IC Analysis"),
        ("scripts/regime_aware_ic.py", "Regime-Aware IC"),
        ("model/train.py", "Model Training"),
        ("tests/comprehensive_test.py", "Comprehensive Tests"),
        ("scripts/dynamic_window_train.py", "Dynamic Window Scan"),
    ]

    # Filter by flags
    if args.no_train:
        tasks = [t for t in tasks if "model/train" not in t[0]]
    if args.no_dw:
        tasks = [t for t in tasks if "dynamic_window" not in t[0]]
    if args.no_tests:
        tasks = [t for t in tasks if "comprehensive_test" not in t[0]]
    if args.quick:
        tasks = [t for t in tasks if "full_ic" in t[0] or "regime_aware" in t[0]]

    total_start = time.time()

    # Step 2: Run in parallel
    print(f"\n[1/5] Launching {len(tasks)} tasks in parallel...")
    print("-" * 50)

    results = {}
    with ProcessPoolExecutor(max_workers=min(5, len(tasks))) as executor:
        future_to_task = {
            executor.submit(
                run_single_script, task[0], timeout=180
            ): (task[0], task[1])
            for task in tasks
        }
        for future in as_completed(future_to_task):
            script_rel, desc = future_to_task[future]
            try:
                r = future.result(timeout=200)
                results[script_rel] = r
                icon = "✅" if r["status"] == "PASS" else "❌" if r["status"] not in ["MISSING", "SKIP"] else "⏭️"
                print(f"  {icon} {desc} ({script_rel}): {r['status']} ({r.get('runtime_s', 0)}s)")
                # Print key insights
                key_lines = parse_ic_results(r, desc)
                for line in key_lines[:5]:
                    print(f"      {line}")
            except Exception as e:
                results[script_rel] = {
                    "script": script_rel,
                    "status": "ERROR",
                    "stderr": str(e),
                    "runtime_s": 0,
                }
                print(f"  ❌ {desc} ({script_rel}): ERROR — {e}")

    total_elapsed = round(time.time() - total_start, 1)

    # Step 3: Summary
    print(f"\n{'='*60}")
    print(f"  心跳 #{args.hb or 'N'}: 平行心跳完成")
    print(f"  总耗时: {total_elapsed}s")
    print(f"{'='*60}")

    pass_count = sum(1 for r in results.values() if r.get("status") == "PASS")
    total_count = len(results)
    print(f"\n结果: {pass_count}/{total_count} 通过")
    for r in results.values():
        status = r.get("status", "UNKNOWN")
        script = r.get("script", "?")
        rt = r.get("runtime_s", 0)
        print(f"  {status}: {script} ({rt}s)")

    # Save summary JSON
    summary = {
        "heartbeat": args.hb,
        "timestamp": datetime.now().isoformat(),
        "total_elapsed_s": total_elapsed,
        "db_counts": counts,
        "scripts": {
            r.get("script", "?"): {
                "status": r.get("status"),
                "runtime_s": r.get("runtime_s"),
            }
            for r in results.values()
        },
    }
    data_dir = os.path.join(PROJECT_ROOT, "data")
    os.makedirs(data_dir, exist_ok=True)
    summary_path = os.path.join(data_dir, f"heartbeat_{args.hb}_summary.json")
    try:
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2, default=str)
        print(f"\nSummary saved to {summary_path}")
    except Exception as e:
        print(f"\nFailed to save summary: {e}")

    return 0 if pass_count == total_count else 1


if __name__ == "__main__":
    exit(main())
