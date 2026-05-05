"""
4H + 即時特徵 組合策略即時分析
===============================
從 OKX 抓 4H OHLCV → 算乖離率/MACD
從 DB 讀最新即時特徵
→ 輸出完整買賣信號
"""
import numpy as np
import sys, ccxt, json, os
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, '/home/kazuha/Poly-Trader')

# 1. 4H 模組
from feature_engine.ohlcv_4h import compute_4h_indicators

# 2. 組合策略
from strategies.combined_4h_spot import combined_strategy


def get_latest_feature_from_db() -> dict:
    """從 DB 讀最新一行 feature 特徵"""
    from database.models import init_db, FeaturesNormalized
    session = init_db('sqlite:///./poly_trader.db')
    row = session.query(FeaturesNormalized).order_by(
        FeaturesNormalized.timestamp.desc()
    ).first()
    session.close()
    
    if not row:
        return {}
    
    return {
        "nose": float(getattr(row, 'feat_nose', row.feat_nose_sigmoid or 0.5)),
        "tongue": float(getattr(row, 'feat_tongue', row.feat_tongue_pct or 0)),
        "pulse": float(getattr(row, 'feat_pulse', 0.5)),
        "eye": float(getattr(row, 'feat_eye', row.feat_eye_dist or 0)),
        "body": float(getattr(row, 'feat_body', row.feat_body_roc or 0)),
        "ear": float(getattr(row, 'feat_ear', row.feat_ear_zscore or 0)),
        "mind": float(getattr(row, 'feat_mind', 0)),
        "aura": float(getattr(row, 'feat_aura', 0)),
    }


def analyze():
    """完整分析：4H + 即時特徵 → 策略信號"""
    print("=" * 70)
    print("🔮 Poly-Trader 4H + 即時特徵 組合策略")
    print("=" * 70)
    
    # ── Step 1: 4H 資料 ──
    print("\n[1/3] 抓取 OKX 4H OHLCV...")
    exchange = ccxt.okx({"enableRateLimit": True})
    ohlcv = exchange.fetch_ohlcv("BTC/USDT", "4h", limit=300)
    
    candles = {
        "timestamps": np.array([o[0] for o in ohlcv]),
        "opens": np.array([o[1] for o in ohlcv]),
        "highs": np.array([o[2] for o in ohlcv]),
        "lows": np.array([o[3] for o in ohlcv]),
        "closes": np.array([o[4] for o in ohlcv]),
        "volumes": np.array([o[5] for o in ohlcv]),
    }
    n = len(candles["closes"])
    current_price = candles["closes"][-1]
    print(f"  BTC/USDT: ${current_price:,.0f}")
    print(f"  4H 時間: {datetime.fromtimestamp(candles['timestamps'][-1]/1000).isoformat()}")
    
    # ── Step 2: 4H 指標 ──
    print("\n[2/3] 計算 4H 指標...")
    ind = compute_4h_indicators(candles)
    
    def gv(name, i, default=0):
        arr = ind.get(name, [default] * n)
        return float(arr[i]) if 0 <= i < len(arr) and isinstance(arr[i], (int, float)) and np.isfinite(arr[i]) else float(default)
    
    bias50 = gv('4h_bias50', n - 1)
    bias200 = gv('4h_bias200', n - 1)
    macd_hist = gv('4h_macd_hist', n - 1)
    rsi_4h = gv('4h_rsi14', n - 1)
    bb_pct = gv('4h_bb_pct_b', n - 1)
    
    print(f"  Bias50:   {bias50:+.2f}% (價格 vs MA50)")
    print(f"  Bias200:  {bias200:+.2f}% (價格 vs MA200)")
    print(f"  MACD Hist: {macd_hist:+.1f}")
    print(f"  RSI 4H:   {rsi_4h:.1f}")
    print(f"  BB %B:    {bb_pct:.2f}")
    
    # ── Step 3: 即時特徵 ──
    print("\n[3/3] 讀取即時特徵...")
    feature = get_latest_feature_from_db()
    
    if feature:
        print(f"  nose (RSI):      {feature.get('nose', 0):.2f}")
        print(f"  tongue (回歸):   {feature.get('tongue', 0):.3f}")
        print(f"  pulse (動量):    {feature.get('pulse', 0):.2f}")
        print(f"  eye (趨勢):       {feature.get('eye', 0):.3f}")
        print(f"  body (波動):      {feature.get('body', 0):.3f}")
        print(f"  ear (動能):       {feature.get('ear', 0):.3f}")
        print(f"  mind (短迴):      {feature.get('mind', 0):.3f}")
    else:
        print("  ⚠️ 無法從 DB 讀取特徵資料，使用預設值")
        feature = {
            "nose": 0.5, "tongue": 0, "pulse": 0.5,
            "eye": 0, "body": 0, "ear": 0, "mind": 0,
        }
    
    # ── Step 4: 策略判斷 ──
    print("\n" + "=" * 70)
    print("📊 策略分析結果")
    print("=" * 70)
    
    result = combined_strategy(
        bias50=bias50,
        macd_hist=macd_hist,
        bias200=bias200,
        feature=feature,
        current_price=current_price,
        base_capital=10000.0,
    )
    
    # ── 輸出 ──
    signal = result["signal"]
    strength = result["strength"]
    urgency = result["urgency"]
    message = result["message"]
    
    color_map = {
        "BUY": "\033[92m", "SELL": "\033[91m", "HOLD": "\033[93m"
    }
    reset = "\033[0m"
    color = color_map.get(signal, "")
    
    print(f"\n  信號: {color}{signal}{reset}")
    print(f"  強度: {strength:.0%}")
    print(f"  緊急度: {urgency}")
    print(f"  價格: ${current_price:,.0f}")
    
    # 4H 方向
    d4h = result["details"].get("4h_direction", "UNKNOWN")
    print(f"\n  📐 4H 方向: {d4h}")
    print(f"     乖離率: {bias50:+.2f}%")
    print(f"     MACD:   {macd_hist:+.1f}")
    
    # 特徵確認
    feature_detail = result["details"].get("feature", {})
    if feature_detail:
        print(f"\n  🎛️ 特徵確認:")
        for cond, met in feature_detail.get("details", {}).items():
            icon = "✅" if met else "❌"
            print(f"     {icon} {cond}")
        print(f"     → {feature_detail.get('reason', '')}")
    
    # 金字塔
    pyramid = result["details"].get("pyramid", {})
    if pyramid:
        print(f"\n  🏗️ 金字塔:")
        print(f"     {pyramid.get('message', '等待加碼條件')}")
        print(f"     配置: {pyramid.get('pct_of_capital', 0)*100:.0f}% = ${pyramid.get('amount_usd', 0):,.0f}")
    
    # 出場/持倉
    exit_check = result["details"].get("exit_check", {})
    if exit_check:
        pos = result["details"].get("position", {})
        entry = pos.get("entry_price", 0)
        ret = (current_price - entry) / entry if entry > 0 else 0
        print(f"\n  📍 持倉檢查:")
        print(f"     入場: ${entry:,.0f}")
        print(f"     現在: ${current_price:,.0f}")
        print(f"     損益: {ret*100:+.1f}%")
        print(f"     → {exit_check.get('reason', '持有中')}")
    
    print(f"\n  💬 {message}")
    print()
    
    # Save result
    output = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "signal": signal,
        "strength": strength,
        "urgency": urgency,
        "price": current_price,
        "message": message,
        "4h": {
            "direction": d4h,
            "bias50": round(bias50, 2),
            "bias200": round(bias200, 2),
            "macd_hist": round(macd_hist, 1),
        },
        "feature_result": feature_detail,
        "pyramid": pyramid,
        "exit_check": exit_check,
    }
    
    out_path = os.path.join('/home/kazuha/Poly-Trader/scripts', 'combined_signal.json')
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"  💾 信号已存: scripts/combined_signal.json")
    
    return result


if __name__ == "__main__":
    analyze()
