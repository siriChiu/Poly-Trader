#!/usr/bin/env python3
"""Heartbeat parallel runner — v1. Runs all diagnostic scripts concurrently."""
import json, os, sys, time, sqlite3, subprocess, argparse, textwrap
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime

PROJECT_ROOT = '/home/kazuha/Poly-Trader'
DB_PATH = f'{PROJECT_ROOT}/poly_trader.db'
PYTHON = f'{PROJECT_ROOT}/venv/bin/python'

SCRIPTS = [
    {'name': 'full_ic',              'script': 'scripts/full_ic.py'},
    {'name': 'regime_aware_ic',      'script': 'scripts/regime_aware_ic.py'},
    {'name': 'dynamic_window_train', 'script': 'scripts/dynamic_window_train.py'},
    {'name': 'model_train',          'script': 'model/train.py'},
    {'name': 'comprehensive_test',   'script': 'tests/comprehensive_test.py'},
]

def db_counts():
    """Quick DB counts — runs serially first (<10s)."""
    conn = sqlite3.connect(DB_PATH)
    counts = {}
    for t in ['raw_market_data', 'features_normalized', 'labels']:
        try:
            c = conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
            counts[t] = c
        except Exception as e:
            counts[t] = f"ERROR: {e}"
    # sell_win rate
    try:
        row = conn.execute(
            'SELECT AVG(CAST(label_sell_win AS FLOAT)), COUNT(*) FROM labels WHERE label_sell_win IS NOT NULL'
        ).fetchone()
        counts['sell_win_rate'] = round(row[0], 4) if row[0] else None
        counts['sell_win_total'] = row[1]
    except Exception:
        counts['sell_win_rate'] = None

    # Recent sell_win (last 500)
    try:
        rows = conn.execute(
            'SELECT label_sell_win FROM labels WHERE label_sell_win IS NOT NULL ORDER BY id DESC LIMIT 500'
        ).fetchall()
        if rows:
            vals = [r[0] for r in rows]
            counts['sell_win_recent_500'] = round(sum(vals) / len(vals), 4)
            # Consecutive loss streak
            streak = 0
            max_streak = 0
            for r in rows[::-1]:
                if r[0] == 0:
                    streak += 1
                    max_streak = max(max_streak, streak)
                else:
                    streak = 0
            counts['sell_loss_streak'] = max_streak
    except Exception:
        pass

    # Timestamps freshness
    try:
        raw_ts = conn.execute('SELECT MAX(timestamp) FROM raw_market_data').fetchone()[0]
        feat_ts = conn.execute('SELECT MAX(timestamp) FROM features_normalized').fetchone()[0]
        label_ts = conn.execute('SELECT MAX(timestamp) FROM labels').fetchone()[0]
        counts['raw_max_ts'] = raw_ts
        counts['feat_max_ts'] = feat_ts
        counts['label_max_ts'] = label_ts
    except Exception:
        pass

    conn.close()
    return counts


def run_script(entry):
    """Run a single script, capture stdout/stderr."""
    name = entry['name']
    script = entry['script']
    script_path = os.path.join(PROJECT_ROOT, script)

    if not os.path.exists(script_path):
        return {'name': name, 'status': 'MISSING', 'stdout': '', 'stderr': f'{script_path} not found'}

    start = time.time()
    try:
        result = subprocess.run(
            [PYTHON, script_path],
            capture_output=True, text=True,
            cwd=PROJECT_ROOT,
            env={**os.environ, 'PYTHONPATH': PROJECT_ROOT},
            timeout=600,
        )
        elapsed = round(time.time() - start, 1)
        return {
            'name': name,
            'status': 'PASS' if result.returncode == 0 else 'FAIL',
            'returncode': result.returncode,
            'stdout': result.stdout[-4000:],  # last 4000 chars
            'stderr': result.stderr[-2000:] if result.stderr else '',
            'elapsed': elapsed,
        }
    except subprocess.TimeoutExpired:
        return {'name': name, 'status': 'TIMEOUT', 'stdout': '', 'stderr': 'Script timed out after 600s', 'elapsed': 600}
    except Exception as e:
        return {'name': name, 'status': 'ERROR', 'stdout': '', 'stderr': str(e), 'elapsed': round(time.time() - start, 1)}


def save_metrics(counts, results, hb_num, total_elapsed):
    """Save metrics to data/hb_metrics.csv."""
    import csv
    metrics_path = os.path.join(PROJECT_ROOT, 'data', 'hb_metrics.csv')
    os.makedirs(os.path.dirname(metrics_path), exist_ok=True)

    fields = ['hb', 'timestamp', 'raw', 'features', 'labels', 'sell_win',
              'losing_streak', 'total_elapsed']
    for s in SCRIPTS:
        fields.append(f"{s['name']}_status")
        fields.append(f"{s['name']}_elapsed")

    row = {
        'hb': hb_num,
        'timestamp': datetime.utcnow().isoformat(),
        'raw': counts.get('raw_market_data', 0),
        'features': counts.get('features_normalized', 0),
        'labels': counts.get('labels', 0),
        'sell_win': counts.get('sell_win_rate', ''),
        'losing_streak': counts.get('sell_loss_streak', ''),
        'total_elapsed': total_elapsed,
    }
    for r in results:
        row[f"{r['name']}_status"] = r['status']
        row[f"{r['name']}_elapsed"] = r.get('elapsed', 0)

    file_exists = os.path.exists(metrics_path)
    with open(metrics_path, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description='Parallel heartbeat runner')
    parser.add_argument('--hb', type=int, required=True, help='Heartbeat number')
    parser.add_argument('--fast', action='store_true', help='Fast mode: counts + quick IC only')
    parser.add_argument('--no-train', action='store_true', help='Skip model training')
    parser.add_argument('--no-dw', action='store_true', help='Skip dynamic window')
    args = parser.parse_args()

    hb_num = args.hb
    print(f"\n{'='*70}")
    print(f"  心跳 #{hb_num} — Parallel Heartbeat Runner v1")
    print(f"  {datetime.utcnow().isoformat()} UTC")
    print(f"{'='*70}\n")

    # Step 0: Quick DB counts (serial)
    print("── Step 0: Database counts ──")
    counts = db_counts()
    for k, v in counts.items():
        print(f"  {k}: {v}")
    print()

    # Filter scripts based on flags
    scripts_to_run = list(SCRIPTS)
    if args.no_train:
        scripts_to_run = [s for s in scripts_to_run if s['name'] != 'model_train']
    if args.no_dw:
        scripts_to_run = [s for s in scripts_to_run if s['name'] != 'dynamic_window_train']
    if args.fast:
        scripts_to_run = [s for s in scripts_to_run if s['name'] in ('full_ic', 'regime_aware_ic')]

    # Step 1: Run all scripts in parallel
    print(f"── Step 1: Running {len(scripts_to_run)} scripts in parallel ──")
    for s in scripts_to_run:
        print(f"  🔨 {s['name']}: {s['script']}")
    print()

    start_all = time.time()
    results = []

    with ProcessPoolExecutor(max_workers=min(len(scripts_to_run), 5)) as executor:
        futures = {executor.submit(run_script, s): s['name'] for s in scripts_to_run}
        for future in as_completed(futures):
            r = future.result()
            status_emoji = '✅' if r['status'] == 'PASS' else '❌'
            print(f"  {status_emoji} {r['name']}: {r['status']} ({r.get('elapsed', '?')}s)")
            results.append(r)

    total_elapsed = round(time.time() - start_all, 1)
    print(f"\n  ⏱️ Total parallel time: {total_elapsed}s")

    # Save metrics
    try:
        save_metrics(counts, results, hb_num, total_elapsed)
    except Exception as e:
        print(f"  ⚠️ Failed to save metrics: {e}")

    # Save summary JSON
    summary = {
        'hb': hb_num,
        'timestamp': datetime.utcnow().isoformat(),
        'db_counts': counts,
        'results': results,
        'total_elapsed': total_elapsed,
    }
    os.makedirs(os.path.join(PROJECT_ROOT, 'data'), exist_ok=True)
    summary_path = os.path.join(PROJECT_ROOT, 'data', f'heartbeat_{hb_num}_summary.json')
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"  📄 Summary saved to data/heartbeat_{hb_num}_summary.json")

    # Print summary table
    print(f"\n{'━'*70}")
    print(f"  心跳 #{hb_num} Summary")
    print(f"{'━'*70}")
    print(f"  Raw: {counts.get('raw_market_data', '?')}")
    print(f"  Features: {counts.get('features_normalized', '?')}")
    print(f"  Labels: {counts.get('labels', '?')}")
    print(f"  sell_win: {counts.get('sell_win_rate', '?')}")
    print(f"  Loss streak: {counts.get('sell_loss_streak', '?')}")
    print()
    for r in results:
        print(f"  {r['name']:25s}: {r['status']:8s} ({r.get('elapsed', '?')}s)")
    print(f"  ⏱️ Wall time: {total_elapsed}s")
    print(f"{'━'*70}\n")


if __name__ == '__main__':
    main()
