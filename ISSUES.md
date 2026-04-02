# Poly-Trader Issues 追踪

> **最後更新：2026-04-02 09:49 GMT+8**
> **🔄 心跳 #81：重訓模型（N=15048, 32feats）CV=50.6%，驗證 lag pipeline 正常運作；model 格式由 dict→XGBClassifier**

---

## 🔴 危急 — 系統性問題

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H93 | 🔴 **n_features DB 記錄為 8（bug）**：model_metrics.n_features 固定存 `len(FEATURE_COLS)=8`，但實際模型使用 32 特徵 | 指標誤導；但不影響訓練和推論 | 🔴 P1 minor |
| #H31 | 🔴 歷史 raw data polymarket_prob 幾乎全 NULL | Ear/Polymarket 歷史信號缺失 | 🔴 P1 |

## 🟡 高優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H91 | 🟡 Eye/Ear/Mind IC 不顯著（p>0.05 at N=9000）| 考慮替換；Eye IC=+0.037,p=0.09 邊緣 | 🟡 P1 |
| #H87 | 🟡 CV≈50% 距目標 90% 差距甚大 | 累積更多數據（現 15K/目標 50K+）+ 特徵創新 | 🟡 P1 |
| #H94 | 🟡 Nose/Ear/Mind IC 極低（<0.03）| 替換方案：Nose→社交情緒/BTC 鏈上數據；Mind→BTC/ETH 量比真實數據 | 🟡 P2 |

## 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #IC4 | 模型動態 IC 加權 | sample_weight 依 IC 動態調整 | 🟢 P3 |

## 🏆 已解決

| ID | 問題 | 解決方案 | 日期 |
|----|------|----------|------|
| **#H93-lag** | lag 特徵未存入 DB | 確認：訓練時 in-memory 計算 lag，predictor 也 in-memory 計算；DB 不需儲存 lag 欄位 | 04-02 09:49 |
| **#H92** | ic_signs.json stale | 重算 N=8853 IC，修正 | 04-02 09:31 |
| **#H89** | eye/body/aura IC 不顯著 | 替換特徵計算 | 04-02 09:08 |
| **#H88** | CV FitFailedWarning | 手動遍歷 fold | 04-02 08:54 |
| **#H86** | predictor._get_proba 失敗 | 優先使用 feature_names_in_ | 04-02 08:24 |
| #H76 | 模型嚴重過擬合 Train=80.2% | 加強正則化 | 04-02 06:44 |
| #H67 | labeling 時間戳匹配失敗 | nearest-match（60min 容差）| 04-02 05:11 |
| #H62 | 偽標籤污染 | 清除 4383 筆偽標籤 | 04-02 04:15 |
| #H43 | 8,760 筆 1969-era 污染數據 | 全部清除 | 04-02 00:06 |
| #H23 | 資料庫崩潰 | 90 天回填 | 04-01 17:16 |

---

## 📊 當前系統健康 (2026-04-02 09:49 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 11,066 筆 | ✅ 正常增長 |
| Features | 11,054 筆 | ✅ |
| Labels h=4（aligned）| 15,048 筆（訓練用）| ✅ |
| BTC 當前 | ~$67,246 | ✅ |
| FNG | 12.0（極度恐慌）| ⚠️ |
| Funding Rate | 7.47e-06（極低/中性）| ℹ️ |
| main.py 進程 | 5分鐘排程運行中 | ✅ |

### 感官 IC（N≈15K aligned，h=4，含 IC 反轉修正）
| 感官 | 特徵 | IC（原始）| 反轉 | 顯著 |
|------|------|-----------|------|------|
| Eye（視覺）| feat_eye_dist | +0.038 | ❌ | ⚠️ p≈0.09 |
| Ear（聽覺）| feat_ear_zscore | -0.019 | ✅ | ❌ |
| Nose（嗅覺）| feat_nose_sigmoid | +0.026 | ❌ | ⚠️ |
| Tongue（味覺）| feat_tongue_pct | +0.044 | ❌ | ✅ |
| Body（觸覺）| feat_body_roc | -0.021 | ✅ | ❌ |
| **Pulse（脈動）**| feat_pulse | **+0.150** | ❌ | ✅✅ 最強 |
| Aura（磁場）| feat_aura | +0.052 | ❌ | ✅ |
| Mind（認知）| feat_mind | -0.015 | ✅ | ❌ |
| **pulse_lag288** | （lag 24h）| **+0.159** | ❌ | ✅✅ 最強 lag |

### 模型性能
| 指標 | 值 | 評估 |
|------|----|----|
| Train Accuracy | **45.9%** | ✅ 欠擬合（無過擬）|
| TimeSeries CV | **50.6% ± 6.4%** | 🟡 穩定但不足 |
| n_features（實際）| **32**（8 base + 24 lag）| ✅ lag 正常使用 |
| n_samples | 15,048 | ✅ |
| model 格式 | XGBClassifier（直存）| ✅ |

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
| P1 | **累積數據**：每天+288筆，目標 30,000+ 筆以提升 CV | #H87 |
| P1 | **替換 Ear/Mind**：IC 長期不顯著，引入新數據源（鏈上數據/BTC期權數據）| #H91 |
| P2 | **特徵創新**：Nose→BTC 社交情緒（Twitter/Reddit）；Mind→真實 BTC/ETH 量比 | #H94 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
