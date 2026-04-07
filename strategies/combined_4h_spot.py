"""
組合策略: 4H 大方向 + 即時特徵確認
=====================================

邏輯:
1. 4H 決定方向 (bias50, MACD)
2. 即時特徵決定入場時機 (nose, pulse, tongue, eye, body)
3. 金字塔加碼 (20/30/50)
4. 動態出場 (4H 回到平衡 / 特徵超賣超買)
"""
import numpy as np
from typing import Dict, Optional, List
from datetime import datetime


# ───────────────────────────────────────
# 4H 方向過濾
# ───────────────────────────────────────
def check_4h_direction(bias50: float, macd_hist: float, bias200: float = 0) -> str:
    """
    4H 大方向判斷
    返回: "BULL", "BEAR", "NEUTRAL"
    """
    # 乖離率 < -3% = 超賣 = 看多 (買入機會)
    if bias50 < -3.0:
        return "BULL"  # 價格遠低於 MA50，反彈機率大
    
    # 乖離率 > +5% = 超買 = 看空 (賣出/做空機會, 需要更嚴格)
    if bias50 > 5.0:
        return "BEAR"  # 價格遠高於 MA50，回調機率大
    
    # MACD + 乖離率 輔助判斷
    if bias50 < -1.0 and macd_hist < 0:
        return "BULL"  # 偏離 + 空頭動能 = 可能觸底反弹
    
    # 只有 bias50 > 3 且 MACD 轉負才考慮 BEAR
    if bias50 > 3.0 and macd_hist < 0:
        return "BEAR"  # 高於 + 動能轉弱 = 可能見頂
    
    return "NEUTRAL"


# ───────────────────────────────────────
# 即時特徵入場確認
# ───────────────────────────────────────
def check_feature_entry(feature: Dict[str, float], direction: str) -> Dict:
    """
    檢查即時 feature 特徵，判斷是否為精確入場點位
    
    feature: {
        "nose": RSI normalized (0-1),
        "tongue": mean-reversion deviation,
        "pulse": volume spike z-score,
        "eye": return/vol ratio,
        "body": volatility z-score,
        "ear": momentum,
        "mind": short-term return,
    }
    
    direction: "BULL" (買) or "BEAR" (賣)
    """
    nose = feature.get("nose", 0.5)       # RSI (0-1, <0.3=超賣, >0.7=超買)
    tongue = feature.get("tongue", 0)     # mean-reversion
    pulse = feature.get("pulse", 0.5)     # volume spike (>0.7=放量)
    eye = feature.get("eye", 0)           # trend strength
    body = feature.get("body", 0)         # volatility
    ear = feature.get("ear", 0)           # momentum
    mind = feature.get("mind", 0)         # short-term return
    
    if direction == "BULL":
        # 買入條件: 超賣 + 放量確認
        rsi_oversold = nose < 0.30
        mean_rev_bullish = tongue < -0.02  # 價格低於均線，準備回歸
        vol_confirm = pulse > 0.65         # 有量
        momentum_turn = ear > -0.01        # 動能開始轉正
        
        score = sum([rsi_oversold, mean_rev_bullish, vol_confirm, momentum_turn])
        strength = score / 4.0
        
        return {
            "action": "BUY" if strength >= 0.5 else "WAIT",
            "strength": round(strength, 2),
            "conditions_met": score,
            "conditions_total": 4,
            "details": {
                "RSI 超賣 (<0.30)": rsi_oversold,
                "均值回歸 (<-0.02)": mean_rev_bullish,
                "放量確認 (>0.65)": vol_confirm,
                "動能轉正 (>-0.01)": momentum_turn,
            },
            "reason": f"RSI={nose:.2f} {'超賣✓' if rsi_oversold else '正常'} | "
                      f"Tongue={tongue:.3f} {'回歸✓' if mean_rev_bullish else '偏離'} | "
                      f"Pulse={pulse:.2f} {'放量✓' if vol_confirm else '平量'} | "
                      f"Ear={ear:.3f} {'轉正✓' if momentum_turn else '負向'}",
        }
    
    elif direction == "BEAR":
        # 賣出條件: 超買 + 放量確認
        rsi_overbought = nose > 0.70
        mean_rev_bearish = tongue > 0.02  # 價格高於均線，準備回歸
        vol_confirm = pulse > 0.65        # 有量
        momentum_turn = ear < 0.01        # 動能開始轉負
        
        score = sum([rsi_overbought, mean_rev_bearish, vol_confirm, momentum_turn])
        strength = score / 4.0
        
        return {
            "action": "SELL" if strength >= 0.75 else "WAIT",  # BEAR needs stronger confirmation
            "strength": round(strength, 2),
            "conditions_met": score,
            "conditions_total": 4,
            "details": {
                "RSI 超買 (>0.70)": rsi_overbought,
                "均值回歸 (>0.02)": mean_rev_bearish,
                "放量確認 (>0.65)": vol_confirm,
                "動能轉負 (<0.01)": momentum_turn,
            },
            "reason": f"RSI={nose:.2f} {'超買✓' if rsi_overbought else '正常'} | "
                      f"Tongue={tongue:.3f} {'回歸✓' if mean_rev_bearish else '偏離'} | "
                      f"Pulse={pulse:.2f} {'放量✓' if vol_confirm else '平量'} | "
                      f"Ear={ear:.3f} {'轉負✓' if momentum_turn else '正向'}",
        }
    
    return {
        "action": "NEUTRAL",
        "strength": 0.5,
        "conditions_met": 0,
        "conditions_total": 4,
        "details": {},
        "reason": "4H 訊號不明確",
    }


# ───────────────────────────────────────
# 金字塔加碼計算
# ───────────────────────────────────────
def calculate_pyramid_entry(entry_price: float, current_price: float, 
                           base_capital: float, level: int = 0) -> Dict:
    """
    計算金字塔加碼
    
    level 0: 未進場
    level 1: 已買 20%
    level 2: 已買 50% (20+30)
    level 3: 已買 100% (20+30+50)
    """
    if level == 0:
        return {
            "action": "BUY",
            "pct_of_capital": 0.20,
            "amount_usd": base_capital * 0.20,
            "price": entry_price,
            "message": f"Layer 1: 買入 20% @ ${entry_price:,.0f}",
        }
    
    drop_pct = (current_price - entry_price) / entry_price
    
    if level == 1 and drop_pct < -0.02:
        return {
            "action": "BUY",
            "pct_of_capital": 0.30,
            "amount_usd": base_capital * 0.30,
            "price": current_price,
            "message": f"Layer 2: 加碼 30% @ ${current_price:,.0f} (已跌 {drop_pct*100:.1f}%)",
        }
    
    if level <= 2 and drop_pct < -0.05:
        return {
            "action": "BUY",
            "pct_of_capital": 0.50,
            "amount_usd": base_capital * 0.50,
            "price": current_price,
            "message": f"Layer 3: 加碼 50% @ ${current_price:,.0f} (已跌 {drop_pct*100:.1f}%)",
        }
    
    return {
        "action": "HOLD",
        "pct_of_capital": 0,
        "amount_usd": 0,
        "price": current_price,
        "message": f"等待回調 (已跌 {drop_pct*100:.1f}%)",
    }


# ───────────────────────────────────────
# 出場條件
# ───────────────────────────────────────
def check_exit_conditions(
    current_price: float, entry_price: float,
    bias50: float, feature: Dict[str, float],
    take_profit_pct: float = 0.05,  # 5% 止盈
    stop_loss_pct: float = -0.08,   # 8% 止損
) -> Dict:
    """
    檢查是否該出場
    """
    ret = (current_price - entry_price) / entry_price
    
    # 1. 固定止盈/止損
    if ret >= take_profit_pct:
        return {
            "action": "SELL",
            "reason": f"達到止盈目標 +{take_profit_pct*100:.0f}% (實際 +{ret*100:.1f}%)",
            "urgency": "HIGH",
        }
    
    if ret <= stop_loss_pct:
        return {
            "action": "SELL",
            "reason": f"觸發止損 {stop_loss_pct*100:.0f}% (實際 {ret*100:.1f}%)",
            "urgency": "CRITICAL",
        }
    
    # 2. 4H 回到平衡 (乖離率回到正區間)
    if bias50 > 2.0:
        return {
            "action": "SELL",
            "reason": f"4H 乖離率回到 +{bias50:.1f}% (已達上方阻力區)",
            "urgency": "MEDIUM",
        }
    
    # 3. 特徵顯示超買
    nose = feature.get("nose", 0.5)
    tongue = feature.get("tongue", 0)
    
    if nose > 0.75 and tongue > 0.03:
        return {
            "action": "SELL",
            "reason": f"特徵超買 (RSI={nose:.2f}, 乖離={tongue:.3f})",
            "urgency": "HIGH",
        }
    
    return {
        "action": "HOLD",
        "reason": f"持有中 (目前 {ret*100:+.1f}%, 乖離率 {bias50:+.1f}%)",
        "urgency": "NONE",
    }


# ───────────────────────────────────────
# 完整策略整合
# ───────────────────────────────────────
def combined_strategy(
    bias50: float, macd_hist: float, bias200: float,
    feature: Dict[str, float],
    current_price: float,
    position: Optional[Dict] = None,  # 當前持倉狀態
    base_capital: float = 10000.0,
) -> Dict:
    """
    整合 4H + 即時特徵的完整策略
    
    返回:
    {
        "signal": "BUY" | "SELL" | "HOLD",
        "strength": 0.0-1.0,
        "price": current_price,
        "urgency": "CRITICAL" | "HIGH" | "MEDIUM" | "NONE",
        "details": { ... },
    }
    """
    result = {
        "signal": "HOLD",
        "strength": 0,
        "price": current_price,
        "urgency": "NONE",
        "details": {},
        "message": "",
    }
    
    # ── Step 1: 4H 方向判斷 ──
    direction_4h = check_4h_direction(bias50, macd_hist, bias200)
    result["details"]["4h_direction"] = direction_4h
    result["details"]["bias50"] = round(bias50, 2)
    result["details"]["macd_hist"] = round(macd_hist, 1)
    
    # ── Step 2: 如果有持倉，檢查出場條件 ──
    if position and position.get("entry_price"):
        exit_result = check_exit_conditions(
            current_price=current_price,
            entry_price=position["entry_price"],
            bias50=bias50,
            feature=feature,
        )
        result["details"]["position"] = position
        result["details"]["exit_check"] = exit_result
        
        if exit_result["action"] == "SELL":
            result["signal"] = "SELL"
            result["urgency"] = exit_result["urgency"]
            result["message"] = f"出場: {exit_result['reason']}"
            return result
    
    # ── Step 3: 4H 方向 → 特徵入場確認 ──
    if direction_4h in ["BULL", "BEAR"]:
        feature_result = check_feature_entry(feature, direction_4h)
        result["details"]["feature"] = feature_result
        result["details"]["feature_reason"] = feature_result.get("reason", "")
        
        if feature_result["action"] in ["BUY", "SELL"]:
            result["signal"] = feature_result["action"]
            result["strength"] = feature_result["strength"]
            
            # 金字塔計算
            if position:
                pyramid = calculate_pyramid_entry(
                    position.get("entry_price", current_price),
                    current_price,
                    base_capital,
                    position.get("level", 0),
                )
                result["details"]["pyramid"] = pyramid
                
                if pyramid["action"] == "BUY":
                    result["urgency"] = "MEDIUM"
                    result["message"] = (
                        f"{direction_4h} 信號 | "
                        f"金字塔 {pyramid['message']} | "
                        f"特徵確認: {feature_result['reason']}"
                    )
                else:
                    result["message"] = (
                        f"{direction_4h} 信號 | {pyramid['message']} | "
                        f"特徵確認: {feature_result['reason']}"
                    )
            else:
                # 新進場
                result["urgency"] = "HIGH" if feature_result["strength"] >= 0.75 else "MEDIUM"
                pyramid = calculate_pyramid_entry(current_price, current_price, base_capital, 0)
                result["details"]["pyramid"] = pyramid
                result["message"] = (
                    f"{direction_4h} 信號 | {pyramid['message']} | "
                    f"特徵確認: {feature_result['reason']}"
                )
    
    else:
        # NEUTRAL
        result["signal"] = "HOLD"
        result["urgency"] = "NONE"
        result["message"] = (
            f"4H 中性 (bias50={bias50:+.1f}%) | 觀望等待明確信號"
        )
    
    return result
