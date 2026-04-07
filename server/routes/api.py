     1|"""
     2|REST API 路由 v3.0 — 多感官策略回測引擎
     3|"""
     4|import ccxt
     5|import math
     6|import json
     7|from fastapi import APIRouter, Query, HTTPException
     8|from pydantic import BaseModel
     9|from typing import Optional, List, Dict, Any
    10|from datetime import datetime, timedelta
    11|
    12|from server.dependencies import get_db, get_config, is_automation_enabled, set_automation_enabled
    13|from server.senses import get_engine
    14|from database.models import TradeHistory, RawMarketData, FeaturesNormalized
    15|from utils.logger import setup_logger
    16|
    17|logger = setup_logger(__name__)
    18|
    19|router = APIRouter()
    20|
    21|# ─── Models ───
    22|class TradeRequest(BaseModel):
    23|    side: str
    24|    symbol: str = "BTCUSDT"
    25|    qty: float = 0.001
    26|
    27|class SenseConfigUpdate(BaseModel):
    28|    sense: str
    29|    module: str
    30|    enabled: Optional[bool] = None
    31|    weight: Optional[float] = None
    32|
    33|# ─── Core Helpers ───
    34|def _calc_ma_at(data, period, i):
    35|    s = max(0, i - period + 1)
    36|    n = i - s + 1
    37|    return sum(data[s:i + 1]) / n if n > 0 else 0
    38|
    39|def _calc_max_dd(eq):
    40|    """計算最大回撤"""
    41|    if not eq:
    42|        return 0
    43|    pk = eq[0]
    44|    mdd = 0
    45|    for v in eq:
    46|        if v > pk:
    47|            pk = v
    48|        dd = (pk - v) / pk
    49|        if dd > mdd:
    50|            mdd = dd
    51|    return mdd
    52|
    53|# ─── API Endpoints ───
    54|
    55|@router.get("/status")
    56|async def api_status():
    57|    cfg = get_config()
    58|    return {
    59|        "automation": is_automation_enabled(),
    60|        "dry_run": cfg.get("trading", {}).get("dry_run", True),
    61|        "symbol": cfg.get("trading", {}).get("symbol", "BTCUSDT"),
    62|        "timestamp": datetime.utcnow().isoformat() + "Z",
    63|    }
    64|
    65|@router.get("/senses")
    66|async def api_senses():
    67|    engine = get_engine()
    68|    scores = engine.calculate_all_scores()
    69|    full_data = engine.get_latest_full_data()
    70|    advice = engine.generate_advice(scores)
    71|    return {
    72|        "senses": engine.get_senses_status(),
    73|        "scores": scores,
    74|        "raw": full_data.get("raw", {}),         # 4H raw values for dashboard
    75|        "recommendation": advice,
    76|    }
    77|
    78|@router.get("/senses/config")
    79|async def api_senses_cfg():
    80|    return get_engine().get_config()
    81|
    82|@router.put("/senses/config")
    83|async def api_put_senses(update: SenseConfigUpdate):
    84|    engine = get_engine()
    85|    updates = {}
    86|    if update.enabled is not None: updates["enabled"] = update.enabled
    87|    if update.weight is not None: updates["weight"] = update.weight
    88|    ok = engine.update_sense_config(update.sense, update.module, updates)
    89|    if not ok: raise HTTPException(status_code=400, detail="無效感官或模組")
    90|    return {"config": engine.get_config(), "scores": engine.calculate_all_scores()}
    91|
    92|@router.get("/recommendation")
    93|async def api_rec():
    94|    engine = get_engine()
    95|    return engine.generate_advice(engine.calculate_all_scores())
    96|
    97|@router.get("/chart/klines")
    98|async def api_klines(symbol: str = "BTCUSDT", interval: str = "1h", limit: int = 500):
    99|    try:
   100|        exchange = ccxt.binance()
   101|        ohlcv = exchange.fetch_ohlcv(symbol, interval, limit=limit)
   102|        candles = [{"time": int(b[0] / 1000), "open": b[1], "high": b[2], "low": b[3], "close": b[4], "volume": b[5]} for b in ohlcv]
   103|        closes = [b[4] for b in ohlcv]
   104|        indicators = {"ma20": [], "ma60": [], "rsi": [], "macd": None, "signal": [], "histogram": []}
   105|        for i in range(len(closes)):
   106|            indicators["ma20"].append(round(_calc_ma_at(closes, 20, i), 2))
   107|            indicators["ma60"].append(round(_calc_ma_at(closes, 60, i), 2))
   108|        if len(closes) >= 15:
   109|            avg_g = [0] * len(closes); avg_l = [0] * len(closes)
   110|            for i in range(1, len(closes)):
   111|                d = closes[i] - closes[i - 1]
   112|                if i < 14:
   113|                    if d > 0: avg_g[i] = d
   114|                    if d < 0: avg_l[i] = -d
   115|                else:
   116|                    avg_g[i] = (avg_g[i - 1] * 13 + max(d, 0)) / 14
   117|                    avg_l[i] = (avg_l[i - 1] * 13 + max(-d, 0)) / 14
   118|            indicators["rsi"] = [round(100 - 100 / (1 + (g / l if l > 0 else 999)), 1) if g + l > 0 else 50 for g, l in zip(avg_g, avg_l)]
   119|        # MACD (12, 26, 9)
   120|        if len(closes) >= 26:
   121|            def _ema(v, period):
   122|                k = 2 / (period + 1); r = [v[0]]
   123|                for x in v[1:]: r.append(r[-1] * (1 - k) + x * k)
   124|                return r
   125|            ema12 = _ema(closes, 12); ema26 = _ema(closes, 26)
   126|            macd_l = [f - s for f, s in zip(ema12, ema26)]
   127|            signal_l = _ema(macd_l[26 - 1:], 9)
   128|            signal_l = [None] * (26 - 1) + signal_l
   129|            indicators["macd"] = [round(m, 4) if m is not None else None for m in macd_l]
   130|            indicators["signal"] = [round(s, 4) if s is not None else None for s in signal_l]
   131|            indicators["histogram"] = [round(m - s, 4) if (m is not None and s is not None) else None for m, s in zip(macd_l, signal_l)]
   132|        return {"symbol": symbol, "candles": candles, "indicators": indicators}
   133|    except Exception as e:
   134|        raise HTTPException(status_code=500, detail=str(e))
   135|
   136|@router.get("/backtest")
   137|async def api_backtest(days: int = Query(default=30, ge=1, le=365)):
   138|    """【多感官策略回測】基於 XGBoost 信心分數的真實回測"""
   139|    try:
   140|        symbol = "BTCUSDT"
   141|        interval = "4h" if days <= 7 else "1d"
   142|        limit = max(int(days * 6), 20)
   143|        exchange = ccxt.binance()
   144|        ohlcv = exchange.fetch_ohlcv(symbol, interval, limit=limit)
   145|        if not ohlcv or len(ohlcv) < 20:
   146|            return {"error": "數據不足", "total_trades": 0, "equity_curve": [], "trades": []}
   147|
   148|        # 1. 讀取 DB 中對應時間區間的特徵
   149|        db = get_db()
   150|        start = datetime.fromtimestamp(ohlcv[0][0] / 1000)
   151|        features = db.query(FeaturesNormalized).filter(
   152|            FeaturesNormalized.timestamp >= start
   153|        ).order_by(FeaturesNormalized.timestamp).all()
   154|        feat_map = {}
   155|        for f in features:
   156|            feat_map[int(f.timestamp.timestamp())] = f
   157|
   158|        # 2. 執行多感官策略回測
   159|        initial = 10000.0
   160|        equity = initial; position = 0.0; entry_price = 0.0
   161|        equity_curve = []; trades = []
   162|        threshold = 0.50  # 買入閾值 (normalized 0~1)
   163|        exit_thresh = 0.45  # 賣出閾值
   164|        stop_p = 0.03  # 3% 止損
   165|
   166|        for bar in ohlcv:
   167|            t, o, h, l, c = bar[0], bar[1], bar[2], bar[3], bar[4]
   168|            dt = int(t / 1000)
   169|            price = c
   170|            # 找最近的特徵 (2小時內)
   171|            feat = None; min_diff = 999999
   172|            for ft, f in feat_map.items():
   173|                d = abs(ft - dt)
   174|                if d < min_diff: min_diff = d; feat = f
   175|            if not feat or min_diff > 2 * 3600:
   176|                # 無特徵時繼續觀察但更新權益
   177|                equity_curve.append({"timestamp": datetime.fromtimestamp(dt).isoformat() + "Z", "equity": round(equity + (position * price if position else 0), 2)})
   178|                continue
   179|
   180|            # 計算多感官綜合分數 (0~1)
   181|            vals = [feat.feat_eye_dist, feat.feat_ear_zscore, feat.feat_nose_sigmoid, feat.feat_tongue_pct, feat.feat_body_roc]
   182|            valid = [v for v in vals if v is not None]
   183|            if not valid: continue
   184|            # Normalize: features are -1~1, convert to 0~1
   185|            normed = [(v + 1) / 2 for v in valid]
   186|            score = sum(normed) / len(normed)
   187|
   188|            # 止損
   189|            if position > 0 and price <= entry_price * (1 - stop_p):
   190|                pnl = (price - entry_price) * position
   191|                equity += pnl
   192|                trades.append({"timestamp": datetime.fromtimestamp(dt).isoformat() + "Z", "action": "sell", "price": round(price, 2), "amount": position, "pnl": round(pnl, 2), "reason": "stop_loss"})
   193|                position = 0
   194|
   195|            # 策略邏輯
   196|            if score >= threshold and position == 0:
   197|                position = (equity * 0.05) / price
   198|                entry_price = price
   199|            elif score < exit_thresh and position > 0:
   200|                pnl = (price - entry_price) * position
   201|                equity += pnl
   202|                trades.append({"timestamp": datetime.fromtimestamp(dt).isoformat() + "Z", "action": "sell", "price": round(price, 2), "amount": position, "pnl": round(pnl, 2), "reason": "signal_exit"})
   203|                position = 0
   204|
   205|            equity_curve.append({"timestamp": datetime.fromtimestamp(dt).isoformat() + "Z", "equity": round(equity + (position * price if position else 0), 2)})
   206|
   207|        if position > 0:
   208|            pnl = (c - entry_price) * position
   209|            equity += pnl
   210|            trades.append({"timestamp": datetime.fromtimestamp(ohlcv[-1][0] / 1000).isoformat() + "Z", "action": "sell", "price": round(c, 2), "amount": position, "pnl": round(pnl, 2), "reason": "end"})
   211|
   212|        win = [t for t in trades if t["pnl"] > 0]
   213|        aw = sum(t["pnl"] for t in win) / max(len(win), 1)
   214|        al = abs(sum(t["pnl"] for t in trades if t["pnl"] < 0)) / max(len(trades) - len(win), 1)
   215|        return {
   216|            "final_equity": round(equity, 2), "initial_capital": initial,
   217|            "total_trades": len(trades), "win_rate": round(len(win) / max(len(trades), 1) * 100, 1),
   218|            "profit_loss_ratio": round(aw / max(al, 0.01), 2),
   219|            "max_drawdown": round(_calc_max_dd([e["equity"] for e in equity_curve]) * 100, 2),
   220|            "total_return": round((equity - initial) / initial * 100, 2),
   221|            "equity_curve": equity_curve[-200:], "trades": trades[-50:]
   222|        }
   223|    except Exception as e:
   224|        logger.error(f"Backtest failed: {e}")
   225|        import traceback; traceback.print_exc()
   226|        return {"error": str(e), "total_trades": 0, "equity_curve": [], "trades": []}
   227|
   228|# ─── Feature Key Map ───
   229|# DB column → clean API key that frontend expects
   230|FEATURE_KEY_MAP = {
   231|    # 8 Core
   232|    'feat_eye': 'eye',
   233|    'feat_ear': 'ear',
   234|    'feat_nose': 'nose',
   235|    'feat_tongue': 'tongue',
   236|    'feat_body': 'body',
   237|    'feat_pulse': 'pulse',
   238|    'feat_aura': 'aura',
   239|    'feat_mind': 'mind',
   240|    # Macro
   241|    'feat_vix': 'vix',
   242|    'feat_dxy': 'dxy',
   243|    # Technical
   244|    'feat_rsi14': 'rsi14',
   245|    'feat_macd_hist': 'macd_hist',
   246|    'feat_atr_pct': 'atr_pct',
   247|    'feat_vwap_dev': 'vwap_dev',
   248|    'feat_bb_pct_b': 'bb_pct_b',
   249|    # P0/P1 (sparse)
   250|    'feat_nq_return_1h': 'nq_return_1h',
   251|    'feat_nq_return_24h': 'nq_return_24h',
   252|    'feat_claw': 'claw',
   253|    'feat_claw_intensity': 'claw_intensity',
   254|    'feat_fang_pcr': 'fang_pcr',
   255|    'feat_fang_skew': 'fang_skew',
   256|    'feat_fin_netflow': 'fin_netflow',
   257|    'feat_web_whale': 'web_whale',
   258|    'feat_scales_ssr': 'scales_ssr',
   259|    'feat_nest_pred': 'nest_pred',
   260|    # 4H Distance Features
   261|    'feat_4h_bias50': '4h_bias50',
   262|    'feat_4h_bias20': '4h_bias20',
   263|    'feat_4h_rsi14': '4h_rsi14',
   264|    'feat_4h_macd_hist': '4h_macd_hist',
   265|    'feat_4h_bb_pct_b': '4h_bb_pct_b',
   266|    'feat_4h_ma_order': '4h_ma_order',
   267|    'feat_4h_dist_swing_low': '4h_dist_sl',
   268|    'feat_4h_dist_swing_high': '4h_dist_sh',
   269|}
   270|
   271|# Reverse map: clean key → DB column
   272|REVERSE_KEY_MAP = {v: k for k, v in FEATURE_KEY_MAP.items()}
   273|
   274|# ─── ECDF Normalization ───
   275|# Pre-computed p5/p95 anchors from full DB data. Updated by backfill script.
   276|_ECDF_ANCHORS = {
   277|    # 8 Core: from actual DB distributions
   278|    'feat_eye': (-4.5, 4.5),
   279|    'feat_ear': (-0.0005, 0.0005),
   280|    'feat_nose': (0.15, 0.80),
   281|    'feat_tongue': (-0.001, 0.001),
   282|    'feat_body': (-1.8, 1.3),
   283|    'feat_pulse': (0.0, 0.99),
   284|    'feat_aura': (-0.003, 0.003),
   285|    'feat_mind': (-0.006, 0.004),
   286|    # Macro
   287|    'feat_vix': (12.0, 35.0),
   288|    'feat_dxy': (95.0, 110.0),
   289|    # Technical
   290|    'feat_rsi14': (0.1, 0.85),
   291|    'feat_macd_hist': (-0.0005, 0.0005),
   292|    'feat_atr_pct': (0.005, 0.03),
   293|    'feat_vwap_dev': (-0.5, 0.5),
   294|    'feat_bb_pct_b': (0.0, 1.0),
   295|    # 4H Distance Features [%]
   296|    'feat_4h_bias50': (-15.0, 10.0),
   297|    'feat_4h_bias20': (-10.0, 10.0),
   298|    'feat_4h_rsi14': (10.0, 90.0),
   299|    'feat_4h_macd_hist': (-1500.0, 1500.0),
   300|    'feat_4h_bb_pct_b': (-0.5, 1.5),
   301|    'feat_4h_ma_order': (-1.5, 1.5),
   302|    'feat_4h_dist_swing_low': (-25.0, 20.0),
   303|}
   304|
   305|
   306|def normalize_for_api(raw_val: float | None, db_key: str) -> float | None:
   307|    """Normalize feature using ECDF anchors (not sigmoid!).
   308|    Returns 0.0~1.0 where 0.05 = p5, 0.95 = p95.
   309|    This preserves actual signal differences instead of compressing to ~0.5.
   310|    """
   311|    if raw_val is None:
   312|        return None
   313|
   314|    anchors = _ECDF_ANCHORS.get(db_key)
   315|    if not anchors:
   316|        # Fallback: clamp to [-1, 1] and map to 0~1
   317|        return max(0.0, min(1.0, (raw_val + 1) / 2))
   318|
   319|    p5, p95 = anchors
   320|    span = p95 - p5
   321|    if span < 1e-10:
   322|        return 0.5
   323|
   324|    clamped = max(p5, min(p95, raw_val))
   325|    return round(0.05 + 0.90 * (clamped - p5) / span, 4)
   326|
   327|
   328|@router.get("/features")
   329|async def api_features(days: int = Query(default=7, ge=1, le=90)):
   330|    """返回全部 22+ 特徵的時間序列資料（正確 key mapping + ECDF 正規化）"""
   331|    db = get_db()
   332|    since = datetime.utcnow() - timedelta(days=days)
   333|    rows = (
   334|        db.query(FeaturesNormalized)
   335|        .filter(FeaturesNormalized.timestamp >= since)
   336|        .order_by(FeaturesNormalized.timestamp)
   337|        .all()
   338|    )
   339|    result = []
   340|    for r in rows:
   341|        obj = {"timestamp": r.timestamp.isoformat() if r.timestamp else None}
   342|        for db_key, clean_key in FEATURE_KEY_MAP.items():
   343|            raw_val = getattr(r, db_key, None)
   344|            obj[clean_key] = normalize_for_api(raw_val, db_key)
   345|        result.append(obj)
   346|    return result
   347|
   348|
   349|@router.get("/model/stats")
   350|async def api_model_stats():
   351|    """返回模型準確率、IC 值等統計資訊，供 Web 顯示"""
   352|    import os, pickle, numpy as np
   353|    from model.train import FEATURE_COLS
   354|    from model.predictor import BASE_FEATURE_COLS as PREDICTOR_FEATURES
   355|    from model.predictor import MODEL_PATH
   356|    from database.models import Labels, FeaturesNormalized
   357|    from sqlalchemy import text
   358|
   359|    db = get_db()
   360|    # Use full feature list from predictor (includes 4H)
   361|    all_features = PREDICTOR_FEATURES
   362|    stats = {
   363|        "model_loaded": False,
   364|        "sample_count": 0,
   365|        "label_distribution": {},
   366|        "cv_accuracy": None,
   367|        "feature_importance": {},
   368|        "ic_values": {},
   369|        "model_params": {},
   370|        "feature_count": len(all_features),
   371|        # P0: Expose 4H signal directly
   372|        "signal_4h": _get_4h_signal(),
   373|    }
   374|
   375|    # 樣本數和標籤分布
   376|    try:
   377|        total = db.query(Labels).count()
   378|        stats["sample_count"] = total
   379|        dist = db.execute(text("SELECT label, COUNT(*) as cnt FROM labels GROUP BY label")).fetchall()
   380|        stats["label_distribution"] = {str(r[0]): r[1] for r in dist}
   381|    except Exception as e:
   382|        logger.error(f"Stats label error: {e}")
   383|
   384|    # 模型準確率 and feature importance
   385|    try:
   386|        if os.path.exists(MODEL_PATH):
   387|            with open(MODEL_PATH, "rb") as f:
   388|                model = pickle.load(f)
   389|            stats["model_loaded"] = True
   390|            if hasattr(model, "feature_importances_"):
   391|                imp = dict(zip(FEATURE_COLS, model.feature_importances_.tolist()))
   392|                stats["feature_importance"] = {k: round(v, 4) for k, v in sorted(imp.items(), key=lambda x: -x[1])}
   393|            if hasattr(model, "get_params"):
   394|                p = model.get_params()
   395|                stats["model_params"] = {k: p.get(k) for k in ["n_estimators", "max_depth", "reg_alpha", "reg_lambda"]}
   396|    except Exception as e:
   397|        logger.error(f"Stats model error: {e}")
   398|
   399|    # IC 計算 — load from ic_signs.json (already computed by train.py)
   400|    try:
   401|        ic_path = os.path.join(os.path.dirname(MODEL_PATH), "ic_signs.json")
   402|        if os.path.exists(ic_path):
   403|            with open(ic_path) as f:
   404|                ic_data = json.load(f)
   405|            # Merge ic_global and ic_tw into ic_values
   406|            for src_key in ["ic_global", "ic_map", "core_ic_summary", "tw_ic_summary"]:
   407|                if src_key in ic_data:
   408|                    for feat, val in ic_data[src_key].items():
   409|                        # Normalize key: feat_eye -> eye, 4h_bias50 -> bias50
   410|                        clean = feat.replace("feat_", "").replace("4h_", "4h_")
   411|                        stats["ic_values"][clean] = round(float(val), 4)
   412|    except Exception as e:
   413|        logger.error(f"Stats IC error: {e}")
   414|
   415|    return stats
   416|
   417|@router.post("/backtest/run")
   418|async def api_run_backtest(days: int = Query(default=30)):
   419|    return await api_backtest(days=days)
   420|
   421|
   422|# ─── Confidence Prediction ───
   423|@router.get("/api/predict/confidence")
   424|async def get_confidence_prediction():
   425|    """返回模型信心分層預測"""
   426|    from model.predictor import predict, load_predictor
   427|    from database.models import init_db
   428|    from config import load_config
   429|
   430|    cfg = load_config()
   431|    session = init_db(cfg["database"]["url"])
   432|    predictor = load_predictor()
   433|    result = predict(session, predictor)
   434|    session.close()
   435|
   436|    if result is None:
   437|        return {"error": "prediction failed", "confidence": 0.5, "signal": "HOLD", "confidence_level": "LOW", "should_trade": False}
   438|    return result
   439|
   440|
   441|# ═══════════════════════════════════════════════
   442|# Strategy Lab API
   443|# ═══════════════════════════════════════════════
   444|
   445|@router.get("/api/strategies/leaderboard")
   446|async def api_strategy_leaderboard():
   447|    """回傳所有已儲存策略的 Leaderboard（依 ROI 排序）。"""
   448|    from backtesting.strategy_lab import load_all_strategies
   449|    strategies = load_all_strategies()
   450|    return {"strategies": strategies, "count": len(strategies)}
   451|
   452|
   453|@router.get("/api/strategies/{name}")
   454|async def api_get_strategy(name: str):
   455|    """取得單一策略定義。"""
   456|    from backtesting.strategy_lab import load_strategy
   457|    s = load_strategy(name)
   458|    if s is None:
   459|        raise HTTPException(status_code=404, detail=f"Strategy '{name}' not found")
   460|    return s
   461|
   462|
   463|@router.delete("/api/strategies/{name}")
   464|async def api_delete_strategy(name: str):
   465|    """刪除策略。"""
   466|    from backtesting.strategy_lab import delete_strategy
   467|    ok = delete_strategy(name)
   468|    if not ok:
   469|        raise HTTPException(status_code=404, detail=f"Strategy '{name}' not found")
   470|    return {"ok": True, "deleted": name}
   471|
   472|
   473|@router.post("/api/strategies/run")
   474|async def api_run_strategy(body: Dict[str, Any]):
   475|    """
   476|    執行回測。
   477|    Body:
   478|      name: 策略名稱
   479|      type: "rule_based" | "hybrid"
   480|      params: 策略參數
   481|    """
   482|    import sqlite3
   483|    import numpy as np
   484|    from backtesting.strategy_lab import run_rule_backtest, run_hybrid_backtest, save_strategy
   485|
   486|    DB_PATH = '/home/kazuha/Poly-Trader/poly_trader.db'
   487|    name = body.get("name", "unnamed_strategy")
   488|    stype = body.get("type", "rule_based")
   489|    params = body.get("params", {})
   490|    initial = body.get("initial_capital", 10000.0)
   491|
   492|    # 從 DB 載入完整資料
   493|    conn = sqlite3.connect(DB_PATH)
   494|    rows = conn.execute("""
   495|        SELECT f.timestamp, r.close_price,
   496|               f.feat_4h_bias50, f.feat_4h_dist_swing_low,
   497|               f.feat_nose, f.feat_pulse, f.feat_ear
   498|        FROM features_normalized f
   499|        JOIN raw_market_data r ON r.timestamp = f.timestamp AND r.symbol = f.symbol
   500|        WHERE f.feat_4h_bias50 IS NOT NULL AND r.close_price IS NOT NULL
   501|
# ═══════════════════════════════════════════════
# Model Leaderboard API
# ═══════════════════════════════════════════════

@router.get("/api/models/leaderboard")
async def api_model_leaderboard():
    """回傳所有 ML 模型的 Walk-Forward Leaderboard"""
    import sqlite3
    import pandas as pd
    import numpy as np
    from backtesting.model_leaderboard import ModelLeaderboard

    DB_PATH = '/home/kazuha/Poly-Trader/poly_trader.db'
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("""
        SELECT f.timestamp, r.close_price, l.label_sell_win,
               f.feat_eye, f.feat_ear, f.feat_nose, f.feat_tongue,
               f.feat_body, f.feat_pulse, f.feat_aura, f.feat_mind,
               f.feat_vix, f.feat_dxy,
               f.feat_rsi14, f.feat_macd_hist, f.feat_atr_pct,
               f.feat_vwap_dev, f.feat_bb_pct_b,
               f.feat_4h_bias50, f.feat_4h_bias20, f.feat_4h_rsi14,
               f.feat_4h_macd_hist, f.feat_4h_bb_pct_b,
               f.feat_4h_ma_order, f.feat_4h_dist_swing_low
        FROM features_normalized f
        JOIN raw_market_data r ON r.timestamp = f.timestamp AND r.symbol = f.symbol
        LEFT JOIN labels l ON l.timestamp = f.timestamp AND l.symbol = f.symbol
        WHERE f.feat_4h_bias50 IS NOT NULL AND r.close_price IS NOT NULL
        ORDER BY f.timestamp
    """, conn)
    conn.close()
    
    df = df.fillna(0)
    df['label_sell_win'] = df['label_sell_win'].fillna(1).astype(int)
    
    lb = ModelLeaderboard(df)
    results = lb.run_all_models([
        "rule_baseline", "logistic_regression", "xgboost",
        "random_forest", "mlp"
    ])
    
    # Serialize
    leaderboard = []
    for r in results:
        fold_data = []
        for f in r.folds:
            fold_data.append({
                "fold": f.fold,
                "train_start": f.train_start,
                "train_end": f.train_end,
                "test_start": f.test_start,
                "test_end": f.test_end,
                "roi": round(f.roi, 4),
                "win_rate": round(f.win_rate, 4),
                "trades": f.total_trades,
                "max_dd": round(f.max_drawdown, 4),
                "profit_factor": round(f.profit_factor, 4),
            })
        
        leaderboard.append({
            "model_name": r.model_name,
            "avg_roi": round(r.avg_roi, 4),
            "avg_win_rate": round(r.avg_win_rate, 4),
            "avg_trades": int(r.avg_trades),
            "avg_max_dd": round(r.avg_max_drawdown, 4),
            "std_roi": round(r.std_roi, 4),
            "profit_factor": round(r.avg_profit_factor, 4),
            "train_acc": round(r.train_accuracy, 4),
            "test_acc": round(r.test_accuracy, 4),
            "train_test_gap": round(r.train_test_gap, 4),
            "composite": round(r.composite_score, 4),
            "folds": fold_data,
        })
    
    return {"leaderboard": leaderboard, "count": len(leaderboard)}
