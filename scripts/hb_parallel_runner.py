#!/usr/bin/env python3
"""
Poly-Trader Heartbeat Parallel Runner v5
Uses ProcessPoolExecutor to run all diagnostic scripts concurrently.

Usage:
  python scripts/hb_parallel_runner.py --hb N
  python scripts/hb_parallel_runner.py --hb N --fast      # counts + IC only
  python scripts/hb_parallel_runner.py --hb N --no-train  # skip model training
  python scripts/hb_parallel_runner.py --hb N --no-dw     # skip dynamic window
"""

import argparse
import json
import os
import sqlite3
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime

PROJECT_ROOT = '/home/kazuha/Poly-Trader'
DB_PATH = os.path.join(PROJECT_ROOT, 'poly_trader.db')
os.environ['PYTHONPATH'] = PROJECT_ROOT


def quick_db_counts():
    """Quick DB counts via direct sqlite3."""
    conn = sqlite3.connect(DB_PATH)
    result = {}
    for table in ['raw_market_data', 'features_normalized', 'labels']:
        count = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
        result[table] = count
    # Sell win rate
    sell_win = conn.execute(
        "SELECT AVG(CAST(label_sell_win AS FLOAT)) FROM labels WHERE label_sell_win IS NOT NULL"
    ).fetchone()[0]
    result['sell_win_rate'] = round(sell_win, 4) if sell_win else None
    # Max timestamps
    for table in ['raw_market_data', 'features_normalized', 'labels']:
        max_ts = conn.execute(f"SELECT MAX(timestamp) FROM {table}").fetchone()[0]
        result[f'{table}_max_ts'] = max_ts
    conn.close()
    return result


def run_script(script_path, timeout=300):
    """Run a Python script and capture output."""
    import subprocess
    full_path = os.path.join(PROJECT_ROOT, script_path)
    if not os.path.exists(full_path):
        return {
            'script': script_path,
            'status': 'SKIP',
            'stdout': f'Script not found: {full_path}',
            'stderr': '',
            'exit_code': -1,
        }
    venv_python = os.path.join(PROJECT_ROOT, 'venv', 'bin', 'python')
    python_exe = venv_python if os.path.exists(venv_python) else sys.executable
    env = os.environ.copy()
    env['PYTHONPATH'] = PROJECT_ROOT
    try:
        result = subprocess.run(
            [python_exe, full_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=PROJECT_ROOT,
            env=env,
        )
        return {
            'script': script_path,
            'status': 'PASS' if result.returncode == 0 else 'FAIL',
            'stdout': result.stdout[-2000:] if result.stdout else '',
            'stderr': result.stderr[-2000:] if result.stderr else '',
            'exit_code': result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            'script': script_path,
            'status': 'TIMEOUT',
            'stdout': f'Timed out after {timeout}s',
            'stderr': '',
            'exit_code': -2,
        }
    except Exception as e:
        return {
            'script': script_path,
            'status': 'ERROR',
            'stdout': '',
            'stderr': str(e),
            'exit_code': -3,
        }


def main():
    parser = argparse.ArgumentParser(description='Poly-Trader Parallel Heartbeat Runner')
    parser.add_argument('--hb', type=int, required=True, help='Heartbeat number')
    parser.add_argument('--fast', action='store_true', help='Fast mode: counts + IC only')
    parser.add_argument('--no-train', action='store_true', help='Skip model training')
    parser.add_argument('--no-dw', action='store_true', help='Skip dynamic window scan')
    args = parser.parse_args()

    hb_num = args.hb
    print(f"{'='*60}")
    print(f"  Poly-Trader 心跳 #{hb_num} — 平行執行器 v5")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    start_time = time.time()

    # --- Step 0: Quick DB counts (serial) ---
    print("\n[Step 0] Quick DB counts...")
    counts = quick_db_counts()
    print(f"  Raw: {counts.get('raw_market_data', '?')}")
    print(f"  Features: {counts.get('features_normalized', '?')}")
    print(f"  Labels: {counts.get('labels', '?')}")
    print(f"  Sell Win: {counts.get('sell_win_rate', '?')}")

    if args.fast:
        # Fast mode: also run IC scripts serially
        print("\n[Fast mode] Running IC scripts...")
        ic_scripts = [
            'scripts/full_ic.py',
            'scripts/regime_aware_ic.py',
        ]
        for script in ic_scripts:
            print(f"\n  Running {script}...")
            result = run_script(script)
            print(f"  {result['status']}")
            if result['stdout']:
                print(result['stdout'][-500:])
            if result['stderr']:
                print(f"  STDERR: {result['stderr'][-300:]}")
        elapsed = time.time() - start_time
        print(f"\n✅ Heartbeat #{hb_num} complete (fast mode) in {elapsed:.1f}s")
        return

    # --- Step 1: Parallel execution ---
    tasks = []

    # Always run these
    tasks.append(('full_ic.py', 'scripts/full_ic.py'))
    tasks.append(('regime_ic.py', 'scripts/regime_aware_ic.py'))
    tasks.append(('comprehensive_test.py', 'tests/comprehensive_test.py'))

    if not args.no_dw:
        tasks.append(('dynamic_window.py', 'scripts/dynamic_window_train.py'))
    if not args.no_train:
        tasks.append(('train.py', 'model/train.py'))

    print(f"\n[Step 1] Running {len(tasks)} tasks in parallel...")
    print(f"  Tasks: {[t[0] for t in tasks]}")

    results = {}
    with ProcessPoolExecutor(max_workers=min(len(tasks), 5)) as executor:
        future_map = {
            executor.submit(run_script, script_path, 300): label
            for label, script_path in tasks
        }
        for future in as_completed(future_map):
            label = future_map[future]
            result = future.result()
            results[label] = result
            status_emoji = '✅' if result['status'] == 'PASS' else '❌'
            print(f"  {status_emoji} {label}: {result['status']}")
            if result['stdout']:
                # Print last 300 chars of stdout
                lines = result['stdout'].strip().split('\n')
                for line in lines[-8:]:
                    if line.strip():
                        print(f"    {line}")
            if result['stderr'] and result['status'] != 'PASS':
                lines = result['stderr'].strip().split('\n')
                for line in lines[-5:]:
                    if line.strip():
                        print(f"    ERR: {line}")

    elapsed = time.time() - start_time
    passed = sum(1 for r in results.values() if r['status'] == 'PASS')
    total = len(results)

    # --- Save summary JSON ---
    summary = {
        'heartbeat': hb_num,
        'timestamp': datetime.now().isoformat(),
        'db_counts': counts,
        'parallel_results': {k: {'status': v['status'], 'exit_code': v['exit_code']} for k, v in results.items()},
        'elapsed_seconds': round(elapsed, 1),
        'passed': passed,
        'total': total,
    }

    os.makedirs(os.path.join(PROJECT_ROOT, 'data'), exist_ok=True)
    summary_path = os.path.join(PROJECT_ROOT, f'data/heartbeat_{hb_num}_summary.json')
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n{'='*60}")
    print(f"  ✅ Heartbeat #{hb_num} complete: {passed}/{total} PASS in {elapsed:.1f}s")
    print(f"  Summary saved to {summary_path}")
    print(f"{'='*60}")

    # Print IC summary from full_ic.py output if available
    if 'full_ic.py' in results and results['full_ic.py']['status'] == 'PASS':
        print("\n📊 IC Analysis Output:")
        print(results['full_ic.py']['stdout'][-1500:])

    if 'regime_ic.py' in results and results['regime_ic.py']['status'] == 'PASS':
        print("\n🏛️ Regime IC Output:")
        print(results['regime_ic.py']['stdout'][-1500:])

    return summary


if __name__ == '__main__':
    main()
