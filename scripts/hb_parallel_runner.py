#!/usr/bin/env python3
"""Heartbeat Parallel Runner v6 — runs all diagnostics concurrently and saves summary."""
import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
import sqlite3
from datetime import datetime, timezone

PROJECT_ROOT = '/home/kazuha/Poly-Trader'
PYTHON = os.path.join(PROJECT_ROOT, 'venv', 'bin', 'python')
DB_PATH = os.path.join(PROJECT_ROOT, 'poly_trader.db')

TASKS = [
    {"name": "full_ic", "label": "🔍 Full IC",
     "cmd": [PYTHON, "scripts/full_ic.py"]},
    {"name": "regime_ic", "label": "🏛️ Regime IC",
     "cmd": [PYTHON, "scripts/regime_aware_ic.py"]},
    {"name": "dynamic_window", "label": "📏 Dynamic Window",
     "cmd": [PYTHON, "scripts/dynamic_window_train.py"]},
    {"name": "train", "label": "🔨 Model Train",
     "cmd": [PYTHON, "model/train.py"]},
    {"name": "tests", "label": "🧪 Comprehensive Tests",
     "cmd": [PYTHON, "tests/comprehensive_test.py"]},
]


def run_task(task):
    """Run a single task and return (name, success, stdout, stderr)."""
    name = task["name"]
    label = task["label"]
    try:
        result = subprocess.run(
            task["cmd"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=600,
        )
        success = result.returncode == 0
        return (name, success, result.stdout.strip(), result.stderr.strip())
    except subprocess.TimeoutExpired:
        return (name, False, "", "TIMEOUT after 600s")
    except Exception as e:
        return (name, False, "", str(e))


def quick_counts():
    """Serial DB counts (<10s)."""
    conn = sqlite3.connect(DB_PATH)
    results = {}
    for table in ['raw_market_data', 'features_normalized', 'labels']:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        results[table] = count
    sw = conn.execute(
        "SELECT AVG(CAST(label_sell_win AS FLOAT)) FROM labels WHERE label_sell_win IS NOT NULL"
    ).fetchone()[0]
    results['sell_win_rate'] = round(sw, 4) if sw else 0
    conn.close()
    return results


def parse_ic_output(stdout):
    """Extract key metrics from full_ic.py output."""
    result = {"global_pass": 0, "tw_ic_pass": 0, "global_ics": {}, "tw_ics": {}}
    if not stdout:
        return result
    for line in stdout.split("\n"):
        line = line.strip()
        # Parse global IC lines like "eye: IC=+0.0135 ❌"
        if "IC=" in line and not line.startswith("Saved"):
            if "TW-IC" in line:
                parts = line.split("IC=")
                if len(parts) >= 2:
                    val = parts[1].split()[0].replace("+", "")
                    result["tw_ics"][line.split(":")[0].strip()] = float(val)
                    if abs(float(val)) >= 0.05:
                        result["tw_ic_pass"] += 1
            else:
                feat = line.split(":")[0].strip()
                if "IC=" in line:
                    parts = line.split("IC=")
                    if len(parts) >= 2:
                        val = parts[1].split()[0].replace("+", "")
                        result["global_ics"][feat] = float(val)
                        if abs(float(val)) >= 0.05:
                            result["global_pass"] += 1
    # Also extract summary lines
    for line in stdout.split("\n"):
        if "Global IC:" in line or "全域 IC:" in line:
            pass  # parsed above
    return result


def parse_regime_output(stdout):
    """Extract regime IC from output."""
    result = {"bear_pass": 0, "bull_pass": 0, "chop_pass": 0, "overall_sw": 0}
    if not stdout:
        return result
    for line in stdout.split("\n"):
        if "sell_win=" in line and "Overall" in line:
            try:
                result["overall_sw"] = float(line.split("sell_win=")[1].strip().split()[0])
            except (ValueError, IndexError):
                pass
    # Count passes from lines containing ✅/❌ per regime
    current_regime = None
    for line in stdout.split("\n"):
        for reg in ["bear", "bull", "chop"]:
            if line.strip().lower().startswith(reg) and "n=" in line:
                current_regime = reg
        if "✅" in line and current_regime:
            key = f"{current_regime}_pass"
            result[key] = result.get(key, 0) + 1
    return result


def parse_dw_output(stdout):
    """Parse dynamic window results."""
    result = {}
    if not stdout:
        return result
    for line in stdout.split("\n"):
        if "N=" in line and "/" in line:
            try:
                # e.g. "N=100: 7/8 ✅"
                if "N=" in line:
                    n_part = line.split("N=")[1].strip()
                    n_val = int(n_part.split(":")[0])
                    pass_part = n_part.split(":")[1].strip().split()[0]
                    if "/" in pass_part:
                        passed, total = pass_part.split("/")
                        result[f"N={n_val}"] = f"{passed.strip()}/{total.strip()}"
            except (ValueError, IndexError):
                pass
    return result


def parse_train_output(stdout):
    """Parse model training results."""
    result = {"train_acc": None, "cv_acc": None, "gap": None, "n_features": 0, "n_samples": 0}
    if not stdout:
        return result
    for line in stdout.split("\n"):
        if "Train accuracy" in line or "Train=" in line:
            try:
                if "Train=" in line:
                    parts = line.split("Train=")[1].split(",")[0]
                    result["train_acc"] = float(parts.replace("%", ""))
            except (ValueError, IndexError):
                pass
        if "CV accuracy" in line or "CV=" in line:
            try:
                if "CV=" in line:
                    parts = line.split("CV=")[1].split(",")[0]
                    result["cv_acc"] = float(parts.replace("%", ""))
            except (ValueError, IndexError):
                pass
        if "gap" in line and "gap=" in line:
            try:
                gap_str = line.split("gap=")[1].split("pp")[0]
                result["gap"] = float(gap_str.strip())
            except (ValueError, IndexError):
                pass
        if "features" in line:
            try:
                for part in line.split():
                    if part.isdigit():
                        result["n_features"] = max(result["n_features"], int(part))
            except:
                pass
    return result


def parse_test_output(stdout):
    """Parse comprehensive test results."""
    passed = stdout.count("[OK") + stdout.count("[PASS") + stdout.count("PASS")
    failed = stdout.count("[FAIL") + stdout.count("[FAIL]")
    total = passed + failed
    return {"passed": passed, "failed": failed, "total": total}


def main():
    parser = argparse.ArgumentParser(description="HB Parallel Runner")
    parser.add_argument("--hb", type=int, required=True, help="Heartbeat number")
    parser.add_argument("--fast", action="store_true", help="Fast mode: counts + quick IC only")
    parser.add_argument("--no-train", action="store_true", help="Skip model training")
    parser.add_argument("--no-dw", action="store_true", help="Skip dynamic window scan")
    args = parser.parse_args()

    hb_num = args.hb
    print(f"\n{'='*70}")
    print(f"  心跳 #{hb_num} 平行執行開始")
    print(f"  時間: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*70}")

    # Step 0: Quick DB counts (serial)
    print("\n📊 Step 0: 快速數據統計...")
    counts = quick_counts()
    for k, v in counts.items():
        print(f"  {k}: {v}")
    print()

    # Filter tasks
    tasks = TASKS.copy()
    if args.no_train:
        tasks = [t for t in tasks if t["name"] != "train"]
    if args.no_dw:
        tasks = [t for t in tasks if t["name"] != "dynamic_window"]

    if args.fast:
        tasks = [t for t in tasks if t["name"] in ["full_ic", "regime_ic"]]

    # Run in parallel
    print(f"🚀 Launching {len(tasks)} tasks in parallel...")
    start_time = datetime.now()
    results = {}

    with concurrent.futures.ProcessPoolExecutor(max_workers=len(tasks)) as executor:
        future_to_name = {executor.submit(run_task, t): t["name"] for t in tasks}
        for future in concurrent.futures.as_completed(future_to_name):
            name = future_to_name[future]
            try:
                fname, success, stdout, stderr = future.result()
                results[name] = {
                    "success": success,
                    "stdout": stdout,
                    "stderr": stderr,
                }
                status = "✅ PASS" if success else "❌ FAIL"
                print(f"  [{status}] {fname}")
            except Exception as e:
                results[name] = {
                    "success": False,
                    "stdout": "",
                    "stderr": str(e),
                }
                print(f"  [❌ ERROR] {name}: {e}")

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n⏱️  Total parallel time: {elapsed:.1f}s")

    # Parse outputs
    ic_result = parse_ic_output(results.get("full_ic", {}).get("stdout", ""))
    regime_result = parse_regime_output(results.get("regime_ic", {}).get("stdout", ""))
    dw_result = parse_dw_output(results.get("dynamic_window", {}).get("stdout", ""))
    train_result = parse_train_output(results.get("train", {}).get("stdout", ""))
    test_result = parse_test_output(results.get("tests", {}).get("stdout", ""))

    # Print summary
    print(f"\n{'='*70}")
    print(f"  心跳 #{hb_num} 執行摘要")
    print(f"{'='*70}")
    print(f"  DB: Raw={counts.get('raw_market_data', '?')}, "
          f"Feat={counts.get('features_normalized', '?')}, "
          f"Labels={counts.get('labels', '?')}, "
          f"sell_win={counts.get('sell_win_rate', '?')}")

    # All tasks status
    pass_count = sum(1 for r in results.values() if r["success"])
    print(f"  平行任務: {pass_count}/{len(results)} PASS ({elapsed:.1f}s)")

    # Test status
    if test_result.get("total", 0) > 0:
        print(f"  測試: {test_result['passed']}/{test_result['total']}")

    # IC summary
    if ic_result.get("global_pass", None) is not None:
        print(f"  全域 IC: {ic_result['global_pass']}/15 (5 TI included)")
    if ic_result.get("tw_ic_pass", 0) > 0:
        print(f"  TW-IC: {ic_result['tw_ic_pass']}/15")

    # Regime
    if regime_result:
        print(f"  Regime IC: Bear={regime_result.get('bear_pass', '?')}/8, "
              f"Bull={regime_result.get('bull_pass', '?')}/8, "
              f"Chop={regime_result.get('chop_pass', '?')}/8")

    # Dynamic Window
    if dw_result:
        for w, v in dw_result.items():
            print(f"  DW {w}: {v}")

    # Train
    if train_result.get("train_acc"):
        print(f"  模型: Train={train_result['train_acc']:.2f}%, "
              f"CV={train_result.get('cv_acc', '?')}%, "
              f"gap={train_result.get('gap', '?')}pp")

    # Save JSON summary
    os.makedirs(os.path.join(PROJECT_ROOT, 'data'), exist_ok=True)
    summary_path = os.path.join(PROJECT_ROOT, f'data/heartbeat_{hb_num}_summary.json')
    summary = {
        "heart beat": hb_num,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "counts": counts,
        "tasks": {n: {"success": r["success"]} for n, r in results.items()},
        "parallel_time_sec": round(elapsed, 1),
        "ic": ic_result,
        "regime": regime_result,
        "dynamic_window": dw_result,
        "train": train_result,
        "tests": test_result,
    }
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\n💾 摘要已存至 {summary_path}")
    print(f"{'='*70}\n")

    # Print raw outputs for parsing
    for name, r in results.items():
        if r.get("stdout"):
            print(f"\n--- {name} stdout (first 2000 chars) ---")
            print(r["stdout"][:2000])
        if r.get("stderr"):
            print(f"\n--- {name} stderr ---")
            print(r["stderr"][:500])


if __name__ == '__main__':
    main()
