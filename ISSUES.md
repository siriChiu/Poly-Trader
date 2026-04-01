# Poly-Trader Issues 追踪

> **最後更新：2026-04-01 14:05 GMT+8**
> **資料量：Raw 2514 | Features 2498 | Labels 2444 | Trades 0**
> **模型：XGBoost 3-class (neg/neutral/pos), 5 核心特徵 + 3 待擴充, 正則化**

---

## 🔴 高優先級（待修）

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H07/#H12 | 模型 CV 準確率低 / 過擬合 | 預測力不足 | 🔄 正則化+三類別標籤已上，待 OOS 回測 |
| #H15 | Tongue 重要性=0 (FNG 靜態, 30 unique) | 純噪音 | 🔄 權重 0.0, 待找新 API |
| #H16 | Eye IC 反向 (-0.224)，是否用作反向指標 | 反向指標可用 | 待評估 |
| #M06 | 缺少 lag 特徵 (1h, 4h, 24h) | 無時間滯後資訊 | 🟡 LAG_COLS 已定義 |
| #M13 | 回填 90 天歷史數據 | 38h→90d 大幅增加樣本 | 🟡 tests/backfill_90d.py |

---

## 🟢 已解決

| ID | 問題 | 方案 | 日期 |
|----|------|------|------|
| #H01 | 回測用 random 數據 | DB 特徵真實回測 | 04-01 |
| #H02 | collector 未寫入新欄位 | 更新 v3/v4 模組 | 04-01 |
| #H03 | 前端 Vite 跨域/端口問題 | 改用相對路徑 + proxy | 04-01 |
| #H04 | 五感特徵正規化不一致 | eye_dist min-max 到 -1~1 | 04-01 |
| #H06 | 訓練資料 cross-join 83K 重複 | 改用 merge_asof 10min | 04-01 |
| #H08 | Ear 零變異 | funding_rate z-score | 04-01 |
| #H09 | Eye 分數恆為 1.0 | (value+1)/2 正規化 | 04-01 |
| #H10 | Volume 欄位全 NaN | fetch_current_volume | 04-01 |
| #H11 | SensesEngine DB 注入 bug | init_dependencies | 04-01 |
| #H13 | ~~無負標籤~~ | label(-1/0/1) ±0.3% | 04-01 13:30 |
| #H19 | ear_zscore 回歸 bug | 手動修 DB + confirm | 04-01 |
| #H20 | ~~Nose/Ear 洩漏 r=0.998~~ | Nose→OI ROC, r=-0.14 | 04-01 13:30 |
| #H21 | ~~api.py import WsManager~~ | WS 統一 ws.py | 04-01 |
| #H22 | ~~標籤管線 horizon=24h~~ | horizon 4h, 2444 labels | 04-01 13:30 |
| UX6-UX8 | 前端三 bug | Props+Null+MergedPoint | 04-01 |

---

## 📊 當前模型狀態

**訓練數據：** 2498 筆 × 5 特徵, 2444 筆標籤 (3-class), 分布均勻
- pos (label=1, up>0.3%): 846 (35%) | neutral (0): 839 (34%) | neg (-1): 759 (31%)

**模型：** XGBoost multi:softprob, n_estimators=200, max_depth=3, reg_alpha=0.1
**測試：** comprehensive_test.py 6/6 PASS ✅

| 感官 | 重要性 | IC | 狀態 |
|------|--------|-----|------|
| Body | 27% | -0.067 | OI ROC, 獨立 ✅ |
| Nose | 18% | +0.053 | OI ROC, 已解耦 ✅ |
| Ear | 15% | -0.008 | Funding z |
| Tongue | 13% | -0.005 | 僵化中 |
| Eye | 11% | -0.224 | 反向指標 ✅ |
| Pulse | — | — | 🆕 新，代碼在但待資料 |
| Aura | — | — | 🆕 新，代碼在但待資料 |
| Mind | — | — | 🆕 新，待外部數據源 |

---

## 📋 下一步

| 優先 | 行動 | Issue |
|------|------|-------|
| P0 | OOS 回測驗證 | #H07 |
| P1 | 90 天歷史數據回填 | #M13 |
| P2 | Tongue 替換 | #H15 |
| P3 | lag features 實現 | #M06 |
| P4 | 擴充 Pulse/Aura/Mind 數據源 | 新 |
| P5 | 雷達圖從五角→多邊形 | 新 |

---

*此文件每次心跳**完全覆蓋**，保持精簡。*
