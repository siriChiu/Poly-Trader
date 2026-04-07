#!/usr/bin/env python3
"""
hb_parallel_runner.py v7 — Parallel Heartbeat Runner for Poly-Trader
Uses ProcessPoolExecutor to run IC analysis, regime IC, dynamic window, training, and tests concurrently.
"""

import os
import sys
import json
import time
import sqlite3
import subprocess
import concurrent.futures
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).parent.parent
os.environ.setdefault("PYTHONPATH", str(PROJECT_ROOT))

DB_PATH = PROJECT_ROOT / "poly_trader.db"


def quick_db_counts():
    """Fast DB count check (<10s)."""
    counts = {}
    try:
        db = sqlite3.connect(str(DB_PATH))
        for t in ["raw_market_data", "features_normalized", "labels"]:
            count = db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            counts[t] = count
        # Also check sell_win
        sell_win = db.execute(
            "SELECT AVG(CAST(label_sell_win AS FLOAT)) FROM labels WHERE label_sell_win IS NOT NULL"
        ).fetchone()[0]
        counts["sell_win"] = round(sell_win, 4) if sell_win else None
        db.close()
    except Exception as e:
        counts["error"] = str(e)
    return counts


def run_task(name, cmd, **kwargs):
    """Run a single script and capture output."""
    start = time.time()
    env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(PROJECT_ROOT),
            env=env,
            **kwargs,
        )
        elapsed = round(time.time() - start, 1)
        stdout = result.stdout.strip() if result.stdout else ""
        stderr = result.stderr.strip() if result.stderr else ""
        # Truncate long outputs
        if len(stdout) > 2000:
            lines = stdout.split("\n")
            stdout = "\n".join(lines[:50] + ["..."] + lines[-30:])
        success = result.returncode == 0
        return {
            "name": name,
            "success": success,
            "returncode": result.returncode,
            "elapsed": elapsed,
            "stdout": stdout,
            "stderr": stderr,
        }
    except subprocess.TimeoutExpired:
        return {
            "name": name,
            "success": False,
            "returncode": -1,
            "elapsed": round(time.time() - start, 1),
            "stdout": "",
            "stderr": "TIMEOUT after 300s",
        }
    except Exception as e:
        return {
            "name": name,
            "success": False,
            "returncode": -2,
            "elapsed": round(time.time() - start, 1),
            "stdout": "",
            "stderr": str(e),
        }


def filter_stderr(stderr):
    """Remove DeprecationWarning/FutureWarning noise from stderr."""
    if not stderr:
        return ""
    lines = stderr.split("\n")
    filtered = [
        l
        for l in lines
        if "DeprecationWarning" not in l and "FutureWarning" not in l
    ]
    return "\n".join(filtered)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Parallel Heartbeat Runner")
    parser.add_argument("--hb", type=int, required=True, help="Heartbeat number")
    parser.add_argument(
        "--no-train", action="store_true", help="Skip model training"
    )
    parser.add_argument(
        "--no-dw", action="store_true", help="Skip dynamic window scan"
    )
    parser.add_argument(
        "--workers", type=int, default=5, help="Number of parallel workers"
    )
    args = parser.parse_args()

    hb_num = args.hb
    print(f"\n{'='*60}")
    print(f"  平行心跳 #{hb_num} — Parallel Heartbeat")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{'='*60}\n")

    # Step 0: Quick DB counts
    print("📊 Step 0: Quick DB counts...")
    counts = quick_db_counts()
    for key, val in counts.items():
        print(f"  {key}: {val}")
    print()

    build_tasks = True
    if build_tasks:
        tasks = []
        
        task_full_ic = [sys.executable, str(PROJECT_ROOT / "scripts" / "full_ic.py")]
        tasks.append(("full_ic", task_full_ic))
        
        task_regime_ic = [sys.executable, str(PROJECT_ROOT / "scripts" / "regime_aware_ic.py")]
        tasks.append(("regime_ic", task_regime_ic))
        
        task_dw = [sys.executable, str(PROJECT_ROOT / "scripts" / "dynamic_window_train.py")]
        tasks.append(("dynamic_window", task_dw))
        
        task_train = [sys.executable, str(PROJECT_ROOT / "model" / "train.py")]
        tasks.append(("train", task_train))
        
        task_tests = [sys.executable, str(PROJECT_ROOT / "tests" / "comprehensive_test.py")]
        tasks.append(("tests", task_tests))
        
        # Run all tasks in parallel
        print(f"🚀 Spawning {len(tasks)} tasks with {args.workers} workers...\n")
        overall_start = time.time()
        
        results = []
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
            future_to_task = {}
            for name, cmd in tasks:
                future = executor.submit(run_task, name, cmd)
                future_to_task[future] = name
            
            for future in concurrent.futures.as_completed(future_to_task):
                name = future_to_task[future]
                try:
                    result = future.result()
                    results.append(result)
                    status = "✅" if result["success"] else "❌"
                    print(f"  {status} {name}: {result['elapsed']}s (rc={result['returncode']})")
                    stderr_clean = filter_stderr(result.get("stderr", ""))
                    if stderr_clean:
                        print(f"     stderr: {stderr_clean[:200]}")
                except Exception as e:
                    results.append({
                        "name": name,
                        "success": False,
                        "returncode": -3,
                        "elapsed": 0,
                        "stdout": "",
                        "stderr": str(e),
                    })
                    print(f"  ❌ {name}: EXCEPTION — {e}")
        
        total_elapsed = round(time.time() - overall_start, 1)
        passed = sum(1 for r in results if r["success"])
        print(f"\n{'='*60}")
        print(
            f"  平行心跳 #{hb_num}: {passed}/{len(tasks)} PASS ({total_elapsed}s)"
        )
        print(f"{'='*60}\n")
        
        # Print detailed output for each task
        for r in results:
            status = "✅" if r["success"] else "❌"
            print(f"\n--- {status} {r['name']} ({r['elapsed']}s) ---")
            if r["stdout"]:
                # Print last 40 lines of stdout
                lines = r["stdout"].split("\n")
                for line in lines[-40:]:
                    print(f"  {line}")
        
        # Save JSON summary
        summary = {
            "heartbeat": hb_num,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "db_counts": counts,
            "tasks": results,
            "total_elapsed": total_elapsed,
            "passed": passed,
            "total_tasks": len(tasks),
        }
        
        data_dir = PROJECT_ROOT / "data"
        data_dir.mkdir(exist_ok=True)
        summary_path = data_dir / f"heartbeat_{hb_num}_summary.json"
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2, default=str)
        print(f"\n💾 Summary saved to {summary_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
