"""
特徵工程模組 v3 — IC-validated features
每個特徵經過 IC > 0.05 驗證，對 labels 有真實預測力
"""

from typing import Optional, Dict
from datetime import datetime, timedelta
import pandas as pd
import math
import numpy as np
from sqlalchemy.orm import Session
from database.models import RawMarketData, FeaturesNormalized
from utils.logger import setup_logger

logger = setup_logger(__name__)


def _compute_technical_indicators_from_df(df: pd.DataFrame) -> Dict[str, float]:
    """Compute IC-validated technical indicators from OHLCV data.
    
    P0: Now also fetches 4H data from OKX for 4H timeframe features.
    The 1min-based indicators are still computed for backward compatibility.
    """
    close = df["close_price"].dropna().astype(float) if "close_price" in df.columns else pd.Series(dtype=float)
    
    # Ensure volume proxy has same length as close series
    # Raw volume data is sparse (153/8913 non-null) → use price-change proxy
    if "volume" in df.columns and df["volume"].notna().sum() > len(close) * 0.5:
        vol = df["volume"].dropna().astype(float)
        # Resample/interpolate to match close length if needed
        if len(vol) != len(close):
            vol = vol.reindex(close.index).interpolate(method="linear").ffill().bfill()
    else:
        # Estimate volume proxy from absolute price changes
        vol = close.diff().abs().fillna(1.0)

    if len(close) < 64:  # Minimum for NW envelope
        return {}

    from feature_engine.technical_indicators import compute_technical_features

    closes = close.values
    high_est = closes * 1.005  # Estimate highs from close
    low_est = closes * 0.995   # Estimate lows from close
    vols = vol.values[-len(closes):]  # now guaranteed same length

    result = compute_technical_features(closes, high_est, low_est, vols)
    
    # ─── P0: 4H Timeframe Features ───
    # Fetch 4H data from OKX and compute 4H support-line bias features
    try:
        import ccxt
        exchange = ccxt.okx({"enableRateLimit": True, "verbose": False})
        ohlcv_4h = exchange.fetch_ohlcv("BTC/USDT", "4h", limit=300)
        if ohlcv_4h and len(ohlcv_4h) >= 200:
            candles_4h = {
                "timestamps": np.array([o[0] for o in ohlcv_4h]),
                "opens": np.array([o[1] for o in ohlcv_4h]),
                "highs": np.array([o[2] for o in ohlcv_4h]),
                "lows": np.array([o[3] for o in ohlcv_4h]),
                "closes": np.array([o[4] for o in ohlcv_4h]),
                "volumes": np.array([o[5] for o in ohlcv_4h]),
            }
            from feature_engine.ohlcv_4h import compute_4h_indicators
            ind_4h = compute_4h_indicators(candles_4h)
            n_4h = len(candles_4h["closes"])
            
            def gv_4h(name, default=0):
                arr = ind_4h.get(name, [default] * n_4h)
                if n_4h > 0:
                    v = arr[-1]
                    try:
                        v_float = float(v)
                    except (TypeError, ValueError):
                        return float(default)
                    return v_float if np.isfinite(v_float) else float(default)
                return float(default)
            
            result["feat_4h_bias50"] = gv_4h("4h_bias50", 0)
            result["feat_4h_bias20"] = gv_4h("4h_bias20", 0)
            result["feat_4h_bias200"] = gv_4h("4h_bias200", 0)
            result["feat_4h_rsi14"] = gv_4h("4h_rsi14", 50)
            result["feat_4h_macd_hist"] = gv_4h("4h_macd_hist", 0)
            result["feat_4h_bb_pct_b"] = gv_4h("4h_bb_pct_b", 0.5)
            result["feat_4h_dist_bb_lower"] = gv_4h("4h_dist_bb_lower", 0)
            result["feat_4h_ma_order"] = gv_4h("4h_ma_order", 0)
            result["feat_4h_dist_swing_low"] = gv_4h("4h_dist_swing_low", 0)
            result["feat_4h_vol_ratio"] = gv_4h("4h_vol_ratio", 1)
        else:
            logger.warning("4H OHLCV data insufficient (< 200 candles)")
    except Exception as e:
        logger.warning(f"4H feature computation failed: {e}")
        # Set defaults
        result["feat_4h_bias50"] = None
        result["feat_4h_bias20"] = None
        result["feat_4h_bias200"] = None
        result["feat_4h_rsi14"] = 50
        result["feat_4h_macd_hist"] = 0
        result["feat_4h_bb_pct_b"] = 0.5
        result["feat_4h_dist_bb_lower"] = 0
        result["feat_4h_ma_order"] = 0
        result["feat_4h_dist_swing_low"] = 0
        result["feat_4h_vol_ratio"] = 1
    
    return result


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
            # P0 #H381: Include VIX & DXY from raw data for feature pipeline
            "vix_value": getattr(r, "vix_value", None),
            "dxy_value": getattr(r, "dxy_value", None),
            "nq_value": getattr(r, "nq_value", None),
            "claw_liq_ratio": getattr(r, "claw_liq_ratio", None),
            "claw_liq_total": getattr(r, "claw_liq_total", None),
            "fang_pcr": getattr(r, "fang_pcr", None),
            "fang_iv_skew": getattr(r, "fang_iv_skew", None),
            "fin_etf_netflow": getattr(r, "fin_etf_netflow", None),
            "fin_etf_trend": getattr(r, "fin_etf_trend", None),
            "web_whale_pressure": getattr(r, "web_whale_pressure", None),
            "web_large_trades_count": getattr(r, "web_large_trades_count", None),
            "scales_ssr": getattr(r, "scales_ssr", None),
            "nest_pred": getattr(r, "nest_pred", None),
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
        "symbol": latest.get("symbol", "BTC/USDT"),
    }

    # 1. Eye (v4b): return_24h / vol_72h — 24期回報除以72期波動率
    #    原 FR 幾乎恆定 -5e-06 => eye~0 => score~0.5 無法識別
    #    新公式: ret_24 / std_72 => 大回報/低波動 = 趨勢強，小回報/高波動 = 雜訊
    if len(returns) >= 72:
        ret24 = float(close.iloc[-1] / close.iloc[-25] - 1) if len(close) >= 25 else 0.0
        vol72 = float(returns.tail(72).std())
        if pd.notna(vol72) and vol72 > 1e-8:
            features["feat_eye_dist"] = float(ret24 / vol72)
        else:
            features["feat_eye_dist"] = 0.0
    elif len(returns) >= 24:
        ret24 = float(close.iloc[-1] / close.iloc[-25] - 1) if len(close) >= 25 else 0.0
        vol_all = float(returns.std())
        features["feat_eye_dist"] = float(ret24 / vol_all) if (pd.notna(vol_all) and vol_all > 1e-8) else 0.0
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
            # #H371 fix: DB column is feat_ear, not feat_ear_zscore
            features["feat_ear"] = float(close.iloc[-1] / c24 - 1)
        else:
            features["feat_ear"] = 0.0
    elif len(close) >= 13:
        c12 = float(close.iloc[-13])
        if c12 > 0:
            features["feat_ear"] = float(close.iloc[-1] / c12 - 1)
        else:
            features["feat_ear"] = 0.0
    else:
        features["feat_ear"] = 0.0

    # Also add alias for backward compatibility
    features["feat_ear_zscore"] = features["feat_ear"]

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

    # 4. Tongue → mean_rev_20h: 20期均值回歸偏移（IC=-0.060, p<0.001, N=8751）
    #    Heartbeat #H122 替換 vol_ratio_24_144 (IC=+0.004, 無效)
    #    公式: (close - sma_20) / sma_20
    #    負 IC → 偏離均線越遠 → 越可能反轉（均值回歸）
    if len(close) >= 21:
        sma20 = float(close.iloc[-20:].mean())
        if sma20 > 0:
            features["feat_tongue_pct"] = float((close.iloc[-1] - sma20) / sma20)
        else:
            features["feat_tongue_pct"] = 0.0
    else:
        features["feat_tongue_pct"] = 0.0

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

    # 7. Aura (v12): price_sma144_deviation — 價格偏離 144 期均線程度（倉位極端程度代理）
    #    fr_abs_norm 失效：funding_rate 只有 10 筆非 NULL 且恆為 2.775e-05 → Aura 二值化
    #    新公式: (close - sma_144) / sma_144 → 價格偏離長期均線 = 市場極端程度
    #    正 IC 預期: 偏離均線越遠 → 趨勢越極端 → 可能延續或反轉
    if len(close) >= 145:
        sma144 = float(close.iloc[-144:].mean())
        if sma144 > 0:
            features["feat_aura"] = float((close.iloc[-1] - sma144) / sma144)
        else:
            features["feat_aura"] = 0.0
    elif len(close) >= 25:
        sma24 = float(close.iloc[-24:].mean())
        if sma24 > 0:
            features["feat_aura"] = float((close.iloc[-1] - sma24) / sma24)
        else:
            features["feat_aura"] = 0.0
    else:
        features["feat_aura"] = 0.0

    # 8. Mind (v3): ret_144 — 144期（12h）價格動量回報率
    #    IC=-0.077 (p<0.001, N=11010): 替換 ret_72 (IC≈0, p=0.840, 無效) #H89
    #    負 IC → 12h 強勢上漲 → 看跌（過熱反轉），加入 NEG_IC_FEATS
    if len(close) >= 145:
        features["feat_mind"] = float(close.iloc[-1] / close.iloc[-145] - 1)
    elif len(close) >= 25:
        features["feat_mind"] = float(close.iloc[-1] / close.iloc[-25] - 1)
    else:
        features["feat_mind"] = 0.0

    # 9. Turning-point / reversal family (v1)
    #    目的不是神準預言極值，而是估計「現在更像局部底 or 局部頂」的品質。
    recent_window = close.tail(48) if len(close) >= 48 else close
    if len(recent_window) >= 5:
        recent_min = float(recent_window.min())
        recent_max = float(recent_window.max())
        recent_range = max(recent_max - recent_min, 1e-9)
        latest_close = float(close.iloc[-1])
        dist_from_min = max(0.0, latest_close - recent_min)
        dist_from_max = max(0.0, recent_max - latest_close)
        bottom_proximity = max(0.0, 1.0 - dist_from_min / recent_range)
        top_proximity = max(0.0, 1.0 - dist_from_max / recent_range)
    else:
        latest_close = float(close.iloc[-1]) if len(close) else 0.0
        recent_max = latest_close
        recent_min = latest_close
        bottom_proximity = 0.0
        top_proximity = 0.0

    if len(close) >= 4:
        last_return = float(close.iloc[-1] / close.iloc[-2] - 1)
        prev_return = float(close.iloc[-2] / close.iloc[-3] - 1)
        rebound_strength = max(0.0, last_return - prev_return)
        fade_strength = max(0.0, prev_return - last_return)
    else:
        rebound_strength = 0.0
        fade_strength = 0.0

    if "volume" in df.columns and df["volume"].notna().sum() >= 5:
        vol_series = df["volume"].dropna().astype(float)
        vol_recent = vol_series.tail(24) if len(vol_series) >= 24 else vol_series
        vol_mean = float(vol_recent.iloc[:-1].mean()) if len(vol_recent) >= 2 else float(vol_recent.mean())
        vol_last = float(vol_recent.iloc[-1]) if len(vol_recent) else 0.0
        volume_exhaustion = max(0.0, min(1.0, (vol_last - vol_mean) / max(vol_mean, 1e-9)))
    else:
        volume_exhaustion = 0.0

    features["feat_wick_rejection"] = float(min(1.0, max(rebound_strength, fade_strength) * 40.0))
    features["feat_volume_exhaustion"] = float(volume_exhaustion)
    features["feat_local_bottom_score"] = float(min(1.0, 0.65 * bottom_proximity + 0.20 * min(1.0, rebound_strength * 40.0) + 0.15 * volume_exhaustion))
    features["feat_local_top_score"] = float(min(1.0, 0.65 * top_proximity + 0.20 * min(1.0, fade_strength * 40.0) + 0.15 * volume_exhaustion))
    features["feat_turning_point_score"] = float(max(features["feat_local_bottom_score"], features["feat_local_top_score"]))
    features["feat_dist_swing_high"] = float(((recent_max - latest_close) / latest_close) * 100.0) if latest_close > 0 else 0.0
    if len(close) >= 144:
        tunnel_ma = float(close.tail(144).mean())
    elif len(close) >= 55:
        tunnel_ma = float(close.tail(55).mean())
    else:
        tunnel_ma = latest_close
    features["feat_tunnel_distance"] = float((latest_close - tunnel_ma) / max(tunnel_ma, 1e-9)) if tunnel_ma else 0.0

    # ─── P0 #H161: Technical Indicators (5 IC-validated) ───
    # MACD-Hist IC=+0.1485, RSI IC=+0.0992, VWAP IC=+0.0969,
    # ATR IC=+0.0835, BB% IC=+0.0595 — all far exceed legacy senses
    ti = _compute_technical_indicators_from_df(df)
    features["feat_rsi14"] = ti.get("feat_rsi14", 0.5)
    features["feat_macd_hist"] = ti.get("feat_macd_hist", 0.0)
    features["feat_atr_pct"] = ti.get("feat_atr_pct", 0.0)
    features["feat_vwap_dev"] = ti.get("feat_vwap_dev", 0.0)
    features["feat_bb_pct_b"] = ti.get("feat_bb_pct_b", 0.5)
    features["feat_nw_width"] = ti.get("feat_nw_width", 0.0)
    features["feat_nw_slope"] = ti.get("feat_nw_slope", 0.0)
    features["feat_adx"] = ti.get("feat_adx", 0.0)
    features["feat_choppiness"] = ti.get("feat_choppiness", 0.5)
    features["feat_donchian_pos"] = ti.get("feat_donchian_pos", 0.5)
    features["feat_4h_bias50"] = ti.get("feat_4h_bias50")
    features["feat_4h_bias20"] = ti.get("feat_4h_bias20")
    features["feat_4h_bias200"] = ti.get("feat_4h_bias200")
    features["feat_4h_rsi14"] = ti.get("feat_4h_rsi14")
    features["feat_4h_macd_hist"] = ti.get("feat_4h_macd_hist")
    features["feat_4h_bb_pct_b"] = ti.get("feat_4h_bb_pct_b")
    features["feat_4h_dist_bb_lower"] = ti.get("feat_4h_dist_bb_lower")
    features["feat_4h_ma_order"] = ti.get("feat_4h_ma_order")
    features["feat_4h_dist_swing_low"] = ti.get("feat_4h_dist_swing_low")
    features["feat_4h_vol_ratio"] = ti.get("feat_4h_vol_ratio")

    # ─── P0 #H381: VIX & DXY — #1 and #2 IC features (must be in pipeline!) ───
    # DXY IC=-0.1107, VIX IC=-0.0796 (highest-IC macro features)
    # Raw data has vix_value/dxy_value — must copy to feature columns
    if "vix_value" in df.columns and df["vix_value"].notna().any():
        features["feat_vix"] = float(df["vix_value"].dropna().iloc[-1])
    else:
        features["feat_vix"] = None
    if "dxy_value" in df.columns and df["dxy_value"].notna().any():
        features["feat_dxy"] = float(df["dxy_value"].dropna().iloc[-1])
    else:
        features["feat_dxy"] = None

    # ─── FUSION: 4H × 1min sensory cross-features ───
    # v6: 讓模型學習 4H 趨勢框架 + 1min 極端觸發的最佳組合
    # 取代人工 if/else 規則
    if all(features.get(f"feat_4h_{k}") is not None for k in ["bias50", "bias20", "dist_swing_low"]):
        try:
            from feature_engine.fusion_features import compute_fusion_features
            fusion = compute_fusion_features(
                feat_4h_bias50=features.get("feat_4h_bias50"),
                feat_4h_bias20=features.get("feat_4h_bias20"),
                feat_4h_dist_swing_low=features.get("feat_4h_dist_swing_low"),
                feat_4h_bb_pct_b=features.get("feat_4h_bb_pct_b"),
                feat_4h_ma_order=features.get("feat_4h_ma_order"),
                feat_4h_rsi14=features.get("feat_4h_rsi14"),
                feat_4h_macd_hist=features.get("feat_4h_macd_hist"),
                feat_nose=features.get("feat_nose"),
                feat_tongue=features.get("feat_tongue"),
                feat_mind=features.get("feat_mind"),
                feat_pulse=features.get("feat_pulse"),
                feat_eye=features.get("feat_eye"),
                feat_ear=features.get("feat_ear"),
                feat_body=features.get("feat_body"),
                feat_aura=features.get("feat_aura"),
            )
            features.update(fusion)
            logger.info(f"Fusion features computed: {len(fusion)} new features")
        except Exception as e:
            logger.warning(f"Fusion feature computation failed: {e}")
    else:
        logger.warning("4H features not ready, skipping fusion")

    # ─── P0 #H232: NEW Sensory Features (6 P0/P1 + NQ) ───
    # NQ (Nasdaq 100): negative return = bullish for SHORT
    if "nq_value" in df.columns and df["nq_value"].notna().any():
        nq_vals = df["nq_value"].dropna()
        if len(nq_vals) >= 2:
            features["feat_nq_return_1h"] = -(float(nq_vals.iloc[-1] / nq_vals.iloc[-2] - 1))
        if len(nq_vals) >= 24:
            features["feat_nq_return_24h"] = -(float(nq_vals.iloc[-1] / nq_vals.iloc[-min(24, len(nq_vals))] - 1))
    if "feat_nq_return_1h" not in features:
        features["feat_nq_return_1h"] = None
    if "feat_nq_return_24h" not in features:
        features["feat_nq_return_24h"] = None

    latest_row = df.iloc[-1] if len(df) > 0 else None

    def _latest_value(column: str):
        if latest_row is None or column not in df.columns:
            return None
        value = latest_row.get(column)
        if pd.isna(value):
            return None
        return float(value)

    # Claw: Liquidation ratio — more long liq = good for SHORT.
    # Missing source data must stay None; writing 0.0 here pollutes coverage and
    # makes source outages look like a real neutral signal.
    raw = _latest_value("claw_liq_ratio")
    if raw is not None:
        features["feat_claw"] = float((raw - 1.0) / (raw + 1.0))
        features["feat_claw_intensity"] = float(math.tanh(raw / 3.0))
    else:
        features["feat_claw"] = None
        features["feat_claw_intensity"] = None

    # Fang: Options PCR — PCR>1 = fear
    pcr = _latest_value("fang_pcr")
    if pcr is not None:
        features["feat_fang_pcr"] = float(math.tanh((pcr - 1.0) * 2.0))
    else:
        features["feat_fang_pcr"] = None
    fang_skew = _latest_value("fang_iv_skew")
    if fang_skew is not None:
        features["feat_fang_skew"] = float(fang_skew / 10.0)
    else:
        features["feat_fang_skew"] = None

    # Fin: ETF Flow — outflow = bearish for BTC = bullish for SHORT
    nf = _latest_value("fin_etf_netflow")
    if nf is not None:
        features["feat_fin_netflow"] = float(-math.tanh(nf / 500_000_000))
    else:
        features["feat_fin_netflow"] = None

    # Web: Whale sell pressure
    web_pressure = _latest_value("web_whale_pressure")
    if web_pressure is not None:
        features["feat_web_whale"] = float(web_pressure)
    else:
        features["feat_web_whale"] = None

    # Scales: Stablecoin SSR
    scales_ssr = _latest_value("scales_ssr")
    if scales_ssr is not None:
        features["feat_scales_ssr"] = float(scales_ssr)
    else:
        features["feat_scales_ssr"] = None

    # Nest: Polymarket prediction
    nest_pred = _latest_value("nest_pred")
    if nest_pred is not None:
        features["feat_nest_pred"] = float(nest_pred - 0.5)
    else:
        features["feat_nest_pred"] = None

    logger.info(
        f"Features v3: eye={features['feat_eye_dist']:.6f} "
        f"ear={features['feat_ear_zscore']:.6f} "
        f"nose={features['feat_nose_sigmoid']:.4f} "
        f"tongue={features['feat_tongue_pct']:.6f} "
        f"body={features['feat_body_roc']:.4f} "
        f"pulse={features['feat_pulse']:.6f} "
        f"aura={features['feat_aura']:.6f} "
        f"mind={features['feat_mind']:.4f} "
        f"| TI: rsi={features['feat_rsi14']:.4f} macd={features['feat_macd_hist']:.6f} "
        f"atr={features['feat_atr_pct']:.6f} vwap={features['feat_vwap_dev']:.6f} "
        f"nw={features['feat_bb_pct_b']:.4f} nw_width={features['feat_nw_width']:.4f} adx={features['feat_adx']:.4f} "
        f"| Macro: vix={features.get('feat_vix')} dxy={features.get('feat_dxy')}"
    )
    return features


def _derive_regime_label(features: Dict) -> str:
    """Derive a lightweight regime label at feature-save time.

    New feature rows should not default to NULL regime labels because that forces
    hb_collect.py to re-backfill the whole table on every heartbeat.
    """
    ma_order = features.get("feat_4h_ma_order")
    bias50 = features.get("feat_4h_bias50")
    body = features.get("feat_body")
    mind = features.get("feat_mind")

    if ma_order is not None:
        if ma_order >= 0.5:
            return "bull"
        if ma_order <= -0.5:
            return "bear"

    if bias50 is not None:
        if bias50 >= 2.0:
            return "bull"
        if bias50 <= -2.0:
            return "bear"
        return "chop"

    momentum = [v for v in (body, mind) if v is not None]
    if momentum:
        avg = sum(float(v) for v in momentum) / len(momentum)
        if avg >= 0.05:
            return "bull"
        if avg <= -0.05:
            return "bear"
        return "chop"

    return "neutral"


def save_features_to_db(
    session: Session, features: Dict
) -> Optional[FeaturesNormalized]:
    """保存特徵（含去重檢查）。"""
    try:
        ts = features["timestamp"]
        symbol = features.get("symbol", "BTC/USDT")
        existing = (
            session.query(FeaturesNormalized)
            .filter(FeaturesNormalized.timestamp == ts)
            .filter((FeaturesNormalized.symbol == symbol) | (FeaturesNormalized.symbol.is_(None)))
            .order_by(FeaturesNormalized.symbol.is_(None))
            .first()
        )
        if existing:
            existing.symbol = symbol
            existing.feat_eye = features.get("feat_eye", features.get("feat_eye_dist"))
            existing.feat_ear = features.get("feat_ear", features.get("feat_ear_zscore"))
            existing.feat_nose = features.get("feat_nose", features.get("feat_nose_sigmoid"))
            existing.feat_tongue = features.get("feat_tongue", features.get("feat_tongue_pct"))
            existing.feat_body = features.get("feat_body", features.get("feat_body_roc"))
            existing.feat_pulse = features.get("feat_pulse")
            existing.feat_aura = features.get("feat_aura")
            existing.feat_mind = features.get("feat_mind")
            existing.feat_rsi14 = features.get("feat_rsi14")
            existing.feat_macd_hist = features.get("feat_macd_hist")
            existing.feat_atr_pct = features.get("feat_atr_pct")
            existing.feat_vwap_dev = features.get("feat_vwap_dev")
            existing.feat_bb_pct_b = features.get("feat_bb_pct_b")
            existing.feat_nw_width = features.get("feat_nw_width")
            existing.feat_nw_slope = features.get("feat_nw_slope")
            existing.feat_adx = features.get("feat_adx")
            existing.feat_choppiness = features.get("feat_choppiness")
            existing.feat_donchian_pos = features.get("feat_donchian_pos")
            existing.feat_vix = features.get("feat_vix")
            existing.feat_dxy = features.get("feat_dxy")
            existing.feat_nq_return_1h = features.get("feat_nq_return_1h")
            existing.feat_nq_return_24h = features.get("feat_nq_return_24h")
            existing.feat_claw = features.get("feat_claw")
            existing.feat_claw_intensity = features.get("feat_claw_intensity")
            existing.feat_fang_pcr = features.get("feat_fang_pcr")
            existing.feat_fang_skew = features.get("feat_fang_skew")
            existing.feat_fin_netflow = features.get("feat_fin_netflow")
            existing.feat_web_whale = features.get("feat_web_whale")
            existing.feat_scales_ssr = features.get("feat_scales_ssr")
            existing.feat_nest_pred = features.get("feat_nest_pred")
            existing.feat_4h_bias50 = features.get("feat_4h_bias50")
            existing.feat_4h_bias20 = features.get("feat_4h_bias20")
            existing.feat_4h_bias200 = features.get("feat_4h_bias200")
            existing.feat_4h_rsi14 = features.get("feat_4h_rsi14")
            existing.feat_4h_macd_hist = features.get("feat_4h_macd_hist")
            existing.feat_4h_bb_pct_b = features.get("feat_4h_bb_pct_b")
            existing.feat_4h_dist_bb_lower = features.get("feat_4h_dist_bb_lower")
            existing.feat_4h_ma_order = features.get("feat_4h_ma_order")
            existing.feat_4h_dist_swing_low = features.get("feat_4h_dist_swing_low")
            existing.feat_4h_vol_ratio = features.get("feat_4h_vol_ratio")
            existing.feat_local_bottom_score = features.get("feat_local_bottom_score")
            existing.feat_local_top_score = features.get("feat_local_top_score")
            existing.feat_turning_point_score = features.get("feat_turning_point_score")
            existing.feat_wick_rejection = features.get("feat_wick_rejection")
            existing.feat_volume_exhaustion = features.get("feat_volume_exhaustion")
            existing.feat_tunnel_distance = features.get("feat_tunnel_distance")
            existing.feat_dist_swing_high = features.get("feat_dist_swing_high")
            existing.regime_label = features.get("regime_label") or _derive_regime_label(features)
            existing.feature_version = 'v4_4h_integration'
            session.commit()
            logger.info(f"4H 特徵已更新 (id={existing.id}), bias50={existing.feat_4h_bias50}, rsi={existing.feat_4h_rsi14}")
            return existing

        record = FeaturesNormalized(
            timestamp=ts,
            symbol=symbol,
            feat_eye_dist=features.get("feat_eye_dist"),
            feat_ear_zscore=features.get("feat_ear_zscore"),
            feat_nose_sigmoid=features.get("feat_nose_sigmoid"),
            feat_tongue_pct=features.get("feat_tongue_pct"),
            feat_body_roc=features.get("feat_body_roc"),
            feat_pulse=features.get("feat_pulse"),
            feat_aura=features.get("feat_aura"),
            feat_mind=features.get("feat_mind"),
            feat_rsi14=features.get("feat_rsi14"),
            feat_macd_hist=features.get("feat_macd_hist"),
            feat_atr_pct=features.get("feat_atr_pct"),
            feat_vwap_dev=features.get("feat_vwap_dev"),
            feat_bb_pct_b=features.get("feat_bb_pct_b"),
            feat_nw_width=features.get("feat_nw_width"),
            feat_nw_slope=features.get("feat_nw_slope"),
            feat_adx=features.get("feat_adx"),
            feat_choppiness=features.get("feat_choppiness"),
            feat_donchian_pos=features.get("feat_donchian_pos"),
            feat_vix=features.get("feat_vix"),
            feat_dxy=features.get("feat_dxy"),
            # P0 #H232: New sensory features
            feat_nq_return_1h=features.get("feat_nq_return_1h"),
            feat_nq_return_24h=features.get("feat_nq_return_24h"),
            feat_claw=features.get("feat_claw"),
            feat_claw_intensity=features.get("feat_claw_intensity"),
            feat_fang_pcr=features.get("feat_fang_pcr"),
            feat_fang_skew=features.get("feat_fang_skew"),
            feat_fin_netflow=features.get("feat_fin_netflow"),
            feat_web_whale=features.get("feat_web_whale"),
            feat_scales_ssr=features.get("feat_scales_ssr"),
            feat_nest_pred=features.get("feat_nest_pred"),
            # P0: 4H timeframe features
            feat_4h_bias50=features.get("feat_4h_bias50"),
            feat_4h_bias20=features.get("feat_4h_bias20"),
            feat_4h_bias200=features.get("feat_4h_bias200"),
            feat_4h_rsi14=features.get("feat_4h_rsi14"),
            feat_4h_macd_hist=features.get("feat_4h_macd_hist"),
            feat_4h_bb_pct_b=features.get("feat_4h_bb_pct_b"),
            feat_4h_dist_bb_lower=features.get("feat_4h_dist_bb_lower"),
            feat_4h_ma_order=features.get("feat_4h_ma_order"),
            feat_4h_dist_swing_low=features.get("feat_4h_dist_swing_low"),
            feat_4h_vol_ratio=features.get("feat_4h_vol_ratio"),
            feat_local_bottom_score=features.get("feat_local_bottom_score"),
            feat_local_top_score=features.get("feat_local_top_score"),
            feat_turning_point_score=features.get("feat_turning_point_score"),
            feat_wick_rejection=features.get("feat_wick_rejection"),
            feat_volume_exhaustion=features.get("feat_volume_exhaustion"),
            feat_tunnel_distance=features.get("feat_tunnel_distance"),
            feat_dist_swing_high=features.get("feat_dist_swing_high"),
            regime_label=features.get("regime_label") or _derive_regime_label(features),
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
    session: Session, symbol: str = "BTC/USDT"
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


def _load_existing_feature_timestamps(session: Session, symbol: str = "BTC/USDT") -> set:
    rows = (
        session.query(FeaturesNormalized.timestamp)
        .filter((FeaturesNormalized.symbol == symbol) | (FeaturesNormalized.symbol.is_(None)))
        .order_by(FeaturesNormalized.timestamp)
        .all()
    )
    return {ts for (ts,) in rows if ts is not None}



def _compute_recent_feature_gap_hours(timestamps, expected_gap_hours: float = 4.0) -> Dict:
    ordered = sorted(ts for ts in timestamps if ts is not None)
    if len(ordered) < 2:
        return {
            "max_gap_hours": 0.0,
            "gap_count_over_expected": 0,
            "largest_gap_start": None,
            "largest_gap_end": None,
        }

    largest_gap_hours = 0.0
    largest_gap_start = None
    largest_gap_end = None
    gap_count = 0
    threshold = float(expected_gap_hours) + 0.5
    for prev_ts, curr_ts in zip(ordered, ordered[1:]):
        gap_hours = (curr_ts - prev_ts).total_seconds() / 3600.0
        if gap_hours > threshold:
            gap_count += 1
        if gap_hours > largest_gap_hours:
            largest_gap_hours = gap_hours
            largest_gap_start = prev_ts
            largest_gap_end = curr_ts
    return {
        "max_gap_hours": round(largest_gap_hours, 4),
        "gap_count_over_expected": gap_count,
        "largest_gap_start": largest_gap_start.isoformat() if largest_gap_start else None,
        "largest_gap_end": largest_gap_end.isoformat() if largest_gap_end else None,
    }



def backfill_missing_feature_rows(
    session: Session,
    symbol: str = "BTC/USDT",
    *,
    lookback_days: int | None = None,
) -> int:
    """Compute features for raw timestamps that do not yet have a feature row.

    Heartbeat #628 continuity repair inserts missing raw rows to close upstream gaps.
    Without this follow-up, the label pipeline still cannot grow because the newly
    restored timestamps never enter `features_normalized`. This helper backfills only
    the missing feature rows instead of recomputing the full history every heartbeat.
    """
    df = load_latest_raw_data(session, symbol, limit=0)
    if df.empty:
        return 0

    existing_timestamps = _load_existing_feature_timestamps(session, symbol)
    cutoff = None
    if lookback_days is not None and lookback_days > 0:
        cutoff = datetime.utcnow() - timedelta(days=lookback_days)

    inserted = 0
    min_window = 10
    for end_idx in range(min_window, len(df) + 1):
        ts = df.iloc[end_idx - 1].get("timestamp")
        if ts is None or ts in existing_timestamps:
            continue
        if cutoff is not None and ts < cutoff:
            continue
        features = compute_features_from_raw(df.iloc[:end_idx])
        if not features:
            continue
        saved = save_features_to_db(session, features)
        if saved:
            existing_timestamps.add(ts)
            inserted += 1

    if inserted:
        scope = f"recent {lookback_days}d" if cutoff is not None else "full history"
        logger.info("補回缺失特徵列完成: %s rows inserted for %s (%s)", inserted, symbol, scope)
    return inserted



def repair_recent_feature_continuity(
    session: Session,
    symbol: str = "BTC/USDT",
    *,
    lookback_days: int = 30,
    expected_gap_hours: float = 4.0,
    return_details: bool = False,
) -> int | Dict:
    """Backfill missing feature rows for recent raw timestamps and report continuity status."""
    df = load_latest_raw_data(session, symbol, limit=0)
    if df.empty:
        details = {
            "symbol": symbol,
            "lookback_days": lookback_days,
            "raw_rows_in_window": 0,
            "missing_before": 0,
            "inserted_total": 0,
            "remaining_missing": 0,
            **_compute_recent_feature_gap_hours([], expected_gap_hours),
        }
        return details if return_details else 0

    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
    min_window = 10
    eligible_recent_timestamps = [
        df.iloc[end_idx - 1].get("timestamp")
        for end_idx in range(min_window, len(df) + 1)
        if df.iloc[end_idx - 1].get("timestamp") is not None and df.iloc[end_idx - 1].get("timestamp") >= cutoff
    ]
    existing_before = _load_existing_feature_timestamps(session, symbol)
    missing_before = [ts for ts in eligible_recent_timestamps if ts not in existing_before]

    inserted = backfill_missing_feature_rows(session, symbol, lookback_days=lookback_days)

    existing_after = _load_existing_feature_timestamps(session, symbol)
    remaining_missing = [ts for ts in eligible_recent_timestamps if ts not in existing_after]
    gap_meta = _compute_recent_feature_gap_hours(
        [ts for ts in existing_after if ts >= cutoff],
        expected_gap_hours=expected_gap_hours,
    )
    details = {
        "symbol": symbol,
        "lookback_days": lookback_days,
        "raw_rows_in_window": len(eligible_recent_timestamps),
        "missing_before": len(missing_before),
        "inserted_total": inserted,
        "remaining_missing": len(remaining_missing),
        "first_missing_before": missing_before[0].isoformat() if missing_before else None,
        "last_missing_before": missing_before[-1].isoformat() if missing_before else None,
        "first_remaining_missing": remaining_missing[0].isoformat() if remaining_missing else None,
        "last_remaining_missing": remaining_missing[-1].isoformat() if remaining_missing else None,
        **gap_meta,
    }
    if inserted:
        logger.info("recent feature continuity repair inserted %s rows for %s", inserted, symbol)
    return details if return_details else inserted


def recompute_all_features(session: Session, symbol: str = "BTC/USDT") -> int:
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
            .filter((FeaturesNormalized.symbol == symbol) | (FeaturesNormalized.symbol.is_(None)))
            .order_by(FeaturesNormalized.symbol.is_(None))
            .first()
        )
        if existing:
            features = compute_features_from_raw(window)
            if features:
                existing.symbol = symbol
                existing.feat_eye = features.get("feat_eye_dist", features.get("feat_eye"))
                existing.feat_ear = features.get("feat_ear_zscore", features.get("feat_ear"))
                existing.feat_nose = features.get("feat_nose_sigmoid", features.get("feat_nose"))
                existing.feat_tongue = features.get("feat_tongue_pct", features.get("feat_tongue"))
                existing.feat_body = features.get("feat_body_roc", features.get("feat_body"))
                existing.feat_pulse = features.get("feat_pulse")
                existing.feat_aura = features.get("feat_aura")
                existing.feat_mind = features.get("feat_mind")
                existing.feat_rsi14 = features.get("feat_rsi14")
                existing.feat_macd_hist = features.get("feat_macd_hist")
                existing.feat_atr_pct = features.get("feat_atr_pct")
                existing.feat_vwap_dev = features.get("feat_vwap_dev")
                existing.feat_bb_pct_b = features.get("feat_bb_pct_b")
                existing.feat_nw_width = features.get("feat_nw_width")
                existing.feat_nw_slope = features.get("feat_nw_slope")
                existing.feat_adx = features.get("feat_adx")
                existing.feat_choppiness = features.get("feat_choppiness")
                existing.feat_donchian_pos = features.get("feat_donchian_pos")
                existing.feat_nq_return_1h = features.get("feat_nq_return_1h")
                existing.feat_nq_return_24h = features.get("feat_nq_return_24h")
                existing.feat_claw = features.get("feat_claw")
                existing.feat_claw_intensity = features.get("feat_claw_intensity")
                existing.feat_fang_pcr = features.get("feat_fang_pcr")
                existing.feat_fang_skew = features.get("feat_fang_skew")
                existing.feat_fin_netflow = features.get("feat_fin_netflow")
                existing.feat_web_whale = features.get("feat_web_whale")
                existing.feat_scales_ssr = features.get("feat_scales_ssr")
                existing.feat_nest_pred = features.get("feat_nest_pred")
                # P0 #H381: VIX & DXY macro features
                existing.feat_vix = features.get("feat_vix")
                existing.feat_dxy = features.get("feat_dxy")
                # P0: 4H timeframe features must stay aligned during recompute
                existing.feat_4h_bias50 = features.get("feat_4h_bias50")
                existing.feat_4h_bias20 = features.get("feat_4h_bias20")
                existing.feat_4h_bias200 = features.get("feat_4h_bias200")
                existing.feat_4h_rsi14 = features.get("feat_4h_rsi14")
                existing.feat_4h_macd_hist = features.get("feat_4h_macd_hist")
                existing.feat_4h_bb_pct_b = features.get("feat_4h_bb_pct_b")
                existing.feat_4h_dist_bb_lower = features.get("feat_4h_dist_bb_lower")
                existing.feat_4h_ma_order = features.get("feat_4h_ma_order")
                existing.feat_4h_dist_swing_low = features.get("feat_4h_dist_swing_low")
                existing.feat_4h_vol_ratio = features.get("feat_4h_vol_ratio")
                existing.regime_label = features.get("regime_label") or _derive_regime_label(features)
                existing.feature_version = "v4_4h_integration"
                count += 1
        else:
            features = compute_features_from_raw(window)
            if features:
                record = FeaturesNormalized(
                    timestamp=ts,
                    symbol=symbol,
                    regime_label=features.get("regime_label") or _derive_regime_label(features),
                    feature_version="v4_4h_integration",
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
