"""
多感官有效性分析：量化每个感官特征与未来收益率的关系
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
    horizon_hours: int = 24
) -> Dict[str, float]:
    """
    计算每个多感官特征与未来收益率的相关性（IC）。
    返回：{
        'feat_eye_dist': IC (相关系数),
        'feat_ear_zscore': IC,
        'feat_nose_sigmoid': IC,
        'feat_tongue_pct': IC,
        'feat_body_roc': IC
    }
    """
    # 取特徵 + 標籤
    labels_df = generate_labels_from_raw(session, symbol, horizon_hours)
    if labels_df.empty:
        logger.warning("無標籤數據可計算 IC")
        return {}

    # 合併特徵
    feat_query = session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp)
    feat_rows = feat_query.all()
    if not feat_rows:
        return {}
    feat_data = [{
        "timestamp": r.timestamp,
        "feat_eye_dist": r.feat_eye_dist,
        "feat_ear_zscore": r.feat_ear_zscore,
        "feat_nose_sigmoid": r.feat_nose_sigmoid,
        "feat_tongue_pct": r.feat_tongue_pct,
        "feat_body_roc": r.feat_body_roc
    } for r in feat_rows]
    feat_df = pd.DataFrame(feat_data)

    merged = pd.merge(feat_df, labels_df, left_on="timestamp", right_on="timestamp", how="inner")
    if merged.empty:
        return {}

    ic = {}
    for col in ["feat_eye_dist", "feat_ear_zscore", "feat_nose_sigmoid", "feat_tongue_pct", "feat_body_roc"]:
        if col in merged.columns and merged[col].notna().any():
            # 使用 Spearman 相关系数（对异常值鲁棒）
            ic_val = merged[col].corr(merged["future_return_pct"], method="spearman")
            ic[col] = ic_val if pd.notna(ic_val) else 0.0
        else:
            ic[col] = 0.0
    return ic

def compute_win_rate_by_feature_quantile(
    session: Session,
    symbol: str,
    horizon_hours: int = 24,
    n_quantiles: int = 5
) -> pd.DataFrame:
    """
    將每個特徵分為 n 分位數，計算每個分位數的未來收益率與 win rate。
    返回 DataFrame: quantile, feature, avg_return, win_rate, sample_count
    """
    labels_df = generate_labels_from_raw(session, symbol, horizon_hours)
    if labels_df.empty:
        return pd.DataFrame()

    feat_query = session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp)
    feat_rows = feat_query.all()
    feat_data = [{
        "timestamp": r.timestamp,
        "feat_eye_dist": r.feat_eye_dist,
        "feat_ear_zscore": r.feat_ear_zscore,
        "feat_nose_sigmoid": r.feat_nose_sigmoid,
        "feat_tongue_pct": r.feat_tongue_pct,
        "feat_body_roc": r.feat_body_roc
    } for r in feat_rows]
    feat_df = pd.DataFrame(feat_data)

    merged = pd.merge(feat_df, labels_df, on="timestamp", how="inner")
    if merged.empty:
        return pd.DataFrame()

    results = []
    for col in ["feat_eye_dist", "feat_ear_zscore", "feat_nose_sigmoid", "feat_tongue_pct", "feat_body_roc"]:
        if col not in merged.columns or merged[col].notna().sum() < 10:
            continue
        # 按特征分位数
        merged[f"{col}_q"] = pd.qcut(merged[col].rank(method='first'), q=n_quantiles, labels=False, duplicates='drop')
        grp = merged.groupby(f"{col}_q")
        for q in range(n_quantiles):
            grp_q = grp.get_group(q) if q in grp.groups else pd.DataFrame()
            if grp_q.empty:
                continue
            avg_ret = grp_q["future_return_pct"].mean()
            win_rate = (grp_q["label"] == 1).mean()
            results.append({
                "quantile": q,
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
