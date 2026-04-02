# Poly-Trader Issues 追踪

> **最後更新：2026-04-02 09:39 GMT+8**
> **🔄 心跳 #80：重訓模型（N=8855）CV=47.1%，發現 lag 特徵未存入 DB 問題**
> **✅ 上輪修復：心跳 #79：ic_signs.json 修正 + 重訓 CV=50.7%**

---

## 🔴 危急 — 系統性問題

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H93 | 🔴 **Lag 特徵未存入 DB**：features_normalized 只有 8 欄，無 _lag 欄位；模型無法使用 lag 特徵（之前認為有 32 特徵是錯的） | Lag 信號（pulse_lag288 IC=+0.16 最強）完全損失 | 🔴 P0 新發現 |
| #H31 | 🔴 歷史 raw data polymarket_prob 幾乎全 NULL | Ear/Polymarket 歷史信號缺失 | 🔴 P1 |

## 🟡 高優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H91 | 🟡 8 感官中僅 nose/tongue/body/pulse/aura 統計顯著（p<0.05），eye/ear/mind 不顯著 | 考慮替換 eye/ear/mind | 🟡 P1 觀察中 |
| #H87 | 🟡 CV=47.1%（本輪）距目標 90% 差距甚大 | 修復 lag pipeline 後重訓預期改善 | 🟡 P1 |

## 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #IC4 | 模型動態 IC 加權 | sample_weight 依 IC 動態調整 | 🟢 P3 |

## 🏆 已解決

| ID | 問題 | 解決方案 | 日期 |
|----|------|----------|------|
| **#H92** | ic_signs.json stale；feat_eye_dist neg_ic_feats 缺失 | 重算 N=8853 IC，修正，重訓 | 04-02 09:31 |
| **#H89** | eye/body/aura IC 不顯著 | 替換特徵計算方式 | 04-02 09:08 |
| **#H88** | CV FitFailedWarning | 手動遍歷 fold | 04-02 08:54 |
| **#H86** | predictor._get_proba 失敗 | 優先使用 model dict feature_names | 04-02 08:24 |
| #H76 | 模型嚴重過擬合 Train=80.2% | 加強正則化 | 04-02 06:44 |
| #H67 | labeling 時間戳匹配失敗 | nearest-match（60min 容差）| 04-02 05:11 |
| #H62 | 偽標籤污染 | 清除 4383 筆偽標籤 | 04-02 04:15 |
| #H43 | 8,760 筆 1969-era 污染數據 | 全部清除 | 04-02 00:06 |
| #H23 | 資料庫崩潰 | 90 天回填 | 04-01 17:16 |

---

## 📊 當前系統健康 (2026-04-02 09:39 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 11,064 筆 | ✅ 正常增長 |
| Features | 11,052 筆 | ✅ |
| Labels h=4 | 8,855 筆（aligned） | ✅ |
| BTC 當前 | ~$67,291 | ✅ |
| FNG | 12.0（極度恐慌）| ⚠️ |
| Funding Rate | 1.427e-05（中性）| ℹ️ |
| main.py 進程 | 5分鐘排程運行中 | ✅ |

### 感官 IC（Fresh 計算，N=8856 aligned，h=4）
| 感官 | 特徵 | IC | p值 | 顯著 |
|------|------|-----|-----|------|
| Eye（視覺）| feat_eye_dist | +0.018 | 0.087 | ❌ |
| Ear（聽覺）| feat_ear_zscore | -0.020 | 0.056 | ❌ |
| Nose（嗅覺）| feat_nose_sigmoid | +0.026 | 0.016 | ✅ |
| Tongue（味覺）| feat_tongue_pct | +0.041 | 0.0001 | ✅ |
| Body（觸覺）| feat_body_roc | -0.026 | 0.015 | ✅ |
| Pulse（脈動）| feat_pulse | +0.125 | <0.0001 | ✅ 最強 |
| Aura（磁場）| feat_aura | +0.034 | 0.002 | ✅ |
| Mind（認知）| feat_mind | -0.012 | 0.247 | ❌ |

### 模型性能
| 指標 | 值 | 評估 |
|------|----|----|
| Train Accuracy | **67.4%** | ⚠️ 輕微過擬 |
| TimeSeries CV | **47.1% ± 7.9%** | 🟡 |
| Training samples | **8,855** | ✅ |
| n_features | **8（基礎）** | ⚠️ lag 特徵缺失 |

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
| P0 | **修復 Lag 特徵 Pipeline**：在 feature_engine/preprocessor.py 中加入 lag 特徵計算並存入 DB；預期 pulse_lag288(IC=+0.16) 帶來大幅改善 | #H93 |
| P1 | **持續累積數據**：每天+288筆，目標 20,000+ 筆 | #H87 |
| P2 | **考慮替換 eye/ear/mind**：3 個感官 p>0.05 不顯著 | #H91 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
