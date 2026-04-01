# Poly-Trader Issues 追踪

> **最後更新：2026-04-01 21:25 GMT+8**
> **🚨 關鍵發現：模型正則化後暴露真相 — 全感官 IC < 0.05，無任何預測力。TS-CV=50.5%（基線52.5%）**
> **comprehensive_test: 5/6 通過 (TypeScript tsc 權限問題 #D01)**

---

## 🔴 🚨 危急 — 系統性問題

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H33 | 🔴 模型無預測力：Train 59.1% / WF 42.1% / TS-CV 50.5%（基線52.5%） | 所有交易決策無效 | 🔴 P0 — 需新特徵 |
| #H34 | 🔴 全感官 IC < 0.05：Pulse 最高 0.0386，其餘 < 0.03 | 無感官達到可用閾值 | 🔴 P0 — 無有效信號 |
| #H35 | 🔴 feat_mind 常數 0（unique=1），feat_aura std=0.001 | 兩感官完全無資訊 | 🔴 P0 — 已從模型排除 |
| #H25 | 🔴 Labels 只有 2 類 (0,1) 無 class -1 | 無「持平」區間 | 🔴 維持 |
| #H26 | 🔴 Body ROC 粗粒度僅 7 unique 值 | 歷史回填離散化 | 🔴 需改用連續 ROC |
| #H27 | 🔴 Tongue FNG API 僅返回極端值 8.0 | FNG 卡死在 Extreme Fear | 🔴 需替換 API |
| #H31 | 🔴 2160/2167 raw rows FNG/funding/poly 為 NULL | 回填只寫 klines | 🔴 回填不完整 |
| #H32 | 🔴 Polymarket prob 非 NULL 僅 7 筆 | collector 新寫入 | 🔴 需修回填 |

## 🔴 高優先級

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H36 | 🔴 Ear 用 price momentum 做代理（回填） | 與 Eye 高度共線 | 🔴 需解耦 |
| #H37 | 🔴 24 筆 labels future_return_pct 為 NULL | 24h horizon 未到 | 🔴 正常延遲 |
| #H16 | 🟡 Eye IC=0.0209 極弱 | 預測力不足 | 🟡 需多時間框架 |
| #D01 | 🟡 TypeScript tsc Permission denied | 無法驗證前端 | 🟡 npx/tsc 權限 |

## 🟡 中優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #M06 | 缺少 lag features | 增加 1h/4h/24h 時間滯後特徵 | 🟡 下一步 |
| #H15 | Tongue 應汰換（FNG 靜態） | 找 Twitter/News sentiment API | 🟡 |

## 🏆 已解決

| ID | 問題 | 解決方案 | 日期 |
|----|------|----------|------|
| #H33b | 模型標籤映射 bug | labels 已是 0/1，移除 -1→0 映射 | 04-01 21:24 |
| #H33c | train/predictor 特徵不一致 | 統一為 6 特徵（排除 mind/aura） | 04-01 21:24 |
| #H33d | 模型嚴重過擬 (96.9%) | 正則化加强: depth 2, lr 0.01, α=5, λ=10 | 04-01 21:24 |
| #H28 ❌ | Ear prob 常數 | **誤判** — Ear 用 price momentum 回填，有 2083 unique | 04-01 17:33 修正 |
| #H23 | 🔴 資料庫崩潰 | 90 天回填 → 2166 rows | 04-01 17:16 |
| #H24 | 🔴 Collector 數據卡死 | backlog filled, realtime OK | 04-01 17:16 |

---

## 📊 當前系統健康 (2026-04-01 21:25)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 2167 筆 (2160 historical + 7 realtime) | ✅ |
| Features | 2166 筆 | ✅ |
| Labels | 2160 筆 (2-class: 0/1), 24 NULL (24h 未到) | ✅ |
| Model | XGBoost 6-feat, depth=2, 6-feature, ~60KB | ⚠️ 無預測力 |
| BTC 當前 | $68,564.14 | ✅ |
| FNG | 8.0 (Extreme Fear, 僅 7 筆 realtime) | 🔴 |
| Funding Rate | 3.031e-05 (僅 7 筆 realtime) | ⚠️ |

### 感官 IC (vs labels, 2136 valid samples)
| 特徵 | IC_label | IC_return | std | unique | 狀態 |
|------|----------|-----------|-----|--------|------|
| Eye | **+0.0209** | +0.0767 | 0.0191 | 2113 | 🔴 |
| Ear | -0.0695 | -0.1612 | 0.3528 | 191 | 🔴 |
| Nose | -0.0142 | -0.0241 | 0.2720 | 196 | 🔴 |
| Tongue | +0.0226 | +0.0214 | 0.2046 | 2133 | 🔴 |
| Body | +0.0093 | +0.0503 | 0.0039 | 2124 | 🔴 |
| Pulse | +0.0386 | +0.1048 | 0.5030 | 2124 | 🔴 |
| Aura | -0.0251 | -0.0031 | 0.0011 | 1562 | ❌ 已排除 |
| Mind | 0.0000 | 0.0000 | 0.0000 | 1 | ❌ 已排除 |

### 模型性能（正則化後）
| 指標 | 舊值 | 新值 | 評估 |
|------|------|------|------|
| Train Accuracy | 96.9% | **59.1%** | ✅ 過擬消除 |
| Walk-Forward | 53.3% | **42.1%** | 🔴 低於基線 |
| TimeSeries CV | — | **50.5% (±10.7%)** | 🔴 ≈ 隨機 (基線52.5%) |
| Overfit Gap | 43.7pp | **17.0pp** | ✅ 大幅改善 |
| Dumb Baseline | 52.5% | 52.5% | — |

**結論：正則化暴露真相 — 特徵無預測力。模型不再過擬，但學不到任何東西。**

---

## 📋 下一步 (ORID 決策)

| 優先 | 行動 | Issue | 指令 |
|------|------|-------|------|
| P0 | **設計新特徵**：lag (1h/4h/24h)、交互特徵、波動率 regime | #H33,#M06 | preprocessor 增加 |
| P0 | **替換 Nose**：改用 OI 變化率 / liquidation flow | #H20 | 新數據源 |
| P0 | **替換 Tongue**：FNG 常數 8 無效，改用社交情緒 | #H27,#H15 | 新 API |
| P0 | **Body 連續化**：移除離散化，用原始 ROC | #H26 | 改 preprocessor |
| P1 | **修復回填**：補充 FNG/funding/poly 歷史 raw 欄位 | #H31,#H32 | re-backfill |
| P2 | **引入鏈上數據**：Glassnode/Santiment 鏈上指標 | #H34 | 新數據源 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
