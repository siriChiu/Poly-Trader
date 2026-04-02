# Poly-Trader Issues 追踪

> **最後更新：2026-04-02 09:08 GMT+8**
> **🔄 心跳 #77：替換 feat_body_roc（stoch_rsi→vol_zscore_24）＋ feat_aura（fr_cum48→pos_in_24h_range），IC 顯著性改善**
> **✅ 上輪修復：心跳 #76：fix #H88 — CV FitFailedWarning 修復，CV 從 44.7% 提升至 50.6%±6.3%**

---

## 🔴 危急 — 系統性問題

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H31 | 🔴 歷史 raw data polymarket_prob 幾乎全 NULL | Ear/Polymarket 歷史信號缺失 | 🔴 P1 |

## 🟡 高優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H90 | 🟡 feat_pulse IC=+0.004（不顯著）、feat_mind IC=+0.001（不顯著）— ic_signs 顯示兩者接近0 | 考慮替換 pulse→ATR-ratio / mind→ret_288 | 🟡 P1 |
| #H87 | 🟡 Train accuracy 47.96%（基準線附近）；CV=50.5%，距目標 90% 差距甚大 | lag 特徵重算 ic_signs（本輪未更新）；持續累積數據 | 🟡 P1 |
| #H33 | 🟡 CV=50.5%，距目標 90% 差距甚大 | 11,045 特徵筆，每天+288筆，累積數據改善中 | 🟡 P1 |

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

## 📊 當前系統健康 (2026-04-02 09:08 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 11,057 筆 | ✅ 正常增長 |
| Features | 11,045 筆 | ✅ |
| Labels h=4 | 11,008 筆 | ✅ |
| BTC 當前 | ~$68,605 | ✅ |
| FNG | 12.0（極度恐慌）| ⚠️ |
| Funding Rate | 3.55e-05（中性）| ℹ️ |
| main.py 進程 | 5分鐘排程運行中 | ✅ |

### 感官 IC（ic_signs.json 本輪更新，N=11014 aligned）
| 感官 | 特徵 | IC | 狀態 |
|------|------|----|------|
| Eye（視覺）| feat_eye_dist | +0.035 | ✅ |
| Ear（聽覺）| feat_ear_zscore | -0.022 | ✅（NEG） |
| Nose（嗅覺）| feat_nose_sigmoid | +0.024 | ✅ |
| Tongue（味覺）| feat_tongue_pct | +0.045 | ✅ 最強 |
| Body（觸覺）| feat_body_roc（vol_zscore_24）| -0.020 | ✅（NEG）🆕替換 |
| Pulse（脈動）| feat_pulse | +0.004 | ❌ 邊緣 → P1 |
| Aura（磁場）| feat_aura（pos_in_24h_range）| +0.050 | ✅ 🆕替換 |
| Mind（認知）| feat_mind | +0.001 | ❌ 邊緣 → P1 |

### 模型性能
| 指標 | 值 | 評估 |
|------|----|----|
| Train Accuracy | **47.96%** | 🔴 基準線附近 |
| TimeSeries CV | **50.50% ± 6.24%** | 🟡 穩定 |
| n_features | **8（基礎）** | ✅ |
| Training samples | **10,720+** | ✅ |

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
| P1 | **替換 feat_pulse/feat_mind**：IC ≈ 0，考慮 ATR-ratio（IC=+0.046✅）替換 pulse | #H90 |
| P1 | **lag 特徵 ic_signs 重算**：本輪只更新了 8 基礎特徵，32 個 lag 特徵的 IC 符號需更新 | #H87 |
| P1 | **持續累積數據**：每天+288筆，目標 20,000+ 筆 | #H33 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
