# Poly-Trader Issues 追踪

> **最後更新：2026-04-02 04:15 GMT+8**
> **🔄 心跳 #54：fix #H62 偽標籤清除（4383筆）+ train.py h=1/non-NULL 過濾 + 重訓 Train=52.9% CV=39.2%**
> **✅ 上輪修復：心跳 #53：fix #H61 save_labels_to_db no-op bug，labels 更新至 20:01 UTC，重訓 Train=54.9% CV=40.1%**

---

## 🔴 危急 — 系統性問題

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H33 | 🟡 模型 CV=39.2%（需持續收集乾淨數據） | 2,150 筆訓練樣本，每天+288筆 | 🟡 P1 — 持續收集（5min 排程中） |
| #H31 | 🔴 歷史 raw data polymarket_prob 幾乎全 NULL | Ear/Polymarket 歷史信號缺失 | 🔴 P1 |
| #H58 | 🔴 feat_tongue_pct 為 volatility_24h（IC=-0.005 on h=1 全量，近乎白噪音）| 應替換為更有效信號 | 🔴 P1 |

## 🟡 高優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H48 | 🟡 NEG_IC_FEATS 硬編碼，未動態更新 | 動態計算 IC 決定是否反轉 | 🟡 P2 |
| #H63 | 🟡 IC 全量（h=1, n=2150）全 < 0.02（無統計顯著性） | 可能原因：1h horizon 對5min粒度信噪比太低；需研究更長 horizon 或聚合粒度 | 🟡 P1 |

## 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #IC4 | 模型動態 IC 加權 | 實現感官動態權重 | 🟢 P3 |

## 🏆 已解決

| ID | 問題 | 解決方案 | 日期 |
|----|------|----------|------|
| **#H62** | **偽標籤污染：4307筆h=24 hourly + 76筆h=1 NULL，稀釋/混淆訓練** | **清除4383筆偽標籤；train.py 過濾 horizon=1+non-NULL；重訓** | **04-02 04:15** |
| **#H61** | **save_labels_to_db() 是 no-op，labels 表停在 2026-04-01 01:00** | **修復函數實際寫入 Labels 表，trading_cycle 每輪更新，重訓 Train=54.9% CV=40.1%** | **04-02 04:05** |
| **#H60** | **feat_pulse IC=+0.019 → v2 pos_in_range_72 (IC=-0.160); feat_mind v2 (ret_72, IC=-0.146)** | **替換計算邏輯+回填+重訓** | **04-02 03:50** |
| **#H59** | **feat_pulse IC=+0.019 誤放 NEG_IC_FEATS** | **從 train.py + predictor.py 移除** | **04-02 03:39** |
| **#H56** | **feat_mind IC=+0.054 誤放 NEG_IC_FEATS** | **從 train.py + predictor.py 移除** | **04-02 03:19** |
| **#H54** | **feat_mind funding_z_24 IC=+0.036 不顯著** | **替換為 price_momentum_60（IC=-0.163）** | **04-02 03:09** |
| **#H54-prev** | **feat_aura fund_x_roc IC=-0.012** | **替換為 funding_zscore_288** | **04-02 02:59** |
| **#H53** | **feat_aura volume_zscore IC=-0.012** | **替換為 fund_x_roc** | **04-02 02:49** |
| **#H36b** | **feat_pulse/feat_tongue NEG_IC_FEATS 錯配** | **修正 train.py+predictor.py** | **04-02 02:04** |
| **#H36** | **IC 負相關特徵方向反** | **NEG_IC_FEATS 反轉邏輯** | **04-02 01:59** |
| **#H46** | **main.py 排程每小時一次** | **改為 interval(5min)** | **04-02 01:52** |
| **#D01** | **TypeScript tsc Permission denied** | **comprehensive_test.py 改用 nodejs + tsc.js** | **04-02 01:34** |
| **#H42** | feat_eye_dist/feat_pulse std≈0 | 縮放×10000（bps） | 04-02 00:19 |
| **#H43** | 8,760 筆 1969-era 污染數據 | 全部清除 | 04-02 00:06 |
| #H23 | 資料庫崩潰 | 90 天回填 | 04-01 17:16 |

---

## 📊 當前系統健康 (2026-04-02 04:15 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 2,235 筆 | ✅ |
| Features | 2,235 筆 | ✅ |
| Labels (h=1, clean) | 2,159 筆 | ✅ 已清除偽標籤 |
| 最新資料時間 | 2026-04-01 20:08 UTC | ✅ |
| BTC 當前 | ~$68,106 | ✅ |
| FNG | 8.0 (極度恐慌) | ⚠️ |
| Funding Rate | 0.0000350 (中性) | ℹ️ |
| OI ROC | +0.0085 | ℹ️ |
| **main.py 進程** | **5分鐘排程（運行中 PID 13573）** | ✅ |

### 感官 IC（h=1 全量 n=2150，統計現況）
| 感官 | IC (h=1 全量) | 顯著? | 狀態 |
|------|-------------|-------|------|
| feat_eye_dist (funding_ma72) | -0.010 | ❌ p=0.64 | ⚠️ 全量不顯著 |
| feat_ear_zscore (momentum_48h) | -0.009 | ❌ p=0.67 | ⚠️ |
| feat_nose_sigmoid (autocorr_48h) | -0.017 | ❌ p=0.42 | ⚠️ |
| feat_tongue_pct (volatility_24h) | -0.005 | ❌ p=0.82 | 🔴 待替換 |
| feat_body_roc (MACD%) | -0.014 | ❌ p=0.51 | ⚠️ |
| feat_pulse v2 (pos_in_range_72) | -0.016 | ❌ p=0.44 | ⚠️ |
| feat_aura (funding_zscore_288) | -0.007 | ❌ p=0.73 | ⚠️ 9 NaN |
| feat_mind v2 (ret_72) | -0.013 | ❌ p=0.53 | ⚠️ |

> ⚠️ IC 全量不顯著可能因：1h horizon 對 5min 粒度信噪比太低；h=24 全量有顯著IC但不用於訓練

### 模型性能（#54 重訓）
| 指標 | 值 | 評估 |
|------|----|----|
| Train Accuracy | 52.9% | ✅ 過擬合改善 |
| TimeSeries CV | 39.2% ± 2.1% | 🟡 需更多數據 |
| 訓練樣本 | 2,150 筆 (clean) | ⚠️ 持續收集中 |

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
| P1 | **調查 IC=0 原因**：1h horizon 信噪比 vs 聚合到小時粒度測試；對比 h=24 IC 顯著的信號 | #H63 |
| P1 | **feat_tongue 替換**：volatility_24h IC≈0，考慮 stablecoin_mcap ROC 或 put-call ratio | #H58 |
| P1 | **持續累積乾淨數據**：現有 2,159 筆（5min 排程，每天新增 ~288 筆） | #H33 |
| P2 | **NEG_IC_FEATS 動態化** — 避免再次手動錯漏 | #H48 |
| P3 | **IC 動態加權** | #IC4 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
