#!/usr/bin/env python3
"""HB Parallel Runner v6 — ProcessPoolExecutor for all 5 heartbeat scripts.

Runs: full_ic.py, regime_aware_ic.py, dynamic_window_train.py, model/train.py, tests/comprehensive_test.py
Usage: python scripts/hb_parallel_runner.py --hb N [--fast] [--no-train] [--no-dw]
"""
import argparse
import concurrent.futures
import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime

PROJECT = "/home/kazuha/Poly-Trader"
DB = os.path.join(PROJECT, "poly_trader.db")
PYTHON = os.path.join(PROJECT, "venv", "bin", "python")
os.environ["PYTHONPATH"] = PROJECT


def quick_counts():
    """Serial DB counts (<10s)."""
    conn = sqlite3.connect(DB)
    counts = {}
    for t in ["raw_market_data", "features_normalized", "labels"]:
        counts[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    sell_win = conn.execute(
        "SELECT AVG(CAST(label_sell_win AS REAL)) FROM labels WHERE label_sell_win IS NOT NULL"
    ).fetchone()[0]
    max_ts = conn.execute(
        "SELECT MAX(timestamp) FROM raw_market_data"
    ).fetchone()[0]
    conn.close()
    return {**counts, "sell_win": round(sell_win, 4) if sell_win else None, "max_ts": max_ts}


def run_script(script_path, label):
    """Run one script and capture output."""
    start = time.time()
    try:
        result = subprocess.run(
            [PYTHON, script_path],
            capture_output=True, text=True, timeout=600,
            cwd=PROJECT,
            env={**os.environ, "PYTHONPATH": PROJECT},
        )
        elapsed = round(time.time() - start, 1)
        out = result.stdout.strip()
        # Extract last ~2000 chars if output is huge
        if len(out) > 2000:
            out = "..." + out[-2000:]
        return {
            "label": label,
            "script": script_path,
            "status": "PASS" if result.returncode == 0 else "FAIL",
            "returncode": result.returncode,
            "elapsed_s": elapsed,
            "stdout": out,
            "stderr": result.stderr.strip()[-1000:] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        elapsed = round(time.time() - start, 1)
        return {
            "label": label,
            "script": script_path,
            "status": "TIMEOUT",
            "elapsed_s": elapsed,
            "stdout": "",
            "stderr": f"Timeout after {elapsed}s",
        }
    except Exception as e:
        return {
            "label": label,
            "script": script_path,
            "status": "ERROR",
            "elapsed_s": round(time.time() - start, 1),
            "stdout": "",
            "stderr": str(e),
        }


def main():
    parser = argparse.ArgumentParser(description="Poly-Trader Parallel Heartbeat")
    parser.add_argument("--hb", type=int, required=True, help="Heartbeat number")
    parser.add_argument("--fast", action="store_true", help="Fast mode: counts + quick IC only")
    parser.add_argument("--no-train", action="store_true", help="Skip model training")
    parser.add_argument("--no-dw", action="store_true", help="Skip dynamic window scan")
    args = parser.parse_args()
    hb_num = args.hb

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"{'='*60}")
    print(f"  心跳 #{hb_num} — 平行心跳 started {ts}")
    print(f"{'='*60}")

    # --- Step 0: Quick DB counts serially ---
    t0 = time.time()
    print("\n📊 Step 0: DB counts...")
    counts = quick_counts()
    for k, v in counts.items():
        print(f"  {k}: {v}")
    print(f"  Step 0 done: {time.time()-t0:.1f}s")

    if args.fast:
        print("\n⚡ Fast mode — skipping heavy scripts")
        summary = {
            "hb": hb_num,
            "timestamp": ts,
            "counts": counts,
            "mode": "fast",
        }
        os.makedirs(os.path.join(PROJECT, "data"), exist_ok=True)
        with open(os.path.join(PROJECT, f"data/heartbeat_{hb_num}_summary.json"), "w") as f:
            json.dump(summary, f, indent=2, default=str)
        print(json.dumps(summary, indent=2, default=str))
        return

    # --- Step 1: Parallel 5 scripts ---
    scripts = [
        (os.path.join(PROJECT, "scripts", "full_ic.py"), "full_ic"),
        (os.path.join(PROJECT, "scripts", "regime_aware_ic.py"), "regime_aware_ic"),
        (os.path.join(PROJECT, "scripts", "dynamic_window_train.py"), "dynamic_window"),
        (os.path.join(PROJECT, "model", "train.py"), "train"),
        (os.path.join(PROJECT, "tests", "comprehensive_test.py"), "tests"),
    ]

    if args.no_train:
        scripts = [s for s in scripts if s[1] != "train"]
    if args.no_dw:
        scripts = [s for s in scripts if s[1] != "dynamic_window"]

    t1 = time.time()
    print(f"\n⚡ Step 1: Parallel execution ({len(scripts)} scripts)...")
    results = []

    with concurrent.futures.ProcessPoolExecutor(max_workers=min(5, len(scripts))) as executor:
        future_map = {
            executor.submit(run_script, sp, label): (sp, label)
            for sp, label in scripts
        }
        for future in concurrent.futures.as_completed(future_map):
            sp, label = future_map[future]
            try:
                r = future.result()
                results.append(r)
                status_icon = "✅" if r["status"] == "PASS" else "❌"
                print(f"  {status_icon} {label}: {r['status']} ({r['elapsed_s']}s)")
                if r["stderr"]:
                    print(f"     stderr: {r['stderr'][:200]}")
            except Exception as e:
                results.append({
                    "label": label,
                    "script": sp,
                    "status": "CRASH",
                    "error": str(e),
                })
                print(f"  💥 {label}: CRASH — {e}")

    elapsed_total = round(time.time() - t1, 1)
    pass_count = sum(1 for r in results if r.get("status") == "PASS")
    print(f"\n  {pass_count}/{len(results)} scripts passed, total: {elapsed_total}s")

    # --- Save summary JSON ---
    summary = {
        "hb": hb_num,
        "timestamp": ts,
        "counts": counts,
        "parallel_results": results,
        "parallel_elapsed_s": elapsed_total,
        "total_elapsed_s": round(time.time() - t0, 1),
    }
    os.makedirs(os.path.join(PROJECT, "data"), exist_ok=True)
    summary_path = os.path.join(PROJECT, f"data/heartbeat_{hb_num}_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\n  💾 Summary saved: {summary_path}")

    # --- Print stdout of key scripts for downstream processing ---
    for r in results:
        if r["status"] == "PASS" and r.get("stdout"):
            print(f"\n{'─'*40} {r['label']} output {'─'*40}")
            print(r["stdout"][:3000])

    print(f"\n{'='*60}")
    print(f"  心跳 #{hb_num} 完成 — {pass_count}/{len(results)} PASS, {elapsed_total}s")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
