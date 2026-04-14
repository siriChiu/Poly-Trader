# ISSUES.md — 問題追蹤

*最後更新：2026-04-14 05:28 UTC — Heartbeat #716 沒有再假設 `regime/gate/quality` bucket 足以代表 current live bull `ALLOW+D`，而是把 **4H structure bucket support** 正式接進 live decision-quality contract。`model/predictor.py` 現在會輸出 `structure_quality / structure_bucket`，在 scope diagnostics 中持久化 `recent500_structure_bucket_counts`、`current_live_structure_bucket_rows/share/metrics`，並新增 `decision_quality_structure_bucket_guardrail_*`；若 chosen calibration scope 幾乎沒有當前 live structure bucket 的歷史支持，runtime 會明確標記 `unsupported_live_structure_bucket_blocks_trade`。本輪驗證發現 current live bucket 是 **`ALLOW|base_allow|q35`**，但 chosen `regime_gate+entry_quality_label` scope 117 rows 中只有 **2 rows / 1.71%** 屬於同 bucket，dominant bucket 卻是 **`ALLOW|base_allow|q65` 66 rows**；exact `bull+ALLOW+D` 14 rows 也全是 **q85**，代表目前 live 結構與歷史 calibration 口袋不對齊。驗證：`python -m pytest tests/test_api_feature_history_and_predictor.py -q` → **23 passed**；`python scripts/hb_predict_probe.py` → `decision_quality_structure_bucket_guardrail_applied=true`、`decision_quality_structure_bucket_support_rows=2`、`execution_guardrail_reason="decision_quality_below_trade_floor; unsupported_live_structure_bucket_blocks_trade"`；`python scripts/hb_parallel_runner.py --fast --hb 716` 重新落地同一份 contract。結論修正：Heartbeat #715 解的是 exact toxic ALLOW lane，Heartbeat #716 再把 **scope-level structure mismatch** machine-check 化；下一輪要決定是把 structure bucket 納入 calibration scope/fallback，還是先為 current q35 live structure 補足可用歷史口袋，而不是繼續拿 q65/q85 spillover 當 proxy。*

## 📊 系統健康狀態 v4.69

| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw | **21,371** | 🟢 `python scripts/hb_parallel_runner.py --fast --hb 715` 本輪新增 **+1**；freshness 健康，continuity repair `4h=0 / 1h=0 / bridge=0` |
| Features | **12,800** | 🟢 fast heartbeat 本輪新增 **+1**；live probe 仍顯示 4H base/lag `10 / 30` 非空 |
| Labels | **42,615** | 🟢 240m / 1440m freshness 仍在 expected horizon lag 內；本輪 labels **+2**（lookahead horizon 內正常） |
|||||||||||||||||||| simulated_pyramid_win (DB overall) | **57.17%** | 🟢 canonical DB 整體口徑；fast heartbeat collect summary `simulated_win=0.5717` |

|||||||||||||||||| spot_long_win | **67.00%（recent 100）** | 🟡 legacy/path-aware 比較口徑；Heartbeat #686 起不再用它否決 canonical positive pocket 判讀 |
|||||||||||||||||| 全域 IC | **17/30** | 🟢 canonical diagnostics 仍可用；Nose/Tongue/Body/Pulse/Aura/Mind + VIX/DXY + ATR/VWAP/4H 路徑通過 |
|||||||||||||||||| TW-IC | **21/30** | 🟢 高於 14/30 gate；本輪與 #713 持平，仍高於全域 |
|||||||||||||||||| Regime IC | **Bear 4/8 / Bull 6/8 / Chop 5/8 / Neutral 4/8** | 🟢 canonical simulated target 維持；bull / chop 仍有可用訊號 |
|||||||||||||||||||| 模型 / 決策語義 | **live predictor = `phase16_baseline_v2`; calibration scope 仍是 `regime_gate+entry_quality_label`（117 rows, win=0.2393, quality=-0.0548, recent_pathology=True），但 exact live `bull+ALLOW+D` lane 已從 24 rows 收斂到 14 rows（wr=0.5000, q=+0.2412, true_negative_share=0.5000），`decision_quality_exact_live_lane_toxicity_applied=false`，`execution_guardrail_reason=decision_quality_below_trade_floor`。broader `regime_label+entry_quality_label` bull D lane 最差 spillover pocket 仍是 `bull|BLOCK`（116 rows, wr=0.0, q=-0.2858, pnl=-0.0111），其中新增 machine-readable `structure_overextended_block:10` + `structure_quality_block:106`** | 🟡 exact toxic ALLOW lane 已解除，但 broader bull/neutral spillover 與 recent pathology 仍把 chosen scope 壓成 D；下一輪要直接檢查 calibration scope 是否需要吃進 structure bucket，而不只是 regime/gate/quality label。`hb_predict_probe.py` 顯示 `non_null_4h_feature_count=10`, `non_null_4h_lag_count=30` |
|||||||||||||||||||| Verification | **`python -m pytest tests/test_api_feature_history_and_predictor.py tests/test_auto_propose_fixes.py tests/test_hb_parallel_runner.py tests/test_strategy_lab.py -q` + `python scripts/hb_predict_probe.py` + `python scripts/hb_parallel_runner.py --fast --hb 715`** | ✅ 本輪已重驗證 |

## 🎯 當前戰略問題（高準確度 / 高勝率 / 低回撤）

### 本輪優先順序（Heartbeat #707 後）
- **P1#1 — `#H_AUTO_LIVE_DQ_PATHOLOGY` 已從「exact toxic lane / overextended pocket」再推進到「scope-level structure mismatch 可 machine-check」**：Heartbeat #715 先把 exact `bull+ALLOW+D` toxic ALLOW pocket 從 gate 本身切掉；Heartbeat #716 再把 `structure_bucket` 正式接進 live decision-quality contract。現在 `model/predictor.py` / `hb_predict_probe.py` 會直接暴露 current live `structure_bucket`、各 scope 的 `recent500_structure_bucket_counts`、以及 `current_live_structure_bucket_rows/share/metrics`，並在 chosen scope 幾乎沒有 live structure 支持時打開 `decision_quality_structure_bucket_guardrail_*`。本輪新證據：current live bucket 是 **`ALLOW|base_allow|q35`**，但 chosen `regime_gate+entry_quality_label` scope 117 rows 內只有 **2 rows / 1.71%** 屬於同 bucket，dominant bucket 卻是 **`ALLOW|base_allow|q65` 66 rows**；exact `bull+ALLOW+D` 14 rows 更全部是 **q85**。也就是說，現在不只是 broader scope 被 neutral spillover 汙染，而是 **current live 結構根本沒有被 calibration scope 正確覆蓋**。下一輪 root-cause 問題因此更精準地收斂成：**是要把 structure bucket 納入 calibration scope / fallback，還是要先為 q35 live structure 補出可用歷史口袋。**
- **P1#2 — `#CORE_VS_RESEARCH_SIGNAL_MIXING`**：Heartbeat #688 已把 recent-drift diagnostics 裡的 sparse-source frozen / shift evidence降級成 `overlay_only=research_sparse_source`，並避免 `feat_claw*` / `feat_nest_pred` 之類研究欄位再次搶走 sibling-window 主證據；但 `null_heavy=10` 與 8 個 blocked sparse sources 仍存在，需持續限制研究訊號只做 overlay，避免再污染 canonical calibration / ranking。
- **P1#3 — `#LEADERBOARD_OBJECTIVE_MISMATCH`**：Strategy Lab/API/backtest 已有 4H gate + entry-quality parity；剩餘缺口更聚焦在 ranking contract 本身，而不是底層 4H 語義分裂。
- **Resolved / downgraded — exact live ALLOW-path ambiguity**：Heartbeat #702 解開了 exact ALLOW lane 與 broader bull+D 的混淆；Heartbeat #703 machine-check 化 gate composition；Heartbeat #706 再把 spillover pocket metrics machine-check 化，所以 heartbeat 不必再靠人工讀 raw scope matrix 才能判斷主病灶。
- **持續監控**：raw continuity bridge 仍連續為 `bridge=0`，保持健康但不可鬆手；`fin_netflow` 仍因 `COINGLASS_API_KEY` 缺失而 blocked。
- **P2**：其餘文件/展示層整理與非阻塞優化。

### 本輪建議起手式
1. 直接沿 **`#H_AUTO_LIVE_DQ_PATHOLOGY`** 做第三段拆解：在 `bull+D` narrowed lane 裡，優先針對 **`bull|BLOCK` 106 rows** 做 gate-input drill-down，列出它們的 `feat_4h_bb_pct_b / feat_4h_dist_bb_lower / feat_4h_dist_swing_low / bias200` 分布，確認 BLOCK 是真病灶還是 gate 過嚴。
2. 針對 `bull|BLOCK` vs `bull|ALLOW` 做 feature / label / gate 對照，優先驗證是否是 **4H collapse feature 真的對應 canonical 負 pocket**，而不是 current live ALLOW path 被 broader bull bucket 稀釋。
3. 持續驗證 continuity bridge 是否為 0；若再次連續觸發 bridge fallback，立刻升級回 raw continuity root-cause investigation。

### 本輪 root-cause 新證據（Heartbeat #684）
- **新增定位到第二個真 root cause**：`feature_engine/preprocessor.py::recompute_all_features()` 雖會重算 features rows，但**先前不會把 `feat_4h_*`、`regime_label`、`feature_version` 回寫到既有/新建 rows**。這代表任何依賴 recompute / backfill 的流程都可能把 recent canonical window 留在「主特徵存在，但 4H projection 缺失」的半同步狀態。
- **資料層證據**：在本輪 patch 前，`python scripts/hb684_recent_4h_gap_check.py` 顯示 recent 500 label-aligned rows 內仍有 **140+ NULL 4H projection cells**；oldest adverse rows 大量呈現 `feat_4h_bias50=None`、`feat_4h_dist_bb_lower=None/0`、`feat_4h_dist_swing_low=None/0`。
- **本輪修復**：補上 `recompute_all_features()` 的 4H/regime projection 寫回，並用 `scripts/hb684_backfill_recent_4h_projection.py` 針對 recent NULL rows 直接回填 4H features。
- **修復後驗證**：`python scripts/hb684_recent_4h_gap_check.py` 已回到 **recent 500 rows = 0 NULL 4H fields**；`python scripts/hb_predict_probe.py` 顯示 **`non_null_4h_feature_count=10`、`non_null_4h_lag_count=30`**；`python scripts/hb_parallel_runner.py --fast --hb 684` 重新產出的 drift artifact 也已不再把 `recent 500 rows` 升級成 `distribution_pathology`。

### #DECISION_QUALITY_GAP（持續 P0，但本輪再推進）
- **現象**：canonical target 與 label DB 已對齊後，真正缺口變成 live predictor / leaderboard / API / 前端摘要 是否使用**同一套** decision-quality semantics，而不是 predictor 說一套、ranking 仍靠 proxy 分數排序。
- **本輪修復**：Heartbeat #642 已把 `backtesting/model_leaderboard.py` / `server/routes/api.py` 接到 canonical decision-quality contract；Heartbeat #643 把 `web/src/pages/StrategyLab.tsx` 的**模型排行榜**切到 canonical quality semantics；Heartbeat #644 再把 `server/routes/api.py::api_strategy_leaderboard()`、`api_get_strategy()` 與 `web/src/pages/StrategyLab.tsx` 的**策略排行榜主表**一起切到 `avg_decision_quality_score / avg_expected_win_rate / avg_expected_drawdown_penalty / avg_expected_time_underwater / avg_allowed_layers / avg_entry_quality`；Heartbeat #645 再把 **active strategy summary** 與 `/api/strategies/run` / `/api/strategies/{name}` payload 一起補上 `decision_contract`（target label / sort semantics / horizon）；Heartbeat #650 對齊 Dashboard `ConfidenceIndicator`；Heartbeat #651 再把 `/api/backtest` 與 `web/src/components/BacktestSummary.tsx` 一起升級到 canonical feature + decision-quality contract；Heartbeat #652 雖已把 standalone `web/src/pages/Backtest.tsx` 內容升級，但 **Heartbeat #653 發現 app shell 仍把 `/backtest` redirect 到 `/lab`**，導致使用者其實打不開那個 canonical page；Heartbeat #654 把 route/nav + 三大 surface wiring 鎖進 regression test；Heartbeat #655 再把 Strategy Lab active summary 的 legacy ROI/PF 卡正式降級為 tie-breaker 區塊，並在 canonical ranking reason 缺欄時顯式顯示 `⚠️ canonical DQ 缺失，暫退回 legacy ROI...`；**本輪 #656 再把 Dashboard 4H 結構卡原本的手寫 bias→action 文案降級為 `結構背景`，主決策固定顯示 live `regime_gate + entry_quality + allowed_layers`，並補上「raw 4H 與 canonical gate 衝突時以 decision-quality contract 為準」的明示。**
- **本輪證據**：`python scripts/hb_parallel_runner.py --fast --hb 656` → Raw **20389** / Features **11818** / Labels **40873**；`python -m pytest tests/test_frontend_decision_contract.py tests/test_api_feature_history_and_predictor.py -q` → **11 passed**；`cd web && npm run build` ✅。
- **剩餘風險**：這仍是 **historical calibration layer + leaderboard-side aggregation**，不是直接訓練出的多目標 live head；雖然 Dashboard confidence card、Dashboard backtest summary、Dashboard 4H structure panel、Strategy Lab compare flow、standalone Backtest page 都已對齊 canonical contract 或顯式 fallback framing，且 regression 已被測試鎖住，但首頁其他 legacy summary 卡與未來新增 compare surfaces 仍可能退回 ROI/PF-only 或舊二元信心文案。
- **建議方向**：下一輪把 Dashboard 其餘摘要卡與任何新 compare surface 一併套上 `decision_quality_score + drawdown_penalty + time_underwater + allowed_layers` 語義，並讓新增 surface 一上線就納入 `tests/test_frontend_decision_contract.py`，避免 UI 可見層再次出現「source 有 contract、runtime 看不到」的假完成。

### #SINGLE_STAGE_ENTRY_LOGIC（P0，本輪再推進）
- **現象**：兩階段決策 baseline 已在 `strategy_lab.py` 落地：`_compute_regime_gate()` / `_compute_entry_quality()` / `_allowed_layers_for_signal()` 已存在，API 與 UI 也能顯示 gate/quality 摘要。
- **本輪修復**：`model/predictor.py::predict()` 現在會正式輸出 `regime_gate` / `entry_quality` / `entry_quality_label` / `allowed_layers`；`scripts/hb_predict_probe.py` 也會把這些欄位印出，避免 heartbeat 再把 live path 誤報成只剩 signal/confidence。
- **剩餘缺口**：目前仍是 baseline 規則鏡射，尚未把更進一步的 decision-quality target 與 leaderboard ranking 完整接上 live contract。

### #LAYER_SIZING_NOT_CONFIDENCE_AWARE（P0，本輪再推進）
- **現象**：Strategy Lab baseline 已按品質分級做 0/1/2/3 層限制；相關 API / UI / tests 已通過。
- **本輪修復**：live predictor 現在會正式回傳 `allowed_layers`，且 `should_trade` 會受 layer allowance 約束；`/predict/confidence` 的 tuple-unpack bug 也已修掉，避免 API 路徑拿到錯誤 predictor object。
- **剩餘缺口**：layer sizing 尚未成為 leaderboard 主排序依據，也還沒和完整 quality-target 輸出綁定。

### #CORE_VS_RESEARCH_SIGNAL_MIXING（持續 P1）
- **現象**：主幹高 coverage technical / 4H features 與 sparse-source research features 仍容易在 UI 與分析語義上混在一起。
- **風險**：會出現「研究信號看起來很厲害，但其實成熟度不足」的假信心，污染準確度與決策穩定性。
- **建議方向**：把訊號明確分成 **核心可用 / 研究中 / blocked** 三層，並在主模型與 UI 上採不同權重與展示策略。

### #LEADERBOARD_OBJECTIVE_MISMATCH（本輪再推進）
- **現象**：先前 leaderboard 已從單看 ROI 進化到複合評分，但勝率權重仍偏高，容易把「看起來命中率漂亮、實際資金效率一般」的模型排太前面。
- **本輪修復**：已把 `backtesting/model_leaderboard.py` 與 `server/routes/api.py::_strategy_leaderboard_sort_key()` 調整成 **ROI + 低回撤優先**，再看 `profit_factor / decision_quality`；勝率只保留為 reference。前端 `StrategyLab.tsx` 的 `sort_semantics` 與 fallback 文案也同步改成 `ROI -> lower max_drawdown -> avg_decision_quality_score -> profit_factor (win_rate reference only)`。
- **額外實作**：Strategy Lab 新增 **`reserve_90`（10% 試單 / 90% 後守）** 資金模式。回測會先用小倉位試單，只有當價格相對首筆建倉回撤達門檻時才解鎖後守資金，目的不是提高名義勝率，而是提升資金生存率與降低早期滿倉風險。
- **對『風暴斬倉』的評估**：概念上有助於降低高位套牢時間，但它需要真正的 **inventory-lot accounting / partial inventory release engine**。目前 `strategy_lab.py` 仍是整筆持倉聚合回測模型，尚未追蹤「低位獲利單同步替高位套牢單減倉」的 lot 級生命週期，因此這一部分先記為下一階段策略引擎升級，不在本輪直接硬上，以免做出假回測。
- **本輪再推進**：Leaderboard 2.0 已不只在 model leaderboard。現在 strategy leaderboard 也已同步升級成 `Overall / Reliability / Return Power / Risk Control / Capital Efficiency` 五維評分，並新增 SQLite `leaderboard_strategy_snapshots / leaderboard_strategy_scorecards`、`/api/strategies/leaderboard/history`、前端可排序總表、策略象限圖、快照歷史與 rank delta。
- **剩餘缺口**：目前仍缺 capital-mode filter / trend chart，也還沒把 `classic_pyramid` vs `reserve_90` 的 OOS 差異回寫成正式 leaderboard diagnostics；storm-unwind / trapped-inventory half-life 仍未納入 score。
- **下一步方向**：直接跑 classic pyramid vs reserve_90 的 OOS `ROI / max_drawdown / PF / underwater time` 對照，並把 capital-mode compare / trend chart 接進 Leaderboard 2.0；若有效，再升級到真正的 inventory-lot / storm-unwind backtest engine，而不是先用勝率包裝成假改善。

### #DYNAMIC_WINDOW_NOT_DISTRIBUTION_AWARE（持續 P0，本輪再推進）
- **現象**：Heartbeat #660 之後，canonical full/regime IC 仍健康，但 recent-weighted TW-IC 持續低於 **14/30**；近期視窗已被證實存在 `constant_target + 100% chop`，不能再讓 recency-heavy path 無條件相信最新 slice。
- **前序修復**：Heartbeat #662 已讓 `scripts/dynamic_window_train.py` 以 `data/recent_drift_report.json` 為 guardrail 來源，將 `constant_target / regime_concentration` 視窗標成 `skip_for_recommendation`，並把 **raw best N=600** 明確降級成 **recommended window = N=5000**；Heartbeat #663 再讓 `model/predictor.py::_infer_live_decision_quality_contract()` 消費這份 contract，把 live calibration 鎖到 `recommended_best_n`；Heartbeat #664 再讓 `model/train.py::load_training_data()` 對 polluted recent tail 做 TW-IC damping；Heartbeat #666 再讓 calibration scope 拒絕 `constant_target / label_imbalance` 的窄 bucket；Heartbeat #667 再把 guardrail 推到 execution-time layer caps。
- **本輪修復（Heartbeat #668）**：`scripts/recent_drift_report.py` 不再只回報 `alerts`。它現在額外輸出 `quality_metrics + drift_interpretation`（`supported_extreme_trend / distribution_pathology / regime_concentration / healthy`），把 recent constant-target 視窗分成「真實極端趨勢口袋」與「真的可疑病灶」。`scripts/auto_propose_fixes.py` 也同步吃這個 contract：當 recent 100-row window 雖為 constant-target，但同時具備 **高 avg_pnl / 高 avg_quality / 低 drawdown_penalty / 高 spot_long_win_rate** 時，blocker 仍保留 calibration guardrail，但 investigation wording 會改成檢查 **recent feature variance / regime narrowness / calibration scope**，不再直接假設 labels 壞掉。
- **本輪證據**：`python scripts/recent_drift_report.py` → last 100 rows `win_rate=1.0000 / dominant_regime=chop(100%) / interpretation=supported_extreme_trend / avg_pnl=0.0202 / avg_quality=0.6869 / avg_dd_penalty=0.0269`；`HB_RUN_LABEL=668 python scripts/auto_propose_fixes.py` → `#H_AUTO_TW_DRIFT` action wording 已改成「保留 guardrail，但改查 recent feature variance / regime narrowness / calibration scope」；`pytest tests/test_auto_propose_fixes.py -q` → **6 passed**；`python scripts/hb_parallel_runner.py --fast --hb 668` 已把新 drift contract 寫回 `data/heartbeat_668_summary.json`。
- **剩餘風險**：這次修的是 **drift blocker 治理與判讀**，不是讓 TW-IC 指標立刻回升；Heartbeat #668 實測 TW-IC 仍是 **12/30**。也就是說，我們現在更清楚知道 recent 100 rows 是「真實單向極端口袋」而不是直接的 label corruption，但 recent feature variance / calibration scope 是否因此被過度稀釋仍未解決。
- **建議方向**：下一輪應直接重跑訓練 / compare pre-post `tw_guardrail + execution_guardrail` 對 `model/ic_signs.json / last_metrics.json / hb_predict_probe.py` 的聯動影響，並額外檢查 recent 100/250 rows 的 feature variance / distinct count / regime narrowness，確認 TW-IC 低迷是 **真實單向行情下的特徵退化**，還是 calibration/training weighting 仍有殘餘偏誤。

### #LIVE_REGIME_ROUTE_MISMATCH（新 P0，本輪已修復）
- **現象**：Heartbeat #663 前，`model/predictor.py::predict()` 的 regime-model routing 仍用 `_determine_regime(features)` heuristic；但 live decision contract / `hb_predict_probe.py` 對外暴露的是 `decision_profile.regime_label`。這會導致 **used_model 與對外宣告的 regime_label 不一致**，形成假語義與錯誤驗證路徑。
- **本輪修復**：predictor routing 現在優先使用 `decision_profile.regime_label`（再 fallback 到 features/db/heuristic），並把 `model_route_regime` 一起輸出。實測 probe 由先前的 `used_model=regime_bear_ensemble` + `regime_label=chop`，修正為 **`used_model=regime_chop_abstain` + `model_route_regime=chop`**。
- **本輪證據**：`python scripts/hb_predict_probe.py` → `signal=ABSTAIN`, `regime_label=chop`, `model_route_regime=chop`, `used_model=regime_chop_abstain`；`python -m pytest tests/test_api_feature_history_and_predictor.py -q` → **9 passed**（新增 routing + guardrail regression）。
- **剩餘風險**：這修的是 live predictor route/contract 一致性，不代表 regime assignment 本身已經最佳化；若之後要重調 `_determine_regime()` heuristic，仍必須與 DB regime label policy / Strategy Lab baseline 一起驗證。

### 實作計畫
- `docs/plans/2026-04-10-phase-16-implementation-plan.md`

## 📈 心跳 #683 摘要

### 本輪已驗證 patch
1. **Live predictor same-scope pathology guardrail now consumes sibling-window contrast, not just streak/means**：`model/predictor.py::_recent_scope_pathology_summary()` 新增 `reference_window_comparison`，會把 chosen pathology window 對比前一個等長 sibling window，輸出 `prev_win_rate / Δquality / Δpnl / top_mean_shift_features`，並把這些資訊直接寫進 `decision_quality_recent_pathology_reason`。
2. **Calibration artifact now carries the concrete 4H collapse fields inside runtime verification**：`_infer_live_decision_quality_contract()` 會把 `feat_4h_dist_bb_lower / feat_4h_dist_swing_low / feat_4h_bb_pct_b` 帶進 live pathology summary，讓 probe/runtime 能直接看到與 heartbeat drift artifact 同一組 top shifts，而不是只剩 aggregate labels。
3. **Predictor probe now exposes the richer pathology artifact end-to-end**：`scripts/hb_predict_probe.py` 已新增 `decision_quality_recent_pathology_*` 欄位，包含 nested `reference_window_comparison`，可直接驗證 runtime 是否與 heartbeat drift contract 對齊。
4. **Regression tests lock the new same-scope contrast contract**：`python -m pytest tests/test_api_feature_history_and_predictor.py -q` → **15 passed**。

### 本輪 runtime facts（Heartbeat #683）
- `python scripts/hb_parallel_runner.py --fast --hb 683`：**Raw 21142→21143 / Features 12571→12572 / Labels 42265→42314**；continuity repair `4h=0 / 1h=0 / bridge=0`。
- Canonical freshness：240m `latest_target=2026-04-13 11:13:01.942065`（lag vs raw ≈3.0h）；1440m `latest_target=2026-04-12 15:13:20.681647`（lag vs raw ≈23.0h, raw gap ≈1.0h）— 皆屬 expected horizon lag。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（fast heartbeat 觸發）：Global **19/30 PASS**、TW-IC **29/30 PASS**；Regime IC **Bear 4/8 / Bull 6/8 / Chop 5/8 / Neutral 4/8**（`simulated_pyramid_win`, n=11,882）。
- `python scripts/recent_drift_report.py`：primary drift window 仍是 **500 rows**, `win_rate=0.1120`, `interpretation=distribution_pathology`, `dominant_regime=chop(78.0%)`，且 sibling-window contrast 再次指向 **`feat_4h_dist_bb_lower / feat_4h_dist_swing_low / feat_4h_bb_pct_b`**。
- `python scripts/hb_predict_probe.py`（patch 後重跑）：live predictor 仍為 `should_trade=false / allowed_layers=0 / decision_quality_label=D`，但 guardrail reason 現在直接帶出 same-scope **`prev_win_rate=0.2 / Δquality=-0.1361 / Δpnl=-0.0021 / top_shifts=feat_4h_dist_bb_lower, feat_4h_bb_pct_b, feat_4h_dist_swing_low`**。

### Blocker 升級 / 狀態更正
- **`#H_AUTO_RECENT_PATHOLOGY` 仍未解除**：本輪修的是 **runtime contract 對齊**，不是 recent canonical 500-row pathology 本身。現在 live path、heartbeat artifact、probe 已對齊到同一個 sibling-window collapse 證據，但 4H 結構 collapse 的 source/label root cause 仍未收斂。
- **沒有假進度**：這輪沒有宣稱 signal 恢復；它把 blocker 從「heartbeat 知道 sibling collapse、live path 只知道 streak/means」推進成「runtime 也能看到同一個 collapse artifact」。下一輪必須直接對 4H 結構 path 與 label path 的根因下手。

## 📈 心跳 #680 摘要

### 本輪已驗證 patch
1. **Recent drift report now exposes the real adverse streak inside a mixed window**：`scripts/recent_drift_report.py` 新增 `longest_target_streak / longest_zero_target_streak / longest_one_target_streak`，CLI 也同步列出 `adverse_streak` 與 example rows；不再只顯示恢復中的 tail streak。
2. **Auto-propose now escalates the hidden losing pocket instead of just the recovered tail**：`scripts/auto_propose_fixes.py` 的 drift summary 會帶出 `adverse_streak` + `adverse_examples`，讓 `#H_AUTO_RECENT_PATHOLOGY` 直接指向 224-row `target=0` pocket，而不是只看到最後 26-row rebound。
3. **Live predictor same-scope pathology reason now cites the same adverse streak evidence**：`model/predictor.py::_recent_scope_pathology_summary()` 會把 chosen scope 內最長 adverse streak 寫進 `decision_quality_guardrail_reason`，probe 已驗證 live path 與 heartbeat 對齊到同一段 recent pathology。
4. **Regression tests locked the new diagnostics contract**：`python -m pytest tests/test_recent_drift_report.py tests/test_api_feature_history_and_predictor.py -q` → **19 passed**。

### 本輪 runtime facts（Heartbeat #680）
- `python scripts/hb_parallel_runner.py --fast --hb 680`：**Raw 21137→21138 / Features 12566→12567 / Labels 42197→42211**；continuity repair `4h=0 / 1h=0 / bridge=0`。
- Canonical freshness：240m `latest_target=2026-04-13 10:12:19.450525`（lag vs raw ≈3.0h）；1440m `latest_target=2026-04-12 14:11:18.089855`（lag vs raw ≈23.0h, raw gap ≈1.0h）— 皆屬 expected horizon lag。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（由 fast heartbeat 觸發）：Global **18/30 PASS**、TW-IC **25/30 PASS**；Regime IC **Bear 4/8 / Bull 6/8 / Chop 6/8 / Neutral 4/8**（`simulated_pyramid_win`, n=11,831）。
- `python scripts/recent_drift_report.py`：primary drift window 仍是 **250 rows**, `win_rate=0.1040`, `interpretation=distribution_pathology`, `dominant_regime=chop(59.2%)`，但現在也明確顯示 **`tail_streak=26x1` + `adverse_streak=224x0 (2026-04-12 05:02:22 -> 2026-04-12 13:39:36)`**。
- `python scripts/hb_predict_probe.py`：live predictor 仍為 `should_trade=false / allowed_layers=0 / decision_quality_label=D`，guardrail reason 直接引用 **250-row pathology + 224x0 adverse streak**。

### Blocker 升級 / 狀態更正
- **#H_AUTO_RECENT_PATHOLOGY 仍未解除**：本輪修的是 **病灶定位品質**，不是 recent canonical path 本身。現在已確定最需要 root-cause drill-down 的不是尾端 26-row rebound，而是其前面的 **224-row target=0 pocket**。
- **沒有假進度**：這輪沒有宣稱 signal 已恢復，只把 recent-pathology evidence 從「尾端看起來有點好轉」推進成「可 machine-read 地指出真正的失敗主體」。下一輪必須直接對 224-row pocket 做 source / feature / label path 拆解。

## 📈 心跳 #679 摘要

### 本輪已驗證 patch
1. **Primary drift window no longer under-reports sustained recent pathology**：`scripts/recent_drift_report.py::_find_primary_window()` 現在在 severity / delta 同級時優先選更持久的視窗，避免把 250-row 連續 target=0 病灶縮成 100-row 短 slice。
2. **Live predictor same-scope pathology guardrail now scans 100/250/500 rows instead of hardcoding 100**：`model/predictor.py::_recent_scope_pathology_summary()` 會挑出最嚴重且最持久的負向 recent window，並把 window 起迄時間寫進 `decision_quality_guardrail_reason`。
3. **Regression tests lock both governance fixes**：`tests/test_recent_drift_report.py` 與 `tests/test_api_feature_history_and_predictor.py` 新增 coverage，固定驗證 drift primary window 與 live recent-pathology summary 都會偏向更持久的 pathology slice。

### 本輪 runtime facts（Heartbeat #679）
- `python scripts/hb_parallel_runner.py --fast --hb 679`：**Raw 21135→21136 / Features 12564→12565 / Labels 42158→42168**；collect pipeline 持續健康，continuity repair `4h=0 / 1h=0 / bridge=0`。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（fast heartbeat 觸發）：Global **20/30 PASS**、TW-IC **29/30 PASS**；Regime IC **Bear 5/8 / Bull 6/8 / Chop 6/8 / Neutral 4/8**（`simulated_pyramid_win`, n=11,805）。
- `python scripts/recent_drift_report.py`（patch 後重跑）：primary drift window 已從 **100 rows** 升級成 **250 rows**；`win_rate=0.0000`、`alerts=['constant_target']`、`interpretation=distribution_pathology`、`tail_streak=250x0 since 2026-04-12 03:00:00.000000`。
- `python scripts/hb_predict_probe.py`（patch 後重跑）：live predictor 仍為 `should_trade=false / allowed_layers=0 / decision_quality_label=D`，且 guardrail reason 現在直接引用 **250-row same-scope pathology window**：`avg_pnl=-0.0120 / avg_quality=-0.2882 / window=2026-04-11 06:24:07.424593->2026-04-12 13:39:36.317262`。
- `python -m pytest tests/test_recent_drift_report.py tests/test_api_feature_history_and_predictor.py -q` → **18 passed**。

### Blocker 升級 / 狀態更正
- **#H_AUTO_RECENT_PATHOLOGY 仍未解除**：本輪修的是 **治理與 runtime guardrail 對 sustained pathology 的對齊**，不是 recent canonical path 本身的 root cause。現在已確認病灶至少持續 250 rows，下一輪必須直接對這段 canonical tail 做 source / feature / label path drill-down。
- **沒有假進度**：這輪沒有宣稱 signal 恢復，也沒有宣稱 recent pathology 消失；只把 blocker 從「知道最後 100 rows 很壞」推進成「heartbeat 與 live predictor 都知道真正更持久的壞區段在哪裡」。

## 📈 心跳 #676 摘要

### 本輪已驗證 patch
1. **Recent drift artifact now carries target-path drill-down, not just aggregate pathology counters**：`scripts/recent_drift_report.py` 新增 `target_path_diagnostics={tail_target_streak, target_regime_breakdown, recent_examples}`，把 recent canonical pocket 具體落到「從何時開始連續 target=0、最後幾筆的 regime / pnl / quality 長什麼樣」。
2. **Heartbeat summary and auto-propose now preserve the same machine-readable path evidence**：`scripts/hb_parallel_runner.py` 會把 `target_path_diagnostics` 寫進 `data/heartbeat_676_summary.json`；`scripts/auto_propose_fixes.py` 也會把 `tail_streak + recent_examples` 直接帶進 `#H_AUTO_RECENT_PATHOLOGY` action，避免下輪 heartbeat 重新退回只看 aggregate 敘事。
3. **Regression tests lock the new governance contract**：`tests/test_recent_drift_report.py`、`tests/test_auto_propose_fixes.py`、`tests/test_hb_parallel_runner.py` 已固定驗證 drift report / auto-propose / heartbeat summary 會同步攜帶 target-path evidence。

### 本輪 runtime facts（Heartbeat #676）
- `python scripts/hb_parallel_runner.py --fast --hb 676`：**Raw 21077→21078 / Features 12506→12507 / Labels 42154→42154**；summary 已刷新 `data/heartbeat_676_summary.json`。
- Canonical freshness：240m `latest_target=2026-04-13 08:00:00`、`raw_gap≈1.0h`；1440m `latest_target=2026-04-12 12:00:00`、`raw_gap≈1.5h`，兩者皆仍屬 `expected_horizon_lag`。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（由 fast heartbeat 觸發）：Global **20/30 PASS**、TW-IC **27/30 PASS**；Regime IC **Bear 5/8 / Bull 6/8 / Chop 6/8 / Neutral 4/8**（`simulated_pyramid_win`, n=11,796）。
- `python scripts/recent_drift_report.py`：primary drift window 仍是 **last 100 rows**，但現在可直接看到 **`tail_streak=100x0 since 2026-04-12 07:21:13`**，且 recent examples 尾端仍為 `target=0 / regime=chop / negative quality`。
- `python scripts/hb_predict_probe.py`：live predictor 仍被壓到 **`expected_win_rate=0.0 / decision_quality_label=D / allowed_layers=0`**，表示 runtime guardrail 仍與 recent pathology 對齊。
- `python -m pytest tests/test_recent_drift_report.py tests/test_auto_propose_fixes.py tests/test_hb_parallel_runner.py -q` → **15 passed**。

### Blocker 升級 / 狀態更正
- **#H_AUTO_RECENT_PATHOLOGY 仍未解除**：這輪修的是 **root-cause evidence path**，不是 recent negative canonical pocket 本身。現在已能 machine-read 地指出 pathology 從哪個 timestamp 開始、最後幾筆樣本長什麼樣；下一輪必須直接對準這段 canonical path 的 source/feature/label 根因。
- **沒有假進度**：這輪沒有宣稱 signal 恢復，也沒有宣稱 recent pathology 消失；只是把 blocker 從「知道有病灶」推進成「heartbeat / auto-propose / summary 都能帶著可執行的 target-path 線索」。

## 📈 心跳 #674 摘要

### 本輪已驗證 patch
1. **Live decision-quality calibration now respects negative recent canonical pathology inside the chosen scope**：`model/predictor.py::_summarize_decision_quality_contract()` 新增 recent-scope pathology stress check。若 chosen calibration lane 的 recent 100 rows 出現 `constant_target / label_imbalance` 且 `avg_pnl` 或 `avg_quality` 已轉負，contract 會直接用 recent 壞資料下修 `expected_win_rate / expected_pyramid_pnl / expected_pyramid_quality`，並同步提高 drawdown / time-underwater 風險，而不是繼續沿用較寬歷史 bucket 的樂觀平均。
2. **Pathology guardrail now reaches execution-time deployment**：`model/predictor.py::_apply_live_execution_guardrails()` 會在 `decision_quality_recent_pathology_applied=true` 時直接把 live deployment 壓到 `allowed_layers=0`，避免 runtime 繼續拿看似 healthy 的 B/C quality 去部署 recent negative pocket。
3. **Regression tests lock the new predictor contract**：`tests/test_api_feature_history_and_predictor.py` 新增 recent-pathology calibration 與 execution guardrail 測試，固定驗證 negative recent slice 會把 contract 壓成 D/0-layer，而不是只在 issue/governance 層報警。

### 本輪 runtime facts（Heartbeat #674）
- `python scripts/hb_parallel_runner.py --fast --hb 674`：**Raw 21026→21027 / Features 12455→12456 / Labels 42152→42152**；summary 已刷新 `data/heartbeat_674_summary.json`。
- Canonical freshness：240m `latest_target=2026-04-13 07:00:00`、`raw_gap≈1.0h`；1440m `latest_target=2026-04-12 11:00:00`、`raw_gap≈1.5h`，兩者皆仍屬 `expected_horizon_lag`。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（由 fast heartbeat 觸發）：Global **20/30 PASS**、TW-IC **27/30 PASS**；Regime IC **Bear 5/8 / Bull 6/8 / Chop 6/8 / Neutral 4/8**（`simulated_pyramid_win`, n=11,795）。
- `python scripts/recent_drift_report.py`（由 fast heartbeat 觸發）：primary drift window 仍是 **last 100 rows**, `win_rate=0.0000`, `dominant_regime=chop(75%)`, `interpretation=distribution_pathology`, `avg_pnl=-0.0108`, `avg_quality=-0.2810`, `feature_diag=variance:28/49, frozen:5, compressed:23, distinct:15, null_heavy:10`。
- `python scripts/hb_predict_probe.py`（patch 後重跑）：live predictor 仍為 `regime_gate=CAUTION / entry_quality_label=C`，但 calibration contract 已被 recent pathology 拉回 **`expected_win_rate=0.0`, `expected_pyramid_pnl=-0.0102`, `expected_pyramid_quality=-0.2649`, `decision_quality_label=D`, `allowed_layers=0`**；不再出現用 broader `regime_gate` 歷史桶稀釋 recent 壞 pocket 的假樂觀。
- `python -m pytest tests/test_api_feature_history_and_predictor.py -q` → **14 passed**。

### Blocker 升級 / 狀態更正
- **#H_AUTO_RECENT_PATHOLOGY 仍未解除**：本輪修的是 live calibration / execution 語義，讓 runtime 不再忽視 recent 負向 canonical pocket；但造成 recent 100-row 全敗的 label/path 根因仍未找出。
- **沒有假進度**：這輪沒有宣稱 signal 已恢復，只是把 blocker 從「issue/heartbeat 看得到、live path 還會稀釋掉」推進成「live predictor 會真的縮手」。下一輪必須直接對準 recent canonical entry path 與 target 生成根因。

## 📈 心跳 #672 摘要

### 本輪已驗證 patch
1. **Auto-propose now escalates negative recent canonical pathology as a first-class P0**：`scripts/auto_propose_fixes.py` 新增 `#H_AUTO_RECENT_PATHOLOGY` 規則；當 primary drift window 是 `distribution_pathology`，且同時出現 `constant_target/label_imbalance` + 負 `avg_pnl/avg_quality` 或極低 `spot_long_win_rate` 時，會直接把真正 blocker 寫回 `issues.json`。
2. **Regression tests lock the new blocker contract**：`tests/test_auto_propose_fixes.py` 新增 recovered-TW-but-pathological-window 測試，固定驗證 TW-IC 已恢復時，治理層仍會升級 `#H_AUTO_RECENT_PATHOLOGY`，不再只留下較弱的 `#H_AUTO_REGIME_DRIFT`。
3. **End-to-end fast heartbeat re-run confirms the runner now emits the real blocker**：`python scripts/hb_parallel_runner.py --fast --hb 672` 已重新收集 fresh raw/features、重跑 IC / drift / auto-propose，summary 與 issues.json 都顯示 current run 的 P0 為 `#H_AUTO_RECENT_PATHOLOGY`。

### 本輪 runtime facts（Heartbeat #672）
- `python scripts/hb_parallel_runner.py --fast --hb 672`：**Raw 20991→20992 / Features 12420→12421 / Labels 42150→42150**；summary 已刷新 `data/heartbeat_672_summary.json`。
- Canonical freshness：240m `latest_target=2026-04-13 06:00:00`、`raw_gap≈1.0h`；1440m `latest_target=2026-04-12 10:00:00`、`raw_gap≈1.5h`，兩者皆仍屬 `expected_horizon_lag`。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（由 fast heartbeat 觸發）：Global **20/30 PASS**、TW-IC **27/30 PASS**；Regime IC **Bear 5/8 / Bull 6/8 / Chop 6/8 / Neutral 4/8**（`simulated_pyramid_win`, n=11,794）。
- `python scripts/recent_drift_report.py`：primary drift window 仍是 **last 100 rows**，`win_rate=0.0000`、`dominant_regime=chop(75%)`、`interpretation=distribution_pathology`、`avg_pnl=-0.0108`、`avg_quality=-0.2809`、`avg_dd_penalty=0.2702`、feature diagnostics=`variance:28/49, distinct:15, null_heavy:10`。
- `python scripts/hb_predict_probe.py`：live predictor 仍被 guardrail 壓到 `should_trade=false`、`allowed_layers=0`、`decision_quality_label=D`；說明 runtime execution path 已保守，但治理層之前沒有把 recent pathology 正確升級。
- `python -m pytest tests/test_auto_propose_fixes.py -q` → **9 passed**。

### Blocker 升級 / 狀態更正
- **#H_AUTO_RECENT_PATHOLOGY 現在是 current runtime 的真正 P0 blocker**：不是 TW-IC 崩掉，而是 recent canonical rows 本身呈現負向 distribution pathology；這個 blocker 現在終於被 auto-propose 正確 machine-check 化。
- **#H_AUTO_TW_DRIFT / #H_AUTO_STREAK 維持 resolved**：它們已不再應該遮蔽真正的 recent-pathology investigation。

## 📈 心跳 #668 摘要

### 本輪已驗證 patch
1. **Recent drift artifacts now distinguish suspicious pathology from an extreme-but-supported trend pocket**：`scripts/recent_drift_report.py` 新增 `quality_metrics + drift_interpretation`，把 `constant_target` 視窗拆成 `supported_extreme_trend / distribution_pathology / regime_concentration / healthy`，不再只靠 alerts 判讀。
2. **Auto-propose no longer auto-describes every constant-target recent window as label corruption**：`scripts/auto_propose_fixes.py` 現在會讀 `drift_interpretation`；若 recent window 雖是 constant-target，但同時具備高 `avg_simulated_pnl / avg_simulated_quality / spot_long_win_rate` 且低 `avg_drawdown_penalty / time_underwater`，則 blocker 會保留 guardrail，但 investigation wording 改成檢查 **recent feature variance / regime narrowness / calibration scope**。
3. **Regression tests lock the new governance contract**：`tests/test_auto_propose_fixes.py` 新增 drift summary richness 與 `supported_extreme_trend` wording coverage，避免未來又退回「只要 constant-target 就一律當 label 壞掉」的假治理。

### 本輪 runtime facts（Heartbeat #668）
- `python scripts/hb_parallel_runner.py --fast --hb 668`：**Raw 20494→20495 / Features 11923→11924 / Labels 41051→41059**；summary 已刷新 `data/heartbeat_668_summary.json`。
- Canonical freshness：240m `latest_target=2026-04-11 05:36:08.122370`、`raw_gap≈0.6h`；1440m `latest_target=2026-04-10 09:36:06.756661`、`raw_gap≈1.4h`，兩者皆仍屬 `expected_horizon_lag`。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（由 fast heartbeat 觸發）：Global **13/30 PASS**、TW-IC **12/30 PASS**；Regime IC **Bear 6/8 / Bull 8/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,274）。
- `python scripts/recent_drift_report.py`：primary drift window 仍是 **last 100 rows**，但現在明確落地為 **`interpretation=supported_extreme_trend`**，同時附帶 `avg_pnl=0.0202 / avg_quality=0.6869 / avg_dd_penalty=0.0269 / spot_long_win_rate=0.93`；這表示它仍必須被 guardrail，但不能再直接描述成 label corruption。
- `HB_RUN_LABEL=668 python scripts/auto_propose_fixes.py`：`#H_AUTO_TW_DRIFT` 仍存在，但 action wording 已改成 **保留 distribution-aware calibration guardrail，並檢查 recent feature variance / regime narrowness / calibration scope**。
- `python -m pytest tests/test_auto_propose_fixes.py -q` → **6 passed**。

### Blocker 升級 / 狀態更正
- **#H_AUTO_TW_DRIFT 仍未解除**：本輪修的是 blocker 判讀與治理契約，不是讓 TW-IC 立即回升；目前 TW-IC 仍是 **12/30**。
- **更精確的根因 framing**：現在已能排除「recent 100 rows 一定是 labels 壞掉」這種過度簡化敘事；真正待驗證的是 **真實單向極端口袋下的 recent feature variance / regime narrowness / calibration scope** 是否讓 TW-IC 被結構性稀釋。

## 📈 心跳 #667 摘要

### 本輪已驗證 patch
1. **Live guardrails now reduce risk at execution time, not just in calibration metadata**：`model/predictor.py` 新增 `_apply_live_execution_guardrails()`，把 `decision_quality_label` 與 `decision_quality_guardrail_applied` 轉成 runtime layer cap。當 live contract 只有 `C/D` 或 calibration 正處於 guardrailed state 時，`allowed_layers` 會直接從 raw profile 下修，避免 polluted-window diagnostics 只停留在 summary。
2. **Predictor probe now exposes the guardrail delta explicitly**：`scripts/hb_predict_probe.py` 新增 `allowed_layers_raw / execution_guardrail_applied / execution_guardrail_reason`，可以直接驗證 live path 是否真的把 guarded calibration 轉成更保守的部位控制。
3. **Regression tests lock the new execution-risk contract**：`tests/test_api_feature_history_and_predictor.py` 新增 execution guardrail tests，固定驗證 `C` quality + guardrailed calibration 會把 `allowed_layers` 從 2 層壓到 1 層。

### 本輪 runtime facts（Heartbeat #667）
- `python scripts/hb_parallel_runner.py --fast --hb 667`：**Raw 20492→20493 / Features 11921→11922 / Labels 40979→41005**；summary 已刷新 `data/heartbeat_667_summary.json`。
- Canonical freshness：240m `latest_target=2026-04-11 04:55:28.480906`、`raw_gap≈0.5h`；1440m `latest_target=2026-04-10 08:56:50.090685`、`raw_gap≈1.4h`，兩者皆仍屬 `expected_horizon_lag`。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（由 fast heartbeat 觸發）：Global **13/30 PASS**、TW-IC **13/30 PASS**；Regime IC **Bear 7/8 / Bull 8/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,240）。
- `python scripts/recent_drift_report.py`（由 fast heartbeat 觸發）：primary drift window 仍是 **last 100 rows**, `win_rate=1.0000`, `dominant_regime=chop(100%)`, alerts=`constant_target + regime_concentration`。
- `python scripts/hb_predict_probe.py`：`regime_label=chop`、`model_route_regime=chop`、`decision_quality_calibration_scope=regime_gate`、`decision_quality_sample_size=3933`、`decision_quality_label=C`，且 **`allowed_layers_raw=2 -> allowed_layers=1`、`execution_guardrail_applied=true`**。
- `python -m pytest tests/test_api_feature_history_and_predictor.py -q` → **12 passed**。

### Blocker 升級 / 狀態更正
- **#H_AUTO_TW_DRIFT 仍未解除**：本輪把 drift guardrail 真正接進 live execution sizing，但 recent 100/250 rows 的 `constant_target + 100% chop` 結構仍存在，TW-IC 只回升到 **13/30**，尚未跨過 14/30 gate。
- **沒有假進度**：這輪沒有宣稱 recent alpha 已修復；只是把 guardrail 從「會說風險」推進到「會真的縮層」。下一輪仍必須對準 recent canonical label / regime concentration 的根因。

## 📈 心跳 #666 摘要

### 本輪已驗證 patch
1. **Live decision-quality calibration no longer trusts an imbalanced scoped bucket just because the window itself was guardrailed**：`model/predictor.py::_summarize_decision_quality_contract()` 現在會在 dynamic-window guardrail 啟動時，拒絕 `constant_target / label_imbalance` 的窄 bucket，並自動回退到更廣的 calibration lane。
2. **Guardrail reasoning is now machine-readable in the probe/API contract**：predictor 新增 `decision_quality_scope_guardrail_applied / reason / alerts`，並把 scope-level rejection reason 合併進既有 `decision_quality_guardrail_reason`，避免 live API 再輸出看似精準、其實只是 chop-only polluted slice 的高勝率預期。
3. **Regression guard added for this calibration-scope fallback**：`tests/test_api_feature_history_and_predictor.py` 新增 imbalanced-bucket fallback test，鎖住 `regime_gate+entry_quality_label -> regime_gate` 的降級路徑。

### 本輪 runtime facts（Heartbeat #666）
- `python scripts/hb_parallel_runner.py --fast --hb 666`：**Raw 20490→20491 / Features 11919→11920 / Labels 40959→40979**；summary 已刷新 `data/heartbeat_666_summary.json`。
- Canonical freshness：240m `latest_target=2026-04-11 04:01:44.374503`、`raw_gap≈0.8h`；1440m `latest_target=2026-04-10 08:26:28.484426`、`raw_gap≈1.4h`，兩者皆仍屬 `expected_horizon_lag`。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（由 fast heartbeat 觸發）：Global **13/30 PASS**、TW-IC **12/30 PASS**；Regime IC **Bear 7/8 / Bull 8/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,216）。
- `python scripts/recent_drift_report.py`（由 fast heartbeat 觸發）：primary drift window 仍是 **last 100 rows**, `win_rate=1.0000`, `dominant_regime=chop(100%)`, alerts=`constant_target + regime_concentration`。
- `python scripts/hb_predict_probe.py`：`regime_label=chop`、`model_route_regime=chop`、`decision_quality_calibration_scope=regime_gate`、`decision_quality_sample_size=3933`、`expected_win_rate=0.7841`、`decision_quality_label=C`；guardrail reason 明示拒絕了原本 `regime_gate+entry_quality_label` 的 imbalanced bucket。
- `python -m pytest tests/test_api_feature_history_and_predictor.py -q` → **10 passed**。

### Blocker 升級 / 狀態更正
- **#H_AUTO_TW_DRIFT 仍未解除**：本輪修掉的是 live expectation contract 裡的 bucket-level 假樂觀，不是 recent 100-row constant-target 本身；TW-IC 仍是 **12/30**。
- **沒有假進度**：這輪沒有宣稱 recent alpha 恢復；只是把 live predictor 從「受污染 bucket 的 98.8% 預期」拉回更誠實的 `regime_gate` calibration。下一輪仍必須對準 recent canonical label 為何長時間維持 `100% win + 100% chop` 的根因。

## 📈 心跳 #665 摘要

### 本輪已驗證 patch
1. **TW-drift auto-propose now compares against numbered heartbeats instead of the anonymous `fast` alias**：`scripts/auto_propose_fixes.py::load_recent_tw_history()` 改為優先載入 `heartbeat_665 / 664 / 663 ...` 這種可追蹤的正式心跳，避免 `#H_AUTO_TW_DRIFT` 被寫成 `#665 -> #fast` 這種低訊號治理輸出。
2. **Regression guard added for the governance fix**：`tests/test_auto_propose_fixes.py` 新增 numbered-vs-fast 優先順序測試；`tests/test_hb_parallel_runner.py` 持續確保 fast summary contract 沒被破壞。
3. **Fast heartbeat re-run on fresh canonical data after the patch**：不是只修測試；`python scripts/hb_parallel_runner.py --fast --hb 665` 已重跑並把更新後的 auto-propose 輸出落地到 `issues.json` / `data/heartbeat_665_summary.json`。

### 本輪 runtime facts（Heartbeat #665）
- `python scripts/hb_parallel_runner.py --fast --hb 665`：**Raw 20473→20475 / Features 11902→11904 / Labels 40954→40959**；summary 已刷新 `data/heartbeat_665_summary.json`。
- Canonical freshness：240m `latest_target=2026-04-11 04:01:44.374503`、`raw_gap≈0.8h`；1440m `latest_target=2026-04-10 08:02:08.205395`、`raw_gap≈1.4h`，兩者皆仍屬 `expected_horizon_lag`。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（由 fast heartbeat 觸發）：Global **13/30 PASS**、TW-IC **12/30 PASS**；Regime IC **Bear 7/8 / Bull 8/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,196）。
- `python scripts/recent_drift_report.py`（由 fast heartbeat 觸發）：primary drift window 仍是 **last 100 rows**, `win_rate=1.0000`, `dominant_regime=chop(100%)`, alerts=`constant_target + regime_concentration`。
- `python scripts/hb_predict_probe.py`：`regime_label=chop`、`model_route_regime=chop`、`used_model=regime_chop_ensemble`、`decision_quality_calibration_window=5000`、`allowed_layers=2`。
- `python -m pytest tests/test_auto_propose_fixes.py tests/test_hb_parallel_runner.py -q` → **10 passed**。

### Blocker 升級 / 狀態更正
- **#H_AUTO_TW_DRIFT 治理訊號已校正，但根因未解除**：這輪修掉的是「auto-propose 用 `fast` alias 當歷史對照」的治理 bug；真 blocker 仍是 **recent 100-row canonical window = 100% win / 100% chop**，所以 TW-IC 依然只有 **12/30**，不能把本輪 patch 誤報成 signal 修復。
- **沒有假進度**：本輪沒有宣稱 recent alpha 恢復，只把 blocker 描述從 `#665 -> #fast` 修正成可追蹤的 `#665 -> #664 -> #663`。下一輪仍必須對準 recent-window constant-target / chop-concentration 的真正根因。

## 📈 心跳 #664 摘要

### 本輪已驗證 patch
1. **Training-side TW-IC weighting now consumes the same distribution guardrail as dynamic-window selection**：`model/train.py::load_training_data()` 會讀 `data/dw_result.json + data/recent_drift_report.json`，當 recent canonical window 出現 `constant_target / regime_concentration` 時，對 polluted tail 做 recent-window damping，而不是讓這段資料享有最大的 recency premium。
2. **TW-IC guardrail is now machine-readable instead of hidden inside training math**：`model/ic_signs.json` 新增 `tw_guardrail={recommended_best_n, raw_best_n, primary_window, damped_recent_rows, damp_factor, guardrail_reason}`，讓 heartbeat / debug / 後續訓練比較可以直接看到本輪 TW weighting 是否受 distribution guardrail 影響。
3. **Regression guard added for the new training-side policy**：`tests/test_train_target_metrics.py` 新增 `load_tw_ic_guardrail` 與 `build_time_decay_weights` tests，固定驗證 `dw_result + recent_drift_report` 會被讀入，且 polluted recent window 會被降權。

### 本輪 runtime facts（Heartbeat #664）
- `python scripts/hb_parallel_runner.py --fast --hb 664`：**Raw 20448→20449 / Features 11877→11878 / Labels 40893→40919**；summary 已落地 `data/heartbeat_664_summary.json`。
- Canonical freshness：240m `latest_target=2026-04-11 03:23:57.530990`、`raw_gap≈0.8h`；1440m `latest_target=2026-04-10 07:26:13.060925`、`raw_gap≈1.4h`，兩者皆仍屬 `expected_horizon_lag`。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（由 fast heartbeat 觸發）：Global **13/30 PASS**、TW-IC **11/30 PASS**；Regime IC **Bear 7/8 / Bull 8/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,159）。
- `python scripts/recent_drift_report.py`（由 fast heartbeat 觸發）：primary drift window 仍是 **last 100 rows**, `win_rate=1.0000`, `dominant_regime=chop(100%)`, alerts=`constant_target + regime_concentration`。
- `python -m pytest tests/test_train_target_metrics.py tests/test_dynamic_window_train.py tests/test_api_feature_history_and_predictor.py -q` → **15 passed**。

### Blocker 升級 / 狀態更正
- **#DYNAMIC_WINDOW_NOT_DISTRIBUTION_AWARE（本輪再收斂）**：guardrail 已從 dynamic-window report → live calibration → **training-side TW weighting** 三段串起來；剩餘真 blocker 不再是「policy 沒接上」，而是 **接上後 TW-IC 仍只有 11/30**，代表 recent true signal 仍弱。
- **沒有假進度**：本輪沒有宣稱 TW-IC 已恢復，只修掉「recent polluted slice 仍可主導 TW weighting」這個 root cause。下一輪若要宣稱 signal 改善，必須拿 retrain 後的 `model/ic_signs.json + last_metrics.json` 做前後對照。

## 📈 心跳 #663 摘要

### 本輪已驗證 patch
1. **Live decision-quality calibration now consumes the guardrailed recommended window instead of a hardcoded recent slice**：`model/predictor.py` 會讀 `data/dw_result.json`，用 `recommended_best_n` 當 calibration window，並對外輸出 `decision_quality_calibration_window / decision_quality_guardrail_applied / decision_quality_guardrail_reason`。
2. **Predictor routing and exposed decision contract now use the same regime label**：live route 不再用獨立 heuristic silently pick bear while API/probe 說 chop；`model_route_regime` 已加入 output，`used_model` 與 `regime_label` 現在一致。
3. **Regression guard added for both fixes**：`tests/test_api_feature_history_and_predictor.py` 新增 guardrail-window 與 regime-route consistency tests，避免之後再回退成 hardcoded 5000/heuristic-only routing。

### 本輪 runtime facts（Heartbeat #663）
- `python scripts/hb_parallel_runner.py --fast --hb 663`：**Raw 20430→20431 / Features 11859→11860 / Labels 40892→40893**；summary 已落地 `data/heartbeat_663_summary.json`。
- Canonical freshness：240m `latest_target=2026-04-11 02:55:43.292475`、`raw_gap≈0.8h`；1440m `latest_target=2026-04-10 05:49:15.768863`、`raw_gap≈1.4h`，兩者皆仍屬 `expected_horizon_lag`。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（由 fast heartbeat 觸發）：Global **13/30 PASS**、TW-IC **12/30 PASS**；Regime IC **Bear 7/8 / Bull 7/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,134）。
- `python scripts/hb_predict_probe.py`：`signal=ABSTAIN`、`used_model=regime_chop_abstain`、`regime_label=chop`、`model_route_regime=chop`、`decision_quality_calibration_scope=regime_gate`、`decision_quality_calibration_window=5000`、`decision_quality_guardrail_applied=true`。
- `python -m pytest tests/test_api_feature_history_and_predictor.py -q` → **9 passed**。

### Blocker 升級 / 狀態更正
- **#DYNAMIC_WINDOW_NOT_DISTRIBUTION_AWARE（本輪再收斂）**：guardrail 不再只停留在 `dynamic_window_train.py` 報表，而是已真正進入 live calibration contract。剩餘真 blocker 收斂到 **TW weighting / recency-heavy training path** 尚未消費同一 policy。
- **#LIVE_REGIME_ROUTE_MISMATCH（本輪已修）**：先前 probe 顯示 `used_model` 與 `regime_label` 語義分裂，現在已用 route/output 一致性 + regression test 關閉這個假語義來源。

## 📈 心跳 #662 摘要

### 本輪已驗證 patch
1. **Dynamic-window selection now consumes distribution-aware guardrails instead of treating polluted recent windows as valid calibration winners**：`scripts/dynamic_window_train.py` 會同時使用 local window distribution 與 `recent_drift_report.json`，輸出 `dominant_regime / alerts / distribution_guardrail`，並把 `constant_target` / `regime_concentration` 視窗排除在推薦 window 之外。
2. **The recommendation contract is now explicit and machine-readable**：`data/dw_result.json` 會同時保存 `raw_best_n` 與 `recommended_best_n`，外加 `guardrail_policy={disqualifying_alerts=['constant_target','regime_concentration']}`，避免 heartbeat 再把「IC pass 最多」錯當成「可安全拿來校準」。
3. **Regression guard added for the new policy**：新增 `tests/test_dynamic_window_train.py`，固定驗證 constant-target / regime-concentration 視窗會被 guardrail、external drift report 會覆寫 recommendation、且 raw best 與 recommended best 可被正確區分。

### 本輪 runtime facts（Heartbeat #662）
- `python scripts/hb_parallel_runner.py --fast --hb 662`：**Raw 20403→20404 / Features 11832→11833 / Labels 40890→40891**；summary 已落地 `data/heartbeat_662_summary.json`。
- Canonical freshness：240m `latest_target=2026-04-11 02:02:02.531985`、`raw_gap≈0.8h`；1440m `latest_target=2026-04-10 05:49:15.768863`、`raw_gap≈1.4h`，兩者皆仍屬 `expected_horizon_lag`。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（由 fast heartbeat 觸發）：Global **13/30 PASS**、TW-IC **12/30 PASS**；Regime IC **Bear 7/8 / Bull 7/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,134）。
- `python scripts/recent_drift_report.py`：last **100 / 250 rows = 100% simulated_pyramid_win=1 且 100% chop**；last **500 rows = 99.8% win_rate / 100% chop**；primary drift window 仍是 **100 rows** with alerts `constant_target + regime_concentration`。
- `python scripts/dynamic_window_train.py`：raw best **N=600 (6/8)**，但 **N=100/200/400/600/1000/2000** 全數被標成 distribution-guardrailed；新的 **recommended window = N=5000 (5/8, guardrail-safe)**。
- `pytest tests/test_dynamic_window_train.py tests/test_hb_parallel_runner.py tests/test_auto_propose_fixes.py -q` → **12 passed**。

### Blocker 升級 / 狀態更正
- **#DYNAMIC_WINDOW_NOT_DISTRIBUTION_AWARE（本輪真推進）**：不再只是在 heartbeat summary 裡提示 recent-window 污染，而是已把 guardrail 實際接進 dynamic-window 選窗邏輯，阻止 `constant_target / 100% chop` 視窗繼續被推薦成 calibration baseline。
- **剩餘真缺口**：guardrail 目前只落在 `dynamic_window_train.py`；live calibration / TW weighting 尚未直接使用這個 contract，因此 recent polluted windows 仍可能在其他 weighting path 造成過度樂觀 expectation。

## 📈 心跳 #661 摘要

### 本輪已驗證 patch
1. **Recent drift is now a first-class machine-readable heartbeat artifact**：新增 `scripts/recent_drift_report.py`，固定對 canonical 1440m `simulated_pyramid_win` 輸出 recent-window label balance / dominant regime / constant-target guardrail 到 `data/recent_drift_report.json`。
2. **Fast heartbeat summary now persists root-cause-ready drift diagnostics**：`scripts/hb_parallel_runner.py` 會在 full/regime IC 後自動執行 drift report，並把 `drift_diagnostics={primary_window, primary_alerts, primary_summary...}` 寫進 `data/heartbeat_661_summary.json`，讓後續心跳不用再從 stdout 猜 recent distribution。
3. **Auto-propose blocker now names the polluted window instead of only shouting about TW-IC**：`scripts/auto_propose_fixes.py` 會讀 `recent_drift_report.json`，把 `recent_window=100, alerts=['constant_target','regime_concentration'], dominant_regime=chop(100.00%)` 直接帶進 `#H_AUTO_TW_DRIFT` action，讓下一輪 patch 可以直接對準 recent-window constant-target / chop concentration。

### 本輪 runtime facts（Heartbeat #661）
- `python scripts/hb_parallel_runner.py --fast --hb 661`：**Raw 20393→20394 / Features 11822→11823 / Labels 40890→40890**；summary 已落地 `data/heartbeat_661_summary.json`。
- Canonical freshness：240m `latest_target=2026-04-11 01:32:18.956763`、`raw_gap≈0.8h`；1440m `latest_target=2026-04-10 05:49:15.768863`、`raw_gap≈1.4h`，兩者皆仍屬 `expected_horizon_lag`。
- Continuity telemetry：`bridge_inserted=0`、`used_bridge=false`；raw continuity 保持乾淨。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（由 fast heartbeat 觸發）：Global **13/30 PASS**、TW-IC **12/30 PASS**；Regime IC **Bear 7/8 / Bull 7/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,134）。
- `python scripts/recent_drift_report.py`：full sample `win_rate=0.6419`、regime mix `chop=85.19%`；**last 100 / 250 rows = 100% simulated_pyramid_win=1 且 100% chop**，last 500 rows = `win_rate=0.9980` / `dominant_regime=chop(100%)`；primary drift window = **100 rows** with alerts `constant_target + regime_concentration`。
- `pytest tests/test_hb_parallel_runner.py tests/test_auto_propose_fixes.py -q` → **9 passed**。

### Blocker 升級 / 狀態更正
- **#DYNAMIC_WINDOW_NOT_DISTRIBUTION_AWARE（本輪真推進）**：不再只是說「TW-IC 持續低」，而是已定位到 recent canonical slice 本身變成 **constant-target + chop-concentrated**。這讓下一輪可以直接把 dynamic-window / calibration guardrail 做成行為，而不是繼續討論抽象 drift。
- **#LOW_COVERAGE_SOURCES（持續真 blocker）**：這輪修的是 heartbeat drift 治理，不是 sparse-source 歷史補齊；blocked features 仍是 **8**，`fin_netflow` 仍受 `COINGLASS_API_KEY` 缺失阻擋。

## 📈 心跳 #659 摘要

### 本輪已驗證 patch
1. **Fast heartbeat now persists machine-readable IC diagnostics and auto-propose output**：`scripts/hb_parallel_runner.py` 新增 `ic_diagnostics` 與 `auto_propose` summary fields，並在 heartbeat 結尾直接執行 `scripts/auto_propose_fixes.py`；`data/heartbeat_658_summary.json` / `data/heartbeat_659_summary.json` 已能直接被後續心跳解析，不必再從 `stdout_preview` 猜 TW-IC。
2. **Auto-propose no longer relies on legacy target semantics**：`scripts/auto_propose_fixes.py` 改為讀 canonical `simulated_pyramid_win` + `data/full_ic_result.json`，不再用 `label_spot_long_win/sell_win` 來決定主 blocker；同時新增 `HB_RUN_LABEL` current-entry path，讓本輪 heartbeat 還沒先寫 summary 時，也能拿 current `TW-IC` 與上一輪 summary 做連續判斷。
3. **TW-IC decay is now an auto-escalated blocker instead of a markdown-only warning**：`HB_RUN_LABEL=660 python scripts/auto_propose_fixes.py` 已實際產生 `#H_AUTO_TW_DRIFT: TW-IC 連續低於 14/30：#660=11/30 -> #659=11/30`，證明心跳 runner 已具備「同一問題連兩輪惡化就升級 blocker」的閉環機制。

### 本輪 runtime facts（Heartbeat #659）
- `python scripts/hb_parallel_runner.py --fast --hb 659`：**Raw 20391→20392 / Features 11820→11821 / Labels 40882→40882**；summary 已落地 `data/heartbeat_659_summary.json`，內含 `ic_diagnostics={global_pass:13, tw_pass:11, total_features:30}` 與 `auto_propose` preview。
- Canonical freshness：240m `latest_target=2026-04-11 00:59:05.983262`、`raw_gap≈0.5h`；1440m `latest_target=2026-04-10 04:53:08.901581`、`raw_gap≈1.4h`，兩者皆仍屬 `expected_horizon_lag`。
- Continuity telemetry：`bridge_inserted=0`、`used_bridge=false`；raw continuity 保持乾淨。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（由 fast heartbeat 觸發）：Global **13/30 PASS**、TW-IC **11/30 PASS**；Regime IC **Bear 7/8 / Bull 7/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,128）。
- `python -m pytest tests/test_frontend_decision_contract.py tests/test_api_feature_history_and_predictor.py tests/test_hb_parallel_runner.py tests/test_auto_propose_fixes.py -q` → **18 passed**；`cd web && npm run build` ✅。

### Blocker 升級 / 狀態更正
- **TW-IC decay 不再只是 markdown 提醒**：Heartbeat #659 已把「連續低於 14/30 就升級 blocker」真正落到 runner + summary + auto-propose；下一輪若 recent-window drift 仍存在，issue 會直接 machine-readable 地浮到 `issues.json` / summary，而不是被新一輪 heartbeat 敘事沖掉。
- **#DECISION_QUALITY_GAP 無假改善**：本輪沒有再碰 Dashboard / Strategy Lab / Backtest contract，本次推進點是 heartbeat 治理閉環。UI/API canonical semantics 仍維持前一輪狀態，未被這輪 patch 破壞。

## 📈 心跳 #656 摘要

### 本輪已驗證 patch
1. **Dashboard 4H structure panel no longer pretends hand-written bias rules are the primary trading decision**：`web/src/pages/Dashboard.tsx` 把原本直接輸出「接近支撐即可 Layer 3」這種手寫文案降級成 `結構背景`，並固定先顯示 live `regime_gate + entry_quality + allowed_layers`，讓首頁這張卡也回到 canonical decision-quality contract。
2. **Dashboard now explicitly warns when raw 4H context and canonical gate diverge**：同卡新增 `若 4H raw 結構與 canonical gate 不一致，應以 decision-quality contract 為主`，避免使用者在首頁同時看到兩套互相衝突的進場語義。
3. **Regression guard widened to cover the 4H structure card contract**：`tests/test_frontend_decision_contract.py` 現在會檢查 Dashboard source 內存在 `主決策以 live decision-quality contract 為準`、`const canonicalGate = confidenceData?.regime_gate || ...` 與衝突警告文案，避免之後又把手寫 bias action copy 偷放回首頁主決策路徑。

### 本輪 runtime facts（Heartbeat #656）
- `python scripts/hb_parallel_runner.py --fast --hb 656`：**Raw 20388→20389 / Features 11817→11818 / Labels 40867→40873**；summary 已落地 `data/heartbeat_656_summary.json`。
- Canonical freshness：240m `latest_target=2026-04-11 00:03:29.073765`、`raw_gap≈0.5h`；1440m `latest_target=2026-04-10 04:09:04.046442`、`raw_gap≈1.4h`，兩者皆仍屬 `expected_horizon_lag`。
- Continuity telemetry：`bridge_inserted=0`、`used_bridge=false`；raw continuity 保持乾淨。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（由 fast heartbeat 觸發）：Global **13/30 PASS**、TW-IC **12/30 PASS**；Regime IC **Bear 7/8 / Bull 7/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,121）。
- `python -m pytest tests/test_frontend_decision_contract.py tests/test_api_feature_history_and_predictor.py -q` → **11 passed**；`cd web && npm run build` ✅。

### Blocker 升級 / 狀態更正
- **#DECISION_QUALITY_GAP（本輪再收斂）**：不能只修排行榜與明細頁，首頁仍有手寫 bias→action copy 也算 contract 漏接。這輪已把 Dashboard 4H 結構卡收回到 canonical live contract 下；剩餘真 gap 收斂到 Dashboard 其他 legacy summary 卡與未來新增 compare surfaces。
- **TW-IC 回落（持續監控，未升級為 blocker）**：本輪 TW-IC 仍是 **12/30**。global/regime canonical path 仍健康，但 recent-weighted 優勢未回升；若再連 1 輪低於 14/30，下一輪必須升級為 distribution-aware / calibration drift 調查。

## 📈 心跳 #655 摘要

### 本輪已驗證 patch
1. **Strategy Lab now treats legacy execution KPIs as secondary instead of silent primary copy**：`web/src/pages/StrategyLab.tsx` 把 ROI / 勝率 / PF 卡明確降級成 **Legacy execution metrics（僅輔助 / tie-breaker）**，避免 active summary 把 legacy 指標和 canonical DQ 摘要混成同級主語義。
2. **Canonical fallback is now explicit and test-guarded**：`describeRankingReason()` / `describeStrategyRankingReason()` 不再默默退回 `ROI · 勝率` 文案；若 DQ 欄位缺失，UI 會顯示 `⚠️ canonical DQ 缺失，暫退回 legacy ROI...`，並由 `tests/test_frontend_decision_contract.py` 固定鎖住這個警告與 tie-breaker 標示，避免 future compare surface 再把 fallback 偽裝成正常 contract。
3. **Closed-loop heartbeat re-verified on fresh canonical data**：`python scripts/hb_parallel_runner.py --fast --hb 655` 成功推進 **Raw 20387→20388 / Features 11816→11817 / Labels 40853→40867**；`simulated_pyramid_win` DB overall 升至 **57.46%**。

### 本輪 runtime facts（Heartbeat #655）
- `python scripts/hb_parallel_runner.py --fast --hb 655`：**Raw 20387→20388 / Features 11816→11817 / Labels 40853→40867**；summary 已落地 `data/heartbeat_655_summary.json`。
- Canonical freshness：240m `latest_target=2026-04-10 23:35:42.751820`、`raw_gap≈0.5h`；1440m `latest_target=2026-04-10 03:44:23.283251`、`raw_gap≈1.4h`，兩者皆仍屬 `expected_horizon_lag`。
- Continuity telemetry：`bridge_inserted=0`、`used_bridge=false`；raw continuity 保持乾淨。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（由 fast heartbeat 觸發）：Global **13/30 PASS**、TW-IC **12/30 PASS**；Regime IC **Bear 7/8 / Bull 7/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,116）。
- `python -m pytest tests/test_frontend_decision_contract.py tests/test_api_feature_history_and_predictor.py -q` → **11 passed**；`cd web && npm run build` ✅。

### Blocker 升級 / 狀態更正
- **#DECISION_QUALITY_GAP（本輪再收斂）**：不能只驗證 route 可達或欄位存在，還要防止 UI 把 canonical fallback 包裝成正常摘要。這輪已把 Strategy Lab 的 legacy fallback 顯式警告化並加 regression guard；剩餘真 gap 進一步收斂到 Dashboard 其他 legacy summary 卡與未來新增 compare surfaces。
- **TW-IC 回落（持續監控，未升級為 blocker）**：本輪 TW-IC 從前輪 **13/30 → 12/30**。目前 global/regime canonical path 仍健康，但 recent-weighted 優勢繼續轉弱；若再連 1 輪低於 14/30，下一輪必須升級為 distribution-aware / calibration drift 調查。

## 📈 心跳 #654 摘要

### 本輪已驗證 patch
1. **Frontend decision-quality regression guard added**：新增 `tests/test_frontend_decision_contract.py`，直接鎖住 `web/src/App.tsx` 的 `/backtest` nav/route contract，以及 Dashboard / Backtest / StrategyLab 三個主要 surface 的 canonical decision-quality wiring，避免 route 可達性或 DQ 欄位再次悄悄退回 legacy 文案。
2. **Route-level false-complete risk closed**：不再只靠人工 browser smoke check 才知道 `/backtest` 有沒有被 router 遮掉；pytest 現在會明確驗證 nav 含 `🔬 回測引擎`、`<Route path="/backtest" element={<Backtest />} />` 存在、且 source 中沒有 `Navigate to="/lab"` 這類舊 redirect。
3. **Closed-loop heartbeat re-verified on fresh canonical data**：`python scripts/hb_parallel_runner.py --fast --hb 654` 成功推進 **Raw 20386→20387 / Features 11815→11816 / Labels 40824→40853**；`simulated_pyramid_win` DB overall 升至 **57.43%**。

### 本輪 runtime facts（Heartbeat #654）
- `python scripts/hb_parallel_runner.py --fast --hb 654`：**Raw 20386→20387 / Features 11815→11816 / Labels 40824→40853**；summary 已落地 `data/heartbeat_654_summary.json`。
- Canonical freshness：240m `latest_target=2026-04-10 22:46:45.648886`、`raw_gap≈0.8h`；1440m `latest_target=2026-04-10 03:28:06.561826`、`raw_gap≈1.4h`，兩者皆仍屬 `expected_horizon_lag`。
- Continuity telemetry：`bridge_inserted=0`、`used_bridge=false`；raw continuity 保持乾淨。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（由 fast heartbeat 觸發）：Global **13/30 PASS**、TW-IC **13/30 PASS**；Regime IC **Bear 7/8 / Bull 7/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,103）。
- `python -m pytest tests/test_frontend_decision_contract.py tests/test_api_feature_history_and_predictor.py -q` → **11 passed**；`cd web && npm run build` ✅；browser `/backtest` runtime check ✅。

### Blocker 升級 / 狀態更正
- **#DECISION_QUALITY_GAP（本輪再收斂）**：不能再把 `/backtest` 的可達性與 canonical surface wiring 只留在口頭或人工 smoke check。這輪已把 route/nav + Dashboard/Backtest/StrategyLab 的核心 DQ fields 鎖進 regression test；剩餘真 gap 收斂到 Dashboard 其他 legacy summary 卡與未來新增 compare surfaces。
- **TW-IC 回落（新監控項，未升級為 blocker）**：本輪 TW-IC 從前輪 16/30 回落到 **13/30**。目前仍未影響 global/regime canonical path，但 recent-weighted 優勢顯著轉弱；若連續 2 輪維持低於 14/30，需升級為 distribution-aware / calibration drift 調查，而不是繼續沿用同一套近期優勢敘事。

## 📈 心跳 #653 摘要

### 本輪已驗證 patch
1. **Canonical Backtest page is reachable for real, not just implemented in source**：`web/src/App.tsx` 改為直接掛載 `Backtest` page 到 `/backtest`，移除舊的 `Navigate to="/lab"`，並把 `🔬 回測引擎` 加回頂部 nav，修掉「頁面內容已升級但 router 還在遮住它」的 root cause。
2. **Standalone Backtest decision-quality surface verified end-to-end**：browser 直接開 `http://127.0.0.1:5173/backtest` 可看到 canonical DQ 摘要、`simulated_pyramid_win` contract 與 trade log 的 `gate / entry quality / allowed layers` 欄位，證明使用者真的能到達 #652 修好的 surface，而不是只存在於 code。
3. **Closed-loop heartbeat re-verified on fresh canonical data**：`python scripts/hb_parallel_runner.py --fast --hb 653` 成功推進 **Raw 20385→20386 / Features 11814→11815 / Labels 40787→40824**；`simulated_pyramid_win` DB overall 升至 **57.38%**。

### 本輪 runtime facts（Heartbeat #653）
- `python scripts/hb_parallel_runner.py --fast --hb 653`：**Raw 20385→20386 / Features 11814→11815 / Labels 40787→40824**；summary 已落地 `data/heartbeat_653_summary.json`。
- Canonical freshness：240m `latest_target=2026-04-10 22:46:45.648886`、`raw_gap≈0.8h`；1440m `latest_target=2026-04-10 03:01:19.250806`、`raw_gap≈1.4h`，兩者皆仍屬 `expected_horizon_lag`。
- Continuity telemetry：`bridge_inserted=0`、`used_bridge=false`；raw continuity 保持乾淨。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（由 fast heartbeat 觸發）：Global **13/30 PASS**、TW-IC **16/30 PASS**；Regime IC **Bear 7/8 / Bull 7/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,074）。
- `python -m pytest tests/test_api_feature_history_and_predictor.py -q` → **7 passed**；`cd web && npm run build` ✅；browser `/backtest` runtime check ✅。

### Blocker 升級 / 狀態更正
- **#DECISION_QUALITY_GAP（本輪再收斂）**：不能再說 standalone Backtest page 已完成就代表使用者可用。真正的 root cause 是 router 仍把 `/backtest` 導回 `/lab`；這輪已修掉，因此 canonical Backtest surface 現在在 source、build、runtime 三層都成立。剩餘真缺口收斂到 Dashboard 其他 legacy summary 卡與未來新增 compare surfaces。
- **#LOW_COVERAGE_SOURCES（持續真 blocker）**：這輪修的是 UI route/accessibility，不是 sparse-source historical backfill；blocked features 仍是 **8**，`fin_netflow` 仍受 `COINGLASS_API_KEY` 缺失阻擋。

## 📈 心跳 #652 摘要

### 本輪已驗證 patch
1. **Standalone Backtest page now shares the same canonical decision-quality contract as Dashboard / Strategy Lab**：`web/src/pages/Backtest.tsx` 改為直接復用 `BacktestSummary`，顯示 `decision_contract / avg_decision_quality_score / avg_expected_win_rate / avg_expected_pyramid_quality / avg_expected_drawdown_penalty / avg_expected_time_underwater / avg_entry_quality / avg_allowed_layers / dominant_regime_gate`，不再只剩 ROI / 勝率 / PF 的 legacy 摘要。
2. **Backtest trade log no longer drops entry semantics on the floor**：同頁交易表改為顯示 `entry_timestamp / regime_gate / entry_quality_label / entry_quality / allowed_layers / exit reason`，讓使用者可以直接看到每筆回測交易是在什麼 gate / quality 條件下進場，不再退回成只有價格 / 數量 / PnL 的舊表格。
3. **Closed-loop heartbeat re-verified on fresh canonical data**：`python scripts/hb_parallel_runner.py --fast` 成功推進 **Raw 20384→20385 / Features 11813→11814 / Labels 40780→40787**；`simulated_pyramid_win` DB overall 維持 **57.31%**，且 `TW-IC` 小幅升至 **17/30**。

### 本輪 runtime facts（Heartbeat #652）
- `python scripts/hb_parallel_runner.py --fast`：**Raw 20384→20385 / Features 11813→11814 / Labels 40780→40787**；summary 已刷新 `data/heartbeat_fast_summary.json`。
- Canonical freshness：240m `latest_target=2026-04-10 21:46:45.648886`、`raw_gap≈1.0h`；1440m `latest_target=2026-04-10 02:32:04.603100`、`raw_gap≈1.4h`，兩者皆仍屬 `expected_horizon_lag`。
- Continuity telemetry：`bridge_inserted=0`、`used_bridge=false`；raw continuity 保持乾淨。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（由 fast heartbeat 觸發）：Global **13/30 PASS**、TW-IC **17/30 PASS**；Regime IC **Bear 7/8 / Bull 6/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,038）。
- `python -m pytest tests/test_api_feature_history_and_predictor.py -q` → **7 passed**；`cd web && npm run build` ✅。

### Blocker 升級 / 狀態更正
- **#DECISION_QUALITY_GAP（本輪再收斂）**：不能再說 standalone Backtest 頁仍停在 ROI-only。現在 Dashboard live card、Dashboard backtest card、Strategy Lab 主表/詳情/compare，以及 standalone Backtest page 都共享 canonical decision-quality contract；剩餘真缺口收斂到 Dashboard 其他 legacy summary 卡與未來新增 compare surfaces。
- **#LOW_COVERAGE_SOURCES（持續真 blocker）**：這輪修的是回測頁語義，不是 sparse-source historical backfill；blocked features 仍是 **8**。

## 📈 心跳 #651 摘要

### 本輪已驗證 patch
1. **`/api/backtest` no longer runs on legacy 5-sense aliases only**：`server/routes/api.py::api_backtest()` 改為直接使用 canonical core features (`feat_eye`~`feat_mind`) + `phase16_baseline_v2` live decision profile，並把每筆回測 trade 附上 `entry_timestamp / regime_gate / entry_quality / entry_quality_label / allowed_layers`。
2. **Backtest API now emits canonical decision-quality contract**：回測 response 新增 `decision_contract`、`avg_expected_win_rate`、`avg_expected_pyramid_quality`、`avg_expected_drawdown_penalty`、`avg_expected_time_underwater`、`avg_decision_quality_score`、`decision_quality_label`、`decision_quality_sample_size`、`avg_entry_quality`、`avg_allowed_layers`、`dominant_regime_gate`，讓 Dashboard 回測卡不再停留在 ROI / 勝率 / PF-only summary。
3. **Dashboard BacktestSummary switched to canonical semantics**：`web/src/components/BacktestSummary.tsx` 與 `web/src/pages/Dashboard.tsx` 現在直接顯示 `simulated_pyramid_win` contract、DQ、預期勝率、回撤懲罰、深套時間、平均 entry quality 與平均 layers，讓首頁回測區與 predictor / Strategy Lab contract 對齊。
4. **Regression guard added**：`tests/test_api_feature_history_and_predictor.py` 新增 `/api/backtest` regression test，確認 route 在只有 canonical features 的情況下也能回傳 decision-quality payload，防止再默默依賴 `feat_eye_dist` 等 legacy-only 路徑。

### 本輪 runtime facts（Heartbeat #651）
- `python scripts/hb_parallel_runner.py --fast`：**Raw 20383→20384 / Features 11812→11813 / Labels 40780→40780**；summary 已刷新 `data/heartbeat_fast_summary.json`。
- Canonical freshness：240m `latest_target=2026-04-10 21:46:45.648886`、`raw_gap≈1.0h`；1440m `latest_target=2026-04-10 01:00:00`、`raw_gap≈1.4h`，兩者皆仍屬 `expected_horizon_lag`。
- Continuity telemetry：本輪 `bridge_inserted=0`、`used_bridge=false`；raw continuity 保持乾淨。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（由 fast heartbeat 觸發）：Global **13/30 PASS**、TW-IC **16/30 PASS**；Regime IC **Bear 7/8 / Bull 6/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,031）。
- `python -m pytest tests/test_api_feature_history_and_predictor.py -q` → **7 passed**；`cd web && npm run build` ✅。

### Blocker 升級 / 狀態更正
- **#DECISION_QUALITY_GAP（本輪再收斂）**：不能再說 Dashboard 回測卡仍只看 ROI/PF。現在 predictor live card、Strategy Lab summaries、side-by-side compare、以及 Dashboard backtest summary 都共享 canonical decision-quality contract；剩餘真缺口縮到 Dashboard 其他 legacy summary 卡與未來新增 compare surfaces。
- **#LOW_COVERAGE_SOURCES（持續真 blocker）**：這輪修的是 backtest/API/UI 語義，不是 sparse-source historical backfill；blocked features 仍是 **8**。

## 📈 心跳 #650 摘要

### 本輪已驗證 patch
1. **Dashboard confidence card now uses canonical decision-quality semantics**：`web/src/components/ConfidenceIndicator.tsx` 不再沿用舊的做空/SELL copy，改成直接顯示 `4H Gate / Entry Quality / Allowed Layers / 預期勝率 / DQ / 回撤懲罰 / 深套時間 / 校準樣本`，把 homepage live card 與 `/predict/confidence` 的 `phase16_baseline_v2` contract 對齊。
2. **Dashboard data contract widened instead of dropping canonical fields on the floor**：`web/src/pages/Dashboard.tsx` 的 `ConfidenceData` 型別與 props 轉接已補齊 `regime_gate / entry_quality / allowed_layers / decision_quality_* / expected_*`，避免 API 已有 canonical 欄位、首頁 UI 卻只顯示舊 binary confidence 的語義掉鏈。
3. **Closed-loop heartbeat re-verified on fresh canonical data**：`python scripts/hb_parallel_runner.py --fast` 成功推進 **Raw 20381→20382 / Features 11810→11811 / Labels 40779→40779**；continuity repair `bridge=0`，`simulated_pyramid_win` DB overall 維持 **57.30%**。

### 本輪 runtime facts（Heartbeat #650）
- `python scripts/hb_parallel_runner.py --fast`：**Raw 20381→20382 / Features 11810→11811 / Labels 40779→40779**；`data/heartbeat_fast_summary.json` 已刷新。
- Canonical freshness：240m `latest_target=2026-04-10 20:46:45.648886`、`raw_gap≈1.0h`；1440m `latest_target=2026-04-10 01:00:00`、`raw_gap≈1.4h`，兩者皆屬 `expected_horizon_lag`。
- Continuity telemetry：本輪 `bridge_inserted=0`、`used_bridge=false`，比 #649 更乾淨，暫未升級 continuity blocker。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（由 fast heartbeat 觸發）：Global **13/30 PASS**、TW-IC **16/30 PASS**；Regime IC **Bear 7/8 / Bull 6/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,031）。
- `python -m pytest tests/test_api_feature_history_and_predictor.py -q` → **6 passed**；`cd web && npm run build` ✅。
- Source blocker 狀態沒有假改善：仍是 **8 blocked sparse features**；`fin_netflow` 仍為 `auth_missing`，Claw / Fin / Fang / Nest / Scales 依舊受 archive/history blocker 限制。

### Blocker 升級 / 狀態更正
- **#DECISION_QUALITY_GAP（本輪再收斂）**：不能再說 Dashboard live card 還停留在舊二元 confidence/做空語義。首頁 `ConfidenceIndicator` 現在已與 predictor/API contract 對齊，剩餘真缺口縮到 Dashboard 其他 legacy summary 卡與未來新增 compare surfaces。
- **#LOW_COVERAGE_SOURCES（持續真 blocker）**：這輪修的是 homepage decision-quality 語義，不是 sparse-source historical backfill；blocked features 仍是 8 個。

## 📈 心跳 #649 摘要

### 本輪已驗證 patch
1. **Strategy Lab side-by-side compare flow now uses canonical decision-quality semantics**：`web/src/pages/StrategyLab.tsx` 新增「策略並排比較」區塊，固定比較 **目前聚焦策略 vs 另一個已儲存策略** 的 `DQ / expected win rate / drawdown penalty / time underwater / allowed layers / ROI`，並顯示各自 `decision_contract.sort_semantics`，避免 compare flow 又退回成 ROI-only 對照。
2. **Compare panel stays aligned with the same contract as leaderboard/detail/run**：compare cards直接復用 `selectedStrategy.decision_contract`、`last_results.avg_decision_quality_score` 與 canonical ranking reason，讓 Strategy Lab 的排行榜、active summary、detail payload 與 compare panel 共用同一套 decision-quality 語義。
3. **Closed-loop heartbeat re-verified on fresh canonical data**：`python scripts/hb_parallel_runner.py --fast` 成功推進 **Raw 20378→20381 / Features 11807→11810 / Labels 40772→40779**；`simulated_pyramid_win` DB overall 維持 **57.30%**，並輸出 `data/heartbeat_fast_summary.json`（含 `bridge_fallback_streak=1` telemetry）。

### 本輪 runtime facts（Heartbeat #649）
- `python scripts/hb_parallel_runner.py --fast`：**Raw 20378→20381 / Features 11807→11810 / Labels 40772→40779**；summary 已落地 `data/heartbeat_fast_summary.json`。
- Canonical freshness：240m `latest_target=2026-04-10 20:46:45.648886`、`raw_gap≈1.0h`；1440m `latest_target=2026-04-10 01:00:00`、`raw_gap≈1.45h`，兩者皆仍屬 `expected_horizon_lag`。
- Continuity telemetry：本輪 `bridge_inserted=2`、`used_bridge=true`、`bridge_fallback_streak=1`；這代表 raw continuity 仍健康，但 bridge workaround 又被啟動一次，若連續升高需重新升級為 collector continuity root-cause investigation。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（由 fast heartbeat 觸發）：Global **13/30 PASS**、TW-IC **16/30 PASS**；Regime IC **Bear 7/8 / Bull 6/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,031）。
- `python scripts/hb_predict_probe.py`：`target_col=simulated_pyramid_win`、`decision_profile_version=phase16_baseline_v2`、`decision_quality_score=0.5515 (B)`、`expected_win_rate=98.73%`、`expected_drawdown_penalty=9.77%`、`expected_time_underwater=31.13%`；4H features / lags 皆為 **10/10 non-null**。
- `cd web && npm run build` ✅。
- Source blocker 狀態沒有假改善：仍是 **8 blocked sparse features**；`fin_netflow` 仍為 `auth_missing`，Claw / Fin / Fang / Nest / Scales 依舊受 historical archive gap 限制。

### Blocker 升級 / 狀態更正
- **#DECISION_QUALITY_GAP（本輪再收斂）**：不能再說 Strategy Lab compare flow 仍只看 ROI。現在排行榜、詳情、active summary 與 side-by-side compare 都直接顯示 canonical DQ / expected win / DD-UW 語義；剩餘真缺口縮到更廣的 Dashboard 其他摘要卡與可能未來新增的 compare surfaces。
- **Continuity bridge fallback（新觀察，未升級）**：雖然本輪 fresh data 有前進，但 `bridge_inserted=2` + `streak=1` 提醒我們近期 raw continuity 仍不完全穩定。若下一輪連續再觸發，必須升級成 source-level continuity 調查，而不是把 bridge workaround 當成已解決。
- **#LOW_COVERAGE_SOURCES（持續真 blocker）**：這輪修的是 compare contract，不是 sparse-source history；blocked features 仍是 8 個。

## 📈 心跳 #648 摘要

### 本輪已驗證 patch
1. **Dashboard radar now surfaces maturity summary instead of hiding score semantics**：`web/src/pages/Dashboard.tsx` 現在會額外抓 `/api/features/coverage?days=30`，在雷達卡上直接顯示 `核心 / 研究 / 阻塞` 計數，並明講雷達保留 research / blocked overlays 供觀察，避免使用者把所有線條都誤解成可同權進主決策。
2. **AdviceCard now carries the same maturity contract as FeatureChart**：`web/src/components/AdviceCard.tsx` 新增成熟度 badge 與說明，提醒主建議卡應優先解讀核心訊號，而 research / blocked features 只用於觀察與排障，正式把 #CORE_VS_RESEARCH_SIGNAL_MIXING 推進到首頁主決策區。
3. **Closed-loop heartbeat kept green on fresh canonical data**：`python scripts/hb_parallel_runner.py --fast --hb 648` 成功推進 **Raw 20377→20378 / Features 11806→11807 / Labels 40766→40772**，`simulated_pyramid_win` DB overall 維持 **57.3%**，並輸出 `data/heartbeat_648_summary.json`。

### 本輪 runtime facts（Heartbeat #648）
- `python scripts/hb_parallel_runner.py --fast --hb 648`：**Raw 20377→20378 / Features 11806→11807 / Labels 40766→40772**；summary 已落地 `data/heartbeat_648_summary.json`。
- Canonical freshness：240m `latest_target=2026-04-10 20:07:57.973491`、`raw_gap≈2.8h`；1440m `latest_target=2026-04-10 00:00:00`、`raw_gap≈2.8h`，兩者皆仍屬 `expected_horizon_lag`。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（由 fast heartbeat 觸發）：Global **13/30 PASS**、TW-IC **16/30 PASS**；Regime IC **Bear 7/8 / Bull 6/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,029）。
- `python -m pytest tests/test_api_feature_history_and_predictor.py tests/test_feature_history_policy.py -q` → **13 passed**；`cd web && npm run build` ✅。
- Source blocker 狀態沒有假改善：仍是 **8 blocked sparse features**；`fin_netflow` 仍為 `auth_missing`，Claw / Claw intensity / Fin 依舊受 `COINGLASS_API_KEY` 缺失阻擋。

### Blocker 升級 / 狀態更正
- **#CORE_VS_RESEARCH_SIGNAL_MIXING（本輪再推進）**：不能再說成熟度語義只停在 FeatureChart。Dashboard 雷達與 AdviceCard 已直接暴露 `核心 / 研究 / 阻塞` 摘要；剩餘真缺口是 Dashboard 其他摘要卡與 Strategy Lab compare flow 尚未共用同一層 maturity contract。
- **#LOW_COVERAGE_SOURCES（持續真 blocker）**：這輪修的是 UI 決策語義，不是 sparse-source historical backfill；blocked features 仍是 **8**。

## 📈 心跳 #647 摘要

### 本輪已驗證 patch
1. **Coverage/API now exposes feature maturity semantics**：`feature_history_policy.py` 與 `/api/features/coverage` 新增 `maturity_tier + maturity_label + score_usable + maturity_counts`，把 feature 正式分成 `core / research / blocked`，不再讓 sparse-source readiness 只停在 quality_flag。
2. **FeatureChart composite score no longer mixes sparse research overlays into canonical score**：`web/src/components/FeatureChart.tsx` 現在只用 `score_usable=true` 的核心訊號計算綜合分數；research sparse-source 仍可視覺觀察，但不再稀釋主分數與進/減碼訊號。
3. **UI now surfaces maturity badges and summary counts**：FeatureChart legend 顯示 `核心 / 研究 / 阻塞` badge，並在圖表上方直接提示「綜合分數只採用核心 decision signals」，把 #CORE_VS_RESEARCH_SIGNAL_MIXING 從抽象文件條目推到實際 UI contract。

### 本輪 runtime facts（Heartbeat #647）
- `python scripts/hb_parallel_runner.py --fast --hb 647`：**Raw 20376→20377 / Features 11805→11806 / Labels 40766→40766**；summary 已落地 `data/heartbeat_647_summary.json`。
- Canonical freshness：240m `latest_target=2026-04-10 17:21:47.280547`、`raw_gap≈0.7h`；1440m `latest_target=2026-04-09 21:00:00`、`raw_gap≈1.4h`，兩者皆仍屬 `expected_horizon_lag`。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（由 fast heartbeat 觸發）：Global **13/30 PASS**、TW-IC **16/30 PASS**；Regime IC **Bear 7/8 / Bull 6/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,027）。
- `python -m pytest tests/test_strategy_lab.py tests/test_model_leaderboard.py tests/test_hb_collect.py tests/test_api_feature_history_and_predictor.py tests/test_feature_history_policy.py -q` → **44 passed**；`cd web && npm run build` ✅。

### Blocker 升級 / 狀態更正
- **#CORE_VS_RESEARCH_SIGNAL_MIXING（本輪實際推進）**：不能再說 UI 完全沒有 maturity-aware contract。FeatureChart 的 legend / score path 已正式分出 core vs research vs blocked；剩餘缺口是 Dashboard 雷達/建議卡也尚未同步採用同一層 maturity summary。
- **#LOW_COVERAGE_SOURCES（持續真 blocker）**：這輪修的是語義分層，不是 sparse-source 歷史補齊；blocked features 仍是 **8**，`fin_netflow` 仍受 `COINGLASS_API_KEY` 缺失阻擋。

## 📈 心跳 #645 摘要

### 本輪已驗證 patch
1. **Strategy detail / run payloads now carry canonical decision-contract metadata**：`server/routes/api.py` 新增 `_strategy_decision_contract_meta()`，`_decorate_strategy_entry()`、`/api/strategies/{name}` 與 `/api/strategies/run` 現在都會固定輸出 `target_col / target_label / sort_semantics / decision_quality_horizon_minutes`，避免 active detail path 又退回成只有數值沒有語義。
2. **Strategy Lab active summary no longer hides canonical quality behind ROI/PF-only cards**：`web/src/pages/StrategyLab.tsx` 新增 Active Strategy Decision Quality 區塊，直接顯示 DQ、預期勝率、預期品質、DD/UW、校準樣本與 canonical 排序語義；傳統 ROI/PF 卡片降級為輔助指標。
3. **Regression guard added for the new detail contract**：`tests/test_strategy_lab.py` 新增斷言，確認 `_decorate_strategy_entry()` 會附帶 `decision_contract` 且保留 canonical target metadata。

### 本輪 runtime facts（Heartbeat #645）
- `python scripts/hb_parallel_runner.py --fast --hb 645`：**Raw 20374→20375 / Features 11803→11804 / Labels 40736→40757**；summary 已落地 `data/heartbeat_645_summary.json`。
- Canonical freshness：240m `latest_target=2026-04-10 17:06:42.391378`、`raw_gap≈0.7h`；1440m `latest_target=2026-04-09 21:00:00`、`raw_gap≈1.4h`，兩者皆仍屬 `expected_horizon_lag`。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（由 fast heartbeat 觸發）：Global **13/30 PASS**、TW-IC **16/30 PASS**；Regime IC **Bear 7/8 / Bull 6/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,027）。
- `python -m pytest tests/test_strategy_lab.py -q` → **10 passed**；`cd web && npm run build` ✅。

### Blocker 升級 / 狀態更正
- **#DECISION_QUALITY_GAP（本輪再收斂）**：不能再說 active strategy summary 仍停在 ROI/PF-only 語義。現在排行榜、詳情、run response 與 active summary 都會帶 canonical decision-quality contract。剩餘真 gap 已縮到 saved-strategy comparison / side-by-side compare flow。
- **#LOW_COVERAGE_SOURCES（持續真 blocker）**：Claw / Fin 等 sparse-source coverage blocker 沒有因本輪 UI/API contract patch 假裝改善；blocked features 仍是 8 個。

## 📈 心跳 #644 摘要

### 本輪已驗證 patch
1. **Strategy leaderboard now ranks on canonical decision-quality semantics instead of ROI-only ordering**：`server/routes/api.py::api_strategy_leaderboard()` 會對已儲存策略的 trade entry timestamps 對齊 `labels.simulated_pyramid_*` 欄位，補出 `avg_decision_quality_score`、`avg_expected_win_rate`、`avg_expected_pyramid_quality`、`avg_expected_drawdown_penalty`、`avg_expected_time_underwater`，並以 `DQ -> 預期勝率 -> 較低 DD -> ROI` 排序。
2. **Saved strategy detail path no longer falls back to stale ROI-only metadata**：`/api/strategies/{name}` 現在也會套同一組 canonical decision-quality enrichment，避免排行榜有新語義、點進詳情又退回舊語義。
3. **Strategy Lab UI main table now surfaces canonical ranking reasons directly**：`web/src/pages/StrategyLab.tsx` 的策略排行榜新增 DQ、預期勝率、DD/UW、層數/品質欄位與 canonical 排序語義摘要，不再只顯示 ROI / PF / 風險標籤。
4. **Regression guards added and re-verified**：`tests/test_strategy_lab.py` 新增 strategy decision-quality aggregation 與 strategy sort-key 測試；整體 `32 passed`，前端 build 與 fresh fast heartbeat 也重新驗證通過。

### 本輪 runtime facts（Heartbeat #644 / #644b）
- `python scripts/hb_parallel_runner.py --fast --hb 644`：**Raw 20372→20373 / Features 11801→11802 / Labels 40707→40727**；summary 已落地 `data/heartbeat_644_summary.json`。
- `python scripts/hb_parallel_runner.py --fast --hb 644b`：**Raw 20373→20374 / Features 11802→11803 / Labels 40727→40736**；summary 已落地 `data/heartbeat_644b_summary.json`。
- Canonical freshness：240m `latest_target=2026-04-10 16:41:21.097814`、`raw_gap≈0.7h`；1440m `latest_target=2026-04-09 20:00:00`、`raw_gap≈1.4h`，兩者皆仍屬 `expected_horizon_lag`。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（由 fast heartbeat 觸發）：Global **13/30 PASS**、TW-IC **16/30 PASS**；Regime IC **Bear 6/8 / Bull 6/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,026）。
- `python /tmp/hb644_strategy_lb_probe.py`：`target_col=simulated_pyramid_win`，top strategy `Hybrid QA` 現在直接帶 `dq=0.2921`、`expected_win_rate=0.6585`、`drawdown_penalty=0.2111`。
- `python /tmp/hb644_strategy_detail_probe.py`：`/api/strategies/Hybrid QA` detail 也回傳 `dq=0.2921`、`expected_win_rate=0.6585`、`drawdown_penalty=0.2111`，證明排行與詳情 contract 已一致。
- Source blocker 狀態沒有假改善：仍是 **8 blocked sparse features**；`fin_netflow` 仍為 `auth_missing`，Claw / Claw intensity / Fin 依舊受 `COINGLASS_API_KEY` 缺失阻擋。

### Blocker 升級 / 狀態更正
- **#DECISION_QUALITY_GAP（本輪再收斂）**：不能再說 Strategy Lab 的策略主表仍只看 ROI。現在模型排行榜、策略排行榜與策略詳情 API 都已用 canonical decision-quality semantics。剩餘真 gap 是 active strategy summary / saved-strategy comparison 的文案仍未完全切到同語義。
- **#LOW_COVERAGE_SOURCES（持續真 blocker）**：本輪修的是 decision-quality contract，不是 sparse-source coverage；blocked features 仍是 8 個。

## 📈 心跳 #643 摘要

### 本輪已驗證 patch
1. **Strategy Lab leaderboard UI now surfaces canonical decision-quality semantics directly**：`web/src/pages/StrategyLab.tsx` 的模型排行榜卡片新增 `avg_decision_quality_score`、`avg_expected_win_rate`、`avg_expected_pyramid_quality`、`avg_expected_drawdown_penalty`、`avg_expected_time_underwater`、`avg_allowed_layers`、`avg_entry_quality` 等欄位，並加入 canonical 排序語義摘要，讓前端看到的 ranking reason 與 API payload 一致。
2. **Closed-loop heartbeat re-verified on fresh data**：`python scripts/hb_parallel_runner.py --fast --hb 643` 本輪把 DB 推進到 **Raw 20372 / Features 11801 / Labels 40707**，且 continuity bridge 仍為 0。
3. **Decision-quality live contract remained aligned**：`python scripts/hb_predict_probe.py` 持續輸出 `target_col=simulated_pyramid_win`、`decision_profile_version=phase16_baseline_v2`、`expected_win_rate=0.7654`、`expected_drawdown_penalty=0.1939`、`expected_time_underwater=0.5178`、`decision_quality_score=0.3623`，證明這輪 UI patch 沒有讓 live contract 漂移。
4. **Regression / build verification passed**：`PYTHONPATH=. pytest tests/test_model_leaderboard.py -q` → **13 passed**；`cd web && npm run build` ✅。

### 本輪 runtime facts（Heartbeat #643）
- `python scripts/hb_parallel_runner.py --fast --hb 643`：**Raw 20371→20372 / Features 11800→11801 / Labels 40704→40707**；summary 已落地 `data/heartbeat_643_summary.json`。
- Canonical freshness：240m `latest_target=2026-04-10 16:03:47.548719`、`raw_gap≈0.7h`；1440m `latest_target=2026-04-09 20:00:00`、`raw_gap≈1.4h`，兩者皆仍屬 `expected_horizon_lag`。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（由 fast heartbeat 觸發）：Global **13/30 PASS**、TW-IC **16/30 PASS**；Regime IC **Bear 6/8 / Bull 6/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,026）。
- Sparse-source blockers 仍是 **8** 個；`fin_netflow` 仍為 `auth_missing`，Claw / Fang / Scales / Nest 仍是 archive-window / historical gap 問題，沒有被這輪 UI patch 假裝解掉。

### Blocker 升級 / 狀態更正
- **#DECISION_QUALITY_GAP（本輪再收斂）**：不能再說 decision-quality 只存在於 API / payload。模型排行榜前端已直接顯示 canonical quality semantics；剩餘真缺口是策略排行榜主表與更細的排序說明仍偏舊語義。
- **#LOW_COVERAGE_SOURCES（持續真 blocker）**：本輪修的是 frontend decision contract，不是 sparse-source coverage；blocked features 仍是 8 個。

## 📈 心跳 #642 摘要

### 本輪已驗證 patch
1. **Leaderboard ranking now consumes canonical decision-quality semantics**：`backtesting/model_leaderboard.py` 會在實際 trade entry timestamps 上對齊 `simulated_pyramid_win / simulated_pyramid_quality / simulated_pyramid_drawdown_penalty / simulated_pyramid_time_underwater`，計算 `avg_decision_quality_score`，並把 composite ranking 權重從純 proxy trade-quality 轉成 canonical decision-quality 優先。
2. **Leaderboard/API payload now exposes the same decision-quality contract as live predictor**：`server/routes/api.py::_serialize_model_scores()` 新增 `avg_decision_quality_score`、`avg_expected_win_rate`、`avg_expected_pyramid_quality`、`avg_expected_drawdown_penalty`、`avg_expected_time_underwater`，fold payload 也同步帶出，避免 ranking contract 再落後 live predictor。
3. **Leaderboard feature frame regained canonical 4H parity**：`load_model_leaderboard_frame()` 現在會載入 `feat_4h_bias200`、`feat_4h_dist_bb_lower`、`feat_4h_vol_ratio`，讓 Strategy Lab / leaderboard 的模型比較不再少掉 canonical train/predict path 已使用的 4H features。
4. **Regression guards added**：`tests/test_model_leaderboard.py` 新增 canonical decision-quality summarization 與 4H parity 斷言，鎖住這次 ranking-contract 修補不再回退。

### 本輪 runtime facts（Heartbeat #642）
- `python scripts/hb_parallel_runner.py --fast --hb 642`：**Raw 20369→20370 / Features 11798→11799 / Labels 40700→40704**；summary 已落地 `data/heartbeat_642_summary.json`。
- 之後直接再跑 `python scripts/hb_collect.py`：**Raw 20370→20371 / Features 11799→11800 / Labels 40704→40704**；證明 collect/label pipeline 在本輪 patch 後仍正常，且沒有新寫鎖回歸。
- Canonical freshness：240m `latest_target=2026-04-10 15:07:34.371405`、`raw_gap≈0.7h`；1440m `latest_target=2026-04-09 19:00:00`、`raw_gap≈1.4h`，兩者皆仍屬 `expected_horizon_lag`。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（由 fast heartbeat 觸發）：Global **13/30 PASS**、TW-IC **16/30 PASS**；Regime IC **Bear 6/8 / Bull 6/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,025）。
- `python scripts/hb_predict_probe.py`：`target_col=simulated_pyramid_win`、`used_model=regime_chop_ensemble`、`signal=HOLD`、`regime_gate=CAUTION`、`entry_quality=0.9137 (A)`、`allowed_layers=2`，且 decision-quality contract 維持 `expected_win_rate=0.7654`、`expected_drawdown_penalty=0.1939`、`expected_time_underwater=0.5179`、`decision_quality_score=0.3623 (C)`。
- `PYTHONPATH=. pytest tests/test_model_leaderboard.py -q` → **13 passed**。

### Blocker 升級 / 狀態更正
- **#DECISION_QUALITY_GAP（本輪部分修復）**：不能再說 leaderboard 仍完全只看 proxy。它現在已能輸出 canonical decision-quality 欄位，且 composite ranking 已開始使用 `avg_decision_quality_score`。剩餘缺口是 Strategy Lab 前端與 live strategy 文案尚未把這組欄位提升成第一層語義。
- **#LEADERBOARD_FEATURE_PARITY（本輪已修）**：leaderboard frame 先前漏掉 `feat_4h_bias200 / feat_4h_dist_bb_lower / feat_4h_vol_ratio`，使 ranking 使用的 canonical 4H feature set 落後 train/predict。現在已補齊並加測試，不應再被誤報成 parity 已成立卻實際少欄位。
- **#LOW_COVERAGE_SOURCES（持續真 blocker）**：Claw / Fin 等 sparse-source coverage blocker 沒有因本輪 ranking patch 假裝改善；仍需 source-level修復。

## 📈 心跳 #641 摘要

### 本輪已驗證 patch
1. **SQLite heartbeat writer lock root cause fixed**：`database/models.py::init_db()` 現在對 SQLite engine 一律開 `timeout=30s`、`check_same_thread=False`，並在 connect 時套用 `journal_mode=WAL`、`synchronous=NORMAL`、`busy_timeout=30000`、`foreign_keys=ON`，避免常駐 API 讀流量把 `hb_collect.py` 的 label commit 卡成 `database is locked`。
2. **Regression test added for the new DB contract**：`tests/test_hb_collect.py` 新增 SQLite pragma 驗證，鎖住 `init_db()` 不能再退回 5s timeout + DELETE journal 的脆弱配置。
3. **Closed-loop verify done on the real heartbeat path**：先直接跑 `python scripts/hb_collect.py` 驗證 labels 可成功 commit（24h +1），再跑 `python scripts/hb_parallel_runner.py --fast --hb 641b` 確認 pre-collect 由 `FAIL` 轉成 `PASS`。

### 本輪 runtime facts（Heartbeat #641 / #641b）
- `python scripts/hb_collect.py`：**Raw 20366→20367 / Features 11795→11796 / Labels 40699→40700**；`Label horizon 24h complete (generated=11153, db_rows=11153, delta=+1)`，不再出現 `database is locked`。
- `python scripts/hb_parallel_runner.py --fast --hb 641b`：**Pre-heartbeat collect: PASS (rc=0)**；**Raw 20367→20368 / Features 11796→11797 / Labels 40700→40700**；summary 已落地 `data/heartbeat_641b_summary.json`。
- Canonical freshness：240m `latest_target=2026-04-10 13:02:11.880523`、`raw_gap=1.4h`；1440m `latest_target=2026-04-09 18:00:00`、`raw_gap=1.4h`，兩者皆仍屬 `expected_horizon_lag`。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（由 fast heartbeat 觸發）：Global **13/30 PASS**、TW-IC **16/30 PASS**；Regime IC **Bear 6/8 / Bull 6/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,024）。
- `python scripts/hb_predict_probe.py`：`target_col=simulated_pyramid_win`、`used_model=regime_chop_abstain`、`signal=ABSTAIN`、`regime_gate=CAUTION`、`entry_quality=0.8708 (A)`、`allowed_layers=2`；decision-quality contract 仍完整回傳 `expected_win_rate=0.7654`、`expected_drawdown_penalty=0.1940`、`expected_time_underwater=0.5179`、`decision_quality_score=0.3623 (C)`。
- `pytest tests/test_hb_collect.py -q` → **4 passed**。

### Blocker 升級 / 狀態更正
- **#SQLITE_HEARTBEAT_WRITER_LOCK（本輪已修）**：Heartbeat #641 前，fast heartbeat pre-collect 會在 `save_labels_to_db()` commit 時被常駐 API / SQLite 共享讀寫路徑卡成 `database is locked`，造成 pre-collect `FAIL` 與 labels freshness 假陰性。現在已改成 WAL + 30s timeout contract，真實 heartbeat 路徑已驗證恢復。
- **#LOW_COVERAGE_SOURCES（持續真 blocker）**：Claw / Claw intensity / Fin 仍受 historical archive / credential 缺口限制；本輪修的是 heartbeat 主資料流寫鎖，不是 sparse-source coverage。
- **#DECISION_QUALITY_GAP（仍是主 P0）**：predictor / API 已能回傳 calibrated decision-quality contract，但 leaderboard / live ranking 尚未把這批 canonical quality score 當成主排序依據。

## 📈 心跳 #640 摘要

### 本輪已驗證 patch
1. **Live predictor / API now carry canonical decision-quality expectations**：`model/predictor.py` 會對當前 `regime_gate + entry_quality_label` 做 1440m historical calibration，輸出 `expected_win_rate`、`expected_pyramid_pnl`、`expected_pyramid_quality`、`expected_drawdown_penalty`、`expected_time_underwater`、`decision_quality_score`、`decision_quality_label`，而不是只剩 baseline gate/quality/layers。
2. **Fallback lanes keep the contract stable**：`/predict/confidence` 的 error path 與 predictor circuit-breaker / chop-abstain paths 都會帶同一組 decision-quality keys，避免 API 在非標準路徑又退回不完整 schema。
3. **Heartbeat probe upgraded from parity-only to decision-quality verification**：`scripts/hb_predict_probe.py` 現在會把 calibration scope / sample size / expected penalties 一起印出，heartbeat 可以直接驗證 live contract 是否真的包含 canonical quality semantics。
4. **Regression tests lock the new contract**：`tests/test_api_feature_history_and_predictor.py` 新增 calibration scope 選擇測試，並驗證 `/predict/confidence` 會把新的 decision-quality 欄位一起回傳。

### 本輪 runtime facts（Heartbeat #640）
- `python scripts/hb_parallel_runner.py --fast --hb 640`：**Raw 20346→20348 / Features 11775→11777 / Labels 40699→40699**；summary 已落地 `data/heartbeat_640_summary.json`。
- Canonical freshness：240m `latest_target=2026-04-10 13:02:11.880523`、`raw_gap=1.4h`；1440m `latest_target=2026-04-09 17:00:00`、`raw_gap=1.4h`，兩者皆仍屬 `expected_horizon_lag`。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（由 fast heartbeat 觸發）：Global **13/30 PASS**、TW-IC **16/30 PASS**；Regime IC **Bear 7/8 / Bull 6/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,023）。
- `python scripts/hb_predict_probe.py`：`target_col=simulated_pyramid_win`、`used_model=regime_bull_ensemble`、`regime_gate=CAUTION`、`entry_quality=0.8393 (A)`、`allowed_layers=2`，且新增 `decision_quality_calibration_scope=regime_gate`、`sample_size=3901`、`expected_win_rate=0.7654`、`expected_drawdown_penalty=0.1940`、`expected_time_underwater=0.5180`、`decision_quality_score=0.3623 (C)`。
- `PYTHONPATH=. pytest tests/test_api_feature_history_and_predictor.py tests/test_model_leaderboard.py tests/test_labeling_p0_p1.py tests/test_hb_collect.py -q` → **24 passed**。
- Source blocker 狀態沒有假改善：仍是 **8 blocked sparse features**；`fin_netflow` 仍為 `auth_missing`，Claw / Claw intensity / Fin 依舊受 `COINGLASS_API_KEY` 缺失阻擋。

### Blocker 升級 / 狀態更正
- **#DECISION_QUALITY_GAP（本輪部分修復）**：不能再說 live predictor 只會回 binary confidence。它現在已能直接回傳 canonical quality target 的 calibrated expectations；剩餘缺口是 ranking / live strategy 還沒有把這組 score 當成主排序與主決策依據。
- **Raw collect fallback（本輪新觀察）**：`hb_collect.py` 本輪出現一次 `Raw data collection FAILED`，但 fallback raw row 仍成功落地且 freshness 未退化。這代表 collector 主路徑仍需監控，但目前尚未造成 raw continuity / label freshness blocker。

## 📈 心跳 #639 摘要

### 本輪已驗證 patch
1. **Canonical decision-quality labels now persist explicit penalty fields**：`database/models.py` 與 `data_ingestion/labeling.py` 新增並回填 `simulated_pyramid_drawdown_penalty` / `simulated_pyramid_time_underwater`，讓 canonical labels 不再只停留在 `simulated_pyramid_win + pnl + quality` 的半成品狀態。
2. **Leaderboard training frame now carries the new quality contract**：`server/routes/api.py::load_model_leaderboard_frame()` 與 `model/train.py` 已把新的 drawdown/time-underwater 欄位一起載入，後續可直接用同一批 canonical rows 比較 binary target 與 quality target，而不是再靠外部人工對照。
3. **Reusable verification lane added**：新增 `scripts/hb_quality_contract_check.py`，heartbeat 現在可以直接檢查 240m / 1440m labels 的 `drawdown_penalty` / `time_underwater` 非空覆蓋與平均值，不用再只靠肉眼翻 DB。
4. **Regression tests cover the new schema contract**：`tests/test_labeling_p0_p1.py`、`tests/test_hb_collect.py`、`tests/test_model_leaderboard.py`、`tests/test_api_feature_history_and_predictor.py` 共 **23 passed**，鎖住 schema / backfill / frame loader 不再回退。

### 本輪 runtime facts（Heartbeat #639）
- `python scripts/hb_parallel_runner.py --fast --hb 639`：**Raw 20313→20315 / Features 11742→11744 / Labels 40699→40699**；summary 已落地 `data/heartbeat_639_summary.json`。
- Canonical freshness：240m `latest_target=2026-04-10 13:02:11.880523`、`raw_gap=1.4h`；1440m `latest_target=2026-04-09 17:00:00`、`raw_gap=1.4h`，兩者皆仍屬 `expected_horizon_lag`。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（由 fast heartbeat 觸發）：Global **13/30 PASS**、TW-IC **16/30 PASS**；Regime IC **Bear 7/8 / Bull 6/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,023）。
- `PYTHONPATH=. python scripts/hb_quality_contract_check.py`：
  - **240m** `rows=20462`, `drawdown_penalty_non_null=11540`, `time_underwater_non_null=11540`, `avg_drawdown_penalty=0.0556`, `avg_time_underwater=0.2521`
  - **1440m** `rows=11152`, `drawdown_penalty_non_null=11152`, `time_underwater_non_null=11152`, `avg_drawdown_penalty=0.2026`, `avg_time_underwater=0.4876`
- `python -m pytest tests/test_labeling_p0_p1.py tests/test_hb_collect.py tests/test_model_leaderboard.py tests/test_api_feature_history_and_predictor.py -q` → **23 passed**。
- Source blocker 狀態沒有假改善：仍是 **8 blocked sparse features**；`fin_netflow` 仍為 `auth_missing`，Claw / Claw intensity / Fin 依舊受 `COINGLASS_API_KEY` 缺失阻擋。

### Blocker 升級 / 狀態更正
- **#DECISION_QUALITY_GAP（本輪部分修復）**：不能再說 canonical quality target 只有 `simulated_pyramid_quality` 一個 proxy。現在 labels DB 已明確持久化 `drawdown_penalty` / `time_underwater`；剩餘缺口是 live predictor / API 主輸出還沒直接回傳它們。
- **#LEADERBOARD_OBJECTIVE_MISMATCH（本輪再推進）**：leaderboard frame 已能讀到 canonical quality penalties，下一輪應直接把這些欄位接入 ranking / API，而不是只靠 backtest-side proxy 分數。
- **#LOW_COVERAGE_SOURCES（持續真 blocker）**：Claw / Claw intensity / Fin 仍受 `COINGLASS_API_KEY` 缺失阻擋；本輪 decision-quality patch 不應被誤報成 source blocker 已解。

## 📈 心跳 #638 摘要

### 本輪已驗證 patch
1. **Leaderboard composite no longer over-rewards raw ROI**：`backtesting/model_leaderboard.py` 現在把 ranking 重心改為 **勝率 / 最大回撤 / PF / trade quality / regime stability / trade count**，不再讓高 ROI 但高回撤模型天然佔優。
2. **Trade-quality fields are now first-class leaderboard outputs**：fold 與 model score 新增 `avg_entry_quality`、`avg_allowed_layers`、`avg_trade_quality`、`regime_stability_score`、`max_drawdown_score`、`profit_factor_score`、`overfit_penalty`，`server/routes/api.py` 會一起序列化到 leaderboard payload。
3. **Regression tests cover the new contract**：新增測試確認 ranking 會偏好低回撤 / 高品質模型，而不是單看 ROI，且 API payload 會輸出新的 quality fields。

### 本輪 runtime facts（Heartbeat #638）
- `python scripts/hb_parallel_runner.py --fast`：**Raw 20308→20309 / Features 11737→11738 / Labels 40697→40697**；summary 已落地 `data/heartbeat_fast_summary.json`。
- Canonical freshness：240m `latest_target=2026-04-10 12:02:11.880523`、`raw_gap=1.4h`；1440m `latest_target=2026-04-09 16:00:00`、`raw_gap=1.4h`，兩者皆仍屬 `expected_horizon_lag`。
- `python scripts/full_ic.py` / `python scripts/regime_aware_ic.py`（由 fast heartbeat 觸發）：Global **13/30 PASS**、TW-IC **17/30 PASS**；Regime IC **Bear 7/8 / Bull 6/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,022）。
- `PYTHONPATH=. pytest tests/test_model_leaderboard.py tests/test_api.py -q` → **20 passed**。這證明新的 leaderboard objective 與 API serialization contract 可回歸驗證。
- Source blocker 狀態沒有假改善：仍是 **8 blocked sparse features**；`fin_netflow` 仍為 `auth_missing`，Claw / Claw intensity / Fin 依舊受 `COINGLASS_API_KEY` 缺失阻擋。

### Blocker 升級 / 狀態更正
- **#LEADERBOARD_OBJECTIVE_MISMATCH（本輪部分修復）**：不能再說 leaderboard 只看 ROI / gap / volatility。它現在已經會輸出 trade-quality / drawdown-aware component fields；剩餘缺口是 canonical quality target 還沒直接接入。
- **#DECISION_QUALITY_GAP（仍是主 P0）**：本輪修的是 leaderboard ranking contract，不是 live predictor 的完整 decision-quality target。`win + pnl_quality + drawdown_penalty + time_underwater` 仍未成為 live 主輸出。
- **#LOW_COVERAGE_SOURCES（持續真 blocker）**：Claw / Claw intensity / Fin 仍受 `COINGLASS_API_KEY` 缺失阻擋；本輪 leaderboard patch 不應被誤報成 source blocker 已解。

## 📈 心跳 #637 摘要

### 本輪已驗證 patch
1. **Live predictor now exports the Phase 16 baseline decision contract**：`model/predictor.py` 新增 `phase16_baseline_v1` live decision profile，`predict()` / chop-abstain path 現在都會回傳 `regime_gate`、`entry_quality`、`entry_quality_label`、`allowed_layers`，不再只有 signal/confidence。
2. **`/predict/confidence` root-cause bug fixed**：`server/routes/api.py` 先前把 `load_predictor()` 的 `(predictor, regime_models)` tuple 當成單一 predictor 傳進 `predict()`，live API 路徑存在真實失配風險。本輪已改為正確 unpack 並把 decision-profile fallback 欄位補齊。
3. **Heartbeat probe upgraded from parity-only to decision-contract verification**：`scripts/hb_predict_probe.py` 現在除了 target/4H parity，也會直接印出 `regime_gate` / `entry_quality` / `allowed_layers`，讓 heartbeat 能驗證 live path 已追上 Strategy Lab baseline。
4. **Regression tests added**：新增 tests 覆蓋 `phase16_baseline_v1` 與 Strategy Lab helper parity，以及 `/predict/confidence` 的 tuple-unpack contract，避免下輪 regression。

### 本輪 runtime facts（Heartbeat #637）
- `python scripts/hb_parallel_runner.py --fast --hb 637`：**Raw 20307→20308 / Features 11736→11737 / Labels 40696→40697**；summary 已落地 `data/heartbeat_637_summary.json`。
- Canonical freshness：240m `latest_target=2026-04-10 12:02:11.880523`、`raw_gap=1.4h`；1440m `latest_target=2026-04-09 16:00:00`、`raw_gap=1.4h`，兩者皆仍屬 `expected_horizon_lag`。
- `python scripts/full_ic.py`：Global **13/30 PASS**、TW-IC **17/30 PASS**；`python scripts/regime_aware_ic.py`：**Bear 7/8 / Bull 6/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,022）。
- `python scripts/hb_predict_probe.py` 現在直接輸出：`target_col=simulated_pyramid_win`、`used_model=regime_chop_abstain`、`regime_gate=CAUTION`、`entry_quality=0.8006 (B)`、`allowed_layers=2`，且 **10/10 canonical 4H features** / **30/30 4H lags** 非空。
- `PYTHONPATH=. pytest tests/test_api_feature_history_and_predictor.py tests/test_strategy_lab.py tests/test_api.py tests/test_model_leaderboard.py -q` → **35 passed**。這證明 live predictor baseline contract 與 Strategy Lab helper semantics 已可回歸驗證。
- Source blocker 狀態沒有假改善：仍是 **8 blocked sparse features**；`fin_netflow` 仍為 `auth_missing`，Claw / Claw intensity / Fin 依舊受 `COINGLASS_API_KEY` 缺失阻擋。

### Blocker 升級 / 狀態更正
- **#PHASE16_LIVE_CONTRACT_GAP（本輪再收斂）**：gate / quality / layer sizing baseline 已正式出現在 live predictor 與 `/predict/confidence`，所以不能再把它描述成「只有 Strategy Lab 有、live path 沒有」。剩餘真 blocker 是 **完整 decision-quality target 尚未成為 live contract**，而不是 baseline gate/quality 完全缺失。
- **#PREDICT_CONFIDENCE_TUPLE_DRIFT（本輪已修）**：`/predict/confidence` 的 `load_predictor()` tuple 未 unpack 會讓 live API 走到錯誤 predictor object。這不是文件問題，而是主路徑 root cause；現在已修掉並加 regression test。
- **#LOW_COVERAGE_SOURCES（持續真 blocker）**：Claw / Claw intensity / Fin 仍受 `COINGLASS_API_KEY` 缺失阻擋；本輪的 live-contract 修補不應被誤報成 sparse-source blocker 已解。

## 📈 心跳 #635 摘要

### 本輪已驗證 patch
1. **Predictor probe import contract fixed at the root cause**：`scripts/hb_predict_probe.py` 現在會自動把 project root 放入 `sys.path`，因此 `python scripts/hb_predict_probe.py` 可在 repo 根目錄直接執行，不再要求人工補 `PYTHONPATH=.`。
2. **Phase 16 baseline re-verified instead of假裝完成**：本輪沒有宣稱 decision-quality / two-stage / layer sizing 已全鏈路完成，而是用 `pytest tests/test_api.py tests/test_strategy_lab.py tests/test_model_leaderboard.py -q` + `npm run build` 明確確認目前只到 Strategy Lab / API / UI baseline，live predictor contract 仍未跟上。

### 本輪 runtime facts（Heartbeat #635）
- `python scripts/hb_parallel_runner.py --fast --hb 635`：**Raw 20302→20303 / Features 11730→11732 / Labels 40511→40560**；summary 已落地 `data/heartbeat_635_summary.json`。
- Canonical freshness：240m `latest_target=2026-04-10 10:02:11.880523`、`raw_gap=4.5h`；1440m `latest_target=2026-04-09 15:00:00`、`raw_gap=4.5h`，兩者皆仍屬 `expected_horizon_lag`。
- `python scripts/full_ic.py`：Global **13/30 PASS**、TW-IC **17/30 PASS**；`python scripts/regime_aware_ic.py`：**Bear 7/8 / Bull 7/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,019）。
- `python scripts/hb_predict_probe.py` 現在可直接成功執行：`target_col=simulated_pyramid_win`、`used_model=regime_bull_ensemble`、`signal=HOLD`、`confidence=0.595967`，且 **10/10 canonical 4H features** / **30/30 4H lags** 非空。
- `PYTHONPATH=. pytest tests/test_api.py tests/test_strategy_lab.py tests/test_model_leaderboard.py -q` → **30 passed**；`cd web && npm run build` ✅。這證明 Phase 16 baseline（regime gate / entry quality / allowed layers / decision-profile summary / leaderboard composite 欄位）在 API 與 UI 層是可回歸驗證的，但並不代表 live predictor contract 已完全閉環。
- Source blocker 狀態沒有假改善：仍是 **8 blocked sparse features**；`fin_netflow` 仍是 `auth_missing`，Claw / Claw intensity / Fin 依舊受 `COINGLASS_API_KEY` 缺失阻擋。

### Blocker 升級 / 狀態更正
- **#PREDICT_PROBE_IMPORT_PATH（本輪已修）**：Heartbeat #634 的 probe 雖可在 `PYTHONPATH=.` 下執行，但 direct command contract 其實未成立。現在已修成 repo 內直接可跑，heartbeat 文件與實際操作重新一致。
- **#PHASE16_LIVE_CONTRACT_GAP（持續真 blocker）**：兩階段決策 / 分層 sizing 的 baseline 已在 backtest/API/UI 驗證，但 `hb_predict_probe.py` 仍看不到 `regime_gate` / `entry_quality` / `allowed_layers`，所以不能把 Phase 16 誤報成全鏈路完成。
- **#LOW_COVERAGE_SOURCES（持續真 blocker）**：Claw / Claw intensity / Fin 仍受 `COINGLASS_API_KEY` 缺失阻擋；這輪的 probe/root-path 修復不應被誤報成 sparse-source blocker 已解。

## 📈 心跳 #634 摘要

### 本輪已驗證 patch
1. **Predictor probe contract restored**：新增 `scripts/hb_predict_probe.py`，把「live inference 是否真的走到 canonical `simulated_pyramid_win` predictor path、且 4H features / lag values 非空」變成 repo 內可重跑的標準腳本，不再依賴已消失的 `scripts/hb633_predict_probe.py` 臨時檔名。
2. **Training warning hygiene fixed at the root cause**：`model/train.py` 把 cross/regime features 改成一次 `pd.concat(...)` 生成，取代多次 `frame.insert`；重新訓練已不再噴 `DataFrame is highly fragmented` PerformanceWarning，heartbeat / retrain stderr 噪音下降。
3. **TW-IC logging corrected**：`model/train.py` 原本把 `TW-IC (core)` 錯誤記成 global `core_ic_summary`，這會污染 heartbeat 對 recent-vs-global feature health 的判讀；本輪已修回真正的 `tw_ic_summary`。
4. **SQLAlchemy 2 deprecation warning removed**：`database/models.py` 改用 `sqlalchemy.orm.declarative_base`，pytest 不再噴 `MovedIn20Warning`，讓 warning channel 更聚焦於真 blocker。

### 本輪 runtime facts（Heartbeat #634）
- `python scripts/hb_parallel_runner.py --fast --hb 634`：**Raw 20167→20168 / Features 11596→11597 / Labels 40446→40511**；summary 已落地 `data/heartbeat_634_summary.json`。
- Canonical freshness 維持健康：240m `latest_target=2026-04-10 04:33:25.898070`、`raw_gap=1.2h`；1440m `latest_target=2026-04-09 08:00:00`、`raw_gap=1.4h`，兩者仍為 `expected_horizon_lag`。
- `python scripts/full_ic.py`：Global **13/25 PASS**、TW-IC **17/25 PASS**；`python scripts/regime_aware_ic.py`：**Bear 7/8 / Bull 7/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,014）。
- `PYTHONPATH=. python model/train.py`（warning-hygiene patch 後）成功完成且 stderr 無 pandas fragmentation warning：global **Train=70.25% / CV=72.23% ± 13.64pp**；regime models **Bear CV 58.97% / Bull 78.30% / Chop 71.05%**。
- `PYTHONPATH=. python scripts/hb_predict_probe.py` 成功走完整 predictor path：`target_col=simulated_pyramid_win`、`used_model=circuit_breaker`、`signal=CIRCUIT_BREAKER`，並確認 **10/10 canonical 4H features** 與 **30/30 4H lag values** 非空。這表示 live inference 對齊仍成立，但目前風控 gate 正主動阻擋交易。
- Source blocker 狀態沒有假改善：仍是 **8 blocked sparse features**；**Claw / Claw intensity / Fin** 繼續被 `COINGLASS_API_KEY` 缺失阻擋。

### Blocker 升級 / 狀態更正
- **#PREDICT_PROBE_DRIFT（本輪已修）**：Heartbeat #633 提到的 predictor probe 腳本名稱已漂移消失，導致 inference verification 不可重跑。現在已用 `scripts/hb_predict_probe.py` 固定成可重跑 contract。
- **#TRAIN_WARNING_HYGIENE（本輪已修）**：train.py 多次插欄造成 pandas fragmentation warnings，會把 retrain stderr 變成高噪音訊號。現在 cross-feature construction 已改為單次 concat，warning channel 重新乾淨。
- **#LOW_COVERAGE_SOURCES（持續真 blocker）**：Claw / Claw intensity / Fin 仍受 `COINGLASS_API_KEY` 缺失阻擋；這輪的 warning/probe 修復不應被誤報成 sparse-source blocker 已解。
- **#CIRCUIT_BREAKER_ACTIVE（持續風控 gate）**：live predictor probe 目前回傳 `used_model=circuit_breaker`，表示交易保護仍在啟動。這不是 probe 壞掉，而是 runtime risk gate 仍有效，下一輪若要解除必須用標籤/策略證據而不是硬關閉保護。

## 📈 心跳 #632c 摘要

### 本輪已驗證 patch
1. **Sparse-source archive-window coverage 不再被 continuity bridge / 非 snapshot rows 稀釋成假 partial coverage**：`feature_engine/feature_history_policy.py` 現在會用 `raw_events` 的實際 snapshot minute buckets 對齊 archive window，只計算有對應 source snapshot 的 feature rows。這修掉了 #629 之後 hourly continuity bridge rows 被算進 sparse-source recent-window denominator、把 coverage 錯誤壓到 92~99% 的假 blocker。
2. **Regression tests 補齊**：`tests/test_feature_history_policy.py` 新增「bridge row without snapshot event must be excluded」測試，並把 forward-archive cases 改成使用 recent timestamps，鎖住 ready / partial / healthy 三種 action lane 不再被 stale fixture 或 continuity bridge 汙染。
3. **Coverage report / fast heartbeat 已用新口徑重驗證**：`feature_coverage_report.py` 與 `hb_parallel_runner.py --fast --hb 632c` 都重新跑過，`web_whale` / `fang_*` archive-window 已回到 **100% recent-window coverage**，剩餘 `nest_pred` / `scales_ssr` 的 <100% 才是真實 source-output 缺值，而不是 bridge side effect。

### 本輪 runtime facts（Heartbeat #632 / #632b / #632c）
- `python scripts/hb_parallel_runner.py --fast --hb 632`：**Raw 20131→20132 / Features 11560→11561 / Labels 40415→40417**。
- `python scripts/hb_parallel_runner.py --fast --hb 632b`：**Raw 20132→20133 / Features 11561→11562 / Labels 40417→40421**。
- `python scripts/hb_parallel_runner.py --fast --hb 632c`：**Raw 20133→20134 / Features 11562→11563 / Labels 40421→40423**；summary 已落地 `data/heartbeat_632c_summary.json`。
- Canonical freshness 維持健康：240m `latest_target=2026-04-10 02:33:12.611102`、`raw_gap=0.3h`；1440m `latest_target=2026-04-09 06:00:00`、`raw_gap=1.4h`，兩者皆為 `expected_horizon_lag`。
- Canonical diagnostics 維持：**Global IC 14/22 PASS**、**TW-IC 14/22 PASS**；regime-aware IC **Bear 7/8 / Bull 7/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,012）。
- Coverage gate 經新口徑校正後：
  - **web_whale / fang_pcr / fang_skew**：archive-window **100.00%**（不再被 continuity bridge rows 誤判成 partial）
  - **nest_pred / scales_ssr**：archive-window **98.46% / 98.77%**，代表仍有少量真實 source-output 缺值，下一輪才需要查 parser/source path，而不是回頭重修 bridge logic
  - **Claw / Claw intensity / Fin**：仍是 `source_auth_blocked`，archive-window **0%**，根因仍是 `COINGLASS_API_KEY` 缺失
- 驗證：`PYTHONPATH=. pytest tests/test_feature_history_policy.py -q` → **7 passed**；`python scripts/feature_coverage_report.py` ✅；`python scripts/hb_parallel_runner.py --fast --hb 632c` ✅。

### Blocker 升級 / 狀態更正
- **#ARCHIVE_WINDOW_FALSE_PARTIAL（本輪已修）**：本輪確認 sparse-source recent-window coverage 的一部分「未達 100%」其實是 continuity bridge / non-snapshot rows 被錯算進 denominator，而非 source path 真的 partial。這個分析污染已修掉，後續只有真正沒有 snapshot event 的 row 會被排除。
- **#LOW_COVERAGE_SOURCES（持續真 blocker）**：本輪把 blocker 再收斂：
  1. **已證明 forward recent-window healthy**：Web / Fang 不要再重開 live-fetch debugging。
  2. **真實 partial recent-window**：Nest / Scales 仍有少量 recent-output 缺值，下一輪若要修，應直接查 parser/source mapping。
  3. **Credential blocker**：Claw / Fin 仍被 `COINGLASS_API_KEY` 卡住，這件事沒有被 coverage policy 修補假裝解掉。

## 📈 心跳 #631b 摘要

### 本輪已驗證 patch
1. **Raw continuity bridge 不再是只能靠肉眼看 log 的隱性 workaround**：`data_ingestion/collector.py::repair_recent_raw_continuity()` 現在支援 `return_details=True`，會回傳 coarse / fine / interpolated bridge 的實際插入數，讓 heartbeat 能分辨這輪是正常 continuity、1h repair，還是真的用了 interpolated bridge。
2. **hb_collect / hb_parallel_runner 會把 continuity telemetry 寫進 summary**：`scripts/hb_collect.py` 現在輸出 `CONTINUITY_REPAIR_META`；`scripts/hb_parallel_runner.py` 會解析它並落地到 `data/heartbeat_631b_summary.json -> collect_result.continuity_repair`，包含 `bridge_inserted`、`used_bridge`、`bridge_fallback_streak`。
3. **Regression guard 補齊**：`tests/test_raw_continuity_repair.py` 新增 detail contract；`tests/test_hb_parallel_runner.py` 鎖住 collect metadata parsing 與 summary persistence，避免下輪又退回「bridge 被用了但 summary 看不見」。

### 本輪 runtime facts（Heartbeat #631 / #631b）
- `python scripts/hb_parallel_runner.py --fast --hb 631`：**Raw 20129→20130 / Features 11558→11559 / Labels 40414→40415**。
- `python scripts/hb_parallel_runner.py --fast --hb 631b`：**Raw 20130→20131 / Features 11559→11560 / Labels 40415→40415**；summary 已落地 `data/heartbeat_631b_summary.json`。
- 本輪 continuity telemetry 顯示：`coarse_inserted=0 / fine_inserted=0 / bridge_inserted=0 / bridge_fallback_streak=0`。這代表 #629 的 bridge workaround **本輪沒有再次觸發**，240m freshness 目前不是靠 interpolated bridge 撐住，而是 collector continuity 仍健康。
- Canonical freshness：240m `latest_target=2026-04-10 01:00:00`、`raw_gap=1.42h`；1440m `latest_target=2026-04-09 06:00:00`、`raw_gap=1.42h`，兩者都維持 `expected_horizon_lag`。
- Canonical diagnostics 維持：**Global IC 14/22 PASS**、**TW-IC 14/22 PASS**；regime-aware IC **Bear 7/8 / Bull 7/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,012）。
- Source blocker 沒有假裝修好：仍是 **8 blocked sparse features**；**Claw / Claw intensity / Fin** 依舊被 `COINGLASS_API_KEY` 缺失阻擋。
- 驗證：`PYTHONPATH=. pytest tests/test_raw_continuity_repair.py tests/test_hb_parallel_runner.py -q` → **9 passed**；`python scripts/hb_parallel_runner.py --fast --hb 631b` ✅。

### Blocker 升級 / 狀態更正
- **#RAW_CONTINUITY_RECOVERY（本輪再收斂）**：Roadmap/charter 仍要求監控「interpolated bridge 是否連續多輪被迫介入」。本輪已把這件事變成 summary 裡的可驗證欄位，不再靠人工翻 log 判讀。現況 streak=0，因此暫不升級成 collector/service continuity blocker。
- **#LOW_COVERAGE_SOURCES（未修、維持真 blocker）**：Claw / Claw intensity / Fin 仍受 `COINGLASS_API_KEY` 缺失阻擋；這仍是下一輪真正的 P0/P1 候選之一。

## 📈 心跳 #630 摘要

### 本輪已驗證 patch
1. **Regime-aware IC 不再把大多數 canonical rows 丟進假 neutral bucket**：`scripts/regime_aware_ic.py` 現在會先用 `feat_mind` tertiles 分配 regime，若 `feat_mind` 缺值則 fallback 到 `features_normalized.regime_label`；不再把 **8,283/11,011** 個 `feat_mind is NULL` 的 row 全部誤判成 neutral。
2. **Regime diagnostics metadata 落地**：`data/ic_regime_analysis.json` 現在會保存 `regime_meta` 與 `regime_counts`，讓 heartbeat summary / 後續 triage 能看見本輪是否依賴 fallback，而不是只看一組誤導性的 regime 數字。
3. **Regression tests 補齊**：新增 `tests/test_regime_aware_ic.py`，鎖住「`feat_mind` 缺值時必須回退到 `feature_regime`」與「mind 樣本不足時只用 feature_regime」兩條 contract。

### 本輪 runtime facts（Heartbeat #630）
- `python scripts/hb_parallel_runner.py --fast --hb 630`：**Raw 20128→20129 / Features 11557→11558 / Labels 40414→40414**；summary 已落地 `data/heartbeat_630_summary.json`。
- Canonical freshness 維持健康口徑：
  - **240m**：`latest_target=2026-04-10 01:00:00`、`lag_vs_raw=3.9h`、`raw_gap=1.4h` → `expected_horizon_lag`
  - **1440m**：`latest_target=2026-04-09 05:00:00`、`lag_vs_raw=23.9h`、`raw_gap=1.4h` → `expected_horizon_lag`
- `python scripts/regime_aware_ic.py`（修正後）顯示：`fallback rows using features.regime_label: 8283 / 11011`；regime distribution 由先前假性的 **bear 900 / bull 900 / chop 928 / neutral 8283** 收斂為 **bear 2131 / bull 965 / chop 7894 / neutral 21**。
- 修正後 canonical regime IC：**Bear 7/8 PASS / Bull 7/8 PASS / Chop 5/8 PASS**；這比 #629 的假結果（Bear 5/8 / Bull 7/8 / Chop 2/8 / Neutral 1/8）更貼近 DB regime reality，直接影響下一輪 P0/P1 排序。
- Source blocker 沒被假裝修好：仍是 **8 blocked sparse features**；**Claw / Claw intensity / Fin** 依舊被 `COINGLASS_API_KEY` 缺失阻擋。
- 驗證：`source venv/bin/activate && pytest tests/test_regime_aware_ic.py tests/test_hb_parallel_runner.py -q` → **5 passed**；`python scripts/regime_aware_ic.py` ✅；`python scripts/hb_parallel_runner.py --fast --hb 630` ✅。

### Blocker 升級 / 狀態更正
- **#REGIME_IC_NULL_BUCKET（本輪已修）**：先前 `regime_aware_ic.py` 在 `feat_mind` 缺值時直接寫成 `neutral`，讓 **75%+** canonical rows 掉進假 neutral bucket，誤導 heartbeat 認為 Chop 幾乎沒訊號。這不是市場 regime 崩掉，而是分析腳本 fallback 缺失。現在已改成 `feat_mind tertiles + features.regime_label fallback`。
- **#LOW_COVERAGE_SOURCES（未修、維持真 blocker）**：Claw / Claw intensity / Fin 仍受 `COINGLASS_API_KEY` 缺失阻擋；本輪不把 regime script 修復誤報成 source coverage 已解。

## 📈 心跳 #629 摘要

### 本輪已驗證 patch
1. **240m raw continuity 不再被「只等下一根 4h kline」卡死**：`data_ingestion/collector.py::repair_recent_raw_continuity()` 現在先跑原本的 4h Binance continuity repair，再加一層 **1h public-kline repair**；若 Binance 公開 kline 仍補不到最近幾小時，則會對 `max_gap_hours<=12h` 的 recent raw gap 生成 **hourly interpolated bridge rows**，把 heartbeat 從「raw gap 只能靠服務恢復後慢慢追」升級成 repo 內可自救的 closed-loop。
2. **Feature / label pipeline 已吃到 continuity bridge**：`scripts/hb_collect.py` 沿用既有 missing feature-row backfill lane，把 bridge / 1h continuity rows 寫進 `features_normalized` 後立即重跑 labels，沒有出現「raw 修了但 feature / label 沒跟上」的假進度。
3. **Regression tests 補齊**：`tests/test_raw_continuity_repair.py` 新增 fine-grain 1h repair 與 interpolated bridge fallback case，鎖住 Heartbeat #629 的 continuity repair contract。

### 本輪 runtime facts（Heartbeat #629 / 629b）
- `python scripts/hb_collect.py`（第一次 #629 patch run）：**Raw 20105→20120 / Features 11534→11549 / Labels 39879→40265**；repair lane 插入 **14 筆 continuity rows**、feature backfill **14 rows**，labels 成長 **+386**。
- `python scripts/hb_collect.py`（bridge fallback 生效後）：**Raw 20120→20126 / Features 11549→11555 / Labels 40265→40414**；再插入 **5 筆 hourly bridge rows**、feature backfill **5 rows**，labels 再成長 **+149**。
- `python scripts/hb_parallel_runner.py --fast --hb 629b`：**Raw 20126→20127 / Features 11555→11556 / Labels 40414→40414**；summary 已落地 `data/heartbeat_629b_summary.json`。
- **240m canonical freshness 已從 blocker 轉回 healthy lane**：
  - `latest_target` **2026-04-09 16:00 → 2026-04-10 01:00**
  - `latest_raw_gap_hours` **6.42h → 1.42h**
  - `freshness` **`raw_gap_blocked` → `expected_horizon_lag`**
- 1440m canonical horizon 同步改善：`latest_target=2026-04-09 05:00:00`、`latest_raw_gap_hours=1.42h`、仍為 `expected_horizon_lag`。
- Latest diagnostics（`simulated_pyramid_win`, n=11,011）：**Global IC 14/22 PASS**、**TW-IC 14/22 PASS**；regime-aware IC **Bear 5/8 / Bull 7/8 / Chop 2/8 / Neutral 1/8**。
- Source blocker 沒被假裝修好：仍是 **8 blocked sparse features**；**Claw / Claw intensity / Fin** 依舊被 `COINGLASS_API_KEY` 缺失阻擋。
- 驗證：`PYTHONPATH=. pytest tests/test_raw_continuity_repair.py tests/test_preprocessor_missing_feature_backfill.py tests/test_hb_collect.py -q` → **8 passed**；`python scripts/hb_collect.py` ✅；`python scripts/hb_parallel_runner.py --fast --hb 629b` ✅。

### Blocker 升級 / 狀態更正
- **#RAW_CONTINUITY_RECOVERY（本輪已再推進）**：Heartbeats #628 已修掉 4h continuity 與 missing feature-row backfill；Heartbeat #629 再補上 **1h public repair + interpolated hourly bridge fallback**，把 240m freshness 從 `raw_gap_blocked` 真正拉回 `expected_horizon_lag`。剩餘 gap 問題不再是 active blocker，而是未來若 bridge 連續多輪介入，需升級成「collector/service continuity 仍不穩」監控項。
- **#LOW_COVERAGE_SOURCES（未修、維持真 blocker）**：Claw / Claw intensity / Fin 仍受 `COINGLASS_API_KEY` 缺失阻擋；本輪不把 raw continuity 修復誤報成 sparse-source 已解。

## 📈 心跳 #628 摘要

### 本輪已驗證 patch
1. **Recent raw continuity is no longer left entirely to the live snapshot cadence**：`data_ingestion/collector.py` 新增 `repair_recent_raw_continuity()`，在 heartbeat live collect 前先用 **Binance 4h public klines** 回補最近缺失的 raw rows，避免 scheduler 斷檔後只靠「下一筆 live snapshot」讓 `raw_gap_blocked` 長期卡死。
2. **Repaired raw rows now actually enter the feature pipeline**：`feature_engine/preprocessor.py` 新增 `backfill_missing_feature_rows()`；`scripts/hb_collect.py` 在正常 `run_preprocessor()` 後會只對缺失 timestamp 補 feature rows，而不是把 raw 修回來卻讓 `features_normalized` 仍缺洞。
3. **Heartbeat collection now closes the raw → feature → label loop for continuity repairs**：`scripts/hb_collect.py` Step 1/2 會明確印出 raw continuity repair 與 missing feature-row backfill 數量，讓 heartbeat runtime 能區分「只是 collect +1」和「真的修回中斷時段」。
4. **Regression tests added**：新增 `tests/test_raw_continuity_repair.py` 與 `tests/test_preprocessor_missing_feature_backfill.py`，鎖住 recent-gap backfill 與 missing-feature backfill contract。

### 本輪 runtime facts（Heartbeat #628 / 628b）
- `python scripts/hb_collect.py`（第一次修復 run）：**Raw 20093→20101 / Features 11478→11479 / Labels 39239→39784**；其中明確印出 **`Recent raw continuity repair inserted 7 Binance 4h rows`**，把 240m / 1440m label growth 從完全卡死推進到 **4h +88 / 24h +457**。
- `python scripts/hb_collect.py`（修 feature gap 後再驗證）：**Raw 20101→20102 / Features 11479→11531 / Labels 39784→39879**；明確印出 **`Backfilled 51 missing feature rows`**，再把 labels 推進 **+95**。
- `python scripts/hb_parallel_runner.py --fast --hb 628b`：**Raw 20102→20103 / Features 11531→11532 / Labels 39879→39879**；summary 已落地 `data/heartbeat_628b_summary.json`。
- 240m canonical freshness **有真前進但未完全解除 blocker**：
  - `latest_target` **2026-04-08 23:56 → 2026-04-09 16:00**
  - `latest_raw_gap_hours` **23.48h → 6.42h**
  - blocker 仍是 `raw_gap_blocked`，因 **2026-04-09 20:00 → 2026-04-10 02:25** 之間仍缺可落在 240m tolerance 內的 raw price（Binance 4h closed-kline backfill 已補到 20:00，00:00 candle尚未在 historical klines 中可用時段內被補齊）。
- 1440m canonical horizon 已恢復健康口徑：`latest_target=2026-04-09 04:00:00`、`freshness=expected_horizon_lag`。
- Latest diagnostics（`simulated_pyramid_win`, n=10,677）：**Global IC 13/22 PASS**、**TW-IC 17/22 PASS**；regime-aware IC **Bear 5/8 / Bull 8/8 / Chop 4/8 / Neutral 1/8**。
- Source blocker 沒被假裝修好：仍是 **8 blocked sparse features**；**Claw / Claw intensity / Fin** 依舊被 `COINGLASS_API_KEY` 缺失阻擋。
- 驗證：`PYTHONPATH=. pytest tests/test_raw_continuity_repair.py tests/test_preprocessor_missing_feature_backfill.py tests/test_hb_collect.py -q` → **6 passed**；`python scripts/hb_collect.py` ✅；`python scripts/hb_parallel_runner.py --fast --hb 628b` ✅。

### Blocker 升級 / 狀態更正
- **#RAW_CONTINUITY_RECOVERY（部分修復）**：本輪已修掉「heartbeat 只會 append 一筆 live raw、完全無法補回 recent gap」這個 root cause；剩餘 blocker 不再是完全沒有修復路徑，而是 **closed 4h kline coverage 只能補到上一根已收線 candle，2026-04-10 00:00 這根對 240m 仍缺可用 raw price**。下一輪需追的是更細粒度 raw continuity（例如更短週期 public price archive / collector service continuity），不是回頭重修 label upsert。
- **#MISSING_FEATURE_ROWS_AFTER_RAW_REPAIR（本輪已修）**：先前即便 raw rows 補回來，`run_preprocessor()` 仍只會寫最新一筆 features，導致 label pipeline 無法消化 repaired raw timestamps；現在已改成自動補缺失 feature rows。
- **#LOW_COVERAGE_SOURCES（未修、維持真 blocker）**：Claw / Claw intensity / Fin 仍受 `COINGLASS_API_KEY` 缺失阻擋；這不是本輪能在 repo 內自行修復的問題。

## 📈 心跳 #627 摘要

### 本輪已驗證 patch
1. **4h label canonical backfill no longer leaves legacy rows half-migrated**：`data_ingestion/labeling.py::save_labels_to_db()` 現在會在既有 row 已有 `future_return_pct`、但 `simulated_pyramid_*` / `label_spot_long_*` 仍為 `NULL` 時回填 canonical 欄位，而不是只更新 `future_return_pct IS NULL` 的舊邏輯。實際效果：**240m simulated targets 由 1,379 → 11,007**，把「4h 看似 stale 其實只是 canonical 欄位沒補齊」的假 blocker 收斂掉。
2. **Heartbeat horizon freshness now distinguishes active / inactive / raw-gap-blocked**：`scripts/hb_collect.py` 新增 `summarize_label_horizons()` 的 active horizon contract（240m / 1440m）、`inactive_horizon` 分類（720m legacy rows 不再被誤報成 heartbeat blocker），以及 `raw_gap_blocked` 診斷（若 label 落後是因為 target 之後 raw timeline 有超過 horizon 容許值的大斷層，就明確指向 upstream raw continuity，而不是籠統寫成 label pipeline 壞掉）。
3. **Fast heartbeat JSON summary 與 collect console 對齊**：`scripts/hb_parallel_runner.py` 改為重用 `summarize_label_horizons()`，`data/heartbeat_627c_summary.json` 現在會直接寫出每個 horizon 的 `freshness / is_active / latest_raw_gap_hours`，避免 runtime 與 summary 對同一個 label blocker 給出不同結論。
4. **Regression tests added**：`tests/test_hb_collect.py` 新增 canonical backfill 與 `raw_gap_blocked` / `inactive_horizon` 分類測試，鎖住本輪修復。

### 本輪 runtime facts（Heartbeat #627）
- `python scripts/hb_collect.py`：**Raw 20089→20090 / Features 11474→11475 / Labels 39239→39239**。
- `python scripts/hb_parallel_runner.py --fast --hb 627c`：**Raw 20090→20091 / Features 11475→11476 / Labels 39239→39239**；summary 已落地 `data/heartbeat_627c_summary.json`。
- Canonical label freshness 現在可分層判讀：
  - **240m**：`target_rows=11007`、`latest_target=2026-04-08 23:56:09`、`lag_vs_raw=27.8h`、**`raw_gap_blocked`**、`latest_raw_gap_hours=23.48` → 不是單純 label 欄位缺失，而是 **2026-04-09 02:56 → 2026-04-10 02:25 的 raw timeline 大斷層** 讓 4h target 無法持續長出。
  - **720m**：`target_rows=0`、**`inactive_horizon`** → DB 裡仍有 legacy 12h rows，但 heartbeat 不再維護它，不能再當 active blocker 報警。
  - **1440m**：`target_rows=10225`、`latest_target=2026-04-09 02:56:15`、**`expected_horizon_lag`**。
- Canonical diagnostics 維持：**Global IC 15/22 PASS**、**TW-IC 12/22 PASS**；regime-aware IC **Bear 4/8 / Bull 8/8 / Chop 6/8 / Neutral 1/8**（`simulated_pyramid_win`, n=10,216）。
- Source blocker 未假裝修好：仍是 **8 blocked sparse features**；Claw / Claw intensity / Fin 依舊被 `COINGLASS_API_KEY` 缺失阻擋。
- 驗證：`PYTHONPATH=. pytest tests/test_hb_collect.py -q` → **3 passed**；`python scripts/hb_collect.py` ✅；`python scripts/hb_parallel_runner.py --fast --hb 627c` ✅。

### Blocker 升級 / 狀態更正
- **#LABEL_HORIZON_GROWTH_GATE（重新定義）**：本輪證明 240m 不再是「canonical 欄位沒回填」造成的假 stale；剩餘 blocker 是 **raw continuity gap**。後續若 240m 仍不增長，優先查 upstream raw collection / service continuity，而不是再重修 label upsert。
- **#LEGACY_720_HORIZON_NOISE（本輪已降噪）**：720m rows 仍存在於 DB，但已被明確標記成 `inactive_horizon`；未來 heartbeat 不應再把它當 active pipeline blocker。
- **#LOW_COVERAGE_SOURCES（未修、維持真 blocker）**：Claw / Claw intensity / Fin 仍受 `COINGLASS_API_KEY` 缺失阻擋；這不是本輪能在 repo 內自行修復的問題。

## 📈 心跳 #626 摘要

### 本輪已驗證 patch
1. **Indicator math no longer emits divide-by-zero / invalid RuntimeWarning during heartbeat collection**：`feature_engine/technical_indicators.py` 與 `feature_engine/ohlcv_4h.py` 全部改成 warning-safe divide（`np.divide(..., where=...)`），修掉 flat/zero-volume window 仍會在 `np.where` 的未選分支先做除法、把 fast heartbeat stderr 汙染成假異常的 root cause。
2. **Regression guard added for flat-series edge cases**：新增 `tests/test_indicator_warning_hygiene.py`，直接覆蓋 technical indicators 與 4H indicator pipeline 在零價格 / 零成交量 / 平坦序列下的 warning hygiene，鎖住 `%B`、VWAP、RSI、4H bias / BB / vol_ratio / dist_swing_low` 不再重引入 RuntimeWarning。
3. **Fast heartbeat re-verified on real runtime**：`python scripts/hb_parallel_runner.py --fast --hb 626` 已確認 pre-collect stderr 不再出現 `technical_indicators.py` / `ohlcv_4h.py` 的 divide-by-zero warnings；現在若 collect stderr 出現內容，優先代表真實 blocker 而不是數值邊界噪音。

### 本輪 runtime facts（Heartbeat #626）
- `python scripts/hb_parallel_runner.py --fast --hb 626`：**Raw 20069→20070 / Features 11455→11456 / Labels 39239→39239**；fast heartbeat 仍先 collect 再診斷，閉環未退化。
- Canonical diagnostics：**Global IC 15/22 PASS**、**TW-IC 12/22 PASS**；regime-aware IC 為 **Bear 4/8 / Bull 8/8 / Chop 6/8 / Neutral 1/8**（`simulated_pyramid_win`, n=10,216）。
- **Pre-collect stderr 已清空 warning 噪音**：Heartbeat #625 還會在 collect 階段看到 `divide by zero encountered in divide` / `invalid value encountered in divide`；Heartbeat #626 同一路徑重跑後這些訊息已消失。
- Source blocker 狀態沒有假改善：仍是 **8 blocked sparse features**，其中 **Claw / Claw intensity / Fin** 明確卡在 `COINGLASS_API_KEY` 缺失；Nest / Fang / Web / Scales 則是 forward archive 已健康、歷史 coverage 仍缺。
- Label freshness 仍顯示 **240m stale / 720m no targets / 1440m expected horizon lag**；這輪沒有假裝修好未處理的 label path 問題。
- 驗證：`PYTHONPATH=. pytest tests/test_indicator_warning_hygiene.py tests/test_hb_collect.py -q` → **3 passed**；`python scripts/hb_parallel_runner.py --fast --hb 626` ✅。

### Blocker 升級 / 狀態更正
- **#HEARTBEAT_STDERR_NOISE（本輪已修）**：先前 collect 階段的 divide-by-zero warnings 會把 flat-window 邊界條件偽裝成 pipeline 異常，降低真正 blocker 的可見性；現在已降噪完成，後續 stderr 若再出現內容，應優先視為真實 collector / source / label blocker。
- **#LOW_COVERAGE_SOURCES（未修、維持真 blocker）**：Claw / Claw intensity / Fin 仍受 `COINGLASS_API_KEY` 缺失阻擋；這不是本輪能在 repo 內自行修復的問題，不能用 warning hygiene 當作假進展掩蓋。
- **#LABEL_HORIZON_GROWTH_GATE（仍開）**：24h canonical horizon 正常；240m stale 與 720m zero-target 仍需獨立判斷是不是 label-path / target-definition 問題，下一輪若持續不動要升級 source-level investigation。

## 📈 心跳 #624 摘要

### 本輪已驗證 patch
1. **Sparse-source recent-window triage refined before archive-ready 10/10**：`feature_engine/feature_history_policy.py` 現在會在 `archive_window_coverage_pct` 還沒到 10 筆成熟門檻前，就先分出兩條 lane：
   - **recent-window 已 100% 健康**（例如 Scales / Web / Fang）→ 明確指示「不要再重查 live fetch」，直接持續累積 archive span，下一步是 historical export / archive loader。
   - **recent-window 只部分有值**（例如 Nest）→ 明確升級為 **active source/path quality gap**，提醒下一輪優先查 parser/source mapping，而不是把它誤判成單純歷史 coverage 缺口。
2. **Coverage API runtime 與 heartbeat summary 共用同一 recent-window判斷**：`server/routes/api.py` 改成先計算 `archive_window_*` 再套用 `attach_forward_archive_meta()`，避免 API / runner 之前看不到 recent-window 狀態、只能給 generic 建議的流程缺口。
3. **Strategy Lab canonical target 去污染**：`server/routes/api.py::_summarize_target_candidates()` 改為 **`simulated_pyramid_win` 優先排序且顯示 canonical 標記**；`web/src/pages/StrategyLab.tsx` 現在把 simulated target 顯示為 `canonical`，`label_spot_long_win` 顯示為 `legacy compare`，避免主排行榜區塊把 path-aware 比較 target 與 canonical target 放在同一層語義。

### 本輪 runtime facts（Heartbeat #624）
- `python scripts/hb_parallel_runner.py --fast --hb 624`：**Raw 19786→19787 / Features 11172→11173 / Labels 38717→38717**；heartbeat 仍持續 collect，但本輪尚未跨出新的 24h label horizon，因此 labels 持平。
- Canonical diagnostics 維持：**Global IC 15/22 PASS**、**TW-IC 17/22 PASS**；regime-aware IC 維持 **Bear 6/8 / Bull 8/8 / Chop 8/8 / Neutral 1/8**（`simulated_pyramid_win`, n=9,763）。
- Source blocker lane 現在更清楚：
  - **CoinGlass auth blocker（Claw / Fin）**：仍是 `auth_missing`，屬 credential blocker，不是 coverage 命名問題。
  - **Nest**：forward archive **9/10**、archive-window **50.0% (4/8)**，已被明確標成 **active source/path quality gap**，下一輪要查 parser / source mapping，不要只等歷史累積。
  - **Scales / Web / Fang**：recent-window 已健康（例如 Scales **100.0% (8/8)**），現在 heartbeat 會直接提示「不要重開 live fetch 除錯」，下一步只剩 archive maturity 與 historical export。
- 驗證：`PYTHONPATH=. pytest tests/test_feature_history_policy.py tests/test_model_leaderboard.py -q` → **15 passed**；`cd web && npm run build` ✅；`python scripts/hb_parallel_runner.py --fast --hb 624` ✅。

### Blocker 升級 / 狀態更正
- **#LOW_COVERAGE_SOURCES**：本輪再切得更細，避免下一輪 heartbeat 在錯的 gate 空轉：
  1. **Auth / fetch blocker lane**：Claw / Fin 先修 `COINGLASS_API_KEY`，否則 coverage 不會改善。
  2. **Active source/path lane**：Nest recent-window 只有 50%，代表 forward archive 雖活著，但 feature path 仍半斷；下一輪應直接查 parser/source mapping。
  3. **Historical-gap lane**：Scales / Web / Fang recent-window 已健康，不要再把時間花在 live fetch root-cause；應排 historical export / archive loader。
- **#LABEL_HORIZON_GROWTH_GATE（新 gate，非新 bug）**：本輪 Labels 持平不是 pipeline 壞掉，而是 fast collect 新增的是最新 raw/features，尚未形成新的 1440m future window。下一輪若連續多輪 raw/features 增長但 labels 仍完全不動，才升級回 pipeline blocker。

## 📈 心跳 #622 摘要

### 本輪已驗證 patch
1. **Source auth blocker 升級為第一級 quality flag**：`feature_engine/feature_history_policy.py` 現在會在 sparse source 最新 snapshot 為 `auth_missing` 或其他非 `ok` 失敗時，直接把 coverage quality 升級成 `source_auth_blocked` / `source_fetch_error`，不再只顯示籠統的 `source_history_gap`。這讓 CoinGlass 類 blocker 會在 API / report / UI 被當成「當前 live fetch 壞掉」而不是「歷史 coverage 低」。 
2. **FeatureChart hidden chip / tooltip / hidden summary 與 runtime blocker 對齊**：`web/src/components/FeatureChart.tsx` 現在會直接顯示 `auth缺失` / `fetch失敗`、最新 snapshot status/message，以及 archive 進度；前端不再把 Claw / Fin 這類 auth blocker 顯示成單純 coverage 不足。
3. **Coverage report markdown 同步 latest status**：`scripts/feature_coverage_report.py` 產生的 md/json 報表現在會把 `status=auth_missing (+ message)` 寫進 Forward archive 欄，ISSUES / report / FeatureChart 對同一 blocker 的敘事正式一致。

### 本輪 runtime facts（Heartbeat #622）
- `python scripts/hb_parallel_runner.py --fast --hb 622`：**Raw 19784→19785 / Features 11170→11171 / Labels 38715→38717**，fast heartbeat 仍先 collect 再診斷，閉環未退化。
- Canonical diagnostics 維持：**Global IC 15/22 PASS**、**TW-IC 17/22 PASS**；regime-aware IC 維持 **Bear 6/8 / Bull 8/8 / Chop 8/8 / Neutral 1/8**（`simulated_pyramid_win`, n=9,763）。
- `feature_coverage_report.py` 重新生成後，**Claw / Claw intensity / Fin** 已正式從 generic `source_history_gap` 升級為 **`source_auth_blocked`**；最新 report 直接寫出 `status=auth_missing` 與 CoinGlass credential message，Nest 維持 **33.33% (2/6)** archive-window coverage、Web/Fang/Scales 維持 **100%** recent-window coverage。
- 這代表 source blocker 目前可分成三層：
  - **當前 fetch 被 credential 擋住**：Claw / Claw intensity / Fin（CoinGlass）
  - **forward path 已恢復但 archive 尚未成熟**：Nest
  - **forward archive 健康、只剩歷史缺口**：Web / Fang / Scales
- 驗證：`PYTHONPATH=. pytest tests/test_feature_history_policy.py tests/test_api_feature_history_and_predictor.py tests/test_hb_parallel_runner.py -q` → **10 passed**；`python scripts/feature_coverage_report.py` ✅；`cd web && npm run build` ✅。

### Blocker 升級 / 狀態更正
- **#LOW_COVERAGE_SOURCES**：本輪把 blocker 再收斂成「coverage 問題」與「當前 live fetch 問題」兩條線，避免下一輪又在錯的 gate 空轉：
  1. **CoinGlass auth blocker is now explicit in quality/UI/report** — 這不是歷史缺口，也不是前端 badge 問題；在 `COINGLASS_API_KEY` 缺失前，Claw / Fin coverage 不可能改善。
  2. **Nest 已不是 source-dead** — 現在應看 archive-window 是否從 2/6 繼續往上，而不是回頭懷疑 parser/collector。
  3. **Web / Fang / Scales 下一輪不要再做 live fetch root-cause 排查** — forward archive 已 100%，應直接規劃 historical export / archive loader。

## 📈 心跳 #621 摘要

### 本輪已驗證 patch
1. **CoinGlass sources no longer masquerade as pure history gaps**：`data_ingestion/claw_liquidation.py` / `data_ingestion/fin_etf.py` 改為使用 **CoinGlass v4 endpoint**，並在缺少 `COINGLASS_API_KEY` 或 API 回應失敗時回傳 `_meta.status`；`collector.py` 會把這個狀態寫進 `raw_events.payload_json`，不再只記一個模糊的 `missing` snapshot。
2. **Sparse-source blocker now surfaces live root cause, not only archive progress**：`feature_history_policy.py` / `hb_parallel_runner.py` 會讀取最新 snapshot payload 的 `status/message`，對 Claw / Fin 這類 forward archive 已在累積、但內容其實是 auth failure 的來源，直接升級為 `latest_status=auth_missing` 與對應 `recommended_action`，避免 heartbeat 再對錯的 gate 空轉。
3. **Nest forward feature path repaired**：`data_ingestion/nest_polymarket.py` 現在可解析 Gamma API 會回傳的 **stringified `outcomes` / `outcomePrices`**，並把搜尋範圍擴到 `limit=500`。結果：`nest_pred` 本輪首次重新產出有效值，archive-window coverage 從 **0% → 20% (1/5)**。

### 本輪 runtime facts（Heartbeat #621）
- `python scripts/hb_parallel_runner.py --fast --hb 621`：**Raw 19783→19784 / Features 11169→11170 / Labels 38709→38715**，fast heartbeat 仍先 collect 再診斷，閉環未退化。
- Canonical diagnostics 維持：**Global IC 15/22 PASS**、**TW-IC 17/22 PASS**；regime-aware IC 維持 **Bear 6/8 / Bull 8/8 / Chop 8/8 / Neutral 1/8**（`simulated_pyramid_win`, n=9,763）。
- Source blocker 現況從「單純 coverage 低」進一步收斂成兩類：
  - **Claw / Claw intensity / Fin**：forward archive 已累積到 **6/10**，但最新 snapshot 明確是 `auth_missing`，目前不是單純 historical backfill 問題，而是 **CoinGlass credential blocker**。
  - **Nest**：forward path 已修通，coverage 雖仍低，但 archive-window 已出現 **20% (1/5)**，代表 blocker 從「完全無值」降級為「需要更多 forward archive / 歷史回補」。
  - **Web / Fang / Scales**：archive-window 仍為 **100%**，繼續證明它們主要是歷史缺口，不是 current collector 壞掉。
- 驗證：`PYTHONPATH=. pytest tests/test_feature_history_policy.py tests/test_api_feature_history_and_predictor.py tests/test_hb_parallel_runner.py tests/test_nest_polymarket.py -q` → **11 passed**；`python scripts/hb_parallel_runner.py --fast --hb 621` ✅；`PYTHONPATH=. python scripts/hb621_probe_sources.py` 顯示 **Nest 有值、Claw/Fin 明確為 auth_missing**。

### Blocker 升級 / 狀態更正
- **#LOW_COVERAGE_SOURCES**：本輪正式拆出一個更高優先子根因：
  1. **CoinGlass auth blocker**（Claw / Fin）— 若 `COINGLASS_API_KEY` 未配置，forward archive 只會累積失敗 snapshot，再跑 heartbeat 不會改善 coverage；必須先修 credential，再談 historical export/backfill。
  2. **Forward path repaired but archive immature**（Nest）— parser bug 已修，下一輪應觀察 archive-window coverage 是否隨 heartbeat 持續上升，而不是再把它誤判成 source 無法取值。
  3. **Historical-gap dominant**（Web / Fang / Scales）— current collector 正常，下一輪不要再把時間花在重查 live fetch；應直接規劃 historical export / archive loader。

## 📈 心跳 #620 摘要

### 本輪已驗證 patch
1. **Sparse-source archive-window coverage surfaced end-to-end**：`feature_engine/feature_history_policy.py`、`/api/features/coverage`、`feature_coverage_report.py`、`FeatureChart.tsx`、`hb_parallel_runner.py` 現在除了總 coverage 與 archive progress，還會顯示 **archive-window coverage**（自 raw snapshot archive 起點以來的 non-null / rows），避免 forward archive 已健康時仍被總 coverage 長尾稀釋成「看起來完全沒進展」。
2. **Ready-state action no longer loops on the wrong gate**：當 sparse-source forward archive 達到 `10/10` 後，`recommended_action` 會從「繼續累積到 10 筆」切換為「archive 已可用於 recent-window 診斷，但歷史 coverage 仍需專門 export/archive loader」，修掉下一輪 heartbeat 容易空轉在舊 gate 的流程缺口。
3. **Coverage tooling hardened for partial schemas/tests**：`compute_sqlite_feature_coverage()` 現在會先讀 `PRAGMA table_info`，缺欄 schema 不再直接炸掉；heartbeat/coverage 測試可以用最小 schema 驗證 sparse-source policy，不必複製整個 production schema。

### 本輪 runtime facts（Heartbeat #620）
- `python scripts/hb_parallel_runner.py --fast --hb 620`：**Raw 19781→19782 / Features 11167→11168 / Labels 38675→38689**，fast heartbeat 仍先 collect 再診斷，閉環未退化。
- Sparse-source forward archive 目前來到 **4/10**；runner 現在能直接看見「總 coverage vs archive-window coverage」分離後的真相：
  - **web_whale / fang_pcr / fang_skew / scales_ssr**：總 coverage 仍約 **15.7%**，但 **archive-window coverage = 100% (3/3)**，代表 forward archive 之後的新窗口其實有值，問題主要是歷史缺口，不是現行 collector 又壞了。
  - **claw / claw_intensity / fin_netflow / nest_pred**：archive-window coverage 仍 **0%**，表示不只是歷史缺口，連 forward archive 新窗口也還沒產出可用 feature 值，屬當前更高優先 source gap。
- Canonical diagnostics 維持：**Global IC 15/22 PASS**、**TW-IC 17/22 PASS**；regime-aware IC 仍為 **Bear 6/8 / Bull 8/8 / Chop 8/8 / Neutral 1/8**（`simulated_pyramid_win`, n=9,763）。
- 驗證：`pytest tests/test_feature_history_policy.py tests/test_api_feature_history_and_predictor.py tests/test_hb_parallel_runner.py -q` → **9 passed**；`python scripts/feature_coverage_report.py` ✅；`python scripts/hb_parallel_runner.py --fast --hb 620` ✅；`cd web && npm run build` ✅。

### Blocker 升級 / 狀態更正
- **#LOW_COVERAGE_SOURCES**：本輪把 blocker 再拆成兩層，避免下一輪繼續空轉：
  1. **historical-gap dominant, forward healthy**：Web / Fang / Scales 的 archive-window coverage 已 100%，下一輪不應再優先懷疑 current collector；真正 blocker 是 historical export / long-span archive loader。
  2. **forward gap still active**：Claw / Fin / Nest（以及 Claw intensity）在 archive-window 內仍是 0%，代表 forward snapshot 雖開始累積，但 feature path 仍未產出可用值；這批才是下一輪 source-level root-cause 修復主戰場。
- **#HEARTBEAT_EMPTY_PROGRESS 防呆再補一層**：先前 heartbeat 只知道 archive 有幾筆，仍可能把「4/10 但新窗口其實全是 NULL」誤當作前進；現在 archive-window coverage 會直接把這種假進度打掉。

## 📈 心跳 #619 摘要

### 本輪已驗證 patch
1. **Fast heartbeat 不再空轉**：`scripts/hb_parallel_runner.py` 新增 pre-heartbeat `hb_collect.py` 步驟（可用 `--no-collect` 關閉），cron/fast mode 不再只是讀取舊 counts，而會先真正推進 **raw → features → labels**。
2. **Forward archive freshness / span metadata surfaced**：`feature_history_policy.py`、`/api/features/coverage`、`feature_coverage_report.py`、`FeatureChart.tsx`、`hb_parallel_runner.py` 現在除了 `raw_snapshot_events` 之外，還會帶出 `latest_ts / oldest_ts / span_hours / latest_age_min / stale status`；sparse-source blocker 不再只知道「有幾筆 archive」，也知道 archive 是否停滯。
3. **Stale-archive blocker escalation**：source blocker 的 `recommended_action` 會在 snapshot archive 超過 **60 分鐘** 未更新時升級成「立即重跑/重啟 heartbeat collection」，避免下一輪又把 archive-building 誤判成在前進。

### 本輪 runtime facts（Heartbeat #619）
- `python scripts/hb_parallel_runner.py --fast --hb 619` 現在會先執行 collect：**Raw 19779→19780 / Features 11165→11166 / Labels 38602→38660**，證明 fast heartbeat 已從「只診斷」修成「先推進再診斷」。
- Forward archive 由前輪 **1/10** 推進到 **2/10**（Claw / Fang / Fin / Web / Scales / Nest 全部同步增加），且 summary / coverage report 可直接看到 `age≈0.2m, span≈0.88h`，證明 archive 在本輪確實有新事件，不是沿用舊狀態假裝前進。
- `feature_coverage_report.py` 已新增 **Freshness** 欄；`FeatureChart` / coverage API 也會顯示 `archive x/10 + stale/building + last age/span`，前端與 heartbeat 對 sparse-source 狀態的解讀再次對齊。
- Canonical diagnostics 維持：**Global IC 15/22 PASS**、**TW-IC 17/22 PASS**；regime-aware IC 仍為 **Bear 6/8 / Bull 8/8 / Chop 8/8 / Neutral 1/8**（`simulated_pyramid_win`, n=9,763）。
- 驗證：`PYTHONPATH=. pytest tests/test_feature_history_policy.py tests/test_hb_parallel_runner.py tests/test_api_feature_history_and_predictor.py tests/test_collector_snapshot_archives.py -q` → **10 passed**；`python scripts/feature_coverage_report.py` ✅；`npm run build` ✅；`python scripts/hb_parallel_runner.py --fast --hb 619` ✅。

### Blocker 升級 / 狀態更正
- **#HEARTBEAT_EMPTY_PROGRESS（已修一層）**：fast heartbeat 之前只會跑 IC 診斷，無法保證 raw/features/labels 或 snapshot archive 有任何新增；現在 runner 先 collect，再診斷，空轉流程缺口已補上。
- **#LOW_COVERAGE_SOURCES**：source-level blocker 仍未解，但判斷標準更嚴格：
  1. **building**：archive 數量 < 10，但 `latest_age_min <= 60`，表示 forward archive 正在累積；
  2. **stale**：archive 已開始但 `latest_age_min > 60`，下一輪必須先恢復 collect，而不是再討論顯示層；
  3. **missing**：沒有任何 snapshot event，屬 source-archive 尚未接通。
- **剩餘根因沒有被掩蓋**：本輪修的是 heartbeat/workflow 與 blocker freshness 可見性，不是歷史 coverage 本身。Claw/Fin 仍需要 historical export；Fang/Web/Scales/Nest 仍需要更多 forward archive 或專門回補來源。

## 📈 心跳 #618 摘要

### 本輪已驗證 patch
1. **Forward raw snapshot archive kickoff**：`data_ingestion/collector.py` 現在會把 **Claw / Fang / Fin / Web / Scales / Nest / Macro** 寫入 `raw_events` (`*_snapshot`)；source-level blocker 不再只是文件上的待辦，而是正式開始累積可回補的 forward archive。
2. **Structured JSON archive payloads**：collector 舊有 `raw_events.payload_json` 原本寫 `str(dict)`；本輪統一改成合法 JSON，並把 snapshot event 包成 `{status, snapshot}`，後續 heartbeat / report / API 不必再靠 `ast.literal_eval` 猜格式。
3. **Claw missing-data hygiene**：`claw_liq_total` 過去在來源缺值時會被寫成 `0`，繼續污染 source-history 判讀；本輪改成「只有有值才加總，否則保持 `None`」，避免把 source outage 假裝成真實零值。
4. **Coverage/report/runtime sync archive progress**：`feature_history_policy.py`、`/api/features/coverage`、`feature_coverage_report.py`、`hb_parallel_runner.py` 現在會帶出 `raw_snapshot_events / forward_archive_ready`，讓 heartbeat 與 FeatureChart 系列輸出可明確看到「歷史仍缺，但 forward archive 已經開始收集」。

### 本輪 runtime facts（Heartbeat #618）
- `python scripts/hb_collect.py`：**Raw 19778→19779 / Features 11164→11165 / Labels 38530→38602**，證明主 pipeline 持續可寫。
- `python scripts/hb618_facts.py` 顯示新的 raw snapshot subtype 已落地：`claw_snapshot=1`, `fang_snapshot=1`, `fin_snapshot=1`, `web_snapshot=1`, `scales_snapshot=1`, `nest_snapshot=1`, `macro_snapshot=1`；修補了先前 **0 個 source snapshot archive event** 的流程缺口。
- `python scripts/hb_parallel_runner.py --fast --hb 618`：**2/2 PASS (0.9s)**；source blockers 仍是 **8 個**，但前 5 個現在都能直接看到 `forward_archive=1`，表示 blocker 已從「完全沒 archive」升級成「歷史仍缺，但 forward collection 正在累積」。
- Canonical diagnostics 維持：**Global IC 15/22 PASS**、**TW-IC 17/22 PASS**；regime-aware IC 仍為 **Bear 6/8 / Bull 8/8 / Chop 8/8 / Neutral 1/8**（`simulated_pyramid_win`）。
- `feature_coverage_report.py` 現在會把 sparse source 的 **Forward archive** 欄位寫進 md/json；coverage 本身尚未立即變高，因為這輪只是開始累積 forward history，不是回填舊歷史。
- 驗證：`PYTHONPATH=. pytest tests/test_collector_snapshot_archives.py tests/test_sparse_source_fallbacks.py tests/test_feature_history_policy.py tests/test_hb_parallel_runner.py tests/test_api_feature_history_and_predictor.py -q` → **11 passed**；`python scripts/hb_collect.py` ✅；`python scripts/feature_coverage_report.py` ✅；`python scripts/hb_parallel_runner.py --fast --hb 618` ✅。

### Blocker 升級 / 狀態更正
- **#LOW_COVERAGE_SOURCES**：本輪不再只是說「下一輪要做 raw snapshot/archive ingestion」；forward snapshot archive 已正式接上 `raw_events`。剩餘 blocker 已收斂成：
  1. **歷史缺口仍在**：Claw / Fin 需要真正 historical export；Fang / Scales / Nest 仍只有從本輪開始累積的 snapshot archive；Web 仍受短窗口 public API 限制。
  2. **這輪解的是流程缺口，不是立即補齊 coverage**：coverage 指標不會因一輪 snapshot 立刻從 0%/15% 變成可用，但之後每輪 heartbeat 不再是空轉。
  3. **下一輪不能退回只修顯示層**：要嘛持續累積 forward archive，要嘛開始做 archive/backfill loader；不能再把 sparse-source 問題當成單純 FeatureChart badge 問題。

## 📈 心跳 #617 摘要

### 本輪已驗證 patch
1. **Shared source-history policy module**：新增 `feature_engine/feature_history_policy.py`，把 `FEATURE_KEY_MAP`、source blocker policy、quality assessment、SQLite coverage aggregation 收斂成單一實作；`scripts/feature_coverage_report.py` 與 `/api/features/coverage` 現在共用同一套邏輯，避免 blocker metadata 漂移後再次誤導 FeatureChart 或 heartbeat 判斷。
2. **hb_parallel_runner fast mode 真正可用**：`scripts/hb_parallel_runner.py` 現在支援 `python scripts/hb_parallel_runner.py --fast` **不必再強制帶 `--hb`**；若有 `--hb 617` 仍可落地成 `data/heartbeat_617_summary.json`，補上 cron 與 skill 文件之間的實際流程缺口。
3. **Source blocker 自動升級進 heartbeat summary**：parallel runner 會在執行前直接輸出並寫入 `source_blockers` 摘要（8 個 blocked sparse features、依 `archive_required / snapshot_only / short_window_public_api` 分類），避免 heartbeat 再只產報告卻沒把 source-level blocker 顯式升級。

### 本輪 runtime facts（Heartbeat #617）
- `python scripts/hb_parallel_runner.py --fast --hb 617`：**2/2 PASS (0.8s)**，summary 已寫入 `data/heartbeat_617_summary.json`；`python scripts/hb_parallel_runner.py --fast` 無 `--hb` 也可直接執行。
- DB counts 維持：**Raw 19,778 / Features 11,164 / Labels 38,530**；canonical `simulated_pyramid_win` rate **0.6008**。
- `feature_coverage_report.py` 與 runner 共享同一 policy 後，source blocker 摘要穩定為 **8 blocked features**：
  - `archive_required`：**3**（Claw / Claw intensity / Fin）
  - `snapshot_only`：**4**（Fang PCR / Fang skew / Scales / Nest）
  - `short_window_public_api`：**1**（Web）
- Canonical diagnostics（fast mode）維持：**Global IC 15/22 PASS**、**TW-IC 17/22 PASS**；regime-aware IC：**Bear 6/8**, **Bull 8/8**, **Chop 8/8**, **Neutral 1/8**（`simulated_pyramid_win` 口徑，n=9,763）。
- 驗證：`pytest tests/test_feature_history_policy.py tests/test_hb_parallel_runner.py tests/test_api_feature_history_and_predictor.py -q` → **8 passed**；`python scripts/feature_coverage_report.py` ✅；`python scripts/hb_parallel_runner.py --fast --hb 617` ✅。

### Blocker 升級 / 狀態更正
- **#LOW_COVERAGE_SOURCES**：本輪正式從「文件裡有 blocker metadata」再升級到「heartbeat runtime 也會主動 surface blocker」；這代表下一輪如果 coverage 還低，不能再假裝是前端 badge / chart policy 問題。
- **heartbeat 空轉缺口已修補**：先前 skill / HEARTBEAT 文件推薦的 `--fast` 命令在實作上會直接因 `--hb required` 失敗，屬於真正的 cron 流程缺口；本輪已修掉。今後 fast heartbeat 可穩定產出 counts + IC + source blockers，而不是卡在參數解析。
- **剩餘未解 blocker 沒有被「修掉」**：Claw / Fin / Fang / Web / Scales / Nest 的歷史 coverage 仍然缺，根因依舊是 source-level archive / snapshot 不存在。這不是前端、不是 carry-forward、也不是 coverage report drift；下一輪要真的前進，必須開始做 raw snapshot/archive ingestion，而不是再追加顯示層修補。

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
| #LOW_COVERAGE_SOURCES | Fin / Fang / Web / Scales / Nest / Claw coverage 低，且歷史上混有假 0 與 stale carry-forward | 🟡 已部分修復並進入 **archive-window gating** 階段（#615 清除假值污染；#618 啟動 `*_snapshot` forward archive；#620 新增 `archive_window_coverage_pct`，已確認 Web/Fang/Scales 在 recent window 為 100%，但 Claw/Fin/Nest 仍為 0%。下一步要分流：Web/Fang/Scales 走 historical export/backfill loader；Claw/Fin/Nest 先修 forward feature path/root cause） |
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
