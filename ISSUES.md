# Poly-Trader Issues 追踪

> **最後更新：2026-04-02 12:05 GMT+8**
> **🔄 心跳 #91：ic_signs.json 以全量 N=15366 更新；Aura IC 提升至 0.0785；model/last_metrics.json 修正（舊值 train=78.9% 為 stale 覆蓋）；raw=11094 BTC=$66,625**

---

## 🔴 危急 — 系統性問題

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H31 | 🔴 歷史 raw data polymarket_prob 幾乎全 NULL | Ear/Polymarket 歷史信號缺失 | 🔴 P1 |

## 🟡 高優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H87 | 🟡 CV≈56% 距目標 90% 差距仍大 | 累積更多數據（現 11K/目標 50K+）+ 特徵創新 | 🟡 P1 |
| #H102 | 🟡 model/last_metrics.json stale（顯示 train=78.9%，實際 51.6%）| 每次心跳同步 last_metrics.json | 🔴 P1 → **已修正** |
| #H98 | 🟡 ic_signs.json 使用 N=15359（stale），本輪已更新至 N=15366 | 確保每次心跳後重算 ic_signs | 🟡 P1 |

## 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H94 | Ear IC 弱（-0.035）| 考慮 Ear 替換方案（當前 mom_12）| 🟢 P2 |
| #IC4 | 模型動態 IC 加權 | sample_weight 依 IC 動態調整 | 🟢 P3 |
| #H97 | IC 不穩定追蹤 | 建立 rolling IC 追蹤機制 | 🟢 P3 |
| #H103 | Nose IC 改善（-0.048，負向）| 目前 ret_1 IC 穩定但偏弱，可考慮加入 volume momentum | 🟢 P2 |

## 🏆 已解決

| ID | 問題 | 解決方案 | 日期 |
|----|------|----------|------|
| **#H102** | model/last_metrics.json stale（train=78.9%）| 同步修正為 train=51.6%，CV=56.37% | 04-02 12:05 |
| **#H101** | Pulse IC=0.0094; Aura IC=0.0029 不顯著 | Pulse→vol_roc48(IC=+0.044); Aura→vol_ratio_short_long(IC=+0.099) | 04-02 11:57 |
| **#H100** | label=-1 只有 2 筆（應有 2404 筆）| UPDATE labels 修正 future_return_pct 門檻；CV 45%→56% | 04-02 11:19 |
| **#H99** | Nose IC≈0.005 完全不顯著 | 替換為 ret_1（IC=-0.054）+ 加入 NEG_IC | 04-02 11:13 |
| **#H96** | ic_signs.json stale | N=4975 重算 + 重訓模型 | 04-02 10:38 |
| **#H95** | Body IC p=0.23 完全不顯著 | 替換為 price_ret_20P | 04-02 10:20 |
| **#H93** | n_features DB 記錄為 8 | 改用 X.shape[1] | 04-02 09:54 |
| **#H92** | ic_signs.json stale | 重算 N=8853 IC | 04-02 09:31 |
| #H76 | 模型嚴重過擬合 Train=80.2% | 加強正則化 | 04-02 06:44 |
| #H67 | labeling 時間戳匹配失敗 | nearest-match（60min 容差）| 04-02 05:11 |
| #H62 | 偽標籤污染 | 清除 4383 筆偽標籤 | 04-02 04:15 |
| #H43 | 8,760 筆 1969-era 污染數據 | 全部清除 | 04-02 00:06 |
| #H23 | 資料庫崩潰 | 90 天回填 | 04-01 17:16 |

---

## 📊 當前系統健康 (2026-04-02 12:05 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 11,094 筆 | ✅ 每 5 分鐘增長 |
| Features | 11,079 筆 | ✅ |
| Labels | 22,071 筆 (h=4 + h=24) | ✅ 三類均衡 |
| BTC 當前 | $66,625 | ✅ |
| FNG | 12.0（極度恐慌）| ⚠️ 市場悲觀 |
| Funding Rate | -3.134e-05（負/偏空）| ⚠️ |

### 感官 IC（全量 N=15366，h=4）
| 感官 | 特徵 | IC | p值 | 狀態 |
|------|------|----|-----|------|
| Eye（視覺）| feat_eye_dist (funding_ma72) | -0.0294 | p=0.0003 | ⚠️ 顯著但弱 |
| Ear（聽覺）| feat_ear_zscore (mom_12) | -0.0352 | p=0.0000 | ⚠️ 顯著但弱 |
| Nose（嗅覺）| feat_nose_sigmoid (ret_1) | -0.0477 | p=0.0000 | ⚠️ 顯著但弱 |
| Tongue（味覺）| feat_tongue_pct (FNG) | +0.0459 | p=0.0000 | ✅ 顯著 |
| Body（觸覺）| feat_body_roc (price_ret_20P) | +0.0303 | p=0.0002 | ✅ 顯著 |
| Pulse（脈動）| feat_pulse (vol_roc48) | +0.0331 | p=0.0000 | ✅ 顯著 |
| Aura（磁場）| feat_aura (vol_ratio_short_long) | +0.0785 | p≈0 | ✅ **最強** |
| Mind（認知）| feat_mind (ret_144) | -0.0661 | p≈0 | ✅ 強（NEG） |

### 模型性能
| 指標 | 值 | 評估 |
|------|----|----|
| Train Accuracy | **51.6%** | ✅ 欠擬合（無過擬）|
| TimeSeries CV | **56.37% ± 8.86%** | 🟡 進步中（目標 90%）|
| n_features | **32**（8 base + 24 lag）| ✅ |

### 測試狀態
| 項目 | 狀態 |
|------|------|
| dev_heartbeat.py | ✅ 全 OK |
| comprehensive_test.py | ✅ 6/6 通過 |

---

## 📋 下一步優先行動

| 優先 | 行動 | Issue |
|------|------|-------|
| P1 | **累積數據**：每天+288筆，目標 50,000+ 筆以提升 CV | #H87 |
| P1 | **ic_signs.json 自動同步**：心跳時自動更新全量 IC | #H98 |
| P2 | **Ear/Nose/Eye 替換研究**：三者 IC 均弱（< 0.05）| #H94 |
| P2 | **回填 polymarket** | #H31 |
| P3 | **IC 動態加權** | #IC4 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
