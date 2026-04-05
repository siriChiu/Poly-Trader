#!/usr/bin/env python3
"""Parallel Heartbeat Runner for Poly-Trader.

Runs all 5 diagnostic scripts concurrently using ProcessPoolExecutor.
"""
import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
import time
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)
os.environ['PYTHONPATH'] = PROJECT_ROOT

# Activate venv: use venv python directly
PYTHON = os.path.join(PROJECT_ROOT, 'venv', 'bin', 'python')

def run_script(name, cmd, timeout=600):
    """Run a single script and return result dict."""
    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=PROJECT_ROOT,
        )
        elapsed = time.time() - start
        return {
            'name': name,
            'exit_code': result.returncode,
            'stdout': result.stdout[-2000:],  # Last 2000 chars
            'stderr': result.stderr[-1000:] if result.stderr else '',
            'elapsed': round(elapsed, 1),
            'status': 'PASS' if result.returncode == 0 else 'FAIL',
        }
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        return {
            'name': name,
            'exit_code': -1,
            'stdout': '',
            'stderr': f'Timeout after {elapsed:.0f}s',
            'elapsed': round(elapsed, 1),
            'status': 'TIMEOUT',
        }
    except Exception as e:
        elapsed = time.time() - start
        return {
            'name': name,
            'exit_code': -1,
            'stdout': '',
            'stderr': str(e),
            'elapsed': round(elapsed, 1),
            'status': 'ERROR',
        }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--hb', type=int, required=True, help='Heartbeat number')
    parser.add_argument('--fast', action='store_true', help='Fast mode: counts + quick IC only')
    parser.add_argument('--no-train', action='store_true', help='Skip model training')
    parser.add_argument('--no-dw', action='store_true', help='Skip dynamic window scan')
    args = parser.parse_args()

    hb = args.hb
    print(f"{'='*60}")
    print(f"  Poly-Trader Parallel Heartbeat #{hb}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    overall_start = time.time()

    # Step 0: Quick DB counts
    print("📊 Step 0: Quick DB counts...")
    counts_script = os.path.join(PROJECT_ROOT, 'scripts', f'hb{hb}_counts.py')
    if os.path.exists(counts_script):
        r = run_script('db_counts', [PYTHON, counts_script], timeout=30)
    else:
        # Inline count check
        import sqlite3
        db = sqlite3.connect(os.path.join(PROJECT_ROOT, 'poly_trader.db'))
        raw = db.execute('SELECT COUNT(*) FROM raw_market_data').fetchone()[0]
        feat = db.execute('SELECT COUNT(*) FROM features_normalized').fetchone()[0]
        labs = db.execute('SELECT COUNT(*) FROM labels').fetchone()[0]
        sw = db.execute('SELECT AVG(CAST(label_sell_win AS FLOAT)) FROM labels WHERE label_sell_win IS NOT NULL').fetchone()[0]
        print(f"  Raw: {raw:,} | Features: {feat:,} | Labels: {labs:,} | sell_win: {sw:.4f}")
        db.close()
        r = {'name': 'db_counts', 'status': 'PASS', 'elapsed': 0}
    print(f"  ✓ DB counts done ({r.get('elapsed', 0):.1f}s)\n")

    if args.fast:
        print("⚡ Fast mode — skipping heavy steps")
        print(f"\n⏱️  Total: {time.time() - overall_start:.1f}s")
        sys.exit(0)

    # Define the 5 parallel tasks
    tasks = [
        ('full_ic', [PYTHON, 'scripts/full_ic.py']),
        ('regime_ic', [PYTHON, 'scripts/regime_aware_ic.py']),
        ('dynamic_window', [PYTHON, 'scripts/dynamic_window_train.py']),
        ('model_train', [PYTHON, 'model/train.py']),
        ('comprehensive_tests', [PYTHON, 'tests/comprehensive_test.py']),
    ]

    if args.no_train:
        tasks = [t for t in tasks if t[0] != 'model_train']
    if args.no_dw:
        tasks = [t for t in tasks if t[0] != 'dynamic_window']

    # Run all tasks in parallel
    print(f"🚀 Spawning {len(tasks)} tasks in parallel...\n")
    results = []

    with concurrent.futures.ProcessPoolExecutor(max_workers=min(len(tasks), 5)) as executor:
        future_map = {}
        for name, cmd in tasks:
            print(f"  ▶ {name}: {' '.join(cmd)}")
            future = executor.submit(run_script, name, cmd)
            future_map[future] = name

        for future in concurrent.futures.as_completed(future_map):
            name = future_map[future]
            try:
                r = future.result()
                results.append(r)
                icon = {'PASS': '✅', 'FAIL': '❌', 'TIMEOUT': '⏰', 'ERROR': '💥'}.get(r['status'], '❓')
                print(f"\n  {icon} {name}: {r['status']} ({r['elapsed']:.1f}s)")
                if r['status'] != 'PASS':
                    if r['stderr']:
                        print(f"     stderr: {r['stderr'][:200]}")
            except Exception as e:
                print(f"\n  💥 {name}: EXCEPTION — {e}")
                results.append({'name': name, 'status': 'ERROR', 'elapsed': 0, 'stderr': str(e)})

    total_elapsed = time.time() - overall_start
    pass_count = sum(1 for r in results if r['status'] == 'PASS')
    fail_count = len(results) - pass_count

    print(f"\n{'='*60}")
    print(f"  Heartbeat #{hb} Summary")
    print(f"  {'='*60}")
    print(f"  ⏱️  Total: {total_elapsed:.1f}s")
    print(f"  ✅ PASS: {pass_count}/{len(results)}")
    if fail_count > 0:
        print(f"  ❌ FAIL: {fail_count}")
        for r in results:
            if r['status'] != 'PASS':
                print(f"     - {r['name']}: {r['status']}")
    print()

    # Print key outputs
    for r in results:
        if r['stdout'].strip():
            # Try to extract key lines
            print(f"\n--- {r['name']} output ---")
            print(r['stdout'][:800])

    # Save summary JSON
    summary = {
        'heartbeat': hb,
        'timestamp': datetime.now().isoformat(),
        'total_seconds': round(total_elapsed, 1),
        'pass': pass_count,
        'total': len(results),
        'results': results,
    }
    summary_path = os.path.join(PROJECT_ROOT, 'data', f'heartbeat_{hb}_summary.json')
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\n📁 Summary saved to {summary_path}")

    sys.exit(0 if fail_count == 0 else 1)

if __name__ == '__main__':
    main()
