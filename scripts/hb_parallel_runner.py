#!/usr/bin/env python3
"""hb_parallel_runner.py — Parallel heartbeat runner.
Runs full_ic.py, regime_aware_ic.py, dynamic_window_train.py,
model/train.py, and tests/comprehensive_test.py in parallel via
ProcessPoolExecutor. Saves results to data/heartbeat_<N>_summary.json.
"""
import json
import os
import time
import sqlite3
import subprocess
import concurrent.futures
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path("/home/kazuha/Poly-Trader")
DB_PATH = PROJECT_ROOT / "poly_trader.db"
PYTHON = str(PROJECT_ROOT / "venv" / "bin" / "python")
ENV = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}


def quick_db_counts():
    """Fast DB counts (<10s)."""
    counts = {}
    try:
        conn = sqlite3.connect(str(DB_PATH))
        for table in ["raw_market_data", "features_normalized", "labels"]:
            cnt = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            latest = conn.execute(f"SELECT MAX(timestamp) FROM {table}").fetchone()[0]
            counts[table] = {"count": cnt, "latest": latest}
        # sell_win stats
        sell_win = conn.execute(
            "SELECT AVG(CAST(label_sell_win AS FLOAT)), COUNT(*) FROM labels WHERE label_sell_win IS NOT NULL"
        ).fetchone()
        counts["sell_win"] = {
            "avg": round(sell_win[0], 4) if sell_win[0] else None,
            "total": sell_win[1],
        }
        conn.close()
    except Exception as e:
        counts["error"] = str(e)
    return counts


def run_script(script_path, label, timeout=300):
    """Run a single script and capture output."""
    abs_path = str(PROJECT_ROOT / script_path)
    start = time.time()
    try:
        result = subprocess.run(
            [PYTHON, abs_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=ENV,
            cwd=str(PROJECT_ROOT),
        )
        elapsed = round(time.time() - start, 1)
        # Extract last 50 lines of stdout for summary
        stdout_lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
        summary_lines = stdout_lines[-50:] if len(stdout_lines) > 50 else stdout_lines
        rc = getattr(result, "returncode", getattr(result, "exit_code", -1))
        return {
            "script": script_path,
            "label": label,
            "exit_code": rc,
            "status": "PASS" if rc == 0 else "FAIL",
            "elapsed_s": elapsed,
            "stdout_summary": "\n".join(summary_lines),
            "stderr": result.stderr.strip()[-2000:] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        elapsed = round(time.time() - start, 1)
        return {
            "script": script_path,
            "label": label,
            "exit_code": -1,
            "status": "TIMEOUT",
            "elapsed_s": elapsed,
            "stdout_summary": "",
            "stderr": f"Timed out after {timeout}s",
        }
    except Exception as e:
        elapsed = round(time.time() - start, 1)
        return {
            "script": script_path,
            "label": label,
            "exit_code": -1,
            "status": "ERROR",
            "elapsed_s": elapsed,
            "stdout_summary": "",
            "stderr": str(e),
        }


def parse_full_ic_output(text):
    """Extract IC pass count from full_ic.py output."""
    for line in reversed(text.split("\n")):
        line = line.strip()
        if "pass" in line.lower() and "/" in line:
            return line
    return ""


def parse_model_train_output(text):
    """Extract model metrics from train.py output."""
    metrics = {}
    for line in text.split("\n"):
        line = line.strip()
        for keyword in ["train", "cv", "gap", "accuracy", "feature", "sample"]:
            if keyword.lower() in line.lower() and ("=" in line or ":" in line):
                # Save relevant lines
                pass
    # Return last 20 lines as summary
    return "\n".join(text.strip().split("\n")[-20:]) if text.strip() else ""


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--hb", type=int, required=True, help="Heartbeat number")
    parser.add_argument("--fast", action="store_true", help="Fast mode: counts + IC only")
    parser.add_argument("--no-train", action="store_true", help="Skip model training")
    parser.add_argument("--no-dw", action="store_true", help="Skip dynamic window scan")
    args = parser.parse_args()

    hb_num = args.hb
    print(f"\n{'='*60}")
    print(f"  ⚡ Poly-Trader 心跳 #{hb_num} — 平行執行器")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{'='*60}\n")

    total_start = time.time()

    # Step 1: Quick DB counts (serial)
    print("[Step 0] Quick DB counts...")
    counts = quick_db_counts()
    for table, info in counts.items():
        if isinstance(info, dict) and "count" in info:
            print(f"  {table}: {info['count']} (latest: {info['latest']})")
        elif table == "sell_win":
            print(f"  sell_win_rate: {info['avg']} ({info['total']} labels)")

    if args.fast:
        # Fast mode: just run IC scripts
        scripts = [
            ("scripts/full_ic.py", "Full IC"),
            ("scripts/regime_aware_ic.py", "Regime IC"),
        ]
    else:
        # Full mode: all 5 scripts
        scripts = [
            ("scripts/full_ic.py", "Full IC"),
            ("scripts/regime_aware_ic.py", "Regime IC"),
        ]
        if not args.no_dw:
            scripts.append(("scripts/dynamic_window_train.py", "Dynamic Window"))
        if not args.no_train:
            scripts.append(("model/train.py", "Model Training"))
        scripts.append(("tests/comprehensive_test.py", "Tests"))

    print(f"\n[Step 1] Spawning {len(scripts)} tasks in parallel...")

    # Step 2: Parallel execution
    results = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=5) as executor:
        future_to_script = {
            executor.submit(run_script, script_path, label): (script_path, label)
            for script_path, label in scripts
        }
        for future in concurrent.futures.as_completed(future_to_script):
            script_path, label = future_to_script[future]
            try:
                result = future.result()
                results.append(result)
                status_icon = {"PASS": "🟢", "FAIL": "🔴", "TIMEOUT": "⏱️", "ERROR": "❌"}.get(
                    result["status"], "❓"
                )
                print(f"  {status_icon} {label}: {result['status']} ({result['elapsed_s']}s)")
            except Exception as e:
                print(f"  ❌ {label}: Exception — {e}")
                results.append(
                    {
                        "script": script_path,
                        "label": label,
                        "status": "ERROR",
                        "elapsed_s": 0,
                        "stderr": str(e),
                    }
                )

    elapsed_total = round(time.time() - total_start, 1)

    # Step 3: Print summaries
    print(f"\n{'='*60}")
    print(f"  📊 結果摘要 (心跳 #{hb_num}, {elapsed_total}s)")
    print(f"{'='*60}\n")

    for r in results:
        status_icon = {"PASS": "🟢", "FAIL": "🔴", "TIMEOUT": "⏱️", "ERROR": "❌"}.get(
            r["status"], "❓"
        )
        print(f"  {status_icon} {r['label']}: {r['status']} ({r.get('elapsed_s', '?')}s)")
        if r.get("stdout_summary"):
            for line in r["stdout_summary"].split("\n")[-10:]:
                if line.strip():
                    print(f"    {line}")
        if r.get("stderr"):
            print(f"    ⚠️ stderr: {r['stderr'][:200]}")
        print()

    pass_count = sum(1 for r in results if r["status"] == "PASS")
    total_count = len(results)
    print(f"  總結: {pass_count}/{total_count} PASS ({elapsed_total}s)")

    # Step 4: Save summary JSON
    summary = {
        "heartbeat": hb_num,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_elapsed_s": elapsed_total,
        "db_counts": counts,
        "results": {
            r["label"]: {
                "status": r["status"],
                "elapsed_s": r.get("elapsed_s", 0),
                "stderr": r.get("stderr", "")[:500],
            }
            for r in results
        },
        "pass_count": pass_count,
        "total_count": total_count,
    }

    out_dir = PROJECT_ROOT / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"heartbeat_{hb_num}_summary.json"
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n  💾 已保存: {out_path}")

    # Return results for further processing
    return summary, results


if __name__ == "__main__":
    main()
