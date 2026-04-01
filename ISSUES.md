# Poly-Trader Issues 追踪

> **最後更新：2026-04-02 02:30 GMT+8**
> **🔄 心跳 #43：feat_pulse 方向修正（#H49），Train=68.1%, CV=40.0%**
> **✅ 上輪修復：feat_pulse IC=-0.075 加回 NEG_IC_FEATS，模型重新訓練**

---

## 🔴 危急 — 系統性問題

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H33 | 🟡 模型 CV=40.0%（數據不足，需持續收集） | 乾淨數據 2,214 筆，不足以提升 CV | 🟡 P1 — 持續收集（5min 排程中） |
| ~~#H25~~ | ~~Labels 只有 2 類~~ | ~~已修復：-1/0/1 三分類，±0.5% 閾值~~ | ✅ 04-02 02:20 |
| #H31 | 🔴 歷史 raw data polymarket_prob 幾乎全 NULL | Ear/Polymarket 歷史信號缺失 | 🔴 P1 |

## 🟡 高優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H48 | 🟡 NEG_IC_FEATS 硬編碼，未動態更新 | IC 隨數據積累可能變化，應定期重算並自動更新 | 🟡 P2 |
| #H44 | 🟡 feat_pulse / feat_mind 有 NULL | 早期數據缺失，不影響近期收集 | 🟡 P2 |
| #H45 | 🟡 Labels 4,307 筆中有 2,147 筆無對應 features | Hourly labels vs 5-min features 對齊問題 | 🟡 P2 |

## 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|-------|------|
| #IC4 | 模型動態 IC 加權 | 實現感官動態權重 | 🟢 P3 |

## 🏆 已解決

| ID | 問題 | 解決方案 | 日期 |
|----|------|----------|------|
| **#H49** | **feat_pulse IC=-0.075 但被錯誤移出 NEG_IC_FEATS** | **重新加回 NEG_IC_FEATS，模型重訓 (n=2151, Train=68.1%, CV=40.0%)** | **04-02 02:30** |
| **#H36b** | **feat_pulse 誤放 NEG_IC_FEATS（IC+0.01）；feat_tongue_pct 漏放** | **移除 pulse，加入 tongue，同步 train.py+predictor.py** | **04-02 02:04** |
| **#H36** | **IC 負相關特徵方向反** | **train.py+predictor.py 加入 NEG_IC_FEATS 反轉** | **04-02 01:59** |
| **#H46** | **main.py 排程每小時收集一次** | **改為 interval(5min)，每天可收集 288 筆** | **04-02 01:52** |
| **#H47** | **collector.py 直接執行時 ModuleNotFoundError** | **加入 sys.path 修正** | **04-02 01:52** |
| **#D01** | **TypeScript tsc Permission denied** | **comprehensive_test.py 改用 nodejs + tsc.js 直接執行** | **04-02 01:34** |
| **#H42** | feat_eye_dist/feat_pulse 數值 std≈0 | 縮放×10000（bps） | 04-02 00:19 |
| **#H43** | 8,760 筆 1969-era 污染數據 | 從 features/labels/raw 全部清除 | 04-02 00:06 |
| #H41 | Collector 未運行 | 已確認 PID 20086 運行中 | 04-01 23:36 |
| #H40 | senses.py 缺少 feat_pulse/aura/mind | 補齊 3 個特徵欄位 | 04-01 23:00 |
| #H27 | Tongue FNG 靜態=8.0 | 替換為 volatility_24h | 04-01 (v3) |
| #H23 | 資料庫崩潰 | 90 天回填 → 2166 rows | 04-01 17:16 |

---

## 📊 當前系統健康 (2026-04-02 02:30 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 2,214 筆 | ✅ |
| Features | 2,214 筆 | ✅ |
| Labels | 4,307 筆 | ✅ |
| 最新資料時間 | 2026-04-01 18:21 UTC | ✅ |
| BTC 當前 | $68,085 | ✅ |
| FNG | 8 (極度恐懼) | ℹ️ |
| **main.py 進程** | **PID 4369 ✅ 5分鐘排程** | ✅ |

### 最新感官 IC（n=500, raw值）
| 感官 | IC 原始 | 在 NEG_IC_FEATS? | 模型用值 |
|------|---------|-----------------|---------|
| feat_eye_dist | -0.343 | ✅ 是 | +0.343 |
| feat_ear_zscore | -0.138 | ✅ 是 | +0.138 |
| feat_nose_sigmoid | -0.344 | ✅ 是 | +0.344 |
| feat_tongue_pct | -0.066 | ✅ 是（剛修正） | +0.066 |
| feat_body_roc | -0.129 | ✅ 是 | +0.129 |
| feat_pulse | -0.075 | ✅ 是（修正加回） | +0.075 |
| feat_aura | -0.102 | ✅ 是 | +0.102 |
| feat_mind | +0.097 | ❌ 否 | +0.097 |

### 模型性能（最新）
| 指標 | 值 | 評估 |
|------|------|------|
| Train Accuracy | 68.1% | ✅ 健康 |
| TimeSeries CV | 40.0% ± 4.7% | 🟡 需更多數據 |
| 訓練樣本 | 2,151 筆 | ⚠️ 持續收集中 |

### 測試狀態
| 項目 | 狀態 |
|------|------|
| 檔案結構 | ✅ PASS |
| 語法檢查 | ✅ PASS |
| 模組導入 | ✅ PASS |
| 感官引擎 | ✅ PASS |
| 前端 TypeScript | ✅ PASS |
| 數據品質 | ✅ PASS |
| **總計** | **6/6** |

---

## 📋 下一步優先行動

| 優先 | 行動 | Issue |
|------|------|-------|
| P1 | **持續累積乾淨數據**：現有 2,210 筆（5min 排程，每天新增 ~288 筆） | #H33 |
| P1 | **Labels 3-class**：加入 class -1（持平/觀望信號，±0.5% 閾值） | #H25 |
| P1 | **Polymarket 數據補全**：ear_zscore 目前用 price momentum 替代 | #H31 |
| P2 | **NEG_IC_FEATS 動態更新**：每 N 筆數據重算一次 IC 並自動調整 | #H48 |
| P2 | **Labels-Features 對齊**：2,147 筆 hourly labels 無對應 feature | #H45 |
| P3 | **IC 動態加權** | #IC4 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
