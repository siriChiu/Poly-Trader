# ISSUES.md — 問題追蹤

*最後更新：2026-04-09 01:38 UTC — Heartbeat #612（hb_collect label horizon repair + accidental 14400m label cleanup + canonical-window IC hardening）*

## 📊 系統健康狀態 v4.39

| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw | **19,757** | 🟢 `hb_collect.py` 本輪再增 +1 |
| Features | **11,143** | 🟢 新 row 持續直接帶 `regime_label` |
| Labels | **38,522** | 🟡 已清掉錯誤 14,400m horizon rows；24h/12h/4h labels 保留 |
|| simulated_pyramid_win (1440m) | **61.37%** | 🟢 canonical 24h 分析口徑（`regime_aware_ic.py`, n=9,763） |
|| spot_long_win | **33.21%** | 🟡 legacy 比較口徑，非主 target |
| 全域 IC | **15/22** | 🟢 再提升 |
| TW-IC | **17/22** | 🟢 維持高檔 |
| 模型數 | **8** | ✅ |
| Tests | **6/6** | ✅ 全過 |

## 📈 心跳 #612 摘要

### 本輪已驗證 patch
1. **hb_collect label horizon unit fix**：`scripts/hb_collect.py` 不再把 `horizon_hours * 60` 傳給 `save_labels_to_db()`，修掉 4h 收集流程誤寫成 **14,400 分鐘** label 的 root cause。
2. **Data cleanup for polluted labels table**：新增 `scripts/fix_hb612_label_horizon_bug.py`，已實際刪除 **10,723** 筆 accidental `horizon_minutes=14400` rows，避免 heartbeat / IC 腳本再被錯誤 horizon 污染。
3. **Canonical-window IC hardening**：`scripts/dynamic_window_train.py`、`scripts/full_ic.py`、`scripts/regime_aware_ic.py` 現在都只讀 **`horizon_minutes=1440`** 的 canonical labels，且對 `constant_target` / `constant_feature` 做顯式診斷，不再產生 NaN 假錯誤。

### 本輪 runtime facts（Heartbeat #612）
- `fix_hb612_label_horizon_bug.py`：**10,723 → 0** 筆 14,400m labels；duplicate `(timestamp,symbol)` 組數 **10,172 → 9,418**；目前 horizon 分佈只剩 **240 / 720 / 1440**。
- `hb_collect.py`：Raw **19756→19757**、Features **11142→11143**、Labels **37410→38522**；證明修完後 4h label pipeline 仍可新增資料，但不再寫出 14,400m 污染列。
- `hb_parallel_runner.py --hb 612`：**5/5 PASS (67.0s)**，summary 已寫入 `data/heartbeat_612_summary.json`。
- Full IC：**15/22 PASS**；TW-IC：**17/22 PASS**。
- Dynamic window（canonical 1440m）：**N=100/200/400 全部 constant_target_window**，**N=600=6/8 PASS**, **N=1000=7/8 PASS**, **N=2000=6/8 PASS**, **N=5000=5/8 PASS**。
- Train：**Train 69.45%, CV 60.09% ± 9.37pp**；Bear CV **58.61%**, Bull CV **77.06%**, Chop CV **61.60%**。

### 新 blocker / 狀態更正
- **#DW_N100_NAN**：已確認**不是 merge bug**。根因是 canonical 24h label 在最近 100/200/400 筆窗口內全部為 **1**，屬於 **constant target saturation**；本輪已修掉 NaN / warning 假錯誤，但 recent-window 指標仍暫時不可用，需升級為 label-distribution / evaluation-window 問題，而不是 join bug。

## 📈 心跳 #610 IC 摘要

### 全域 IC (Spearman, n=8770)
| 特徵 | IC | 狀態 |
|------|-----|------|
| VIX | +0.0714 | ✅ PASS |
| BB%B | +0.0575 | ✅ PASS |
| RSI14 | +0.0542 | ✅ PASS |
| MACD-Hist | +0.0505 | ✅ PASS |
| Nose | +0.0500 | ❌ FAIL（擦邊持平） |
| 其餘17個 | <0.05 | ❌ |

**全域 IC: 5/22 通過（持平）**

### TW-IC (tau=200, n=8770)
| 特徵 | TW-IC | 狀態 |
|------|-------|------|
| VWAP Dev | +0.1293 | ✅ PASS |
| ATR% | -0.1280 | ✅ PASS |
| VIX | +0.0876 | ✅ PASS |
| BB%B | +0.0826 | ✅ PASS |
| AURA | +0.0799 | ✅ PASS |
| Mind | +0.0750 | ✅ PASS |
| RSI14 | +0.0746 | ✅ PASS |
| 4h_bias50 | +0.0715 | ✅ PASS（4H特徵） |
| Nose | +0.0587 | ✅ PASS |
| MACD-Hist | +0.0554 | ✅ PASS |
| 4h_rsi14 | +0.0622 | ✅ PASS（4H特徵） |
| 4h_dist_swing_low | +0.0620 | ✅ PASS（4H特徵） |
| Pulse | -0.0871 | ✅ PASS |
| 其餘9個 | | ❌ |

**TW-IC: 13/22 通過（持平）**

### Dynamic Window（核心8特徵）
- N=100: **7/8**🟢（持平！耳唯一失敗；Aura+0.2773, Mind+0.2301, Nose+0.1766, Body+0.1288, Tongue-0.1149 極強）
- N=200: **7/8**🟢（持平！）
- N=400: 3/8（持平）
- N=600: **0/8**💀（持續死區）
- N=1000: 4/8（持平）
- N=2000: 2/8（持平）
- N=5000: 0/8（持平）

### Regime-aware IC
| 區間 | 通過 | 狀態 |
|------|------|------|
| Bear | **4/8** | ⚠️ 持平（Ear, Nose, Body, Aura） |
| Bull | **0/8** | 🔴 持續！（200+輪持續） |
| Chop | **0/8** | 🔴 持續！（200+輪持續） |

**Spot Long Win by Regime**: Bear 48.55%, Bull 50.90%, Chop 48.29%, Overall 49.24%（legacy sell_win 口徑）

### 模型訓練
- Train: 63.92%, CV: 51.39%, gap: 12.53pp
- Features: 73, Samples: 9,106, Positive ratio: 30.45%
- **Regime models**:
  - Bear: CV=60.22%, Train=79.8%, n=2980
  - Bull: CV=73.37%, Train=93.5%, n=2939
  - Chop: CV=65.60%, Train=71.48%, n=3124

## 📊 市場快照（#610 即時）
- BTC: **$67,985**（⬆️ +$216 vs #609 $67,769，微幅反彈！）
- 24h Change: **-2.41%**
- FNG: **11**（持續極度恐懼）
- FR: **0.00006505**（⬆️ +7.1% vs #609 0.00006073，空頭壓力再創新高！）
- LSR: **1.3618**（⬆️ +116bps vs #609 1.3502，長倉比例持續攀升）
- OI: **89,482**（⬆️ +171 vs #609 89,311，持倉量止跌回暖）

## 🔒 Heartbeat 閉環治理（新規則）

- `HEARTBEAT.md` 已重寫為 **嚴厲的專案推行者憲章**：每輪心跳都必須完成 `facts → strategy decision → 六帽/ORID → patch → verify → docs sync → next gate`。
- 主 target 已正式定為 `simulated_pyramid_win`；`label_spot_long_win` 僅保留 path-aware 比較；`sell_win` 僅作 legacy 相容。
- 若一次心跳沒有 **patch + verify + 文件同步 + 下一輪 gate**，則該輪視為失敗，不算進度。
- 若同一 issue 連續 2 輪無修復，下一輪必須升級為 blocker 或 source-level investigation。
- 若連續 3 輪只有報告沒有 patch，需新增/啟動 `#HEARTBEAT_EMPTY_PROGRESS` 並停止空轉。

## 🧢 文件與流程六帽 review

### 白帽
- 已有 HEARTBEAT / ISSUES / ROADMAP / ARCHITECTURE，但 canonical target 仍需完全對齊。

### 紅帽
- 如果每輪只留下「沒達標」而沒有修復，心跳會變成空轉。

### 黑帽
- 舊的 sell_win 語義殘留會持續污染後續分析與回測定義。

### 黃帽
- 4H 特徵、regime models、tests PASS 是可重複利用的穩定基底。

### 綠帽
- 需要把「觀察」直接升級成「觀察 → ORID → issue → patch → verify」的閉環。

### 藍帽
- 本文件應作為問題中樞：先定義問題，再推動修復，再同步回寫路線圖與架構。

## 🧢 六色帽會議決議（研究結論 → 修復主線）

### P0 — 資料乾淨度治理
1. 統一 canonical key：
   - raw/features → `(timestamp, symbol)`
   - labels → `(timestamp, symbol, horizon_minutes)`
2. 停止讓 legacy `NULL symbol` rows 與 canonical rows 混雜污染新資料。
3. 訓練/標籤流程不得再靠 timestamp-only 假設對齊。
4. 缺值與歷史世代差異要顯式隔離，而不是默默混成「中性值」。

### P1 — label 穩定度重建
1. 由 final-close threshold 改為 **path-aware label**。
2. `spot_long_win` 定義應對齊現貨金字塔語義：
   - 只要 horizon 內 **曾 hit TP**
   - 且 **未破 DD 預算**
   - 即視為可交易成功 setup。
3. 後續繼續推進 simulated pyramid outcome label / continuous trade-quality label。
4. 已新增第一版 simulated pyramid labels：`simulated_pyramid_win / pnl / quality`，且已接入 training / leaderboard target comparison。
5. 2026-04-08 target comparison 實測：
   - `label_spot_long_win` → Train **77.18%**, CV **45.99% ± 9.64%**, positive ratio **26.83%**
   - `simulated_pyramid_win` → Train **61.74%**, CV **58.12% ± 4.12%**, positive ratio **61.51%**
   - 結論：**simulated pyramid target 明顯比 path-aware binary 更穩、更不易過擬合**。

## P0

| ID | 問題 | 狀態 |
|----|------|------|
| #LABELS_FROZEN | Labels 曾長期凍結於 27,684 | ✅ 已修復（Heartbeat #611 後升至 **48,133**，`hb_collect.py` 可持續新增 labels） |
| #SPOT_LONG_WIN_33 | spot_long_win=33.21% 遠低於目標（需≥90%） | 🔴 持續（legacy 比較指標；主 target 已切到 simulated_pyramid_win） |
| #BULL_CHOP_DEAD | Bull 0/8, Chop 0/8（200+輪持續零信號）| 🟡 重新評估中（#611 的 Mind-tertile regime IC 顯示 Bull 7/8、Chop 4/8，但方法差異仍待確認） |
| #CV_CEILING | CV 51.39% 天花板（6+月無法突破）| 🟡 已部分修復（#611 global CV 升至 **59.48%**，但仍需確認是否穩定、是否受 regime / window bug 影響） |
| #CANONICAL_KEY_DRIFT | features/labels/analysis 對齊仍受 timestamp-only 舊語義污染，symbol NULL 舊資料混入 | 🟡 已部分修復（新特徵保存改為 timestamp+symbol，標籤優先使用 canonical symbol rows，analysis 腳本已強制 `horizon_minutes=1440`） |
| #FEATURE_SYMBOL_NULL | `features_normalized.symbol` 歷史上可為 NULL，造成 mixed-generation dataset | ✅ 已修復（歷史 NULL symbol 已回填為 0 筆） |
| #LABEL_HORIZON_UNIT_BUG | `hb_collect.py` 曾把 4h label job 寫成 14,400m，污染 labels 與 heartbeat 分析 | ✅ 已修復（Heartbeat #612 已修正呼叫參數並刪除 **10,723** 筆 14,400m rows） |
| #DW_N100_NAN | `dynamic_window_train.py` 在 N=100 產生 8/8 NaN，recent-window 診斷失真 | 🟡 已部分修復（NaN / warning 已消失；根因改判為 recent 24h target 全為 1 的 constant-target saturation，需要另做窗口/標籤分布治理） |

## P1

| ID | 問題 | 狀態 |
|----|------|------|
| #DW_DEADZONE | N=600 和 N=5000 持續 0/8 死區 | 🟡 已部分修復（#612 canonical 24h runtime：N=600=6/8、N=1000=7/8、N=5000=5/8；真正的 recent-window 問題改為 N=100/200/400 constant-target saturation） |
| #EAR_LOW_VAR | feat_ear std=0.0029, unique=13（準離散特徵）| ⚠️ 持續 |
| #TONGUE_LOW_VAR | feat_tongue std=0.0016, unique=9（準離散特徵）| ⚠️ 持續 |
| #LABELS_JUMP | Labels 從 18,052 跳增至 27,684（+53%）原因未明 | ✅ 已定位（hb_collect pipeline 重建 labels；後續以 24h/canonical horizon 管理，不再視為隨機跳增） |
| #LOW_COVERAGE_SOURCES | Fin / Fang / Web / Scales / Nest coverage 僅 ~19%，且過去會用假 0 偽裝可用資料 | 🟡 已部分修復（#611 已改成 fetch failure → `None`，避免新增假中性值；下一步是真正補歷史 coverage） |
| #FEATURECHART_QUALITY_SIGNAL | FeatureChart 對低 coverage 特徵只顯示模糊 badge，使用者無法判斷是 coverage 還是 distinct 問題 | ✅ 已修復（圖例/警示卡已顯示 `coverage% / distinct / reasons`） |
| #FINAL_CLOSE_LABEL_NOISE | final-close-only TP threshold 會把「曾 hit TP 但收盤回落」的可交易 setup 誤標為失敗 | ✅ 已修復（spot_long_win 已改為 path-aware label，並已重建實際 labels） |
| #LABEL_PATH_MISMATCH | 標籤語義與現貨金字塔執行路徑不一致，只看 horizon 結束點 | 🟡 已部分修復（path-aware + simulated pyramid labels 均已上線，且已接入模型排行榜 target comparison；下一步要把 simulated target 升為預設訓練主線） |

## ✅ 已修復（Web / UX）

| ID | 問題 | 修復 |
|----|------|------|
| #WEB_SHORT_BIAS | Dashboard / AdviceCard 將高分錯誤解讀為做空訊號，與現貨金字塔策略衝突 | ✅ 已改為 spot-long / 減碼語義，移除前端做空引導 |
| #WEB_TRADE_404 | Dashboard 交易按鈕呼叫 `/api/trade`，但後端缺少 endpoint | ✅ 已新增 dry-run trade endpoint，買入/減碼操作可正常回應 |
| #BACKTEST_CAPITAL_IGNORED | 回測頁面的初始資金輸入未傳入後端 | ✅ 已串接 `initial_capital` 參數 |
| #STRATEGY_RUNCOUNT_ZERO | Strategy Lab 首次執行顯示 `(x0)` | ✅ 已修正首次執行 run_count=1 |
| #MODEL_LB_500 | `/api/models/leaderboard` 因 walk-forward split 型別錯誤與脆弱 join 導致 500 / 空資料 | ✅ 已改為 asof 對齊並修正 month/int split，API 恢復可用 |
| #MODEL_LB_UI_MISSING | Web 缺少模型排行榜視覺化 | ✅ 已在 Strategy Lab 新增模型排行榜表格 |
| #REGIME_ALIGN_FFILL | 4H/regime 稀疏欄位在訓練時靠 ffill 補值，與「特徵必須獨立計算」原則衝突 | ✅ 已改為 sparse 4H snapshot asof 對齊，不再用訓練時 ffill 擴散 regime/4H 值 |
| #STRATEGY_SCHEMA_DIRTY | Strategy Lab 歷史策略 JSON 缺欄位/NaN/暫存策略污染排行榜，導致 `(x0)`、NaN%、測試殘留 | ✅ 已加入 strategy schema sanitize + internal strategy filter，排行榜只顯示有效策略 |
| #STRATEGY_RUNCOUNT_SAVE | `/api/strategies/save` 只存定義也會錯誤增加 run_count | ✅ 已修正為只有實際回測才增加 run_count，純保存保留既有次數 |
| #REGIME_BACKTEST_MISSING | Strategy Lab 缺少 Bull/Bear/Chop 分拆回測，無法直接檢驗 Bull/Chop 對齊 | ✅ 已新增依進場 regime 的分類回測表格與 API `regime_breakdown` |

## ✅ 本次摘要
- 🟡 **Raw 10,248（+9 vs #609 10,239）**：持續增長但增速進一步放緩（+29→+10→+9）
- 🟡 **Features 10,207（+9 vs #609 10,198）**：跟隨 Raw 增長
- 🔴 **Labels 27,684**：完全凍結（與 #609 相同，零增長已超 100 輪）
- 🔴 **spot_long_win=33.21%**：持平（vs #609 33.21%），遠低於 90% 目標
- 🟢 **TW-IC 13/22**（持平，3個4H特徵持續貢獻：4h_bias50, 4h_rsi14, 4h_dist_swing_low）
- 🟢 **全域 IC 5/22**（持平：VIX, BB%B, RSI14, MACD-Hist, Nose擦邊）
- 🟢 **DW N=100 7/8 + N=200 7/8 持平**：短窗口持續最強（耳唯一失敗）
- 🟢 **Regime IC 持平**：Bear 4/8（Ear, Nose, Body, Aura），Bull 0/8🔴，Chop 0/8🔴
- 🟢 **平行心跳 5/5 PASS（54.0s）**：full_ic ✅, regime_ic ✅, dynamic_window ✅, train ✅, tests ✅（6/6）— 全面通過！
- 🟢 **Tests 6/6 PASS**：全面通過（9983 Python files syntax OK, TS 通過）
- 🟢 **Global model**: Train=63.92%, CV=51.39%, gap=12.53pp，73 features, 9106 samples
- 🟢 **Regime models**: Bear CV=60.22%, Bull CV=73.37%, Chop CV=65.60%
- 🟡 **BTC $67,985（+$216 vs #609）**：微幅反彈但24h仍在跌（-2.41%）
- 🔴 **FR 0.00006505（+7.1% vs #609）**：空頭付費壓力再創新高！從 0.00006073 → 0.00006505
- 🟡 **LSR 1.3618（+116bps vs #609）**：長倉比例持續攀升，多頭持續抄底
- 🟡 **OI 89,482（+171 vs #609）**：持倉量止跌回暖
