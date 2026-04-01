# Poly-Trader Issues 追踪

> **最後更新：2026-04-02 04:05 GMT+8**
> **🔄 心跳 #53：fix #H61 save_labels_to_db no-op bug，labels 更新至 20:01 UTC，重訓 Train=54.9% CV=40.1%**
> **✅ 上輪修復：心跳 #52：fix #H60 feat_pulse v2 (pos_in_range_72, IC=-0.160) + feat_mind v2 (ret_72, IC=-0.146)**

---

## 🔴 危急 — 系統性問題

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H33 | 🟡 模型 CV=40.1%（數據不足，需持續收集） | 乾淨數據 2,225 筆訓練樣本 | 🟡 P1 — 持續收集（5min 排程中） |
| #H31 | 🔴 歷史 raw data polymarket_prob 幾乎全 NULL | Ear/Polymarket 歷史信號缺失 | 🔴 P1 |
| #H58 | 🔴 feat_tongue_pct 為 volatility_24h（IC=-0.068 弱效）| 應替換為更有效信號 | 🔴 P1 |


## 🟡 高優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H48 | 🟡 NEG_IC_FEATS 硬編碼，未動態更新 | 動態計算 IC 決定是否反轉 | 🟡 P2 |
| #H44 | 🟡 feat_pulse / feat_mind 有 NULL（早期數據） | 不影響近期收集 | 🟡 P2 |
| #H45 | 🟡 Labels 6,541 筆（含 4,307 舊 hourly + 2,234 新 5-min）時間戳混用 | 建議清除舊 hourly labels | 🟡 P2 |

## 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|---|------|------|
| #IC4 | 模型動態 IC 加權 | 實現感官動態權重 | 🟢 P3 |

## 🏆 已解決

| ID | 問題 | 解決方案 | 日期 |
|----|------|----------|------|
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

## 📊 當前系統健康 (2026-04-02 04:05 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 2,234 筆 | ✅ |
| Features | 2,234 筆 | ✅ |
| Labels | 6,541 筆（2,234 新 5-min + 4,307 舊 hourly） | ✅ |
| 最新資料時間 | 2026-04-01 20:01 UTC | ✅ |
| BTC 當前 | ~$68,100 | ✅ |
| Funding Rate | 0.0000314 (中性) | ℹ️ |
| OI ROC | +0.0087 | ℹ️ |
| **main.py 進程** | **5分鐘排程（重啟中）** | ✅ |

### 最新感官 IC（n=500, 近期，訓練前計算）
| 感官 | IC 原始 | NEG_IC_FEATS? | 有效 IC | 狀態 |
|------|---------|--------------|--------|------|
| feat_eye_dist | -0.353 | ✅ | +0.353 | ✅ 最強 |
| feat_ear_zscore | -0.167 | ✅ | +0.167 | ✅ |
| feat_nose_sigmoid | -0.178 | ✅ | +0.178 | ✅ |
| feat_tongue_pct | +0.090 | ✅ (反轉後=-0.090) | -0.090 | ⚠️ 方向可疑 |
| feat_body_roc | -0.235 | ✅ | +0.235 | ✅ |
| feat_pulse v2 | -0.225 | ✅ | +0.225 | ✅ |
| feat_aura | -0.255 | ✅ | +0.255 | ✅ |
| feat_mind v2 | -0.300 | ✅ | +0.300 | ✅ 強 |

### 模型性能（最新，#53 重訓）
| 指標 | 值 | 評估 |
|------|------|------|
| Train Accuracy | 54.9% | ✅ 過擬合改善（71%→55%） |
| TimeSeries CV | 40.1% ± 3.4% | 🟡 需更多數據 |
| 訓練樣本 | 2,225 筆 | ⚠️ 持續收集中 |

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
| P1 | **feat_tongue 替換**：IC 方向混亂（raw IC=+0.090 on 500-row，全量=-0.068），考慮替換為 stablecoin_mcap 或其他信號 | #H58 |
| P1 | **清除舊 hourly labels**：6,541 中有 4,307 是 hourly backfill，可能稀釋訓練信號 | #H45 |
| P1 | **持續累積乾淨數據**：現有 2,234 筆（5min 排程，每天新增 ~288 筆） | #H33 |
| P2 | **NEG_IC_FEATS 動態化** — 避免再次手動錯漏 | #H48 |
| P3 | **IC 動態加權** | #IC4 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
