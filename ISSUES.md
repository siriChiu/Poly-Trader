# ISSUES.md — 問題追蹤

*最後更新：2026-04-08 18:35 UTC — Heartbeat #616（source-history blocker surfacing + FeatureChart quality rationale）*

## 📊 系統健康狀態 v4.42

| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw | **19,778** | 🟢 `hb_collect.py` 本輪再增 +1 |
| Features | **11,164** | 🟢 新 row 持續直接帶 `regime_label` |
| Labels | **38,530** | 🟡 canonical horizons 持續增長（240/720/1440） |
|| simulated_pyramid_win (1440m) | **61.37%** | 🟢 canonical 24h 分析口徑（`regime_aware_ic.py`, n=9,763） |
|| spot_long_win | **33.21%** | 🟡 legacy 比較口徑，非主 target |
| 全域 IC | **15/22** | 🟢 維持 |
| TW-IC | **17/22** | 🟢 維持高檔 |
| 模型數 | **8** | ✅ |
| Tests | **6/6** | ✅ 全過 |

## 📈 心跳 #616 摘要

### 本輪已驗證 patch
1. **Source-history blocker metadata surfaced end-to-end**：`scripts/feature_coverage_report.py` 與 `/api/features/coverage` 現在除了 `quality_flag/quality_label`，還會輸出 `history_class / backfill_status / backfill_blocker / recommended_action`，把 low-coverage sparse sources 明確升級成 **source-history blocker**，不再被誤判成前端畫圖問題。
2. **FeatureChart hidden-state rationale upgrade**：`web/src/components/FeatureChart.tsx` 的隱藏 chip / tooltip / hidden summary 改成顯示 `archive_required / snapshot_only / short_window_public_api` 等 history policy，並把 blocker 訊息直接帶到 UI，避免 heartbeat 再對同一批 sparse sources 空轉。
3. **Coverage API regression guard**：`tests/test_api_feature_history_and_predictor.py` 新增 coverage metadata 斷言，鎖住 source blocker metadata 不被移除或退化。

### 本輪 runtime facts（Heartbeat #616）
- `feature_coverage_report.py` 重新生成後，低 coverage sparse sources 已被明確分類為 source-history blocker：
  - **Claw / Claw intensity / Fin** → `archive_required`
  - **Fang / Scales / Nest** → `snapshot_only`
  - **Web** → `short_window_public_api`
- 目前 coverage 現況維持真實缺口而非假值污染：
  - **Claw / Fin / Nest = 0%**
  - **Web / Fang / Scales ≈ 15.7%**
  - 核心 canonical feature coverage 不受影響（usable **24**, hidden **11**）
- `hb_parallel_runner.py --hb 616 --no-train`：**4/4 PASS (3.9s)**；DB counts 維持 **Raw 19778 / Features 11164 / Labels 38530**；canonical `simulated_pyramid_win` rate **0.6008**。
- Canonical diagnostics 維持：**Global IC 15/22 PASS**, **TW-IC 17/22 PASS**；Dynamic Window 最佳 **N=1000 = 7/8 PASS**；recent **N=100/200/400** 仍是 `constant_target_window`，屬 label-distribution 問題，非 merge bug。
- Regime-aware IC：**Bear 6/8**, **Bull 8/8**, **Chop 8/8**, **Neutral 1/8**（`simulated_pyramid_win` 口徑）。
- 驗證：`pytest tests/test_api_feature_history_and_predictor.py -q` **3 passed**；`npm run build` ✅；`tests/comprehensive_test.py` via parallel runner **6/6 PASS**。

### Blocker 升級 / 狀態更正
- **#LOW_COVERAGE_SOURCES**：本輪不再把它視為單純 coverage 低或前端顯示 bug，而是**已明確升級為 source-history blocker map**：
  1. **archive_required**：Claw / Fin 需要 historical export 或完整 archive，不能靠 current live collector 逆向補歷史。
  2. **snapshot_only**：Fang / Scales / Nest 目前只有最新 snapshot，若過去未存 raw snapshot，就無法回補出可信歷史。
  3. **short_window_public_api**：Web 現在只有短 recent trade window，不能用 carry-forward 假造長期歷史。
- **結論**：這批 sparse sources 下一輪若要真正改善 coverage，必須做 **source-level raw snapshot collection / archive ingestion**，不是再調 FeatureChart 顯示策略。

## 📈 心跳 #615 摘要

### 本輪已驗證 patch
1. **Sparse-source historical cleanup**：新增 `scripts/cleanup_sparse_source_history.py`，把 historical features/raw 中「raw 缺值卻殘留 feature 值」與已知 sentinel fallback（Claw `ratio=1,total=0`、Nest `0.5`、Fin `0/0`）清洗成 `NULL`，停止讓舊污染繼續影響 FeatureChart / coverage / 後續重算。
2. **Canonical leaderboard target hygiene**：`server/routes/api.py::load_model_leaderboard_frame()` 改為 **優先保留 `simulated_pyramid_win` rows**，不再用 `label_spot_long_win IS NOT NULL` 當硬 gate；即使 path-aware label 為空，canonical simulated rows 仍可進入 leaderboard / target comparison。
3. **Regression test for target pollution**：`tests/test_model_leaderboard.py` 新增 simulated-only label row case，鎖住 canonical target loader 不再退回 legacy path-aware gate。

### 本輪 runtime facts（Heartbeat #615）
- `cleanup_sparse_source_history.py --apply` 實際清掉：
  - **Claw** feature rows **2403 → 0**；raw fallback sentinel rows **2188** 筆清成 NULL
  - **Fin** feature rows **2336 → 0**；raw fallback/null rows **2121** 筆對齊清理
  - **Nest** feature rows **2432 → 0**；raw fallback `0.5` rows **2217** 筆清成 NULL
  - **Fang/Web/Scales** stale carry-forward rows再各清 **669 / 669 / 680** 筆；剩餘 coverage 分別為 **15.79% / 15.79% / 15.69%**，現在反映真實 source history gap，而不是舊值偷帶
- `feature_coverage_report.py` 重新生成後，**`source_fallback_zero` 已從 Claw / Fin / Nest 消失**；三者現為 **0% coverage + `source_history_gap`**，表示污染已去除但真實歷史資料仍缺。
- `hb_parallel_runner.py --hb 615 --no-train`：**4/4 PASS (3.9s)**；DB counts 維持 **Raw 19778 / Features 11164 / Labels 38530**；canonical `simulated_pyramid_win` rate **0.6008**。
- Full IC 仍為 **15/22 PASS**，TW-IC **17/22 PASS**；表示這輪清的是 sparse-source 污染，不是核心 canonical label / IC 主線。
- `tests/test_model_leaderboard.py -q`：**9 passed**；`tests/comprehensive_test.py`：**6/6 PASS**。

### 新 blocker / 狀態更正
- **#LOW_COVERAGE_SOURCES**：從「假 0 污染 + history gap 混在一起」進一步收斂成兩件事：
  1. **污染清理已完成**：Claw / Fin / Nest 舊 fallback rows 已清成 NULL；Fang/Web/Scales stale carry-forward rows 已移除。
  2. **真正 blocker 只剩 history/backfill**：現在 coverage 低就是 source-level coverage 低，不再是 feature layer 假值污染。
- **canonical target 污染收斂**：model leaderboard loader 已不再被 `label_spot_long_win` 綁架；剩餘 legacy 污染範圍主要在舊報告/欄位命名，不在 leaderboard 主資料載入鏈路。

## 📈 心跳 #614 摘要

### 本輪已驗證 patch
1. **Sparse source no-carry-forward fix**：`feature_engine/preprocessor.py` 對 Claw / Fang / Fin / Web / Scales / Nest 改為只讀 **latest raw row**，若最新來源缺值就維持 `None`，不再用 `dropna().iloc[-1]` 把舊資料偷偷帶到新 row。
2. **Claw fallback zero stop**：`data_ingestion/claw_liquidation.py` 與 preprocessor 共同改成 **fetch fail → `None`**，不再把來源失敗寫成 `0.0 / ratio=1.0` 假中性值。
3. **Source-quality coverage surfacing**：`scripts/feature_coverage_report.py`、`/api/features/coverage`、`FeatureChart` 新增 `quality_flag / quality_label`，可明確區分 `source_fallback_zero` 與 `source_history_gap`，不再只顯示模糊 coverage/distinct badge。

### 本輪 runtime facts（Heartbeat #614）
- `hb_collect.py` 連續兩次在 **Raw fallback** 情境下仍可完成 pipeline：最新累計 **Raw 19778 / Features 11164 / Labels 38530**。
- **關鍵驗證**：第二次 fallback collect 後，`features_normalized` **+1 row**，但 `feat_claw` non-null **維持 2403 不再增加**，證明 sparse source 舊值不再被 forward-carry 到新 row。
- `feature_coverage_report.py` 現在把 **fin_netflow / claw / nest_pred** 標為 `source_fallback_zero`，把 **web_whale / fang_* / scales_ssr** 標為 `source_history_gap`，已可直接區分「假 0 污染」與「歷史 coverage 不足」。
- `hb_parallel_runner.py --hb 614 --no-train`：**4/4 PASS (3.9s)**，summary 已寫入 `data/heartbeat_614_summary.json`。
- Full IC：**15/22 PASS**；TW-IC：**17/22 PASS**。
- Dynamic window（canonical 1440m）：**N=100/200/400 仍為 constant_target_window**，**N=600=6/8 PASS**, **N=1000=7/8 PASS**, **N=2000=6/8 PASS**, **N=5000=5/8 PASS**。
- Frontend build：`npm run build` ✅ 通過；API coverage pytest：`3 passed`。

### 新 blocker / 狀態更正
- **#LOW_COVERAGE_SOURCES**：現已拆成兩種根因：
  - `source_fallback_zero`：Fin / Claw / Nest 的歷史 row 仍有假 0 污染；本輪已**停止新增污染**，但舊資料尚未 cleanup。
  - `source_history_gap`：Web / Fang / Scales 主要是歷史 coverage 不足，不是前端顯示問題。
- **根因升級**：先前的 source coverage 問題不只是「coverage 低」，還包含 **sparse source 被 preprocessor 舊值偷帶** 的流程缺口；此 root cause 已修復，但歷史資料仍需另輪回填/清洗。

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
| #LOW_COVERAGE_SOURCES | Fin / Fang / Web / Scales / Nest / Claw coverage 低，且歷史上混有假 0 與 stale carry-forward | 🟡 已部分修復並升級 blocker（#615 已清除假值污染；#616 再把剩餘缺口明確分類成 `archive_required / snapshot_only / short_window_public_api`。下一步必須做 source-level raw snapshot/archive ingestion，不能再把它當前端圖表問題） |
| #FEATURECHART_QUALITY_SIGNAL | FeatureChart 對低 coverage 特徵只顯示模糊 badge，使用者無法判斷是 coverage、distinct 還是 source fallback / source-history blocker 問題 | ✅ 已修復（#614 已顯示 `quality_flag / quality_label`；#616 再把 `history_class / backfill_status / backfill_blocker / recommended_action` 帶到 coverage API 與 hidden legend，前端現在能直接區分 frontend 隱藏與 source-level blocker） |
| #FINAL_CLOSE_LABEL_NOISE | final-close-only TP threshold 會把「曾 hit TP 但收盤回落」的可交易 setup 誤標為失敗 | ✅ 已修復（spot_long_win 已改為 path-aware label，並已重建實際 labels） |
| #LABEL_PATH_MISMATCH | 標籤語義與現貨金字塔執行路徑不一致，只看 horizon 結束點 | 🟡 已部分修復（path-aware + simulated pyramid labels 均已上線，#615 再修 model leaderboard loader，不再用 `label_spot_long_win` gate 掉 canonical simulated rows；下一步是把剩餘 legacy 報表/欄位命名完全去污） |

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
