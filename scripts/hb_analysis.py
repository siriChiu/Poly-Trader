#!/usr/bin/env python
"""Heartbeat Step 2: Data inspection and sensory IC analysis."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'senses'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import sqlite3
import numpy as np
from scipy.stats import spearmanr

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'poly_trader.db')

def main():
    print("=== Step 2: Sensory IC Analysis ===\n")
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Raw market data stats
    cur.execute('SELECT COUNT(*), MIN(timestamp), MAX(timestamp), MIN(close_price), MAX(close_price) FROM raw_market_data')
    row = cur.fetchone()
    print(f"=== Raw Market Data ===")
    print(f"Count: {row[0]}")
    print(f"Timestamp range: {row[1]} / {row[2]}")
    print(f"Price range: ${row[3]:.2f} / ${row[4]:.2f}")
    
    # Check recent data
    cur.execute('SELECT COUNT(*) FROM raw_market_data WHERE timestamp >= datetime("now", "-48 hours")')
    recent48 = cur.fetchone()[0]
    print(f"Recent (48h): {recent48} rows")
    
    cur.execute('SELECT COUNT(*) FROM raw_market_data WHERE timestamp >= datetime("now", "-4 hours")')
    recent4 = cur.fetchone()[0]
    print(f"Very recent (4h): {recent4} rows")
    
    # Latest price
    cur.execute('SELECT close_price, timestamp FROM raw_market_data ORDER BY timestamp DESC LIMIT 1')
    latest = cur.fetchone()
    print(f"Latest: ${latest[0]:.2f} at {latest[1]}")
    
    # Features
    cur.execute('SELECT COUNT(*) FROM features_normalized')
    feature_count = cur.fetchone()[0]
    print(f"\n=== Features: {feature_count} rows ===")
    
    # Get feature column names
    cur.execute('PRAGMA table_info(features_normalized)')
    feature_cols = [r[1] for r in cur.fetchall()]
    print(f"Columns: {feature_cols}")
    
    # Labels
    cur.execute('SELECT COUNT(*), SUM(CASE WHEN label_up=1 THEN 1 ELSE 0 END), SUM(CASE WHEN label_up=0 THEN 1 ELSE 0 END), SUM(CASE WHEN label_spot_long_win=1 THEN 1 ELSE 0 END), SUM(CASE WHEN label_spot_long_win=0 THEN 1 ELSE 0 END) FROM labels')
    lrow = cur.fetchone()
    print(f"\n=== Labels ===")
    print(f"Total: {lrow[0]} | label_up=1: {lrow[1]} | label_up=0: {lrow[2]}")
    print(f"label_spot_long_win=1: {lrow[3]} | label_spot_long_win=0: {lrow[4]}")
    
    # Sensory IC calculation  
    print(f"\n=== Sensory IC Calculation (recent window) ===")
    
    # Join features with labels - use the feature columns directly
    query = """
        SELECT f.timestamp, f.feat_eye, f.feat_ear, f.feat_nose, 
               f.feat_tongue, f.feat_body, f.feat_pulse, f.feat_aura, f.feat_mind,
               l.label_up, l.label_spot_long_win
        FROM features_normalized f
        JOIN labels l ON l.timestamp = f.timestamp
        ORDER BY f.timestamp DESC
        LIMIT 5000
    """
    cur.execute(query)
    rows = cur.fetchall()
    
    if not rows:
        print("ERROR: No joined data. Trying nearest-match...")
        # Nearest match approach
        cur.execute('SELECT timestamp, feat_eye, feat_ear, feat_nose, feat_tongue, feat_body, feat_pulse, feat_aura, feat_mind FROM features_normalized ORDER BY timestamp DESC LIMIT 5000')
        feat_rows = cur.fetchall()
        
        if feat_rows:
            print(f"Got {len(feat_rows)} feature rows, finding nearest labels...")
            rows = []
            for fr in feat_rows:
                fts = fr[0]
                cur.execute('SELECT label_up, label_spot_long_win FROM labels ORDER BY ABS(julianday(timestamp) - julianday(?)) LIMIT 1', (fts,))
                lr = cur.fetchone()
                if lr:
                    rows.append(fr + lr)
    
    if not rows:
        print("ERROR: Cannot join features with labels!")
        conn.close()
        return
    
    print(f"Joined rows: {len(rows)}")
    
    label_col_idx = 9  # label_up is the 10th column (index 9)
    
    # Feature mapping: sense name -> index in row
    sense_cols = {
        'Eye': 1, 'Ear': 2, 'Nose': 3, 'Tongue': 4,
        'Body': 5, 'Pulse': 6, 'Aura': 7, 'Mind': 8
    }
    
    ic_results = {}
    for sense, idx in sense_cols.items():
        values = [r[idx] for r in rows]
        labels = [r[label_col_idx] for r in rows]
        
        # Remove None/NaN
        valid = [(float(v), int(l)) for v, l in zip(values, labels) if v is not None and l is not None]
        if len(valid) < 100:
            print(f"  {sense}: INSUFFICIENT DATA (only {len(valid)} valid pairs)")
            ic_results[sense] = {'ic': 'NaN', 'std': 'N/A', 'valid_count': len(valid)}
            continue
        
        feats_arr = np.array([v for v, l in valid])
        labs_arr = np.array([l for v, l in valid])
        
        std_val = float(np.std(feats_arr))
        unique_count = int(len(np.unique(feats_arr)))
        
        try:
            ic, pval = spearmanr(feats_arr, labs_arr)
            if np.isnan(ic):
                ic_str = 'NaN'
            else:
                ic_str = f"{ic:+.4f} (p={pval:.4f})"
            ic_val = float(ic) if not np.isnan(ic) else None
        except Exception as e:
            ic_str = f'Error: {e}'
            ic_val = None
        
        status = 'FAIL' if (ic_val is not None and abs(ic_val) < 0.05) else ('OK' if ic_val is not None else 'NO_DATA')
        print(f"  {sense}: IC={ic_str}, std={std_val:.4f}, unique={unique_count}, valid={len(valid)} [{status}]")
        ic_results[sense] = {
            'ic': round(ic_val, 4) if ic_val is not None else 'NaN',
            'std': round(std_val, 4),
            'unique_count': unique_count,
            'valid_count': len(valid),
            'status': status
        }
    
    # Derivatives data from raw_market_data
    print(f"\n=== Market Context ===")
    cur.execute('SELECT funding_rate, fear_greed_index, polymarket_prob FROM raw_market_data ORDER BY timestamp DESC LIMIT 1')
    mkt = cur.fetchone()
    if mkt:
        print(f"Funding Rate: {mkt[0]}")
        print(f"Fear & Greed Index: {mkt[1]}")
        print(f"Polymarket Prob: {mkt[2]}")
    
    conn.close()
    
    # Save results
    output = {
        'timestamp': '2026-04-04T04:30:00Z',
        'raw_count': row[0],
        'feature_count': feature_count,
        'label_count': lrow[0],
        'label_pos': int(lrow[1]) if lrow[1] else 0,
        'label_neg': int(lrow[2]) if lrow[2] else 0,
        'latest_price': latest[0] if latest else None,
        'fng': mkt[1] if mkt else None,
        'funding_rate': mkt[0] if mkt else None,
        'polymarket_prob': mkt[2] if mkt else None,
        'ics': ic_results
    }
    
    with open(os.path.join(os.path.dirname(__file__), '..', 'data', 'ic_signs.json'), 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nIC results saved to data/ic_signs.json")

if __name__ == '__main__':
    main()
