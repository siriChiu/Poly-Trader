"""
修復歷史特徵：只用 close_price 生成合理的 Body/Tongue 特徵值
- Body: 24h 價格動量（tan_h 壓縮）→ 代理清算壓力
- Tongue: 滾動波動率 Z-score（tan_h 壓縮）→ 代理市場情緒
"""
import sys, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))
import numpy as np
from config import load_config
from database.models import init_db, FeaturesNormalized, RawMarketData

cfg = load_config()
session = init_db(cfg["database"]["url"])

# 讀取所有 raw data 的 close_price
raw_rows = session.query(RawMarketData).order_by(RawMarketData.timestamp).all()
feat_rows = session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp).all()

prices = [(r.timestamp, r.close_price) for r in raw_rows if r.close_price is not None]
print(f"Price data: {len(prices)} points")
price_arr = np.array([p[1] for p in prices])

# Body: 24h 價格動量 proxy
# 價格快速下跌 = 多頭槓桿壓力大 = 清算壓力
body_values = []
for i in range(len(prices)):
    if i >= 24:
        mom = (price_arr[i] - price_arr[i-24]) / price_arr[i-24]
        body_values.append(math.tanh(mom * 20))  # 放大後壓縮到 -1~1
    else:
        body_values.append(0.0)

# Tongue: 滾動波動率 proxy
# 高波動 = 恐懼, 低波動 = 貪婪
tongue_values = []
window = 12  # 12 小時窗口
for i in range(len(prices)):
    if i >= window:
        segment = price_arr[i-window:i]
        vol = np.std(segment) / np.mean(segment)  # 相對波動率
        # 歷史波動率的 Z-score（全局）
        tongue_values.append(vol)
    else:
        tongue_values.append(0.0)

# 標準化 Tongue
tongue_arr = np.array(tongue_values)
tongue_mean = tongue_arr.mean()
tongue_std = tongue_arr.std() if tongue_arr.std() > 0 else 1
tongue_normalized = [(v - tongue_mean) / tongue_std for v in tongue_values]
tongue_compressed = [math.tanh(z) for z in tongue_normalized]

# 建立時間→值映射
body_map = {prices[i][0].replace(minute=0, second=0, microsecond=0): body_values[i] for i in range(len(prices))}
tongue_map = {prices[i][0].replace(minute=0, second=0, microsecond=0): tongue_compressed[i] for i in range(len(prices))}

# 更新 FeaturesNormalized
updated = 0
for feat in feat_rows:
    ts_key = feat.timestamp.replace(minute=0, second=0, microsecond=0)
    if ts_key in body_map:
        feat.feat_body_roc = body_map[ts_key]
    if ts_key in tongue_map:
        feat.feat_tongue_pct = tongue_map[ts_key]
    updated += 1

session.commit()

# 驗證
tongue_all = [f.feat_tongue_pct for f in session.query(FeaturesNormalized).all() if f.feat_tongue_pct is not None]
body_all = [f.feat_body_roc for f in session.query(FeaturesNormalized).all() if f.feat_body_roc is not None]

print(f"\nAfter fix:")
print(f"Tongue: {len(tongue_all)} values, {len(set(round(v,3) for v in tongue_all))} unique, std={np.std(tongue_all):.4f}")
print(f"Body: {len(body_all)} values, {len(set(round(v,3) for v in body_all))} unique, std={np.std(body_all):.4f}")

# 重跑感官驗證
from analysis.sense_validator import validate_senses, format_validation_report
result = validate_senses(session, "BTCUSDT")
print(f"\n{format_validation_report(result)}")

session.close()
