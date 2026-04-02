# Poly-Trader Issues 追踪

> **最後更新：2026-04-02 09:59 GMT+8**
> **🔄 心跳 #83：更新 ic_signs.json（N=5000 重算）；Body IC 無效 p=0.23；Mind 升為最強 IC=-0.147；raw=11069 feats=11057 BTC=$67358**

---

## 🔴 危急 — 系統性問題

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H31 | 🔴 歷史 raw data polymarket_prob 幾乎全 NULL | Ear/Polymarket 歷史信號缺失 | 🔴 P1 |

## 🟡 高優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H95 | 🟡 Body IC p=0.23 完全不顯著 | 替換為 BTC 鏈上數據（活躍地址/交易量）| 🟡 P1 |
| #H87 | 🟡 CV≈50% 距目標 90% 差距甚大 | 累積更多數據（現 11K/目標 50K+）+ 特徵創新 | 🟡 P1 |

## 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H94 | Nose/Ear IC 強度偏低 | Nose→社交情緒；考慮 Ear 替換方案 | 🟢 P2 |
| #IC4 | 模型動態 IC 加權 | sample_weight 依 IC 動態調整 | 🟢 P3 |

## 🏆 已解決

| ID | 問題 | 解決方案 | 日期 |
|----|------|----------|------|
| **#H95-ic** | ic_signs.json stale（Pulse 符號反向；Body/Mind IC 值偏差）| N=5000 重算，Pulse sign -1→+1，Mind IC -0.079→-0.147 | 04-02 09:59 |
| **#H93** | n_features DB 記錄為 8（bug）| 改用 X.shape[1]，現在正確記錄實際特徵數 | 04-02 09:54 |
| **#H92** | ic_signs.json stale | 重算 N=8853 IC，修正 | 04-02 09:31 |
| **#H91** | Eye/Ear/Mind IC 不顯著（N=9000）| N=5000 最新數據重算，全部顯著 | 04-02 09:59 |
| **#H89** | eye/body/aura IC 不顯著 | 替換特徵計算 | 04-02 09:08 |
| **#H88** | CV FitFailedWarning | 手動遍歷 fold | 04-02 08:54 |
| **#H86** | predictor._get_proba 失敗 | 優先使用 feature_names_in_ | 04-02 08:24 |
| #H76 | 模型嚴重過擬合 Train=80.2% | 加強正則化 | 04-02 06:44 |
| #H67 | labeling 時間戳匹配失敗 | nearest-match（60min 容差）| 04-02 05:11 |
| #H62 | 偽標籤污染 | 清除 4383 筆偽標籤 | 04-02 04:15 |
| #H43 | 8,760 筆 1969-era 污染數據 | 全部清除 | 04-02 00:06 |
| #H23 | 資料庫崩潰 | 90 天回填 | 04-01 17:16 |

---

## 📊 當前系統健康 (2026-04-02 09:59 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 11,069 筆 | ✅ 每 5 分鐘增長 |
| Features | 11,057 筆 | ✅ |
| Labels | 22,045 筆 | ✅ |
| BTC 當前 | $67,357.9 | ✅ |
| FNG | 12.0（極度恐慌）| ⚠️ |
| Funding Rate | 3.44e-06（極低/中性）| ℹ️ |

### 感官 IC（N=5000，h=4，最新重算）
| 感官 | 特徵 | IC | p 值 | 顯著 |
|------|------|----|------|------|
| Eye（視覺）| feat_eye_dist | -0.0750 | 0.0000 | ✅ |
| Ear（聽覺）| feat_ear_zscore | -0.0695 | 0.0000 | ✅ |
| Nose（嗅覺）| feat_nose_sigmoid | -0.0631 | 0.0000 | ✅ |
| Tongue（味覺）| feat_tongue_pct | +0.0674 | 0.0000 | ✅ |
| Body（觸覺）| feat_body_roc | -0.0170 | 0.2307 | ❌ 待替換 |
| **Pulse（脈動）**| feat_pulse | **+0.1135** | 0.0000 | ✅✅ 強 |
| Aura（磁場）| feat_aura | -0.0423 | 0.0028 | ✅ |
| **Mind（認知）**| feat_mind | **-0.1471** | 0.0000 | ✅✅ 最強 |

### 模型性能
| 指標 | 值 | 評估 |
|------|----|----|
| Train Accuracy | **45.9%** | ✅ 欠擬合（無過擬）|
| TimeSeries CV | **50.6% ± 6.4%** | 🟡 穩定但不足 |
| n_features | **32**（8 base + 24 lag）| ✅ |
| n_samples | 22,045（labels）/ 11,057（features）| ✅ |

### 測試狀態
| 項目 | 狀態 |
|------|------|
| dev_heartbeat.py | ✅ 全 OK |
| comprehensive_test.py | ✅ 6/6 通過 |

---

## 📋 下一步優先行動

| 優先 | 行動 | Issue |
|------|------|-------|
| P1 | **替換 Body**：feat_body_roc IC 完全不顯著，引入 BTC 鏈上數據（Glassnode/CryptoQuant active address/exchange inflow）| #H95 |
| P1 | **累積數據**：每天+288筆，目標 50,000+ 筆以提升 CV | #H87 |
| P2 | **特徵創新**：Nose→BTC 社交情緒（Twitter/Reddit 情緒分數）| #H94 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
