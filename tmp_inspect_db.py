import sqlite3
import math

conn = sqlite3.connect('/home/kazuha/Poly-Trader/poly_trader.db')
cursor = conn.cursor()

# Stats for ear and tongue columns
for col in ['feat_ear', 'feat_tongue']:
    cursor.execute(f'SELECT COUNT(*), COUNT(DISTINCT {col}), MIN({col}), MAX({col}), AVG({col}) FROM features_normalized WHERE {col} IS NOT NULL')
    row = cursor.fetchone()
    count, unique, mn, mx, avg = row
    
    # Compute stddev manually
    cursor.execute(f'SELECT {col} FROM features_normalized WHERE {col} IS NOT NULL')
    vals = [r[0] for r in cursor.fetchall()]
    if len(vals) > 1:
        mean = sum(vals) / len(vals)
        variance = sum((x - mean) ** 2 for x in vals) / len(vals)
        stddev = math.sqrt(variance)
    else:
        stddev = 0
    
    print(f'\n=== {col} ===')
    print(f'  Total: {count}, Unique: {unique}, Min: {mn}, Max: {mx}, Avg: {avg:.6f}, StdDev: {stddev:.6f}')
    # Get unique values distribution
    cursor.execute(f'SELECT {col}, COUNT(*) as cnt FROM features_normalized WHERE {col} IS NOT NULL GROUP BY {col} ORDER BY {col}')
    vals_dist = cursor.fetchall()
    for v in vals_dist:
        print(f'  Value={v[0]}, Count={v[1]}')

# Also check raw features table
print('\n=== Checking raw features table columns ===')
cursor.execute('PRAGMA table_info(features_raw)')
columns_raw = cursor.fetchall()
for col in columns_raw:
    print(f'  {col[1]} ({col[2]})')

# Check what columns might have ear in them
print('\n=== Looking for ear/tongue columns in raw features ===')
for col_name in [c[1] for c in columns_raw]:
    if 'ear' in col_name.lower() or 'tongue' in col_name.lower():
        cursor.execute(f'SELECT COUNT(*), COUNT(DISTINCT {col_name}) FROM features_raw WHERE {col_name} IS NOT NULL')
        row = cursor.fetchone()
        print(f'  {col_name}: Total={row[0]}, Unique={row[1]}')
        if row[1] and row[1] <= 20:
            cursor.execute(f'SELECT DISTINCT {col_name} FROM features_raw WHERE {col_name} IS NOT NULL ORDER BY {col_name}')
            vals = cursor.fetchall()
            for v in vals:
                print(f'    Unique value: {v[0]}')

# Check what data sources feed the ear/tongue features
print('\n=== Sample raw feature rows (closest to ear/tongue) ===')
# Look for any col with close, price, or ratio
raw_cols = [c[1] for c in columns_raw]
for pattern in ['close', 'price', 'ratio']:
    matches = [c for c in raw_cols if pattern in c.lower()]
    if matches:
        print(f'  Columns with "{pattern}": {matches}')

conn.close()
