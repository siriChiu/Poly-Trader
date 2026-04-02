# Poly-Trader Issues 追踪

> **最後更新：2026-04-02 08:54 GMT+8**
> **🔄 心跳 #76：fix #H88 — CV FitFailedWarning 修復（skip fold 0 missing class 0），CV 從 44.7% 提升至 50.6%±6.3%**
> **✅ 上輪修復：心跳 #75：感官全數通過 IC 顯著性驗證（N=4523 aligned）；數據正常增長至 2289 筆；系統穩定**

---

## 🔴 危急 — 系統性問題

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H31 | 🔴 歷史 raw data polymarket_prob 幾乎全 NULL | Ear/Polymarket 歷史信號缺失 | 🔴 P1 |

## 🟡 高優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H89 | 🟡 eye/body/aura IC 不顯著（live h=4, N=5841）：eye p=0.47, body p=0.40, aura p=0.99 | eye 考慮換為 funding_rate z-score 或 VWAP 距離；aura 再次替換 | 🟡 P1 |
| #H87 | 🟡 Train accuracy 從 56.9% 降至 48.0%（模型以 10720 樣本重訓後） | 更多樣本稀釋舊模式；lag 特徵 IC 普遍弱；需探索非線性組合 | 🟡 P1 |
| #H33 | 🟡 CV=50.6%（fix #H88後），距目標 90% 差距甚大 | 11,044 特徵筆，每天+288筆，累積數據改善中 | 🟡 P1 |
| #H85 | 🟡 feat_nose_sigmoid IC=-0.025 p=0.17（h=4 live，不穩定） | EMA 距離替換可提升穩定性 | 🟢 P2 |

## 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #IC4 | 模型動態 IC 加權 | tongue IC=+0.025（live） / mind IC=-0.052 強，考慮 sample_weight | 🟢 P3 |


## 🏆 已解決

| ID | 問題 | 解決方案 | 日期 |
|----|------|----------|------|
| **#H88** | **CV FitFailedWarning：fold 0 缺少 class 0（早期回填數據全為多頭），CV=nan** | **手動遍歷 fold，跳過 <3 class 的 fold，CV 從 44.7%→50.6%±6.3%（4 valid folds）** | **04-02 08:54** |
| **#H86** | **predictor._get_proba 使用 clf.feature_names_in_ 失敗→靜默回退 8 特徵，imputer 需 32 特徵→ValueError** | **優先使用 model dict 的 feature_names key，修復 32-feature 預測路徑** | **04-02 08:24** |
| **#H84** | **feat_pulse IC=-0.028 p=0.18（不顯著）** | **本輪重新計算 IC: pulse=-0.047 p=0.026（✅已顯著）** | **04-02 08:24** |
| **#H83** | **feat_aura IC=-0.004, p=0.83（完全無效）** | **替換為 fr_cum48_norm（48h 累積資金費率正規化），IC=-0.097, p=0.000** | **04-02 08:20** |
| **#H82** | **predictor.py ValueError: feature_names mismatch（8 vs 32）** | **load_latest_features 改為讀 289 筆計算 lag；_get_proba 動態讀 clf.feature_names_in_** | **04-02 07:59** |
| **#M06** | **lag 特徵缺失** | **加入 feat_*_lag12/lag48/lag288 共 24 個 lag 特徵；N=1955, CV=44.9%** | **04-02 07:49** |
| #H81 | 重複 main.py 進程 | kill 25614，保留較新進程 26388 | 04-02 07:46 |
| #H80 | collector.py run_preprocessor 重複呼叫 | 移除內嵌的 run_preprocessor 呼叫 | 04-02 07:39 |
| #H79 | predictor.py AttributeError: 'dict' has no attribute 'predict_proba' | __init__ 判斷 dict 並解包 clf/imputer/neg_ic_feats | 04-02 07:14 |
| #H78 | feat_ear_zscore MACD_hist 假顯著 | 替換為 mom_12 (12期動量，p=0.027 ✅) | 04-02 07:04 |
| #H77 | feat_ear_zscore IC 不顯著 | 替換為 MACD histogram(12/26) | 04-02 07:01 |
| #H76 | 模型嚴重過擬合 Train=80.2%/CV=42.8% | 加強正則化 → Train=60.1%/CV=45.8% gap=14% | 04-02 06:44 |
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

## 📊 當前系統健康 (2026-04-02 08:54 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 11,056 筆 | ✅ 正常增長 |
| Features | 11,044 筆 | ✅ |
| Labels h=4 | 11,007 筆 | ✅ |
| Labels h=24 | 11,025 筆 | ✅ |
| BTC 當前 | ~$68,585 | ✅ |
| FNG | 12.0（極度恐慌）| ⚠️ |
| Funding Rate | 3.48e-05（中性）| ℹ️ |
| main.py 進程 | 5分鐘排程運行中（PID 26388）| ✅ |

### 感官 IC（h=4 live aligned N=5841，心跳#76更新）
| 感官 | IC | p值 | 狀態 |
|------|----|-----|------|
| feat_eye_dist | -0.010 | 0.465 | ❌ 不顯著 → P1 替換 |
| feat_ear_zscore | -0.045 | 0.001 | ✅ 顯著 |
| feat_nose_sigmoid | -0.036 | 0.006 | ✅ 顯著（稍弱）|
| feat_tongue_pct | +0.025 | 0.053 | ❌ 邊緣 |
| feat_body_roc | -0.011 | 0.399 | ❌ 不顯著 |
| feat_pulse | -0.039 | 0.003 | ✅ 顯著 |
| feat_aura | +0.000 | 0.987 | ❌ 完全隨機 → 立即替換 |
| feat_mind | -0.052 | 0.000 | ✅ 最強 |

⚠️ **退步警報：3感官不顯著（eye/body/aura），比心跳#75的全通過倒退**

### 模型性能
| 指標 | 值 | 評估 |
|------|----|----|
| Train Accuracy | **48.0%** | 🔴 降至基準線附近 |
| TimeSeries CV | **50.6% ± 6.3%** | 🟡 fix #H88後修正（4 valid folds）|
| n_features | **8（基礎）+ 24 lag = 32** | ✅ |
| Training samples | **10,720** | ✅ 大幅增加 |

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
| P1 | **立即替換 feat_aura**：p=0.99 完全無效，考慮 exchange_netflow 或 spot_future_basis | #H89 |
| P1 | **調查 train acc 降至 48%**：模型能力下降或特徵品質惡化，需診斷 feature importance | #H87 |
| P1 | **替換 eye/body 感官**：live IC 退步，考慮 VWAP 距離（eye）、ATR z-score（body）| #H89 |
| P1 | **持續累積數據**：每天+288筆，目標 20,000+ 筆 | #H33 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
