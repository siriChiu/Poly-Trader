import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Users\Kazuha\repo\Poly-Trader")
db_path = PROJECT_ROOT / "poly_trader.db"

def main():
    conn = sqlite3.connect(str(db_path))
    # Query to get features and labels, join on id
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
    ORDER BY f.timestamp
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    print(f"Total rows: {len(df)}")
    if len(df) == 0:
        print("No data found.")
        return

    # Ensure timestamp is datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    # Sort by timestamp
    df = df.sort_values('timestamp').reset_index(drop=True)

    senses = ['eye', 'ear', 'nose', 'tongue', 'body']
    feature_cols = [f'feat_{s}' for s in senses]
    sense_names = [s.capitalize() for s in senses]  # Eye, Ear, Nose, Tongue, Body

    # Compute future_return_pct > 0 for accuracy calculation
    future_returns = df['future_return_pct']
    actual_up = future_returns > 0

    results = []
    for feat_col, name in zip(feature_cols, sense_names):
        series = df[feat_col]
        # IC (Pearson correlation)
        ic = np.corrcoef(series, future_returns)[0,1] if len(series) > 1 else 0
        # Statistics
        mean_val = series.mean()
        std_val = series.std()
        range_val = series.max() - series.min()
        unique_count = series.nunique()
        # Trend: difference between last and first value (assuming ordered by time)
        if len(series) > 1:
            trend = series.iloc[-1] - series.iloc[0]
        else:
            trend = 0
        # Accuracy: predict up if feature > median
        median_val = series.median()
        pred_up = series > median_val
        accuracy = (pred_up == actual_up).mean() * 100
        results.append({
            'sense': name,
            'feature': feat_col,
            'ic': ic,
            'mean': mean_val,
            'std': std_val,
            'range': range_val,
            'unique': unique_count,
            'trend': trend,
            'accuracy': accuracy
        })
        print(f"\n{name} ({feat_col}):")
        print(f"  IC (corr with future return): {ic:.6f}")
        print(f"  Mean: {mean_val:.6f}")
        print(f"  Std: {std_val:.6f}")
        print(f"  Range: {range_val:.6f}")
        print(f"  Unique values: {unique_count}")
        print(f"  Trend (last - first): {trend:.6f}")
        print(f"  Accuracy (predict up if feature > median): {accuracy:.2f}%")
        # Anomaly flags
        if abs(ic) < 0.05:
            print("  *** IC < 0.05 -> Sense ineffective, consider replacement")
        elif abs(ic) < 0.03:
            print("  *** IC < 0.03 -> Sense needs optimization")
        if std_val < 1e-6:
            print("  *** Std approx 0 -> No variation, white noise")
        # Check accuracy vs target 90%
        if accuracy >= 90:
            print("  *** Accuracy >= 90% (meets target)")
        else:
            print("  *** Accuracy < 90% -> Below target")

    # Check for duplicate IC (sense leakage)
    print("\n=== Checking for duplicate IC (possible leakage) ===")
    ics = {r['sense']: r['ic'] for r in results}
    tol = 1e-4
    for i in range(len(senses)):
        for j in range(i+1, len(senses)):
            si, sj = senses[i].capitalize(), senses[j].capitalize()
            if abs(ics[si] - ics[sj]) < tol:
                print(f"!!! {si} and {sj} have nearly identical IC: {ics[si]:.6f} vs {ics[sj]:.6f} (possible leakage)")

    # Summary table
    print("\n=== Summary Table ===")
    print(f"{'Sense':<8} {'IC':<10} {'Mean':<10} {'Std':<10} {'Range':<10} {'Unique':<8} {'Trend':<10} {'Acc%':<8}")
    for r in results:
        print(f"{r['sense']:<8} {r['ic']:<10.6f} {r['mean']:<10.6f} {r['std']:<10.6f} {r['range']:<10.6f} {r['unique']:<8} {r['trend']:<10.6f} {r['accuracy']:<8.2f}")

    # Determine if any sense needs replacement (IC < 0.05) or optimization (IC < 0.03)
    ineffective = [r['sense'] for r in results if abs(r['ic']) < 0.05]
    needs_opt = [r['sense'] for r in results if abs(r['ic']) < 0.03 and abs(r['ic']) >= 0.05]
    no_variation = [r['sense'] for r in results if r['std'] < 1e-6]
    low_acc = [r['sense'] for r in results if r['accuracy'] < 90]

    print("\n=== Actions Required (based on HEARTBEAT.md Step 2) ===")
    if ineffective:
        print(f"*** Ineffective senses (IC < 0.05): {', '.join(ineffective)} -> consider replacement")
    if needs_opt:
        print(f"*** Senses needing optimization (IC < 0.03): {', '.join(needs_opt)}")
    if no_variation:
        print(f"*** Senses with no variation (std approx 0): {', '.join(no_variation)} -> white noise")
    if low_acc:
        print(f"*** Senses with accuracy < 90%: {', '.join(low_acc)} -> below target")
    # If none, print OK
    if not (ineffective or needs_opt or no_variation or low_acc):
        print("*** All senses meet criteria (IC >= 0.05, std > 0, accuracy >= 90%)")

    # Get latest raw market data for BTC price, FNG, funding rate, OI ROC
    print("\n=== Latest Raw Market Data ===")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM raw_market_data ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    cursor.execute("PRAGMA table_info(raw_market_data)")
    cols = [description[0] for description in cursor.description]
    conn.close()
    if row:
        data = dict(zip(cols, row))
        print(f"  Timestamp: {data.get('timestamp')}")
        print(f"  Symbol: {data.get('symbol')}")
        print(f"  Close Price: ${data.get('close_price'):,.2f}")
        print(f"  Funding Rate: {data.get('funding_rate'):.6f}")
        print(f"  Fear & Greed Index: {data.get('fear_greed_index'):.2f}")
        print(f"  OI ROC: {data.get('oi_roc'):.6f}")
        # Also maybe stablecoin_mcap, polymarket_prob, etc.
    else:
        print("  No raw market data found.")

if __name__ == "__main__":
    main()