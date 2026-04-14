# 2026-04-14 Feature Ablation + Calibration Notes

## Goal
在**不新增一堆使用者參數**的前提下，先從模型與特徵治理層面提升 accuracy / stability。

## Quick findings

### 1. Feature ablation（directional quick check）
使用最近 3000 rows、單一 holdout、輕量 XGBoost 快速比對：

- `core_only` (8 features) → **0.4856**
- `core_plus_4h` (18 features) → **0.4944**
- `current_full` (111 features) → **0.5100**

### Interpretation
- 只留 core features 目前不夠
- 加入 4H 結構有幫助，但提升有限
- full feature set 目前仍是這個快速檢查裡表現最好的組合
- 這表示短期內不適合直接大砍成「只有 core」
- 真正問題更像是：**full set 裡混有能拉高平均、但也可能拉高 variance 的弱特徵群**

## 2. Calibration quick check
以 70/30 split 快速檢查三個模型：

### Logistic Regression
- brier: **0.1877**
- avg_prob: **0.6958**
- top10 win rate: **0.8867**
- bottom10 win rate: **0.5524**

### Random Forest
- brier: **0.1937**
- avg_prob: **0.6347**
- top10 win rate: **1.0000**
- bottom10 win rate: **0.5722**

### XGBoost
- brier: **0.1887**
- avg_prob: **0.6697**
- top10 win rate: **1.0000**
- bottom10 win rate: **0.8074**

## Interpretation
- **Random Forest** 的高分桶仍然很強，符合先前 bear top-k OOS 證據
- **Logistic Regression** 的 calibration 沒有想像中那麼糟，但低分桶區分力普通
- **XGBoost** 最大問題不是 top bucket 不強，而是 **low-score bucket 失去區分力**
  - bottom10 win rate 仍高達 **0.8074**
  - 代表排序能力在某些切面上不夠乾淨

## Current conclusion
下一步應優先：

1. 對 full feature set 做更細的 **group ablation**
   - core
   - core + 4H
   - core + technical
   - core + macro
   - core + cross/lag

2. 專門檢查 **哪些特徵群在提高平均分數的同時拖累 worst fold**

3. 把 calibration 問題聚焦在：
   - 為何 XGBoost 的低分桶仍然偏高
   - 為何 RF 的 top bucket 強但整體 brier 未必最優

4. leaderboard 仍要保留現在的 deployment profile 改善，
   但必須承認：
   - **目前仍是手工 evidence-driven presets**
   - 還不是自動學出最佳 deployment lane
