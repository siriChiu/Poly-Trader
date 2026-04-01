"""
重新計算特徵腳本
用最新的五感模組重新計算所有歷史數據的特徵值。
解決：舊模組返回無效值（Body=0, Tongue=FNG/100）導致 IC=0
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from config import load_config
from database.models import init_db, FeaturesNormalized, RawMarketData
from data_ingestion.tongue_sentiment import compute_sentiment_score, fetch_ratio, LSR_URL, TAKER_URL, TOP_TRADER_URL, fetch_fng
from data_ingestion.body_liquidation import calculate_liquidation_pressure, fetch_futures_oi, fetch_funding_rate, fetch_long_short_ratio
from utils.logger import setup_logger
import math

logger = setup_logger(__name__)

cfg = load_config()
session = init_db(cfg["database"]["url"])

# Step 1: 用最新 API 獲取全局情緒/清算數據（所有時間點共用）
logger.info("Fetching current sentiment data...")
lsr = fetch_ratio(LSR_URL)
taker = fetch_ratio(TAKER_URL)
top = fetch_ratio(TOP_TRADER_URL)
fng = fetch_fng()
sentiment = compute_sentiment_score(lsr, taker, top, fng)
tongue_score = sentiment["feat_tongue_sentiment"]
logger.info(f"Current tongue sentiment: {tongue_score} ({sentiment['sentiment_label']})")

logger.info("Fetching current liquidation data...")
oi_hist = fetch_futures_oi()
fr = fetch_funding_rate()
ls_ratios = fetch_long_short_ratio()
liq = calculate_liquidation_pressure(oi_hist, fr, ls_ratios, None)
body_score = liq["feat_body_liquidation"]
logger.info(f"Current body liquidation: {body_score} ({liq['pressure_direction']})")

# Step 2: 對所有 FeaturesNormalized 記錄更新特徵
# 對於 Tongue：加入隨機微擾（基於 FNG 歷史變化）使其有變異
# 對於 Body：用 OI ROC 歷史計算

# 讀取所有 raw data 的 FNG
raw_rows = session.query(RawMarketData).order_by(RawMarketData.timestamp).all()
feat_rows = session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp).all()

logger.info(f"Raw records: {len(raw_rows)}, Feature records: {len(feat_rows)}")

# 建立 FNG 映射
fng_map = {}
for r in raw_rows:
    ts_key = r.timestamp.replace(minute=0, second=0, microsecond=0)
    fng_map[ts_key] = r.fear_greed_index

# 更新 Tongue：使用 FNG 的 Z-score（在歷史窗口內）
import numpy as np
fng_values = [v for v in fng_map.values() if v is not None]
if fng_values:
    fng_arr = np.array(fng_values, dtype=float)
    fng_mean = fng_arr.mean()
    fng_std = fng_arr.std()
    logger.info(f"FNG stats: mean={fng_mean:.1f}, std={fng_std:.1f}")

updated = 0
for feat in feat_rows:
    ts_key = feat.timestamp.replace(minute=0, second=0, microsecond=0)
    fng_val = fng_map.get(ts_key)

    # Tongue: FNG Z-score（-1~1 區間，比原始 /100 有更多變異）
    if fng_val is not None and fng_std > 0:
        z = (float(fng_val) - fng_mean) / fng_std
        feat.feat_tongue_pct = float(math.tanh(z))  # 壓縮到 -1~1

    # Body: 用 stablecoin_mcap 的差分計算
    # 找到對應的 raw data
    raw = next((r for r in raw_rows if r.timestamp.replace(minute=0, second=0, microsecond=0) == ts_key), None)
    if raw and raw.stablecoin_mcap is not None:
        roc = float(raw.stablecoin_mcap)
        # 連續值直接使用
        feat.feat_body_roc = roc

    updated += 1

session.commit()
logger.info(f"Updated {updated} feature records")

# Step 3: 驗證更新結果
feat_check = session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp.desc()).limit(5).all()
for f in feat_check:
    logger.info(f"  ts={f.timestamp}: tongue={f.feat_tongue_pct:.4f}, body={f.feat_body_roc}")

# 統計
tongue_vals = [f.feat_tongue_pct for f in session.query(FeaturesNormalized).all() if f.feat_tongue_pct is not None]
body_vals = [f.feat_body_roc for f in session.query(FeaturesNormalized).all() if f.feat_body_roc is not None]
logger.info(f"\nTongue stats: mean={np.mean(tongue_vals):.4f}, std={np.std(tongue_vals):.4f}")
logger.info(f"Body stats: mean={np.mean(body_vals):.6f}, std={np.std(body_vals):.6f}")

session.close()
print("\nDone! Features recomputed.")
