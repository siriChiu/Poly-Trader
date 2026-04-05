#!/usr/bin/env python3
"""
hb_parallel_runner.py — Poly-Trader Parallel Heartbeat Executor

Uses ProcessPoolExecutor to run all heavy tasks concurrently:
1. full_ic.py — Global + TW-IC analysis
2. regime_aware_ic.py — Regime-aware IC
3. dynamic_window_train.py — Dynamic window scanning
4. model/train.py — XGBoost model training
5. tests/comprehensive_test.py — Full test suite

Usage:
  python scripts/hb_parallel_runner.py --hb N        # Full parallel run
  python scripts/hb_parallel_runner.py --hb N --fast # Fast mode (counts + IC only)
  python scripts/hb_parallel_runner.py --hb N --no-train --no-dw  # Skip heavy steps
"""

import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
import time
from datetime import datetime

PROJECT_ROOT = '/home/kazuha/Poly-Trader'
DB_PATH = f'{PROJECT_ROOT}/poly_trader.db'
PYTHON = os.path.join(PROJECT_ROOT, 'venv', 'bin', 'python')

def quick_db_counts():
    """Quick DB counts serial (<10s)."""
    import sqlite3
    counts = {}
    try:
        conn = sqlite3.connect(DB_PATH)
        for table in ['raw_market_data', 'features_normalized', 'labels']:
            count = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
            counts[table] = count
        # Check latest timestamp
        ts_max = conn.execute('SELECT MAX(timestamp) FROM raw_market_data').fetchone()[0]
        counts['latest_raw_ts'] = ts_max or 'N/A'
        
        # Sell win rate
        try:
            row = conn.execute('SELECT AVG(label_sell_win), COUNT(*) FROM labels WHERE label_sell_win IS NOT NULL').fetchone()
            counts['sell_win'] = round(row[0], 4) if row[0] else None
            counts['labels_with_sell'] = row[1]
        except:
            pass
        conn.close()
    except Exception as e:
        print(f"DB count error: {e}")
    return counts

def run_script(name, script_path, timeout=600):
    """Run a single script and capture output."""
    print(f"[{name}] Starting: {script_path}")
    start = time.time()
    env = os.environ.copy()
    env['PYTHONPATH'] = PROJECT_ROOT
    
    try:
        result = subprocess.run(
            [PYTHON, script_path],
            capture_output=True, text=True, timeout=timeout,
            cwd=PROJECT_ROOT, env=env
        )
        elapsed = round(time.time() - start, 1)
        exit_ok = result.returncode == 0
        status = "PASS" if exit_ok else f"FAIL (exit={result.returncode})"
        
        # Extract key metrics from stdout
        summary_lines = []
        for line in result.stdout.strip().split('\n')[-20:]:  # Last 20 lines
            summary_lines.append(line)
        
        return {
            'name': name, 'script': script_path, 'status': status,
            'exit_code': result.returncode, 'elapsed_s': elapsed,
            'stdout_tail': '\n'.join(summary_lines),
            'stderr': '' if exit_ok else result.stderr[:500],
            'stdout_full': result.stdout,
        }
    except subprocess.TimeoutExpired:
        elapsed = round(time.time() - start, 1)
        return {
            'name': name, 'script': script_path, 'status': f'TIMEOUT ({timeout}s)',
            'exit_code': -1, 'elapsed_s': elapsed, 'stdout_tail': '', 'stderr': f'Timed out after {timeout}s',
            'stdout_full': '',
        }
    except Exception as e:
        return {
            'name': name, 'script': script_path, 'status': f'ERROR: {e}',
            'exit_code': -1, 'elapsed_s': 0, 'stdout_tail': '', 'stderr': str(e)[:500],
            'stdout_full': '',
        }

def main():
    parser = argparse.ArgumentParser(description='Poly-Trader Parallel Heartbeat Runner')
    parser.add_argument('--hb', type=int, required=True, help='Heartbeat number')
    parser.add_argument('--fast', action='store_true', help='Fast mode — only counts + IC')
    parser.add_argument('--no-train', action='store_true', help='Skip model training')
    parser.add_argument('--no-dw', action='store_true', help='Skip dynamic window scan')
    parser.add_argument('--no-tests', action='store_true', help='Skip tests')
    parser.add_argument('--no-regime', action='store_true', help='Skip regime IC')
    args = parser.parse_args()
    
    hb_num = args.hb
    print("=" * 70)
    print(f"Poly-Trader 平行心跳 #{hb_num}")
    print(f"Started: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 70)
    
    overall_start = time.time()
    
    # Step 0: Quick DB counts
    print("\n[Step 0] Quick DB counts...")
    counts = quick_db_counts()
    for k, v in counts.items():
        print(f"  {k}: {v}")
    
    if args.fast:
        print("\nFast mode — running IC only (serial)")
        ic_result = run_script('full_ic', f'{PROJECT_ROOT}/scripts/full_ic.py')
        print(f"\n  full_ic: {ic_result['status']} ({ic_result['elapsed_s']}s)")
        
        total = round(time.time() - overall_start, 1)
        summary = {
            'heartbeat': hb_num,
            'timestamp': datetime.utcnow().isoformat(),
            'db_counts': counts,
            'elapsed_s': total,
            'mode': 'fast',
            'tasks': {'full_ic': ic_result},
        }
        os.makedirs(f'{PROJECT_ROOT}/data', exist_ok=True)
        with open(f'{PROJECT_ROOT}/data/heartbeat_{hb_num}_summary.json', 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        print(f"\nSummary saved to data/heartbeat_{hb_num}_summary.json")
        print(f"Total elapsed: {total}s")
        return summary
    
    # Step 1-5: Parallel execution
    print("\n[Step 1-5] Parallel execution...")
    
    tasks = []
    
    # Task 1: Full IC
    tasks.append(('full_ic', f'{PROJECT_ROOT}/scripts/full_ic.py'))
    # Task 2: Regime IC
    tasks.append(('regime_ic', f'{PROJECT_ROOT}/scripts/regime_aware_ic.py'))
    
    if not args.no_dw:
        # Task 3: Dynamic window
        tasks.append(('dynamic_window', f'{PROJECT_ROOT}/scripts/dynamic_window_train.py'))
    
    if not args.no_train:
        # Task 4: Model training
        tasks.append(('model_train', f'{PROJECT_ROOT}/model/train.py'))
    
    if not args.no_tests:
        # Task 5: Tests
        tasks.append(('tests', f'{PROJECT_ROOT}/tests/comprehensive_test.py'))
    
    print(f"Spawning {len(tasks)} tasks in parallel...")
    print("  1. full_ic.py")
    print("  2. regime_aware_ic.py")
    if not args.no_dw: print("  3. dynamic_window_train.py")
    if not args.no_train: print("  4. model/train.py")
    if not args.no_tests: print("  5. tests/comprehensive_test.py")
    
    results = {}
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(5, len(tasks))) as executor:
        future_to_name = {}
        for name, path in tasks:
            future = executor.submit(run_script, name, path)
            future_to_name[future] = name
        
        for future in concurrent.futures.as_completed(future_to_name):
            name = future_to_name[future]
            try:
                res = future.result()
                results[name] = res
                print(f"\n  ✅ {name}: {res['status']} ({res['elapsed_s']}s)")
            except Exception as e:
                print(f"\n  ❌ {name}: EXCEPTION — {e}")
                results[name] = {'name': name, 'status': f'EXCEPTION: {e}', 'elapsed_s': 0}
    
    # Summary
    total = round(time.time() - overall_start, 1)
    passed = sum(1 for r in results.values() if r.get('exit_code') == 0)
    total_tasks = len(results)
    
    print(f"\n{'='*70}")
    print(f"平行心跳 #{hb_num} COMPLETE — {passed}/{total_tasks} PASS ({total}s)")
    print(f"{'='*70}")
    for name, res in results.items():
        print(f"  {name:20s}: {res['status']:25s} ({res.get('elapsed_s', 0):>6.1f}s)")
    
    # Save summary JSON
    summary = {
        'heartbeat': hb_num,
        'timestamp': datetime.utcnow().isoformat(),
        'db_counts': counts,
        'elapsed_s': total,
        'mode': 'parallel',
        'passed': passed,
        'total_tasks': total_tasks,
        'tasks': {k: {kk: vv for kk, vv in v.items() if kk != 'stdout_full'} for k, v in results.items()},
    }
    
    os.makedirs(f'{PROJECT_ROOT}/data', exist_ok=True)
    with open(f'{PROJECT_ROOT}/data/heartbeat_{hb_num}_summary.json', 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\nSummary saved to data/heartbeat_{hb_num}_summary.json")
    
    return summary


if __name__ == '__main__':
    main()
