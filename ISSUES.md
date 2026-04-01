# Poly-Trader Issues 追踪

> **最後更新：2026-04-02 03:39 GMT+8**
> **🔄 心跳 #51：fix #H59 feat_pulse 從 NEG_IC_FEATS 移除（IC=+0.019 正向被錯誤反轉），模型重訓；新增 #H60 feat_pulse/feat_mind 統計噪音待替換**
> **✅ 上輪修復：心跳 #50：新增 #H58 feat_tongue FNG 卡 8，升 P1；系統 6/6 通過**

---

## 🔴 危急 — 系統性問題

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H33 | 🟡 模型 CV=38.8%（數據不足，需持續收集） | 乾淨數據 2,228 筆，不足以提升 CV | 🟡 P1 — 持續收集（5min 排程中） |
| #H31 | 🔴 歷史 raw data polymarket_prob 幾乎全 NULL | Ear/Polymarket 歷史信號缺失 | 🔴 P1 |
| #H58 | 🔴 feat_tongue_pct 改為 volatility_24h（已替換，IC=-0.056 p=0.209 弱效），FNG 卡 NULL | 應替換為更有效信號 | 🔴 P1 |
| #H60 | 🔴 feat_pulse IC=+0.019 (p=0.667) 統計噪音；feat_mind IC=+0.020 (p=0.653) 統計噪音 | 兩個弱特徵稀釋模型有效信號 | 🔴 P1 — 新增！|

## 🟡 高優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H48 | 🟡 NEG_IC_FEATS 硬編碼，未動態更新 | feat_mind/feat_pulse 翻轉事件證明靜態硬編碼有風險 | 🟡 P2 |
| #H44 | 🟡 feat_pulse / feat_mind 有 NULL（早期數據） | 不影響近期收集 | 🟡 P2 |
| #H45 | 🟡 Labels 4,307 筆中有 2,147 筆無對應 features | Hourly labels vs 5-min features 對齊問題 | 🟡 P2 |

## 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|-------|------|
| #IC4 | 模型動態 IC 加權 | 實現感官動態權重 | 🟢 P3 |

## 🏆 已解決

| ID | 問題 | 解決方案 | 日期 |
|----|------|----------|------|
| **#H59** | **feat_pulse IC=+0.019 (正向) 誤放 NEG_IC_FEATS（被雙重反轉）** | **從 train.py + predictor.py 移除，重訓** | **04-02 03:39** |
| **#H56** | **feat_mind 全量 IC=+0.054 但誤放 NEG_IC_FEATS（原基於近500筆IC=-0.163）** | **從 train.py + predictor.py 移除，重訓** | **04-02 03:19** |
| **#H54** | **feat_mind funding_z_24 IC=+0.036（p=0.093, 2輪確認統計不顯著）** | **替換為 price_momentum_60（IC=-0.163）** | **04-02 03:09** |
| **#H54-prev** | **feat_aura fund_x_roc IC=-0.012** | **替換為 funding_zscore_288** | **04-02 02:59** |
| **#H53** | **feat_aura volume_zscore IC=-0.012** | **替換為 fund_x_roc** | **04-02 02:49** |
| **#H36b** | **feat_pulse 誤放 NEG_IC_FEATS；feat_tongue_pct 漏放** | **修正 train.py+predictor.py** | **04-02 02:04** |
| **#H36** | **IC 負相關特徵方向反** | **train.py+predictor.py 加入 NEG_IC_FEATS 反轉** | **04-02 01:59** |
| **#H46** | **main.py 排程每小時一次** | **改為 interval(5min)** | **04-02 01:52** |
| **#D01** | **TypeScript tsc Permission denied** | **comprehensive_test.py 改用 nodejs + tsc.js** | **04-02 01:34** |
| **#H42** | feat_eye_dist/feat_pulse std≈0 | 縮放×10000（bps） | 04-02 00:19 |
| **#H43** | 8,760 筆 1969-era 污染數據 | 全部清除 | 04-02 00:06 |
| #H23 | 資料庫崩潰 | 90 天回填 | 04-01 17:16 |

---

## 📊 當前系統健康 (2026-04-02 03:39 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 2,228 筆 | ✅ |
| Features | 2,228 筆 | ✅ |
| Labels | 4,307 筆 | ✅ |
| 最新資料時間 | 2026-04-01 19:31 UTC | ✅ |
| BTC 當前 | $68,270 | ✅ |
| Funding | 0.000024 (極低/中性) | ℹ️ |
| OI ROC | +0.0087 | ℹ️ |
| **main.py 進程** | **5分鐘排程** | ✅ |

### 最新感官 IC（n=500, 近期）
| 感官 | IC 原始 | 在 NEG_IC_FEATS? | 有效 IC | 狀態 |
|------|---------|-----------------|--------|------|
| feat_eye_dist | -0.348 | ✅ 是 | +0.348 | ✅ 最強 |
| feat_ear_zscore | -0.126 | ✅ 是 | +0.126 | ✅ |
| feat_nose_sigmoid | -0.314 | ✅ 是 | +0.314 | ✅ 強 |
| feat_tongue_pct | -0.056 | ✅ 是 | +0.056 | ⚠️ 弱（p=0.209 不顯著）|
| feat_body_roc | -0.126 | ✅ 是 | +0.126 | ✅ |
| feat_pulse | +0.019 | ❌ 已移除 | +0.019 | 🔴 統計無效 p=0.667 |
| feat_aura | -0.190 | ✅ 是 | +0.190 | ✅ |
| feat_mind (price_momentum_60) | +0.020 | ❌ 移除 | +0.020 | 🔴 統計無效 p=0.653 |

### 模型性能（最新）
| 指標 | 值 | 評估 |
|------|------|------|
| Train Accuracy | 68.2% | ✅ 健康 |
| TimeSeries CV | 38.8% ± 5.2% | 🟡 需更多數據 |
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
| P1 | **持續累積乾淨數據**：現有 2,228 筆（5min 排程，每天新增 ~288 筆） | #H33 |
| P1 | **feat_pulse 替換**：IC=+0.019 (p=0.667) 統計噪音 → 考慮 OBV_z / bid-ask spread 方差 | #H60 |
| P1 | **feat_mind 替換**：IC=+0.020 (p=0.653) 統計噪音 → 考慮 BTC/ETH 相關係數 rolling 窗口 | #H60 |
| P2 | **NEG_IC_FEATS 動態化** — 避免再次手動錯漏 | #H48 |
| P3 | **IC 動態加權** | #IC4 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
