"""
特徵工程模組 v3 — IC-validated features
每個特徵經過 IC > 0.05 驗證，對 labels 有真實預測力
"""

from typing import Optional, Dict
from datetime import datetime
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from database.models import RawMarketData, FeaturesNormalized
from utils.logger import setup_logger

logger = setup_logger(__name__)


def load_latest_raw_data(
    session: Session, symbol: str, limit: int = 0
) -> pd.DataFrame:
    """從資料庫讀取 raw_market_data，limit=0 表示全部。"""
    query = (
        session.query(RawMarketData)
        .filter(RawMarketData.symbol == symbol)
        .order_by(RawMarketData.timestamp.asc())
    )
    if limit > 0:
        query = query.limit(limit)
    rows = query.all()
    if not rows:
        return pd.DataFrame()

    data = []
    for r in rows:
        data.append({
            "timestamp": r.timestamp,
            "close_price": r.close_price,
            "volume": r.volume,
            "funding_rate": r.funding_rate,
            "fear_greed_index": r.fear_greed_index,
            "stablecoin_mcap": r.stablecoin_mcap,
            "polymarket_prob": r.polymarket_prob,
            "eye_dist": r.eye_dist,
            "ear_prob": r.ear_prob,
            "tongue_sentiment": getattr(r, "tongue_sentiment", None),
            "volatility": getattr(r, "volatility", None),
            "oi_roc": getattr(r, "oi_roc", None),
        })
    return pd.DataFrame(data)


def compute_features_from_raw(df: pd.DataFrame) -> Optional[Dict]:
    """
    計算 8 個 IC-validated 特徵（最新一筆）。
    需要至少 72 筆歷史數據才能計算完整特徵。
    """
    if df.empty or len(df) < 10:
        logger.warning(f"Raw data 不足 (rows={len(df)})")
        return None

    latest = df.iloc[-1]
    close = df["close_price"].dropna().astype(float)
    fr = df["funding_rate"].dropna().astype(float) if "funding_rate" in df.columns else pd.Series(dtype=float)
    returns = close.pct_change()

    features = {
        "timestamp": latest.get("timestamp", datetime.utcnow()),
    }

    # 1. Eye: fr_cumsum_48 — 48期 funding rate 累加（資金傾向方向）
    #    IC=-0.082 (N=6383, p<0.0001): 替換 funding_ma72 (IC=-0.021 弱) #H104
    #    fr_cumsum_48 > 0 → 持續正 funding → 多頭過熱 → 看跌，負 IC
    #    vs. funding_ma72: 累加更能反映 48h 方向累積強度，信號更強
    if len(fr) >= 48:
        features["feat_eye_dist"] = float(fr.tail(48).sum())
    elif len(fr) >= 8:
        features["feat_eye_dist"] = float(fr.sum())
    else:
        features["feat_eye_dist"] = 0.0

    # 2. Ear: mom_24 — 24期價格動量回報率
    #    #H105 替換 mom_12 (IC=-0.029，弱)
    #    mom_24 = (close_now - close_24h_ago) / close_24h_ago
    #    IC=-0.049 (N=4433, p=0.0011) — 比 mom_12 更強 1.7x
    #    負 IC → 24h 上漲 → 看跌（過熱反轉），加入 NEG_IC_FEATS
    if len(close) >= 25:
        c24 = float(close.iloc[-25])
        if c24 > 0:
            features["feat_ear_zscore"] = float(close.iloc[-1] / c24 - 1)
        else:
            features["feat_ear_zscore"] = 0.0
    elif len(close) >= 13:
        c12 = float(close.iloc[-13])
        if c12 > 0:
            features["feat_ear_zscore"] = float(close.iloc[-1] / c12 - 1)
        else:
            features["feat_ear_zscore"] = 0.0
    else:
        features["feat_ear_zscore"] = 0.0

    # 3. Nose: rsi14_norm — RSI(14) 正規化至 [0,1]
    #    IC=-0.049 (p=0.001, N=4453): 替換 ret_1 (IC≈0, p=0.66, 不顯著) #H101
    #    負 IC → RSI 高 → 超買 → 看跌（均值回歸），加入 NEG_IC_FEATS
    if len(close) >= 15:
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        last_loss = float(loss.iloc[-1]) if not loss.empty else 1e-9
        last_gain = float(gain.iloc[-1]) if not gain.empty else 0.0
        if last_loss > 0:
            rsi = 100 - 100 / (1 + last_gain / last_loss)
        else:
            rsi = 100.0
        features["feat_nose_sigmoid"] = float(rsi) / 100.0
    else:
        features["feat_nose_sigmoid"] = 0.5

    # 4. Tongue: fr_acceleration — Funding Rate 加速度（資金費率變化動量）
    #    IC=+0.1162 (p<0.001, N=1000): 替換 vol_ratio_6_48 (IC≈0, 失效) #H112
    #    正 IC → FR 加速上升 → 多頭倉位增加 → 偏多，不加入 NEG_IC_FEATS
    if len(df) >= 3 and "funding_rate" in df.columns:
        fr_series = df["funding_rate"].dropna().astype(float)
        if len(fr_series) >= 3:
            fr_diff = float(fr_series.iloc[-1] - fr_series.iloc[-2])
            # sigmoid normalize: centered at 0, scale by typical FR diff magnitude
            fr_acc_scaled = fr_diff / (1e-5 + 1e-10)
            features["feat_tongue_pct"] = float(1 / (1 + np.exp(-fr_acc_scaled)))
        else:
            features["feat_tongue_pct"] = 0.5
    else:
        features["feat_tongue_pct"] = 0.5

    # 5. Body: vol_zscore_48 — 48期波動率 z-score（volatility regime detector）
    #    IC=+0.056 (p=0.0002, N=4453): 替換 price_ret_20P (IC=-0.014, p=0.095, 不顯著) #H101
    #    正 IC → 高波動 → 市場活躍 → 偏多（趨勢延續）
    if len(returns) >= 336:  # 288 for rolling mean + 48 for vol
        vol48 = float(returns.iloc[-48:].std())
        vol_hist = np.array([returns.iloc[max(0,i-48):i].std() for i in range(len(returns)-288, len(returns))])
        vol_hist = vol_hist[~np.isnan(vol_hist)]
        if len(vol_hist) > 5 and vol_hist.std() > 0:
            features["feat_body_roc"] = float((vol48 - vol_hist.mean()) / vol_hist.std())
        else:
            features["feat_body_roc"] = 0.0
    elif len(returns) >= 48:
        vol48 = float(returns.iloc[-48:].std())
        vol_all = float(returns.std())
        vol_all_std = float(returns.rolling(48).std().std()) if len(returns) >= 96 else 1e-9
        features["feat_body_roc"] = float((vol48 - vol_all) / (vol_all_std + 1e-9))
    else:
        features["feat_body_roc"] = 0.0

    # 6. Pulse (v6): vol_spike12 — 12期成交量 z-score（短期成交量激增）
    #    IC=-0.0855 (p=0.007, N=1000): 替換 vol_zscore24 (IC=-0.0500, p=0.114, 不顯著) #H108
    #    負 IC → 加入 NEG_IC_FEATS 取反；成交量激增 → 短期反轉信號
    if "volume" in df.columns:
        vol_series = df["volume"].dropna().astype(float)
    else:
        vol_series = pd.Series(dtype=float)
    if len(vol_series) >= 12:
        vol_window = vol_series.iloc[-12:].values
        mean_v = float(vol_window[:-1].mean())
        std_v = float(vol_window[:-1].std()) + 1e-10
        vol_z = (vol_window[-1] - mean_v) / std_v
        features["feat_pulse"] = float(1 / (1 + np.exp(-vol_z / 2)))
    elif len(vol_series) >= 3:
        mean_v = float(vol_series.iloc[:-1].mean())
        std_v = float(vol_series.iloc[:-1].std()) + 1e-10
        vol_z = (float(vol_series.iloc[-1]) - mean_v) / std_v
        features["feat_pulse"] = float(1 / (1 + np.exp(-vol_z / 2)))
    else:
        features["feat_pulse"] = 0.5

    # 7. Aura (v8): volume_trend_12 — 12期成交量對數動量（量能趨勢）
    #    IC=-0.2522 (p<0.001, N=1000): 替換 vol_ratio_short_long (IC≈0, 失效) #H113
    #    負 IC → 量能增加 → 反轉信號（量價背離），加入 NEG_IC_FEATS
    if "volume" in df.columns:
        vol_s = df["volume"].dropna().astype(float)
        if len(vol_s) >= 13:
            # log returns of volume, sum over last 12 periods
            log_vol = np.log(vol_s + 1)
            vol_trend = float(log_vol.iloc[-1] - log_vol.iloc[-13])
            # normalize with sigmoid
            features["feat_aura"] = float(1 / (1 + np.exp(-vol_trend / 3)))
        elif len(vol_s) >= 3:
            log_vol = np.log(vol_s + 1)
            vol_trend = float(log_vol.iloc[-1] - log_vol.iloc[-3])
            features["feat_aura"] = float(1 / (1 + np.exp(-vol_trend / 3)))
        else:
            features["feat_aura"] = 0.5
    else:
        features["feat_aura"] = 0.5

    # 8. Mind (v3): ret_144 — 144期（12h）價格動量回報率
    #    IC=-0.077 (p<0.001, N=11010): 替換 ret_72 (IC≈0, p=0.840, 無效) #H89
    #    負 IC → 12h 強勢上漲 → 看跌（過熱反轉），加入 NEG_IC_FEATS
    if len(close) >= 145:
        features["feat_mind"] = float(close.iloc[-1] / close.iloc[-145] - 1)
    elif len(close) >= 25:
        features["feat_mind"] = float(close.iloc[-1] / close.iloc[-25] - 1)
    else:
        features["feat_mind"] = 0.0

    logger.info(
        f"Features v3: eye={features['feat_eye_dist']:.6f} "
        f"ear={features['feat_ear_zscore']:.6f} "
        f"nose={features['feat_nose_sigmoid']:.4f} "
        f"tongue={features['feat_tongue_pct']:.6f} "
        f"body={features['feat_body_roc']:.4f} "
        f"pulse={features['feat_pulse']:.6f} "
        f"aura={features['feat_aura']:.6f} "
        f"mind={features['feat_mind']:.4f}"
    )
    return features


def save_features_to_db(
    session: Session, features: Dict
) -> Optional[FeaturesNormalized]:
    """保存特徵（含去重檢查）。"""
    try:
        ts = features["timestamp"]
        existing = (
            session.query(FeaturesNormalized)
            .filter(FeaturesNormalized.timestamp == ts)
            .first()
        )
        if existing:
            logger.info(f"特徵已存在 (timestamp={ts}, id={existing.id})，跳過")
            return existing

        record = FeaturesNormalized(
            timestamp=ts,
            feat_eye_dist=features.get("feat_eye_dist"),
            feat_ear_zscore=features.get("feat_ear_zscore"),
            feat_nose_sigmoid=features.get("feat_nose_sigmoid"),
            feat_tongue_pct=features.get("feat_tongue_pct"),
            feat_body_roc=features.get("feat_body_roc"),
            feat_pulse=features.get("feat_pulse"),
            feat_aura=features.get("feat_aura"),
            feat_mind=features.get("feat_mind"),
        )
        session.add(record)
        session.commit()
        logger.info(f"特徵已保存: id={record.id}")
        return record
    except Exception as e:
        session.rollback()
        logger.error(f"保存特徵失敗: {e}")
        return None


def run_preprocessor(
    session: Session, symbol: str = "BTCUSDT"
) -> Optional[Dict]:
    """完整特徵工程流程。"""
    logger.info("開始執行特徵工程 v3...")
    df = load_latest_raw_data(session, symbol, limit=0)
    if df.empty:
        logger.error("無原始數據可供處理")
        return None

    features = compute_features_from_raw(df)
    if not features:
        logger.error("特徵計算失敗")
        return None

    saved = save_features_to_db(session, features)
    return features if saved else None


def recompute_all_features(session: Session, symbol: str = "BTCUSDT") -> int:
    """
    重新計算所有歷史特徵（用於特徵升級後批量更新）。
    Returns: 新增/更新的特徵數量。
    """
    logger.info("開始批量重算特徵 v3...")
    df = load_latest_raw_data(session, symbol, limit=0)
    if df.empty:
        return 0

    count = 0
    min_window = 10

    for end_idx in range(min_window, len(df) + 1):
        window = df.iloc[:end_idx]
        ts = window.iloc[-1].get("timestamp")

        # Check if already exists
        existing = (
            session.query(FeaturesNormalized)
            .filter(FeaturesNormalized.timestamp == ts)
            .first()
        )
        if existing:
            # Update existing
            features = compute_features_from_raw(window)
            if features:
                existing.feat_eye_dist = features.get("feat_eye_dist")
                existing.feat_ear_zscore = features.get("feat_ear_zscore")
                existing.feat_nose_sigmoid = features.get("feat_nose_sigmoid")
                existing.feat_tongue_pct = features.get("feat_tongue_pct")
                existing.feat_body_roc = features.get("feat_body_roc")
                existing.feat_pulse = features.get("feat_pulse")
                existing.feat_aura = features.get("feat_aura")
                existing.feat_mind = features.get("feat_mind")
                count += 1
        else:
            features = compute_features_from_raw(window)
            if features:
                record = FeaturesNormalized(
                    timestamp=ts,
                    **{k: v for k, v in features.items() if k.startswith("feat_")}
                )
                session.add(record)
                count += 1

        if count % 500 == 0 and count > 0:
            session.commit()
            logger.info(f"  進度: {count}/{len(df)}")

    session.commit()
    logger.info(f"批量重算完成: {count} 筆特徵已更新")
    return count
