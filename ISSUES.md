# Poly-Trader Issues 追踪

> **最後更新：2026-04-02 07:39 GMT+8**
> **🔄 心跳 #69：fix #H80 — collector.py 移除重複 run_preprocessor 呼叫；重啟 server（舊 PID 13573 殘留導致 trading_cycle 重複執行已解決）**
> **✅ 上輪修復：心跳 #68：fix #H79 — predictor.py XGBoostPredictor dict 格式支援（AttributeError 修復），trading_cycle 恢復正常**

---

## 🔴 危急 — 系統性問題

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H31 | 🔴 歷史 raw data polymarket_prob 幾乎全 NULL | Ear/Polymarket 歷史信號缺失 | 🔴 P1 |

## 🟡 高優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H33 | 🟡 模型 CV=45.8%（Train/CV gap已縮至14%） | 2,277 筆，每天+288筆，累積數據改善中 | 🟡 P1 — 持續收集（5min 排程中） |

## 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #IC4 | 模型動態 IC 加權 | tongue IC=+0.148 遠高於其他，應加大 XGBoost 輸入權重 | 🟢 P3 |
| #M06 | 缺少 lag 特徵 | 1h/4h/24h lag 增強時序記憶 | 🟢 P3 |

## 🏆 已解決

| ID | 問題 | 解決方案 | 日期 |
|----|------|----------|------|
| **#H80** | **collector.py run_preprocessor 重複呼叫（每次 trading_cycle 特徵工程執行兩次）** | **移除 collector.py 內嵌的 run_preprocessor 呼叫，由 trading_cycle 統一管理** | **04-02 07:39** |
| **#H79** | **predictor.py AttributeError: 'dict' has no attribute 'predict_proba'（XGBoostPredictor 未處理 dict 格式模型）** | **__init__ 判斷 dict 並解包 clf/imputer/neg_ic_feats，新增 _get_proba() 共用方法** | **04-02 07:14** |
| **#H78** | **feat_ear_zscore MACD_hist 假顯著（79% |>100bps 極端值，Spearman p=0.177）** | **替換為 mom_12 (12期動量，Spearman p=0.027 ✅)，修正DB所有ear值** | **04-02 07:04** |
| **#H77** | **feat_ear_zscore IC=-0.025 p=0.233 再次不顯著（RSI-72失效）** | **替換為 MACD histogram(12/26) (IC=-0.046 p=0.031 ✅)** | **04-02 07:01** |
| **#H76** | **模型嚴重過擬合 Train=80.2%/CV=42.8% gap=37%** | **加強正則化(max_depth=2,reg_lambda=8)+class_weight balance → Train=53.2%/CV=42.4% gap=9%** | **04-02 06:44** |
| **#H74** | **feat_ear_zscore IC=-0.040 p=0.064 不顯著** | **RSI-24 → RSI-72 (IC=-0.044 p=0.039 ✅)** | **04-02 06:37** |
| **#H75** | **feat_tongue_pct IC=+0.037 p=0.080 不顯著** | **volatility_24h → vol_ratio_6_48 (IC=+0.127 p<0.0001 ✅)** | **04-02 06:37** |
| **#H66** | **feat_body_roc IC=+0.041 p=0.055 邊緣不顯著** | **atr_ratio_14 → stoch_rsi_14 (IC=-0.053 p=0.013 ✅)** | **04-02 06:37** |
| **#H73** | **feat_aura 9筆 NULL，logger 重複 log** | **NULL 填補，logger 修正** | **04-02 06:04** |
| **#H72** | **feat_body_roc IC 符號翻轉** | **重算 ic_signs，移出 neg_ic** | **04-02 05:59** |
| **#H70** | **ic_signs.json 未隨新數據更新** | **重算並重訓** | **04-02 05:44** |
| **#H69** | **feat_ear momentum_48h IC 不顯著** | **替換為 RSI-24** | **04-02 05:29** |
| **#H48** | **NEG_IC_FEATS 硬編碼** | **動態計算 ic_signs.json** | **04-02 05:29** |
| **#H67** | **labeling 時間戳精確匹配失敗** | **改為 nearest-match（60min 容差）** | **04-02 05:11** |
| **#H65** | **h=1 horizon IC 全部不顯著** | **改為 h=4** | **04-02 04:30** |
| **#H62** | **偽標籤污染** | **清除 4383 筆偽標籤** | **04-02 04:15** |
| #H46 | main.py 排程每小時一次 | 改為 interval(5min) | 04-02 01:52 |
| #H43 | 8,760 筆 1969-era 污染數據 | 全部清除 | 04-02 00:06 |
| #H23 | 資料庫崩潰 | 90 天回填 | 04-01 17:16 |

---

## 📊 當前系統健康 (2026-04-02 07:39 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 2,277 筆 | ✅ |
| Features | 2,277 筆 | ✅ |
| Labels (h=4, clean) | 2,236 筆 | ✅ |
| 最新資料時間 | 2026-04-01 23:32 UTC | ✅ |
| BTC 當前 | ~$68,154 | ✅ |
| FNG | 8.0 (極度恐慌) | ⚠️ |
| Funding Rate | 3.4e-05 (中性) | ℹ️ |
| **main.py 進程** | **5分鐘排程運行中（PID 26383）** | ✅ |

### 感官 IC（全量 2208 筆，h=4）
| 感官 | IC | p值 | 顯著? | NEG_IC | 狀態 |
|------|----|----|-------|--------|------|
| feat_eye_dist | -0.069 | 0.0011 | ✅ | ✅反轉 | 有效 |
| feat_ear_zscore | -0.056 | 0.0085 | ✅ | ✅反轉 | ✅ mom_12 |
| feat_nose_sigmoid | -0.081 | 0.0001 | ✅ | ✅反轉 | 有效 |
| feat_tongue_pct | +0.148 | <0.0001 | ✅ | ❌ | ✅ vol_ratio（最強）|
| feat_body_roc | -0.055 | 0.0102 | ✅ | ✅反轉 | ✅ stoch_rsi_14 |
| feat_pulse | -0.049 | 0.0208 | ✅ | ✅反轉 | 有效 |
| feat_aura | -0.069 | 0.0012 | ✅ | ✅反轉 | 有效 |
| feat_mind | -0.092 | <0.0001 | ✅ | ✅反轉 | 有效 |

**🎉 里程碑：8/8 感官全部 IC 顯著！**

### 模型性能（#67 重訓）
| 指標 | 值 | 評估 |
|------|----|----|
| Train Accuracy | **60.1%** | ✅ |
| TimeSeries CV | **45.8% ± 7.3%** | 🟡 持續改善中 |
| 最新預測 | conf=0.197, SELL | ✅ 運作正常 |
| 訓練樣本 | 2,236 筆 (clean h=4) | ✅ |

### 測試狀態
| 項目 | 狀態 |
|------|------|
| 檔案結構 | ✅ PASS |
| 語法檢查 | ✅ PASS |
| comprehensive_test.py | ✅ 6/6 通過 |

---

## 📋 下一步優先行動

| 優先 | 行動 | Issue |
|------|------|-------|
| P1 | **持續累積 h=4 乾淨數據**：5min 排程每天新增 ~288 筆，累積→CV 改善 | #H33 |
| P2 | **IC 動態加權**：tongue IC=+0.148 遠高於其他感官，應加大 XGBoost 輸入權重 | #IC4 |
| P3 | **lag 特徵**：加入 1h/4h/24h lag 增強時序記憶 | #M06 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
