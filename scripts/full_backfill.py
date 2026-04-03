#!/usr/bin/env python
"""Run full backfill of all features using the rolling window method."""
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
    print(f"  Full Feature Backfill [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Load raw market data
    cur.execute('''SELECT timestamp, close_price, volume, funding_rate, 
                   fear_greed_index, stablecoin_mcap, polymarket_prob,
                   eye_dist, ear_prob, tongue_sentiment, volatility, oi_roc, body_label
            FROM raw_market_data ORDER BY timestamp ASC''')
    cols = ['timestamp', 'close_price', 'volume', 'funding_rate', 
            'fear_greed_index', 'stablecoin_mcap', 'polymarket_prob',
            'eye_dist', 'ear_prob', 'tongue_sentiment', 'volatility', 'oi_roc', 'body_label']
    rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=cols)
    
    # Convert types
    for col in ['close_price', 'volume', 'funding_rate', 'eye_dist', 'ear_prob', 
                'tongue_sentiment', 'volatility', 'oi_roc']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    print(f"[1] Raw data loaded: {len(df)} rows")
    
    # Compute features using rolling window
    close = df['close_price'].astype(float)
    returns = close.pct_change()
    vol_col = df['volume']
    fr_col = df['funding_rate']
    
    feat_eye = []
    feat_ear = []
    feat_nose = []
    feat_tongue = []
    feat_body = []
    feat_pulse = []
    feat_aura = []
    feat_mind = []
    
    n = len(df)
    window = 336  # max lookback
    
    for i in range(n):
        start = max(0, i - window + 1)
        win = df.iloc[start:i+1]
        win_close = close.iloc[start:i+1].dropna().astype(float)
        win_returns = win_close.pct_change() if len(win_close) > 1 else pd.Series()
        win_vol = vol_col.iloc[start:i+1].dropna() if 'volume' in win.columns else pd.Series()
        win_fr = fr_col.iloc[start:i+1].dropna() if 'funding_rate' in win.columns else pd.Series()
        
        if len(win) < 10:
            feat_eye.append(0.0)
            feat_ear.append(0.0)
            feat_nose.append(0.5)
            feat_tongue.append(1.0)
            feat_body.append(0.0)
            feat_pulse.append(0.5)
            feat_aura.append(0.0)
            feat_mind.append(0.0)
            continue
        
        # Eye: fr_cumsum_48 (funding rate cumulative sum over 48h)
        if len(win_fr) >= 48:
            feat_eye.append(float(win_fr.iloc[-48:].sum()))
        elif len(win_fr) >= 8:
            feat_eye.append(float(win_fr.sum()))
        else:
            feat_eye.append(0.0)
        
        # Ear: mom_24 (momentum 24h)
        if len(win_close) >= 25:
            c24 = float(win_close.iloc[-25])
            if c24 > 0:
                feat_ear.append(float(win_close.iloc[-1] / c24 - 1))
            else:
                feat_ear.append(0.0)
        elif len(win_close) >= 13:
            c12 = float(win_close.iloc[-13])
            if c12 > 0:
                feat_ear.append(float(win_close.iloc[-1] / c12 - 1))
            else:
                feat_ear.append(0.0)
        else:
            feat_ear.append(0.0)
        
        # Nose: rsi14 normalized
        if len(win_close) >= 15:
            delta = win_close.diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            last_loss = float(loss.iloc[-1]) if not loss.empty else 1e-9
            last_gain = float(gain.iloc[-1]) if not gain.empty else 0.0
            if last_loss <= 0:
                rsi = 100.0
            else:
                rsi = 100 - 100 / (1 + last_gain / last_loss)
            feat_nose.append(float(rsi) / 100.0)
        else:
            feat_nose.append(0.5)
        
        # Tongue: vol_ratio_24_144
        if len(win_returns) >= 144:
            vol24 = float(win_returns.iloc[-24:].std())
            vol144 = float(win_returns.iloc[-144:].std())
            feat_tongue.append(float(vol24 / (vol144 + 1e-10)))
        elif len(win_returns) >= 24:
            vol_short = float(win_returns.iloc[-12:].std())
            vol_long = float(win_returns.std())
            feat_tongue.append(float(vol_short / (vol_long + 1e-10)))
        else:
            feat_tongue.append(1.0)
        
        # Body: vol_zscore_48 (volume z-score over 48h window vs history)
        if len(win) >= 48:
            vol48 = float(win_returns.iloc[-48:].std()) if len(win_returns) >= 48 else float(returns.iloc[max(0,i-48):i+1].dropna().std())
            vol_all = float(win_returns.dropna().std()) if len(win_returns.dropna()) > 1 else 1e-9
            rolling_std = returns.iloc[max(0,i-96):i+1].dropna().rolling(48).std().dropna()
            vol_std = float(rolling_std.std()) if len(rolling_std) > 1 else 1e-9
            if vol_std < 1e-12:
                vol_std = 1e-9
            feat_body.append(float((vol48 - vol_all) / vol_std))
        else:
            feat_body.append(0.0)
        
        # Pulse: vol_spike12 (volume spike detection)
        if len(win_vol) >= 12:
            vol_win = win_vol.iloc[-12:].values
            mean_v = float(np.nanmean(vol_win[:-1]))
            std_v = float(np.nanstd(vol_win[:-1]) + 1e-10)
            vol_z = (float(vol_win[-1]) - mean_v) / std_v
            feat_pulse.append(float(1 / (1 + math.exp(-vol_z / 2))))
        elif len(win_vol) >= 3:
            mean_v = float(np.nanmean(win_vol.iloc[:-1]))
            std_v = float(np.nanstd(win_vol.iloc[:-1]) + 1e-10)
            vol_z = (float(win_vol.iloc[-1]) - mean_v) / std_v
            feat_pulse.append(float(1 / (1 + math.exp(-vol_z / 2))))
        else:
            feat_pulse.append(0.5)
        
        # Aura: fr_abs_norm (funding rate absolute normalized)
        if len(win_fr) >= 2:
            fr_abs = float(abs(win_fr.iloc[-1]))
            roll_len = min(96, len(win_fr))
            fr_max = float(win_fr.abs().rolling(roll_len).max().iloc[-1]) + 1e-10
            feat_aura.append(float(fr_abs / fr_max))
        else:
            feat_aura.append(0.0)
        
        # Mind: ret_144 (144h return)
        if len(win_close) >= 145:
            feat_mind.append(float(win_close.iloc[-1] / win_close.iloc[-145] - 1))
        elif len(win_close) >= 25:
            feat_mind.append(float(win_close.iloc[-1] / win_close.iloc[-25] - 1))
        else:
            feat_mind.append(0.0)
        
        if (i + 1) % 1000 == 0:
            print(f"  Progress: {i+1}/{n} ({(i+1)/n*100:.0f}%)", end='\r')
    
    print(f"\n[2] Features computed for {n} rows")
    
    # Stats on features
    for name, arr in [('Eye', feat_eye), ('Ear', feat_ear), ('Nose', feat_nose),
                       ('Tongue', feat_tongue), ('Body', feat_body), ('Pulse', feat_pulse),
                       ('Aura', feat_aura), ('Mind', feat_mind)]:
        a = np.array(arr, dtype=float)
        print(f"  {name}: mean={np.nanmean(a):.4f}, std={np.nanstd(a):.4f}, min={np.nanmin(a):.4f}, max={np.nanmax(a):.4f}, unique={len(np.unique(a))}")
    
    # Update features_normalized table
    print(f"\n[3] Updating database...")
    
    # Delete existing features and re-insert
    cur.execute('DELETE FROM features_normalized')
    conn.commit()
    print("  Cleared existing features")
    
    # Insert new features
    for i in range(n):
        ts = rows[i][0]
        close_p = rows[i][1]
        cur.execute('''INSERT INTO features_normalized 
            (timestamp, symbol, feat_eye, feat_ear, feat_nose, feat_tongue, 
             feat_body, feat_pulse, feat_aura, feat_mind,
             feat_whisper, feat_tone, feat_chorus, feat_hype, feat_oracle, 
             feat_shock, feat_tide, feat_storm, regime_label, feature_version)
            VALUES (?, 'BTCUSDT', ?, ?, ?, ?, ?, ?, ?, ?,
                    0, 0, 0, 0, 0, 0, 0, 0, 'neutral', 'v5')''',
            (ts, feat_eye[i], feat_ear[i], feat_nose[i], feat_tongue[i],
             feat_body[i], feat_pulse[i], feat_aura[i], feat_mind[i]))
        
        if (i + 1) % 500 == 0:
            conn.commit()
            print(f"  DB insert: {i+1}/{n}", end='\r')
    
    conn.commit()
    cur.execute('SELECT COUNT(*) FROM features_normalized')
    count = cur.fetchone()[0]
    print(f"\n  Features in DB: {count}")
    
    conn.close()
    print(f"\n{'='*60}")
    print(f"  Backfill complete!")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
