#!/usr/bin/env python3
"""Pyramid Spot Trading Strategy — 4H 結構定位 + 金字塔分批 + 止損止盈

核心理念:
  4H 乖離率(MA50)定位市場高低 → 知道現在貴還是便宜
  金字塔 20→30→50 分批入場 → 越跌越買但不一次 All-in
  特徵過濾(nose RSI)抓時機     → 不在超買時進場
  -5% 止損 + bias50>+4% 止盈  → 虧損可控，獲利會跑

Web Dashboard Integration:
  輸出 signal 到 scripts/pyramid_signal.json
  心跳 runner 每 4H 執行一次
"""
import sys
import os
sys.path.insert(0, '/home/kazuha/Poly-Trader')
os.chdir('/home/kazuha/Poly-Trader')

import json
import sqlite3
import bisect
import numpy as np
import ccxt
from datetime import datetime, timezone

DB_PATH = '/home/kazuha/Poly-Trader/poly_trader.db'
SIGNAL_PATH = '/home/kazuha/Poly-Trader/scripts/pyramid_signal.json'

# ══════════════════════════════════════════════
# 策略參數 (可在 config 中調整)
# ══════════════════════════════════════════════
STRATEGY = {
    "name": "pyramid_4h_spot",
    "version": "v1",

    # 倉位分配
    "layers": {
        "L1": {"pct": 0.20, "bias_range": [-1.5, 1.0], "condition": "nose < 0.40"},
        "L2": {"pct": 0.30, "bias_range": [-3.5, -1.5], "condition": "auto"},
        "L3": {"pct": 0.50, "bias_range": [-6.0, -3.5], "condition": "dist_swing_low < 5%"},
    },

    # 出場
    "take_profit_bias": 4.0,   # bias50 >+4% 止盈
    "take_profit_roi": 0.08,   # 單筆 ROI >8% 止盈
    "stop_loss": -0.05,         # 跌 5% 止損

    # 特徵過濾
    "nose_max": 0.40,          # RSI 不高於此值才進場
}


# ══════════════════════════════════════════════
# 4H 結構計算
# ══════════════════════════════════════════════
def ema(data, period):
    k = 2.0 / (period + 1)
    out = [data[0]]
    for x in data[1:]:
        out.append(out[-1] * (1 - k) + x * k)
    return out


def find_swings_rolling(highs, lows, window=10):
    n = len(highs)
    swing_low = [float(lows[0])] * n
    swing_high = [float(highs[0])] * n
    cur_low = float(lows[0])
    cur_high = float(highs[0])
    for i in range(window, min(n - window, n)):
        is_low = all(
            lows[j] >= lows[i]
            for j in range(max(0, i - window), min(n, i + window + 1))
            if j != i
        )
        is_high = all(
            highs[j] <= highs[i]
            for j in range(max(0, i - window), min(n, i + window + 1))
            if j != i
        )
        if is_low:
            cur_low = float(lows[i])
        if is_high:
            cur_high = float(highs[i])
        swing_low[i] = cur_low
        swing_high[i] = cur_high
    for i in range(max(0, n - window), n):
        swing_low[i] = cur_low
        swing_high[i] = cur_high
    return swing_low, swing_high


def compute_rsi(closes, period=14):
    n = len(closes)
    out = [50.0] * n
    if n < period + 1:
        return out
    closes_arr = np.array(closes, dtype=float)
    diffs = np.diff(closes_arr)
    gains = np.maximum(diffs, 0)
    losses = np.maximum(-diffs, 0)
    avg_g = np.mean(gains[:period])
    avg_l = np.mean(losses[:period])
    for i in range(period, len(gains)):
        avg_g = (avg_g * (period - 1) + gains[i]) / period
        avg_l = (avg_l * (period - 1) + losses[i]) / period
        rs = avg_g / avg_l if avg_l > 0 else 100
        out[i] = 100.0 - 100.0 / (1.0 + rs)
    return out


def compute_macd_hist(closes, fast=12, slow=26, signal_p=9):
    n = len(closes)
    out = [0.0] * n
    if n < slow + signal_p:
        return out
    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    macd_valid = macd_line[slow - 1:]
    signal_arr = ema(macd_valid, signal_p)
    start = (slow - 1) + (signal_p - 1)
    for i, sig_val in enumerate(signal_arr):
        idx = start + i
        if idx < n and i + signal_p - 1 < len(macd_valid):
            out[idx] = macd_valid[i + signal_p - 1] - sig_val
    return out


def fetch_4h_candles(limit=1000):
    """Fetch latest 4H candles from Binance."""
    exchange = ccxt.binance({"enableRateLimit": True})
    ohlcv = exchange.fetch_ohlcv("BTC/USDT", "4h", limit=limit)
    return [
        {"ts": o[0], "o": o[1], "h": o[2], "l": o[3], "c": o[4], "v": o[5]}
        for o in ohlcv
    ]


def build_4h_structure(candles):
    """Compute all 4H structural levels from OHLCV list."""
    n = len(candles)
    if n < 200:
        return None

    closes = [c["c"] for c in candles]
    highs  = [c["h"] for c in candles]
    lows   = [c["l"] for c in candles]
    timestamps = [c["ts"] for c in candles]

    ma50 = ema(closes, 50)
    ma200 = ema(closes, 200)
    ma20 = ema(closes, 20)
    rsi14 = compute_rsi(closes, 14)
    macd_h = compute_macd_hist(closes)
    swing_low, swing_high = find_swings_rolling(highs, lows, window=10)

    return {
        "timestamps": timestamps,
        "ma50": ma50, "ma200": ma200, "ma20": ma20,
        "rsi14": rsi14, "macd_hist": macd_h,
        "swing_low": swing_low, "swing_high": swing_high,
        "n": n,
    }


def get_current_4h_values(structure, current_price):
    """Get latest 4H level values and compute current bias/distances."""
    idx = structure["n"] - 1
    bias50 = (current_price - structure["ma50"][idx]) / structure["ma50"][idx] * 100
    bias200 = (current_price - structure["ma200"][idx]) / structure["ma200"][idx] * 100
    bias20 = (current_price - structure["ma20"][idx]) / structure["ma20"][idx] * 100
    dist_swing_low = (current_price - structure["swing_low"][idx]) / structure["swing_low"][idx] * 100
    dist_swing_high = (current_price - structure["swing_high"][idx]) / structure["swing_high"][idx] * 100

    # MA order
    ma_ord = 0
    if structure["ma20"][idx] > structure["ma50"][idx] > structure["ma200"][idx]:
        ma_ord = 1
    elif structure["ma20"][idx] < structure["ma50"][idx] < structure["ma200"][idx]:
        ma_ord = -1

    return {
        "bias50": round(bias50, 2),
        "bias200": round(bias200, 2),
        "bias20": round(bias20, 2),
        "ma_order": ma_ord,
        "rsi14": round(structure["rsi14"][idx], 1),
        "macd_hist": round(structure["macd_hist"][idx], 1),
        "dist_swing_low": round(dist_swing_low, 2),
        "dist_swing_high": round(dist_swing_high, 2),
        "ma50": round(structure["ma50"][idx], 0),
        "ma200": round(structure["ma200"][idx], 0),
        "swing_low": round(structure["swing_low"][idx], 0),
        "swing_high": round(structure["swing_high"][idx], 0),
    }


# ══════════════════════════════════════════════
# 策略引擎
# ══════════════════════════════════════════════
def load_feature_features():
    """Load latest feature features from DB."""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("""
        SELECT feat_nose, feat_ear, feat_pulse, feat_aura, feat_eye
        FROM features_normalized
        ORDER BY timestamp DESC LIMIT 1
    """).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "nose": float(row[0]) if row[0] is not None else 0.5,
        "ear": float(row[1]) if row[1] is not None else 0,
        "pulse": float(row[2]) if row[2] is not None else 0,
        "aura": float(row[3]) if row[3] is not None else 0,
        "eye": float(row[4]) if row[4] is not None else 0,
    }


def load_portfolio_state():
    """Load current portfolio state (position, layers, cash)."""
    if os.path.exists(SIGNAL_PATH):
        try:
            with open(SIGNAL_PATH) as f:
                data = json.load(f)
            return data.get("portfolio", {
                "position": 0,
                "layers": [],
                "total_invested": 0,
                "initial_capital": 10000,
                "cash": 10000,
            })
        except Exception:
            pass
    return {
        "position": 0,
        "layers": [],
        "total_invested": 0,
        "initial_capital": 10000,
        "cash": 10000,
    }


def evaluate_signal(
    structure_4h,
    current_price,
    feature,
    portfolio,
):
    """Evaluate current trading signal based on all inputs."""
    v4h = get_current_4h_values(structure_4h, current_price)
    b50 = v4h["bias50"]
    dsl = v4h["dist_swing_low"]
    n_val = feature["nose"] if feature else 0.5

    position = portfolio.get("position", 0)
    layers = portfolio.get("layers", [])
    INITIAL = portfolio.get("initial_capital", 10000)

    # Default: hold
    signal = "HOLD"
    action = None
    details = {}
    urgency = "NONE"

    # ─── 止損檢查 ───
    if position > 0 and layers:
        avg_cost = sum(l["price"] * l["coins"] for l in layers) / sum(l["coins"] for l in layers)
        pnl_pct = (current_price - avg_cost) / avg_cost

        if pnl_pct <= STRATEGY["stop_loss"]:
            signal = "STOP_LOSS"
            action = "SELL_ALL"
            urgency = "HIGH"
            details = {
                "reason": f"止損觸發: 虧損 {pnl_pct:.1%} (閾值 {STRATEGY['stop_loss']:.0%})",
                "avg_cost": round(avg_cost, 0),
                "current_price": current_price,
                "pnl_pct": round(pnl_pct, 3),
                "sell_all": True,
            }
            # Also compute sell amount
            total_coins = sum(l["coins"] for l in layers)
            details["coins_to_sell"] = total_coins
            details["estimated_proceeds"] = round(total_coins * current_price, 0)
            details["estimated_pnl"] = round((current_price - avg_cost) * total_coins, 0)
            return signal, action, urgency, v4h, details

    # ─── 止盈檢查 ───
    if position > 0 and layers:
        avg_cost = sum(l["price"] * l["coins"] for l in layers) / sum(l["coins"] for l in layers)
        pnl_pct = (current_price - avg_cost) / avg_cost

        if b50 > STRATEGY["take_profit_bias"]:
            signal = "TAKE_PROFIT_BIAS"
            action = "SELL_ALL"
            urgency = "MEDIUM"
            details = {
                "reason": f"超買止盈: bias50=+{b50:.1f}% > +{STRATEGY['take_profit_bias']:.0f}%",
                "avg_cost": round(avg_cost, 0),
                "pnl_pct": round(pnl_pct, 3),
                "sell_all": True,
            }
            total_coins = sum(l["coins"] for l in layers)
            details["coins_to_sell"] = total_coins
            details["estimated_proceeds"] = round(total_coins * current_price, 0)
            details["estimated_pnl"] = round((current_price - avg_cost) * total_coins, 0)
            return signal, action, urgency, v4h, details

        elif pnl_pct > STRATEGY["take_profit_roi"]:
            signal = "TAKE_PROFIT_ROI"
            action = "SELL_ALL"
            urgency = "MEDIUM"
            details = {
                "reason": f"ROI 止盈: {pnl_pct:.1%} > {STRATEGY['take_profit_roi']:.0%}",
                "avg_cost": round(avg_cost, 0),
                "pnl_pct": round(pnl_pct, 3),
                "sell_all": True,
            }
            total_coins = sum(l["coins"] for l in layers)
            details["coins_to_sell"] = total_coins
            details["estimated_proceeds"] = round(total_coins * current_price, 0)
            details["estimated_pnl"] = round((current_price - avg_cost) * total_coins, 0)
            return signal, action, urgency, v4h, details

    # ─── 進場檢查 ───
    L1_range = STRATEGY["layers"]["L1"]["bias_range"]
    L2_range = STRATEGY["layers"]["L2"]["bias_range"]
    L3_range = STRATEGY["layers"]["L3"]["bias_range"]
    nose_max = STRATEGY["nose_max"]

    if position == 0:
        # Layer 1: -1.5% <= bias50 <= +1.0%, nose < 0.40
        if L1_range[0] <= b50 <= L1_range[1] and n_val < nose_max:
            buy_amt = round(INITIAL * 0.20, 0)
            coins = round(buy_amt / current_price, 6)
            signal = "BUY_L1"
            action = "BUY"
            urgency = "LOW"
            details = {
                "layer": 1,
                "reason": f"牛市常規買入 (bias50={b50:+.1f}%, nose={n_val:.2f})",
                "amount_usd": buy_amt,
                "coins": coins,
                "condition": f"RSI={n_val:.2f} < {nose_max} (特徵確認)",
            }
        else:
            details = {
                "reason": f"未達進場條件 (bias50={b50:+.1f}%, nose={n_val:.2f})",
            }

    elif len(layers) == 1:
        # Layer 2: -3.5% < bias50 <= -1.5%
        if L2_range[0] < b50 <= L2_range[1]:
            buy_amt = round(INITIAL * 0.30, 0)
            coins = round(buy_amt / current_price, 6)
            signal = "BUY_L2"
            action = "BUY"
            urgency = "MEDIUM"
            details = {
                "layer": 2,
                "reason": f"回調加碼 (bias50={b50:+.1f}%)",
                "amount_usd": buy_amt,
                "coins": coins,
                "condition": "小幅回調自動加碼",
            }
        else:
            details = {"reason": f"未達 Layer2 條件 (bias50={b50:+.1f}%)"}

    elif len(layers) == 2:
        # Layer 3: -6.0% <= bias50 <= -3.5%, dist_swing_low < 5%
        if L3_range[0] <= b50 <= L3_range[1] and dsl < 5:
            buy_amt = round(INITIAL * 0.50, 0)
            coins = round(buy_amt / current_price, 6)
            signal = "BUY_L3"
            action = "BUY"
            urgency = "HIGH"
            details = {
                "layer": 3,
                "reason": f"暴跌重倉 (bias50={b50:+.1f}%, dist_swing_low={dsl:+.1f}%)",
                "amount_usd": buy_amt,
                "coins": coins,
                "condition": f"靠近支撐線 {dsl:.1f}% < 5%",
            }
        elif L3_range[0] <= b50 <= L3_range[1]:
            details = {"reason": f"符合暴跌但遠離支撐 (dist_swing_low={dsl:.1f}% > 5%)"}
        else:
            details = {"reason": f"未達 Layer3 條件 (bias50={b50:+.1f}%)"}

    return signal, action, urgency, v4h, details


# ══════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════
def main():
    print("=== 金字塔現貨策略 ===\n")
    start = datetime.now(timezone.utc)

    # 1. Get current price
    print("[1/4] Getting current BTC price...")
    exchange = ccxt.binance({"enableRateLimit": True})
    ticker = exchange.fetch_ticker("BTC/USDT")
    current_price = ticker["last"]
    print(f"  BTC/USDT: ${current_price:,.0f}")

    # 2. Fetch 4H structure
    print("\n[2/4] Computing 4H structure...")
    candles = fetch_4h_candles(limit=1000)
    structure_4h = build_4h_structure(candles)
    if structure_4h is None:
        print("  ❌ Not enough 4H candles")
        return
    v4h = get_current_4h_values(structure_4h, current_price)
    print(f"  MA50=${v4h['ma50']:,.0f}  bias={v4h['bias50']:+.1f}%")
    print(f"  MA200=${v4h['ma200']:,.0f}  bias={v4h['bias200']:+.1f}%")
    print(f"  RSI14={v4h['rsi14']:.1f}  MACD-H={v4h['macd_hist']:.0f}")
    print(f"  SwingL=${v4h['swing_low']:,.0f}  dist={v4h['dist_swing_low']:+.1f}%")

    # 3. Get feature + portfolio
    print("\n[3/4] Loading feature + portfolio...")
    feature = load_feature_features()
    portfolio = load_portfolio_state()
    if feature:
        print(f"  nose={feature['nose']:.2f} ear={feature['ear']:.3f} pulse={feature['pulse']:.2f}")
    else:
        print("  ⚠️ Feature data not available")
    print(f"  Position: {portfolio['position']:.6f} BTC ({portfolio['total_invested']:,.0f} USDT)")
    print(f"  Layers: {len(portfolio['layers'])}")
    print(f"  Cash: ${portfolio['cash']:,.0f}")

    # 4. Evaluate
    print("\n[4/4] Evaluating signal...")
    signal, action, urgency, v4h_info, details = evaluate_signal(
        structure_4h, current_price, feature, portfolio
    )

    # Print result
    emoji_map = {
        "BUY_L1": "🟢", "BUY_L2": "🟡", "BUY_L3": "🔴",
        "STOP_LOSS": "🛑", "TAKE_PROFIT_BIAS": "💰", "TAKE_PROFIT_ROI": "💰",
        "HOLD": "⚪",
    }
    emoji = emoji_map.get(signal, "❓")
    print(f"\n{emoji} 信號: {signal} | 動作: {action} | 緊急度: {urgency}")
    print(f"  原因: {details.get('reason', '')}")
    if "amount_usd" in details:
        print(f"  金額: ${details['amount_usd']:,.0f} ({details['coins']:.6f} BTC)")

    # Build output
    output = {
        "timestamp": start.isoformat(),
        "signal": signal,
        "action": action,
        "urgency": urgency,
        "price": current_price,
        "4h": v4h_info,
        "feature": feature,
        "portfolio": {
            "position": portfolio["position"],
            "layers": portfolio["layers"],
            "total_invested": portfolio["total_invested"],
            "initial_capital": portfolio["initial_capital"],
            "cash": portfolio["cash"],
            "avg_cost": round(
                sum(l["price"] * l["coins"] for l in portfolio["layers"])
                / max(sum(l["coins"] for l in portfolio["layers"]), 1e-10), 0
            ) if portfolio["layers"] else 0,
            "unrealized_pnl_pct": round(
                (current_price / max(
                    sum(l["price"] * l["coins"] for l in portfolio["layers"])
                    / max(sum(l["coins"] for l in portfolio["layers"]), 1e-10),
                    1e-10
                ) - 1) * 100, 2
            ) if portfolio["layers"] else 0,
        },
        "details": details,
        "strategy": {
            "take_profit_bias": STRATEGY["take_profit_bias"],
            "take_profit_roi": STRATEGY["take_profit_roi"],
            "stop_loss": STRATEGY["stop_loss"],
            "nose_max": STRATEGY["nose_max"],
        },
    }

    # Save
    os.makedirs(os.path.dirname(SIGNAL_PATH), exist_ok=True)
    with open(SIGNAL_PATH, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n✓ Signal saved to {SIGNAL_PATH}")

    # Summary line
    lines = []
    lines.append(f"📊 金字塔: {signal} | 價格 ${current_price:,.0f} | bias50={v4h['bias50']:+.1f}%")
    if portfolio["layers"]:
        avg = sum(l["price"] * l["coins"] for l in portfolio["layers"]) / sum(l["coins"] for l in portfolio["layers"])
        pnl_pct = (current_price / avg - 1) * 100
        lines.append(f"   倉位: {portfolio['position']:.6f} BTC | 均價 ${avg:,.0f} | 浮盈 {pnl_pct:+.1f}%")
    print("\n" + "\n".join(lines))

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    print(f"\nDone in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
