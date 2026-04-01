# Poly-Trader Issues 追踪

> **最後更新：2026-04-01 14:41 GMT+8**
> **資料量：Raw 2514 | Features 2499 | Labels 2444 | Trades 0**
> **模型：XGBoost 3-class (neg/neutral/pos), 5 核心特徵, 正則化**

---

## 🔴 高優先級（待修）

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H07/#H12 | 模型 CV 準確率低 / 過擬合 | 預測力不足 | 🔄 正則化已上，待 OOS 回測 |
| #M13 | 回填 90 天歷史數據 | 38h→90d 大幅增加樣本 | 🟡 tests/backfill_90d.py |
| #H15 | Tongue 重要性=0 (FNG 靜態, 30 unique) | 純噪音 | 🟡 權重 0.0 |
| #M06 | 缺少 lag 特徵 | 無時間滯後資訊 | 🟡 LAG_COLS 已定義 |

---

## 🟢 已解決

| ID | 問題 | 方案 | 日期 |
|----|------|------|------|
| #H20 | ~~Nose/Ear 特徵洩漏~~ | Nose→funding z-score(30-period), 與 Ear 窗口不同 | 04-01 14:39 |
| #H22 | ~~標籤管線 horizon=24h~~ | horizon 4h, 2444 labels (3-class) | 04-01 13:30 |
| #H13 | ~~無負標籤~~ | label(-1/0/1) ±0.3% | 04-01 13:30 |
| #H21 | ~~api.py import WsManager~~ | WS 統一 ws.py | 04-01 |
| #H19 | ~~ear_zscore 回歸 bug~~ | 手動修 DB | 04-01 |
| #H11 | ~~SensesEngine DB 注入~~ | init_dependencies | 04-01 |
| #H10 | ~~Volume 欄位全 NaN~~ | fetch_current_volume | 04-01 |
| #H09 | ~~Eye 分數恆為 1.0~~ | (value+1)/2 正規化 | 04-01 |
| #H08 | ~~Ear 零變異~~ | funding z-score | 04-01 |
| #H06 | ~~cross-join 83K 重複~~ | merge_asof 10min | 04-01 |
| #H04 | ~~五感正規化不一致~~ | min-max | 04-01 |
| #H01 | ~~回測用 random~~ | DB 真實回測 | 04-01 |
| UX6-UX8 | ~~前端三 bug~~ | null safety | 04-01 |

---

## 📊 當前狀態 (14:41 Heartbeat)

**特徵統計 (最近 50 筆)：**
| 感官 | Mean | Std | Unique | 狀態 |
|------|------|-----|--------|------|
| Eye | -0.018 | 0.138 | 17 | 正常 |
| Ear | 0.902 | 0.235 | 49 | 正常 |
| Nose | -0.260 | 0.040 | 36 | ✅ 已解耦 |
| Tongue | 0.080 | 0.000 | 1 | 🔴 僵化 |
| Pulse | 0.141 | 0.383 | 49 | 🆕 正常 |
| Aura | 0.000 | 0.000 | 7 | 🆕 微弱 |
| Mind | 0.000 | 0.000 | 1 | 🆕 待外部數據 |

**標籤**：2444 筆 (neg=759 31% / neutral=839 34% / pos=846 35%) — **分布均勻**
**測試**：6/6 PASS ✅

---

## 📋 下一步

| 優先 | 行動 | Issue |
|------|------|-------|
| P0 | OOS 回測驗證 | #H07 |
| P1 | 90 天歷史數據回填 | #M13 |
| P2 | Tongue 替換 (Twitter/CryptoPanic) | #H15 |
| P3 | lag features 實現 | #M06 |
| P4 | 擴充 Pulse/Aura/Mind 數據源 | 新 |

---

*此文件每次心跳**完全覆蓋**，保持精簡。ORID 詳細記錄在 memory/2026-04-01.md。*
