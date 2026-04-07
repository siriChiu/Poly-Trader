"""
融合特徵工程 v2 — 4H 結構框架 × 1min 即時感知

核心理念:
==========
- 4H 趨勢線/支撐線決定「方向」和「安全距離」→ 中長期交易的核心
- 1min 感官只在極端狀態下作為入場觸發器 → 精準狙擊
- 用交叉特徵讓 XGBoost 模型學習最佳組合，取代人工 if/else

融合公式:
         (靠近 4H 支撐) × (感官極端度) = 入場置信度
         越靠近支撐 × 感官越極端 = 得分越高
"""

import numpy as np
from typing import Dict, Optional


def compute_fusion_features(
    feat_4h_bias50: Optional[float],
    feat_4h_bias20: Optional[float],
    feat_4h_dist_swing_low: Optional[float],
    feat_4h_bb_pct_b: Optional[float],
    feat_4h_ma_order: Optional[float],
    feat_4h_rsi14: Optional[float],
    feat_4h_macd_hist: Optional[float],
    # 1min 即時感官 (v7 core senses)
    feat_nose: Optional[float],
    feat_tongue: Optional[float],
    feat_mind: Optional[float],
    feat_pulse: Optional[float],
    feat_eye: Optional[float],
    feat_ear: Optional[float],
    feat_body: Optional[float],
    feat_aura: Optional[float],
) -> Dict[str, float]:
    """
    計算融合特徵。返回 dict of new fusion features.
    
    設計原則:
    - 每個特徵都是連續數值 (非 0/1 硬閾值)
    - 交叉特徵讓模型自行學習最佳組合
    - 入場置信度閘門確保只有雙重條件才觸發
    """
    features = {}
    
    # ══════════════════════════════════════════
    # 1. 4H 支撐線接近度 (Support Proximity)
    #    越小 = 越靠近支撐 = 潛在買點
    # ══════════════════════════════════════════
    # 三種支撐: bias50(乖離率), swing_low, BB 下軌
    # bias50: -3% → bias20: -2% → swing: 1% → BB下軌: 0=在下軌, 1=在上軌
    
    d_bias50 = abs(feat_4h_bias50) if feat_4h_bias50 is not None else 10.0
    d_bias20 = abs(feat_4h_bias20) if feat_4h_bias20 is not None else 10.0
    d_swing = abs(feat_4h_dist_swing_low) if feat_4h_dist_swing_low is not None else 10.0
    # bb_pct_b: 0=在下軌(支撐) 1=在上軌 → 距離支撐 = pct_b * 典型波動
    d_bb = max(0.0, (feat_4h_bb_pct_b or 0.5) * 5.0)  # 假設典型波動 5%
    
    # 最近支撐距離 (取最小值)
    features['feat_4h_support_proximity'] = float(min(d_bias50, d_bias20, d_swing, d_bb))
    
    # 是否「跌穿/貼近」支撐區 (超賣) → 連續值非 0/1
    # bias50 < -2% OR dist_swing_low < 2% → 貼近/跌破支撐
    below_signals = []
    if feat_4h_bias50 is not None:
        below_signals.append(np.clip(1.0 + feat_4h_bias50 / 3.0, 0.0, 1.0))  # -3% → 1.0, 0% → 0
    if feat_4h_dist_swing_low is not None:
        below_signals.append(np.clip(1.0 - feat_4h_dist_swing_low / 3.0, 0.0, 1.0))  # 0% → 1.0, 3% → 0
    if feat_4h_bb_pct_b is not None:
        below_signals.append(np.clip(1.0 - feat_4h_bb_pct_b, 0.0, 1.0))  # 0 → 1.0, 1 → 0
    features['feat_4h_below_support'] = float(np.mean(below_signals) if below_signals else 0.0)


    # ══════════════════════════════════════════
    # 2. 4H 支撐收斂/共振 (Confluence / Resonance)
    #    多個支撐收斂在同一水平 → 支撐強度大增
    # ══════════════════════════════════════════
    if all(v is not None for v in [feat_4h_bias50, feat_4h_dist_swing_low, feat_4h_bb_pct_b]):
        supports = [d_bias50, d_swing, d_bb]
        std_val = float(np.std(supports))
        # confluence: 標準差越小(支撐越收斂) → 越接近 1
        features['feat_4h_confluence'] = float(np.exp(-std_val / 2.0))
        features['feat_4h_support_spread'] = std_val
    else:
        features['feat_4h_confluence'] = 0.0
        features['feat_4h_support_spread'] = 10.0


    # ══════════════════════════════════════════
    # 3. 4H 趨勢方向與強度
    #    +1 = 強烈多頭, -1 = 強烈空頭, 0 = 中性
    # ══════════════════════════════════════════
    if feat_4h_ma_order is not None:
        features['feat_4h_trend_direction'] = float(feat_4h_ma_order)  # ±1 from MA alignment
    else:
        features['feat_4h_trend_direction'] = 0.0
    
    # 趨勢強度: |bias50| 越大表示越偏離中性，可能越極端
    if feat_4h_bias50 is not None:
        # 用高斯核: 0% → 1.0(中性), ±10% → 0.03(極端偏離)
        features['feat_4h_bias50_extreme'] = float(np.exp(-(feat_4h_bias50 ** 2) / 50.0))
    else:
        features['feat_4h_bias50_extreme'] = 1.0


    # ══════════════════════════════════════════
    # 4. 1min 感官極端度 (Sensory Extremeness)
    #    只在"極端"狀態下才觸發入場，排除雜訊
    # ══════════════════════════════════════════
    def _extreme_score(val: Optional[float], low: float, high: float) -> float:
        """0 = 中性, 1 = 極端。越超出正常範圍越高。"""
        if val is None or np.isnan(val):
            return 0.0
        if val < low:
            return min(1.0, (low - val) / abs(low + 1e-10))
        elif val > high:
            return min(1.0, (val - high) / abs(1 - high + 1e-10))
        return 0.0
    
    # nose (RSI): 正常 0.3~0.7, <0.2 超賣, >0.8 超買
    nose_ext = _extreme_score(feat_nose, 0.2, 0.8)
    # tongue (mean-revert): 正常 ±0.02, >0.05 極端
    tongue_ext = min(1.0, abs(feat_tongue or 0) / 0.05)
    # mind (12h momentum): 正常 ±0.03, >0.10 極端
    mind_ext = min(1.0, abs(feat_mind or 0) / 0.10)
    # pulse (volume spike): <0.7 正常, >0.8 放量
    pulse_ext = max(0.0, min(1.0, ((feat_pulse or 0.5) - 0.7) / 0.3))
    # eye (trend/vol): <0.3 或 >0.7 極端
    eye_ext = _extreme_score(feat_eye, 0.3, 0.7)
    # ear (24h momentum): 正常 ±0.03, >0.08 極端
    ear_ext = min(1.0, abs(feat_ear or 0) / 0.08)
    # body (volatility z-score): <2 or >2 extreme
    body_ext = min(1.0, abs(feat_body or 0) / 3.0)
    
    extremes = [nose_ext, tongue_ext, mind_ext, pulse_ext, eye_ext, ear_ext, body_ext]
    
    # 極端度: 取前 3 高平均 (多個感官同時極端才有意義)
    top3 = sorted(extremes, reverse=True)[:3]
    features['feat_sensory_extreme'] = float(np.mean(top3))
    features['feat_sensory_max_extreme'] = float(max(extremes))
    
    # 各個感官極端度 (讓模型可以學習特定感官的權重)
    features['feat_nose_extreme'] = float(nose_ext)
    features['feat_tongue_extreme'] = float(tongue_ext)
    features['feat_mind_extreme'] = float(mind_ext)
    features['feat_pulse_extreme'] = float(pulse_ext)
    features['feat_eye_extreme'] = float(eye_ext)
    features['feat_ear_extreme'] = float(ear_ext)
    features['feat_body_extreme'] = float(body_ext)


    # ══════════════════════════════════════════
    # 5. 4H × 1min 交叉特徵 (讓模型學習!)
    #    靠近支撐 + 超賣極端 = 強烈做多訊號
    #    這完全取代手動 if/else
    # ══════════════════════════════════════════
    prox = features['feat_4h_support_proximity']
    # 越靠近支撐(越小prox) → 權重越高
    prox_weight = 1.0 / (1.0 + prox)  # prox=0 → 1.0, prox=5 → 0.17
    
    below = features['feat_4h_below_support']
    sensory = features['feat_sensory_extreme']
    confluence = features['feat_4h_confluence']
    
    # 交叉特徵: 4H 支撐 × 感官極端 (主融合信號)
    features['feat_4h_sup_x_sensory'] = float(below * prox_weight * sensory)
    
    # 細粒度交叉
    features['feat_4h_sup_x_nose_extreme'] = float(below * prox_weight * nose_ext)
    features['feat_4h_sup_x_tongue_extreme'] = float(below * prox_weight * tongue_ext)
    features['feat_4h_sup_x_mind_extreme'] = float(below * prox_weight * mind_ext)
    features['feat_4h_sup_x_pulse_extreme'] = float(below * prox_weight * pulse_ext)
    features['feat_4h_sup_x_eye_extreme'] = float(below * prox_weight * eye_ext)
    
    # 收斂 × 極端 (多個支撐聚集 + 感官極端 = 最強訊號)
    features['feat_4h_confluence_x_sensory'] = float(confluence * sensory)
    features['feat_4h_confluence_x_below_support'] = float(confluence * below)


    # ══════════════════════════════════════════
    # 6. 趨勢方向一致性 (4H vs 1min)
    #    如果 4H 方向和 1min 動量一致，加分
    # ══════════════════════════════════════════
    if feat_4h_bias50 is not None:
        # 4H 方向: 負 = 偏超賣(潛在反彈), 正 = 偏多
        bias_sign = 1.0 if feat_4h_bias50 > 0 else -1.0
        
        mind_sign = 1.0 if (feat_mind or 0) > 0 else -1.0
        ear_sign = 1.0 if (feat_ear or 0) > 0 else -1.0
        nose_sign = 1.0 if (feat_nose or 0.5) > 0.5 else -1.0
        
        # 方向一致: +1, 不一致: -1
        features['feat_4h_mind_direction'] = float(bias_sign * mind_sign)
        features['feat_4h_ear_direction'] = float(bias_sign * ear_sign)
        features['feat_4h_nose_direction'] = float(bias_sign * nose_sign)
    else:
        features['feat_4h_mind_direction'] = 0.0
        features['feat_4h_ear_direction'] = 0.0
        features['feat_4h_nose_direction'] = 0.0


    # ══════════════════════════════════════════
    # 7. RSI × MACD 確認 (4H 技術共振)
    # ══════════════════════════════════════════
    if feat_4h_rsi14 is not None and feat_4h_macd_hist is not None:
        rsi_norm = feat_4h_rsi14 / 100.0  # 0-1
        macd_dir = 1.0 if feat_4h_macd_hist > 0 else -1.0
        features['feat_4h_rsi_macd_confirm'] = float(rsi_norm * macd_dir)
        
        # 4H RSI 超買/超賣狀態
        if feat_4h_rsi14 < 30:
            features['feat_4h_rsi_oversold'] = (30.0 - feat_4h_rsi14) / 30.0
        elif feat_4h_rsi14 > 70:
            features['feat_4h_rsi_overbought'] = (feat_4h_rsi14 - 70.0) / 30.0
        else:
            features['feat_4h_rsi_oversold'] = 0.0
            features['feat_4h_rsi_overbought'] = 0.0
    else:
        features['feat_4h_rsi_macd_confirm'] = 0.0
        features['feat_4h_rsi_oversold'] = 0.0
        features['feat_4h_rsi_overbought'] = 0.0


    # ══════════════════════════════════════════
    # 8. 4H Bias50 歸一化 (用於金字塔分層)
    #    讓模型學習非线性關係，而非 if/else 分層
    # ══════════════════════════════════════════
    if feat_4h_bias50 is not None:
        bias = feat_4h_bias50
        # 歸一化到 -1~+1 (±10% 為極端)
        features['feat_4h_bias50_norm'] = float(np.clip(bias / 10.0, -1.0, 1.0))
        # 絕對值: 0 = 中性, 1 = 極端偏離
        features['feat_4h_bias50_abs'] = float(np.clip(abs(bias) / 10.0, 0.0, 1.0))
    else:
        features['feat_4h_bias50_norm'] = 0.0
        features['feat_4h_bias50_abs'] = 0.0


    # ══════════════════════════════════════════
    # 9. 入場置信度閘門 (非 if/else!)
    #    三條件的 soft 乘積: 都滿足才高分
    #    1) 靠近 4H 支撐 (below_support)
    #    2) 支撐收斂 (confluence)
    #    3) 感官極端 (sensory_extreme)
    # ══════════════════════════════════════════
    entry_confidence = (
        below * 0.40 +           # 40% 權重: 靠近支撐
        confluence * 0.30 +      # 30% 權重: 支撐共振
        (1.0 - prox_weight) * 0.30  # 30% 權重: 遠距離低置信度 (inverse)
    ) * sensory
    
    features['feat_entry_confidence'] = float(np.clip(entry_confidence, 0.0, 1.0))


    # ══════════════════════════════════════════
    # 10. Aura × 4H 方向對齊 (長期偏離 vs 中長期趨勢)
    # ══════════════════════════════════════════
    if feat_aura is not None and feat_4h_bias50 is not None:
        aura_sign = 1.0 if feat_aura > 0 else -1.0
        bias_sign = 1.0 if feat_4h_bias50 > 0 else -1.0
        features['feat_aura_4h_align'] = float(aura_sign * bias_sign)
    else:
        features['feat_aura_4h_align'] = 0.0


    return features
