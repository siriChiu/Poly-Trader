"""
多特徵有效性分析：量化每个特徵特征与未来收益率的关系
"""

import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, Tuple
from sqlalchemy.orm import Session
from datetime import timedelta

from database.models import FeaturesNormalized, Labels, RawMarketData
from utils.logger import setup_logger

logger = setup_logger(__name__)

def compute_information_coefficient(
    session: Session,
    symbol: str,
    horizon_hours: int = 24,
    use_recent_n: int = None
) -> Dict[str, float]:
    """
    计算每个多特徵特征与未来收益率的相关性（IC）。
    返回：{ 'eye': IC, 'ear': IC, 'nose': IC, 'tongue': IC, 'body': IC }
    """
    import numpy as np
    from sqlalchemy import asc
    # get features
    q = session.query(FeaturesNormalized).order_by(asc(FeaturesNormalized.timestamp))
    feat_rows = q.all()
    if not feat_rows:
        return {}
    feat_data = [{
        "ts": r.timestamp,
        "eye": r.feat_eye if r.feat_eye is not None else getattr(r, "feat_eye_dist", None),
        "ear": r.feat_ear if r.feat_ear is not None else getattr(r, "feat_ear_zscore", None),
        "nose": r.feat_nose if r.feat_nose is not None else getattr(r, "feat_nose_sigmoid", None),
        "tongue": r.feat_tongue if r.feat_tongue is not None else getattr(r, "feat_tongue_pct", None),
        "body": r.feat_body if r.feat_body is not None else getattr(r, "feat_body_roc", None),
        "regime": getattr(r, "regime_label", None),
    } for r in feat_rows]
    feat_df = pd.DataFrame(feat_data)
    feat_df["ts"] = pd.to_datetime(feat_df["ts"])
    feat_df = feat_df.sort_values("ts").reset_index(drop=True)
    if use_recent_n and len(feat_df) > use_recent_n:
        feat_df = feat_df.iloc[-use_recent_n:].reset_index(drop=True)
    # labels: forward return
    prices = generate_labels_from_raw(session, symbol, horizon_hours)
    if prices.empty:
        return {}
    prices = prices.rename(columns={"timestamp": "ts"})
    prices["ts"] = pd.to_datetime(prices["ts"])
    # nearest-match merge
    merged = pd.merge_asof(feat_df, prices, on="ts", direction="nearest", tolerance=timedelta(hours=1))
    if merged.empty:
        return {}
    ic = {}
    for col_label, col_key in [("eye","eye"),("ear","ear"),("nose","nose"),("tongue","tongue"),("body","body")]:
        if col_key not in merged.columns or merged[col_key].notna().sum() < 10:
            ic[col_label] = 0.0
            continue
        valid = merged[[col_key, "future_return_pct"]].dropna()
        if len(valid) < 10 or valid[col_key].std() < 1e-10 or valid["future_return_pct"].std() < 1e-10:
            ic[col_label] = 0.0
            continue
        ic_val = float(valid[col_key].corr(valid["future_return_pct"], method="spearman"))
        ic[col_label] = ic_val if np.isfinite(ic_val) else 0.0
    return ic

def compute_win_rate_by_feature_quantile(
    session: Session,
    symbol: str,
    horizon_hours: int = 24,
    n_quantiles: int = 5
) -> pd.DataFrame:
    """
    分位數勝率熱圖數據。
    返回 DataFrame: quantile, feature, avg_return, win_rate, samples
    """
    q = session.query(FeaturesNormalized).order_by(asc(FeaturesNormalized.timestamp))
    feat_rows = q.all()
    if not feat_rows:
        return pd.DataFrame()
    feat_data = [{
        "ts": r.timestamp,
        "eye": r.feat_eye if r.feat_eye is not None else getattr(r, "feat_eye_dist", None),
        "ear": r.feat_ear if r.feat_ear is not None else getattr(r, "feat_ear_zscore", None),
        "nose": r.feat_nose if r.feat_nose is not None else getattr(r, "feat_nose_sigmoid", None),
        "tongue": r.feat_tongue if r.feat_tongue is not None else getattr(r, "feat_tongue_pct", None),
        "body": r.feat_body if r.feat_body is not None else getattr(r, "feat_body_roc", None),
    } for r in feat_rows]
    feat_df = pd.DataFrame(feat_data)
    feat_df["ts"] = pd.to_datetime(feat_df["ts"])
    feat_df = feat_df.sort_values("ts").reset_index(drop=True)
    prices = generate_labels_from_raw(session, symbol, horizon_hours)
    if prices.empty:
        return pd.DataFrame()
    prices = prices.rename(columns={"timestamp": "ts"})
    prices["ts"] = pd.to_datetime(prices["ts"])
    merged = pd.merge_asof(feat_df, prices, on="ts", direction="nearest", tolerance=timedelta(hours=1))
    if merged.empty:
        return pd.DataFrame()
    results = []
    for col in ["eye", "ear", "nose", "tongue", "body"]:
        if col not in merged.columns or merged[col].notna().sum() < 20:
            continue
        clean = merged[[col, "future_return_pct", "label", "ts"]].dropna()
        if len(clean) < 20:
            continue
        clean["_q"] = pd.qcut(clean[col].rank(method='first'), q=n_quantiles, labels=False, duplicates='drop')
        for qv in range(n_quantiles):
            grp_q = clean[clean["_q"] == qv]
            if grp_q.empty:
                continue
            avg_ret = grp_q["future_return_pct"].mean()
            win_rate = float((grp_q["label"] == 1).mean())
            results.append({
                "quantile": qv,
                "feature": col,
                "avg_return": avg_ret,
                "win_rate": win_rate,
                "samples": len(grp_q)
            })
    return pd.DataFrame(results)

def generate_labels_from_raw(
    session: Session,
    symbol: str,
    horizon_hours: int = 24,
    threshold_pct: float = 0.0
) -> pd.DataFrame:
    """
    從 RawMarketData 與 FeaturesNormalized 生成標籤（簡化版，不依賴 Labels 表）。
    這對於沒有持久化標籤的現有數據很有用。
    """
    # 取特徵時間
    feat_query = session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp)
    feat_times = [r.timestamp for r in feat_query.all()]
    if not feat_times:
        return pd.DataFrame()

    # 取價格時間序列
    raw_query = session.query(RawMarketData).filter(
        RawMarketData.symbol == symbol,
        RawMarketData.close_price.isnot(None)
    ).order_by(RawMarketData.timestamp)
    raw_rows = raw_query.all()
    if not raw_rows:
        return pd.DataFrame()
    prices_df = pd.DataFrame([
        {"timestamp": r.timestamp, "close_price": r.close_price}
        for r in raw_rows
    ]).set_index("timestamp").sort_index()

    labels = []
    for ts in feat_times:
        future_ts = ts + timedelta(hours=horizon_hours)
        # 向後查找最接近 future_ts 的價格
        idx = prices_df.index.searchsorted(future_ts)
        if idx >= len(prices_df):
            continue
        future_price = prices_df.iloc[idx]["close_price"]
        # 當前價格
        idx_cur = prices_df.index.searchsorted(ts)
        if idx_cur >= len(prices_df):
            continue
        current_price = prices_df.iloc[idx_cur]["close_price"]
        if current_price == 0:
            continue
        ret = (future_price - current_price) / current_price
        label = 1 if ret > threshold_pct else 0
        labels.append({
            "timestamp": ts,
            "label": label,
            "future_return_pct": ret
        })
    return pd.DataFrame(labels)

if __name__ == "__main__":
    print("Sense effectiveness analysis module loaded.")
