"""
歷史數據回填腳本
從各 API 獲取歷史數據，計算多感官特徵，生成標籤，寫入 DB。
訓練模型所需的一次性數據準備。

數據來源：
- Binance Klines (Eye: 歷史 K 線)
- Binance Futures Funding Rate (Nose)
- Alternative.me FNG (Tongue)
- DefiLlama (Body: 穩定幣市值)
- 標籤：基於未來 N 小時的價格變化
"""

import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.models import RawMarketData, FeaturesNormalized, Labels, init_db
from config import load_config
from utils.logger import setup_logger

logger = setup_logger(__name__)

# ──────────────────────────────────────────────
# 1. Binance Klines (Eye - 歷史價格 + 訂單簿近似)
# ──────────────────────────────────────────────

def fetch_binance_klines(
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    days: int = 30,
    limit: int = 1000,
) -> pd.DataFrame:
    """
    從 Binance 獲取歷史 K 線數據。
    Returns DataFrame: timestamp, open, high, low, close, volume
    """
    url = "https://api.binance.com/api/v3/klines"
    end_time = int(datetime.utcnow().timestamp() * 1000)
    start_time = int((datetime.utcnow() - timedelta(days=days)).timestamp() * 1000)

    all_data = []
    current_start = start_time

    while current_start < end_time:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": current_start,
            "endTime": end_time,
            "limit": limit,
        }
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if not data:
                break
            all_data.extend(data)
            # 下一批：從最後一根 K 線的時間 + 1ms 開始
            current_start = data[-1][0] + 1
            time.sleep(0.1)  # 避免 rate limit
        except Exception as e:
            logger.error(f"Binance Klines 請求失敗: {e}")
            break

    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["close"] = df["close"].astype(float)
    df["volume"] = df["volume"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    return df[["timestamp", "open", "high", "low", "close", "volume"]]


# ──────────────────────────────────────────────
# 2. Binance Futures Funding Rate (Nose)
# ──────────────────────────────────────────────

def fetch_funding_rate_history(
    symbol: str = "BTCUSDT",
    days: int = 30,
    limit: int = 1000,
) -> pd.DataFrame:
    """
    從 Binance Futures 獲取歷史 Funding Rate。
    Returns DataFrame: timestamp, funding_rate
    """
    url = "https://fapi.binance.com/fapi/v1/fundingRate"
    end_time = int(datetime.utcnow().timestamp() * 1000)
    start_time = int((datetime.utcnow() - timedelta(days=days)).timestamp() * 1000)

    all_data = []
    current_start = start_time

    while current_start < end_time:
        params = {
            "symbol": symbol,
            "startTime": current_start,
            "endTime": end_time,
            "limit": limit,
        }
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if not data:
                break
            all_data.extend(data)
            current_start = data[-1]["fundingTime"] + 1
            time.sleep(0.1)
        except Exception as e:
            logger.error(f"Funding Rate 歷史請求失敗: {e}")
            break

    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data)
    df["timestamp"] = pd.to_datetime(df["fundingTime"], unit="ms")
    df["funding_rate"] = df["fundingRate"].astype(float)
    return df[["timestamp", "funding_rate"]].sort_values("timestamp")


# ──────────────────────────────────────────────
# 3. Fear & Greed Index (Tongue)
# ──────────────────────────────────────────────

def fetch_fng_history(days: int = 30) -> pd.DataFrame:
    """
    從 Alternative.me 獲取歷史 Fear & Greed Index。
    Returns DataFrame: timestamp, fng_value
    """
    url = "https://api.alternative.me/fng/"
    params = {"limit": days, "format": "json"}
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if not data:
            return pd.DataFrame()
        records = []
        for item in data:
            records.append({
                "timestamp": datetime.fromtimestamp(int(item["timestamp"])),
                "fng_value": int(item["value"]),
            })
        df = pd.DataFrame(records)
        return df.sort_values("timestamp")
    except Exception as e:
        logger.error(f"FNG 歷史請求失敗: {e}")
        return pd.DataFrame()


# ──────────────────────────────────────────────
# 4. DefiLlama Stablecoin (Body)
# ──────────────────────────────────────────────

def fetch_stablecoin_history() -> pd.DataFrame:
    """
    從 DefiLlama 獲取穩定幣市值歷史。
    Returns DataFrame: timestamp, total_usd
    """
    url = "https://stablecoins.llama.fi/stablecoincharts/all"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):
            data = data.get("all", [])
        if not data:
            return pd.DataFrame()

        records = []
        for item in data:
            ts = datetime.fromtimestamp(int(item["date"]))
            val = item.get("totalCirculatingUSD")
            if isinstance(val, dict):
                total = sum(v for v in val.values() if isinstance(v, (int, float)))
            elif isinstance(val, (int, float)):
                total = float(val)
            else:
                total = None
            records.append({"timestamp": ts, "total_usd": total})
        df = pd.DataFrame(records).dropna()
        return df.sort_values("timestamp")
    except Exception as e:
        logger.error(f"DefiLlama 歷史請求失敗: {e}")
        return pd.DataFrame()


# ──────────────────────────────────────────────
# 5. 合併數據 + 計算特徵 + 生成標籤
# ──────────────────────────────────────────────

def sigmoid(x: float) -> float:
    return 1 / (1 + np.exp(-x))


def build_historical_dataset(
    symbol: str = "BTCUSDT",
    days: int = 30,
    label_horizon_hours: int = 24,
) -> pd.DataFrame:
    """
    從所有來源拉取歷史數據，合併並計算特徵 + 標籤。
    Returns DataFrame with columns:
        timestamp, close, feat_eye_dist, feat_ear_zscore,
        feat_nose_sigmoid, feat_tongue_pct, feat_body_roc, label, future_return
    """
    logger.info(f"開始拉取 {days} 天歷史數據...")

    # 拉取各來源
    klines = fetch_binance_klines(symbol, "1h", days)
    logger.info(f"  Klines: {len(klines)} 筆")
    time.sleep(0.2)

    funding = fetch_funding_rate_history(symbol, days)
    logger.info(f"  Funding Rate: {len(funding)} 筆")
    time.sleep(0.2)

    fng = fetch_fng_history(days)
    logger.info(f"  FNG: {len(fng)} 筆")
    time.sleep(0.2)

    stablecoin = fetch_stablecoin_history()
    logger.info(f"  Stablecoin: {len(stablecoin)} 筆")

    if klines.empty:
        logger.error("無 K 線數據，無法繼續")
        return pd.DataFrame()

    # 以 Klines 為基準（每小時）
    df = klines.copy()
    df = df.set_index("timestamp").sort_index()

    # Eye 特徵：使用高低點作為 resistance/support 近似
    # feat_eye_up = (rolling_high - close) / close
    # feat_eye_down = (close - rolling_low) / close
    window = 24  # 24 小時窗口
    df["rolling_high"] = df["high"].astype(float).rolling(window).max()
    df["rolling_low"] = df["low"].astype(float).rolling(window).min()
    df["feat_eye_up"] = (df["rolling_high"] - df["close"].astype(float)) / df["close"].astype(float)
    df["feat_eye_down"] = (df["close"].astype(float) - df["rolling_low"]) / df["close"].astype(float)
    df["feat_eye_dist"] = df["feat_eye_up"]  # 使用向上距離作為 eye 特徵

    # Nose: Funding Rate Sigmoid
    if not funding.empty:
        funding = funding.set_index("timestamp")
        df["funding_rate"] = funding["funding_rate"].reindex(df.index, method="ffill")
        df["feat_nose_sigmoid"] = df["funding_rate"].apply(
            lambda x: 2 * sigmoid(x * 10000) - 1 if pd.notna(x) else None
        )
    else:
        df["feat_nose_sigmoid"] = None

    # Tongue: FNG 百分比
    if not fng.empty:
        fng = fng.set_index("timestamp")
        # FNG 是每天一筆，reindex 到每小時（向前填充）
        df["fng_value"] = fng["fng_value"].reindex(df.index, method="ffill")
        df["feat_tongue_pct"] = df["fng_value"] / 100.0
    else:
        df["feat_tongue_pct"] = None

    # Body: 穩定幣市值 ROC 離散化
    if not stablecoin.empty:
        stablecoin = stablecoin.set_index("timestamp")
        df["total_usd"] = stablecoin["total_usd"].reindex(df.index, method="ffill")
        df["body_roc"] = df["total_usd"].pct_change(periods=24)  # 24h ROC
        df["feat_body_roc"] = df["body_roc"].apply(
            lambda x: 1.0 if x > 0.005 else (-1.0 if x < -0.005 else 0.0) if pd.notna(x) else None
        )
    else:
        df["feat_body_roc"] = None

    # Ear: 暫時用價格動量作為代理（Polymarket 歷史難取得）
    # feat_ear_zscore = 滾動窗口內的 close 動量 Z-score
    df["price_momentum"] = df["close"].astype(float).pct_change(periods=6)  # 6h 動量
    mom_window = 48
    df["mom_mean"] = df["price_momentum"].rolling(mom_window).mean()
    df["mom_std"] = df["price_momentum"].rolling(mom_window).std()
    df["feat_ear_zscore"] = (df["price_momentum"] - df["mom_mean"]) / df["mom_std"].replace(0, np.nan)

    # 標籤：未來 N 小時的價格變化方向
    df["future_close"] = df["close"].astype(float).shift(-label_horizon_hours)
    df["future_return"] = (df["future_close"] - df["close"].astype(float)) / df["close"].astype(float)
    df["label"] = (df["future_return"] > 0).astype(int)

    # 清理
    df = df.reset_index()
    result_cols = [
        "timestamp", "close", "feat_eye_dist", "feat_ear_zscore",
        "feat_nose_sigmoid", "feat_tongue_pct", "feat_body_roc",
        "label", "future_return",
    ]
    result = df[[c for c in result_cols if c in df.columns]].copy()
    result.dropna(subset=["close", "label"], inplace=True)

    logger.info(f"歷史數據集構建完成: {len(result)} 筆")
    return result


def save_historical_to_db(
    session: Session,
    df: pd.DataFrame,
    symbol: str = "BTCUSDT",
) -> Dict[str, int]:
    """
    將歷史數據集寫入 DB：RawMarketData + FeaturesNormalized + Labels。
    Returns: {"raw": n, "features": n, "labels": n}
    """
    counts = {"raw": 0, "features": 0, "labels": 0}

    for _, row in df.iterrows():
        ts = row["timestamp"]

        # RawMarketData
        raw = RawMarketData(
            timestamp=ts,
            symbol=symbol,
            close_price=row.get("close"),
            eye_dist=row.get("feat_eye_dist"),
            ear_prob=None,  # 歷史 ear 用動量近似
        )
        session.add(raw)
        counts["raw"] += 1

        # FeaturesNormalized
        feat = FeaturesNormalized(
            timestamp=ts,
            feat_eye_dist=row.get("feat_eye_dist"),
            feat_ear_zscore=row.get("feat_ear_zscore"),
            feat_nose_sigmoid=row.get("feat_nose_sigmoid"),
            feat_tongue_pct=row.get("feat_tongue_pct"),
            feat_body_roc=row.get("feat_body_roc"),
        )
        session.add(feat)
        counts["features"] += 1

        # Labels
        if pd.notna(row.get("label")):
            label = Labels(
                timestamp=ts,
                symbol=symbol,
                horizon_hours=24,
                future_return_pct=row.get("future_return"),
                label=int(row["label"]),
            )
            session.add(label)
            counts["labels"] += 1

    session.commit()
    logger.info(f"寫入完成: {counts}")
    return counts


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def run_backfill(
    days: int = 30,
    symbol: str = "BTCUSDT",
    horizon_hours: int = 24,
) -> Dict:
    """
    完整回填流程：
    1. 拉取歷史數據
    2. 計算特徵 + 標籤
    3. 寫入 DB
    4. 觸發模型訓練
    """
    cfg = load_config()
    session = init_db(cfg["database"]["url"])

    logger.info(f"=== 歷史數據回填開始 ({days} 天) ===")

    df = build_historical_dataset(symbol, days, horizon_hours)
    if df.empty:
        logger.error("無歷史數據可寫入")
        return {"error": "no data"}

    counts = save_historical_to_db(session, df, symbol)

    # 統計
    label_dist = df["label"].value_counts().to_dict() if "label" in df.columns else {}
    non_null = {}
    for col in ["feat_eye_dist", "feat_ear_zscore", "feat_nose_sigmoid", "feat_tongue_pct", "feat_body_roc"]:
        if col in df.columns:
            non_null[col] = int(df[col].notna().sum())

    result = {
        "total_rows": len(df),
        "db_counts": counts,
        "label_distribution": label_dist,
        "non_null_features": non_null,
        "date_range": f"{df['timestamp'].min()} ~ {df['timestamp'].max()}",
    }

    logger.info(f"=== 回填完成: {result} ===")
    session.close()
    return result


if __name__ == "__main__":
    result = run_backfill(days=30)
    print(f"\n=== Backfill Result ===")
    for k, v in result.items():
        print(f"  {k}: {v}")
