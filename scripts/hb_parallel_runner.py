#!/usr/bin/env python3
"""Parallel heartbeat runner for Poly-Trader.
Uses ProcessPoolExecutor to run 5 tasks concurrently:
1. full_ic.py — full IC analysis
2. regime_aware_ic.py — regime-aware IC
3. dynamic_window_train.py — dynamic window scanning
4. model/train.py — model training
5. tests/comprehensive_test.py — test suite

Usage:
    python scripts/hb_parallel_runner.py --hb N
    python scripts/hb_parallel_runner.py --fast  # quick mode
"""
import os
import sys
import json
import time
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.environ.setdefault("PYTHONPATH", str(PROJECT_ROOT))

SCRIPTS = {
    "full_ic": "scripts/full_ic.py",
    "regime_ic": "scripts/regime_aware_ic.py",
    "dynamic_window": "scripts/dynamic_window_train.py",
    "train": "model/train.py",
    "tests": "tests/comprehensive_test.py",
}

QUICK_SCRIPTS = {
    "full_ic": "scripts/full_ic.py",
    "regime_ic": "scripts/regime_aware_ic.py",
    "dynamic_window": "scripts/dynamic_window_train.py",
}


def run_script(name: str, rel_path: str) -> dict:
    """Run a single script and capture its output."""
    import subprocess
    full_path = PROJECT_ROOT / rel_path
    if not full_path.exists():
        return {"name": name, "status": "SKIP", "output": f"Not found: {rel_path}", "exit_code": -1}

    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, str(full_path)],
            capture_output=True, text=True, timeout=600,
            cwd=str(PROJECT_ROOT),
            env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
        )
        elapsed = time.time() - start
        stdout_lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
        # Find key metrics in output
        summary_lines = []
        for line in stdout_lines:
            if any(kw in line.lower() for kw in ["ic", "pass", "fail", "train", "cv", "accuracy", "test", "pass", "window", "regime"]):
                summary_lines.append(line.strip())

        status = "PASS" if result.returncode == 0 else "FAIL"
        return {
            "name": name,
            "status": status,
            "exit_code": result.returncode,
            "elapsed": round(elapsed, 1),
            "summary": summary_lines[:15],  # key lines only
            "error": result.stderr[-2000:] if result.stderr else None,
        }
    except subprocess.TimeoutExpired:
        return {"name": name, "status": "TIMEOUT", "elapsed": 600, "summary": ["Timed out after 600s"]}
    except Exception as e:
        return {"name": name, "status": "ERROR", "output": str(e), "exit_code": -1}


def quick_db_counts() -> dict:
    """Quick serial DB counts."""
    import sqlite3
    db_path = PROJECT_ROOT / "poly_trader.db"
    counts = {}
    try:
        db = sqlite3.connect(str(db_path))
        for t in ["raw_market_data", "features_normalized", "labels"]:
            counts[t] = db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        try:
            counts["sell_win_rate"] = round(
                db.execute("SELECT AVG(CAST(label_sell_win AS FLOAT)) FROM labels WHERE label_sell_win IS NOT NULL").fetchone()[0], 4
            )
        except:
            counts["sell_win_rate"] = None
        try:
            counts["latest_timestamp"] = db.execute("SELECT MAX(timestamp) FROM raw_market_data").fetchone()[0]
        except:
            counts["latest_timestamp"] = None
        db.close()
    except Exception as e:
        counts["error"] = str(e)
    return counts


def main():
    parser = argparse.ArgumentParser(description="Parallel heartbeat runner")
    parser.add_argument("--hb", type=int, required=False, help="Heartbeat number")
    parser.add_argument("--fast", action="store_true", help="Quick mode: only IC scripts")
    parser.add_argument("--no-train", action="store_true", help="Skip model training")
    parser.add_argument("--no-dw", action="store_true", help="Skip dynamic window")
    args = parser.parse_args()

    hb_num = args.hb or 0
    print(f"\n{'='*60}")
    print(f"  Poly-Trader 平行心跳 #{hb_num}")
    print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  Project: {PROJECT_ROOT}")
    print(f"{'='*60}\n")

    # Step 0: Quick DB counts (serial)
    print("[Step 0] Quick DB counts...")
    counts = quick_db_counts()
    for k, v in counts.items():
        print(f"  {k}: {v}")
    print(f"  Elapsed: <5s (serial)\n")

    # Select scripts to run
    scripts_to_run = dict(SCRIPTS)
    if args.fast:
        scripts_to_run = dict(QUICK_SCRIPTS)
    if args.no_train:
        scripts_to_run.pop("train", None)
    if args.no_dw:
        scripts_to_run.pop("dynamic_window", None)

    # Step 1: Run all scripts in parallel
    print(f"[Step 1] Running {len(scripts_to_run)} tasks in parallel...\n")
    n_workers = min(len(scripts_to_run), 5)
    results = {}
    overall_start = time.time()

    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        futures = {}
        for name, rel_path in scripts_to_run.items():
            f = executor.submit(run_script, name, rel_path)
            futures[f] = name
            print(f"  🚀 Started: {name} ({rel_path})")

        print()
        for future in as_completed(futures):
            name = futures[future]
            try:
                r = future.result()
                results[name] = r
                icon = "✅" if r["status"] == "PASS" else "❌"
                print(f"  {icon} {name}: {r['status']} ({r.get('elapsed', '?')}s)")
            except Exception as e:
                results[name] = {"name": name, "status": "EXCEPTION", "error": str(e)}
                print(f"  ❌ {name}: EXCEPTION - {e}")

    elapsed = round(time.time() - overall_start, 1)

    # Summary
    print(f"\n{'='*60}")
    print(f"  PARALLEL HEARTBEAT #{hb_num} SUMMARY")
    print(f"{'='*60}")
    total = len(results)
    passed = sum(1 for r in results.values() if r["status"] == "PASS")
    print(f"  {passed}/{total} tasks passed")
    print(f"  Total parallel time: {elapsed}s")

    for name, r in results.items():
        print(f"\n  --- {name} ({r['status']}, {r.get('elapsed', '?')}s) ---")
        if r.get("summary"):
            for line in r["summary"]:
                print(f"    {line}")
        if r.get("error"):
            print(f"    STDERR (last 500): {r['error'][:500]}")

    # Save JSON summary
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    summary = {
        "heartbeat": hb_num,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "db_counts": {k: v for k, v in counts.items()},
        "parallel_time": elapsed,
        "tasks": results,
        "pass_count": passed,
        "total_count": total,
    }
    summary_path = data_dir / f"heartbeat_{hb_num}_summary.json"
    with open(str(summary_path), "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\n  📄 Summary saved: {summary_path}")

    return results


if __name__ == "__main__":
    main()
