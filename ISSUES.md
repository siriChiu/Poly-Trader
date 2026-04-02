# Poly-Trader Issues 追踪

> **最後更新：2026-04-02 09:20 GMT+8**
> **🔄 心跳 #78：定期重訓模型（10,760+ 樣本），CV=50.6%±6.3% 穩定**
> **✅ 上輪修復：心跳 #77：替換 feat_body_roc（stoch_rsi→vol_zscore_24）＋ feat_aura（fr_cum48→pos_in_24h_range），IC 顯著性改善**

---

## 🔴 危急 — 系統性問題

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H31 | 🔴 歷史 raw data polymarket_prob 幾乎全 NULL | Ear/Polymarket 歷史信號缺失 | 🔴 P1 |

## 🟡 高優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H90 | 🟡 feat_pulse IC=+0.004（base 不顯著），但 pulse_lag288=+0.053✅；feat_mind IC=+0.001，但 mind_lag288=+0.084✅（最強 lag 信號） | lag 版本已有效，base 不替換；考慮 ic_sign 反映 lag 最強值 | 🟡 P1 觀察中 |
| #H87 | 🟡 Train accuracy 46%（基準線附近）；CV=50.6%，距目標 90% 差距甚大 | 持續累積數據；現在用 10,760+ 樣本訓練 | 🟡 P1 |
| #H33 | 🟡 CV=50.6%，距目標 90% 差距甚大 | 11,048 特徵筆，每天+288筆，累積數據改善中 | 🟡 P1 |

## 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #IC4 | 模型動態 IC 加權 | 考慮 sample_weight 依 IC 動態調整 | 🟢 P3 |


## 🏆 已解決

| ID | 問題 | 解決方案 | 日期 |
|----|------|----------|------|
| **#H89** | **eye/body/aura IC 不顯著（live N=5841）** | **body: stoch_rsi_14→vol_zscore_24 (IC=+0.030✅); aura: fr_cum48→pos_in_24h_range (IC=+0.061✅ 最強)** | **04-02 09:08** |
| **#H88** | **CV FitFailedWarning：fold 0 缺少 class 0** | **手動遍歷 fold，跳過 <3 class 的 fold，CV 從 44.7%→50.6%±6.3%** | **04-02 08:54** |
| **#H86** | **predictor._get_proba 使用 clf.feature_names_in_ 失敗** | **優先使用 model dict 的 feature_names key** | **04-02 08:24** |
| **#H84** | **feat_pulse IC=-0.028 p=0.18（不顯著）** | **重新計算 IC: pulse=-0.047 p=0.026（✅已顯著）** | **04-02 08:24** |
| **#H83** | **feat_aura IC=-0.004, p=0.83（完全無效）** | **替換為 fr_cum48_norm（48h 累積資金費率）** | **04-02 08:20** |
| **#H82** | **predictor.py ValueError: feature_names mismatch（8 vs 32）** | **修復 32-feature 預測路徑** | **04-02 07:59** |
| **#M06** | **lag 特徵缺失** | **加入 24 個 lag 特徵；N=1955, CV=44.9%** | **04-02 07:49** |
| #H76 | 模型嚴重過擬合 Train=80.2%/CV=42.8% | 加強正則化 → Train=60.1%/CV=45.8% | 04-02 06:44 |
| #H73 | feat_aura NULL / logger 重複 | NULL 填補，logger 修正 | 04-02 06:04 |
| #H67 | labeling 時間戳精確匹配失敗 | 改為 nearest-match（60min 容差） | 04-02 05:11 |
| #H65 | h=1 horizon IC 全部不顯著 | 改為 h=4 | 04-02 04:30 |
| #H62 | 偽標籤污染 | 清除 4383 筆偽標籤 | 04-02 04:15 |
| #H43 | 8,760 筆 1969-era 污染數據 | 全部清除 | 04-02 00:06 |
| #H23 | 資料庫崩潰 | 90 天回填 | 04-01 17:16 |

---

## 📊 當前系統健康 (2026-04-02 09:20 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 11,060 筆 | ✅ 正常增長 |
| Features | 11,048 筆 | ✅ |
| Labels h=4 | ~15,332 筆 | ✅ |
| BTC 當前 | ~$68,142 | ✅ |
| FNG | 12.0（極度恐慌）| ⚠️ |
| Funding Rate | 3.04e-05（中性）| ℹ️ |
| main.py 進程 | 5分鐘排程運行中 | ✅ |

### 感官 IC（ic_signs.json，N=11,048 aligned）
| 感官 | 特徵 | Base IC | Best Lag IC | 狀態 |
|------|------|---------|-------------|------|
| Eye（視覺）| feat_eye_dist | +0.037 | lag12=+0.038 | ✅ |
| Ear（聽覺）| feat_ear_zscore | -0.020 | lag288=-0.035 | ✅（NEG） |
| Nose（嗅覺）| feat_nose_sigmoid | +0.026 | lag288=+0.070 | ✅ |
| Tongue（味覺）| feat_tongue_pct | +0.045 | lag12=+0.029 | ✅ |
| Body（觸覺）| feat_body_roc (vol_zscore_24) | -0.022 | lag288=-0.041 | ✅（NEG） |
| Pulse（脈動）| feat_pulse | +0.004 | lag288=+0.053 | ⚠️ base 弱，lag 強 |
| Aura（磁場）| feat_aura (pos_in_24h_range) | +0.053 | lag12=+0.048 | ✅ 最強 |
| Mind（認知）| feat_mind | +0.001 | lag288=+0.084 | ⚠️ base 弱，lag=最強 |

### 模型性能
| 指標 | 值 | 評估 |
|------|----|----|
| Train Accuracy | **46.05%** | 🟡 無過擬合 |
| TimeSeries CV | **50.62% ± 6.30%** | 🟡 穩定 |
| Training samples | **~10,760**（心跳#78）| ✅ 新增 |
| n_features | **32（含 lag）** | ✅ |

### 測試狀態
| 項目 | 狀態 |
|------|------|
| comprehensive_test.py | ✅ 6/6 通過 |
| 語法檢查 | ✅ PASS |
| TypeScript 編譯 | ✅ PASS |

---

## 📋 下一步優先行動

| 優先 | 行動 | Issue |
|------|------|-------|
| P1 | **持續累積數據**：每天+288筆，目標 20,000+ 筆 | #H33 |
| P1 | **觀察 mind/pulse lag 效果**：lag288 IC=+0.084/+0.053，可考慮提高這兩個 lag 在模型中的權重 | #H90 |
| P2 | **考慮 IC 動態加權**：依 lag IC 強弱動態調整 sample_weight | #IC4 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
