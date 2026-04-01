# Poly-Trader Issues 追踪

> **最後更新：2026-04-01 13:30 GMT+8**
> **資料量：Raw 2514 | Features 2498 | Labels 2444**
> **模型：XGBoost 3-class, 8 特徵, 正則化**

---

## 🔴 高優先級

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H20 | 🔴 Nose 和 Ear 共享 funding_rate (r=0.998) | 模型 double-count 同一信號 | ✅ **已修復** — Nose 改用 OI ROC, r→-0.14 |
| #H22 | 🔴 標籤管線斷裂 (horizon=24h 太長，標籤卡在 251) | 模型訓練樣本不足 | ✅ **已修復** — horizon 4h, 三類別重建 2444 |
| #H13 | 🔴 無負標籤 (模型從未學過 SELL) | 下跌時模型必失效 | ✅ **已修復** — label(-1/0/1) ±0.3% |
| #H12 | 🔴 模型過擬合 (train 96% vs CV 36%) | 模型無實際預測力 | ✅ **已修復** — 正則化 + 8特徵重訓 |
| #H07 | 🔴 模型 CV 準確率低於基線 | 同上 | ✅ 同上 |

---

## 🟡 中優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H15 | Tongue 重要性=0 (FNG 靜態，120/2498 unique) | 權重降至 0.0, 找替代 API | 🟡 已降權，待找新 API |
| #M06 | 缺少 lag features (1h, 4h, 24h) | 增加時間滯後特徵 | 🟡 LAG_COLS 已定義 |
| #M09 | Tongue FNG 太稀疏 (std=0.009, 30 unique) | 同上 #H15 | 🟡 同上 |
| #M12 | 舊版 Nose 振幅過窄 (已修) | 歷史問題 | ✅ 已隨 #H20 解決 |
| #009 | 缺少 SHAP 可解釋性圖表 | 集成 shap 庫 | 🟡 待處理 |
| #M13 | 回填更多歷史數據 (當前 38h, 目標 90 天) | tests/backfill_90d.py | 🟡 待執行 |

---

## 🟡 觀察中

| ID | 問題 | 當前狀態 |
|----|------|----------|
| #H16 | Eye IC 反向 (-0.22)，是否用作反向指標 | ⏳ Mind 0.15, nose=0.15, tongue=0.0, body=0.10, pulse=0.20, aura=0.10, mind=0.20 |

---

## 🏆 已解決

| ID | 問題 | 解決方案 | 日期 |
|----|------|----------|------|
| #H01 | 回測用 random 數據 | 改為基於 DB 特徵真實回測 | 04-01 |
| #H02 | collector 未寫入新欄位 | 更新 v3/v4 模組 | 04-01 |
| #H03 | 前端 Vite 跨域問題 | 改用相對路徑 + proxy | 04-01 |
| #H04 | 五感特徵正規化不一致 | eye_dist min-max 到 -1~1 | 04-01 |
| #H06 | 訓練資料 cross-join 83K 重複 | 改用 merge_asof 10min | 04-01 |
| #H08 | Ear 零變異 (ear_prob) | 改用 funding_rate z-score | 04-01 |
| #H09 | Eye 分數恆為 1.0 | normalize 改用 (value+1)/2 | 04-01 |
| #H10 | Volume 欄位全 NaN | 新增 fetch_current_volume | 04-01 |
| #H11 | SensesEngine DB 注入 bug | init_dependencies 正確注入 | 04-01 |
| #H14 | Ear 極端值 (z=-1.71) | 真實信號，非 bug | 04-01 |
| #H19 | ear_zscore 回歸 bug (raw 未 tanh) | 手動修 DB + 確認 preprocessor | 04-01 |
| #H21 | api.py import WsManager → ECONNABORTED | 移除 import, WS 統一 ws.py | 04-01 |
| #H20 | Ear/Nose 特徵洩漏 r=0.998 | Nose 改用 OI ROC, r→-0.14 | 04-01 13:30 |
| #H22 | 標籤管線斷裂 251→2444 | 4h horizon + 三類別標籤 | 04-01 13:30 |
| #H13 | 無負標籤 | label(-1/0/1), neg 31% | 04-01 13:30 |
| #H12 | 模型過擬合 | 正則化 (depth=3, reg=0.1/1.0) | 04-01 13:30 |
| UX6 | AdviceCard undefined length | Props 預設值防護 | 04-01 |
| UX7 | 回測摘要報錯 | BacktestSummary Null Safety | 04-01 |
| UX8 | 五感走勢圖時間對齊 | 重構 MergedPoint 邏輯 | 04-01 |
| #017 | Body 零變異 | Body v4: 清算壓力指標 | 03-31 |
| #018 | 測試文件散落 | 移入 tests/ | 03-31 |
| #M10 | 空 DB 殘留 | 已刪除 | 04-01 |
| #M11 | ear_zscore 超出範圍 (-3.89) | tanh(z/2) 壓縮 | 04-01 |

---

## 📊 當前模型狀態 (2026-04-01 13:30)

### 訓練數據
- **特徵：** 2498 筆 × 8 感官
- **標籤：** 2444 筆 (merge_asof 10min tolerance)
- **分佈：** neg(-1→0)=752 (31%) | neutral(0→1)=814 (34%) | pos(1→2)=811 (35%)
- **Horizon：** 4h, 閾值 ±0.3%

### 特徵重要性 (8 感官)
| 感官 | 重要性 | IC | 評價 |
|------|--------|-----|------|
| Aura (磁場) | **23.7%** | +0.043 | 新最強 — funding×price 背離 |
| Body (觸覺) | **18.7%** | -0.067 | OI ROC |
| Ear (聽覺) | 12.6% | -0.008 | 解耦後獨立貢獻 |
| Tongue (味覺) | 12.6% | -0.005 | ⚠️ FNG 靜態 |
| Nose (嗅覺) | 11.6% | +0.053 | ✅ 已獨立 (OI ROC) |
| Eye (視覺) | 11.1% | -0.224 | 穩定反向指標 |
| Pulse (脈動) | 9.6% | +0.099 | 新 — 波動率 z-score |
| Mind (認知) | 0.0% | — | 待數據注入 (BTC/ETH ratio) |

### 模型參數
- XGBoost, multi:softprob 3-class, n_estimators=200
- max_depth=3, reg_alpha=0.1, reg_lambda=1.0, min_child_weight=5
- subsample=0.7, colsample_bytree=0.7

### IC 結果 (2377 樣本)
| 感官 | IC (Pearson) | 評價 |
|------|-------------|------|
| Eye | -0.224 | 🔴 穩定反向指標 |
| Ear | -0.008 | ⚠️ 近零 (解耦後) |
| Nose | +0.053 | 🟡 弱但獨立 |
| Tongue | -0.005 | ❌ 無預測力 |
| Body | -0.067 | 🟡 微弱 |
| Pulse | +0.099 | 🟡 新, 待觀察 |
| Aura | +0.043 | 🟡 新, 待觀察 |

---

## 🎩 六帽會議 Action Items

| Action | 狀態 | 備註 |
|--------|------|------|
| 統一感官特徵到 -1~1 | ✅ | eye_dist min-max |
| 重寫回測 API | ✅ | DB 特徵真實回測 |
| 增加 lag features (1h, 4h, 24h) | 🟡 | LAG_COLS 已定義 |
| 修復 cross-join bug | ✅ | merge_asof |
| 評估/汰換 Tongue | 🔴 | 持續 |
| Nose 替換數據源 | ✅ | OI ROC |
| Tongue 停用/替換 | 🔴 | 找實時情緒 API |
| 模型正則化 | ✅ | 已完成 |

---

## 📋 下一步行動優先序

| 優先級 | 行動 | Issue |
|--------|------|-------|
| P0 | 模型 OOS 回測驗證 | #H07 |
| P1 | 回填 90 天歷史數據 | #M13 |
| P2 | Tongue 替換 (CryptoPanic/Twitter) | #H15 |
| P3 | 加入 lag features 到 preprocessor | #M06 |
| P4 | SHAP 可解釋性圖表 | #009 |
| P5 | Mind 感官數據注入 (BTC/ETH ratio) | 新 |

---

*本文件在每次 ISSUES 更新時**完全覆蓋**，保持簡潔。詳細 ORID 追蹤記錄見 memory/YYYY-MM-DD.md。*
