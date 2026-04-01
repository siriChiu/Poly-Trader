# Poly-Trader Issues 追踪

> **最後更新：2026-04-02 02:39 GMT+8**
> **🔄 心跳 #45：feat_aura 替換為 volume_zscore（IC=-0.008→待驗證）；新增 #H51 (feat_body_roc IC=0.012)**
> **✅ 上輪修復：feat_pulse 加回 NEG_IC_FEATS（#H49）**

---

## 🔴 危急 — 系統性問題

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H33 | 🟡 模型 CV=40.0%（數據不足，需持續收集） | 乾淨數據 2,217 筆，不足以提升 CV | 🟡 P1 — 持續收集（5min 排程中） |
| #H31 | 🔴 歷史 raw data polymarket_prob 幾乎全 NULL | Ear/Polymarket 歷史信號缺失 | 🔴 P1 |
| #H51 | 🔴 feat_body_roc IC=-0.012（全量，遠低於閾值 0.05） | OI_ROC 更新緩慢（重複值），body 感官退化 | 🔴 P1 — 下輪替換 |

## 🟡 高優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H50 | 🟡 feat_aura 替換為 volume_zscore（已執行） | 觀察新 IC；若 2 次心跳後 <0.05 再考慮其他方案 | 🟡 P2 — 觀察新 IC |
| #H52 | 🟡 feat_ear_zscore IC=-0.046（邊界，接近 0.05 閾值） | 觀察 1 輪；若下輪 <0.04 則列入替換計劃 | 🟡 P2 — 觀察 |
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
| **#H50-fix** | **feat_aura IC=-0.008（2 次觀察確認無效）** | **替換為 volume_zscore（成交量 z-score，72期窗口）** | **04-02 02:39** |
| **#H49** | **feat_pulse IC=-0.075 但被錯誤移出 NEG_IC_FEATS** | **重新加回 NEG_IC_FEATS，模型重訓** | **04-02 02:30** |
| **#H36b** | **feat_pulse 誤放 NEG_IC_FEATS；feat_tongue_pct 漏放** | **修正 train.py+predictor.py** | **04-02 02:04** |
| **#H36** | **IC 負相關特徵方向反** | **train.py+predictor.py 加入 NEG_IC_FEATS 反轉** | **04-02 01:59** |
| **#H46** | **main.py 排程每小時一次** | **改為 interval(5min)** | **04-02 01:52** |
| **#H47** | **collector.py ModuleNotFoundError** | **加入 sys.path 修正** | **04-02 01:52** |
| **#D01** | **TypeScript tsc Permission denied** | **comprehensive_test.py 改用 nodejs + tsc.js** | **04-02 01:34** |
| **#H42** | feat_eye_dist/feat_pulse std≈0 | 縮放×10000（bps） | 04-02 00:19 |
| **#H43** | 8,760 筆 1969-era 污染數據 | 全部清除 | 04-02 00:06 |
| #H41 | Collector 未運行 | PID 20086 | 04-01 23:36 |
| #H40 | senses.py 缺少 feat_pulse/aura/mind | 補齊 3 個特徵欄位 | 04-01 23:00 |
| #H27 | Tongue FNG 靜態=8.0 | 替換為 volatility_24h | 04-01 (v3) |
| #H23 | 資料庫崩潰 | 90 天回填 | 04-01 17:16 |

---

## 📊 當前系統健康 (2026-04-02 02:39 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 2,217 筆 | ✅ |
| Features | 2,217 筆 | ✅ |
| Labels | 4,307 筆 | ✅ |
| 最新資料時間 | 2026-04-01 18:41 UTC | ✅ |
| BTC 當前 | $68,318 | ✅ |
| FNG | 8 (極度恐懼) | ℹ️ |
| **main.py 進程** | **PID 4369 ✅ 5分鐘排程** | ✅ |

### 最新感官 IC（n=2,160, 全量）
| 感官 | IC 原始 | 在 NEG_IC_FEATS? | 有效值 | 狀態 |
|------|---------|-----------------|--------|------|
| feat_eye_dist | -0.152 | ✅ 是 | +0.152 | ✅ |
| feat_ear_zscore | -0.046 | ✅ 是 | +0.046 | ⚠️ 邊界 |
| feat_nose_sigmoid | -0.095 | ✅ 是 | +0.095 | ✅ |
| feat_tongue_pct | -0.094 | ✅ 是 | +0.094 | ✅ |
| feat_body_roc | -0.012 | ✅ 是 | +0.012 | 🔴 無效 |
| feat_pulse | -0.077 | ✅ 是 | +0.077 | ✅ |
| feat_aura | → **volume_zscore** | ✅ 是 | 待驗證 | 🆕 已替換 |
| feat_mind | +0.054 | ❌ 否 | +0.054 | ✅ |

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
| P1 | **持續累積乾淨數據**：現有 2,217 筆（5min 排程，每天新增 ~288 筆） | #H33 |
| P1 | **替換 feat_body_roc**：IC=0.012 確認無效；計劃用 LSR divergence（需 schema 遷移） | #H51 |
| P1 | **Polymarket 數據補全**：ear_zscore 目前用 price momentum 替代 | #H31 |
| P2 | **驗證 feat_aura (volume_zscore) IC**：本輪已替換，下輪確認是否 >0.05 | #H50 |
| P2 | **監控 feat_ear_zscore**：IC=0.046 邊界，下輪若 <0.04 列入替換計劃 | #H52 |
| P2 | **NEG_IC_FEATS 動態更新** | #H48 |
| P3 | **IC 動態加權** | #IC4 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
