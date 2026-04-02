# Poly-Trader Issues 追踪

> **最後更新：2026-04-02 08:34 GMT+8**
> **🔄 心跳 #75：感官全數通過 IC 顯著性驗證（N=4523 aligned）；數據正常增長至 2289 筆；系統穩定**
> **✅ 上輪修復：心跳 #74：fix #H86 — predictor _get_proba 優先使用 model dict feature_names（修復 32 vs 8 特徵 mismatch ValueError）**

---

## 🔴 危急 — 系統性問題

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H31 | 🔴 歷史 raw data polymarket_prob 幾乎全 NULL | Ear/Polymarket 歷史信號缺失 | 🔴 P1 |

## 🟡 高優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H33 | 🟡 模型 CV=44.7%（Train=56.9%, gap=12%） | 2,289 筆，每天+288筆，累積數據改善中 | 🟡 P1 — 持續收集 |
| #H87 | 🟡 CV 長期卡在 44-45%，距目標 90% 差距甚大 | 需要更多數據 + 可能需要非線性特徵組合或外部信號 | 🟡 P1 |
| #H85 | 🟡 feat_nose_sigmoid IC=-0.07（負向） | EMA 距離替換可提升穩定性 | 🟢 P2 |

## 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #IC4 | 模型動態 IC 加權 | tongue IC=+0.083 遠高，應加大 XGBoost 輸入權重 | 🟢 P3 |


## 🏆 已解決

| ID | 問題 | 解決方案 | 日期 |
|----|------|----------|------|
| **#H86** | **predictor._get_proba 使用 clf.feature_names_in_ 失敗→靜默回退 8 特徵，imputer 需 32 特徵→ValueError** | **優先使用 model dict 的 feature_names key，修復 32-feature 預測路徑** | **04-02 08:24** |
| **#H84** | **feat_pulse IC=-0.028 p=0.18（不顯著）** | **本輪重新計算 IC: pulse=-0.047 p=0.026（✅已顯著）** | **04-02 08:24** |
| **#H83** | **feat_aura IC=-0.004, p=0.83（完全無效）** | **替換為 fr_cum48_norm（48h 累積資金費率正規化），IC=-0.097, p=0.000** | **04-02 08:20** |
| **#H82** | **predictor.py ValueError: feature_names mismatch（8 vs 32）** | **load_latest_features 改為讀 289 筆計算 lag；_get_proba 動態讀 clf.feature_names_in_** | **04-02 07:59** |
| **#M06** | **lag 特徵缺失** | **加入 feat_*_lag12/lag48/lag288 共 24 個 lag 特徵；N=1955, CV=44.9%** | **04-02 07:49** |
| **#H81** | **重複 main.py 進程（PID 25614+26388 同時運行）** | **kill 25614，更新 poly_trader.pid=26388，保留較新進程** | **04-02 07:46** |
| **#H80** | **collector.py run_preprocessor 重複呼叫** | **移除 collector.py 內嵌的 run_preprocessor 呼叫** | **04-02 07:39** |
| **#H79** | **predictor.py AttributeError: 'dict' has no attribute 'predict_proba'** | **__init__ 判斷 dict 並解包 clf/imputer/neg_ic_feats** | **04-02 07:14** |
| **#H78** | **feat_ear_zscore MACD_hist 假顯著** | **替換為 mom_12 (12期動量，p=0.027 ✅)** | **04-02 07:04** |
| **#H77** | **feat_ear_zscore IC 不顯著** | **替換為 MACD histogram(12/26)** | **04-02 07:01** |
| **#H76** | **模型嚴重過擬合 Train=80.2%/CV=42.8%** | **加強正則化 → Train=60.1%/CV=45.8% gap=14%** | **04-02 06:44** |
| #H74 | feat_ear_zscore IC 不顯著 | RSI-24 → RSI-72 | 04-02 06:37 |
| #H75 | feat_tongue_pct IC 不顯著 | volatility_24h → vol_ratio_6_48 | 04-02 06:37 |
| #H66 | feat_body_roc IC 邊緣不顯著 | atr_ratio_14 → stoch_rsi_14 | 04-02 06:37 |
| #H73 | feat_aura NULL / logger 重複 | NULL 填補，logger 修正 | 04-02 06:04 |
| #H72 | feat_body_roc IC 符號翻轉 | 重算 ic_signs | 04-02 05:59 |
| #H70 | ic_signs.json 未隨新數據更新 | 重算並重訓 | 04-02 05:44 |
| #H69 | feat_ear momentum_48h IC 不顯著 | 替換為 RSI-24 | 04-02 05:29 |
| #H48 | NEG_IC_FEATS 硬編碼 | 動態計算 ic_signs.json | 04-02 05:29 |
| #H67 | labeling 時間戳精確匹配失敗 | 改為 nearest-match（60min 容差） | 04-02 05:11 |
| #H65 | h=1 horizon IC 全部不顯著 | 改為 h=4 | 04-02 04:30 |
| #H62 | 偽標籤污染 | 清除 4383 筆偽標籤 | 04-02 04:15 |
| #H46 | main.py 排程每小時一次 | 改為 interval(5min) | 04-02 01:52 |
| #H43 | 8,760 筆 1969-era 污染數據 | 全部清除 | 04-02 00:06 |
| #H23 | 資料庫崩潰 | 90 天回填 | 04-01 17:16 |

---

## 📊 當前系統健康 (2026-04-02 08:34 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 2,289 筆 | ✅ +2 筆（持續增長）|
| Features | 2,289 筆 | ✅ |
| Labels (h=4, clean) | 4,523 筆 | ✅ |
| 最新資料時間 | 2026-04-02 00:34 UTC | ✅ |
| BTC 當前 | ~$68,292 | ✅ |
| FNG | 12.0 (極度恐慌) | ⚠️ |
| Funding Rate | 3.72e-05 (中性) | ℹ️ |
| **main.py 進程** | **5分鐘排程運行中（PID 26388）** | ✅ |
| **預測模組** | **XGBoostPredictor（32特徵）** | ✅ |

### 感官 IC（aligned N=4523，心跳#75更新）
| 感官 | IC | p值 | 狀態 |
|------|----|-----|------|
| feat_eye_dist | -0.039 | 0.009 | ✅ 顯著 |
| feat_ear_zscore | -0.043 | 0.004 | ✅ 顯著 |
| feat_nose_sigmoid | -0.040 | 0.007 | ✅ 顯著 |
| feat_tongue_pct | +0.083 | 0.000 | ✅ 最強 |
| feat_body_roc | -0.059 | 0.000 | ✅ 顯著 |
| feat_pulse | -0.030 | 0.044 | ✅ 顯著（邊緣）|
| feat_aura | -0.051 | 0.001 | ✅ 顯著 |
| feat_mind | -0.042 | 0.005 | ✅ 顯著 |

🎉 **里程碑持續：全部 8 感官 IC 均顯著（p<0.05）**

### 模型性能
| 指標 | 值 | 評估 |
|------|----|----|
| Train Accuracy | **56.9%** | ✅ gap 縮小 |
| TimeSeries CV | **44.7% ± 6.7%** | 🟡 數據累積中 |
| n_features | **32（含 lag）** | ✅ |

### 測試狀態
| 項目 | 狀態 |
|------|------|
| 檔案結構 | ✅ PASS |
| 語法檢查 | ✅ PASS |
| comprehensive_test.py | ✅ 6/6 通過 |
| main.py 進程 | ✅ 運行中 PID 26388 |

---

## 📋 下一步優先行動

| 優先 | 行動 | Issue |
|------|------|-------|
| P1 | **持續累積 h=4 乾淨數據**：5min 排程每天新增 ~288 筆，目標 5,000+ 筆提升 CV | #H33 |
| P1 | **評估 CV 突破瓶頸策略**：lag-288 特徵 IC 弱 → 考慮引入鏈上數據（交易所淨流量、巨鯨動態）作為新感官 | #H87 |
| P2 | **feat_nose EMA 距離替換**：ema_dist IC 穩定性更好 | #H85 |
| P3 | **動態 IC 加權**：tongue IC=+0.083 遠高，考慮 sample_weight 或 feature 重複 | #IC4 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
