# ARCHITECTURE.md — Poly-Trader 系統架構

> 完整技術架構文檔。問題追蹤見 [ISSUES.md](ISSUES.md)，產品需求見 [PRD.md](PRD.md)，發展路線見 [ROADMAP.md](ROADMAP.md)。

---

## 技術棧

| 層 | 技術 |
|----|------|
| 前端 | React + TypeScript + Tailwind CSS + Recharts + lightweight-charts |
| 後端 | FastAPI + SQLite + WebSocket |
| 模型 | XGBoost / LightGBM + confidence-based filtering |

---

## 系統分層

### 1. 資料層
統一所有來源進入 raw event store，保留原始事件與來源資訊，支援回放與補歷史。

### 2. 特徵層
將 raw 資料轉換為可量化特徵特徵，並提供 IC、穩定性與版本控制。

**Sparse-source contract（Heartbeat #614）**：對 Claw / Fang / Fin / Web / Scales / Nest 這類低頻/稀疏來源，特徵計算只允許讀取 **latest raw row**；若最新來源缺值，feature 必須保持 `NULL/None`。禁止用舊的非空值 forward-carry 到新 row，也禁止把 fetch failure 寫成 `0.0` 假中性值。

**Historical decontamination（Heartbeat #615）**：舊資料若出現「當前 raw row 已缺值，但 features row 仍殘留 sparse-source 值」或 sentinel fallback（如 Claw `ratio=1,total=0`、Nest `0.5`、Fin `0/0`），必須透過 `scripts/cleanup_sparse_source_history.py` 清回 `NULL`，避免 FeatureChart / coverage / 重算流程讀到假歷史訊號。

**Source-history blocker contract（Heartbeat #616）**：對 sparse sources，coverage/report/API/UI 不只回報 `coverage/distinct/quality_flag`，還必須同步回傳 `history_class / backfill_status / backfill_blocker / recommended_action`。若缺口根因是 `archive_required` / `snapshot_only` / `short_window_public_api`，前端應把它視為 source-level blocker，而不是可用前端美化或 carry-forward 修好的歷史線問題。

**Shared policy contract（Heartbeat #617）**：source-history policy 不可再在 report/API/heartbeat runner 各自複製一份。`feature_engine/feature_history_policy.py` 現在是單一真相來源（single source of truth），`scripts/feature_coverage_report.py`、`/api/features/coverage`、`hb_parallel_runner.py` 都必須共用它，避免 blocker metadata drift 導致 UI 與 heartbeat 對同一 sparse source 給出不同治理結論。

**Archive-window coverage contract（Heartbeat #620 / #632c）**：對 sparse sources，除了整體 `coverage_pct` 與 `raw_snapshot_events`，還必須同步輸出 `archive_window_rows / archive_window_non_null / archive_window_coverage_pct`（自第一筆 snapshot archive 起點以來的 recent-window coverage）。這個 recent-window denominator 不可再用「所有 feature rows since archive start」粗算；必須以 `raw_events` 的實際 snapshot timestamp buckets 對齊，只計算有對應 source snapshot 的 feature rows，排除 continuity bridge / non-snapshot rows。FeatureChart、coverage report、heartbeat runner 都必須顯示同一口徑，避免把歷史稀釋或 continuity workaround 誤判成 active source partial coverage。

**Source auth/fetch blocker contract（Heartbeat #622）**：若 sparse source 最新 snapshot `status != ok`（尤其 `auth_missing`），coverage policy 必須把 quality 從 generic `source_history_gap` 升級成 `source_auth_blocked` / `source_fetch_error`，並把 `raw_snapshot_latest_status/message` 同步給 API、markdown report、FeatureChart。這批欄位的用途不是附註，而是要讓 UI 與 heartbeat 明確知道「現在 live fetch 壞掉」優先於「歷史 coverage 還不夠」。

**Warning-safe indicator math contract（Heartbeat #626）**：feature layer 的技術指標 / 4H 指標計算不得在 flat price、zero-volume 或 zero-width band 視窗下產生 `divide by zero` / `invalid value` RuntimeWarning。所有分母可能為 0 的計算都必須使用 warning-safe divide（例如 `np.divide(..., where=...)`），確保 fast heartbeat stderr 只保留真實 blocker，而不是數值邊界噪音。

**Label horizon freshness contract（Heartbeat #627）**：heartbeat 維護的 active horizons 目前只有 **240m 與 1440m**。`scripts/hb_collect.py::summarize_label_horizons()` 與 `hb_parallel_runner.py` summary 必須把 label freshness 分成：
- `expected_horizon_lag`：符合 lookahead 預期
- `raw_gap_blocked`：label 落後主因是 target 之後的 raw timeline 出現超過 horizon 容許值的斷層
- `inactive_horizon`：DB 中保留的 legacy horizon（如 720m），不得再當 active heartbeat blocker

**Canonical label backfill contract（Heartbeat #627）**：`save_labels_to_db()` 不得只更新 `future_return_pct IS NULL` 的舊 rows。若既有 label row 已有 `future_return_pct`，但 `simulated_pyramid_*` / `label_spot_long_*` canonical 欄位仍為 `NULL`，heartbeat label generation 必須原地回填，避免 heartbeat 對 4h/24h freshness 做出假陰性判斷。

**Recent raw continuity repair contract（Heartbeat #628）**：當 heartbeat 偵測到 recent raw timeline 有多小時斷層時，`data_ingestion/collector.py::repair_recent_raw_continuity()` 必須先用 public Binance **closed 4h klines** 回補缺失 raw rows，再 append live snapshot。這條 lane 的目的不是重建完整 tick history，而是先把 4h canonical label 所需的 recent raw continuity 補回來，避免 `raw_gap_blocked` 永遠只能靠下一筆 live row 慢慢前進。

**Sub-4h continuity bridge contract（Heartbeat #629）**：若 4h repair 之後 240m label path 仍會因最近幾小時缺口被卡住，`repair_recent_raw_continuity()` 還必須再跑 **1h public-kline repair**；若 public kline 仍補不到 gap，則允許對 `max_gap_hours<=12h` 的 recent raw gap 生成 **hourly interpolated bridge rows** 作為 temporary continuity bridge。這個 bridge 只用來讓 canonical 240m label / freshness pipeline 繼續閉環，不是歷史價格真值替代；若它連續多輪被觸發，下一輪必須升級成 collector/service continuity root-cause investigation。

**Continuity telemetry contract（Heartbeat #631b）**：`repair_recent_raw_continuity()` 不可再只回傳單一 inserted count。Heartbeat collect / summary 必須同步落地 `coarse_inserted / fine_inserted / bridge_inserted / used_bridge / bridge_fallback_streak`，讓 runner、ISSUES、ROADMAP 能分辨「raw continuity 真健康」與「只是靠 interpolated bridge 暫時撐住」，避免 workaround 再次變成隱性假進度。

**SQLite writer resilience contract（Heartbeat #641）**：heartbeat collect / label pipeline 需要和常駐 API 共享同一個 SQLite DB，因此 `database.models.init_db()` 對 SQLite 連線必須統一使用 `timeout>=30s`、`check_same_thread=False`，並在 connect 時套用 `PRAGMA journal_mode=WAL`、`PRAGMA synchronous=NORMAL`、`PRAGMA busy_timeout=30000`、`PRAGMA foreign_keys=ON`。若缺少這層 writer-resilience，`hb_collect.py` 可能在 `save_labels_to_db()` commit 時被 API 讀流量卡成 `database is locked`，讓 heartbeat 假失敗並污染 raw/features/labels freshness 判讀。

**Missing feature-row backfill contract（Heartbeat #628）**：raw continuity repair 之後，`feature_engine/preprocessor.py::backfill_missing_feature_rows()` 必須把 repaired raw timestamps 補進 `features_normalized`。否則 raw rows 即使回來了，label generation 仍會因 feature timestamps 缺失而無法消化 repaired window，形成新的假進度。

**Recompute projection contract（Heartbeat #684）**：`feature_engine/preprocessor.py::recompute_all_features()` 不得只重算 core features。當既有 rows 或 backfill/recompute 流程被觸發時，函式必須同步回寫 **`feat_4h_*` 欄位、`regime_label`、`feature_version`**，否則 canonical recent window 會出現「主特徵有值，但 4H projection/metadata 缺失」的半同步狀態，直接污染 drift diagnostics、predictor calibration 與任何 recent-window root-cause 判讀。Heartbeat #684 已用 regression test 鎖住這個 contract，並用 recent 4H backfill 驗證它不是文件承諾而已。

**Fast heartbeat contract（Heartbeat #617 / #659 / #661 / #688 / #689 / #691 / #696）**：`python scripts/hb_parallel_runner.py --fast` 必須可直接在 cron 執行，不依賴額外 `--hb` 參數；fast summary 仍需包含 DB counts、canonical IC 腳本結果與 `source_blockers` 摘要，確保快檢查模式不是「只剩數字」的半閉環。Heartbeat #659 起，summary 必須持久化 `ic_diagnostics` 與 `auto_propose`；Heartbeat #661 再新增 distribution-aware drift artifact；Heartbeat #688 再補 **core-vs-research drift hygiene**：sparse-source research features 必須在 recent-drift diagnostics 中被標成 `overlay_only=research_sparse_source`，不可再混進 `unexpected_frozen` escalation，也不可在存在 core shift 時搶走 sibling-window `top_mean_shift_features` 主證據；Heartbeat #689 再補 **stale regime-drift recovery**：若 current run 已回到 `TW-IC <= Global IC + 2`，`scripts/auto_propose_fixes.py` 必須自動 resolve `#H_AUTO_REGIME_DRIFT`，避免 `issues.json` / heartbeat docs 留下與當前 run 不一致的假 blocker；Heartbeat #691 再補 **live runtime governance**：fast heartbeat 必須同步執行 `scripts/hb_predict_probe.py`、持久化 `data/live_predict_probe.json`、並在 summary 寫入 `live_predictor_diagnostics`，讓 auto-propose 能把 live same-scope pathology 升級成 `#H_AUTO_LIVE_DQ_PATHOLOGY`，而不是只看 global drift artifact。Heartbeat #696 再補 **narrowed-lane governance**：即使 `decision_quality_recent_pathology_applied=false`、broad calibration lane 健康，只要 `decision_quality_scope_diagnostics.pathology_consensus.worst_pathology_scope` 已證明存在嚴重的 narrowed pathology lane（例如 bull-only D pocket），auto-propose 也必須升級 `#H_AUTO_LIVE_DQ_PATHOLOGY`。
- `ic_diagnostics = {global_pass, tw_pass, total_features, n}`
- `drift_diagnostics = {primary_window, primary_alerts, primary_summary, full_sample}`  
  （Heartbeat #676 起，`primary_summary` 內還必須包含 `target_path_diagnostics={tail_target_streak, target_regime_breakdown, recent_examples}`，讓 recent pathology 可直接追到 canonical path 時間線；**Heartbeat #680 再補 `longest_target_streak / longest_zero_target_streak / longest_one_target_streak`**，避免 mixed window 只看到尾端 rebound 而漏掉真正的 adverse pocket；**Heartbeat #682 再補 `reference_window_comparison={prev_win_rate, prev_quality, prev_pnl, top_mean_shift_features, new_*_features}`**，讓 heartbeat 能直接對比 pathology slice 與前一個等長 sibling window，而不是只知道「最近很糟」）
- `auto_propose = {attempted, success, returncode, stdout_preview, stderr_preview}`

另外，fast heartbeat 必須在 auto-propose 之前自動執行 `scripts/recent_drift_report.py`，把 canonical 1440m recent-window `label balance / dominant regime / constant-target` 寫到 `data/recent_drift_report.json`。Heartbeat #687 補充：若 recent window 的 canonical `win/pnl/quality` 很強、`avg_drawdown_penalty` 很低，而 `avg_time_underwater` 只是略高於舊 0.45 cutoff，drift classifier 仍必須維持 `supported_extreme_trend`，避免近閾值 TUW 再次把健康 canonical pocket 誤打成 `distribution_pathology`。Heartbeat #677 再補一條治理約束：feature drift diagnostics 不得把**週末關閉的 macro features（VIX / DXY / NQ returns）**與**離散 4H regime features（`feat_4h_ma_order`）**直接併入 generic freeze blocker；artifact 必須顯式輸出 `expected_static_count / unexpected_frozen_count / expected_static_examples`，讓後續 auto-propose 與 heartbeat 聚焦在真正異常的 compressed/frozen core features，而不是被 market-closed 靜態值誤導。**Heartbeat #679 再補 persistent-pathology selection 約束**：當 `constant_target / label_imbalance` 的 severity 與 win-rate delta 同級時，primary drift window 必須優先選更持久的 recent pathology slice（例如 250 rows，而不是較短的 100 rows），避免 governance 持續低估病灶跨度。這樣後續 heartbeat / drift triage / blocker automation 才能直接 machine-read 最近兩輪的 TW-IC 狀態與污染視窗，而不是重新從 `stdout_preview` 猜字串。**Heartbeat #665 再補一條治理約束**：`scripts/auto_propose_fixes.py::load_recent_tw_history()` 在組裝 `#H_AUTO_TW_DRIFT` 歷史時，必須優先使用正式編號的 `heartbeat_<N>_summary.json`，不可讓匿名 `heartbeat_fast_summary.json` 取代上一輪 numbered heartbeat，否則 blocker escalation 會變成 `#665 -> #fast` 這種不可追蹤的假治理訊號。**Heartbeat #668 再補 drift-interpretation contract**：`recent_drift_report.json` 不得只輸出 `alerts`；每個 recent window 還必須同步輸出 `quality_metrics={avg_simulated_pnl, avg_simulated_quality, avg_drawdown_penalty, avg_time_underwater, spot_long_win_rate, ...}` 與 `drift_interpretation={supported_extreme_trend|distribution_pathology|regime_concentration|healthy}`。`scripts/auto_propose_fixes.py` 必須消費這個欄位，將「真實極端趨勢口袋」和「真正可疑的 label/pathology」分開治理：前者保留 calibration guardrail，但 investigation 方向轉向 recent feature variance / regime narrowness / calibration scope；後者才維持 label/path simulation root-... [truncated]

**Dynamic-window guardrail contract（Heartbeat #662 / #663 / #664）**：`scripts/dynamic_window_train.py` 不得再只用「哪個 window 有最多 IC pass」決定推薦 window。它現在必須同時讀取 local window distribution 與 `data/recent_drift_report.json`，對每個候選 window 輸出 `dominant_regime / alerts / distribution_guardrail`，並把 `constant_target` 或 `regime_concentration` 視窗標成 `skip_for_recommendation`。`data/dw_result.json` 也必須同時保存 `raw_best_n` 與 `recommended_best_n`，避免 heartbeat / calibration path 把 distribution-polluted recent window 誤認為可直接採用的 calibration baseline。Heartbeat #663 補充：live predictor 的 decision-quality calibration 也必須消費這份 artifact，至少輸出 `decision_quality_calibration_window / decision_quality_guardrail_applied / decision_quality_guardrail_reason`，證明 calibration summary 沒有偷偷回退到 guardrailed raw-best window。**Heartbeat #664 再補一條硬約束**：training-side TW weighting（`model/train.py::load_training_data()`）也必須消費同一份 guardrail；當 `recent_drift_report.json` 的 primary window 出現 `constant_target` / `regime_concentration` 時，必須對 polluted recent tail 做 damping，並把 `tw_guardrail={recommended_best_n, raw_best_n, primary_window, damped_recent_rows, damp_factor, guardrail_reason}` 持久化到 `model/ic_signs.json`，避免 training math 又偷偷回退成「最新 slice 永遠最可信」。

**Regime-aware IC fallback contract（Heartbeat #630）**：`scripts/regime_aware_ic.py` 必須以 `feat_mind` tertiles 作為首選 regime split，但當 canonical rows 的 `feat_mind` 缺值時，不可直接把 row 丟進 `neutral`。必須回退到 `features_normalized.regime_label`，並把 `regime_meta / regime_counts / fallback_rows` 寫入輸出 JSON，否則 heartbeat 會把 analysis artifact 誤判成市場 regime 崩壞，污染 P0/P1 優先級。

### 3. 標籤層
根據未來報酬建立多 horizon 標籤，並以 `simulated_pyramid_win` 作為 canonical 主 KPI；`label_spot_long_win` 僅保留 path-aware 比較診斷；`sell_win` 僅保留 legacy 相容欄位。

**Canonical consumer rule（Heartbeat #615）**：Leaderboard / target-comparison 類資料載入應優先以 `simulated_pyramid_win` 作為 row gate；`label_spot_long_win` 僅保留比較欄位，不得再作為 canonical dataset 的必要條件。

**Decision-quality label contract（Heartbeat #639）**：canonical labels 不得只剩 `simulated_pyramid_win + simulated_pyramid_pnl + simulated_pyramid_quality` 的半成品語義。`labels` 現在還必須持久化：
- `simulated_pyramid_drawdown_penalty`
- `simulated_pyramid_time_underwater`

這兩個欄位由 labeling pipeline 在生成金字塔路徑標籤時一併計算，heartbeat 也必須驗證它們在 active horizons（240m / 1440m）上有非空覆蓋，避免「說要低回撤 / 低深套，DB 卻沒有顯式欄位」的假對齊。

### 4. 模型層
使用特徵做交易決策與現貨 long 加碼判斷，允許 abstain 與 regime-aware weights。

**Decision-quality contract（2026-04-10 strategy review）**：模型層不可只回答「會不會贏」。canonical `simulated_pyramid_win` 已完成目標對齊，但下一階段必須把模型輸出升級成 **交易品質評分**，至少能區分：
- 勝率/是否獲利
- pnl quality（賺得是否夠乾淨）
- drawdown penalty（中間承受的回撤）
- time underwater（解套所需時間）

這樣模型學到的就不是單純 binary 結果，而是更貼近使用者真實偏好的「高勝率、低回撤、低深套」交易。

**Two-stage decision contract（2026-04-10 strategy review）**：正式決策流程應拆成兩層，而不是單段式 entry rule：
1. **4H regime gate**：先判斷目前市場背景是否允許 spot-long 金字塔（ALLOW / CAUTION / BLOCK）
2. **short-term entry-quality score**：只在 gate 允許時，才用短線 technical / microstructure 特徵決定進場品質與層數

這個 contract 的目的，是避免在錯的高時間框架背景裡，讓看似漂亮的短線訊號繼續造成深套或高回撤。

**Confidence-based sizing contract（2026-04-10 strategy review）**：模型輸出除了進/不進，還必須逐步演化成 `size / layer_count` 決策依據。低品質訊號只允許首層，強訊號才允許完整 20/30/50 金字塔；倉位本身就是回撤控制器，不可再完全與信號品質脫鉤。

**Live predictor decision-profile contract（Heartbeat #640 / #692 / #694 / #699）**：`model/predictor.py::predict()`、`scripts/hb_predict_probe.py`、`/predict/confidence` 必須共同輸出 `phase16_baseline_v2` contract，而不是只剩 signal/confidence：
- `regime_gate`（ALLOW / CAUTION / BLOCK）
- `entry_quality`
- `entry_quality_label`
- `allowed_layers`
- `decision_quality_calibration_scope`
- `decision_quality_scope_diagnostics`
- `recent500_regime_counts` / `recent500_dominant_regime` inside each scope diagnostic
- `decision_quality_calibration_window`
- `decision_quality_sample_size`
- `decision_quality_guardrail_applied`
- `decision_quality_guardrail_reason`
- `decision_quality_narrowed_pathology_applied`
- `decision_quality_narrowed_pathology_scope`
- `decision_quality_narrowed_pathology_reason`
- `model_route_regime`
- `expected_win_rate`
- `expected_pyramid_pnl`
- `expected_pyramid_quality`
- `expected_drawdown_penalty`
- `expected_time_underwater`
- `decision_quality_score`
- `decision_quality_label`
- `decision_profile_version`

其中 quality-related 欄位目前不是直接多目標模型輸出，而是用 canonical **1440m historical labels** 按 `regime_gate + entry_quality_label`（不足時 fallback 到 `regime_gate / entry_quality_label / global`）做 calibrated expectation layer。這層的目的，是讓 live path 直接說出「這筆 setup 在歷史上通常贏多少、回撤多深、會不會久套」，把 canonical quality semantics 從 DB / leaderboard 往前推到即時 API。**Heartbeat #663 補充兩條硬約束**：
1. calibration layer 不得偷用 guardrailed recent-window，必須明確輸出 `decision_quality_calibration_window / decision_quality_guardrail_*` 來證明它消費的是 `dw_result.json` 的 `recommended_best_n`；
2. regime-model routing 不得再用另一套 heuristic 對外說一個 regime、實際走另一個 model path；`model_route_regime` 必須與 live decision profile 的 regime label 一起可見。
**Heartbeat #666 再補一條 calibration-scope contract**：即使整體 calibration window 已 guardrail 到 `recommended_best_n`，若最窄的 `regime_gate+entry_quality_label` bucket 仍出現 `constant_target` 或 `label_imbalance`，predictor 也不得直接輸出該 bucket 的 expectation；必須拒絕該 bucket、回退到更廣的 `regime_gate / entry_quality_label / global` lane，並把 `decision_quality_scope_guardrail_applied / reason / alerts` 一起輸出，避免 live API 再次被 polluted slice 的高勝率假象污染。
**Heartbeat #667 再補 execution contract**：guardrail 不得只停留在 expectation metadata。`model/predictor.py::predict()` 現在必須把 `decision_quality_label` 與 `decision_quality_guardrail_applied` 轉成 live execution sizing 限制：輸出 `allowed_layers_raw / allowed_layers / execution_guardrail_applied / execution_guardrail_reason`，並在 `C/D` quality 或 guardrailed calibration 狀態下主動壓低層數（必要時降到 0/1 層），避免 polluted recent window 仍驅動過度加碼。
**Heartbeat #715 再補 overextended-structure veto contract**：`_compute_live_regime_gate_debug()` / `_compute_live_regime_gate()` 與 `backtesting.strategy_lab._compute_regime_gate()` 不得再把「越遠離 4H 下緣越安全」當成單調真理。當 `feat_4h_bb_pct_b >= 1.0`、`feat_4h_dist_bb_lower >= 10`、`feat_4h_dist_swing_low >= 11` 同時成立時，這代表 bull `ALLOW+D` lane 進入已驗證的 overextended pocket，必須直接落到 `structure_overextended_block`；live predictor、Strategy Lab 與 gate-path diagnostics 都要共用這條 veto，避免 runtime 只靠後段 D-label guardrail 擋單而 gate 本身仍宣稱 ALLOW。
**Heartbeat #700 再補 narrowed-pathology clamp contract**：當 `regime_label+entry_quality_label` 這種更窄的當前 runtime lane 已經被辨識為 pathological，不得只用它的 aggregate lane average 去下修 expectation。`_narrowed_regime_scope_downside_guardrail()` 現在還必須吃進該 narrowed lane 的 `recent_pathology.summary`，直接用最近病灶視窗的 `win/pnl/quality` 去壓低 live contract，否則 runtime 仍會把 bull-only `100x0` collapse pocket 包裝成較溫和的平均值。
**Heartbeat #674 再補 same-scope pathology contract**：即使 calibration scope 已 fallback 到較寬的 `regime_gate` / `global` lane，也不得讓 broader history 掩蓋 chosen lane 的最近負向 canonical pocket。`model/predictor.py::_summarize_decision_quality_contract()` 現在必須對 chosen rows 再做 recent-window stress check；若近期候選視窗（至少 100/250/500 rows）落入 `constant_target / label_imbalance` 且 `avg_pnl` 或 `avg_quality` 已轉負，必須把**最嚴重且最持久**的 pathology 直接回寫到 `expected_win_rate / expected_pyramid_pnl / expected_pyramid_quality / drawdown_penalty / time_underwater`，並暴露 `decision_quality_recent_pathology_*` 欄位與 chosen window 起迄時間。**Heartbeat #680 再補 adverse-streak evidence contract**：same-scope pathology summary 不得只回報 mixed window 的平均值或最後尾端 streak；必須同步輸出該視窗內最長 adverse target streak（例如 `224x0`）並把它寫進 `decision_quality_guardrail_reason`，避免 runtime / issue / heartbeat 都被尾端 rebound 誤導。**Heartbeat #683 再補 sibling-window live contract**：same-scope pathology summary 還必須同步輸出 `reference_window_comparison = {prev_win_rate, Δquality, Δpnl, top_mean_shift_features}`，而且這份 artifact 必須直接進入 `decision_quality_recent_pathology_reason` 與 `scripts/hb_predict_probe.py`。也就是說，live predictor 不得只知道「最近很差」，還要知道「和前一個等長 sibling window 相比是如何塌陷，以及是哪幾個 4H 結構欄位在塌陷」。`_apply_live_execution_guardrails()` 也必須在這個 flag 打開時允許直接把 live deployment 壓到 `allowed_layers=0`，避免 runtime 再次被 broader historical average 稀釋成假樂觀。
**Heartbeat #712 pocket-outcome evidence contract**：`_summarize_gate_path()` / `spillover_gate_path` / `exact_gate_path` 不得只回報 structure bands。它們現在還必須同步輸出 `target_counts / pnl_sign_counts / quality_sign_counts / canonical_true_negative_rows/share`，讓 heartbeat 能 machine-check worst spillover pocket 究竟是 canonical 真負樣本（應該被 gate 擋下）還是 gate 過嚴誤傷，而不是只憑 `avg_structure` 或 threshold band 猜測。
Heartbeat #650 起，`web/src/components/ConfidenceIndicator.tsx` 與 `web/src/pages/Dashboard.tsx` 也必須直接消費這組欄位，首頁 live card 不得再回退成舊的二元 confidence/做空 copy。Heartbeat #695 補充：scope diagnostics 不能只告訴 heartbeat 哪條 lane 壞掉，還要告訴它**壞 pocket 是單一 regime 還是 broad calibration lane**；因此 `decision_quality_scope_diagnostics` 內每條 scope 都必須持久化 `recent500_regime_counts` 與 `recent500_dominant_regime`，並把同樣的 regime-mix 證據帶進 `pathology_consensus / worst_pathology_scope`。Heartbeat #702 再補一條 exact-lane contract：`decision_quality_scope_diagnostics` 必須額外提供 **`regime_label+regime_gate+entry_quality_label`**，讓 heartbeat / probe / auto-propose 能明確區分「current live bull+ALLOW+D」與「broader bull+D pathology」是否其實是不同 bucket。這樣 live probe、auto-propose、ISSUES 才能直接 machine-check「`regime_label+entry_quality_label` 是 bull-only 147 rows，而 exact `regime_label+regime_gate+entry_quality_label` 只剩 24 rows」，避免 heartbeat 再把 broader pathology 誤報成 current live ALLOW path。Heartbeat #703 再補 **gate-composition contract**：scope diagnostics 不得只停在 regime mix；每條 scope 還必須同步輸出 `avg_drawdown_penalty / avg_time_underwater / recent500_gate_counts / recent500_dominant_gate / recent500_regime_gate_counts / recent500_dominant_regime_gate`。目的是讓 heartbeat 直接看懂 broader bull+D 是 `bull|BLOCK + bull|CAUTION + bull|ALLOW` 哪一段在拖垮 quality，而不是只知道它是「bull-only bad lane」。**Heartbeat #705 再補 spillover contract**：凡是比 exact live lane 更寬的 scope（例如 `regime_gate+entry_quality_label`、`regime_label+entry_quality_label`、`entry_quality_label`），還必須輸出 `spillover_vs_exact_live_lane = {extra_rows, extra_row_share, extra_gate_counts, extra_regime_gate_counts, extra_dominant_gate, extra_dominant_regime_gate, win_rate_delta_vs_exact, avg_pnl_delta_vs_exact, avg_quality_delta_vs_exact, ...}`。這讓 heartbeat 不只知道「broader lane 比 exact lane 差」，而是能 machine-read 地回答**多出的哪些 gate pocket 在拖垮結果、拖垮多少**；Heartbeat #705 已用它定位出 `bull+D` 相對 exact `bull+ALLOW+D` 的 123-row spillover 幾乎都落在 `bull|BLOCK` / `bull|CAUTION`。**Heartbeat #713 再補 exact-live-lane toxicity contract**：治理層與 auto-propose 必須把 `exact_live_lane=(rows/wr/q/dd/tuw/targets/true_negative_rows/final_gate)` 與 `exact_lane_status=toxic_allow_lane` 一起寫回，避免治理只盯 spillover `bull|BLOCK` pocket。**Heartbeat #714 再把這條 exact toxic lane contract 推進到 runtime**：`model/predictor.py::_summarize_decision_quality_contract()` 現在必須額外輸出 `decision_quality_exact_live_lane_toxicity_applied / status / reason / summary`，而 `_apply_live_execution_guardrails()` 必須把這類 `ALLOW` 但 canonical 真負樣本過高的 exact lane 明確轉成 `execution_guardrail_reason=exact_live_lane_toxic_allow_lane_blocks_trade`。也就是說，exact toxic lane 不能再只存在於 docs / auto-propose / scope diagnostics；live predictor payload 本身必須承認它，並把它變成 runtime 縮手信號。 

**Backtest decision-quality contract（Heartbeat #651 / #652）**：`server/routes/api.py::api_backtest()` 不得再只回傳 ROI / 勝率 / PF 這種 legacy summary，也不得默默依賴 `feat_eye_dist` 等舊欄位語義。它現在必須直接使用 canonical core features (`feat_eye`~`feat_mind`) 建立回測 entry，並在 response 中同步輸出：
- `decision_contract = {target_col, target_label, sort_semantics, decision_quality_horizon_minutes}`
- `avg_entry_quality`
- `avg_allowed_layers`
- `dominant_regime_gate`
- `avg_expected_win_rate`
- `avg_expected_pyramid_quality`
- `avg_expected_drawdown_penalty`
- `avg_expected_time_underwater`
- `avg_decision_quality_score`
- `decision_quality_label`
- `decision_quality_sample_size`

這組欄位由 `web/src/components/BacktestSummary.tsx` 與 `web/src/pages/Backtest.tsx` 共同顯示；其中 standalone Backtest trade log 也必須保留 `entry_timestamp / regime_gate / entry_quality_label / entry_quality / allowed_layers / reason`，讓 Dashboard 回測卡、獨立回測頁、live predictor 與 Strategy Lab 共用同一套 canonical decision-quality semantics，而不是首頁 live card 已升級、其他回測 surface 仍停留在 ROI-only。**Heartbeat #653 補充 contract**：app shell (`web/src/App.tsx`) 必須真的把 `/backtest` route 掛到 `Backtest` page 並在 nav 曝露入口；若 router 仍 redirect 到 `/lab`，即使 page/component 已完成也視為 contract 未落地。**Heartbeat #654 regression guard**：`tests/test_frontend_decision_contract.py` 必須固定驗證 `/backtest` nav/route 存在，且 Dashboard / Backtest / StrategyLab 仍保留 canonical decision-quality fields，避免 UI contract 再次只靠人工 smoke test 維持。**Heartbeat #694 補充 4H parity guard**：Strategy Lab / API strategy runner / benchmark path 不得再把 `bias50` 傳進 regime-gate 的 `bias200` 位置，也不得把 shared 4H collapse-pocket features 留在 probe 層而不進 entry-quality 計算；`tests/test_api_feature_history_and_predictor.py` 與 `tests/test_strategy_lab.py` 現在鎖住這個 parity。 

**Dashboard 4H structure panel contract（Heartbeat #656）**：`web/src/pages/Dashboard.tsx` 的 4H 結構卡不得再用手寫 `bias50 -> Layer 3 / 買入時機` 文案充當主決策。該卡現在只能把 4H raw 指標當作 `結構背景`，真正的進場語義必須直接引用 live predictor 的 `regime_gate + entry_quality + allowed_layers`；若 raw 4H context 與 canonical gate 衝突，UI 必須明示「以 decision-quality contract 為主」。這個 contract 也必須由 `tests/test_frontend_decision_contract.py` 固定鎖住，避免首頁再次出現兩套互相衝突的主決策文案。
**Leaderboard objective contract（Heartbeat #638 / #639 / #642）**：`backtesting/model_leaderboard.py` 與 `/api/models/leaderboard` 不可再只用 ROI / overfit gap / volatility 當主排序語義。當前 composite score 與 API payload 至少要同步輸出以下 decision-aware components：
- `avg_entry_quality`
- `avg_allowed_layers`
- `avg_trade_quality`
- `avg_decision_quality_score`
- `avg_expected_win_rate`
- `avg_expected_pyramid_quality`
- `avg_expected_drawdown_penalty`
- `avg_expected_time_underwater`
- `regime_stability_score`
- `max_drawdown_score`
- `profit_factor_score`
- `overfit_penalty`

Heartbeat #642 起，leaderboard 不只「能讀到」 canonical labels 中的 `simulated_pyramid_drawdown_penalty` / `simulated_pyramid_time_underwater`；它還必須在每個 fold 的**實際 trade entry timestamps** 上聚合這些欄位，計算與 predictor 對齊的 `avg_decision_quality_score`，並把這組欄位序列化到 API payload。Heartbeat #643 已把 Strategy Lab 模型排行榜前端摘要同步切到這組 canonical decision-quality semantics；Heartbeat #644 再把 `/api/strategies/leaderboard`、`/api/strategies/{name}` 與 Strategy Lab 的**策略排行榜主表**一起升級為同一組 `avg_decision_quality_score + avg_expected_*` contract。Heartbeat #645 進一步要求 `/api/strategies/{name}`、`/api/strategies/run` 與前端 active strategy summary 一律攜帶 `decision_contract = {target_col, target_label, sort_semantics, decision_quality_horizon_minutes}`，讓「剛跑完的策略」與「已儲存策略詳情」都使用同一套 canonical 語義，而不是只在 leaderboard 中成立。Heartbeat #649 再把 Strategy Lab 的 **side-by-side compare panel** 也切到相同 contract，固定比較 `DQ / expected win / drawdown penalty / time underwater / allowed layers / ROI`，避免任何 compare surface 回退成 ROI-only 文案。**Heartbeat #655 補充 UI fallback contract**：若 Strategy Lab 任一 visible summary / ranking reason 拿不到 canonical DQ 欄位，不得默默退回普通 `ROI · 勝率` 摘要，而必須顯式顯示 `⚠️ canonical DQ 缺失，暫退回 legacy ROI...`，並把 ROI / 勝率 / PF 區塊標成 `Legacy execution metrics（僅輔助 / tie-breaker）`。這樣前端可見層才能把 fallback 視為 regression signal，而不是正常主語義。剩餘缺口縮小到更深的 Dashboard 摘要卡與未來新增比較入口。

**Core-vs-research signal contract（2026-04-10 strategy review）**：主模型與主 UI 必須區分兩類信號：
- **核心信號**：4H 結構 + 高 coverage technical（可直接參與主決策）
- **研究信號**：sparse-source / 低 coverage / forward-archive 中的特徵（只可作 overlay、bonus、veto 或研究用途）

若不分層，系統會把成熟度不足的 alpha source 誤混入主決策，造成假信心。

**Feature maturity contract（Heartbeat #647 / #648）**：`feature_history_policy.py` / `/api/features/coverage` / `FeatureChart.tsx` / `Dashboard.tsx` / `AdviceCard.tsx` 現在共同使用 `maturity_tier = core | research | blocked` 與 `score_usable` 的同一套語義。FeatureChart composite score / entry-reduce markers 只能使用 `score_usable=true` 的 core features；Dashboard 雷達與 AdviceCard 則必須直接揭露 `核心 / 研究 / 阻塞` 摘要，明講 research / blocked 只作 overlay / 排障，禁止把 auth-blocked / snapshot-only sparse-source 特徵誤包裝成與核心訊號同權的主決策依據。

**Model feature parity contract（Heartbeat #633 / #642）**：`model/train.py`、`model/predictor.py`、`scripts/full_ic.py`、`load_model_leaderboard_frame()` 必須共用同一個 canonical base feature semantics。當 DB / preprocessor 新增可訓練特徵（例如 `feat_4h_bias200`、`feat_4h_dist_bb_lower`、`feat_4h_vol_ratio`）時，不允許只更新 schema 或 coverage/UI；訓練、推論、IC diagnostics、leaderboard frame 必須同輪一起升級，否則 heartbeat 會落入「資料已存在但模型、診斷、ranking 其中一條路仍忽略」的假進度。

**Sparse 4H inference alignment contract（Heartbeat #633）**：predictor 不可直接使用 latest dense row 上的 raw 4H 欄位，因為 4H features 在 dense rows 上可能是 sparse/NULL。`load_latest_features()` 必須套用與 training 相同的 asof alignment（目前沿用 `model.train._align_sparse_4h_features()`）來生成 base + lag 4H features；若 recent 4H rows 在 DB 已 stale，應先 backfill 4H history，而不是讓推論默默退回 0/NULL。

**Predictor probe contract（Heartbeat #634 / #635 / #691 / #692 / #693）**：repo 內必須保留可直接重跑的 live inference probe（目前為 `scripts/hb_predict_probe.py`），固定輸出 `target_col / used_model / canonical 4H feature non-null count / 4H lag non-null count`。這個 probe 必須能在 repo 根目錄直接用 `python scripts/hb_predict_probe.py` 執行，不得要求 heartbeat 額外手補 `PYTHONPATH=.`；否則文件會宣稱可重跑、實際上卻只在特定 shell 前提下可用。Heartbeat 不可再引用一次性臨時 probe 檔名作為唯一驗證證據。Heartbeat #691 再補上持久化約束：fast heartbeat 必須把 probe JSON 寫到 `data/live_predict_probe.json` 並摘取成 `live_predictor_diagnostics`，讓 auto-propose / ISSUES / heartbeat summary 能直接引用同一份 live runtime contract。Heartbeat #692 再補 **scope-matrix 約束**：probe payload 還必須輸出 `decision_quality_scope_diagnostics`，至少覆蓋 `regime_gate+entry_quality_label`、`regime_label+entry_quality_label`、`entry_quality_label`、`global` 等 lane 的 rows / alerts / recent-pathology 摘要，讓 live-path blocker 可以直接比較「更窄 lane 更糟」還是「只有廣 scope 壞掉」，避免 heartbeat 再次退回 ad-hoc 腳本調查。Heartbeat #693 再補 **scope-consensus 約束**：`decision_quality_scope_diagnostics` 不得只是一堆平行 lane rows；它還必須輸出 `pathology_consensus={shared_top_shift_features, worst_pathology_scope, pathology_scopes}`，把多個 pathological scopes 共同指向的 4H collapse feature（目前為 `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`）與最差 lane 一起 machine-check 化，確保後續 heartbeat 直接沿 shared root-cause 做 patch，而不是反覆做 ad-hoc scope 比較。

**Training warning/logging hygiene contract（Heartbeat #634）**：`model/train.py` 的 cross-feature engineering 不可再用大量逐欄 `frame.insert` 方式製造 pandas fragmentation warnings；training stderr 應盡量只保留真實失敗訊號。同時 recent-vs-global IC log 必須分別輸出真實 `tw_ic_summary` 與 `core_ic_summary`，避免 heartbeat 被假觀測污染。

### 5. 回測層
驗證不同特徵組合、不同市場狀態與不同入場／加碼／出場閾值下的表現。

### 6. 可視化層
顯示每個特徵的 IC、勝率、風險貢獻、spot-long 勝率、回測摘要與會議整理。

---

## 目錄結構

```
Poly-Trader/
├── data_ingestion/              ← 數據收集器 / backfill
│   ├── collector.py             ← 主收集器（整合所有來源）
│   ├── raw_events.py            ← raw event schema / 寫入介面（建議新增）
│   ├── market.py                ← K 線 / funding / OI / liquidation
│   ├── social.py                ← Twitter / RSS / 社群文本
│   ├── prediction.py            ← Polymarket / prediction markets
│   └── macro.py                 ← DXY / VIX / futures / event calendar
├── feature_engine/
│   └── preprocessor.py          ← 特徵工程 v4（IC-validated + versioned）
├── database/
│   └── models.py                ← ORM：raw_events / features / labels
├── model/
│   ├── predictor.py             ← 預測器（spot-long aware）
│   └── train.py                 ← 訓練腳本
├── backtesting/
│   ├── engine.py                ← 回測引擎（spot_long_win_rate / regime aware）
│   ├── metrics.py               ← 績效指標
│   └── optimizer.py             ← 參數優化
├── analysis/
│   ├── sense_effectiveness.py   ← IC / 分位數勝率 / regime analysis
│   └── regime.py                ← 市場狀態分類（建議新增）
├── dashboard/
│   └── app.py                   ← 儀表板（總覽 / 回測 / 特徵 / 會議）
├── server/
│   └── senses.py                ← 特徵引擎
└── tests/
```

---

## 特徵架構 v4（建議）

| # | 特徵 | 特徵主軸 | 資料源 | 用途 |
|---|------|----------|--------|------|
| 1 | Eye | 趨勢 / 方向 | K 線 / 報酬 | 判斷主方向 |
| 2 | Ear | 波動 / 節奏 | K 線 / ATR | 判斷躁動 |
| 3 | Nose | 均值回歸 / 自相關 | K 線衍生 | 判斷過熱 / 過冷 |
| 4 | Tongue | 噪音 / 波動味覺 | K 線 / wick-body | 判斷亂跳 |
| 5 | Body | 結構位置 | range / breakout | 判斷所處階段 |
| 6 | Pulse | 資金壓力 | funding / OI / liquidation | 判斷多空擁擠 |
| 7 | Aura | 複合結構 | vol×autocorr / funding×price | 判斷轉折區 |
| 8 | Mind | 長周期風險 | funding z / macro proxy | 判斷風險狀態 |
| 9 | Whisper | 討論量 / 爆量 | Twitter / RSS / 社群 | 判斷敘事熱度 |
|10 | Tone | 情緒極性 | Text sentiment | 判斷正負情緒 |
|11 | Chorus | 共識 / 分歧 | 文本聚類 / sentiment spread | 判斷市場一致性 |
|12 | Hype | 炒作 / 噪訊 | 重複帖 / influencer spread | 判斷熱炒 |
|13 | Oracle | 預期變化 | Polymarket | 判斷市場預期 |
|14 | Shock | 事件驚訝程度 | news / calendar | 判斷事件衝擊 |
|15 | Tide | 風險偏好 | DXY / VIX / futures | 判斷 risk-on / risk-off |
|16 | Storm | 宏觀壓力 | macro news / rates shock | 判斷宏觀波動 |

---

## 資料庫 Schema

### raw_events
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| timestamp | DATETIME | 事件時間 |
| source | STRING | twitter / polymarket / news / macro / exchange |
| entity | STRING | BTC / ETH / FED / ETF / event |
| subtype | STRING | sentiment / probability / funding / etc. |
| value | FLOAT | 原始值 |
| confidence | FLOAT | 來源可信度 |
| quality_score | FLOAT | 清洗後品質分數 |
| language | STRING | 語言 |
| region | STRING | 區域 |
| payload_json | JSON/TEXT | 原始 payload |
| ingested_at | DATETIME | 寫入時間 |

### features_normalized
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| timestamp | DATETIME | 時間戳 |
| symbol | STRING | 交易對 |
| feat_eye ~ feat_storm | FLOAT | 特徵特徵 |
| regime_label | STRING | trend / chop / panic / event |
| feature_version | STRING | 特徵版本 |

### labels
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| timestamp | DATETIME | 時間戳 |
| symbol | STRING | 交易對 |
| horizon_minutes | INTEGER | 預測窗口 |
| future_return_pct | FLOAT | 未來收益率 |
| future_max_drawdown | FLOAT | 未來最大回撤 |
| future_max_runup | FLOAT | 未來最大漲幅 |
|| label_spot_long_win | INTEGER | 現貨 long 是否獲利 |
| label_up | INTEGER | 漲跌分類 |
| regime_label | STRING | 市場狀態 |

---

## 歷史補資料方案

### 1. 可回補資料
- K 線 / volume / funding / OI / liquidation
- Polymarket 歷史事件
- 宏觀資料（DXY / VIX / futures / calendar）
- GDELT / RSS / 部分新聞歷史

### 2. 只能前向累積資料
- Twitter / X 即時流
- Telegram / Discord 即時訊號
- 私域社群事件

### 3. 補資料流程
1. 先寫 raw_events，不直接覆蓋。
2. 統一 timestamp、entity、source。
3. 依版本重算 features_normalized。
4. 依 horizon 重生 labels。
5. 重新回測與重訓。

### 4. 原則
- raw 永遠保留
- 特徵版本化
- labels 可重算
- 嚴禁未來函數洩漏
- 來源可信度需可追溯

---

## 回測評估指標

### 交易績效
- total return
- annualized return
- max drawdown
- sharpe
- calmar
- profit factor
- expectancy
- trade count

### 現貨 long 勝率
- spot_long_win_rate = profitable_longs / total_longs
- average long profit
- average long loss
- long precision
- long recall
- forward long win rate

### 模型品質
- coverage
- abstain rate
- confidence calibration
- regime-wise performance
- false sell rate
- delayed sell rate

### 特徵品質
- IC / rank IC
- stability
- regime-wise IC
- feature turnover
- mutual information

---

## API 端點

| 端點 | 方法 | 說明 |
|------|------|------|
| `/api/senses` | GET | 所有特徵分數 + 建議 |
| `/api/senses/config` | GET/PUT | 特徵配置 |
| `/api/recommendation` | GET | 交易建議 |
| `/api/predict/confidence` | GET | 信心分層預測 |
| `/api/backtest` | GET | 回測結果 |
| `/api/model/stats` | GET | 模型統計 |
| `/api/chart/klines` | GET | K 線數據 |
| `/ws/live` | WS | 即時推送 |
```

---

## 文檔關聯

| 文檔 | 用途 |
|------|------|
| [AI_AGENT_ROLE.md](AI_AGENT_ROLE.md) | AI 角色、紀律、邊界 |
| [HEARTBEAT.md](HEARTBEAT.md) | 心跳詳細流程 |
| [ISSUES.md](ISSUES.md) | 問題追蹤 |
| [PRD.md](PRD.md) | 產品需求 |
| [ROADMAP.md](ROADMAP.md) | 發展路線 |


## 決策層補充

在特徵層與回測層之間，新增兩個關鍵控制點：

### 7. 時間對齊層
- 負責價格、特徵、標籤的 timestamp 對齊。
- 支援 nearest-match 與資料窗覆蓋檢查。
- 若樣本重疊不足，回傳明確 empty-state，而不是靜默空圖。

### 8. 模型校準層
- 負責 confidence calibration、regime-aware model selection、abstain 門檻。
- 用來區分「特徵有效」與「模型輸出不準」。
- 不可直接把特徵分數當成最終推薦分數，需保留校準與版本資訊。

### 9. 文件治理與心跳閉環
- 每次心跳後，必須同步更新 `HEARTBEAT.md`、`ISSUES.md`、`ROADMAP.md`，必要時修正 `ARCHITECTURE.md`。
- `HEARTBEAT.md` 現在是嚴格的 project-driver 憲章：流程固定為 `facts → strategy decision → 六帽/ORID → patch → verify → docs sync → next gate`。
- 使用六帽 + ORID 先把問題分層，再把 P0/P1 變成可執行 patch。
- 若本輪只得到「未達標」而沒有修復，視為流程不完整，不算閉環。
- 若一次心跳缺少 `patch + verify + 文件同步 + 下一輪 gate` 任一項，整輪視為失敗。

---

## API 端點補充

| 端點 | 方法 | 說明 |
|------|------|------|
| `/api/predict/confidence` | GET | 綜合信心預測與校準後信號 |
| `/api/backtest` | GET | 回測結果與 spot_long_win_rate（legacy sell_win_rate） |
| `/api/senses` | GET | 特徵分數 + 建議 |

