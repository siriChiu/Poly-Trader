#!/usr/bin/env python3
"""Poly-Trader Heartbeat Parallel Runner v6
Runs all heartbeat diagnostics concurrently using ProcessPoolExecutor.
"""
import subprocess, sys, os, json, time, sqlite3
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)
os.environ["PYTHONPATH"] = str(PROJECT_ROOT)

PYTHON = str(PROJECT_ROOT / "venv" / "bin" / "python")
if not os.path.exists(PYTHON):
    PYTHON = sys.executable  # fallback


def run_script(script_path, env_extra=None, timeout=300):
    """Run a script and return (name, exit_code, stdout, stderr, elapsed)."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    if env_extra:
        env.update(env_extra)
    start = time.time()
    try:
        result = subprocess.run(
            [PYTHON, str(script_path)],
            capture_output=True, text=True, timeout=timeout, env=env,
            cwd=str(PROJECT_ROOT),
        )
        elapsed = time.time() - start
        return (script_path.name, result.returncode, result.stdout, result.stderr, elapsed)
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        return (script_path.name, -1, "", "TIMEOUT", elapsed)
    except Exception as e:
        elapsed = time.time() - start
        return (script_path.name, -2, "", str(e), elapsed)


def db_counts():
    """Quick DB counts."""
    db = sqlite3.connect(str(PROJECT_ROOT / "poly_trader.db"))
    counts = {}
    for t in ["raw_market_data", "features_normalized", "labels"]:
        counts[t] = db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    # Check data freshness
    latest_ts = db.execute(
        "SELECT MAX(timestamp) FROM raw_market_data"
    ).fetchone()[0]
    db.close()
    counts["latest_timestamp"] = latest_ts
    return counts


def main():
    hb_num = 301  # next heartbeat number
    start_total = time.time()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    print(f"🧬 Poly-Trader 心跳 #{hb_num} — 平行執行器")
    print(f"開始時間: {ts}")
    print("=" * 60)

    # Step 0: Quick DB counts
    print("\n📊 Step 0: 資料庫統計...")
    counts = db_counts()
    raw_count = counts.get("raw_market_data", 0)
    feat_count = counts.get("features_normalized", 0)
    label_count = counts.get("labels", 0)
    latest = counts.get("latest_timestamp", "N/A")
    print(f"  Raw market data: {raw_count}")
    print(f"  Features:        {feat_count}")
    print(f"  Labels:          {label_count}")
    print(f"  Latest data:     {latest}")

    # Build summary
    summary = {
        "heartbeat": hb_num,
        "timestamp": ts,
        "db_counts": counts,
        "tasks": {},
        "total_elapsed_s": 0,
    }

    # Step 1: Parallel execution of all heavy scripts
    scripts = [
        ("🔍 full_ic", PROJECT_ROOT / "scripts" / "full_ic.py"),
        ("🏛️ regime_aware_ic", PROJECT_ROOT / "scripts" / "regime_aware_ic.py"),
        ("📏 dynamic_window_train", PROJECT_ROOT / "scripts" / "dynamic_window_train.py"),
        ("🔨 model/train", PROJECT_ROOT / "model" / "train.py"),
        ("🧪 comprehensive_test", PROJECT_ROOT / "tests" / "comprehensive_test.py"),
    ]

    print(f"\n🚀 Step 1: 平行執行 {len(scripts)} 任務...")
    results = {}
    with ProcessPoolExecutor(max_workers=5) as executor:
        future_map = {}
        for label, script_path in scripts:
            if os.path.exists(script_path):
                f = executor.submit(run_script, script_path)
                future_map[f] = (label, str(script_path))
            else:
                results[label] = {
                    "status": "MISSING",
                    "returncode": -1,
                    "stdout": "",
                    "stderr": f"Script not found: {script_path}",
                    "elapsed_s": 0,
                }
                print(f"  ⚠️  {label}: 腳本不存在 ({script_path.name})")

        for future in as_completed(future_map):
            label, path = future_map[future]
            try:
                name, rc, stdout, stderr, elapsed = future.result()
                status = "PASS" if rc == 0 else "FAIL"
                results[label] = {
                    "status": status,
                    "returncode": rc,
                    "stdout": stdout[-2000:] if stdout else "",
                    "stderr": stderr[-1000:] if stderr else "",
                    "elapsed_s": round(elapsed, 1),
                }
                print(f"  {'✅' if rc == 0 else '❌'} {label} ({elapsed:.1f}s)")
            except Exception as e:
                results[label] = {
                    "status": "EXCEPTION",
                    "returncode": -2,
                    "stdout": "",
                    "stderr": str(e),
                    "elapsed_s": 0,
                }
                print(f"  ❌ {label}: 異常 {e}")

    total_elapsed = round(time.time() - start_total, 1)
    summary["tasks"] = results
    summary["total_elapsed_s"] = total_elapsed

    # Print summary
    print(f"\n{'=' * 60}")
    print(f"📋 心跳 #{hb_num} 總結")
    print(f"{'=' * 60}")
    passed = sum(1 for v in results.values() if v["status"] == "PASS")
    total = len(results)
    print(f"  通過: {passed}/{total}")
    print(f"  總耗時: {total_elapsed:.1f}s")

    for label, info in results.items():
        print(f"  {label}: {info['status']} ({info['elapsed_s']}s)")
        if info["stderr"] and info["status"] != "PASS":
            print(f"    錯誤: {info['stderr'][:200]}")

    print(f"\n  DB: Raw={raw_count}, Features={feat_count}, Labels={label_count}")

    # Save summary JSON
    summary_path = PROJECT_ROOT / "data" / f"heartbeat_{hb_num}_summary.json"
    os.makedirs(summary_path.parent, exist_ok=True)
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\n  總結已保存: {summary_path}")

    # Print key IC / model highlights from stdout
    for label, info in results.items():
        if info["stdout"]:
            print(f"\n--- {label} 輸出摘要 ---")
            # Print last 20 lines
            lines = info["stdout"].strip().split("\n")
            for line in lines[-20:]:
                print(f"  {line}")

    return results


if __name__ == "__main__":
    main()
