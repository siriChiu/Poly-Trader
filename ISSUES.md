# Poly-Trader Issues 追踪

> **最後更新：2026-04-01 22:14 GMT+8**
> **🔄 心跳 #7：Collector PID 20086 運行中，CV=54.8%，feat_mind=1.046（最新行已修復），Polymarket 仍 13/10933**

---

## 🔴 危急 — 系統性問題

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H33 | 🟡 模型 CV=54.8% 超過基線但仍需提升至 90% | 距目標仍遠 | 🟡 P1 — 繼續優化 |
| #H34 | 🟡 多感官 IC < 0.10：Eye=+0.043, Ear=-0.166, Nose=-0.169, Body=-0.102, Aura=-0.112 | 多為負向預測，樹模型可自動處理 | 🟡 P1 — 繼續改進 |
| #H25 | 🔴 Labels 只有 2 類 (0,1)，無 class -1（持平） | 無「觀望」信號 | 🔴 P1 |
| #H31 | 🔴 歷史 raw data polymarket_prob 幾乎全 NULL（13/10933 筆） | Ear/Polymarket 信號缺失 | 🔴 P1 |

## 🟡 高優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H36 | 🟡 Ear 用 price momentum（可能與 Eye/Aura 共線） | 確認相關性，考慮解耦 | 🟡 P1 |
| #H16 | 🟡 Pulse IC 弱 (+0.013，近雜訊) | 替換為 OI 變化率或 BTC/ETH 相對強度 | 🟡 P1 |
| #D01 | 🟡 TypeScript tsc Permission denied | npx tsc 路徑問題 | 🟡 P2 |

## 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #IC4 | 模型動態 IC 加權 | 實現感官動態權重 | 🟢 P3 |

## 🏆 已解決

| ID | 問題 | 解決方案 | 日期 |
|----|------|----------|------|
| #H39 | feat_mind 最新行 NULL | 已修復，最新行 feat_mind=1.046 ✅ | 04-01 22:14 |
| #H38 | feat_pulse/mind/tongue/body 全為 NULL/常數 | 批次重算，修復 v2 recompute | 04-01 21:53 |
| Predictor mismatch | feature_names mismatch (raw vs feat_*) | 重訓後 model/xgb_model.pkl 已覆蓋為 feat_* | 04-01 22:05 |
| Aura leakage | Nose×Aura 相關 0.91 | Aura 重設為 price vs funding 背離 | 04-01 21:53 |
| model_metrics | 無法追蹤 CV accuracy | 新增 model_metrics 表 + train.py 自動寫入 | 04-01 21:53 |
| #H27 | Tongue FNG 靜態=8.0 | 替換為 volatility_24h | 04-01 (v3) |
| #M13 | feat_tongue_pct 只有 6 unique 值 | v3 preprocessor 修復 | 04-01 (v3) |
| #H33b | 模型標籤映射 bug | labels 已是 0/1，移除 -1→0 映射 | 04-01 21:24 |
| #H33c | train/predictor 特徵不一致 | 統一為 8 特徵 | 04-01 21:24 |
| #H33d | 模型嚴重過擬 (96.9%) | 正則化加強: depth 3, lr 0.03 | 04-01 21:24 |
| #H23 | 資料庫崩潰 | 90 天回填 → 2166 rows | 04-01 17:16 |
| #H24 | Collector 數據卡死 | backlog filled, realtime OK | 04-01 17:16 |
| #M06 | lag 特徵 IC 測試 | ret_1h=0.008, ret_4h=0.003, ret_24h=0.087；不改善 CV，暫緩 | 04-01 |

---

## 📊 當前系統健康 (2026-04-01 22:14 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 10933 筆 | ✅ |
| Features | 2171 筆 | ✅ |
| feat_mind (最新行) | 1.046 | ✅ |
| Labels | 13067 筆 (0: 6855, 1: 6212) | ✅ |
| 最新資料時間 | 2026-04-01 14:13 UTC | ✅ |
| BTC 當前 | $68,157 | ✅ |
| Polymarket prob | 非空 13/10933 | 🔴 |
| Collector | PID 20086 (運行中) | ✅ |

### 感官 IC (vs labels, last 500 samples)
| 感官/特徵 | IC | 說明 | 狀態 |
|-----------|-----|------|------|
| Eye (feat_eye_dist) | +0.043 | funding_ma72 | 🟡 |
| Ear (feat_ear_zscore) | -0.166 | momentum_48h（負向） | 🟡 XGB 可用 |
| Nose (feat_nose_sigmoid) | -0.169 | autocorr_48h（負向最強） | 🟡 XGB 可用 |
| Tongue (feat_tongue_pct) | -0.066 | volatility_24h | 🟡 |
| Body (feat_body_roc) | -0.102 | range_pos_24h | 🟡 XGB 可用 |
| Pulse (feat_pulse) | +0.013 | funding_trend（近雜訊） | 🔴 弱 |
| Aura (feat_aura) | -0.112 | price vs funding 背離 | 🟡 XGB 可用 |
| Mind (feat_mind) | +0.097 | funding_z_24h（最強正向） | 🟡 |

### 模型性能（最新）
| 指標 | 值 | 評估 |
|------|------|------|
| Train Accuracy | 73.1% | ✅ 健康 |
| TimeSeries CV | 54.8% ± 5.6% | 🟡 **超越基線 52.5%** |
| Dumb Baseline | 52.5% | — |
| 目標 | 90% | 🔴 仍需大幅改進 |
| 特徵重要性 | 全部 10-14%（均衡分佈） | ✅ |
| 最後訓練 | 2026-04-01 14:05 UTC | ✅ |

---

## 📋 下一步優先行動

| 優先 | 行動 | Issue |
|------|------|-------|
| P1 | **替換 Pulse**：IC=+0.013 近雜訊，改用 OI 變化率或 BTC/ETH 相對強度 | #H16 |
| P1 | **Polymarket 數據回填**：只有 13 筆，需修復收集邏輯 | #H31 |
| P1 | **持續收集 realtime 數據**：增加訓練樣本量改善 CV | #H33 |
| P2 | **Labels 3-class**：加入 class -1（持平/觀望信號） | #H25 |
| P2 | **修復 TypeScript 權限** | #D01 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
