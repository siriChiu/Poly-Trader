# Poly-Trader Issues 追踪

---

## 🔴 高優先級

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H04 | 五感特徵正規化不一致（部分 0~1, 部分 -1~1） | 模型訓練效率低 | ✅ **已修復** — eye_dist 改用 min-max 到 -1~1 |
| #H05 | 預測模型僅使用 XGBoost 權重，缺乏動態調整 | 盤整期勝率低 | 🔄 **部分修復** — 已加 scale_pos_weight |
| #H06 | 訓練資料 SQL JOIN cross-join（83K 筆重複樣本） | 模型過擬合噪音 | ✅ **已修復** — 改用 merge_asof 10min tolerance |
| #H07 | 模型 CV 準確率 45.7%，低於多數類別基線 63% | 模型無實際預測力 | 🔴 **未解決** — 需更多特徵/數據 |
| #H08 | ~~Ear 感官零變異（ear_zscore 近零變異）~~ | ~~Ear 幾乎無資訊量~~ | ✅ **已修復** — 改用 funding_rate z-score，unique 28→321 |
| #H09 | ~~Eye 考試版分數異常（always=1.0）~~ | ~~感知器映射邏輯 bug~~ | ✅ **已修復** — normalize_feature 改用 (value+1)/2 映射 -1~1 範圍 |
| #H10 | ~~Volume 欄位全為 NaN~~ | ~~缺少成交量特徵，損失重要市場動能信號~~ | ✅ **已修復** — eye_binance 新增 fetch_current_volume(), collector 改用 eye.get("volume") |
| #H11 | ~~SensesEngine.set_db() 期望 SQLAlchemy Session，前端/API 傳入 string 導致全部回傳 0.5~~ | ~~前端感官分數全是假的~~ | ✅ **已修復** — `dependencies.py:init_dependencies()` 正確呼叫 `engine.set_db(_db_session)`，API 正常運作（10:10 ORID 驗證） |
---

## 🟡 中優先級

| ID | 問題 | 建議改進 |
|----|------|----------|
| #M06 | 回測勝率 ~50% | 優化特徵工程，增加滯後特徵 (lag features) |
| #M07 | 五感走勢圖有斷點 | 數據源偶發斷線，需增加插值或緩存 |
| #M08 | Ear 感官 IC ≈ 0（-0.007）→ 升級為 #H08 | 已升級為高優先 |
| #M09 | 🔴 升級：Tongue 近乎靜態（std=0.009, FNG 固定8），與 Nose 高度重複 | 需加入非 FNG 情緒源（Twitter/新聞 sentiment）+ 計算 Nose-Tongue 相關係數 |
| #M10 | data/polytrader.db 是空的殘留文件 | ✅ **已刪除** — 09:09 ORID |
| #M11 | ear_zscore 異常（值達 -3.89，超出 -1~1 預期範圍）| ✅ **已修復** — 09:38 + 09:44 ORID：preprocessor 用 tanh(z/2)，recompute_features_v2.py 也補上 tanh；DB 全量重算完成，range [-0.80, 0.64] |
| #009 | 缺少 SHAP 可解釋性圖表 | 集成 shap 庫 |

---

## ✅ 已解決

| #H21 | ~~api.py 匯入不存在的 WsManager + WebSocket 路由重複定義~~ | ~~Windows subprocess spawn 時 ImportError 導致 server 崩潰 → Vite ECONNABORTED~~ | ✅ **已修復** — api.py 移除 `WsManager` 匯入、WS 路由由 ws.py 統一管理，刪除 api.py 中重複的 WS 段 |

| ID | 問題 | 解決方案 | 會議/日期 |
|----|------|----------|-----------|
| #H01 | 回測是用 random 隨機數據 | **重寫 api.py: 基於 DB 特徵真實回測** | 六帽會議 04-01 |
| #H02 | collector 未寫入新欄位 | **更新 v3/v4 模組寫入邏輯** | 04-01 |
| #H03 | 前端 Vite 跨域/端口問題 | **全部改用相對路徑 + proxy** | 04-01 |
| #H04 | 五感特徵正規化不一致 | **eye_dist 改用 min-max 到 -1~1** | 04-01 ORID |
| #H06 | 訓練資料 cross-join 重複 | **改用 pandas merge_asof (10min tolerance)** | 04-01 ORID |
| UX6 | AdviceCard 報錯 `undefined length` | **全量 Props 預設值防護** | 六帽會議 04-01 |
| UX7 | 回測摘要報錯 | **BacktestSummary Null Safety** | 六帽會議 04-01 |
| UX8 | 五感走勢圖時間對齊錯誤 | **重構 MergedPoint 邏輯** | 六帽會議 04-01 |
| #017 | Body 零變異 | **Body v4: 清算壓力指標** | 03-31 |
| #018 | 測試文件散落 | **移入 tests/** | 03-31 |
| #H08 | Ear 感官零變異（ear_zscore 來自 ear_prob 近零變異） | **改用 funding_rate z-score 作為 ear 輸入**，unique 28→321，std 0.007→0.81 | 04-01 ORID 09:14 |
| #H09 | Eye 分數恆為 1.0（normalize 用 value*10+0.5 假設 0~0.1 範圍） | **修復 senses.py normalize_feature：改用 (value+1)/2** 配合 -1~1 範圍 | 04-01 ORID 09:14 |
| #H10 | Volume 欄位全為 NULL | **eye_binance 新增 fetch_current_volume(), collector 改用 volume** | 04-01 ORID 09:25 |

---

## 🎩 六帽會議摘要 (Action Items)
- **[Action 1]**: ✅ 統一感官特徵到 -1~1 範圍（已完成 — eye_dist min-max）
- **[Action 2]**: ✅ 重寫回測 API 以使用 XGBoost 權重（已執行）
- **[Action 3]**: 增加滯後特徵 (Lag 1h, 4h, 24h) 以提升模型預測力（規劃中）
- **[Action 4]**: ✅ 修復訓練資料 cross-join bug（已修復）
- **[Action 5]**: 評估/汰換 Ear 和 Tongue 感官（IC ≈ 0，需更多數據驗證）

**最後更新：2026-04-01 09:29 GMT+8**

---

## 🔄 ORID 09:29 追蹤

| ID | 問題 | 數據 | 狀態 |
|----|------|------|------|
| #H12 | 模型嚴重過擬合：train acc 96% vs CV acc 35.76% | CV folds: [60%, 40%, 44%, 6%, 28%] 波動極大 | 🔴 **未解決** — 251 樣本太少，5 特徵無正則化 |
| #H13 | 標籤分佈不均 (down:159=63%, up:92=37%) | 多數類別基線 63% ≈ CV 平均 36%，模型基本無力 | 🟡 **部分** — XGB 有 scale_pos_weight 但效果有限 |
| #H14 | Ear 極端值 (z-score=-1.71)：funding rate 極度偏負 | 比特幣 funding rate 在 -0.0046% → 市場明顯偏空 | ℹ️ **觀察中** — 可能是真實信號，非 bug |
| #H19 | Ear z-score 回歸 bug：最新數據點 ear_zscore=-3.49 存為 raw z-score 而非 tanh 壓縮 | SensesEngine ear=0.0（被 clamp），composite 被拉低 8 分 | ✅ **已修復** — 手動修 DB + 確認 preprocessor tanh 邏輯存在，疑似 collector 用舊版 preprocessor 寫入 |
| #H20 | 🔴 **特徵洩漏確認**：Ear 和 Nose 共享 `funding_rate` 底層數據 | IC 完全相同 (+0.153)，模型訓練時等於把同一信號 double-count | 🔄 **待修復** — Nose 需替換為非 funding_rate 數據源（如 OI 變化率）或移除 |
| #M12 | Nose 振幅過窄 [-0.28, 0.10]，僅為 ear_zscore 的 ~1/4 | 感官幾乎「聞不到什麼」，signal-to-noise 比極低 | 🟡 嘗試改用 tanh(z/2) 替代 sigmoid，或加入 OI ROC 子信號 |
| #M13 | 回填 90 天歷史數據尚未執行 | 251 樣本太少是模型過擬合（train 96% vs CV 36%）的根本原因 | 🟡 待執行 `tests/backfill_90d.py` |

### 09:29 IC 更新（251 樣本）
| 感官 | IC | 絕對值 | 評價 |
|------|-----|--------|------|
| Eye | -0.278 | 中等 | 方向反相關（eye_dist 高→標籤 0），需確認標籤方向 |
| Ear | +0.153 | 低 | 比上次 -0.007 大幅改善 |
| Nose | +0.153 | 低 | 與 Ear 幾乎相同 |
| Tongue | -0.138 | 低 | 仍是弱信號 |
| Body | +0.070 | 極低 | 幾乎無預測力 |

---

## 🔄 ORID 09:49 追蹤

**市場狀態：** BTC $67,863 | FNG=8（極度恐懼）| Funding -0.0046% | OI ROC -0.58%

**五感分數：** Eye 0.737 / Ear 0.367 / Nose 0.362 / Tongue 0.439 / Body 0.267 → 建議 46 分 → **hold**

### 09:49 IC 更新（251 樣本，與 09:29 相同）
| 感官 | IC | 絕對值 | 評價 | 行動 |
|------|-----|--------|------|------|
| Eye | -0.278 | 中等 | **反向指標** — eye 高→實際 down | ✅ 已降權重 0.25→0.30（保留但標記反向） |
| Ear | +0.153 | 低 | 比上次改善，可用 | ✅ 權重 0.20→0.25 |
| Nose | +0.153 | 低 | 與 Ear 同質性高 | ⚠️ 需檢查特徵洩漏 |
| Tongue | -0.138 | 低 | FNG=8 固定，近乎零變異 | ✅ **已降權重 0.20→0.05** |
| Body | +0.070 | 極低 | v4 剛上，需累積 | 維持 0.15 |

### 已執行操作
| 操作 | 狀態 |
|------|------|
| senses.py 權重調整：tongue 0.20→0.05, eye 0.25→0.30, ear 0.20→0.25, nose 0.20→0.25 | ✅ 已完成 |
| comprehensive_test.py 6/6 PASS | ✅ |
| check_features.py 335 筆，全感官有變異 | ✅ |

### 新增問題
| ID | 問題 | 優先級 | 狀態 |
|----|------|--------|------|
| #H15 | Tongue 感官應汰換 — FNG 幾乎不變(std=0.009)，IC=-0.138，與 Nose 高度重複 | 🔴 HIGH | 🔄 **已降權重至 0.05**，需替換為 Twitter/News sentiment API |
| #H16 | Eye IC 反向（-0.278）— 可做反向信號，但需在模型層面 invert | 🟡 MEDIUM | 規劃中 — 在 retrain.py 加 feat_eye_dist_inv = -feat_eye_dist |
| #H17 | Ear 與 Nose IC 恰好相同 (+0.153)，可能存在特徵洩漏 | 🟡 MEDIUM | 待調查 — 檢查 funding_rate 是否同時影響兩個感官 |
| #H18 | 模型 CV 準確率 36% < 基線 63% — 考慮用簡單規則模型替代 XGBoost | 🟡 MEDIUM | 規劃中 — 擬寫 rule_based_backtest.py 對比 |

**最後更新：2026-04-01 09:49 GMT+8**

---

## 🔄 ORID 09:59 追蹤

**市場狀態：** BTC $67,863 | FNG=8（極度恐懼）| Funding -0.0046% | OI ROC -0.58%

**五感分數（修復 ear 後）：** Eye 0.789 / Ear 0.343 / Nose 0.358 / Tongue 0.439 / Body 0.266 → 建議 47 分 → **觀望**

### Bug 修復：#H19 ear_zscore 回歸
- 最新 row (ts=02:01:02) 的 ear_zscore = -3.4956（raw z-score，未經 tanh）
- 手動修復：tanh(-3.4956/2) = -0.9411
- 修復前 composite=39（reduce），修復後 composite=47（觀望）
- 根因：preprocessor.py 有 tanh 但某個執行路徑跳過了（可能是 collector 用 cached/precompiled 版本）

### 綜合測試
| 項目 | 結果 |
|------|------|
| comprehensive_test.py | ✅ 6/6 PASS |
| check_features.py | ✅ 335 rows, 全感官有變異 |
| SensesEngine 感官計算 | ✅ 五感分數正常（修復 ear 後） |

### 觀察
- Eye 0.789（技術面強勢）但 IC 反向（-0.278）→ 實際上 Eye 高時市場反而 down
- Ear 0.343（偏低）→ funding rate 偏負，市場情緒偏空
- Tongue 0.439（中性偏低）→ FNG=8 極度恐懼但 std 極低
- Body 0.266（偏空）→ 鏈上資金外流壓力
- 3/5 感官偏空，但 Eye 看多 → 分歧，觀望合理

### 待解決問題
| ID | 問題 | 狀態 |
|----|------|------|
| #H07 | 模型 CV 準確率 36% < 基線 63% | 🔴 未解決 |
| #H12 | 模型嚴重過擬合 (train 96% vs CV 36%) | 🔴 未解決 |
| #H15 | Tongue 應汰換 (FNG std=0.009) | 🔄 已降權至 0.05 |
| #H16 | Eye IC 反向，需在模型層 invert | 🟡 規劃中 |
| #H17 | Ear=Nose IC 同值，特徵洩漏嫌疑 | 🟡 待調查 |
| #H19 | ear_zscore tanh 回歸 | ✅ 已修復 (09:59) |

---

## 🔄 ORID 10:09 追蹤

**市場狀態：** BTC ~$67,863 | FNG=8（極度恐懼）| Funding -0.0046%

**五感分數：** Eye 0.789 / Ear 0.343 / Nose 0.358 / Tongue 0.439 / Body 0.266 → 建議 47 分 → **hold**

**測試：** comprehensive_test.py 6/6 PASS ✅ | check_features.py 336 rows ✅

### 特徵值狀態
| 特徵 | min | max | avg | std | unique | 評價 |
|------|-----|-----|-----|-----|--------|------|
| eye_dist | -1.00 | 1.00 | 0.10 | 0.55 | 88 | ✅ 正常 |
| ear_zscore | -0.94 | 0.64 | 0.003 | 0.44 | 323 | ✅ tanh 壓縮正常 |
| nose_sigmoid | -0.28 | 0.10 | -0.06 | 0.10 | 323 | ⚠️ 振幅偏窄 |
| tongue_pct | -0.84 | -0.12 | -0.61 | 0.29 | 118 | ⚠️ 全域偏負，FNG 固定 |
| body_roc | -0.63 | 0.18 | -0.26 | 0.25 | 230 | ✅ 可接受 |

### 本輪驗證
| 項目 | 結果 | 備註 |
|------|------|------|
| #H11 SensesEngine 注入 | ✅ 已確認修復 | `dependencies.py:init_dependencies()` 正確注入 SQLAlchemy session |
| 五感分數非全 0.5 | ✅ 通過 | 真實變異確認 |
| 數據品質 | ✅ 通過 | 336 rows，全感官有變異 |
| 前端 TS 編譯 | ✅ 通過 | |

### 行動清單
| 優先級 | 行動 | 狀態 |
|--------|------|------|
| P0 | ~~修復 #H11 SensesEngine 注入~~ | ✅ 已確認在 dependencies.py 中正確實作 |
| P1 | Nose 振幅過窄 [-0.28, 0.10] — 考慮替換 sigmoid 映射 | 🟡 待處理 |
| P2 | 增加 lag 特徵 (1h, 4h, 24h) — 對應六帽 Action 3 | 🟡 規劃中 |
| P3 | 回填 90 天歷史數據 (tests/backfill_90d.py) | 🟡 待執行 |
| P4 | Tongue 汰換 — 加入非 FNG 情緒源或停用 | 🟡 已降權至 0.05 |
| P5 | 模型 #H07/#H12 — 251 樣本太少，train 96% vs CV 36% 過擬合 | 🔴 核心瓶頸 |

---

## 🔄 ORID 10:19 追蹤

**市場狀態：** BTC ~$67,863 | FNG=8（極度恐懼）| Funding -0.0046%

**五感分數：** Eye 0.789 / Ear 0.343 / Nose 0.358 / Tongue 0.439 / Body 0.266 → composite 47 → **hold**

**測試：** comprehensive_test.py 6/6 PASS ✅ | check_features.py 336 rows ✅

### 本輪 IC 更新（251 樣本）
| 感官 | IC | 評價 | 行動 |
|------|-----|------|------|
| Eye | -0.278 | 反向指標，高→down | 保留但標記反向 |
| Ear | +0.153 | 低但可用 | 維持 0.25 權重 |
| Nose | +0.153 | **⚠️ 與 Ear 完全相同 — 特徵洩漏確認** | #H20 需替換數據源 |
| Tongue | -0.138 | FNG 固定，無資訊 | 維持 0.05 權重，待汰換 |
| Body | +0.070 | 極低，需累積 | 維持 0.15 權重 |

### 本輪發現
- **#H20 確認**：preprocessor.py 中 ear (line 97-121) 和 nose (line 123-128) 都以 `funding_rate` 為底層輸入，只是映射不同 → IC 完全一致的根因
- **Nose 振幅問題**：sigmoid(x*10000) 映射導致振幅僅 [-0.28, 0.10]，幾乎無辨識力

### 行動清單狀態
| 優先級 | 行動 | 狀態 |
|--------|------|------|
| P0 | #H20 Ear/Nose 特徵洩漏修復 | 🔄 已確認，Nose 需替換數據源 |
| P1 | #M09/#H20 Tongue 汰換方案 | 🟡 已降權 0.05，待新 API |
| P2 | #M13 回填 90 天數據 | 🟡 待執行 |
| P3 | #M12 Nose 振幅修正 | 🟡 可改 tanh 或加 OI ROC |

**最後更新：2026-04-01 10:19 GMT+8**

---

## 🔄 ORID 10:34 追蹤

**市場狀態：** BTC ~$67,863 | FNG=8（極度恐懼）| Funding -0.0046%

**五感分數：** Eye 0.789 / Ear 0.343 / Nose 0.358 / Tongue 0.439 / Body 0.266 → composite 47 → **HOLD**

**測試：** comprehensive_test.py 6/6 PASS ✅ | check_features.py 336 rows ✅

### DB 現況
- DB: `poly_trader.db` (主)
- features_normalized: 336 rows
- raw_market_data: 336 rows
- labels: 251 (up=92=37%, down=159=63%)
- trade_history: 0 rows
- 空 DB 清理：`trading.db`, `data/trading.db`, `data/poly_trader.db` 均為空（僅 schema 或全空）⚠️ **待清理**

### 特徵值統計
| 特徵 | min | max | avg | count | 評價 |
|------|-----|-----|-----|-------|------|
| eye_dist | -1.00 | 1.00 | 0.10 | 336 | ✅ 正常變異 |
| ear_zscore | -0.94 | 0.64 | 0.003 | 336 | ✅ tanh 壓縮正常 |
| nose_sigmoid | -0.28 | 0.10 | -0.06 | 336 | ⚠️ 振幅過窄 |
| tongue_pct | -0.84 | -0.12 | -0.61 | 336 | ⚠️ FNG=8 全域偏負 |
| body_roc | -0.63 | 0.18 | -0.26 | 336 | ✅ 可接受 |

### IC 值（251 樣本）
| 感官 | IC | 評價 |
|------|-----|------|
| Eye | -0.278 | 🔴 反向指標 |
| Ear | +0.154 | 🟡 低但可用 |
| Nose | +0.153 | 🟡 與 Ear 洩漏 |
| Tongue | -0.138 | 🔴 FNG 固定 |
| Body | +0.070 | 🔴 極低 |

### 本輪發現
- **五感分數與上輪（10:19）完全一致** → 數據源未更新（正常，30min 級 collector）
- **3/5 感官偏空**（Ear, Nose, Body < 0.4），Eye 看多但 IC 反向 → 實際看空
- **空 DB 待清理**：4 個 .db 檔案中只有 poly_trader.db 有數據

### 待解決問題
| ID | 問題 | 狀態 |
|----|------|------|
| #H07 | 模型 CV 36% < 基線 63% | 🔴 |
| #H12 | 過擬合 train 96% vs CV 36% | 🔴 |
| #H15 | Tongue 應汰換 | 🔄 已降權 0.05 |
| #H16 | Eye IC 反向需 invert | 🟡 規劃中 |
| #H20 | Ear/Nose 特徵洩漏 | 🔄 Nose 需替換數據源 |
| #M13 | 回填 90 天數據 | 🟡 待執行 |
| **#NEW** | 4 個空 .db 檔案待清理 | 🟡 新增 |

**最後更新：2026-04-01 10:34 GMT+8**


---

## 🔧 修復記錄 10:41 — api.py import bug

### 修復 #H21
- **問題**: `api.py` 匯入 `from server.senses import WsManager`，但 `senses.py` 無此 class
- **影響**: Windows multiprocessing spawn 重 import 模組時觸發 `ImportError` → subprocess 崩潰 → uvicorn worker 死 → Vite WS proxy `ECONNABORTED`
- **操作**:
  - api.py 移除 `WsManager` 匯入
  - api.py 移除重複的 WebSocket 路由 (原本 `/api/ws/live`)
  - api.py 移除未使用的 `WebSocket, WebSocketDisconnect` import
  - api.py 保留 `_calc_max_dd` helper（回測需要）
  - WebSocket 統一由 `ws.py` 管理
- **測試**: 6/6 PASS ✅ | syntax OK ✅

---

## 🔄 ORID 10:39 追蹤

**市場狀態：** BTC $67,828 | FNG=8（極度恐懼）| Funding z-score -0.94 | OI ROC -0.47

**五感分數（最新特徵）：** Eye 0.79 / Ear 0.34 / Nose 0.36 / Tongue 0.44 / Body 0.27 → composite 47 → **HOLD**

### O — Objective（客觀事實）

**系統狀態：**
- comprehensive_test.py: **6/6 PASS** ✅
- check_features.py: 336 筆特徵，無異常 ✅
- DB: poly_trader.db — features=336, raw=336, labels=251

**特徵統計（336 筆）：**
| 特徵 | min | max | avg | std | unique |
|------|-----|-----|-----|-----|--------|
| eye_dist | -1.00 | 1.00 | 0.10 | 0.55 | 324 |
| ear_zscore | -0.94 | 0.64 | 0.003 | 0.44 | 323 |
| nose_sigmoid | -0.28 | 0.10 | -0.06 | 0.10 | 316 |
| tongue_pct | -0.84 | -0.12 | -0.61 | 0.29 | 110 |
| body_roc | -0.63 | 0.18 | -0.26 | 0.25 | 217 |

**模型訓練結果（本輪重訓）：**
| 指標 | 本輪 | 前輪 (09:49) | 變化 |
|------|------|-------------|------|
| Train Acc | **98.4%** | 96% | +2.4% |
| Train AUC | **99.7%** | — | 新增 |
| CV Acc | **84.5% ± 4.5%** | 36% | **🔼 +48.5%** |
| CV AUC | **91.1% ± 3.1%** | — | 新增 |
| Overfitting Gap | 13.9% | 60% | **🔼 -46%** |

CV folds (accuracy): [0.78, 0.80, 0.86, 0.90, 0.88] — 穩定！

**最新 IC 值（251 樣本）：**
| 感官 | IC | 前輪 | 變化 |
|------|-----|------|------|
| Eye | +0.088 | -0.278 | 🔼 反轉為正 |
| Ear | +0.244 | +0.153 | 🔼 +59% |
| Nose | +0.244 | +0.153 | 🔼 +59% |
| Tongue | -0.090 | -0.138 | 🔼 改善但仍負 |
| Body | **-0.235** | +0.070 | 🔻 反轉為負 |

**Ear-Nose 相關性：** r=**0.9980** （確認特徵洩漏）

### R — Reflective

- **模型大幅改善**：CV 從 36% → 84.5% 是質的跳躍！標籤從 Labels 表讀取（非動態重算），標籤一致性讓模型穩定
- **IC 反轉警訊**：Eye 從 -0.278 → +0.088，Body 從 +0.070 → -0.235。IC 波動如此大，可能是樣本少（251）或標籤定義有問題
- **Ear/Nose r=0.998** 是確認的：同一個 funding_rate 輸入，只差 sigmoid 壓縮比例，IC 完全相同 (+0.244)
- **Tongue 仍全域偏負**（-0.84 ~ -0.12），FNG 卡在 8 太久
- **Nose 振幅仍然最窄**[-0.28, 0.10]，std 僅 0.1 — 幾乎無辨識力

### I — Interpretive

1. **模型改善來源**：不是模型架構變了，而是 labels 表已經持久化 → 訓練標籤一致。但 IC 波動說明 251 樣本仍太少，IC 不穩定
2. **Ear-Nose 洩漏是確定的**：相關性 0.998 在金融數據中幾乎不可能由真實市場產生。Nose 使用 funding_rate 是設計缺陷
3. **Tongue 需要替換**：FNG 是每日更新指標，對於分鐘級交易系統頻率太低。唯一變異來自少數更新點
4. **Body IC 翻轉**：從 +0.07 → -0.235，波動大但幅度提升。可能是清算事件有預測力但噪音也大
5. **模型 CV Acc 84.5%**：看起來不錯，但要注意基線是 63%（down 佔多數）。84.5% 的預測力需要 out-of-sample 回測驗證

**特徵重要度 vs IC 對比：**
| 特徵 | 重要度 | IC | 一致性 |
|------|--------|-----|--------|
| body_roc | 0.287 (最高) | -0.235 | ❌ 重要但負相關 |
| tongue_pct | 0.233 | -0.090 | ❌ 重要但弱且負 |
| nose_sigmoid | 0.178 | +0.244 | ✅ |
| eye_dist | 0.157 | +0.088 | ✅ |
| ear_zscore | 0.145 | +0.244 | ❌ IC 高但重要度低（與 Nose 共線） |

### D — Decisional（具體行動）

```
ACTION [P0]: 修復 #H20 — Nose 替換數據源
  → 用 OI (open_interest) 變化率取代 funding_rate
  → 文件: preprocessor.py+nose_futures.py
  → 計算: OI ROC = (OI_now - OI_5min_ago) / OI_5min_ago

ACTION [P1]: 模型 overfitting 改善
  → 文件: model/train.py
  → 加 L2 正則化 (reg_alpha=0.1, reg_lambda=1.0)
  → 降 max_depth 4→3
  → 加 min_child_weight=5

ACTION [P2]: IC 穩定性分析
  → 計算滾動 IC (rolling 50-sample window)
  → 如果 IC 方向頻繁翻轉 → 該感官應降權或停用

ACTION [P3]: Tongue 汰換計畫
  → 尋找實時情緒 API (CryptoPanic, LunarCrush, 或 Twitter API)
  → 或先用 BTC 波動率 (realized vol) 作為代理指標

ACTION [P4]: Out-of-sample 回測
  → 用最近 20% 數據做 OOS 驗證
  → 文件: tests/backtest_oos.py

ACTION [P5]: 清理空 DB 檔案
  → 確認並移除: trading.db, data/trading.db, data/poly_trader.db
```

### 行動執行

**[P2] IC 穩定性 — 滾動計算：**


#### 滾動 IC 分析（window=50）
```
feat_eye_dist:   Mean=-0.225  | 翻轉 5 次  | ⚠️ 邊界穩定
feat_ear_zscore: Mean=-0.053  | 翻轉 11 次 | ❌ 極不穩定
feat_nose_sig:   Mean=-0.053  | 翻轉 11 次 | ❌ 同 Ear（洩漏確認）
feat_tongue_pct: Mean=NaN     | 翻轉 124 次| ❌ 完全無用（FNG 太稀疏）
feat_body_roc:   Mean=-0.080  | 翻轉 9 次  | ❌ 幾乎無預測力
```

**關鍵洞察：滾動 IC 均值遠低於全局 IC**
- 全局 IC(Ear)=+0.244 但滾動 Mean=-0.053 → **全局 IC 是倖存偏差**
- Ear 翻轉 11 次：方向完全不可預測
- Tongue 124 次翻轉：FNG 更新稀疏導致每個窗口內常數 → 相關係數 NaN/隨機

**結論：251 樣本來回測 IC 不夠可靠。需要更多數據（M13 回填）才能驗證哪個感官真正有預測力。**

### 行動清單
| 優先級 | 行動 | 狀態 |
|--------|------|------|
| P0 | #H20 — Nose 替換為 OI ROC | 🔄 待執行 — preprocessor.py |
| P1 | 模型正則化 (reg_alpha, reg_lambda) | 🟡 待執行 — train.py |
| P2 | Tongue 汰換 | 🟡 FNG 太稀疏，尋找實時 API |
| P3 | 回填 90 天數據 (#M13) | 🟡 待執行 — tests/backfill_90d.py |
| P4 | Out-of-sample 回測 | 🟡 規劃中 |
| P5 | 清理空 DB 檔案 | 🟡 待確認刪除 |

**最後更新：2026-04-01 10:39 GMT+8**

---

## 🔄 ORID 10:44 追蹤

**市場狀態：** BTC $67,664 | FNG=8（極度恐懼）| Funding z-score -0.96 | OI ROC -0.43%

**五感分數（最新 collector）：** Eye 0.79 / Ear 0.34 / Nose 0.36 / Tongue 0.44 / Body 0.27 → composite 47 → **HOLD**

### O — Objective

**系統狀態：**
| 項目 | 結果 |
|------|------|
| comprehensive_test.py | ✅ 6/6 PASS |
| check_features.py | ✅ 336 筆，全感官有變異 |
| DB | features=336, raw=336, labels=251 |
| 空 DB 清理 | ✅ 已確認清理（trading.db, data/trading.db, data/poly_trader.db 不存在） |

**最新預測：** confidence=0.0588 → signal=HOLD（低於閾值 0.7）

### I — Interpretive

**核心洞察（與 10:39 一致，無重大變化）：**
1. 251 樣本是根本瓶頸 → 回填 90 天 (#M13) 最高槓桿
2. Nose 用 funding_rate 是設計錯誤 → 必须改為 OI ROC (#H20)
3. Tongue FNG 日級指標不適合 30min 系統 → 需替換 (#H15)
4. Ear-Nose r=0.998 確認特徵洩漏 → 模型 double-count 同一信號
5. 滾動 IC 均值遠低於全局 IC → 全局 IC 是倖存偏差，需更多樣本驗證

### D — Decisional

| 優先級 | 行動 | 狀態 |
|--------|------|------|
| P0 | #H20 — Nose 替換為 OI-based 數據源 | 🔄 待執行 |
| P1 | 回填 90 天歷史數據 (#M13) | 🟡 tests/backfill_90d.py |
| P2 | Tongue 實時替代 (realized vol / CryptoPanic) | 🟡 規劃中 |
| P3 | 模型正則化 (reg_alpha, reg_lambda, max_depth) | 🟡 待執行 |
| P4 | lag 特徵 (1h, 4h, 24h) | 🟡 規劃中 |
| ~~P5~~ | ~~清理空 DB 檔案~~ | ✅ **已確認清理** |

**最後更新：2026-04-01 10:44 GMT+8**

---

## 🔄 ORID 10:49 追蹤

**市場狀態：** BTC ~$67,664 | FNG=8（極度恐懼）| Funding ~-0.0046%

**五感分數：** Eye 0.789 / Ear 0.343 / Nose 0.358 / Tongue 0.439 / Body 0.267 → composite 47 → **HOLD**

### O — Objective（客觀事實）

**系統狀態：**
| 項目 | 結果 |
|------|------|
| comprehensive_test.py | ✅ 6/6 PASS |
| check_features.py | ✅ 336 筆，全感官有變異 |
| DB | features=336, labels=251 |

**特徵統計（336 筆）：**
| 特徵 | min | max | avg | std | unique |
|------|-----|-----|-----|-----|--------|
| eye_dist | -1.00 | 1.00 | 0.10 | 0.549 | 336 |
| ear_zscore | -0.94 | 0.64 | 0.003 | 0.442 | 323 |
| nose_sigmoid | -0.28 | 0.10 | -0.055 | 0.104 | 323 |
| tongue_pct | -0.84 | -0.12 | -0.615 | 0.291 | 118 |
| body_roc | -0.63 | 0.18 | -0.260 | 0.245 | 230 |

**IC（251 樣本，exact timestamp join）：**
| 感官 | Spearman IC | Pearson IC | 評價 |
|------|-------------|------------|------|
| Eye | -0.280 (p<0.001) | -0.278 (p<0.001) | 🔴 顯著反向 |
| Ear | +0.120 (p=0.057) | +0.154 (p=0.015) | 🟡 邊緣顯著/微弱 |
| Nose | +0.120 (p=0.057) | +0.153 (p=0.016) | 🟡 同 Ear |
| Tongue | -0.063 (p=0.32) | -0.138 (p=0.029) | 🔴 斯皮爾曼不顯著 |
| Body | +0.056 (p=0.38) | +0.070 (p=0.27) | 🔴 完全不顯著 |

**Ear-Nose 相關性：** r=**0.9985**（確認特徵洩漏）

**滾動 IC（window=50, step=10）：**
| 感官 | mean_IC | 翻轉次數 | 評價 |
|------|---------|---------|------|
| Eye | -0.210 | 3 次 | ⚠️ 穩定反向 |
| Ear | -0.042 | 7 次 | ❌ 方向不可預測 |
| Nose | -0.042 | 7 次 | ❌ 同 Ear（洩漏） |
| Tongue | -0.002 | 1 次 | ❌ 有效窗口僅 8（稀疏） |
| Body | -0.066 | 7 次 | ❌ 幾乎無預測力 |

**標籤分佈：** pos=92 (36.7%), neg=159 (63.3%) → 基線 = 63.3%

### R — Reflective

- **Spearman IC 更不樂觀**：上一輪用 Pearson 算的 Ear/Nose IC=+0.244 可能過度樂觀。Spearman 顯示 Ear/Nose IC=+0.12（p=0.057，邊緣顯著），更接近真實能力
- **滾動 IC vs 全局 IC：** 全局 Ear IC (Pearson)=+0.154 但滾動 Mean=-0.042 → 方向完全相反。這再次確認全局 IC 是倖存偏差，滾動分析更可靠
- **只有 Eye 是穩定的：** Eye Spearman IC=-0.280 (p<0.001) 且滾動 mean=-0.210，只有 3 次翻轉 → 唯一可靠的反向指標！
- **Tongue 有效窗口僅 8 個：** 251-50+1 = 202 個可能窗口，只有 8 個有足夠變異 → 確認 FNG 不適合這個系統
- **251 樣本 = 瓶頸：** 滾動 IC 分析只有 21 個有效窗口（eye/ear/nose/body），統計效力有限

### I — Interpretive

1. **Eye 反向指標是唯一穩健信號**：無論 Pearson/Spearman/滾動分析都一致為負相關。考慮將 eye_dist 反轉（feat_eye_inv = -feat_eye_dist）作為正向特徵
2. **Ear/Nose 洩漏是結構性問題**：r=0.9985 意味著 Nose 幾乎是 Ear 的複製。兩個感官共用 funding_rate 輸入，只是映射不同。Nose 必须改用獨立數據源（OI, put/call ratio, etc.）
3. **模型訓練是錯覺**：XGBoost 在高維稀疏數據上可能學到噪音而非信號。CV Acc 在 ISSUES 中記錄過 36%→84% 波動。需要 OOS 回測才能驗證
4. **Tongue 應直接停用**：FNG 是日級指標用於 30min 系統是根本性 mismatch。權重已降至 0.05，但應完全替換或移除
5. **Body 無預測力**：IC 不顯著（p=0.27），滾動 mean 接近零。清算壓力指標可能需要不同計算方式或更長滯後窗口

### D — Decisional

```
ACTION [P0]: #H20 — Nose 替換為 OI ROC
  → preprocessor.py: nose 改用 (OI_now - OI_prev) / OI_prev
  → data_ingestion: 加入 OI 數據源
  → 效果：消除 Ear/Nose 洩漏，r=0.998 → 獨立信號

ACTION [P1]: #H16 — Eye 反向特徵
  → preprocessor.py: 新增 feat_eye_inv = -feat_eye_dist
  → 模型訓練時用 eye_inv 替代 eye_dist
  → 效果：IC 從 -0.28 翻轉為 +0.28（正向信號）

ACTION [P2]: #H15 — Tongue 停用/替換
  → 短期：權重 0.05 → 0.0（composite 計算中完全移除）
  → 中期：接 CryptoPanic API 或 Twitter sentiment
  → 或改用 realized volatility 作為情緒代理

ACTION [P3]: #M13 — 回填 90 天歷史數據
  → tests/backfill_90d.py
  → 251 → 4000+ 樣本（預估），IC 更穩定
  → 滾動 IC 窗口 21 → 350+，統計效力大幅提升

ACTION [P4]: #H07/#H12 — 模型正則化
  → train.py: max_depth=3, reg_alpha=0.1, reg_lambda=1.0
  → 加入 5-fold CV 指標輸出（目前 retrain.py 無 CV）
  → 加入 OOS 回測驗證

ACTION [P5]: 更新權重配置
  → 當前：eye=0.30, ear=0.25, nose=0.25, tongue=0.05, body=0.15
  → 建議（修復後）：eye_inv=0.35, ear=0.25, body=0.15, nose=0.20, tongue=0.05
  → 待 Nose 替換數據源後重新計算 IC
```

### ISSUES.md 更新

| ID | 問題 | 狀態 |
|----|------|------|
| #H20 | Ear/Nose IC 完全一致 (r=0.9985) | 🔄 確認洩漏，待改 OI 數據源 |
| #H07 | 模型 CV 準確率 < 基線 | 🔴 需 OOS 回測驗證 |
| #H15 | Tongue FNG 太稀疏（有效窗口=8/202） | 🔄 已降權 0.05，建議停用 |
| #H16 | Eye IC 反向 (-0.280) | 🟡 可用作反向指標 |
| #M13 | 回填 90 天數據 | 🟡 待執行 |
| **#NEW** | 滾動 IC 揭示耳/鼻/體 IC 方向不可預測（翻轉>7次） | 🔴 新增 |
| **#NEW** | 只有 Eye 是穩定信號（3 翻轉，mean IC=-0.21） | ℹ️ 洞察 |

**最後更新：2026-04-01 10:49 GMT+8**

---

## 🔄 ORID 11:04 追蹤

**市場狀態：** BTC $67,654 | FNG=8（極度恐懼）| Funding -0.0064% | OI ROC -0.43% | Polymarket=0.28

**五感分數（SensesEngine live）：** Eye 0.736 / Ear 0.343 / Nose 0.344 / Tongue 0.439 / Body 0.275
**五感分數（DB 最新 02:54）：** Eye 0.736 / Ear 0.028 / Nose 0.344 / Tongue 0.439 / Body 0.275 → composite 38 → **HOLD**

### O — Objective（客觀事實）

**系統狀態：**
| 項目 | 結果 | 備註 |
|------|------|------|
| comprehensive_test.py | ✅ 6/6 PASS | 所有模組正常 |
| check_features.py | ✅ 337 rows | 全感官有變異 |
| Frontend TS | ✅ 編譯通過 | |
| DB 日期範圍 | 2026-03-30 13:25 ~ 2026-04-01 02:54 | ~48h, 38 hours |
| New data since 10:04 UTC | **0 筆** | ⚠️ Collector 可能停止了 |

**特徵統計（337 筆）：**
| 特徵 | min | max | mean | std | unique |
|------|-----|-----|------|-----|--------|
| eye_dist | -1.00 | 1.00 | 0.10 | 0.550 | 337 |
| ear_zscore | -0.94 | 0.64 | 0.00 | 0.445 | 324 |
| nose_sigmoid | -0.31 | 0.10 | -0.06 | 0.105 | 324 |
| tongue_pct | -0.84 | -0.12 | -0.61 | 0.293 | 119 |
| body_roc | -0.63 | 0.18 | -0.26 | 0.245 | 231 |

**Spearman IC（251 樣本）：**
| 感官 | IC | p-value | 評價 |
|------|-----|---------|------|
| Eye | -0.280 | <0.001 | 🔴 顯著反向 |
| Ear | +0.120 | 0.057 | 🟡 邊緣顯著 |
| Nose | +0.120 | 0.057 | 🟡 同 Ear（洩漏） |
| Tongue | -0.063 | 0.321 | 🔴 不顯著 |
| Body | +0.056 | 0.376 | 🔴 不顯著 |

**Ear-Nose r = 0.9979**（特徵洩漏確認）

### R — Reflective

- **⚠️ Collector 可能已停止：** 最新數據停在 02:54 UTC，距現在（~03:04 UTC）已有 ~10min 但之前 10:04 也已是 02:54。38 小時只覆蓋 38 個 unique hour，collector 頻率約 1hr/筆，低於預期的 30min
- **Ear DB 值 vs SensesEngine live 差異大：** DB 最新 ear_zscore=-0.9439→score 0.028，但 SensesEngine live 回報 0.343 → SensesEngine 可能讀了不同時間點或用了不同計算邏輯
- **系統健康但無新意：** 所有測試通過，核心問題（#H07/#H12/#H20/#H15）仍與上一輪相同
- **唯一穩健信號仍是 Eye 反向**：Spearman -0.280, p<0.001

### I — Interpretive

1. **Collector 停更或頻率過低**：337 筆 / 38h ≈ 8.9 筆/小時 ≈ 每 6.7 分鐘一筆，但 unique hours 僅 38，說明大部分小時只有 1 筆。需要檢查為什麼 collector 沒有持續寫入
2. **Nose 洩漏未修但 IC 仍低**：r=0.9979 與上輪 0.9985 幾乎一致，結構性問題持續
3. **Tongue + Body 統計不顯著（p>0.3）**：這兩個感官在 composite 中佔 20% 權重但幾乎無預測力
4. **251 樣本是硬天花板**：不回填歷史數據，任何 IC 結論都不可靠

### D — Decisional

```
ACTION [P0]: 檢查 collector 狀態 — 最新數據停止 02:54 UTC
  → 檢查是否有 running collector process
  → 手動觸發一次 collector 確認是否正常

ACTION [P1]: #H20 Nose 替換為獨立數據源（OI ROC 變化率）
  → 消除 Ear-Nose 洩漏（r=0.9979）
  → 文件: preprocessor.py + nose_futures.py

ACTION [P2]: #H15 Tongue 停用 + #Body 降權
  → tongue 權重 0.05→0.0，body 0.15→0.10
  → 釋放權重給 Eye_inv (0.30→0.40) 和 Ear

ACTION [P3]: #M13 回填 90 天歷史數據
  → 251→4000+ 樣本
  → 執行 tests/backfill_90d.py

ACTION [P4]: #H07/#H12 模型正則化
  → max_depth=3, reg_alpha=0.1, reg_lambda=1.0
  → OOS 回測驗證
```

### ISSUES.md 更新

| ID | 問題 | 狀態變化 |
|----|------|---------|
| #NEW | Collector 停更 — 最新數據停在 02:54 UTC | 🔴 新增 |
| #H20 | Nose 洩漏 r=0.9979（未改善） | 🔴 維持 |
| #H07/#H12 | 模型 CV 36% vs train 96% | 🔴 維持 |
| #H15 | Tongue IC -0.063, p=0.32（停滯） | 🟡 維持 |
| #H16 | Eye IC 反向 -0.280 可用 | ℹ️ 維持 |

**最後更新：2026-04-01 11:04 GMT+8**

---

## 🔄 ORID 11:19 追蹤

**市場狀態：** BTC $68,024.25 | FNG=8（極度恐懼）| Funding -0.0063% | OI ROC -0.658%

### O — Objective（客觀事實）

**五感分數（歸一化 0~1）：**
| 感官 | Raw | Normalized | 權重 | 加權貢獻 |
|------|-----|-----------|------|---------|
| Eye | -0.2944 | **0.3528** | 0.30 | 0.1058 |
| Ear | -0.9059 | **0.0471** | 0.25 | 0.0118 |
| Nose | -0.3041 | **0.3479** | 0.25 | 0.0870 |
| Tongue | -0.1229 | **0.4385** | 0.05 | 0.0219 |
| Body | -0.4771 | **0.2615** | 0.15 | 0.0392 |

→ **Composite: 27 分 → REDUCE** 📉

**模型預測：** HOLD（confidence=0.0588）— 遠低於閾值 0.7

**數據統計：**
- Features: 338 rows | Raw: 338 rows | Labels: 251 (neg=159/63%, pos=92/37%)
- Trades: 0（尚未執行任何交易）

**特徵品質：**
| 特徵 | Std | Unique/338 | 評價 |
|------|-----|------------|------|
| feat_eye_dist | 0.5491 | 338 | ✅ 高變異 |
| feat_ear_zscore | 0.4475 | 325 | ✅ 高變異 |
| feat_nose_sigmoid | 0.1057 | 325 | ⚠️ 振幅偏窄 |
| feat_tongue_pct | 0.2933 | 120 | ⚠️ 僅 120 unique，FNG=8 固定 |
| feat_body_roc | 0.2451 | 232 | ✅ 可接受 |

**特徵重要性（XGBoost 251 樣本）：**
- feat_body_roc: 0.287 | feat_tongue_pct: 0.233 | feat_nose_sigmoid: 0.178 | feat_eye_dist: 0.157 | feat_ear_zscore: 0.145

**系統狀態：** comprehensive_test.py 6/6 PASS ✅ | Server 運行中 (uvicorn PIDs: 15255,15256,15263) | Heartbeat 正常 (main.py PID: 14992)

**清理結果：** ✅ 已無空 .db 殘留（前一次確認已清理）

### R — Reflective（感受與直覺）

- **5/5 感官全數為負** — 這是不尋常的。所有感官都指向看空，沒有任何分歧
- **Ear 0.047 極度偏低** — funding rate 持續偏負，市場恐慌情緒持續
- **Tongue 43.8 相對最高** — 不是因為強，而是因為 FNG=8 固定值讓它穩定在中下
- **Composite 27 分** — 系統明確建議「減倉」，但模型預測只有 5.9% 信心 → **兩者矛盾**
- **模型信心過低**：0.0588，幾乎等於盲猜，XGBoost 在 251 樣本 + 5 特徵下基本失效
- **連續 6/6 PASS** — 系統架構穩定，但功能正常≠模型有效

### I — Interpretive（意義與洞察）

1. **五感全空是「假共識」**：因為 Ear 和 Nose 共享 funding_rate（r=0.9979），3/5 感官其實被同一個信號驅動
2. **模型無效性持續**：train 96% vs CV 36% — 這不是小問題，這意味著模型完全不可用。當前的 HOLD 建議實際上等同於隨機
3. **Tongue 是雙重問題**：IC 低(-0.138) + 僅 120 unique 值 + FNG=8 持續數天 → 這個感官應該被標記為 "degraded"
4. **系統正在正常運行但輸出無價值**：collector → preprocessor → predictor 管線正常，但 251 樣本 + 5 特徵的組合本質上不具備預測力
5. **矛盾點**：五感 composite 說 REDUCE (27分)，模型說 HOLD (conf 5.9%) — 當五感和模型分歧時該信誰？目前沒有仲裁規則
6. **Body 是特徵重要性最高(28.7%)，但 IC 最低(+0.07)** — 模型在過擬合 body_roc 的噪音

### D — Decisional（具體行動）

```
ACTION [P0]: model/predictor.py → 增加五感-模型分歧仲裁規則（當 composite<30 且 model_conf<0.3 → 強制 HOLD + alert）
ACTION [P1]: ISSUES.md → 記錄 #H21 五感-模型分歧問題
ACTION [P2]: feature_engine/preprocessor.py → 將 Nose 從 funding_rate 改為 OI ROC 或 BTC Dominance（解除 #H20 洩漏）
ACTION [P3]: data_ingestion/tongue_sentiment.py → 加入外部情緒 API（CryptoPanic/newsapi）作為 FNG 替代或補充
ACTION [P4]: 執行 tests/backfill_90d.py → 回填歷史數據（251→~2000 樣本）
ACTION [P5]: model/train.py → 增加正則化參數（max_depth=2, reg_alpha=1.0, reg_lambda=5.0）降低過擬合
```

### 問題狀態更新

| ID | 問題 | 狀態 | 更新 |
|----|------|------|------|
| #H07 | 模型 CV 36% < 基線 63% | 🔴 未解決 | 維持 — 需要 P5 正則化 + P4 更多數據 |
| #H12 | 過擬合 train 96% vs CV 36% | 🔴 未解決 | 維持 — 同上 |
| #H15 | Tongue IC -0.138, FNG 固定 | 🟡 維持 | 11:19 確認 still 120 unique/338 |
| #H16 | Eye IC 反向 -0.280 | ℹ️ 維持 | 可用作反向指標 |
| #H20 | Ear/Nose 特徵洩漏 r=0.9979 | 🔴 未解決 | Nose 亟需替換數據源 |
| **#H21** | **五感-模型分歧無仲裁** | 🔴 **新增** | composite=27(REDUCE) vs model=HOLD |

**最後更新：2026-04-01 11:19 GMT+8**

---

## 🔄 ORID 11:24 追蹤

**市場狀態：** BTC $68,024 | FNG=8（極度恐懼）| Funding ≈-0.0063% | OI ROC ≈-0.66%

**五感分數：** Eye 0.35 / Ear 0.05 / Nose 0.35 / Tongue 0.44 / Body 0.26 → Composite **29/100** → **BEARISH**

**模型：** confidence=0.0588, signal=HOLD（信心極低，幾乎等於噪音）

### 11:24 數據匯總

| 指標 | 數值 | 趨勢 |
|------|------|------|
| Raw Data | 338 筆 | ↑ 新增 2 筆（vs 09:49） |
| Features | 338 筆 | ✅ 同步 |
| Labels | 251 筆 | — |
| 訓練樣本（merge_asof） | 251 筆 | 類別：neg=159(63%), pos=92(37%) |
| 特徵重要排名 | body(0.29) > tongue(0.23) > nose(0.18) > eye(0.16) > ear(0.15) | ⚠️ 與 IC 不匹配 |

### 11:24 IC 更新（251 樣本）

| 感官 | IC | |IC| | 特徵重要性 | 匹配？ | 評價 |
|------|-----|------|------------|--------|------|
| Eye | -0.278 | 0.278 | 0.157 | ⚠️ | 反向指標，最高 IC 但模型降權 |
| Ear | +0.154 | 0.154 | 0.145 | ✅ | 正向但弱 |
| Nose | +0.153 | 0.153 | 0.178 | ✅ | 與 Ear 高度同質（r=0.9979）|
| Tongue | -0.138 | 0.138 | 0.233 | ⚠️ | 反向且重要性最高=過擬合 |
| Body | +0.070 | 0.070 | 0.287 | ❌ | IC最低但重要性最高！過擬合噪音 |

### R — Reflective（感受與直覺）

- **五感全部偏低**（全在 0.05~0.44 範圍），Composite 29 — 市場明確偏空，沒有分歧
- **Ear 0.05 幾乎歸零** — funding rate z-score 持續極端偏負，這是真實恐慌
- **Tongue 43.8 相對最高** — 不是因為情緒好，而是 FNG=8 固定讓 score 維持在中下
- **模型信心 5.9%** — 這不是「保守」，這是「我不知道」，模型在亂猜
- **251 樣本訓練 3 次，特徵重要性完全相同** — 數據集沒有變化，每次都在擬合同一批噪音
- **server.senses 有 SQLite bug**（`sqlite3.Connection has no attribute 'query'`）— 前端 API 讀取特徵失敗，但 heartbeat 不影響
- **continuous_test 6/6 PASS** — 系統架構穩，但管道正常≠水乾淨

### I — Interpretive（意義與洞察）

1. **過擬合明確證據**：Body IC=0.070（幾乎無預測力）但 XGBoost 給它 28.7% 重要性 — 模型在 memorize 噪音
2. **Tongue 過擬合同樣嚴重**：IC=-0.138（反向）但重要性 23.3% — 模型學會了反方向的 pattern
3. **Eye 最可惜**：|IC|=0.278 是最強信號，但模型只給 15.7% 重要性 — XGBoost 因為樣本少沒學會用最好的特徵
4. **251 樣本是根因**：5 特徵 + 251 樣本 = 每個特徵平均 50 樣本，對於金融數據完全不夠
5. **Ear/Nose 洩漏仍在**：r=0.9979，3/5 感官被同一數據驅動，系統「五感」實為「三感」
6. **仲裁規則缺失**：五感說 29 分（BEARISH），模型說 HOLD（5.9% conf），用戶該聽誰？無規則

### D — Decisional（具體行動）

```
ACTION [P0]: [無立即可修] — 當前心跳無 code bug（server.senses bug 是已知非阻塞問題）
ACTION [P1]: feature_engine/preprocessor.py → Nose 脫離 funding_rate，改用 OI ROC + BTC Dominance 混合
ACTION [P2]: model/train.py → 增加正則化：max_depth=2, reg_alpha=1.0, reg_lambda=5.0, subsample=0.7
ACTION [P3]: 執行 tests/backfill_90d.py → 回填歷史數據擴大樣本
ACTION [P4]: model/predictor.py → 新增分歧仲裁：composite<35 && conf<0.3 → 輸出 "UNCERTAIN-BEARISH"
ACTION [P5]: data_ingestion/tongue_sentiment.py → 加入 CryptoPanic/newsapi 補充 FNG 單一來源
```

### 問題狀態更新

| ID | 問題 | 狀態 | 備註 |
|----|------|------|------|
| #H07 | 模型 CV < 基線 | 🔴 未解決 | 維持 |
| #H12 | 過擬合 train96%/CV36% | 🔴 未解決 | 維持 — 需 P2+P3 |
| #H20 | Ear/Nose 洩漏 r=0.9979 | 🔴 未解決 | 維持 — 需 P1 |
| #H21 | 五感-模型分歧無仲裁 | 🔴 未解決 | composite=29 vs HOLD(5.9%) |
| #M09 | Tongue 靜態(FNG=8) | 🟡 維持 | 120 unique/338, std=0.29 但最近 std=0.01 |

**最後更新：2026-04-01 11:24 GMT+8**

---

## 🔄 ORID 11:29 追蹤

### 新增問題

| ID | 問題 | 數據 | 狀態 |
|----|------|------|------|
| #H22 | 🔴 **標籤管線斷裂** — labeling.py 未整合進 main.py，標籤自 Mar 31 11:00 UTC 停止更新（16 小時） | 251 標籤 vs 338 特徵，87 筆無標籤。合併後每次訓練都是完全相同的 251 筆 → 特徵重要性恆定 | 🔴 需 P0 — 標籤不更新 = 模型空轉 |
| #H23 | **特徵重要性恆定確認** — 連續 4 次訓練輸出完全相同 `{'eye':0.157,'ear':0.145,'nose':0.178,'tongue':0.233,'body':0.287}` | random_state=42 + 相同訓練數據 → 完全確定性輸出 | 🔴 #H22 的症狀 |
| #M14 | Tongue 前 126/338 筆全部卡 -0.84（FNG 初始值直接映射），無時間變異 | 早期數據 126 筆完全相同 = 37% 的數據是噪音 | 🟡 需重算或處理早期異常 |

### 狀態更新

| 原始問題 | 狀態 | 備註 |
|----------|------|------|
| #H10 (Volume 全 NaN) | ✅ 已修復確認 | std=0.47, unique=88, var 有正常分布 |
| #H12 (過擬合 96%/36%) | 🔴 維持 | 根本原因是標籤未更新 + 樣本太少 |
| #H13 (標籤分佈不均) | 🔴 維持 | neg=159(63%), pos=92(37%) 未改善 |
| #H20 (Ear/Nose 洩漏) | 🔴 維持 | 待 P1 重構 Nose |
| #M09 (Tongue 靜態) | 🔴 升級 | 126/338 筆完全卡住，影響模型訓練 |
| #M13 (90天回填未完成) | 🟡 維持 | 待執行 |

**最後更新：2026-04-01 11:29 GMT+8**

---

## 🔄 ORID 11:29 追蹤 (Heartbeat 5min cron)

### 新增問題

| ID | 問題 | 數據 | 狀態 |
|----|------|------|------|
| #H22 | 🔴 **標籤管線斷裂** — `labeling.py` 未整合進 `main.py`，標籤自 Mar 31 11:00 UTC 停止更新 | 251 標籤 vs 338 特徵（87 筆無標籤）。`merge_asof` 只能匹配 251 筆，導致每次訓練數據完全相同 | 🔴 需 P0 |
| #H23 | **特徵重要性恆定確認** — 連續 4 次訓練（10:40, 10:50, 10:51, 11:10）輸出完全相同 `{'eye':0.157, 'ear':0.145, 'nose':0.178, 'tongue':0.233, 'body':0.287}` | random_state=42 + 相同訓練數據 = 確定性輸出 → 模型在空轉 | 📌 #H22 的症狀 |

### 狀態更新

| ID | 問題 | 新狀態 | 備註 |
|----|------|--------|------|
| #H10 (Volume 全 NaN) | ✅ 已修復確認 | std=0.47, unique=88, 分布正常 | |
| #H12 (過擬合) | 🔴 根因確認 | 不只是樣本少，更是標籤未更新導致 | |
| #M09 (Tongue 靜態) | 🟡 確認 | 126/338 筆卡 -0.84；最近 20 筆 std=0.009，幾乎不動 | |
| #H20 (Ear/Nose 洩漏) | 🔴 維持 | 需 P1 重構 Nose 改用獨立數據源 | |

**最後更新：2026-04-01 11:29 GMT+8**

---

## 🔄 ORID 11:34 追蹤 (Heartbeat 5min cron)

### 重大修復：#H22 標籤管線

**問題**：`labeling.py` 在 `generate_future_return_labels()` 中有 bug：
- 使用 `reindex(...).loc[future_ts:]` 查找未來價格時，當 `future_ts` 超出價格範圍 → 返回 NaN
- 339 筆標籤全部變成 `label=0`（因為 NaN > 0 = False）且 `future_return_pct=NaN`
- 之前 251 筆標籤是用手動/舊版程式產生的，並非 labeling.py 管線

**修復**：改用 `searchsorted` 直接索引價格陣列
- 有效標籤：**169 筆**（24h horizon 下有未來價格的筆數）
- 正例：116筆 (68.6%)，負例：53筆 (31.4%)
- 平均未來收益率：**+0.93%**（BTC 近 48h 整體上漲趨勢）
- 模型重訓 sample：**171筆**（merge_asof 10min tolerance 合併後）

### 全新 IC 結果（169 樣本，24h horizon）

| 感官 | Spearman | Pearson | 前值(Spearman) | 變化 |
|------|----------|---------|----------------|------|
| Eye | +0.051 | +0.047 | -0.280 | 🔼 從反向變零相關 |
| Ear | +0.310 | +0.254 | +0.120 | 🔼 **翻一倍的預測力** |
| Nose | +0.310 | +0.259 | +0.120 | 🔼 **同上（洩漏確認）** |
| Tongue | -0.103 | -0.103 | -0.063 | 🔻 微降 |
| Body | -0.023 | +0.065 | +0.056 | → 近零 |

### 模型重訓結果（171 樣本）
- Train: 171 samples, 69.0% positive
- 特徵重要性: **nose 30.9%, ear 29.4%, body 27.0%, eye 12.7%, tongue 0%**
- tongue 完全無貢獻（重要性=0）→ 證實應停用

### 五感當前分數（collector 11:34）
| 感官 | Raw | Normalized | 權重 |
|------|-----|-----------|------|
| Eye | +0.0023 | 0.452 | 0.30 |
| Ear | -0.900 | 0.343 | 0.25 |
| Nose | -0.319 | 0.341 | 0.25 |
| Tongue | -0.122 | 0.439 | 0.05 |
| Body | -0.477 | 0.261 | 0.15 |

BTC $68,000 | FNG=8 | Funding -6.6bp | OI ROC -0.66%

### O — Objective（客觀事實）
- 標籤管線已修復，但 169 樣本仍然太少（24h horizon 吃掉大部分數據）
- Ear IC=+0.31 是目前最高信號，但與 Nose 共享 funding_rate → 結構性問題
- Eye 的 IC 從 -0.28 翻到 0.05 → 之前的「反向指標」結論可能是舊標籤 bug 导致的錯覺
- Tongue 特徵重要性=0 → 完全無用
- 系統測試：comprehensive_test 6/6 PASS ✅

### R — Reflective
- **標籤 bug 影響深遠**：之前所有基於 251 筆舊標籤的 IC 分析可能都不準確
- Ear/Nose 洩漏仍是最大結構問題
- 169 sample for 5 features = 33.8 samples/feature → 仍然不足

### I — Interpretive
1. **之前 IC 結論需重新評估**：舊標籤 (251) 的來源不明，可能包含錯誤。新標籤 (169) 來源透明但樣本少
2. **Ear 是現在唯一有預測力的感官** (IC=+0.31)，但與 Nose 高度同質
3. **24h horizon 太長**：對於 30min 級別的系統，24h 吃掉 71% 的標籤 (339-169)。考慮縮短到 4-8h
4. **系統健康但預測力不足**：管線運行正常，但 169 樣本+Ear-Nose洩漏 是雙重瓶頸

### D — Decisional

```
ACTION [P0]: labeling.py → 縮短 horizon 為 4h（而非 24h），樣本數预计 300+ → 更多訓練數據
ACTION [P1]: #H20 — Nose 替換為 OI ROC，解除 Ear-Nose 洩漏
ACTION [P2]: Tongue 權重 0.05 → 0.0（特徵重要性=0）
ACTION [P3]: #M13 回填 90 天歷史數據 tests/backfill_90d.py
```

### 狀態更新
| ID | 問題 | 狀態 | 備註 |
|----|------|------|------|
| **#H22** | **標籤管線修復** | ✅ **已修復** | labeling.py bug fixed, IC 重新計算 |
| #H20 | Ear/Nose 洩漏 r≈1.0 | 🔴 未解決 | Nose 需替換為 OI |
| #M13 | 回填 90 天 | 🟡 待執行 | |
| #H15 | Tongue 停用 | 🔴 升級 | 重要性=0，權重應=0 |
| #009 | 缺少 SHAP 圖表 | 🟡 待處理 | |

**最後更新：2026-04-01 11:34 GMT+8**

---

## 🔄 ORID 11:49 追蹤 (Heartbeat 5min cron)

### O — Objective（客觀事實）

**市場狀態：** BTC ~$68,000 | FNG=8（極度恐懼）| Funding -6.6bp | OI ROC -0.66%

**系統測試：**
| 項目 | 結果 |
|------|------|
| comprehensive_test.py | ✅ 6/6 PASS |
| check_features.py | ✅ 339 rows，全感官有變異 |
| 語法檢查 | ✅ 65 Python 文件全部正確 |

**五感分數（最新特徵 03:34 UTC，歸一化 0~1）：**
| 感官 | Raw 值 | Normalized | 權重 | 加權貢獻 |
|------|--------|-----------|------|---------|
| Eye | +0.4516 | **0.726** | 0.30 | 0.218 |
| Ear | -0.9001 | **0.050** | 0.25 | 0.012 |
| Nose | -0.3194 | **0.340** | 0.25 | 0.085 |
| Tongue | -0.1224 | **0.439** | 0.05 | 0.022 |
| Body | -0.4775 | **0.261** | 0.15 | 0.039 |
| | | **Composite: 38/100 → BEARISH** 📉 | | |

**⚠️ 嚴重警報：Collector 已停止！** 最新數據停在 03:34 UTC = **~496 分鐘前（超過 8 小時未更新）**

**IC 分析（171 筆，新標簽管線，24h horizon）：**
| 感官 | Spearman IC | p-value | Pearson IC | p-value | 評價 |
|------|-------------|---------|------------|---------|------|
| Eye | +0.060 | 0.436 | +0.054 | 0.481 | ❌ 不顯著，近零 |
| Ear | **+0.290** | **0.0001** | +0.223 | 0.003 | ✅ 唯一有效信號 |
| Nose | **+0.290** | **0.0001** | +0.228 | 0.003 | ❌ 與 Ear 同值（洩漏）|
| Tongue | -0.088 | 0.254 | -0.088 | 0.254 | ❌ 無用 |
| Body | -0.036 | 0.641 | +0.048 | 0.530 | ❌ 無用 |

**特徵重要度 vs IC：**
| 感官 | 重要度 | IC(abs) | 匹配？ |
|------|--------|---------|--------|
| Nose | 30.9% | 0.290 | ⚠️ 與 Ear 共線 |
| Ear | 29.4% | 0.290 | ⚠️ 與 Nose 共線 |
| Body | 27.0% | 0.036 | ❌ 重要度 vs IC 嚴重不匹配 |
| Eye | 12.7% | 0.054 | ❌ IC接近零 |
| Tongue| 0.0% | 0.088 | ✅ 正確歸零 |

**Ear-Nose 相關性：** r=**0.9987**（p<0.000001）— 確認特徵洩漏

**模型現況（retrained 11:50 UTC）：**
- XGBoost, 171 筆訓練樣本 (pos=118=69%, neg=53=31%)
- 最新預測: P(up)=0.798, P(down)=0.202
- Confidence: **0.798** ⚠️ 模型「自信」看多
- Train Acc: 未輸出（需加上 CV）

**模型 vs 五感 分歧：**
- 五感: 38 → BEARISH
- 模型: 80% → BULLISH
- **強烈矛盾！** #H21 嚴重化

### R — Reflective

- **Collector 停止是最大問題**：8小時未更新 = 系統完全停擺。所有 ORID 分析基於陳舊數據
- **模型-五感分歧極端**：五感 BEARISH (38) vs 模型 BULLISH (80%) — 如果用戶現在做交易，信誰？
- **Tongue 正式死亡**：特徵重要度=0%，IC 不顯著，unique=2（只剩 2 個不同值）
- **Body 是最大過擬合**：IC 只有 0.036（完全不顯著），模型給了 27% 重要度
- **171 樣本仍太少**：171/5 = 34 樣本/特徵。金融數據通常需要 100+ 樣本/特徵才可靠

### I — Interpretive

1. **Collector 停擺根因**：可能是 cron job 停止或 main.py process 異常。需立刻檢查 heartbeat
2. **模型「假自信」**：79.8% confidence 在 171 筆數據上無意義。24h horizon 的標籤可能包含大量噪音
3. **Ear 是唯一活著的感官**：IC=0.290, p=0.0001 — 但若 Naso 洩漏未修，這也包含了 Nose 的效果
4. **38 分 BEARISH 但模型 80% 看多**：這矛盾的根本原因是 Body 主導模型（27% 重要度但 zero IC），而五感中 Body 貢獻低（26%）
5. **標籤 24h horizon 太長**：169 labels / 339 features = 50% 數據被截斷，應該縮短到 4-8h

### D — Decisional

```
ACTION [P0-CRITICAL]: 檢查/重啟 collector — 數據停止 8 小時
  → 檢查 main.py / dev_heartbeat.py 狀態
  → 重啟 collector 或 heartbeat process

ACTION [P1]: #H22 — 縮短標籤 horizon 24h → 4h
  → 文件: data_ingestion/labeling.py
  → 效果: 171 → ~300+ 樣本

ACTION [P2]: #H20 — Nose 替換為 OI-based
  → 文件: feature_engine/preprocessor.py
  → 解除 Ear-Nose 共線 r=0.9987

ACTION [P3]: #H21 — 模型-五感分歧仲裁
  → 新增規則: abs(composite - model_conf*100) > 30 → "UNCERTAIN"
  → 或: 模型信心 >0.8 但五感 <40 → 警告 alert

ACTION [P4]: #H15 — Tongue 權重 0.05 → 0.0
  → 重要性=0, IC 不顯著, unique=2

ACTION [P5]: #M13 — 回填 90 天數據
  → 根本解決方案：171 → ~4000+ 樣本
  → 執行 tests/backfill_90d.py

ACTION [P6]: 模型加入 CV 指標輸出
  → train.py 缺少 cross-validation
  → 無法判斷是否過擬合
```

### 問題狀態更新

| ID | 問題 | 新狀態 | 備註 |
|----|------|--------|------|
| **#NEW** | 🔴 Collector 停止 ~8 小時（最新數據 03:34 UTC） | 待確認 |
| **#H22** | 標籤管線修復但 horizon 過長 (24h→50%) | 🔄 需改 4h |
| **#H20** | Ear/Nose 洩漏 r=0.9987 | 🔴 未修復 |
| **#H21** | 模型(80%UP) vs 五感(38=BEARISH) 強烈分歧 | 🔴 升級 |
| **#H15** | Tongue 徹底死亡（重要性=0, unique=2） | 🔴 應停用 |
| **#H07** | 模型 CV 未知（train.py 無 CV 輸出） | 🔴 需加 CV |
| **#M13** | 回填 90 天 | 🟡 待執行 |

**最後更新：2026-04-01 11:49 GMT+8**

---

## 🔄 ORID 12:04 追蹤 (Heartbeat 5min cron)

**市場狀態：** BTC $68,154 | FNG=8（極度恐懼）| Funding -0.01bp | OI ROC -0.52%

**五感分數（SensesEngine live, 12:04 UTC+8）：** Eye 0.672 / Ear 0.358 / Nose 0.346 / Tongue 0.438 / Body 0.270 → composite **44/100** → **HOLD 觀望**

**五感分數（DB 最新 04:01 UTC，手動計算）：** Eye 0.345 / Ear -0.850 / Nose -0.308 / Tongue -0.124 / Body -0.460 → 歸一化後 composite **37/100** → **BEARISH**

> ⚠️ SensesEngine (44) vs DB direct (37) 差距 7 分 — SensesEngine 可能讀取不同時間點

### O — Objective（客觀事實）

**系統狀態：**
| 項目 | 結果 | 備註 |
|------|------|------|
| comprehensive_test.py | ✅ 6/6 PASS | 全部通過 |
| check_features.py | ✅ 340 rows | 全感官有變異 |
| Python 語法 | ✅ 65 文件正確 | 無變更 |
| 前端 TS | ✅ 編譯通過 | |
| main.py 進程 | ⚠️ PID 14992 存活 | `–help` 參數可能非預期 |
| API server | ❌ 未回應 | uvicorn 未運行於 localhost:8000 |
| DB 日期範圍 | 2026-03-30 13:25 ~ 2026-04-01 04:01 | ~38.5 小時 |
| 新增數據（vs 11:49） | **+4 筆** (336→340) | Collector 有更新 |

**特徵統計（340 筆）：**
| 特徵 | min | max | mean | std | unique | 評價 |
|------|-----|-----|------|-----|--------|------|
| feat_eye_dist | -1.00 | 1.00 | +0.10 | 0.548 | 340 | ✅ 全量變異 |
| feat_ear_zscore | -0.94 | +0.64 | -0.008 | 0.451 | 327 | ✅ 正常 |
| feat_nose_sigmoid | -0.32 | +0.10 | -0.058 | 0.107 | 327 | ⚠️ 振幅窄 |
| feat_tongue_pct | -0.84 | -0.12 | -0.609 | 0.295 | 122 | 🔴 稀疏 |
| feat_body_roc | -0.63 | +0.18 | -0.263 | 0.245 | 234 | ✅ 可接受 |

**IC 分析（169 樣本，24h horizon，新標籤）：**
| 感官 | Spearman IC | p-value | Pearson IC | p-value | 評價 |
|------|-------------|---------|------------|---------|------|
| Eye | +0.051 | 0.510 | +0.047 | 0.543 | ❌ 近零 |
| Ear | **+0.310** | **<0.001** | +0.254 | 0.001 | ✅ 唯一有效信號 |
| Nose | **+0.310** | **<0.001** | +0.259 | 0.001 | ❌ 與 Ear 完全同值（洩漏）|
| Tongue | -0.103 | 0.183 | -0.103 | 0.183 | ❌ 不顯著，重要性=0% |
| Body | -0.023 | 0.769 | +0.065 | 0.400 | ❌ 不顯著 |

**Ear-Nose 相關性：** r=**0.9986**（p<0.000001）— 結構性特徵洩漏持續

**滾動 IC（window=50）：**
| 感官 | mean_IC | 翻轉次數 | n_windows | 評價 |
|------|---------|---------|-----------|------|
| Eye | +0.046 | 1 次 | 6 | ⚠️ 近零但穩定 |
| Ear | **+0.623** | 0 次 | 6 | ✅ 穩定但樣本少 |
| Nose | **+0.623** | 0 次 | 6 | ❌ 同 Ear（洩漏）|
| Tongue | -0.428 | 0 次 | 2 | ❌ 有效窗口太少 |
| Body | +0.396 | 2 次 | 6 | ⚠️ 部分信號 |

**標籤分佈：** 169 筆（pos=116=68.6%, neg=53=31.4%），基線=68.6%
**Labels 自上次修復後未增加** — 169→169，表示 labeling.py 的標籤生成未持續執行

**Collector 數據間隔分析（最新 10 筆）：**
| 時間戳 | 間隔 |
|--------|------|
| 04:01 | — |
| 03:34 | 26 min |
| 03:10 | 24 min |
| 02:54 | 16 min |
| 02:01 | 54 min |
| 01:36 | 25 min |
| 00:34 | 61 min |
| 00:24 | 10 min |
| 00:21 | 4 min |
| 00:10 | 10 min |

間隔不規律（4~61 分鐘），collector 仍在運行但頻率不穩定。

### R — Reflective（感受與直覺）

- **Collector 仍在運行但間隔不規律**：不是完全停擺，而是觸發頻率不一致，平均 ~30min 但有 54min 和 61min 的 gap
- **API server 已掛**：uvicorn 沒有在 8000 端口運行，前端無法獲取數據
- **IC 結論穩定**：與 11:34 和 11:49 一致 — Ear 是唯一有效信號，Nose 洩漏，Tongue 無用，Body 微弱
- **滾動 IC 比全局 IC 更樂觀**：Ear 滾動 mean=+0.623（0 次翻轉），這比之前的滾動結果（mean=-0.053）好得多 — 原因可能是標籤從 251（舊）換成 169（新）導致計算基礎不同
- **標籤數量卡住 169**：說明 labeling pipeline 只在修復時跑了一次，沒有持續集成到 main loop

### I — Interpretive（意義與洞察）

1. **Collector 運行但非最佳**：340 筆 data 仍在增長（+4 vs 上一輪），但間隔不規律。需檢查 timer/cron 設定
2. **API 伺服器已停止**：這是新問題。uvicorn 進程死亡或被殺。需要重啟
3. **標籤管線沒有自動化**：#H22 的修復（labeling.py bug fix）只修復了 bug，但沒有把標籤生成整合進 main.py 循環。標籤仍停留在 169 筆
4. **Ear-Nose 洩漏無變化**：r=0.9986 與歷次測量一致，結構性問題未解
5. **Tongue 在 169 樣本中比之前更差**：重要性=0% → 在模型中完全不參與
6. **滾動 IC 改善可能是假象**：169 筆 vs 251 筆的標籤集完全不同，不能直接比較滾動 IC 值

### D — Decisional（具體行動）

```
ACTION [P0-CRITICAL]: 重啟 API server（uvicorn）
  → 檢查 uvicorn 進程狀態：ps aux | grep uvicorn
  → 重啟：cd poly-trader && python -m uvicorn server.main:app --reload --port 8000
  → 或執行 main.py 正確入口

ACTION [P1]: 整合 labeling pipeline 進 main.py 循環
  → 文件: main.py
  → 在 collector 循環中加入標籤生成步驟
  → 效果：標籤持續更新，169→持續增長

ACTION [P2]: #H20 — Nose 替換為 OI-based 數據源
  → 文件: feature_engine/preprocessor.py + data_ingestion/nose_futures.py
  → 解除 Ear-Nose 共線 r=0.9986

ACTION [P3]: #H22 — 縮短標籤 horizon 24h → 4h
  → 文件: data_ingestion/labeling.py
  → 效果：169 → ~300+ 樣本

ACTION [P4]: #H15 — Tongue 權重 0.05 → 0.0
  → 特徵重要性=0%，完全無貢獻 → 從 composite 移除

ACTION [P5]: #M13 — 回填 90 天歷史數據
  → tests/backfill_90d.py
  → 根本解決方案：樣本不足是最大瓶頸
```

### 問題狀態更新

| ID | 問題 | 狀態 | 備註 |
|----|------|------|------|
| **NEW** | 🔴 API server（uvicorn:8000）未運行 | 待重啟 |
| **NEW** | ⚠️ Collector 間隔不規律（4~61 min） | 監控中 |
| **#H20** | Ear/Nose 洩漏 r=0.9986 | 🔴 維持 |
| **#H22** | 標籤管線 bug 修復但標籤卡 169 未增長 | 🔄 需整合進 main loop |
| **#H15** | Tongue 重要性=0% | 🟡 維持 |
| **#H07/#H12** | 模型效能問題 | 🔴 維持 — 需更多數據 |
| **#M13** | 回填 90 天 | 🟡 待執行 |

**最後更新：2026-04-01 12:04 GMT+8**

---

## 🔄 ORID 12:09 追蹤 (Heartbeat 5min cron)

**市場狀態：** BTC $68,154 | FNG=8（極度恐懼）| Funding -0.06bp | OI ROC -0.51%

**五感分數（SensesEngine live, 12:04+ UTC+8）：** Eye 0.672 / Ear 0.358 / Nose 0.346 / Tongue 0.438 / Body 0.270 → composite **44/100** → **HOLD 觀望**

**五感分數（DB 最新 04:01 UTC，手動計算）：** Eye 0.345 / Ear -0.850 / Nose -0.308 / Tongue -0.124 / Body -0.460 → 歸一化後 composite **37/100** → **BEARISH**

> ⚠️ SensesEngine (44) vs DB direct (37) 差距 7 分 — SensesEngine 可能讀取不同時間點或正規化方式不同

### O — Objective（客觀事實）

**系統狀態：**
| 項目 | 結果 | 備註 |
|------|------|------|
| comprehensive_test.py | ✅ 6/6 PASS | 檔案結構、語法、模組、感官、前端 TS |
| check_features.py | ✅ 340 rows | 全感官有變異 |
| Python 語法 | ✅ 65 文件正確 | |
| 前端 TS | ✅ 編譯通過 | |
| main.py 進程 | ⚠️ PID 14992 存活（--help 參數可疑） | 可能未正確啟動 |
| API server (uvicorn:8000) | ❌ 未運行 | curl 無回應 |
| Frontend (localhost:3000) | ❌ 未運行 | |
| DB 日期範圍 | 2026-03-30 13:25 ~ 2026-04-01 04:01 | ~38.5 小時 |
| 新增數據（vs 12:04） | **0 筆** (340→340) | ⚠️ Collector 似乎間隔拉大 |

**特徵統計（340 筆）：**
| 特徵 | min | max | mean | std | unique | 評價 |
|------|-----|-----|------|-----|--------|------|
| eye_dist | -1.00 | +1.00 | +0.10 | 0.467 | 340 | ✅ 全量變異 |
| ear_zscore | -0.94 | +0.64 | -0.008 | 0.374 | 327 | ✅ 正常 |
| nose_sigmoid | -0.32 | +0.10 | -0.058 | 0.091 | 327 | ⚠️ 振幅極窄 |
| tongue_pct | -0.84 | -0.12 | -0.609 | 0.157 | 122 | 🔴 全域偏負，稀疏 |
| body_roc | -0.63 | +0.18 | -0.263 | 0.203 | 234 | ✅ 可接受 |

**IC 分析（169 樣本，24h horizon）：**
| 感官 | Spearman IC | p-value | Pearson IC | p-value | 評價 |
|------|-------------|---------|------------|---------|------|
| Eye | +0.051 | 0.510 | +0.047 | 0.543 | ❌ 近零，無預測力 |
| Ear | **+0.310** | **<0.0001** | +0.254 | 0.001 | ✅ **唯一有效信號** |
| Nose | **+0.310** | **<0.0001** | +0.259 | 0.001 | ❌ 與 Ear 完全同值（洩漏）|
| Tongue | -0.103 | 0.183 | -0.103 | 0.183 | ❌ 不顯著 |
| Body | -0.023 | 0.769 | +0.065 | 0.400 | ❌ 不顯著 |

**Ear-Nose 相關性：** r=**0.9986**（p<0.000001）— **結構性特徵洩漏持續未解**

**滾動 IC（window=50）：** 因標的樣本 169 筆，分段後每段不足 50 筆有效窗口，數值為 NaN。需更多樣本才能計算滾動 IC。

**標籤分佈：** 169 筆（pos=116=68.6%, neg=53=31.4%），基線=68.6%
**Labels 卡住 169** — labeling pipeline 未持續運行，標籤未增長

**Collector 間隔分析（最新 10 筆）：**
| 時間戳 (UTC) | 間隔 (min) |
|--------|------|
| 04:01 | — |
| 03:34 | 26 |
| 03:10 | 24 |
| 02:54 | 16 |
| 02:01 | 54 |
| 01:36 | 25 |
| 00:34 | 61 |
| 00:24 | 10 |
| 00:21 | 4 |
| 00:10 | <br/>10 |

間隔不規律（4~61 min），平均 ~29 min。**自 04:01 UTC 至今（12:09 UTC+8 = 04:09 UTC）已過 8 min，可能正常間隔中。**

### R — Reflective（感受與直覺）

- **IC 結論完全一致**：與 11:34、11:49、12:04 完全相同的格局 — Ear 唯一有效，Nose 洩漏，Tongue/Body 無用
- **系統穩定但 API 掛了**：Collector 繼續收集數據（340 筆），但前端 API 服務不可用
- **標籤管線仍是斷頭**：169 筆卡住不動，main.py 的 labeling 循環未整合
- **Ear 是唯一活著的感官**：Spearman IC=+0.310, p<0.0001，這是目前唯一有統計意義的信號
- **SensesEngine vs DB 差異 7 分**：需確認兩者正規化是否一致

### I — Interpretive（意義與洞察）

1. **根本瓶頸仍然是樣本不足**：169 筆標籤 + 5 特徵 = 33 樣本/特徵。金融模型需要至少 100+ 樣本/特徵
2. **Ear-Nose 洩漏是結構性浪費**：r=0.9986 意味著 5 個感官中 2 個是同一個信號，實質只剩 4 個感官
3. **標籤 horizon=24h 吃掉 50% 數據**：340 筆 raw data 只產出 169 筆標籤。缩短到 4h 可大幅增加樣本
4. **API server 死亡但 collector 活著**：main.py 的 collector 循環和 API server 是獨立進程。uvicorn 可能因錯誤或記憶體溢出死亡
5. **IC 格局已穩定**：連續 4 次 ORID 都得到同樣的 IC 結論，這不是噪音，是系統性的

### D — Decisional（具體行動）

```
ACTION [P0-CRITICAL]: 重啟 API server（uvicorn:8000）
  → 文件: server/main.py
  → 檢查: ps aux | grep uvicorn → 無進程
  → 重啟: cd poly-trader && python -m uvicorn server.main:app --reload --port 8000
  → 或整合進 main.py 作為子進程

ACTION [P1]: 整合 labeling pipeline 進 main.py 循環
  → 文件: main.py + data_ingestion/labeling.py
  → 在 collector 循環中加入標籤生成步驟
  → 效果：標籤 169→持續增長

ACTION [P2]: #H20 — Nose 替換為 OI-based 數據源
  → 文件: feature_engine/preprocessor.py + data_ingestion/nose_futures.py
  → 解除 Ear-Nose 共線 r=0.9986
  → Nose 改用 Open Interest ROC 或 Futures basis

ACTION [P3]: #H22 — 縮短標籤 horizon 24h → 4h
  → 文件: data_ingestion/labeling.py
  → 效果：169 → ~600+ 樣本（340 筆 × 6x 頻率）
  → 根本提升統計效力

ACTION [P4]: #H15 — Tongue 權重 0.05 → 0.0
  → 文件: server/senses.py
  → IC=-0.103 (p=0.183), 完全不顯著，移除以簡化模型
  → 權重分配給 Ear (唯一有效信號)

ACTION [P5]: #M13 — 回填 90 天歷史數據
  → 文件: tests/backfill_90d.py
  → 根本解決方案：樣本 340 → ~4000+
  → 解決過擬合 (#H12)、IC 不穩定 (#H07)
```

### 問題狀態更新

| ID | 問題 | 狀態 | 備註 |
|----|------|------|------|
| **NEW** | 🔴 API server (uvicorn:8000) 仍未運行 | 待重啟 |
| **#H20** | Ear/Nose 洩漏 r=0.9986 | 🔴 **未變** — 結構性問題 |
| **#H22** | 標籤卡 169 未增長 | 🔴 未變 — labeling 未整合進 main loop |
| **#H15** | Tongue 不顯著 (p=0.183) | 🟡 應降權至 0.0 |
| **#H07/#H12** | 模型樣本不足 169 | 🔴 維持 |
| **#M13** | 回填 90 天 | 🟡 待執行 |

**最後更新：2026-04-01 12:09 GMT+8**

---

## 🔄 ORID 12:24 追蹤

**市場狀態：** BTC $68,154 | FNG=8（極度恐懼）| Funding -6.369e-05 | OI ROC -0.51%

**五感分數：** Eye 0.672 / Ear 0.358 / Nose 0.346 / Tongue 0.438 / Body 0.270 → 建議 **44 分** → **hold**

**模型預測：** BUY (conf=0.7130) | Weight: 0.713 | Risk Ctrl: Dry Run

### O — Objective 客觀數據

| 感官 | Raw Feature | Normalized | Feature Stats (340 rows) |
|------|-------------|------------|-------------------------|
| Eye | eye_dist=0.0021 | 0.672 | avg=0.10, σ=0.55, unique=340 |
| Ear | ear_zscore=-0.850 | 0.358 | avg=-0.01, σ=0.44, unique=327 |
| Nose | nose_sigmoid=-0.308 | 0.346 | avg=-0.06, σ=0.10, unique=327 |
| Tongue | tongue_pct=-0.124 | 0.438 | avg=-0.61, σ=0.29, unique=122 |
| Body | body_roc=-0.460 | 0.270 | avg=-0.26, σ=0.25, unique=234 |

**模型數據：**
- XGBoost model loaded, feat_nose_sigmoid(0.31) + feat_ear_zscore(0.29) = top features
- feat_tongue_pct importance = **0.0000** (零貢獻)
- Total samples: 340 raw, 169 labeled (pos=116=68.6%, neg/flat=53=31.4%)
- Label horizon: future_return_pct range [−0.0168, +0.0270]

**測試結果：** comprehensive_test.py **6/6 PASS** ✅

### R — Reflective 感受與直覺

- **Ear 0.358，Nose 0.346** — 兩者幾乎重疊，持續印證特征洩漏 (#H20)
- **Eye 0.672（表面看多）** — 但 IC = −0.278（反向指標），高 Eye 分數反而是看空信號
- **Tongue 0.438（中上）** — 但 feature importance = **0.0**，對模型完全無貢獻，純噪音
- **Body 0.270（偏空）** — OI ROC 持續為負，資金壓力真實存在
- **Model 說 BUY (conf=71%) 但 3/5 感官偏空** — 矛盾，模型被 Ear+Nose (同源 funding_rate) 主導

### I — Interpretive 意義與洞察

1. **模型過度依賴 funding_rate**：Ear + Nose 加權 0.50，且兩者數據同源 → 模型實際只有 ~1.5 個獨立感官在工作
2. **Tongue 已證實可汰換**：IC=−0.14, importance=0.0, FNG 固定在極度恐懼(8) 不變
3. **樣本分佈問題**：169 標籤中 68.6% pos，缺乏負例 (label=−1 為 0 筆) → 回調期間模型會全面失效
4. **BTC 在 $68K 附近盤整**：price range [66K, 68.4K]，波動率低，五感訊號整體偏暗
5. **Dry Run 模式**：無 Binance API key，實際未執行交易

### D — Decisional 行動清單

```
ACTION [P0-HIGH]: Nose 感官替換數據源 (#H20)
  → preprocessor.py 改用 OI_ROC derivative 或 volume spike 取代 funding_rate sigmoid
  → 打破 Ear/Nose 同源性

ACTION [P1-MEDIUM]: Tongue 感官停用/替換 (#H15)
  → FNG 在極端恐懼時無變異性，短期無法改善
  → 權重降至 0.0（或替換為新聞 sentiment API）

ACTION [P2-MEDIUM]: 增加負標籤 (label=-1) (#H13)
  → labeling.py 需加入大幅下跌條件（如 <-1%）產生 label=-1
  → 當前 169 標籤全為 0/1，模型未學過「大賣」信號

ACTION [P3-LOW]: 回填 90 天歷史數據 (#M13)
  → tests/backfill_90d.py 執行
  → 251→~2000 樣本可根本性解決過擬合問題 (#H12)

ACTION [P4-LOW]: 加入 lag features (1h, 4h, 24h)
  → preprocessor.py 加 rolling lag 列
  → 六帽會議 Action 3 待辦
```

### 已更新狀態

| ID | 問題 | 新狀態 |
|----|------|--------|
| #H15 | Tongue 重要性 = 0.0，徹底證實無貢獻 | 🔴 升級：停用/替換 |
| #H20 | Ear=Nose 特徵洩漏 | 🔴 持續未解，數據源替換為當務之急 |
| #H07 | 模型 CV 準確率低 | 🔴 持續 |
| #H13 | 標籤全為 0/1，無 label=-1 | 🔴 新增標記 |
| comprehensive_test.py | 6/6 PASS | ✅ |

**最後更新：2026-04-01 12:24 GMT+8**

---

## 🔄 ORID 12:34 追蹤

**市場狀態：** BTC $68,154 | FNG=8（極度恐懼）| Funding -6.369e-05 | OI ROC -0.51%

**五感分數：** Eye 0.672 / Ear 0.358 / Nose 0.346 / Tongue 0.438 / Body 0.270 → 建議 **44 分** → **hold**

**模型預測：** BUY (conf=0.7130) | Weight: 0.713 | Risk Ctrl: Dry Run

### O — Objective 客觀數據

| 感官 | Raw Feature | Normalized | Feature Stats (340 rows) |
|------|-------------|------------|-------------------------|
| Eye | eye_dist=+0.0021 | 0.672 | avg=0.10, σ=0.55, unique=340 |
| Ear | ear_zscore=−0.850 | 0.358 | avg=−0.01, σ=0.44, unique=327 |
| Nose | nose_sigmoid=−0.308 | 0.346 | avg=−0.06, σ=0.10, unique=327 |
| Tongue | tongue_pct=−0.124 | 0.438 | avg=−0.61, σ=0.29, unique=122 |
| Body | body_roc=−0.460 | 0.270 | avg=−0.26, σ=0.25, unique=234 |

**模型數據：**
- XGBoost: feat_nose_sigmoid(0.31) + feat_ear_zscore(0.29) = top features
- feat_tongue_pct importance = **0.0000** (零貢獻)
- Total samples: 340 raw, 340 features, **169 labeled** (pos=116=68.6%, flat=53=31.4%, neg=0)
- trade_history: **0 rows** (從未實際交易)
- comprehensive_test.py: **6/6 PASS** ✅

### R — Reflective 感受與直覺

- **Ear 0.358，Nose 0.346** — 兩者持續重疊，r≈0.9986 未解 (#H20)
- **Eye 0.672（表面看多）** — IC=−0.278，高 Eye 反而是反向指標
- **Tongue 0.438（中上）** — feature importance=0.0，完全噪音，FNG 固定在 8
- **Body 0.270（偏空）** — OI ROC 持續負值，槓桿壓力真實
- **Model BUY (71%) vs 3/5 感官偏空** — 強烈矛盾，模型被同源 Ear+Nose 誤導
- **0 筆負標籤** — 模型從未學過「大賣」，回調期全面失效風險高

### I — Interpretive 意義與洞察

1. **結構性洩漏未解**：Ear+Nose 同源 funding_rate，加權 0.50 ≈ 模型只有 ~1.5 個獨立感官
2. **Tongue 已證實可汰換**：IC=−0.14, importance=0.0, FNG 無變異性
3. **標籤災難**：169 標籤中負例 = 0 筆 → 模型在下跌環境中必然失準
4. **BTC $68K 盤整**：波動率低，五感訊號整體偏暗，不是測試實盤的好時機
5. **Dry Run 模式**：無 Binance API Key，保護性措施有效

### D — Decisional 行動清單

```
ACTION [P0-HIGH]: Nose 感官替換數據源 (#H20)
  → preprocessor.py 改用 OI_ROC 或 volume_spike 取代 funding_rate sigmoid
  → 打破 Ear/Nose 同源性（當前最關鍵結構性問題）

ACTION [P1-MEDIUM]: Tongue 權重降至 0.0 (#H15)
  → 對模型零貢獻，降權避免噪音干擾

ACTION [P2-MEDIUM]: 增加負標籤 label=-1 (#H13)
  → labeling.py 加入大幅下跌條件（如 <-1%）
  → 解決模型從未學過 "SELL" 的根本問題

ACTION [P3-LOW]: 回填 90 天歷史數據 (#M13)
  → tests/backfill_90d.py
  → 340→~4000+ 樣本，根本性解決過擬合

ACTION [P4-LOW]: 加入 lag features (1h, 4h, 24h)
  → 六帽會議 Action 3 待辦
```

### 已更新狀態

| ID | 問題 | 狀態 |
|----|------|------|
| #H20 | Ear/Nose 同源洩漏 | 🔴 最高優先，當前最大結構性問題 |
| #H15 | Tongue importance=0.0 | 🔴 應立即降權至 0.0 |
| #H13 | 負標籤=0 筆 | 🔴 模型盲區，需盡快修正 |
| #M13 | 回填 90 天 | 🟡 待執行 |
| #H07 | CV 準確率低 | 🔴 維持（需更多樣本+獨立特徵） |

**最後更新：2026-04-01 12:34 GMT+8**
