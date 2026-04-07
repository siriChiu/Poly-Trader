#!/usr/bin/env python3
"""Heartbeat Parallel Runner v7 — runs all diagnostics concurrently and saves summary.
Usage: python scripts/hb_parallel_runner.py --hb N [--fast] [--no-train] [--no-dw]
"""
import argparse, concurrent.futures, json, os, subprocess, sqlite3, sys
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
    try:
        env = {**os.environ, "PYTHONPATH": PROJECT_ROOT}
        result = subprocess.run(task["cmd"], cwd=PROJECT_ROOT,
                                capture_output=True, text=True, timeout=600,
                                env=env)
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
    sw = conn.execute("SELECT AVG(CAST(label_sell_win AS FLOAT)) FROM labels WHERE label_sell_win IS NOT NULL").fetchone()[0]
    results['sell_win_rate'] = round(sw, 4) if sw else 0
    conn.close()
    return results

def save_summary(hb_num, counts, results, elapsed):
    """Save heartbeat summary JSON."""
    passed = sum(1 for r in results.values() if r["success"])
    total = len(results)
    
    # Extract key metrics from outputs
    summary = {
        "heartbeat": hb_num,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "db_counts": counts,
        "parallel_results": {},
        "stats": {"passed": passed, "total": total, "elapsed_seconds": round(elapsed, 1)},
    }
    
    for name, r in results.items():
        summary["parallel_results"][name] = {
            "success": r["success"],
            "stdout_preview": r["stdout"][:2000] if r.get("stdout") else "",
            "stderr_preview": r["stderr"][:1000] if r.get("stderr") else "",
        }
    
    # Save JSON
    summary_path = os.path.join(PROJECT_ROOT, 'data', f'heartbeat_{hb_num}_summary.json')
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    return summary

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hb", type=int, required=True)
    parser.add_argument("--fast", action="store_true")
    parser.add_argument("--no-train", action="store_true")
    parser.add_argument("--no-dw", action="store_true")
    args = parser.parse_args()

    # Step 0: Quick DB counts (serial, <10s)
    counts = quick_counts()
    print(f"📊 DB Counts: Raw={counts['raw_market_data']}, Features={counts['features_normalized']}, Labels={counts['labels']}, sell_win={counts['sell_win_rate']}")
    
    tasks = TASKS.copy()
    if args.no_train: tasks = [t for t in tasks if t["name"] != "train"]
    if args.no_dw: tasks = [t for t in tasks if t["name"] != "dynamic_window"]
    if args.fast: tasks = [t for t in tasks if t["name"] in ["full_ic", "regime_ic"]]

    print(f"心跳 #{args.hb} 平行执行 — {len(tasks)} tasks")
    start = datetime.now()
    results = {}
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(len(tasks), 5)) as ex:
        f2n = {ex.submit(run_task, t): t["name"] for t in tasks}
        for f in concurrent.futures.as_completed(f2n):
            name = f2n[f]
            n, ok, out, err = f.result()
            results[name] = {"success": ok, "stdout": out, "stderr": err}
            print(f"  [{'✅' if ok else '❌'}] {name}")

    elapsed = (datetime.now() - start).total_seconds()
    passed = sum(1 for r in results.values() if r["success"])
    print(f"\n  {passed}/{len(results)} PASS ({elapsed:.1f}s)")
    
    # Print key outputs
    for name, r in results.items():
        if r.get("stdout"): 
            lines = r['stdout'].split('\n')
            # Show first 50 lines or last 30 lines (whichever is more informative)
            display = '\n'.join(lines[:50])
            if len(lines) > 50:
                display += '\n...\n' + '\n'.join(lines[-30:])
            print(f"\n--- {name} ---\n{display}")
        if r.get("stderr"): 
            stderr_lines = r['stderr'].strip().split('\n')
            # Show error lines but skip common noise
            errors = [l for l in stderr_lines if l.strip() and not l.startswith('Deprecation') and not l.startswith('FutureWarning')]
            if errors:
                print(f"\n--- {name} stderr ---\n" + '\n'.join(errors[:20]))

    # Save summary
    summary = save_summary(args.hb, counts, results, elapsed)
    print(f"\n📄 Summary saved: data/heartbeat_{args.hb}_summary.json")

if __name__ == '__main__':
    main()
