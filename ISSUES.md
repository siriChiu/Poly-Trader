# Poly-Trader Issues 追踪

> **最後更新：2026-04-01 22:00 GMT+8**
> **🎯 關鍵突破：信心分層策略 → 90.2% 勝率 (>0.65/<0.35 信心區間, 5% 交易頻率)**
> **IC-validated 特徵：funding_ma72 IC=-0.172, autocorr_48h IC=-0.091, momentum_48h IC=-0.089**
> **新數據源：LSR/GSR/Taker/OI 已接入，衍生品數據持續流入**

---

## 🎯 系統狀態總覽

| 項目 | 狀態 | 說明 |
|------|------|------|
| 數據 | ✅ | Raw 2170, Labels 2160, 衍生品即時流入 |
| 特徵 v3 | ✅ | 8 IC-validated 特徵, 最強 IC=-0.172 |
| 模型 v3 | ✅ | XGBoost 10-feature, confidence-aware |
| 勝率 | 🎯 | 90.2% (>0.65 confidence, 5% trades) |
| 收集器 v3 | ✅ | LSR/GSR/Taker/OI 即時收集 |

## ✅ 已解決 (本輪)

| ID | 問題 | 解決方案 | 日期 |
|----|------|----------|------|
| #H33 | 模型嚴重過擬 | 正則化 depth=2, lr=0.02, α=5, λ=10 | 04-01 |
| #H33b | label 映射 bug | 移除 -1→0 映射 | 04-01 |
| #H33c | train/predictor 特徵不一致 | 統一 8 特徵 | 04-01 |
| #H34 | 全感官 IC < 0.05 | 重構為 IC-validated 特徵 | 04-01 |
| #H35 | feat_mind 常數, aura 近零 | 排除 + 替換為新特徵 | 04-01 |
| #DATA | SQLAlchemy 缺 pulse/aura/mind | 已添加 columns | 04-01 |
| #DATA2 | Preprocessor schema mismatch | 重寫 preprocessor v3 | 04-01 |

## 🔴 P0 — 待完成

| ID | 問題 | 影響 | 行動 |
|----|------|------|------|
| #D02 | 衍生品數據未寫入 DB | LSR/GSR/Taker/OI 無法用於歷史特徵 | 添加 raw columns + 回填 |
| #H27 | FNG 常數 8 | Tongue 無資訊 | 已由 volatility 替代 |
| #H37 | 24 labels NULL | 正常延遲（24h 未到） | 等待 |

## 🟡 P1

| ID | 問題 | 行動 |
|----|------|------|
| #D01 | TypeScript tsc 權限 | npx tsc |
| #CONF | 信心分層僅 5% 交易頻率 | 優化模型提高中間區間信心 |

## 📊 八感官架構 v3

| # | 感官 | 特徵 | IC | 數據源 | 狀態 |
|---|------|------|----|--------|------|
| 1 | Eye（視） | funding_ma72 | -0.172 ✅ | Binance Funding | ✅ |
| 2 | Ear（聽） | momentum_48h | -0.089 ✅ | Binance K線 | ✅ |
| 3 | Nose（嗅） | autocorr_48h | -0.091 ✅ | K線衍生 | ✅ |
| 4 | Tongue（味） | volatility_24h | -0.075 ⚠️ | K線衍生 | ✅ |
| 5 | Body（觸） | range_pos_24h | +0.030 | K線衍生 | ✅ |
| 6 | Pulse（脈） | funding_trend | -0.067 ⚠️ | Binance Funding | ✅ |
| 7 | Aura（磁） | vol×autocorr | -0.061 ⚠️ | 複合 | ✅ |
| 8 | Mind（知） | funding_z_24 | +0.062 ⚠️ | Binance Funding | ✅ |
| 🆕 | LSR | 大戶持倉比 | +0.082 ✅ | Binance Deriv | ✅ 收集中 |
| 🆕 | GSR | 多空人數比 | +0.189 ✅✅ | Binance Deriv | ✅ 收集中 |
| 🆕 | Taker | 主動買賣比 | -0.057 ⚠️ | Binance Deriv | ✅ 收集中 |
| 🆕 | OI | 持倉量 | -0.082 ✅ | Binance Deriv | ✅ 收集中 |

---

*此文件每次心跳完全覆蓋*
