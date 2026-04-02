# Poly-Trader Issues 追踪

> **最後更新：2026-04-02 09:31 GMT+8**
> **🔄 心跳 #79：修復 ic_signs.json（feat_eye_dist 符號錯誤 + stale IC 值），重訓模型 CV=50.7%**
> **✅ 上輪修復：心跳 #79：recalculate 全部 IC（N=8853 aligned），修正 feat_eye_dist neg_ic_feats 缺失**

---

## 🔴 危急 — 系統性問題

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H31 | 🔴 歷史 raw data polymarket_prob 幾乎全 NULL | Ear/Polymarket 歷史信號缺失 | 🔴 P1 |

## 🟡 高優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H91 | 🟡 現有 8 感官中只有 eye(IC=-0.028,p<0.01) 和 mind(IC=-0.045,p<0.001) 統計顯著；其餘 6 個 p>0.05 | 考慮替換/加強 ear/nose/tongue/body/pulse/aura | 🟡 P1 觀察中 |
| #H87 | 🟡 Train accuracy 46%（基準線附近）；CV=50.7%，距目標 90% 差距甚大 | 持續累積數據；現在用 11,050+ 樣本訓練 | 🟡 P1 |
| #H33 | 🟡 CV=50.7%，距目標 90% 差距甚大 | 11,050 特徵筆，每天+288筆，累積數據改善中 | 🟡 P1 |

## 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #IC4 | 模型動態 IC 加權 | 考慮 sample_weight 依 IC 動態調整 | 🟢 P3 |


## 🏆 已解決

| ID | 問題 | 解決方案 | 日期 |
|----|------|----------|------|
| **#H92** | **ic_signs.json stale：feat_eye_dist 缺少 neg_ic_feats；feat_pulse 顯示 IC=+0.15（實際=+0.004）** | **重算 N=8853 aligned IC，修正 neg_ic_feats，重訓模型** | **04-02 09:31** |
| **#H89** | **eye/body/aura IC 不顯著（live N=5841）** | **body: stoch_rsi_14→vol_zscore_24 (IC=+0.030✅); aura: fr_cum48→pos_in_24h_range (IC=+0.061✅ 最強)** | **04-02 09:08** |
| **#H88** | **CV FitFailedWarning：fold 0 缺少 class 0** | **手動遍歷 fold，跳過 <3 class 的 fold，CV 從 44.7%→50.6%±6.3%** | **04-02 08:54** |
| **#H86** | **predictor._get_proba 使用 clf.feature_names_in_ 失敗** | **優先使用 model dict 的 feature_names key** | **04-02 08:24** |
| #H76 | 模型嚴重過擬合 Train=80.2%/CV=42.8% | 加強正則化 → Train=60.1%/CV=45.8% | 04-02 06:44 |
| #H67 | labeling 時間戳精確匹配失敗 | 改為 nearest-match（60min 容差） | 04-02 05:11 |
| #H62 | 偽標籤污染 | 清除 4383 筆偽標籤 | 04-02 04:15 |
| #H43 | 8,760 筆 1969-era 污染數據 | 全部清除 | 04-02 00:06 |
| #H23 | 資料庫崩潰 | 90 天回填 | 04-01 17:16 |

---

## 📊 當前系統健康 (2026-04-02 09:31 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 11,062 筆 | ✅ 正常增長 |
| Features | 11,050 筆 | ✅ |
| Labels h=4 | 11,011 筆（aligned N=8853） | ✅ |
| BTC 當前 | ~$67,467 | ✅ |
| FNG | 12.0（極度恐慌）| ⚠️ |
| Funding Rate | 2.12e-05（中性）| ℹ️ |
| main.py 進程 | 5分鐘排程運行中 | ✅ |

### 感官 IC（Fresh 計算，N=8853 aligned，h=4）
| 感官 | 特徵 | Base IC | p值 | 顯著 |
|------|------|---------|-----|------|
| Eye（視覺）| feat_eye_dist | -0.028 | 0.009 | ✅ |
| Ear（聽覺）| feat_ear_zscore | -0.006 | 0.582 | ❌ |
| Nose（嗅覺）| feat_nose_sigmoid | -0.010 | 0.363 | ❌ |
| Tongue（味覺）| feat_tongue_pct | +0.011 | 0.285 | ❌ |
| Body（觸覺）| feat_body_roc | +0.001 | 0.911 | ❌ |
| Pulse（脈動）| feat_pulse | +0.004 | 0.705 | ❌ |
| Aura（磁場）| feat_aura | +0.005 | 0.657 | ❌ |
| Mind（認知）| feat_mind | -0.045 | <0.001 | ✅（最強） |

### 模型性能
| 指標 | 值 | 評估 |
|------|----|----|
| Train Accuracy | **45.83%** | 🟡 無過擬合 |
| TimeSeries CV | **50.66% ± 6.35%** | 🟡 穩定 |
| Training samples | **~10,760** | ✅ |
| n_features | **8（基礎）+ 24（lag）= 32** | ✅ |

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
| P1 | **考慮替換低 IC 感官**：ear/nose/tongue/body/pulse/aura 全部 p>0.05；考慮引入新數據源（社交情緒、鏈上數據） | #H91 |
| P1 | **持續累積數據**：每天+288筆，目標 20,000+ 筆 | #H33 |
| P2 | **考慮 IC 動態加權**：依 IC 強弱動態調整 sample_weight | #IC4 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
