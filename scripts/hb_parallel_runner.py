#!/usr/bin/env python3
"""Poly-Trader 平行心跳執行器 v6 — multi-process parallel runner.

Spawns full_ic.py, regime_aware_ic.py, dynamic_window_train.py,
model/train.py, and tests/comprehensive_test.py concurrently.

Usage:
    python scripts/hb_parallel_runner.py --hb N
    python scripts/hb_parallel_runner.py --hb N --no-train --no-dw
    python scripts/hb_parallel_runner.py --fast
"""
import argparse
import concurrent.futures
import json
import os
import sqlite3
import subprocess
import sys
import time

PROJECT_ROOT = '/home/kazuha/Poly-Trader'
DB_PATH = os.path.join(PROJECT_ROOT, 'poly_trader.db')
# Use the Poly-Trader venv python, NOT sys.executable (which may be Hermes venv)
_VENV_PYTHON = os.path.join(PROJECT_ROOT, 'venv', 'bin', 'python')
if not os.path.isfile(_VENV_PYTHON):
    _VENV_PYTHON = sys.executable  # fallback

# Core scripts that always run
ALWAYS_TASKS = [
    {"name": "full_ic", "script": "scripts/full_ic.py"},
    {"name": "regime_aware_ic", "script": "scripts/regime_aware_ic.py"},
]
OPTIONAL_TASKS = {
    "dynamic_window": {"name": "dynamic_window", "script": "scripts/dynamic_window_train.py"},
    "train": {"name": "model_train", "script": "model/train.py"},
    "tests": {"name": "comprehensive_test", "script": "tests/comprehensive_test.py"},
}


def quick_db_counts():
    """Serial step: get Raw / Features / Labels counts (<10s)."""
    print("=" * 60)
    print(" Step 0: 快速數據統計")
    print("=" * 60)
    t0 = time.time()
    conn = sqlite3.connect(DB_PATH)
    for table in ['raw_market_data', 'features_normalized', 'labels']:
        try:
            count = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
            print(f"  {table}: {count:,}")
        except Exception as e:
            print(f"  {table}: ERROR - {e}")
    # Sell win rate
    try:
        row = conn.execute("SELECT COUNT(*), SUM(label_sell_win) FROM labels WHERE label_sell_win IS NOT NULL").fetchone()
        if row[0] > 0:
            print(f"  sell_win: {row[1] / row[0]:.4f} ({row[0]:,} labeled)")
    except Exception:
        pass
    # Latest timestamp
    try:
        latest = conn.execute("SELECT MAX(timestamp) FROM raw_market_data").fetchone()[0]
        print(f"  Latest raw: {latest}")
    except Exception:
        pass
    conn.close()
    elapsed = time.time() - t0
    print(f"  Done in {elapsed:.1f}s\n")
    return elapsed


def run_one_script(task, hb_num):
    """Run one script, capture stdout+stderr. Called inside a subprocess."""
    script = task['script']
    name = task['name']
    script_path = os.path.join(PROJECT_ROOT, script)

    if not os.path.isfile(script_path):
        return {
            'name': name,
            'script': script,
            'status': 'SKIPPED',
            'stdout': f"Script not found: {script_path}",
            'stderr': '',
            'elapsed_s': 0,
        }

    cmd = [_VENV_PYTHON, script_path, '--hb', str(hb_num)]
    env = os.environ.copy()
    env['PYTHONPATH'] = PROJECT_ROOT
    env['LC_ALL'] = 'C.UTF-8'

    t0 = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 min per script
            cwd=PROJECT_ROOT,
            env=env,
        )
        elapsed = time.time() - t0
        return {
            'name': name,
            'script': script,
            'status': 'PASS' if result.returncode == 0 else 'FAIL',
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode,
            'elapsed_s': round(elapsed, 1),
        }
    except subprocess.TimeoutExpired:
        elapsed = time.time() - t0
        return {
            'name': name,
            'script': script,
            'status': 'TIMEOUT',
            'stdout': '',
            'stderr': f'{script} timed out after 600s',
            'elapsed_s': round(elapsed, 1),
        }
    except Exception as e:
        elapsed = time.time() - t0
        return {
            'name': name,
            'script': script,
            'status': 'ERROR',
            'stdout': '',
            'stderr': str(e),
            'elapsed_s': round(elapsed, 1),
        }


def parallel_run(tasks, hb_num, max_workers=5):
    """Run multiple tasks in parallel using ProcessPoolExecutor."""
    results = {}
    print("=" * 60)
    print(f" Steps 1-{len(tasks)}: 平行執行 {len(tasks)} 個任務 (workers={max_workers})")
    print("=" * 60)
    t_start = time.time()

    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_name = {}
        for task in tasks:
            f = executor.submit(run_one_script, task, hb_num)
            future_to_name[f] = task['name']

        for future in concurrent.futures.as_completed(future_to_name):
            name = future_to_name[future]
            try:
                result = future.result()
                status_icon = {"PASS": "✅", "FAIL": "❌", "TIMEOUT": "⏱️", "ERROR": "💥", "SKIPPED": "⏭️"}
                icon = status_icon.get(result['status'], '❓')
                print(f"  {icon} {name}: {result['status']} ({result['elapsed_s']:.1f}s)")
                results[name] = result
            except Exception as e:
                print(f"  💥 {name}: EXCEPTION - {e}")
                results[name] = {
                    'name': name,
                    'status': 'ERROR',
                    'stdout': '',
                    'stderr': str(e),
                    'elapsed_s': 0,
                }

    total = time.time() - t_start
    print(f"\n  平行執行總時間: {total:.1f}s\n")
    return results, total


def run_live_market_data():
    """Serial step after parallel: get live market data."""
    print("=" * 60)
    print(" Step: Live market data")
    print("=" * 60)
    t0 = time.time()
    cmd = [_VENV_PYTHON, os.path.join(PROJECT_ROOT, 'scripts/get_live_market_data.py')]
    env = os.environ.copy()
    env['PYTHONPATH'] = PROJECT_ROOT
    env['LC_ALL'] = 'C.UTF-8'
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                                cwd=PROJECT_ROOT, env=env)
        elapsed = time.time() - t0
        print(result.stdout)
        if result.stderr:
            print("[STDERR]", result.stderr[:500])
        return {'status': 'PASS' if result.returncode == 0 else 'FAIL', 'elapsed_s': round(elapsed, 1)}
    except Exception as e:
        print(f"  ERROR: {e}")
        return {'status': 'ERROR', 'elapsed_s': 0}


def main():
    parser = argparse.ArgumentParser(description='Poly-Trader Parallel Heartbeat Runner v6')
    parser.add_argument('--hb', type=int, required=True, help='Heartbeat number')
    parser.add_argument('--fast', action='store_true', help='Fast mode: only DB counts + IC')
    parser.add_argument('--no-train', action='store_true', help='Skip model training')
    parser.add_argument('--no-dw', action='store_true', help='Skip dynamic window')
    parser.add_argument('--no-tests', action='store_true', help='Skip comprehensive tests')
    parser.add_argument('--workers', type=int, default=5, help='Max parallel workers')
    args = parser.parse_args()

    hb_num = args.hb
    print(f"\n{'=' * 60}")
    print(f" 💓 Poly-Trader 平行心跳 #{hb_num}")
    print(f"{'=' * 60}\n")

    # Step 0: Quick DB counts (serial, fast)
    step0_time = quick_db_counts()

    # Build task list
    tasks = list(ALWAYS_TASKS)
    if not args.fast and not args.no_dw:
        tasks.append(OPTIONAL_TASKS['dynamic_window'])
    if not args.fast and not args.no_train:
        tasks.append(OPTIONAL_TASKS['train'])
    if not args.fast and not args.no_tests:
        tasks.append(OPTIONAL_TASKS['tests'])

    # Parallel execution
    results, parallel_time = parallel_run(tasks, hb_num, max_workers=args.workers)

    # Step after parallel: Live market data (serial)
    live_result = None
    if not args.fast:
        live_result = run_live_market_data()

    # Summary
    total_elapsed = step0_time + parallel_time
    passed = sum(1 for r in results.values() if r['status'] == 'PASS')
    failed = sum(1 for r in results.values() if r['status'] in ('FAIL', 'ERROR', 'TIMEOUT'))

    print(f"\n{'=' * 60}")
    print(f" ✅ 心跳 #{hb_num} 完成!")
    print(f"{'=' * 60}")
    print(f"  總時間: {total_elapsed:.1f}s")
    print(f"  任務: {passed} 通過, {failed} 失敗 / {len(results)}")
    if live_result:
        status_icon = {"PASS": "✅", "FAIL": "❌", "ERROR": "💥"}
        print(f"  市場數據: {status_icon.get(live_result['status'], '?')} ({live_result['elapsed_s']:.1f}s)")
    print(f"{'=' * 60}\n")

    # Save summary JSON
    summary = {
        'heartbeat': hb_num,
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'total_elapsed_s': round(total_elapsed, 1),
        'passed': passed,
        'failed': failed,
        'total': len(results),
        'results': {
            name: {
                'status': r['status'],
                'elapsed_s': r.get('elapsed_s', 0),
            }
            for name, r in results.items()
        },
    }
    if live_result:
        summary['live_market'] = live_result

    # Extract key metrics from results for easy access
    for name, r in results.items():
        if name == 'full_ic':
            # Parse Global IC pass count from stdout
            for line in r.get('stdout', '').split('\n'):
                if 'Global IC:' in line and 'pass' in line.lower():
                    summary['global_ic_pass'] = line.strip()
                if 'TW-IC' in line and 'pass' in line.lower():
                    summary['tw_ic'] = line.strip()
        elif name == 'model_train':
            for line in r.get('stdout', '').split('\n'):
                if 'Train=' in line or 'train=' in line.lower():
                    summary['model_train'] = line.strip()
                    break
    save_dir = os.path.join(PROJECT_ROOT, 'data')
    os.makedirs(save_dir, exist_ok=True)
    summary_path = os.path.join(save_dir, f'heartbeat_{hb_num}_summary.json')
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"💾 Summary saved to {summary_path}")


if __name__ == '__main__':
    main()
