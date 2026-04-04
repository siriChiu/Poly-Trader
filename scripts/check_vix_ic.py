#!/usr/bin/env python3
"""Check VIX/DXY columns and compute their ICs, then compute dynamic window IC."""
import sys, json
sys.path.insert(0, '/home/kazuha/Poly-Trader')

from sqlalchemy import create_engine, text
import pandas as pd
import numpy as np
from datetime import datetime

DB_PATH = '/home/kazuha/Poly-Trader/poly_trader.db'
engine = create_engine(f'sqlite:///{DB_PATH}')

# Check columns
with engine.connect() as conn:
    result = conn.execute(text('PRAGMA table_info(features_normalized)')).fetchall()
    cols = [r[1] for r in result]
    print('Feature columns:', cols)
    
    # Fetch features + labels
    feat = pd.read_sql('SELECT * FROM features_normalized', engine)
    labs = pd.read_sql('SELECT timestamp, label_up FROM labels', engine)
    
    feat['ts_key'] = pd.to_datetime(feat['timestamp'], format='mixed').dt.floor('s')
    labs['ts_key'] = pd.to_datetime(labs['timestamp'], format='mixed').dt.floor('s')
    data = feat.merge(labs, on='ts_key', suffixes=('', '_label')).sort_values('timestamp')
    
    print(f"\nTotal merged records: {len(data)}")
    
    # VIX/DXY IC
    if 'feat_vix' in cols:
        vix_data = data[['feat_vix', 'label_up']].dropna()
        if len(vix_data) > 10:
            vix_ic = vix_data['feat_vix'].corr(vix_data['label_up'])
            print(f"\nVIX IC (full): {vix_ic:+.4f} (n={len(vix_data)})")
        
        # VIX IC by regime (using feat_mind)
        data['regime'] = 'chop'
        mind = data['feat_mind'].fillna(0)
        p33 = mind.quantile(0.33)
        p67 = mind.quantile(0.67)
        data.loc[mind < p33, 'regime'] = 'bear'
        data.loc[mind > p67, 'regime'] = 'bull'
        
        for reg in ['bear', 'bull', 'chop']:
            rd = data[data['regime'] == reg][['feat_vix', 'label_up']].dropna()
            if len(rd) > 10:
                ric = rd['feat_vix'].corr(rd['label_up'])
                print(f"  VIX IC ({reg}): {ric:+.4f} (n={len(rd)})")
    
    if 'feat_dxy' in cols:
        dxy_data = data[['feat_dxy', 'label_up']].dropna()
        if len(dxy_data) > 10:
            dxy_ic = dxy_data['feat_dxy'].corr(dxy_data['label_up'])
            print(f"DXY IC (full): {dxy_ic:+.4f} (n={len(dxy_data)})")
    
    # VIX cross features
    vix_cross_feats = [c for c in cols if c.startswith('feat_vix_x')]
    if vix_cross_feats:
        print(f"\nVIX cross features: {vix_cross_feats}")
        for vf in vix_cross_feats:
            vdata = data[[vf, 'label_up']].dropna()
            if len(vdata) > 10:
                vic = vdata[vf].corr(vdata['label_up'])
                print(f"  {vf}: IC={vic:+.4f}")

    # Latest BTC price and market data
    r = conn.execute(text('SELECT btc_close, feat_vix, feat_dxy, timestamp FROM raw_market_data ORDER BY timestamp DESC LIMIT 1')).fetchall()
    if r:
        print(f"\nLatest BTC: ${r[0][0]:.2f}")
        if r[0][1]: print(f"Latest VIX feat: {r[0][1]:.4f}")
        if r[0][2]: print(f"Latest DXY feat: {r[0][2]:.4f}")
        
    # Label stats
    label_pos = data['label_up'].sum()
    label_pct = label_pos / len(data) * 100
    print(f"\nLabel balance: {len(data)} total, {label_pos} pos ({label_pct:.1f}%)")
    
    # Feature counts
    print(f"\nFeatures: {len(feat)} rows, {len(cols)} columns")
    print(f"Labels: {len(labs)} rows")
    
    # Save summary
    summary = {
        'timestamp': datetime.now().isoformat(),
        'n_records': len(data),
        'n_features': len(cols),
        'n_labels': len(labs),
        'label_balance_pct': round(label_pct, 1),
        'features_count': len(feat),
    }
    with open('/home/kazuha/Poly-Trader/data/ic_heartbeat_latest.json', 'w') as f:
        json.dump(summary, f, indent=2)
    print("\nSummary saved to data/ic_heartbeat_latest.json")
