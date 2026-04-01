# Poly-Trader Issues 追踪

> **最後更新：2026-04-02 01:59 GMT+8**
> **🔄 心跳 #40：IC 反轉修復完成，6個負相關特徵取反，Train=75.9% CV=49.4%，BTC=$68,349，Raw=2,209**
> **✅ 上輪修復：model/train.py + predictor.py 加入 NEG_IC_FEATS 反轉邏輯**

---

## 🔴 危急 — 系統性問題

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H33 | 🟡 模型 CV=49.4%（數據不足，需持續收集） | 乾淨數據只有 2,209 筆，不足以提升 CV | 🟡 P1 — 持續收集（5min 排程中） |
| #H25 | 🔴 Labels 只有 2 類 (0,1)，無 class -1（持平） | 無「觀望」信號 | 🔴 P1 |
| #H31 | 🔴 歷史 raw data polymarket_prob 幾乎全 NULL | Ear/Polymarket 歷史信號缺失 | 🔴 P1 |

## 🟡 高優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H36 | 🟡 多感官 IC 偏弱（全數負相關，|IC|<0.15 全量，近期 n=500 更強） | **✅ 已加入 IC 反轉（6特徵取反）** | **✅ 已修復** |
| #H44 | 🟡 feat_pulse / feat_mind 有 NULL | 早期數據缺失，不影響近期收集 | 🟡 P2 |
| #H45 | 🟡 Labels 4,307 筆中有 2,147 筆無對應 features | Hourly labels vs 5-min features 對齊問題，影響 IC 精確計算 | 🟡 P2 |

## 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|-------|------|
| #IC4 | 模型動態 IC 加權 | 實現感官動態權重 | 🟢 P3 |

## 🏆 已解決

| ID | 問題 | 解決方案 | 日期 |
|----|------|----------|------|
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

## 📊 當前系統健康 (2026-04-02 01:59 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 2,209 筆 | ✅ |
| Features | 2,209 筆 | ✅ |
| Labels | 4,307 筆 | ✅ |
| 最新資料時間 | 2026-04-01 17:56 UTC | ✅ |
| BTC 當前 | $68,349 | ✅ |
| FNG | 8 (極度恐懼) | ℹ️ |
| **main.py 進程** | **PID 4369 ✅ 5分鐘排程** | ✅ |

### 最新感官 IC（n=500, joined）
| 感官 | IC 原始 | IC 反轉後 | 狀態 |
|------|---------|-----------|------|
| feat_eye_dist | -0.368 | +0.368 | ✅ 強正相關 |
| feat_ear_zscore | -0.149 | +0.149 | ✅ 正相關 |
| feat_nose_sigmoid | -0.227 | +0.227 | ✅ 正相關 |
| feat_tongue_pct | +0.080 | +0.080 | 🟡 弱正 |
| feat_body_roc | -0.191 | +0.191 | ✅ 正相關 |
| feat_pulse | -0.058 | +0.058 | ⚠️ 弱 |
| feat_aura | -0.121 | +0.121 | ✅ 正相關 |
| feat_mind | +0.056 | +0.056 | ⚠️ 弱 |

### 模型性能（最新）
| 指標 | 值 | 評估 |
|------|------|------|
| Train Accuracy | 75.9% | ✅ 健康 |
| TimeSeries CV | 49.4% ± 3.8% | 🟡 需更多數據 |
| 訓練樣本 | 2,151 筆（合併後） | ⚠️ 持續收集中 |

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
| P1 | **持續累積乾淨數據**：現有 2,209 筆（5min 排程，每天新增 ~288 筆） | #H33 |
| P1 | **Labels 3-class**：加入 class -1（持平/觀望信號，±0.5% 閾值） | #H25 |
| P1 | **Polymarket 數據補全**：ear_zscore 目前用 price momentum 替代 | #H31 |
| P2 | **Labels-Features 對齊**：2,147 筆 hourly labels 無對應 feature | #H45 |
| P3 | **IC 動態加權** | #IC4 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
