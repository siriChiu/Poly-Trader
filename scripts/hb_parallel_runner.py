#!/usr/bin/env python3
"""
hb_parallel_runner.py — Poly-Trader 平行心跳執行器 (v6)

Uses ProcessPoolExecutor to run all diagnostic scripts in parallel:
1. scripts/full_ic.py —全域 IC 分析
2. scripts/regime_aware_ic.py — 分區間 IC
3. scripts/dynamic_window_train.py — 動態窗口掃描
4. model/train.py — XGBoost 模型訓練
5. tests/comprehensive_test.py — 完整測試套件

Usage:
    python scripts/hb_parallel_runner.py --hb N
    python scripts/hb_parallel_runner.py --hb N --fast
    python scripts/hb_parallel_runner.py --hb N --no-train --no-dw
"""

import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

PYTHON = str(PROJECT_ROOT / "venv" / "bin" / "python")
DB_PATH = str(PROJECT_ROOT / "poly_trader.db")


def quick_db_counts():
    """Quick serial DB counts — <10s step 0."""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    result = {}
    for table in ['raw_market_data', 'features_normalized', 'labels']:
        count = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
        result[table] = count
    sw = conn.execute('SELECT AVG(CAST(label_sell_win AS FLOAT)) FROM labels WHERE label_sell_win IS NOT NULL').fetchone()
    result['sell_win'] = round(sw[0], 4) if sw[0] is not None else None
    conn.close()
    return result


def run_script(name, script_path, timeout=300):
    """Run a single script and return (name, success, stdout, stderr, elapsed)."""
    start = time.time()
    try:
        result = subprocess.run(
            [PYTHON, str(script_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(PROJECT_ROOT),
            env={**os.environ, 'PYTHONPATH': str(PROJECT_ROOT)},
        )
        elapsed = time.time() - start
        return {
            'name': name,
            'success': result.returncode == 0,
            'stderr': result.stderr[-2000:] if result.stderr else '',
            'stdout': result.stdout[-2000:] if result.stdout else '',
            'elapsed': round(elapsed, 1),
        }
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        return {'name': name, 'success': False, 'stderr': f'Timeout after {timeout}s', 'stdout': '', 'elapsed': round(elapsed, 1)}
    except Exception as e:
        return {'name': name, 'success': False, 'stderr': str(e), 'stdout': '', 'elapsed': round(time.time() - start, 1)}


def run_heartbeat(hb_num, no_train=False, no_dw=False, fast=False):
    """Main parallel heartbeat execution."""
    overall_start = time.time()
    print(f"\n{'='*60}")
    print(f"🫀 Poly-Trader Heartbeat #{hb_num}")
    print(f"{'='*60}\n")

    # Step 0: Quick serial checks
    print("▶ Step 0: Quick DB counts...")
    counts = quick_db_counts()
    for k, v in counts.items():
        print(f"  {k}: {v}")
    print()

    # Define tasks
    tasks = []

    # Core IC scripts (always run)
    tasks.append(('full_ic', PROJECT_ROOT / 'scripts' / 'full_ic.py'))
    tasks.append(('regime_aware_ic', PROJECT_ROOT / 'scripts' / 'regime_aware_ic.py'))

    if not fast:
        if not no_dw:
            tasks.append(('dynamic_window', PROJECT_ROOT / 'scripts' / 'dynamic_window_train.py'))
        if not no_train:
            tasks.append(('model_train', PROJECT_ROOT / 'model' / 'train.py'))
        tasks.append(('comprehensive_test', PROJECT_ROOT / 'tests' / 'comprehensive_test.py'))

    # Parallel execution
    print(f"▶ Step 1: Parallel execution ({len(tasks)} tasks)...\n")
    results = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(len(tasks), 5)) as executor:
        future_map = {}
        for name, script_path in tasks:
            print(f"  🚀 {name}: {script_path.relative_to(PROJECT_ROOT)}")
            future = executor.submit(run_script, name, script_path)
            future_map[future] = name

        for future in concurrent.futures.as_completed(future_map):
            name = future_map[future]
            try:
                result = future.result()
                results.append(result)
                status = '✅ PASS' if result['success'] else '❌ FAIL'
                print(f"  {status} [{result['elapsed']:.1f}s] {name}")
                if result['stderr'] and not result['success']:
                    print(f"    stderr: {result['stderr'][:200]}")
            except Exception as e:
                results.append({'name': name, 'success': False, 'stderr': str(e), 'elapsed': 0})
                print(f"  ❌ ERROR {name}: {e}")

    total_elapsed = round(time.time() - overall_start, 1)
    passed = sum(1 for r in results if r['success'])
    total = len(results)

    # Summary
    print(f"\n{'='*60}")
    print(f"✅ Heartbeat #{hb_num} Complete: {passed}/{total} passed in {total_elapsed:.1f}s")
    print(f"{'='*60}")

    # Extract key metrics from outputs for summary
    summary = {
        'heartbeat': hb_num,
        'timestamp': datetime.now().isoformat(),
        'db_counts': counts,
        'total_elapsed': total_elapsed,
        'results': results,
        'passed': passed,
        'total': total,
    }

    # Save summary JSON
    summary_dir = PROJECT_ROOT / 'data'
    summary_dir.mkdir(exist_ok=True)
    summary_path = summary_dir / f'heartbeat_{hb_num}_summary.json'
    try:
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        print(f"\n📄 Summary saved: {summary_path}")
    except Exception as e:
        print(f"\n⚠️ Could not save summary: {e}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Poly-Trader Parallel Heartbeat")
    parser.add_argument('--hb', type=int, required=True, help="Heartbeat number")
    parser.add_argument('--fast', action='store_true', help="Fast mode: only IC scripts")
    parser.add_argument('--no-train', action='store_true', help="Skip model training")
    parser.add_argument('--no-dw', action='store_true', help="Skip dynamic window")
    args = parser.parse_args()

    run_heartbeat(args.hb, no_train=args.no_train, no_dw=args.no_dw, fast=args.fast)


if __name__ == '__main__':
    main()
