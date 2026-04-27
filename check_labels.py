import sqlite3
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Users\Kazuha\repo\Poly-Trader")
db_path = PROJECT_ROOT / "poly_trader.db"

def main():
    conn = sqlite3.connect(str(db_path))
    # Check labels table
    query = """
    SELECT future_return_pct, COUNT(*) as cnt
    FROM labels
    GROUP BY future_return_pct
    ORDER BY cnt DESC
    LIMIT 10
    """
    df = pd.read_sql_query(query, conn)
    print("Future return pct distribution:")
    print(df)
    # Also check for nulls
    query_null = "SELECT COUNT(*) as null_count FROM labels WHERE future_return_pct IS NULL"
    null_cnt = pd.read_sql_query(query_null, conn).iloc[0,0]
    print(f"Null future_return_pct: {null_cnt}")
    # Check variance
    query_var = "SELECT AVG(future_return_pct) as mean, VARIANCE(future_return_pct) as var FROM labels WHERE future_return_pct IS NOT NULL"
    var_df = pd.read_sql_query(query_var, conn)
    print(f"Mean: {var_df.iloc[0,0]}, Variance: {var_df.iloc[0,1]}")
    conn.close()

if __name__ == "__main__":
    main()