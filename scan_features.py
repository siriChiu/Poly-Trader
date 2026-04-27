import sqlite3
import pandas as pd
import numpy as np

def main():
    conn = sqlite3.connect('C:/Users/Kazuha/repo/Poly-Trader/poly_trader.db')
    # Get joined data where all raw features exist? We'll just use features_normalized and labels
    query = """
    SELECT 
        f.feat_eye,
        f.feat_ear,
        f.feat_nose,
        f.feat_tongue,
        f.feat_body,
        f.timestamp,
        l.future_return_pct
    FROM features_normalized f
    JOIN labels l ON f.id = l.id
    WHERE f.feat_eye IS NOT NULL 
      AND f.feat_ear IS NOT NULL 
      AND f.feat_nose IS NOT NULL 
      AND f.feat_tongue IS NOT NULL 
      AND f.feat_body IS NOT NULL
      AND l.future_return_pct IS NOT NULL
    """
    df = pd.read_sql_query(query, conn)
    print(f"Rows: {len(df)}")
    if len(df) == 0:
        print("No data")
        return
    # Ensure timestamp datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    future_returns = df['future_return_pct']
    actual_up = future_returns > 0
    # Define candidate features for each sense
    candidates = {
        'eye': [
            ('feat_eye', df['feat_eye']),
            ('return_1', df['close_price'].pct_change(1).shift(-1)),  # placeholder, need close price
        ],
        'ear': [
            ('feat_ear', df['feat_ear']),
            ('mom_12', (df['close_price'] / df['close_price'].shift(12) - 1)),
            ('mom_24', (df['close_price'] / df['close_price'].shift(24) - 1)),
            ('mom_48', (df['close_price'] / df['close_price'].shift(48) - 1)),
            ('vol_zscore_12', (df['close_price'].pct_change().rolling(12).std())),
        ],
        'nose': [
            ('feat_nose', df['feat_nose']),
            ('rsi_14', 100 - 100 / (1 + (df['close_price'].diff().clip(lower=0).rolling(14).mean() / (-df['close_price'].diff().clip(upper=0).rolling(14).mean().abs()+1e-9)))),
            ('cci_20', (df['close_price'] - df['close_price'].rolling(20).mean()) / (0.015 * df['close_price'].rolling(20).std())),
        ],
        'tongue': [
            ('feat_tongue', df['feat_tongue']),
            ('vol_ratio_6_24', (df['close_price'].pct_change().rolling(6).std() / (df['close_price'].pct_change().rolling(24).std() + 1e-10))),
            ('vol_ratio_12_48', (df['close_price'].pct_change().rolling(12).std() / (df['close_price'].pct_change().rolling(48).std() + 1e-10))),
            ('bb_width_20', ((df['close_price'].rolling(20).mean() + 2*df['close_price'].rolling(20).std()) - (df['close_price'].rolling(20).mean() - 2*df['close_price'].rolling(20).std())) / df['close_price'].rolling(20).mean()),
        ],
        'body': [
            ('feat_body', df['feat_body']),
            ('vol_zscore_24', (df['close_price'].pct_change().rolling(24).std() - df['close_price'].pct_change().rolling(24*7).std().rolling(24).mean()) / (df['close_price'].pct_change().rolling(24*7).std().rolling(24).std() + 1e-10)),
            ('atr_14', (df['high'] - df['low']).rolling(14).mean()),  # need high low
        ]
    }
    # We need close price, high, low from raw data. Let's fetch raw market data for the same timestamps.
    # Instead, we can compute features directly from raw data in the same query.
    # Let's do a more comprehensive approach: fetch raw data and compute a set of features.
    # For simplicity, we'll just test a few known candidates from ISSUES.
    # We'll compute IC for each candidate and print.
    # We'll need to align lengths.
    # Let's get raw data for the same time range as features_normalized.
    # We'll join on timestamp.
    raw_query = """
    SELECT 
        r.timestamp,
        r.close_price,
        r.high,
        r.low,
        r.volume,
        r.funding_rate,
        r.fear_greed_index,
        r.eye_dist,
        r.ear_prob,
        r.tongue_sentiment,
        r.volatility,
        r.oi_roc
    FROM raw_market_data r
    WHERE r.symbol = 'BTCUSDT'
    ORDER BY r.timestamp
    """
    raw_df = pd.read_sql_query(raw_query, conn)
    raw_df['timestamp'] = pd.to_datetime(raw_df['timestamp'])
    raw_df = raw_df.set_index('timestamp')
    # Align df to raw_df by timestamp
    df = df.set_index('timestamp')
    # Join
    joined = df.join(raw_df, how='inner')
    print(f"Joined rows: {len(joined)}")
    if len(joined) == 0:
        print("Failed to join")
        return
    future_returns = joined['future_return_pct']
    # Define candidate functions
    def add_candidate(name, series):
        if series is not None and len(series) == len(joined):
            candidates_list.append((name, series))
    
    # We'll test a handful of candidates for each sense based on ISSUES and common sense.
    results = {}
    for sense in ['eye', 'ear', 'nose', 'tongue', 'body']:
        candidates_list = []
        if sense == 'eye':
            # Eye: return over volatility
            returns = joined['close_price'].pct_change()
            # ret_24 / vol_72
            if len(joined) >= 72:
                ret24 = joined['close_price'] / joined['close_price'].shift(24) - 1
                vol72 = returns.rolling(72).std()
                add_candidate('eye_ret24_vol72', ret24 / (vol72 + 1e-10))
            # ret_12 / vol_48
            if len(joined) >= 48:
                ret12 = joined['close_price'] / joined['close_price'].shift(12) - 1
                vol48 = returns.rolling(48).std()
                add_candidate('eye_ret12_vol48', ret12 / (vol48 + 1e-10))
            # eye_dist from raw (already)
            add_candidate('eye_raw_dist', joined['eye_dist'])
            # ear_prob? no
            # tongue_sentiment? no
            # volatility? maybe
            add_candidate('eye_volatility', joined['volatility'])
            # oi_roc
            add_candidate('eye_oi_roc', joined['oi_roc'])
            # funding_rate
            add_candidate('eye_funding_rate', joined['funding_rate'])
            # fear_greed_index
            add_candidate('eye_fear_greed', joined['fear_greed_index'])
            # stablecoin_mcap not in raw_df? we didn't select it. Let's add.
        elif sense == 'ear':
            # Ear: price momentum
            close = joined['close_price']
            for h in [6,12,24,48,96,168]:
                if len(joined) >= h+1:
                    mom = close / close.shift(h) - 1
                    add_candidate(f'ear_mom_{h}', mom)
            # volume momentum
            vol = joined['volume']
            for h in [6,12,24]:
                if len(joined) >= h+1:
                    vol_mom = vol / vol.shift(h) - 1
                    add_candidate(f'ear_vol_mom_{h}', vol_mom)
            # zscore of volume
            if len(joined) >= 24:
                vol_mean = vol.rolling(24).mean()
                vol_std = vol.rolling(24).std()
                add_candidate('ear_vol_zscore_24', (vol - vol_mean) / (vol_std + 1e-10))
            # kdj? skip
        elif sense == 'nose':
            # Nose: RSI, CCI, Stoch
            close = joined['close_price']
            high = joined['high']
            low = joined['low']
            # RSI 14
            delta = close.diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            rsi = 100 - 100 / (1 + gain / (loss + 1e-10))
            add_candidate('nose_rsi_14', rsi / 100.0)  # normalize to 0-1
            # RSI 7
            if len(joined) >= 8:
                gain7 = delta.clip(lower=0).rolling(7).mean()
                loss7 = (-delta.clip(upper=0)).rolling(7).mean()
                rsi7 = 100 - 100 / (1 + gain7 / (loss7 + 1e-10))
                add_candidate('nose_rsi_7', rsi7 / 100.0)
            # CCI 20
            tp = (high + low + close) / 3
            cci20 = (tp - tp.rolling(20).mean()) / (0.015 * tp.rolling(20).std() + 1e-10)
            add_candidate('nose_cci_20', cci20)
            # Williams %R
            willr = (high.rolling(14).max() - close) / (high.rolling(14).max() - low.rolling(14).min() + 1e-10) * -100
            add_candidate('nose_willr_14', willr / 100.0)  # normalize 0-1
            # Stoch K
            lowest_low = low.rolling(14).min()
            highest_high = high.rolling(14).max()
            stoch_k = (close - lowest_low) / (highest_high - lowest_low + 1e-10)
            add_candidate('nose_stoch_k_14', stoch_k)
        elif sense == 'tongue':
            # Tongue: volatility ratio, breakout strength
            returns = joined['close_price'].pct_change()
            for fast in [6,12]:
                for slow in [24,48,96]:
                    if len(joined) >= slow+1:
                        vol_fast = returns.rolling(fast).std()
                        vol_slow = returns.rolling(slow).std()
                        add_candidate(f'tongue_vol_ratio_{fast}_{slow}', vol_fast / (vol_slow + 1e-10))
            # Bollinger Band Width
            if len(joined) >= 20:
                ma20 = close.rolling(20).mean()
                std20 = close.rolling(20).std()
                upper = ma20 + 2*std20
                lower = ma20 - 2*std20
                bbw = (upper - lower) / (ma20 + 1e-10)
                add_candidate('tongue_bbw_20', bbw)
            # Keltner Channel Width
            if len(joined) >= 20:
                ma20 = close.rolling(20).mean()
                atr = (joined['high'] - joined['low']).rolling(14).mean()
                upper = ma20 + 2*atr
                lower = ma20 - 2*at
                kcw = (upper - lower) / (ma20 + 1e-10)
                add_candidate('tongue_kcw_20', kcw)
            # Donchian Channel Width
            if len(joined) >= 20:
                dc_high = high.rolling(20).max()
                dc_low = low.rolling(20).min()
                dcw = (dc_high - dc_low) / (close + 1e-10)
                add_candidate('tongue_dcw_20', dcw)
        elif sense == 'body':
            # Body: volatility regime, trend strength
            returns = joined['close_price'].pct_change()
            # volatility z-score
            if len(joined) >= 48:
                vol48 = returns.rolling(48).std()
                vol_hist_mean = vol48.rolling(288).mean()
                vol_hist_std = vol48.rolling(288).std()
                add_candidate('body_vol_zscore_48', (vol48 - vol_hist_mean) / (vol_hist_std + 1e-10))
            # price change over period
            for h in [6,12,24,48,96]:
                if len(joined) >= h+1:
                    ret = close / close.shift(h) - 1
                    add_candidate(f'body_ret_{h}', ret)
            # volume trend
            vol = joined['volume']
            if len(joined) >= 24:
                vol_ma = vol.rolling(24).mean()
                add_candidate('body_vol_ma_ratio', vol / (vol_ma + 1e-10))
            # volatility of volume
            if len(joined) >= 24:
                vol_of_vol = vol.rolling(24).std()
                add_candidate('body_vol_of_vol_24', vol_of_vol)
        else:
            continue
        # Compute IC for each candidate
        results[sense] = []
        for name, series in candidates_list:
            # Drop NaNs
            mask = ~series.isna() & ~future_returns.isna()
            if mask.sum() < 10:
                continue
            ic = np.corrcoef(series[mask], future_returns[mask])[0,1]
            results[sense].append((name, ic, mask.sum()))
        # Sort by absolute IC descending
        results[sense].sort(key=lambda x: abs(x[1]), reverse=True)
    # Print results
    for sense in ['eye', 'ear', 'nose', 'tongue', 'body']:
        print(f"\n=== {sense.upper()} ===")
        for name, ic, cnt in results[sense][:5]:
            print(f"  {name}: IC={ic:.6f} (n={cnt})")
        # Also show current feature IC
        cur_name = f'feat_{sense}'
        # find in list
        cur_ic = None
        for name, ic, cnt in results[sense]:
            if name == cur_name:
                cur_ic = ic
                break
        if cur_ic is not None:
            print(f"  Current {cur_name}: IC={cur_ic:.6f}")
        else:
            print(f"  Current feature not in candidates list.")
    conn.close()

if __name__ == '__main__':
    main()