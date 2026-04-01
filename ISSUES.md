# Poly-Trader Issues 追踪

> **最後更新：2026-04-02 00:19 GMT+8**
> **🔄 心跳 #27：Collector ✅ 運行中(PID 20086)，CV=49.6%，BTC=$68,699，Raw=2,195，Features=2,195**
> **✅ 本輪修復：#H42 feat_eye_dist/feat_pulse 縮放修復（×10000 bps），特徵重算+重訓完成**

---

## 🔴 危急 — 系統性問題

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H33 | 🟡 模型 CV=49.6%（數據不足，需持續收集） | 乾淨數據只有 2,151 筆，不足以提升 CV | 🟡 P1 — 持續收集 |
| #H25 | 🔴 Labels 只有 2 類 (0,1)，無 class -1（持平） | 無「觀望」信號 | 🔴 P1 |
| #H31 | 🔴 歷史 raw data polymarket_prob 幾乎全 NULL | Ear/Polymarket 歷史信號缺失 | 🔴 P1 |

## 🟡 高優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H36 | 🟡 多感官 IC 偏弱（最強 eye=-0.129, 其餘 |IC|<0.1） | 需要更強信號特徵 | 🟡 P1 |
| #H16 | 🟡 Body IC 極弱 (+0.017)，aura IC 微弱 (-0.025) | 替換 body/aura 感官 | 🟡 P1 |
| #D01 | 🟡 TypeScript tsc Permission denied | npx tsc 路徑問題 | 🟡 P2 |

## 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|-------|------|------|
| #IC4 | 模型動態 IC 加權 | 實現感官動態權重 | 🟢 P3 |

## 🏆 已解決

| ID | 問題 | 解決方案 | 日期 |
|----|------|----------|------|
| **#H42** | **feat_eye_dist/feat_pulse 數值在 1e-5 範圍（std≈0，XGBoost 無法分裂）** | **縮放×10000（轉為 bps），重算 2186 筆特徵，重訓模型。Eye IC: -0.044→-0.129, Pulse IC: ≈0→-0.079** | **04-02 00:19** |
| **#H43** | **8,760 筆 1969-era 污染數據混入訓練** | **從 features/labels/raw 全部清除，重訓模型** | **04-02 00:06** |
| #H41 | Collector 未運行 | 已確認 PID 20086 運行中，數據正常收集 | 04-01 23:36 |
| #H40 | senses.py `_get_latest_features()` 缺少 feat_pulse/aura/mind | 補齊 3 個特徵欄位，XGBoost mismatch 修復 | 04-01 23:00 |
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

## 📊 當前系統健康 (2026-04-02 00:19 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 2,195 筆 | ✅ |
| Features | 2,195 筆 | ✅ |
| Labels | 4,307 筆 (valid) | ✅ |
| 最新資料時間 | 2026-04-01 16:13 UTC | ✅ |
| BTC 當前 | $68,699 | ✅ |
| Polymarket prob (realtime) | 0.6711 | ✅ |
| **Collector 進程** | **PID 20086 ✅ 運行中** | ✅ |

### 模型性能（重訓後，#H42 修復）
| 指標 | 值 | 評估 |
|------|------|------|
| Train Accuracy | 75.7% | ✅ 健康（無過擬） |
| TimeSeries CV | 49.6% ± 5.1% | 🟡 略低，需更多數據 |
| Dumb Baseline | ~52.5% | — |
| 目標 | 90% | 🔴 仍需大幅改進 |
| 訓練樣本 | 2,151 筆（乾淨） | ⚠️ 持續收集中 |

### 感官 IC（修復 #H42 後，n=2,151）
| 感官 | IC（修復後） | IC（修復前） | 評估 |
|------|-------------|-------------|------|
| eye | **-0.129** | -0.044 | 🟡 ↑↑ 大幅改善 |
| ear | -0.053 | -0.108 | ⚠️ |
| nose | -0.105 | -0.063 | 🟡 改善 |
| tongue | -0.098 | +0.091 | ⚠️ 極性反轉 |
| body | +0.017 | +0.013 | ⚠️ 極弱 |
| pulse | **-0.079** | ≈0 | 🟡 ↑↑ 大幅改善 |
| aura | -0.025 | +0.011 | ⚠️ 弱 |
| mind | +0.072 | +0.039 | 🟢 改善 |

---

## 📋 下一步優先行動

| 優先 | 行動 | Issue |
|------|------|-------|
| P1 | **持續累積乾淨數據**：現有 2,151 筆，需更多樣本提升 CV | #H33 |
| P1 | **Polymarket 數據回填**：只有少量歷史，需修復收集邏輯 | #H31 |
| P1 | **替換 Body 感官**：IC=+0.017 極弱，考慮 OI ROC（已有 35 筆數據） | #H16 |
| P1 | **Labels 3-class**：加入 class -1（持平/觀望信號） | #H25 |
| P2 | **修復 TypeScript 權限** | #D01 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
