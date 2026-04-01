# Poly-Trader Issues 追踪

> **最後更新：2026-04-02 01:34 GMT+8**
> **🔄 心跳 #38：Collector ✅ 運行中，CV=49.7%，BTC=$68,757，Raw=2,208，Features=2,208**
> **✅ 上輪：#D01 TypeScript tsc 修復 — comprehensive_test 改用 nodejs 路徑，6/6 全通過**

---

## 🔴 危急 — 系統性問題

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H33 | 🟡 模型 CV=49.7%（數據不足，需持續收集） | 乾淨數據只有 2,208 筆，不足以提升 CV | 🟡 P1 — 持續收集 |
| #H25 | 🔴 Labels 只有 2 類 (0,1)，無 class -1（持平） | 無「觀望」信號 | 🔴 P1 |
| #H31 | 🔴 歷史 raw data polymarket_prob 幾乎全 NULL | Ear/Polymarket 歷史信號缺失 | 🔴 P1 |

## 🟡 高優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H36 | 🟡 多感官 IC 偏弱（最強 eye/nose/ear 約 -0.09，其餘 |IC|<0.08） | 需要更強信號特徵 | 🟡 P1 |
| #H44 | 🟡 feat_pulse / feat_mind 有 9 筆 NULL | 早期數據缺失，不影響近期收集 | 🟡 P2 |
| #H45 | 🟡 Labels 4,307 筆中有 2,147 筆無對應 features | Hourly labels vs 5-min features 對齊問題，影響 IC 精確計算 | 🟡 P2 |

## 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|-------|------|
| #IC4 | 模型動態 IC 加權 | 實現感官動態權重 | 🟢 P3 |

## 🏆 已解決

| ID | 問題 | 解決方案 | 日期 |
|----|------|----------|------|
| **#D01** | **TypeScript tsc Permission denied** | **comprehensive_test.py 改用 nodejs + tsc.js 直接執行；Dashboard.tsx ConfidenceData 補 error?: string** | **04-02 01:34** |
| **#H42** | feat_eye_dist/feat_pulse 數值 std≈0 | 縮放×10000（bps），Eye IC: -0.044→-0.129, Pulse IC: ≈0→-0.079 | 04-02 00:19 |
| **#H43** | 8,760 筆 1969-era 污染數據 | 從 features/labels/raw 全部清除，重訓模型 | 04-02 00:06 |
| #H41 | Collector 未運行 | 已確認 PID 20086 運行中 | 04-01 23:36 |
| #H40 | senses.py 缺少 feat_pulse/aura/mind | 補齊 3 個特徵欄位 | 04-01 23:00 |
| #H39 | feat_mind 最新行 NULL | 已修復 | 04-01 22:14 |
| #H38 | feat_pulse/mind/tongue/body NULL | 批次重算 | 04-01 21:53 |
| #H16 | Body IC 極弱 | 替換為 MACD_pct (IC=-0.072) | 04-02 01:19 |
| #H27 | Tongue FNG 靜態=8.0 | 替換為 volatility_24h | 04-01 (v3) |
| #H23 | 資料庫崩潰 | 90 天回填 → 2166 rows | 04-01 17:16 |

---

## 📊 當前系統健康 (2026-04-02 01:34 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 2,208 筆 | ✅ |
| Features | 2,208 筆 | ✅ |
| 最新資料時間 | 2026-04-01 17:18 UTC | ✅ |
| BTC 當前 | $68,757 | ✅ |
| **Collector 進程** | **PID 3067/3068 ✅ 運行中** | ✅ |

### 最新感官讀數 (17:18 UTC)
| 感官 | 值 | IC | 說明 |
|------|-----|-----|------|
| feat_eye_dist | 0.0172 | -0.089 | 技術面（中性偏弱） |
| feat_ear_zscore | 0.0144 | -0.091 | 市場共識（中性偏空） |
| feat_nose_sigmoid | 0.0831 | -0.103 | 資金費率（轉多） |
| feat_tongue_pct | 0.0012 | -0.076 | 情緒（中性偏低） |
| feat_body_roc | 0.2384 | -0.072 | 清算壓力（偏低） |
| feat_pulse | -0.0197 | -0.055 | 脈搏（微弱偏空） |
| feat_aura | 0.3742 | -0.026 | Aura（偏多，弱信號） |
| feat_mind | -1.4347 | +0.063 | Mind（強烈偏空） |

### 模型性能（最新）
| 指標 | 值 | 評估 |
|------|------|------|
| Train Accuracy | 75.6% | ✅ 健康（無過擬） |
| TimeSeries CV | 49.7% ± 4.6% | 🟡 略低，需更多數據 |
| 訓練樣本 | 2,208 筆 | ⚠️ 持續收集中 |

### 測試狀態
| 項目 | 狀態 |
|------|------|
| 檔案結構 | ✅ PASS |
| 語法檢查 | ✅ PASS |
| 模組導入 | ✅ PASS |
| 感官引擎 | ✅ PASS |
| 前端 TypeScript | ✅ PASS（修復 #D01） |
| 數據品質 | ✅ PASS |
| **總計** | **6/6** |

---

## 📋 下一步優先行動

| 優先 | 行動 | Issue |
|------|------|-------|
| P1 | **持續累積乾淨數據**：現有 2,208 筆，目標 5,000+ 以提升 CV | #H33 |
| P1 | **Polymarket 數據回填**：只有少量歷史，需修復收集邏輯 | #H31 |
| P1 | **Labels 3-class**：加入 class -1（持平/觀望信號） | #H25 |
| P2 | **Labels-Features 對齊**：2,147 筆 hourly labels 無對應 feature（可能影響 IC） | #H45 |
| P3 | **IC 動態加權** | #IC4 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
