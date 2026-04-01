# Poly-Trader Issues 追踪

> **最後更新：2026-04-02 06:24 GMT+8**
> **🔄 心跳 #63：fix #H74 — ic_signs.json 更新（ear p=0.064/tongue p=0.080 已不顯著），重訓 Train=60.5% CV=45.5%**
> **✅ 上輪修復：心跳 #62：fix #H73 — feat_aura NULL 填補，logger 重複 log 修正，重訓 Train=60.5% CV=45.5%**

---

## 🔴 危急 — 系統性問題

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H31 | 🔴 歷史 raw data polymarket_prob 幾乎全 NULL | Ear/Polymarket 歷史信號缺失 | 🔴 P1 |

## 🟡 高優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H33 | 🟡 模型 CV=45.5%（需持續收集乾淨數據） | 2,260 筆 h=4 訓練樣本，每天+288筆 | 🟡 P1 — 持續收集（5min 排程中） |
| #H74 | 🟡 feat_ear_zscore IC=-0.040 p=0.064 不顯著 | 替換為更強信號（OpenInterest 動量/BTC dominance 變化率）| 🟡 P2 |
| #H75 | 🟡 feat_tongue_pct IC=+0.037 p=0.080 不顯著（FNG 持續卡底=8） | 替換為 put-call ratio 或 social sentiment | 🟡 P2 |
| #H66 | 🟡 feat_body_roc IC=0.041 p=0.055 邊緣不顯著 | 替換信號（OBV ROC）| 🟡 P2 |
| #H71 | 🟡 nose IC 在最近500筆為+0.207但全量為-0.073 | 信號在短期方向性翻轉，需監控 | 🟡 P2 |

## 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #IC4 | 模型動態 IC 加權 | 實現感官動態權重（加權 XGBoost 輸入） | 🟢 P3 |

## 🏆 已解決

| ID | 問題 | 解決方案 | 日期 |
|----|------|----------|------|
| **#H74** | **ic_signs.json 數值過時（ear/tongue p 值已超門檻）** | **重算全量 IC，更新 ic_signs.json，commit** | **04-02 06:24** |
| **#H73** | **feat_aura 9筆 NULL（合併後 IC=NaN），logger nohup double-log** | **NULL 填補最早非空值，logger 加 isatty() 判斷，ic_signs 重算，重訓 Train=60.5% CV=45.5%** | **04-02 06:04** |
| **#H72** | **feat_body_roc IC 符號翻轉（ic_signs 過時）** | **重算全量 IC，body_roc 移出 neg_ic_feats，重訓 Train=80.2% CV=42.8%** | **04-02 05:59** |
| **#H70** | **ic_signs.json 未隨新數據更新** | **重新計算全量 IC 並重訓，Train=72.2% CV=45.3%** | **04-02 05:44** |
| **#H69** | **feat_ear momentum_48h IC=-0.059 不顯著** | **替換為 RSI-24，IC=-0.098（p=0.028）✅** | **04-02 05:29** |
| **#H48** | **NEG_IC_FEATS 硬編碼** | **動態計算 ic_signs.json** | **04-02 05:29** |
| **#H68** | **feat_nose_sigmoid 誤放 NEG_IC_FEATS** | **移除，重訓** | **04-02 05:18** |
| **#H67** | **labeling 5min 時間戳精確匹配失敗** | **改為 nearest-match（60min 容差）** | **04-02 05:11** |
| **#H65** | **h=1 horizon IC 全部不顯著** | **改為 h=4** | **04-02 04:30** |
| **#H64** | **save_labels_to_db 不更新已存在 NULL labels** | **改為 upsert** | **04-02 04:28** |
| **#H62** | **偽標籤污染** | **清除4383筆偽標籤** | **04-02 04:15** |
| **#H61** | **save_labels_to_db() 是 no-op** | **修復函數實際寫入 Labels 表** | **04-02 04:05** |
| **#H60** | **feat_pulse IC=+0.019 → v2 pos_in_range_72** | **替換計算邏輯+回填+重訓** | **04-02 03:50** |
| #H46 | main.py 排程每小時一次 | 改為 interval(5min) | 04-02 01:52 |
| #H43 | 8,760 筆 1969-era 污染數據 | 全部清除 | 04-02 00:06 |
| #H23 | 資料庫崩潰 | 90 天回填 | 04-01 17:16 |

---

## 📊 當前系統健康 (2026-04-02 06:24 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 2,260 筆 | ✅ |
| Features | 2,260 筆 | ✅ |
| Labels (h=4, clean) | 2,208 筆 | ✅ |
| 最新資料時間 | 2026-04-01 22:13 UTC | ✅ |
| BTC 當前 | ~$68,198 | ✅ |
| FNG | 8.0 (極度恐慌) | ⚠️ |
| Funding Rate | 0.0000344 (中性) | ℹ️ |
| **main.py 進程** | **5分鐘排程運行中** | ✅ |

### 感官 IC（全量 2208 筆，h=4，心跳 #63 更新）
| 感官 | IC | p值 | 顯著? | NEG_IC | 狀態 |
|------|----|----|-------|--------|------|
| feat_eye_dist | -0.077 | 0.0003 | ✅ | ✅反轉 | 有效 |
| feat_ear_zscore | -0.040 | 0.0636 | ❌ | ✅反轉 | ⚠️ #H74 替換中 |
| feat_nose_sigmoid | -0.073 | 0.0006 | ✅ | ✅反轉 | 有效 |
| feat_tongue_pct | +0.037 | 0.0797 | ❌ | ❌ | ⚠️ #H75 替換中 |
| feat_body_roc | +0.041 | 0.0553 | ❌ | ❌ | ⚠️ #H66 邊緣 |
| feat_pulse | -0.047 | 0.0274 | ✅ | ✅反轉 | 有效 |
| feat_aura | -0.064 | 0.0028 | ✅ | ✅反轉 | 有效 |
| feat_mind | -0.079 | 0.0002 | ✅ | ✅反轉 | 有效 |

### 模型性能（#63 重訓）
| 指標 | 值 | 評估 |
|------|----|----|
| Train Accuracy | **60.5%** | 🟡 |
| TimeSeries CV | **45.5% ± 10.0%** | 🟡 持續改善中 |
| 訓練樣本 | 2,208 筆 (clean h=4) | ✅ |

### 測試狀態
| 項目 | 狀態 |
|------|------|
| 檔案結構 | ✅ PASS |
| 語法檢查 | ✅ PASS |
| dev_heartbeat.py | ✅ 全通過 |

---

## 📋 下一步優先行動

| 優先 | 行動 | Issue |
|------|------|-------|
| P1 | **持續累積 h=4 乾淨數據**：5min 排程每天新增 ~288 筆 | #H33 |
| P2 | **feat_ear 替換**：OI_動量 或 BTC Dominance 變化率 | #H74 |
| P2 | **feat_tongue 替換**：FNG 持續 8，考慮 put-call ratio 或 social sentiment API | #H75 |
| P2 | **feat_body_roc 替換/驗證**：OBV ROC 或 stochastic RSI | #H66 |
| P3 | **IC 動態加權** | #IC4 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
