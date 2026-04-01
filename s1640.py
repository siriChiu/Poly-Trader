import sqlite3
conn = sqlite3.connect("poly_trader.db")
c = conn.cursor()

c.execute("SELECT COUNT(*) FROM features_normalized")
feat = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM raw_market_data")
raw = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM labels")
labels = c.fetchone()[0]

c.execute("SELECT id, timestamp, close_price, funding_rate, fear_greed_index FROM raw_market_data ORDER BY id DESC LIMIT 1")
r = c.fetchone()
print(f"Latest raw: id={r[0]}, ts={r[1]}, price={r[2]}, fng={r[4]}, funding={r[3]}")

c.execute("SELECT id, timestamp, round(feat_eye_dist,4), round(feat_ear_zscore,4), round(feat_nose_sigmoid,4), round(feat_tongue_pct,4), round(feat_body_roc,4) FROM features_normalized ORDER BY id DESC LIMIT 1")
r = c.fetchone()
print(f"Latest feat: id={r[0]}, ts={r[1]}")
print(f"  Eye={r[2]}, Ear={r[3]}, Nose={r[4]}, Tongue={r[5]}, Body={r[6]}")

print(f"\nDB: Raw={raw}, Features={feat}, Labels={labels}")

c.execute("SELECT MAX(timestamp) FROM features_normalized")
print(f"Feature pipeline last update: {c.fetchone()[0]}")

conn.close()
