#!/usr/bin/env python3
"""Poly-Trader Parallel Heartbeat Runner — hb #385

Runs 5 diagnostics concurrently via ProcessPoolExecutor:
  1. scripts/full_ic.py
  2. scripts/regime_aware_ic.py
  3. scripts/dynamic_window_train.py
  4. model/train.py
  5. tests/comprehensive_test.py

Also does quick DB counts + freshness checks serially first.
Saves summary JSON to data/heartbeat_385_summary.json
"""

import argparse, json, os, sys, time, subprocess, sqlite3
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime

PROJECT_ROOT = "/home/kazuha/Poly-Trader"
VENV_PYTHON = os.path.join(PROJECT_ROOT, "venv/bin/python")
HB_NUM = 385


def quick_db_checks():
    """Serial DB counts + freshness — returns dict."""
    result = {}
    try:
        db = sqlite3.connect(os.path.join(PROJECT_ROOT, "poly_trader.db"))
        for t in ["raw_market_data", "features_normalized", "labels"]:
            result[t] = db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        # Freshness
        for t, col_name in [
            ("raw_market_data", "timestamp"),
            ("labels", "timestamp"),
        ]:
            row = db.execute(f'SELECT MAX("{col_name}") FROM {t}').fetchone()
            result[f"{t}_max_ts"] = row[0] if row else None
        # sell_win rate
        row = db.execute(
            "SELECT AVG(CAST(label_sell_win AS FLOAT)) FROM labels WHERE label_sell_win IS NOT NULL"
        ).fetchone()
        result["sell_win_rate"] = round(row[0] * 100, 2) if row[0] else None
        db.close()
    except Exception as e:
        result["error"] = str(e)
    return result


def run_script(script_path, label):
    """Run a single script and capture output. Returns dict with status."""
    start = time.time()
    result = {"label": label, "script": script_path}
    try:
        proc = subprocess.run(
            [VENV_PYTHON, script_path],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=PROJECT_ROOT,
            env={**os.environ, "PYTHONPATH": PROJECT_ROOT, "HB_NUM": str(HB_NUM)},
        )
        result["exit_code"] = proc.returncode
        result["duration_s"] = round(time.time() - start, 1)
        # Capture last 2000 chars of output
        result["stdout_tail"] = proc.stdout[-2000:] if proc.stdout else ""
        result["stderr_tail"] = proc.stderr[-1000:] if proc.stderr else ""
        result["status"] = "PASS" if proc.returncode == 0 else "FAIL"

        # Extract key metrics from stdout
        for line in proc.stdout.split("\n"):
            line = line.strip()
            if "sell_win" in line.lower():
                result["sell_win"] = line
            if "cv" in line.lower() and ("%" in line or "accuracy" in line.lower()):
                result["cv"] = line
            if "train" in line.lower() and ("%" in line or "accuracy" in line.lower()):
                result["train"] = line
        return result
    except subprocess.TimeoutExpired:
        result["status"] = "TIMEOUT"
        result["duration_s"] = 300
        return result
    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)
        result["duration_s"] = round(time.time() - start, 1)
        return result


def summarize(full_ic_out, regime_ic_out, dw_out, train_out, test_out):
    """Generate human-readable summary from all results."""
    lines = [f"\n{'='*60}", f"  心跳 #{HB_NUM} 平行心跳摘要", f"{'='*60}"]
    for r in [full_ic_out, regime_ic_out, dw_out, train_out, test_out]:
        status_emoji = "✅" if r["status"] == "PASS" else "❌"
        lines.append(
            f"  {status_emoji} {r['label']}: {r['status']} ({r.get('duration_s', '?')}s)"
        )
        if r.get("stderr_tail") and r["status"] != "PASS":
            lines.append(f"     stderr: {r['stderr_tail'][:200]}")
    lines.append(f"{'='*60}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hb", type=int, default=HB_NUM)
    parser.add_argument("--fast", action="store_true", help="Skip train + DW")
    parser.add_argument("--no-train", action="store_true")
    parser.add_argument("--no-dw", action="store_true")
    args = parser.parse_args()

    hb_num = args.hb
    print(f"🧬 平行心跳 #{hb_num} 開始 {datetime.now().strftime('%H:%M:%S')}")

    # Step 0: Quick DB counts (serial)
    t0 = time.time()
    db_info = quick_db_checks()
    print(f"\n📊 DB Counts: Raw={db_info.get('raw_market_data', '?')}, "
          f"Features={db_info.get('features_normalized', '?')}, "
          f"Labels={db_info.get('labels', '?')}, "
          f"sell_win={db_info.get('sell_win_rate', '?')}%")
    print(f"   Raw max ts: {db_info.get('raw_market_data_max_ts', '?')}")
    print(f"   Labels max ts: {db_info.get('labels_max_ts', '?')}")

    # Step 1: Parallel execution
    scripts_to_run = [
        (os.path.join(PROJECT_ROOT, "scripts/full_ic.py"), "🔍 Full IC"),
        (os.path.join(PROJECT_ROOT, "scripts/regime_aware_ic.py"), "🏛️ Regime IC"),
    ]
    if not args.no_dw and not args.fast:
        scripts_to_run.append(
            (os.path.join(PROJECT_ROOT, "scripts/dynamic_window_train.py"), "📏 Dynamic Window")
        )
    if not args.no_train and not args.fast:
        scripts_to_run.append(
            (os.path.join(PROJECT_ROOT, "model/train.py"), "🔨 Model Train")
        )
    scripts_to_run.append(
        (os.path.join(PROJECT_ROOT, "tests/comprehensive_test.py"), "🧪 Tests")
    )

    print(f"\n🚀 啟動 {len(scripts_to_run)} 個平行任務...")
    results = {}
    with ProcessPoolExecutor(max_workers=min(len(scripts_to_run), 5)) as executor:
        futures = {
            executor.submit(run_script, path, label): label
            for path, label in scripts_to_run
        }
        for future in as_completed(futures):
            label = futures[future]
            try:
                r = future.result()
                results[label] = r
                emoji = "✅" if r["status"] == "PASS" else "❌"
                print(f"  {emoji} {label}: {r['status']} ({r.get('duration_s', '?')}s)")
            except Exception as e:
                results[label] = {"label": label, "status": "ERROR", "error": str(e)}
                print(f"  ❌ {label}: ERROR — {e}")

    elapsed = round(time.time() - t0, 1)
    total_elapsed = round(time.time() - t0, 1)
    pass_count = sum(1 for r in results.values() if r["status"] == "PASS")
    total_count = len(results)
    print(f"\n⏱️  總耗時: {elapsed}s | 結果: {pass_count}/{total_count} PASS")

    # Save summary
    summary_data = {
        "hb": hb_num,
        "timestamp": datetime.now().isoformat(),
        "db": db_info,
        "results": {k: {kk: vv for kk, vv in v.items() if kk not in ("stdout_tail", "stderr_tail")}
                     for k, v in results.items()},
        "total_elapsed_s": total_elapsed,
        "pass_count": pass_count,
        "total_count": total_count,
    }
    os.makedirs(os.path.join(PROJECT_ROOT, "data"), exist_ok=True)
    out_path = os.path.join(PROJECT_ROOT, f"data/heartbeat_{hb_num}_summary.json")
    with open(out_path, "w") as f:
        json.dump(summary_data, f, indent=2, default=str)
    print(f"\n📁 摘要已存: {out_path}")

    # Print summary
    summary_text = summarize(
        results.get("🔍 Full IC", {}),
        results.get("🏛️ Regime IC", {}),
        results.get("📏 Dynamic Window", {}),
        results.get("🔨 Model Train", {}),
        results.get("🧪 Tests", {}),
    )
    print(summary_text)

    # Append results to stdout_tail for extraction
    for label, r in results.items():
        if r.get("stdout_tail"):
            print(f"\n--- {label} OUTPUT ---")
            print(r["stdout_tail"][-3000:])

    return 0 if pass_count == total_count else 1


if __name__ == "__main__":
    sys.exit(main())
