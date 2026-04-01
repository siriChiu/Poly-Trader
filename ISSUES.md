# Poly-Trader Issues 追踪

> **最後更新：2026-04-01 21:53 GMT+8**
> **🆙 心跳 #3 修復成果：Aura 特徵洩漏修復，CV=54.8% (>基線52.5%)，首次突破！**
> **comprehensive_test: 5/6 通過 (TypeScript tsc 權限問題 #D01)**

---

## 🔴 危急 — 系統性問題

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H33 | 🟡 模型 CV=54.8% 超過基線但仍需提升至 90% | 距目標仍遠 | 🟡 P1 — 繼續優化 |
| #H34 | 🟡 多感官 IC < 0.10：最高 Nose=-0.103，Mind=+0.095 | 信號弱但已有用 | 🟡 P1 — 繼續改進 |
| #H25 | 🔴 Labels 只有 2 類 (0,1)，無 class -1（持平） | 無「觀望」信號 | 🔴 P1 |
| #H26 | 🟡 Body ROC 現為連續值（已修復 v2 recompute bug） | 已修復 | ✅ |
| #H27 | 🔴 Tongue FNG API 仍返回極端值 8.0 | FNG 靜態=8 | 🔴 P1 需替換 API |
| #H31 | 🔴 歷史 raw data volume/FNG/ear_prob 幾乎全 NULL | 回填不完整 | 🔴 P1 |
| #H32 | 🔴 Polymarket prob 非 NULL 僅 9 筆 | collector 才寫 | 🔴 P1 |

## 🟡 高優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H36 | 🟡 Ear 用 price momentum（可能與 Eye/Aura 共線） | 確認相關性，考慮解耦 | 🟡 P1 |
| #H16 | 🟡 Eye IC=-0.089 仍弱 | 考慮多時間框架 eye | 🟡 P2 |
| #D01 | 🟡 TypeScript tsc Permission denied | npx tsc 路徑問題 | 🟡 P2 |
| #M06 | 🟡 缺少 lag features (1h/4h/24h) | 增加時間滯後特徵 | 🟡 P1 |
| #M13 | 缺少 volume 回填 | volume 只有 9 筆 | 🟡 P2 |

## 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H15 | Tongue FNG 靜態 | 社交情緒/put-call ratio | 🟢 P2 |
| #IC4 | 模型動態 IC 加權 | 實現感官動態權重 | 🟢 P3 |

## 🏆 已解決

| ID | 問題 | 解決方案 | 日期 |
|----|------|----------|------|
| #H38 | feat_pulse/mind/tongue/body 全為 NULL/常數 | 批次重算，修復 v2 recompute | 04-01 21:53 |
| Aura leakage | Nose×Aura 相關 0.91 | Aura 重設為 price vs funding 背離 | 04-01 21:53 |
| model_metrics | 無法追蹤 CV accuracy | 新增 model_metrics 表 + train.py 自動寫入 | 04-01 21:53 |
| #H33b | 模型標籤映射 bug | labels 已是 0/1，移除 -1→0 映射 | 04-01 21:24 |
| #H33c | train/predictor 特徵不一致 | 統一為 8 特徵 | 04-01 21:24 |
| #H33d | 模型嚴重過擬 (96.9%) | 正則化加強: depth 3, lr 0.03 | 04-01 21:24 |
| #H23 | 資料庫崩潰 | 90 天回填 → 2166 rows | 04-01 17:16 |
| #H24 | Collector 數據卡死 | backlog filled, realtime OK | 04-01 17:16 |

---

## 📊 當前系統健康 (2026-04-01 21:53)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 2169 筆 | ✅ |
| Features | 2169 筆（全欄位完整） | ✅ |
| Labels | 2160 筆 (0: 1179, 1: 981) | ✅ |
| BTC 當前 | $68,488 | ✅ |
| FNG | 8.0 (Extreme Fear, 靜態) | 🔴 |
| Collector | PID 20086 (運行中) | ✅ |

### 感官 IC (vs labels, ~2160 samples)
| 特徵 | IC_label | 設計說明 | 狀態 |
|------|----------|----------|------|
| Eye | -0.089 | funding_ma72 | 🟡 |
| Ear | -0.091 | momentum_48h | 🟡 |
| Nose | -0.103 | autocorr_48h | 🟡 最強 |
| Tongue | -0.047 | volatility_24h | 🟡 |
| Body | -0.011 | range_pos_24h | 🔴 弱 |
| Pulse | -0.067 | funding_trend | 🟡 |
| Aura | -0.051 | price vs funding 背離（🆕 已修復洩漏）| 🟡 |
| Mind | +0.095 | funding_z_24h | 🟡 最強正向 |

### 模型性能（心跳 #3 後）
| 指標 | 值 | 評估 |
|------|------|------|
| Train Accuracy | 73.1% | ✅ 健康 |
| TimeSeries CV | 54.8% ± 5.6% | 🟡 **首次超越基線 52.5%** |
| Dumb Baseline | 52.5% | — |
| 目標 | 90% | 🔴 仍需大幅改進 |

---

## 📋 下一步優先行動

| 優先 | 行動 | Issue |
|------|------|-------|
| P1 | **增加 lag 特徵**：price_ret_1h, price_ret_4h, price_ret_24h 時間滯後 | #M06 |
| P1 | **替換 Tongue**：FNG=8 常數，改用 DeFiLlama TVL 變化率 | #H27 |
| P1 | **回填 volume 數據**：只有 9 筆，Aura 需要 | #M13 |
| P2 | **解耦 Eye/Ear**：兩者可能與 Aura 存在共線性 | #H36 |
| P2 | **修復 TypeScript 權限** | #D01 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
