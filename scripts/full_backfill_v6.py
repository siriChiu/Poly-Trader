#!/usr/bin/env python
"""Full Feature Backfill v6 — uses AVAILABLE data, not NULL columns.

Key fixes:
- Eye: uses eye_dist column (99.6% populated) instead of funding_rate (0.1%)
- Pulse: uses price volatility as proxy when volume is NULL
- Aura: uses |funding_rate| when available, else 0
- Body: uses price returns std, not just volume
- All features computed from columns that actually have data
"""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
import math
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'poly_trader.db')

def main():
    print("=" * 60)
    print(f"  Full Feature Backfill v6 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute('''SELECT timestamp, close_price, volume, funding_rate, 
                   fear_greed_index, stablecoin_mcap, polymarket_prob,
                   eye_dist, ear_prob, tongue_sentiment, volatility, oi_roc, body_label
            FROM raw_market_data ORDER BY timestamp ASC''')
    cols = ['timestamp', 'close_price', 'volume', 'funding_rate', 
            'fear_greed_index', 'stablecoin_mcap', 'polymarket_prob',
            'eye_dist', 'ear_prob', 'tongue_sentiment', 'volatility', 'oi_roc', 'body_label']
    rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=cols)
    
    for col_n in ['close_price', 'volume', 'funding_rate', 'eye_dist', 'ear_prob', 
                'tongue_sentiment', 'volatility', 'oi_roc']:
        df[col_n] = pd.to_numeric(df[col_n], errors='coerce')
    
    print(f"[1] Raw data loaded: {len(df)} rows")
    
    close = df['close_price'].astype(float)
    returns = close.pct_change()
    
    n = len(df)
    window = 336  # max lookback
    
    feat_eye = []
    feat_ear = []
    feat_nose = []
    feat_tongue = []
    feat_body = []
    feat_pulse = []
    feat_aura = []
    feat_mind = []
    
    for i in range(n):
        start = max(0, i - window + 1)
        win_close = close.iloc[start:i+1].dropna()
        win_returns = win_close.pct_change() if len(win_close) > 1 else pd.Series(dtype=float)
        
        if len(win_close) < 10:
            feat_eye.append(0.0)
            feat_ear.append(0.0)
            feat_nose.append(0.5)
            feat_tongue.append(1.0)
            feat_body.append(0.0)
            feat_pulse.append(0.5)
            feat_aura.append(0.0)
            feat_mind.append(0.0)
            continue
        
        # ===== Eye: use eye_dist column (99.6% populated) =====
        # Cumulative eye_dist over 48h window, or shorter if less history
        eye_vals = df['eye_dist'].iloc[start:i+1].dropna()
        if len(eye_vals) >= 48:
            feat_eye.append(float(eye_vals.iloc[-48:].sum()))
        elif len(eye_vals) >= 8:
            feat_eye.append(float(eye_vals.iloc[-8:].sum()))
        elif len(eye_vals) > 0:
            feat_eye.append(float(eye_vals.sum()))
        else:
            feat_eye.append(0.0)
        
        # ===== Ear: mom_24 (momentum 24h) =====
        if len(win_close) >= 25:
            c24 = float(win_close.iloc[-25])
            feat_ear.append(float(win_close.iloc[-1] / c24 - 1) if c24 > 0 else 0.0)
        elif len(win_close) >= 13:
            c12 = float(win_close.iloc[-13])
            feat_ear.append(float(win_close.iloc[-1] / c12 - 1) if c12 > 0 else 0.0)
        else:
            feat_ear.append(0.0)
        
        # ===== Nose: RSI14 normalized =====
        if len(win_close) >= 15:
            delta = win_close.diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            last_loss = float(loss.iloc[-1]) if len(loss) > 0 else 1e-9
            last_gain = float(gain.iloc[-1]) if len(gain) > 0 else 0.0
            rsi = 100.0 if last_loss <= 1e-12 else 100 - 100 / (1 + last_gain / last_loss)
            feat_nose.append(float(rsi) / 100.0)
        else:
            feat_nose.append(0.5)
        
        # ===== Tongue: vol_ratio returns 24/144 =====
        if len(win_returns) >= 144:
            r144 = win_returns.dropna()
            vol144 = float(r144.std()) if len(r144) > 1 else 1e-10
            vol144 = max(vol144, 1e-10)
            r24 = win_returns.iloc[-24:].dropna()
            vol24 = float(r24.std()) if len(r24) > 1 else 0.0
            feat_tongue.append(float(vol24 / vol144))
        elif len(win_returns) >= 24:
            r12 = win_returns.iloc[-12:].dropna()
            rall = win_returns.dropna()
            vol_short = float(r12.std()) if len(r12) > 1 else 0.0
            vol_long = float(rall.std()) if len(rall) > 1 else 1e-10
            feat_tongue.append(float(vol_short / (vol_long + 1e-10)))
        else:
            feat_tongue.append(1.0)
        
        # ===== Body: returns vol z-score over 48h vs trailing window =====
        if len(win_returns) >= 48:
            all_valid = win_returns.dropna()
            if len(all_valid) >= 48:
                vol48 = float(all_valid.iloc[-48:].std())
            else:
                vol48 = float(all_valid.std()) + 0.01
            vol_all = float(all_valid.std()) if len(all_valid) > 1 else 1e-9
            # Rolling std of std
            rolling_vol = all_valid.rolling(48).std().dropna()
            if len(rolling_vol) > 5 and float(rolling_vol.std()) > 1e-12:
                feat_body.append(float((vol48 - vol_all) / float(rolling_vol.std())))
            else:
                feat_body.append(0.0)
        else:
            feat_body.append(0.0)
        
        # ===== Pulse: price volatility spike (when volume is NULL) =====
        # Uses 12h return volatility vs mean
        if len(win_returns) >= 12:
            v12 = win_returns.iloc[-12:].dropna()
            if len(v12) >= 4:
                vol_short = float(v12.std()) + 1e-10
                vol_mean = float(win_returns.dropna().rolling(12).std().mean())
                vol_overall = float(win_returns.dropna().std()) + 1e-10
                spike_ratio = vol_short / (vol_overall + 1e-10)
                # Sigmoid transform
                feat_pulse.append(float(1 / (1 + math.exp(-(spike_ratio - 1.0) * 3))))
            else:
                feat_pulse.append(0.5)
        elif len(win_returns) >= 3:
            vol_now = float(win_returns.dropna().std()) + 1e-10
            feat_pulse.append(float(1 / (1 + math.exp(-(vol_now - 0.01) * 100))))
        else:
            feat_pulse.append(0.5)
        
        # ===== Aura: funding rate absolute (when available) or 0 =====
        fr_vals = df['funding_rate'].iloc[start:i+1].dropna()
        if len(fr_vals) >= 2:
            fr_abs = float(abs(fr_vals.iloc[-1]))
            roll_len = min(96, len(fr_vals))
            fr_max = float(fr_vals.abs().rolling(roll_len).max().iloc[-1]) + 1e-10
            feat_aura.append(float(fr_abs / fr_max))
        else:
            feat_aura.append(0.0)
        
        # ===== Mind: 144h return =====
        if len(win_close) >= 145:
            feat_mind.append(float(win_close.iloc[-1] / win_close.iloc[-145] - 1))
        elif len(win_close) >= 25:
            feat_mind.append(float(win_close.iloc[-1] / win_close.iloc[-25] - 1))
        else:
            feat_mind.append(0.0)
        
        if (i + 1) % 1000 == 0:
            print(f"  Progress: {i+1}/{n} ({(i+1)/n*100:.0f}%)", end='\r')
    
    print(f"\n[2] Features computed for {n} rows")
    
    # Stats
    for name, arr in [('Eye', feat_eye), ('Ear', feat_ear), ('Nose', feat_nose),
                       ('Tongue', feat_tongue), ('Body', feat_body), ('Pulse', feat_pulse),
                       ('Aura', feat_aura), ('Mind', feat_mind)]:
        a = np.array(arr, dtype=float)
        print(f"  {name}: mean={np.nanmean(a):.6f}, std={np.nanstd(a):.6f}, min={np.nanmin(a):.6f}, max={np.nanmax(a):.6f}, unique={len(np.unique(a))}")
    
    # Update DB
    print(f"\n[3] Updating database...")
    cur.execute('DELETE FROM features_normalized')
    conn.commit()
    
    for i in range(n):
        ts = rows[i][0]
        cur.execute('''INSERT INTO features_normalized 
            (timestamp, symbol, feat_eye, feat_ear, feat_nose, feat_tongue, 
             feat_body, feat_pulse, feat_aura, feat_mind,
             feat_whisper, feat_tone, feat_chorus, feat_hype, feat_oracle, 
             feat_shock, feat_tide, feat_storm, regime_label, feature_version)
            VALUES (?, 'BTCUSDT', ?, ?, ?, ?, ?, ?, ?, ?,
                    0, 0, 0, 0, 0, 0, 0, 0, 'neutral', 'v6')''',
            (ts, feat_eye[i], feat_ear[i], feat_nose[i], feat_tongue[i],
             feat_body[i], feat_pulse[i], feat_aura[i], feat_mind[i]))
        if (i + 1) % 500 == 0:
            conn.commit()
    
    conn.commit()
    cur.execute('SELECT COUNT(*) FROM features_normalized')
    count = cur.fetchone()[0]
    print(f"\n  Features in DB: {count}, version=v6")
    
    conn.close()
    print(f"\n{'='*60}")
    print(f"  Backfill v6 complete!")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
