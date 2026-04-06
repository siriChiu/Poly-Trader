#!/usr/bin/env python3
"""Parallel Heartbeat Runner — spawns IC, regime IC, dynamic window, training, and tests concurrently."""
import json, os, sys, time, sqlite3, subprocess, argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone

PROJECT = '/home/kazuha/Poly-Trader'
DB_PATH = f'{PROJECT}/poly_trader.db'

def quick_counts():
    """Fast DB counts — runs serially first."""
    conn = sqlite3.connect(DB_PATH)
    counts = {}
    for table in ['raw_market_data', 'features_normalized', 'labels']:
        try:
            c = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
            counts[table] = c
        except Exception as e:
            counts[table] = f'ERROR:{e}'

    try:
        latest_raw = conn.execute('SELECT MAX(timestamp) FROM raw_market_data').fetchone()[0]
        latest_label = conn.execute('SELECT MAX(timestamp) FROM labels').fetchone()[0]
        counts['latest_raw'] = latest_raw
        counts['latest_label'] = latest_label

        sell_win_row = conn.execute(
            'SELECT COUNT(*) as total, SUM(CAST(label_sell_win AS FLOAT)) as wins '
            'FROM labels WHERE label_sell_win IS NOT NULL'
        ).fetchone()
        if sell_win_row and sell_win_row[0] > 0:
            counts['sell_win_rate'] = round(sell_win_row[1] / sell_win_row[0], 4)
    except Exception as e:
        counts['latest_raw'] = f'ERR:{e}'
        counts['latest_label'] = f'ERR:{e}'

    conn.close()
    return counts


def _run_script(script_rel_path, name):
    """Run a single script via subprocess, capture output."""
    full_path = os.path.join(PROJECT, script_rel_path)
    if not os.path.exists(full_path):
        return {'name': name, 'status': 'SKIP', 'script': script_rel_path,
                'stdout': '', 'stderr': f'Script not found: {full_path}', 'returncode': None}

    try:
        env = os.environ.copy()
        env['PYTHONPATH'] = PROJECT
        result = subprocess.run(
            [os.path.join(PROJECT, 'venv', 'bin', 'python'), full_path],
            capture_output=True, text=True, timeout=300,
            cwd=PROJECT, env=env
        )
        return {
            'name': name, 'status': 'PASS' if result.returncode == 0 else 'FAIL',
            'script': script_rel_path, 'stdout': result.stdout[-3000:],
            'stderr': result.stderr[-2000:] if result.returncode != 0 else '',
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {'name': name, 'status': 'TIMEOUT', 'script': script_rel_path,
                'stdout': '', 'stderr': 'Script timed out after 300s', 'returncode': -1}
    except Exception as e:
        return {'name': name, 'status': 'ERROR', 'script': script_rel_path,
                'stdout': '', 'stderr': str(e), 'returncode': -1}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--hb', type=int, required=True, help='Heartbeat number')
    parser.add_argument('--fast', action='store_true', help='Fast mode: counts + IC only')
    parser.add_argument('--no-train', action='store_true', help='Skip model training')
    parser.add_argument('--no-dw', action='store_true', help='Skip dynamic window')
    args = parser.parse_args()

    print(f"{'='*70}")
    print(f"🔁 Poly-Trader Heartbeat #{args.hb} — Parallel Runner")
    print(f"⏰ Started: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{'='*70}")

    # Step 0: Quick DB counts
    print("\n📊 Step 0: Quick DB counts...")
    counts = quick_counts()
    for k, v in counts.items():
        print(f"  {k}: {v}")

    if args.fast:
        print("\n⚡ Fast mode — skipping parallel scripts")
        # Just run full_ic.py serially
        result = _run_script('scripts/full_ic.py', 'full_ic')
        results = [result]
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return

    # Parallel execution
    tasks = [
        ('scripts/full_ic.py', 'full_ic'),
    ]

    if not args.no_train:
        tasks.append(('model/train.py', 'train'))

    tasks.append(('tests/comprehensive_test.py', 'tests'))

    # regime_aware_ic and dynamic_window if they exist
    for sp, nm in [
        ('scripts/regime_aware_ic.py', 'regime_ic'),
        ('scripts/dynamic_window_train.py', 'dynamic_window'),
    ]:
        if os.path.exists(os.path.join(PROJECT, sp)):
            tasks.append((sp, nm))

    print(f"\n🚀 Step 1: Running {len(tasks)} tasks in parallel...")
    for sp, nm in tasks:
        print(f"  ▶ {nm}: {sp}")

    t0 = time.time()
    results = []
    # Use spawn context to avoid importing everything in child
    with ProcessPoolExecutor(max_workers=min(len(tasks), 5)) as executor:
        futures = {}
        for sp, nm in tasks:
            future = executor.submit(_run_script, sp, nm)
            futures[future] = nm

        for future in as_completed(futures):
            nm = futures[future]
            elapsed = time.time() - t0
            try:
                res = future.result()
                res['elapsed_s'] = round(elapsed, 1)
                status_icon = '✅' if res['status'] == 'PASS' else '❌' if res['status'] == 'FAIL' else '⏭️'
                print(f"\n{status_icon} {nm} DONE in {res['elapsed_s']:.1f}s [{res['status']}]")
                if res['stdout']:
                    # Print last 80 chars of stdout
                    lines = res['stdout'].strip().split('\n')
                    for line in lines[-15:]:
                        print(f"    {line}")
                if res['stderr']:
                    print(f"    ⚠️ stderr: {res['stderr'][:300]}")
                results.append(res)
            except Exception as e:
                err_msg = str(e)
                print(f"\n❌ {nm} EXCEPTION: {err_msg}")
                results.append({'name': nm, 'status': 'ERROR', 'error': err_msg, 'elapsed_s': round(elapsed, 1)})

    total_time = time.time() - t0
    pass_count = sum(1 for r in results if r['status'] == 'PASS')
    skip_count = sum(1 for r in results if r['status'] == 'SKIP')
    print(f"\n{'='*70}")
    print(f"⏱️  Total parallel time: {total_time:.1f}s — {pass_count}/{len(results)} PASS")
    print(f"{'='*70}")

    # Save summary
    summary = {
        'heartbeat': args.hb,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'total_elapsed_s': round(total_time, 1),
        'pass_count': pass_count,
        'total_tasks': len(results),
        'counts': counts,
        'results': results,
    }
    os.makedirs(f'{PROJECT}/data', exist_ok=True)
    out_path = f'{PROJECT}/data/heartbeat_{args.hb}_summary.json'
    with open(out_path, 'w') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
    print(f"📁 Summary saved to {out_path}")


if __name__ == '__main__':
    main()
