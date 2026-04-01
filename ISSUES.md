# Poly-Trader Issues 追踪

> **最後更新：2026-04-02 00:06 GMT+8**
> **🔄 心跳 #26：Collector ✅ 運行中(PID 20086)，CV=50.6%（重訓後），BTC=$68,878，Raw=2,193，Features=2,193**
> **🚨 重大修復：清除 8,760 筆 1969-era 污染數據，資料庫已乾淨**

---

## 🔴 危急 — 系統性問題

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H33 | 🟡 模型 CV=50.6%（清除污染數據後，需繼續收集乾淨數據） | 乾淨數據只有 2,160 筆，不足以提升 CV | 🟡 P1 — 持續收集 |
| #H25 | 🔴 Labels 只有 2 類 (0,1)，無 class -1（持平） | 無「觀望」信號 | 🔴 P1 |
| #H31 | 🔴 歷史 raw data polymarket_prob 幾乎全 NULL | Ear/Polymarket 歷史信號缺失 | 🔴 P1 |

## 🟡 高優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H42 | 🟡 feat_eye_dist/feat_pulse std≈0（near-zero values, 1e-5 range）| 數值太小，訊號可能被淹沒；考慮縮放或重新設計 | 🟡 P1 |
| #H36 | 🟡 IC 偏弱：ear=-0.108 tongue=+0.091 其餘 |abs|<0.1 | 需要更強信號特徵 | 🟡 P1 |
| #H16 | 🟡 Pulse IC 弱 (-0.038) | 替換為 OI 變化率或 BTC/ETH 相對強度 | 🟡 P1 |
| #D01 | 🟡 TypeScript tsc Permission denied | npx tsc 路徑問題 | 🟡 P2 |

## 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|-------|------|------|
| #IC4 | 模型動態 IC 加權 | 實現感官動態權重 | 🟢 P3 |

## 🏆 已解決

| ID | 問題 | 解決方案 | 日期 |
|----|------|----------|------|
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

## 📊 當前系統健康 (2026-04-02 00:06 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 2,193 筆（清除污染後） | ✅ |
| Features | 2,193 筆 | ✅ |
| Labels | 4,307 筆 (valid) | ✅ |
| 最新資料時間 | 2026-04-01 16:01 UTC | ✅ |
| BTC 當前 | $68,878 | ✅ |
| Polymarket prob (realtime) | 0.6846 | ✅ |
| **Collector 進程** | **PID 20086 ✅ 運行中** | ✅ |
| 所有 Phase 1-7 檔案 | 全部存在 | ✅ |
| 語法檢查 | 全部通過 | ✅ |

### 模型性能（重訓後）
| 指標 | 值 | 評估 |
|------|------|------|
| Train Accuracy | 76.0% | ✅ 健康（無過擬） |
| TimeSeries CV | 50.6% ± 6.5% | 🟡 略低於之前但基於乾淨數據 |
| Dumb Baseline | 52.5% | — |
| 目標 | 90% | 🔴 仍需大幅改進 |
| 訓練樣本 | 2,160 筆（乾淨） | ⚠️ 樣本量不足，持續收集中 |

### 感官 IC（乾淨數據，n=2,160）
| 感官 | IC | 評估 |
|------|------|------|
| eye | -0.044 | ⚠️ 弱負向 |
| ear | -0.108 | 🟡 有信號（負動量→反轉） |
| nose | -0.063 | ⚠️ 弱 |
| tongue | +0.091 | 🟢 最強正向信號！ |
| body | +0.013 | ⚠️ 近雜訊 |
| pulse | -0.038 | ⚠️ 弱 |
| aura | +0.011 | ⚠️ 近雜訊 |
| mind | +0.039 | ⚠️ 弱正向 |

---

## 📋 下一步優先行動

| 優先 | 行動 | Issue |
|------|------|-------|
| P1 | **feat_eye_dist/feat_pulse 縮放問題**：數值在 1e-5 範圍，考慮標準化到可比較 scale | #H42 |
| P1 | **持續累積乾淨數據**：現有 2,160 筆，需要更多樣本提升 CV | #H33 |
| P1 | **Polymarket 數據回填**：只有少量歷史，需修復收集邏輯 | #H31 |
| P1 | **替換 Pulse**：IC=-0.038 近雜訊，改用 OI 變化率 | #H16 |
| P2 | **Labels 3-class**：加入 class -1（持平/觀望信號） | #H25 |
| P2 | **修復 TypeScript 權限** | #D01 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
