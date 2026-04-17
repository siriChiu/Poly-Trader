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

**Fast heartbeat contract（Heartbeat #617 / #659 / #661 / #688 / #689 / #691 / #696 / #722 / #728 / #729 / #743）**：`python scripts/hb_parallel_runner.py --fast` 必須可直接在 cron 執行，不依賴額外 `--hb` 參數；fast summary 仍需包含 DB counts、canonical IC 腳本結果與 `source_blockers` 摘要，確保快檢查模式不是「只剩數字」的半閉環。Heartbeat #722 再補 **feature-family / bull-pocket governance**：fast heartbeat 也必須自動執行 `scripts/feature_group_ablation.py` 與 `scripts/bull_4h_pocket_ablation.py`，刷新 `data/feature_group_ablation.json`、`data/bull_4h_pocket_ablation.json` 與對應 markdown，並把 `recommended_profile / current_full delta / bull live bucket support` 持久化到 heartbeat summary，避免 collect/IC/drift 都是新的、但 shrinkage / bull blocker 證據仍停在舊 snapshot。Heartbeat #733 再補 **exact-bucket root-cause persistence**：bull pocket artifact 不可只回報 gap；還必須 machine-read `support_pathology_summary.exact_bucket_root_cause / root_cause_interpretation / broad_current_live_structure_bucket_rows / broad_dominant_regime`，明確區分「exact bucket 完全缺失」、「只存在 spillover regime」、與「已出現 exact rows 但仍低於 minimum support」三種情境，避免 heartbeat 把少量 exact rows 誤寫成 blocker 已解除。Heartbeat #728 再補 **leaderboard candidate governance**：fast heartbeat 也必須同步執行 `scripts/hb_leaderboard_candidate_probe.py`，刷新 `data/leaderboard_feature_profile_probe.json`，並把 `leaderboard_selected_profile / global_recommended_profile / train_support_aware_profile / dual_profile_state / blocked_candidate_profiles / live_current_structure_bucket_rows` 持久化到 heartbeat summary，避免 bull live blocker 已經變了、但 leaderboard winner vs train fallback 還停留在舊 probe。Heartbeat #743 再補 **current-vs-snapshot alignment recency contract**：candidate probe 不得只因 `leaderboard_snapshot_created_at` 舊就把所有 mismatch 一律標成 stale；必須同時輸出 `alignment_evaluated_at / current_alignment_inputs_stale / current_alignment_recency / artifact_recency`。當 current inputs 已是最新（例如 train、bull pocket、feature ablation 都比 probe evaluation 更舊而非更新），`dual_profile_state` 必須反映**當前**治理差異（例如 exact-supported 後仍 fallback），而舊 snapshot 只能留在 `artifact_recency` 當背景訊號。Heartbeat #729 再補 **warning hygiene**：`scripts/hb_leaderboard_candidate_probe.py` 必須抑制已知 sklearn feature-name warnings（`X has feature names, but ... was fitted without feature names`），避免 fast heartbeat / cron stderr 被無害 probe 雜訊淹沒；heartbeat 應保留 stderr 給真實錯誤與 blocker。Heartbeat #659 起，summary 必須持久化 `ic_diagnostics` 與 `auto_propose`；Heartbeat #661 再新增 distribution-aware drift artifact；Heartbeat #688 再補 **core-vs-research drift hygiene**：sparse-source research features 必須在 recent-drift diagnostics 中被標成 `overlay_only=research_sparse_source`，不可再混進 `unexpected_frozen` escalation，也不可在存在 core shift 時搶走 sibling-window `top_mean_shift_features` 主證據；Heartbeat #689 再補 **stale regime-drift recovery**：若 current run 已回到 `TW-IC <= Global IC + 2`，`scripts/auto_propose_fixes.py` 必須自動 resolve `#H_AUTO_REGIME_DRIFT`，避免 `issues.json` / heartbeat docs 留下與當前 run 不一致的假 blocker；Heartbeat #691 再補 **live runtime governance**：fast heartbeat 必須同步執行 `scripts/hb_predict_probe.py`、持久化 `data/live_predict_probe.json`、並在 summary 寫入 `live_predictor_diagnostics`，讓 auto-propose 能把 live same-scope pathology 升級成 `#H_AUTO_LIVE_DQ_PATHOLOGY`，而不是只看 global drift artifact。Heartbeat #696 再補 **narrowed-lane governance**：即使 `decision_quality_recent_pathology_applied=false`、broad calibration lane 健康，只要 `decision_quality_scope_diagnostics.pathology_consensus.worst_pathology_scope` 已證明存在嚴重的 narrowed pathology lane（例如 bull-only D pocket），auto-propose 也必須升級 `#H_AUTO_LIVE_DQ_PATHOLOGY`。
- `ic_diagnostics = {global_pass, tw_pass, total_features, n}`
- `drift_diagnostics = {primary_window, primary_alerts, primary_summary, full_sample}`  
  （Heartbeat #676 起，`primary_summary` 內還必須包含 `target_path_diagnostics={tail_target_streak, target_regime_breakdown, recent_examples}`，讓 recent pathology 可直接追到 canonical path 時間線；**Heartbeat #680 再補 `longest_target_streak / longest_zero_target_streak / longest_one_target_streak`**，避免 mixed window 只看到尾端 rebound 而漏掉真正的 adverse pocket；**Heartbeat #682 再補 `reference_window_comparison={prev_win_rate, prev_quality, prev_pnl, top_mean_shift_features, new_*_features}`**，讓 heartbeat 能直接對比 pathology slice 與前一個等長 sibling window，而不是只知道「最近很糟」）
- `auto_propose = {attempted, success, returncode, stdout_preview, stderr_preview}`

另外，fast heartbeat 必須在 auto-propose 之前自動執行 `scripts/recent_drift_report.py`，把 canonical 1440m recent-window `label balance / dominant regime / constant-target` 寫到 `data/recent_drift_report.json`。Heartbeat #687 補充：若 recent window 的 canonical `win/pnl/quality` 很強、`avg_drawdown_penalty` 很低，而 `avg_time_underwater` 只是略高於舊 0.45 cutoff，drift classifier 仍必須維持 `supported_extreme_trend`，避免近閾值 TUW 再次把健康 canonical pocket 誤打成 `distribution_pathology`。Heartbeat #677 再補一條治理約束：feature drift diagnostics 不得把**週末或美股休市時段靜止的 macro features（VIX / DXY / NQ returns）**與**離散 4H regime features（`feat_4h_ma_order`）**直接併入 generic freeze blocker；artifact 必須顯式輸出 `expected_static_count / unexpected_frozen_count / expected_static_examples`，讓後續 auto-propose 與 heartbeat 聚焦在真正異常的 compressed/frozen core features，而不是被 market-closed 靜態值誤導。Heartbeat #1025 再補 **expected-compression provenance contract**：對 `feat_atr_pct` 這類 volatility-derived feature，recent drift artifact 不得只回報 `new_compressed`；它還必須 machine-read `expected_compressed_count / expected_compressed_examples`，並在 `raw_market_data.volatility` 也同步壓縮時標成 `underlying_raw_volatility_compression`。Heartbeat #1026 再補 **4H bias200 provenance contract**：若 `feat_4h_bias200` 在 recent bull pocket 被判成 compressed，artifact 不得直接把它丟進 `unexpected_compressed`；必須同步檢查 `raw_market_data.close_price` 與 `raw_market_data.volatility` 是否一起收縮，並把結果寫進 `expected_compressed_details.proxy_stats`。只有當價格/波動沒有同步收縮時，才可把它升級成真正的 projection blocker。Heartbeat #2026-04-16 再補 **4H bias50 provenance contract**：若 `feat_4h_bias50` 在 recent bull pocket 變成 sibling-window 的新 `compressed` 主病灶，artifact 不得先假設是單點 4H formula 失真；必須同步檢查 `raw_close_price`、`raw_volatility`、`feat_4h_rsi14`、`feat_4h_bb_pct_b`、`feat_4h_macd_hist` 是否一起收斂，並在滿足 trend-stack coherence 時把它降級成 `coherent_4h_trend_compression`。只有 bias50 自己收斂、而價格/波動與 sibling 4H trend proxies 沒有同步壓縮時，才可把它升級成真正的 projection blocker。Heartbeat #2026-04-16 再補 **4H RSI14 provenance contract**：若 `feat_4h_rsi14` 成為 recent bull pocket 的 `new_compressed`，artifact 不得先把它當成單一 oscillator 失真；必須同步檢查 `raw_close_price`、`raw_volatility`、`feat_4h_bias20`、`feat_4h_bb_pct_b`、`feat_4h_macd_hist` 是否一起收斂。只有在短趨勢 cluster 沒有共同收斂時，才可把 RSI14 升級成真正的 projection blocker；否則必須降級成 `coherent_4h_short_trend_oscillator_compression`。Heartbeat #1027 再補 **4H swing-low provenance contract**：若 `feat_4h_dist_swing_low` 在 recent bull pocket 變成低方差，不得先假設是 projection 故障；artifact 必須同步檢查 `raw_close_price`、`raw_volatility`、`feat_4h_dist_bb_lower`、`feat_4h_bb_pct_b` 是否呈現同向支撐群壓縮，並在滿足 support-cluster coherence 時把它降級成 `coherent_4h_support_cluster_compression`。只有 swing-low 自己收斂、而原始價格/波動與 sibling 4H 支撐 proxy 沒有一起壓縮時，才可把它升級成真正的 blocker。若沒有這層 provenance，heartbeat 會把健康 bull-pocket 支撐收斂誤寫成單點 4H 投影失真。Heartbeat #1028 再補 **4H lower-band-floor provenance contract**：若 `feat_4h_dist_bb_lower` 在 recent bull pocket 變成低方差，也不得立刻升級成新的 projection blocker；artifact 必須同步檢查 `raw_close_price`、`raw_volatility`、`feat_4h_bb_pct_b`、`feat_4h_dist_swing_low` 是否一起壓縮，並在滿足 band-floor coherence 時把它降級成 `coherent_4h_band_floor_compression`。只有 lower-band distance 自己收斂、而 raw price/volatility 與 sibling 4H support proxies 沒有同步收斂時，才可把它升級成真正的 blocker。若沒有這層 provenance，heartbeat 會把健康 bull-pocket 下緣收斂誤寫成新的 recent-window root cause。**Heartbeat #679 再補 persistent-pathology selection 約束**：當 `constant_target / label_imbalance` 的 severity 與 win-rate delta 同級時，primary drift window 必須優先選更持久的 recent pathology slice（例如 250 rows，而不是較短的 100 rows），避免 governance 持續低估病灶跨度。這樣後續 heartbeat / drift triage / blocker automation 才能直接 machine-read 最近兩輪的 TW-IC 狀態與污染視窗，而不是重新從 `stdout_preview` 猜字串。**Heartbeat #665 再補一條治理約束**：`scripts/auto_propose_fixes.py::load_recent_tw_history()` 在組裝 `#H_AUTO_TW_DRIFT` 歷史時，必須優先使用正式編號的 `heartbeat_<N>_summary.json`，不可讓匿名 `heartbeat_fast_summary.json` 取代上一輪 numbered heartbeat，否則 blocker escalation 會變成 `#665 -> #fast` 這種不可追蹤的假治理訊號。**Heartbeat #668 再補 drift-interpretation contract**：`recent_drift_report.json` 不得只輸出 `alerts`；每個 recent window 還必須同步輸出 `quality_metrics={avg_simulated_pnl, avg_simulated_quality, avg_dra... [truncated]

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
- `regime_gate_reason`
- `structure_quality`
- `structure_bucket`
- `entry_quality`
- `entry_quality_label`
- `entry_quality_components = {base_components, base_quality, structure_components, structure_quality, entry_quality, trade_floor, trade_floor_gap}`
- `allowed_layers_raw`
- `allowed_layers_raw_reason`
- `allowed_layers`
- `allowed_layers_reason`
- `deployment_blocker`
- `deployment_blocker_reason`
- `deployment_blocker_source`
- `deployment_blocker_details`
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

其中 quality-related 欄位目前不是直接多目標模型輸出，而是用 canonical **1440m historical labels** 做 calibrated expectation layer。校準 scope 的最低 contract 現在是：先嘗試 `regime_label+regime_gate+entry_quality_label`，再依序 fallback 到 `regime_gate+entry_quality_label / regime_label+entry_quality_label / regime_gate / entry_quality_label / global`；若 chosen scope 對當前 `structure_bucket` 支持不足，還必須再用 same-bucket metrics 把 expectation 保守夾回來。這層的目的，是讓 live path 直接說出「這筆 setup 在歷史上通常贏多少、回撤多深、會不會久套」，把 canonical quality semantics 從 DB / leaderboard 往前推到即時 API。**Heartbeat #663 補充兩條硬約束**：
1. calibration layer 不得偷用 guardrailed recent-window，必須明確輸出 `decision_quality_calibration_window / decision_quality_guardrail_*` 來證明它消費的是 `dw_result.json` 的 `recommended_best_n`；
2. regime-model routing 不得再用另一套 heuristic 對外說一個 regime、實際走另一個 model path；`model_route_regime` 必須與 live decision profile 的 regime label 一起可見。
**Heartbeat #666 再補一條 calibration-scope contract**：即使整體 calibration window 已 guardrail 到 `recommended_best_n`，若最窄的 `regime_gate+entry_quality_label` bucket 仍出現 `constant_target` 或 `label_imbalance`，predictor 也不得直接輸出該 bucket 的 expectation；必須拒絕該 bucket、回退到更廣的 `regime_gate / entry_quality_label / global` lane，並把 `decision_quality_scope_guardrail_applied / reason / alerts` 一起輸出，避免 live API 再次被 polluted slice 的高勝率假象污染。
**Heartbeat #719 再補 cross-regime spillover contract**：就算 broader lane 本身沒有 `constant_target / label_imbalance`，若它的 recent 500 rows 已被**其他 regime 主導（≥80%）**，也不得再把那條 lane 當成當前 live regime 的 calibration scope。predictor 必須明確拒絕這種 `dominant recent regime mismatch` broader lane，保留 rejection chain，並在只剩 same-regime 語義可代表 live path 時，優先保留 same-regime fallback，而不是退回 `global` 假平均。
**Heartbeat #667 再補 execution contract**：guardrail 不得只停留在 expectation metadata。`model/predictor.py::predict()` 現在必須把 `decision_quality_label` 與 `decision_quality_guardrail_applied` 轉成 live execution sizing 限制：輸出 `allowed_layers_raw / allowed_layers / execution_guardrail_applied / execution_guardrail_reason`，並在 `C/D` quality 或 guardrailed calibration 狀態下主動壓低層數（必要時降到 0/1 層），避免 polluted recent window 仍驅動過度加碼。
**Heartbeat #715 再補 overextended-structure veto contract**：`_compute_live_regime_gate_debug()` / `_compute_live_regime_gate()` 與 `backtesting.strategy_lab._compute_regime_gate()` 不得再把「越遠離 4H 下緣越安全」當成單調真理。當 `feat_4h_bb_pct_b >= 1.0`、`feat_4h_dist_bb_lower >= 10`、`feat_4h_dist_swing_low >= 11` 同時成立時，這代表 bull `ALLOW+D` lane 進入已驗證的 overextended pocket，必須直接落到 `structure_overextended_block`；live predictor、Strategy Lab 與 gate-path diagnostics 都要共用這條 veto，避免 runtime 只靠後段 D-label guardrail 擋單而 gate 本身仍宣稱 ALLOW。
**Heartbeat #718 再補 borderline-structure caution contract**：若 base gate 仍是 `ALLOW`，但 `structure_quality < 0.65`（也就是原本會落在 `q35` 的弱結構 pocket），live predictor 與 Strategy Lab 必須同步降成 `structure_quality_caution / CAUTION`。原因不是要放寬或縮緊所有 bull lane，而是 current live `ALLOW|q35` 歷史支持只有 **2 rows**，屬於不足以校準的假 ALLOW pocket；runtime 與 backtest 不得再把這類 borderline 4H 結構包裝成 permissive ALLOW lane。
**Heartbeat #739 再補 exact-lane toxic sub-bucket veto contract**：live predictor 的 decision-quality contract 不得只知道整條 exact lane 好或壞；它現在還必須 machine-read `decision_quality_exact_live_lane_bucket_verdict / reason / toxic_bucket / bucket_diagnostics`。若 exact lane 已識別出 `toxic_sub_bucket_identified`，且**當前 live structure bucket 本身就是那個 toxic bucket**，predictor 必須把它升級成 `toxic_sub_bucket_current_bucket` execution veto，直接把 `allowed_layers` 壓到 0；若當前 bucket 不是 toxic bucket，則只保留 diagnostics，不得連坐把 current bucket 一起降級。這條 contract 的目的，是把 bull `q15` 這種 lane-internal pathology 變成可執行規則，同時保護仍健康的 current `q35` pocket 不被誤傷。**Heartbeat #745 再補 single-bucket exact-lane contract**：當 exact live lane 只有當前 `structure_bucket` 一個 bucket 時，`decision_quality_exact_live_lane_bucket_verdict` 必須固定為 `no_exact_lane_sub_bucket_split`，`toxic_bucket` 必須為 `null`；不得再把單一 bucket 誤標成 `sub_buckets_present_but_not_toxic`。同輪也必須顯式輸出 `allowed_layers_reason`，讓 heartbeat 能區分「layers=0 是 entry-quality trade floor」還是「execution guardrail 額外壓層」。**Heartbeat #746 再補 entry-quality decomposition contract**：當 runtime 仍停在 `entry_quality_below_trade_floor` 時，probe / heartbeat summary / drilldown 不得只回報單一 `entry_quality` 數值。它們現在還必須 machine-read `entry_quality_components={base_components, base_quality, structure_components, structure_quality, trade_floor, trade_floor_gap}`，讓 heartbeat 能直接回答是 `feat_4h_bias50 / feat_nose / feat_pulse / feat_ear` 還是 4H structure mix 在壓低 q35 live lane，而不是再靠人工反推 raw quality 根因。
**Heartbeat #740 / #741 proxy governance contract**：當 bull current structure bucket 已出現 exact rows、但仍低於 `minimum_support_rows`，且 historical same-bucket proxy 與 current exact bucket 差距仍在可接受範圍內時，artifact / leaderboard probe / heartbeat summary / docs 不得再輸出模糊的 `proxy_boundary_inconclusive`。這時必須統一落成 `proxy_governance_reference_only_exact_support_blocked`：proxy 只可作 governance 參考，用來說明 broader same-bucket 是否被 cross-regime spillover 汙染；在 exact support 補滿前，proxy **不得**被當成 deployment 放行依據。**Heartbeat #741 再補 exact-supported 分支**：一旦 `exact_bucket_root_cause=exact_bucket_supported`，同一批 surface 必須同步改寫成 `proxy_boundary_verdict=exact_bucket_supported_proxy_not_required`，明確表示後續治理 / 驗證應直接以 exact bucket 為主，proxy 僅保留輔助比較，不再作 blocker 判讀。
**Heartbeat #1002 / #1004 / #1005 / #1015 q35 scaling / bull-cohort calibration contract**：當 current bull live path 同時滿足 `regime_gate=CAUTION`、`structure_bucket=CAUTION|structure_quality_caution|q35`、`allowed_layers_reason=entry_quality_below_trade_floor` 時，heartbeat 不得再只重述 `trade_floor_gap`。必須額外執行 `scripts/hb_q35_scaling_audit.py`，輸出 `data/q35_scaling_audit.json` / `docs/analysis/q35_scaling_audit.md`，至少 machine-read：`overall_verdict`、`structure_scaling_verdict`、`scope_applicability.{status,active_for_current_live_row,current_structure_bucket,target_structure_bucket,reason}`、`exact_lane_summary.current_bias50_percentile`、`broader_bull_cohorts.{same_gate_same_quality,same_bucket,bull_all}`、`segmented_calibration.{status,recommended_mode,exact_lane,reference_cohort,broader_bull_cohorts,runtime_contract_status}`、`counterfactuals.gate_allow_only_changes_layers`、`counterfactuals.required_bias50_cap_for_floor`。治理規則是：若 **只把 q35 CAUTION 改回 ALLOW 仍不會增加 layers**，且 current `feat_4h_bias50` 高於 exact-lane 與 broader bull cohorts 的 p90，就必須把這條 lane 明確視為 **hold-only / bias50 overheat**，不得直接放寬 q35 gate 或 trade floor；若 current bias50 雖高於 exact-lane p90、但仍落在更廣 bull cohort 的 p90 內，則應升級為 **bull cohort segmentation / bias50 calibration** 問題，下一步只能做分段 / 分位數校準研究，不能直接放寬 runtime gate。Heartbeat #1004 再加一條硬約束：artifact 必須明確輸出 **exact lane 是 overheat、但哪一個更廣 bull cohort 仍屬於 p90 內**，並用 `segmented_calibration.reference_cohort` 指定下一輪 piecewise / quantile calibration 應參照的 cohort；沒有這個 reference cohort，就不准把問題包裝成「已可校準」。**Heartbeat #1005 再補 exact-lane formula-review 分支**：一旦 current `feat_4h_bias50` 已回到 exact-lane p90 內，但 legacy 線性公式仍把 bias50 score 壓成 0，artifact 必須把 `overall_verdict` 升級成 `bias50_formula_may_be_too_harsh`，並要求 `segmented_calibration.status=formula_review_required` / `recommended_mode=exact_lane_formula_review`。這個分支允許 runtime 對 **exact-lane 高側但仍受支持** 的 q35 row 套用保守非零 bias50 score（例如 `segment=exact_lane_elevated_within_p90`），但在 entry quality 尚未跨過 trade floor 前，`allowed_layers` 仍必須維持 0，不得把公式 review 誤寫成 gate 已放寬。**Heartbeat #1015 再補 scope-applicability 約束**：若 current live row 已離開 q35（例如回到 q15 或其他 bucket），artifact 必須把 `scope_applicability.status` 改成 reference-only，並明講 q35 scaling 只能作 calibration 參考；只有 `scope_applicability.active_for_current_live_row=true` 時，heartbeat 才能把 q35 結論當成當輪 live blocker 主治理路徑。
**Heartbeat #1009 / #2026-04-16 q15 support / floor-cross legality contract**：當 current bull live path 已回到 `CAUTION|structure_quality_caution|q15` 且 blocker 來自 `unsupported_exact_live_structure_bucket_blocks_trade` 時，heartbeat 不得再只報 `remaining_gap_to_floor` 或 `best_single_component=feat_4h_bias50`。必須額外執行 `scripts/hb_q15_support_audit.py`，輸出 `data/q15_support_audit.json` / `docs/analysis/q15_support_audit.md`，至少 machine-read：`scope_applicability.{status,active_for_current_live_row,current_structure_bucket,target_structure_bucket,reason}`、`support_route.{verdict,deployable,preferred_support_cohort,release_condition,support_progress}`、`floor_cross_legality.{verdict,legal_to_relax_runtime_gate,remaining_gap_to_floor,best_single_component,best_single_component_required_score_delta}`、`component_experiment.{verdict,feature,machine_read_answer,verify_next}`、以及 `next_action`。其中 `support_progress` 必須持久化 `status / current_rows / minimum_support_rows / gap_to_minimum / previous_rows / delta_vs_previous / stagnant_run_count / escalate_to_blocker / history`，讓 heartbeat 能直接回答 q15 exact support 是在累積、停滯還是回退，而不是每輪只重述當前 rows。**Heartbeat #2026-04-16 再補歷史承接約束**：`support_progress` 的歷史比對不得只認舊的 `q15_support_audit_diagnostics` key，也不得因為 support route 從 `missing_proxy` 轉成 `present_but_below_minimum` 就中斷 bucket accumulation 判讀；同一 `current_live_structure_bucket` 的 rows 變化仍必須被視為同一條累積鏈。治理規則是：只要 current q15 exact bucket 尚未達 `minimum_support_rows`，即使 `feat_4h_bias50` 在數學上足以單點跨過 floor，也只能標成 **calibration research / governance reference**，不得單靠 component score 或 proxy rows 解除 runtime blocker；只有 exact q15 support 達標後，才允許把 component-level patch 升級成 deployment 級驗證。**Heartbeat #1021 補充**：q15 audit 不得再把 exact-supported component experiment 的可行性留在文字敘述。它現在必須 machine-read 回答 `support_ready / entry_quality_ge_0_55 / allowed_layers_gt_0 / preserves_positive_discrimination_status`；若 support 未達標，必須明確輸出 `reference_only_until_exact_support_ready`，避免 heartbeat 再把 q15 component research 誤寫成可直接放行的 runtime patch。**Heartbeat #1024 補充**：若 current live row 已離開 q15 lane（例如回到 `...|q35`），q15 audit 不得再把 `exact_supported_component_experiment_ready` 誤包裝成 current-live deployment closure；必須把狀態降成 `exact_supported_component_experiment_ready_but_current_live_not_q15`，並以 `scope_applicability.active_for_current_live_row=false` 明示它只是 standby q15 route readiness，讓 heartbeat 主焦點回到真正活躍的 current-live lane。**Heartbeat #1016 補充**：當 q35 audit 已明確判定 `bias50_formula_may_be_too_harsh`，而 current bias50 落在 exact-lane `min..p25` 的 core-normal 低側支持區間時，`model/q35_bias50_calibration.py` 也必須提供保守非零 score（`segment=exact_lane_core_band_below_p25`），不可再讓 legacy 線性公式把這類 exact-supported row 壓成 0 分，否則 q35/q15 live lane 會被誤殺成無法驗證的假 blocker。**Heartbeat #1017 補充**：當 q35 live lane 已 exact-supported、bias50 formula patch 已落地但 `allowed_layers` 仍為 0 時，`scripts/hb_q35_scaling_audit.py` 不得只回報單點 bias50 counterfactual；還必須輸出 `joint_component_experiment={verdict,machine_read_answer,best_scenario,required_bias50_cap_after_swing_uplift}`，至少覆蓋 `feat_4h_bias50 + feat_4h_dist_swing_low` 的聯合 experiment，讓 heartbeat 能 machine-read 回答「結構 uplift 是否真的縮小 floor gap、縮小後還差多少 bias50 cap」，避免下一輪又退回只看單一 bias50 的假收斂。**Heartbeat #1018 補充**：若 `joint_component_experiment` 已證明 structure uplift 幾乎不動 floor gap，audit/runner/docs 還必須同步輸出 `base_mix_component_experiment={verdict,machine_read_answer,best_scenario,required_bias50_cap_after_base_mix}`，至少覆蓋 `feat_4h_bias50 + feat_pulse (+ feat_nose)`。若這個 base-mix experiment 也仍失敗，runner/docs 不得再把主路徑描述成 generic structure closure，而要升級成 base-stack redesign / governance 問題。**Heartbeat #1019 補充**：當 `base_mix_component_experiment` 仍失敗、而本輪進一步要求驗證「base-stack redesign 是否值得繼續」時，`scripts/hb_q35_scaling_audit.py` / `hb_parallel_runner.py` / 文件同步還必須共同輸出 `base_stack_redesign_experiment={verdict,machine_read_answer,best_discriminative_candidate,best_floor_candidate,unsafe_floor_cross_candidate}`。治理規則是：
1. `best_discriminative_candidate` 代表 **runtime exact lane** 內、仍保留正向 win-vs-loss discrimination 的 support-aware reweight；
2. `best_floor_candidate` 代表純粹把 current live row 拉到最高 entry quality 的候選；
3. 若只有 `best_floor_candidate` 能跨過 floor、但 `unsafe_floor_cross_candidate` 不為空（例如 ear-heavy 權重），就必須把這條 bull q35 lane 升級成 **no-deploy governance blocker**，不得再把 base-stack 權重微調包裝成 deployment closure；
4. fast heartbeat summary / ISSUES / ROADMAP 必須 machine-read `positive_discriminative_gap` 與 `unsafe_floor_cross_candidate`，避免下一輪又把「破壞 discrimination 的假跨 floor」誤當成可部署 patch。**Heartbeat #1020 再補 live governance propagation contract**：當上述 no-deploy blocker 成立，`model/predictor.py::predict()`、`scripts/hb_predict_probe.py`、`scripts/live_decision_quality_drilldown.py`、`hb_parallel_runner.py` 不得只留下 `entry_quality_below_trade_floor`。這些主要治理 surface 必須同步輸出 `deployment_blocker / deployment_blocker_reason / deployment_blocker_source / deployment_blocker_details`，並把 execution guardrail reason 升級為 `bull_q35_no_deploy_governance`。目的不是額外擋單，而是防止 heartbeat / probe / docs 再把 current bull q35 lane 誤寫成「只差一點 floor gap」或 support shortage；只要 `unsafe_floor_cross_candidate` 仍是唯一跨 floor 路徑，live contract 就必須明示 **exact-supported but still no-deploy**。**Heartbeat #1022 再補 q35 discriminative deployment contract**：若 `q35_scaling_audit.base_stack_redesign_experiment.machine_read_answer = {entry_quality_ge_0_55=true, allowed_layers_gt_0=true, positive_discriminative_gap=true}`，且 current live row 仍是同一條 `bull + CAUTION + q35` row，`model/predictor.py::_build_live_decision_profile()` 必須直接套用 `best_discriminative_candidate.weights` 到 live `entry_quality_components`，並顯式輸出 `q35_discriminative_redesign_applied / q35_discriminative_redesign`。但這個 runtime patch只能在 **artifact timestamp 與 current live row一致** 時生效；若 q35 audit 已 stale、row 已切換、或 candidate 不再保留正向 discrimination，則必須自動退回 baseline 權重，避免用舊 audit 誤放行新 row。**Heartbeat #2026-04-16 再補 q35 exact-support replay contract**：當 current live row 已套用 `q35_discriminative_redesign_applied=true`，但 decision-quality exact scope 仍因歷史 rows 沿用 baseline label 而短暫顯示 0 rows，live predictor / probe 不得退回 `unsupported_exact_live_structure_bucket` 假 blocker。此時必須把 q35 audit 的 deployed runtime 視為 source of truth，至少回放到 `under_minimum_exact_live_structure_bucket` 或 exact-supported 狀態，並明示這是 **runtime redesign 已落地、歷史 calibration labels 尚待完全重播** 的治理狀態。**Heartbeat #1023 / #2026-04-15 再補 q35 baseline/runtime surface contract**：`scripts/hb_q35_scaling_audit.py` 與 `hb_parallel_runner.py` 不得再把 component-level calibration preview 混稱為 deployed runtime。artifact / summary 必須同時分開 machine-read `baseline_current_live`、`calibration_runtime_current`、`deployed_runtime_current(current_live)`，並在 `deployment_grade_component_experiment` 內顯式輸出 `runtime_source` 與 `q35_discriminative_redesign_applied`。此外，fast heartbeat runner 不得再先 snapshot 舊 `live_predict_probe.json` 再跑 q35 audit；正確順序必須先跑 q35 audit，再刷新 probe / drilldown。**同時 q35 audit 本身也必須執行 post-write second-pass runtime refresh**：先寫出當輪 q35 artifact，再重跑 `hb_predict_probe.py` 對同一條 current q35 row 做 second-pass refresh，最後回寫 deployment-grade runtime。這樣 fast heartbeat 內的 `q35_scaling_audit` / `live_predict_probe` / `live_decision_quality_drilldown` / summary 才能共享同一條當輪 runtime 真相，而不是讓 q35 audit 卡在 pre-artifact 視角。是先跑 q35 audit 產生當輪 artifact，再刷新 `live_predict_probe.json` 與 `live_decision_quality_drilldown`。若 q35 audit 本輪自己生成了新的可部署 candidate，audit 也必須在寫出 artifact 後再做一次與 current row 對齊的 runtime refresh（或共用同一條 shared live-surface pipeline），避免上一輪 probe 汙染本輪 deployment-grade 判讀。
**Heartbeat #1013 q15 boundary-replay contract**：當 `hb_q15_bucket_root_cause.py` 曾回報 `boundary_sensitivity_candidate`，下一輪 heartbeat 不得只停在「看起來接近 q35」的敘述；必須額外執行 `scripts/hb_q15_boundary_replay.py`，輸出 `data/q15_boundary_replay.json` / `docs/analysis/q15_boundary_replay.md`，至少 machine-read：`boundary_replay.{legacy_bucket,replay_bucket,replay_scope_bucket_rows,generated_rows_via_boundary_only,preexisting_rows_in_replay_bucket}`、`component_counterfactual.{feature,raw_delta_to_cross_q35,entry_quality_after,trade_floor_gap_after,allowed_layers_after,verdict}`、以及總體 `verdict / next_action / verify_next / carry_forward`。治理規則是：若 `verdict=boundary_relabels_into_existing_q35_support`、`boundary_replay_not_applicable`、或 **`same_lane_counterfactual_bucket_proxy_only`**，則 q15 boundary review / `feat_4h_bb_pct_b` counterfactual 都只能保留為治理參考，不得包裝成 runtime gate 放寬 patch；其中 `same_lane_counterfactual_bucket_proxy_only` 明確表示 **same-lane q35 鄰近 bucket 已存在，但最小 `feat_4h_bb_pct_b` 反事實只會 rebucket、不會跨 trade floor**，因此下一輪必須直接回頭處理真正的 trade-floor component（目前是 `feat_4h_bias50`）或 exact-support accumulation，而不是把 q15 blocker 假裝成已解。
**Heartbeat #700 再補 narrowed-pathology clamp contract**：當 `regime_label+entry_quality_label` 這種更窄的當前 runtime lane 已經被辨識為 pathological，不得只用它的 aggregate lane average 去下修 expectation。`_narrowed_regime_scope_downside_guardrail()` 現在還必須吃進該 narrowed lane 的 `recent_pathology.summary`，直接用最近病灶視窗的 `win/pnl/quality` 去壓低 live contract，否則 runtime 仍會把 bull-only `100x0` collapse pocket 包裝成較溫和的平均值。
**Heartbeat #674 再補 same-scope pathology contract**：即使 calibration scope 已 fallback 到較寬的 `regime_gate` / `global` lane，也不得讓 broader history 掩蓋 chosen lane 的最近負向 canonical pocket。`model/predictor.py::_summarize_decision_quality_contract()` 現在必須對 chosen rows 再做 recent-window stress check；若近期候選視窗（至少 100/250/500 rows）落入 `constant_target / label_imbalance` 且 `avg_pnl` 或 `avg_quality` 已轉負，必須把**最嚴重且最持久**的 pathology 直接回寫到 `expected_win_rate / expected_pyramid_pnl / expected_pyramid_quality / drawdown_penalty / time_underwater`，並暴露 `decision_quality_recent_pathology_*` 欄位與 chosen window 起迄時間。**Heartbeat #680 再補 adverse-streak evidence contract**：same-scope pathology summary 不得只回報 mixed window 的平均值或最後尾端 streak；必須同步輸出該視窗內最長 adverse target streak（例如 `224x0`）並把它寫進 `decision_quality_guardrail_reason`，避免 runtime / issue / heartbeat 都被尾端 rebound 誤導。**Heartbeat #683 再補 sibling-window live contract**：same-scope pathology summary 還必須同步輸出 `reference_window_comparison = {prev_win_rate, Δquality, Δpnl, top_mean_shift_features}`，而且這份 artifact 必須直接進入 `decision_quality_recent_pathology_reason` 與 `scripts/hb_predict_probe.py`。也就是說，live predictor 不得只知道「最近很差」，還要知道「和前一個等長 sibling window 相比是如何塌陷，以及是哪幾個 4H 結構欄位在塌陷」。`_apply_live_execution_guardrails()` 也必須在這個 flag 打開時允許直接把 live deployment 壓到 `allowed_layers=0`，避免 runtime 再次被 broader historical average 稀釋成假樂觀。
**Heartbeat #712 pocket-outcome evidence contract**：`_summarize_gate_path()` / `spillover_gate_path` / `exact_gate_path` 不得只回報 structure bands。它們現在還必須同步輸出 `target_counts / pnl_sign_counts / quality_sign_counts / canonical_true_negative_rows/share`，讓 heartbeat 能 machine-check worst spillover pocket 究竟是 canonical 真負樣本（應該被 gate 擋下）還是 gate 過嚴誤傷，而不是只憑 `avg_structure` 或 threshold band 猜測。
Heartbeat #650 起，`web/src/components/ConfidenceIndicator.tsx` 與 `web/src/pages/Dashboard.tsx` 也必須直接消費這組欄位，首頁 live card 不得再回退成舊的二元 confidence/做空 copy。**Heartbeat 2026-04-17 補一條 layer-reason truth contract**：`allowed_layers_raw_reason` 代表進入 execution guardrail 之前的原始 sizing 解釋（例如 `entry_quality_C_single_layer`），`allowed_layers_reason` 則必須代表**最終有效**層數原因；當 deployment / execution guardrail 把 `1 → 0` 壓回時，`allowed_layers_reason` 不得繼續回傳 raw sizing 文案，避免 Dashboard / probe / drilldown 把已被擋單的 lane 誤讀成仍可單層部署。Heartbeat #695 補充：scope diagnostics 不能只告訴 heartbeat 哪條 lane 壞掉，還要告訴它**壞 pocket 是單一 regime 還是 broad calibration lane**；因此 `decision_quality_scope_diagnostics` 內每條 scope 都必須持久化 `recent500_regime_counts` 與 `recent500_dominant_regime`，並把同樣的 regime-mix 證據帶進 `pathology_consensus / worst_pathology_scope`。Heartbeat #716 再補 **structure-support contract**：每條 scope 也必須持久化 `recent500_structure_bucket_counts / recent500_dominant_structure_bucket / current_live_structure_bucket_rows/share/metrics`，並在 chosen scope 幾乎沒有當前 live structure bucket 歷史支持時打開 `decision_quality_structure_bucket_guardrail_*`，避免 runtime 再把 `q35` live 結構誤校準到 `q65/q85` spillover lane。Heartbeat #717 再補 **fallback-selection contract**：`label_imbalance` 不能自動等於 toxic proxy；只有當該 scope 同時呈現負向 `win/pnl/quality` 時才可被 reject。若 chosen scope 對 live bucket support 幾乎為 0，guardrail 也必須改寫 expectation，而不是只留下 warning。這代表 `decision_quality_structure_bucket_guardrail_*` 不只要揭露 support rows/share，還要把 expectation 用 same-bucket metrics 保守夾回。Heartbeat #702 再補一條 exact-lane contract：`decision_quality_scope_diagnostics` 必須額外提供 **`regime_label+regime_gate+entry_quality_label`**，讓 heartbeat / probe / auto-propose 能明確區分「current live bull+ALLOW+D」與「broader bull+D pathology」是否其實是不同 bucket。這樣 live probe、auto-propose、ISSUES 才能直接 machine-check「`regime_label+entry_quality_label` 是 bull-only 147 rows，而 exact `regime_label+regime_gate+entry_quality_label` 只剩 24 rows」，避免 heartbeat 再把 broader pathology 誤報成 current live ALLOW path。Heartbeat #703 再補 **gate-composition contract**：scope diagnostics 不得只停在 regime mix；每條 scope 還必須同步輸出 `avg_drawdown_penalty / avg_time_underwater / recent500_gate_counts / recent500_dominant_gate / recent500_regime_gate_counts / recent500_dominant_regime_gate`。目的是讓 heartbeat 直接看懂 broader bull+D 是 `bull|BLOCK + bull|CAUTION + bull|ALLOW` 哪一段在拖垮 quality，而不是只知道它是「bull-only bad lane」。**Heartbeat #705 再補 spillover contract**：凡是比 exact live lane 更寬的 scope（例如 `regime_gate+entry_quality_label`、`regime_label+entry_quality_label`、`entry_quality_label`），還必須輸出 `spillover_vs_exact_live_lane = {extra_rows, extra_row_share, extra_gate_counts, extra_regime_gate_counts, extra_dominant_gate, extra_dominant_regime_gate, win_rate_delta_vs_exact, avg_pnl_delta_vs_exact, avg_quality_delta_vs_exact, ...}`。這讓 heartbeat 不只知道「broader lane 比 exact lane 差」，而是能 machine-read 地回答**多出的哪些 gate pocket 在拖垮結果、拖垮多少**；Heartbeat #705 已用它定位出 `bull+D` 相對 exact `bull+ALLOW+D` 的 123-row spillover 幾乎都落在 `bull|BLOCK` / `bull|CAUTION`。**Heartbeat #713 再補 exact-live-lane toxicity contract**：治理層與 auto-propose 必須把 `exact_live_lane=(rows/wr/q/dd/tuw/targets/true_negative_rows/final_gate)` 與 `exact_lane_status=toxic_allow_lane` 一起寫回，避免治理只盯 spillover `bull|BLOCK` pocket。**Heartbeat #714 再把這條 exact toxic lane contract 推進到 runtime**：`model/predictor.py::_summarize_decision_quality_contract()` 現在必須額外輸出 `decision_quality_exact_live_lane_toxicity_applied / status / reason / summary`，而 `_apply_live_execution_guardrails()` 必須把這類 `ALLOW` 但 canonical 真負樣本過高的 exact lane 明確轉成 `execution_guardrail_reason=exact_live_lane_toxic_allow_lane_blocks_trade`。也就是說，exact toxic lane 不能再只存在於 docs / auto-propose / scope diagnostics；live predictor payload 本身必須承認它，並把它變成 runtime 縮手信號。 

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
**Leaderboard objective contract（Heartbeat #638 / #639 / #642 / #724）**：`backtesting/model_leaderboard.py` 與 `/api/models/leaderboard` 不可再只用 ROI / overfit gap / volatility 當主排序語義。當前 composite score 與 API payload 至少要同步輸出以下 decision-aware components：
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

Heartbeat #642 起，leaderboard 不只「能讀到」 canonical labels 中的 `simulated_pyramid_drawdown_penalty` / `simulated_pyramid_time_underwater`；它還必須在每個 fold 的**實際 trade entry timestamps** 上聚合這些欄位，計算與 predictor 對齊的 `avg_decision_quality_score`，並把這組欄位序列化到 API payload。Heartbeat #643 已把 Strategy Lab 模型排行榜前端摘要同步切到這組 canonical decision-quality semantics；Heartbeat #644 再把 `/api/strategies/leaderboard`、`/api/strategies/{name}` 與 Strategy Lab 的**策略排行榜主表**一起升級為同一組 `avg_decision_quality_score + avg_expected_*` contract。Heartbeat #645 進一步要求 `/api/strategies/{name}`、`/api/strategies/run` 與前端 active strategy summary 一律攜帶 `decision_contract = {target_col, target_label, sort_semantics, decision_quality_horizon_minutes}`，讓「剛跑完的策略」與「已儲存策略詳情」都使用同一套 canonical 語義，而不是只在 leaderboard 中成立。Heartbeat #649 再把 Strategy Lab 的 **side-by-side compare panel** 也切到相同 contract，固定比較 `DQ / expected win / drawdown penalty / time underwater / allowed layers / ROI`，避免任何 compare surface 回退成 ROI-only 文案。**Heartbeat #655 補充 UI fallback contract**：若 Strategy Lab 任一 visible summary / ranking reason 拿不到 canonical DQ 欄位，不得默默退回普通 `ROI · 勝率` 摘要，而必須顯式顯示 `⚠️ canonical DQ 缺失，暫退回 legacy ROI...`，並把 ROI / 勝率 / PF 區塊標成 `Legacy execution metrics（僅輔助 / tie-breaker）`。這樣前端可見層才能把 fallback 視為 regression signal，而不是正常主語義。**Heartbeat #724 再補 leaderboard lane-selection contract**：`ModelLeaderboard.evaluate_model()` 不得再為每個模型只跑單一 hand-tuned deployment preset；它現在必須至少比較固定候選 lanes（`standard`、`high_conviction_bear_top10`、`bear_top5`、`balanced_conviction`、`quality_filtered_all_regimes` 的相容子集），再把選中的 `deployment_profile` 與 `deployment_profiles_evaluated` 持久化到 status / API payload。剩餘缺口縮小到更深的 Dashboard 摘要卡與未來新增比較入口。

**Core-vs-research signal contract（2026-04-10 strategy review）**：主模型與主 UI 必須區分兩類信號：
- **核心信號**：4H 結構 + 高 coverage technical（可直接參與主決策）
- **研究信號**：sparse-source / 低 coverage / forward-archive 中的特徵（只可作 overlay、bonus、veto 或研究用途）

若不分層，系統會把成熟度不足的 alpha source 誤混入主決策，造成假信心。

**Feature maturity contract（Heartbeat #647 / #648）**：`feature_history_policy.py` / `/api/features/coverage` / `FeatureChart.tsx` / `Dashboard.tsx` / `AdviceCard.tsx` 現在共同使用 `maturity_tier = core | research | blocked` 與 `score_usable` 的同一套語義。FeatureChart composite score / entry-reduce markers 只能使用 `score_usable=true` 的 core features；Dashboard 雷達與 AdviceCard 則必須直接揭露 `核心 / 研究 / 阻塞` 摘要，明講 research / blocked 只作 overlay / 排障，禁止把 auth-blocked / snapshot-only sparse-source 特徵誤包裝成與核心訊號同權的主決策依據。

**Model feature parity contract（Heartbeat #633 / #642 / #723）**：`model/train.py`、`model/predictor.py`、`scripts/full_ic.py`、`load_model_leaderboard_frame()` 必須共用同一個 canonical base feature semantics。當 DB / preprocessor 新增可訓練特徵（例如 `feat_4h_bias200`、`feat_4h_dist_bb_lower`、`feat_4h_vol_ratio`）時，不允許只更新 schema 或 coverage/UI；訓練、推論、IC diagnostics、leaderboard frame 必須同輪一起升級，否則 heartbeat 會落入「資料已存在但模型、診斷、ranking 其中一條路仍忽略」的假進度。**Heartbeat #723 補充**：training-side feature profile registry 也必須接受 ablation artifact 產出的 extended profile names（例如 `core_macro_plus_stable_4h`、`current_full_no_bull_collapse_4h`）；若 artifact profile name 與 training registry 脫節，不得 silently 回退到 `code_default`。

**Sparse 4H inference alignment contract（Heartbeat #633）**：predictor 不可直接使用 latest dense row 上的 raw 4H 欄位，因為 4H features 在 dense rows 上可能是 sparse/NULL。`load_latest_features()` 必須套用與 training 相同的 asof alignment（目前沿用 `model.train._align_sparse_4h_features()`）來生成 base + lag 4H features；若 recent 4H rows 在 DB 已 stale，應先 backfill 4H history，而不是讓推論默默退回 0/NULL。

**Support-aware training profile contract（Heartbeat #723 / #730 / #735 / #737 / #738 / #742 / #744）**：global ablation `recommended_profile` 與 live bull blocker 不可被混成單一語義。當 `bull_4h_pocket_ablation.json` 顯示 **exact live structure bucket support = 0**，`model/train.py::select_feature_profile()` 不得先退回寬鬆的 neighbor/collapse cohort；必須優先嘗試**更貼近當前 live bucket 的代理 cohort**（`bull_live_exact_lane_bucket_proxy` → `bull_exact_live_lane_proxy` → `bull_supported_neighbor_buckets_proxy` → `bull_collapse_q35`）。當 `support_pathology_summary.exact_bucket_root_cause = exact_bucket_supported` 時，training path 也不得再直接回退到 global `feature_group_ablation.recommended_profile`；必須改走 `bull_4h_pocket_ablation.exact_supported_profile` 分支，優先嘗試 `exact_live_bucket / bull_live_exact_lane_bucket_proxy / bull_all / bull_exact_live_lane_proxy`，並把 `feature_profile_meta = {source, support_cohort, support_rows, exact_live_bucket_rows, exact_bucket_root_cause}` 持久化到 `model/last_metrics.json`。**Heartbeat #744 再補 runner 順序約束**：`scripts/hb_parallel_runner.py` 在 full heartbeat 只要會執行 `model/train.py`，就必須先 serial refresh `feature_group_ablation.json` 與 `bull_4h_pocket_ablation.json`，再啟動 train；不得再讓 train 與 artifact refresh 平行競速，否則 train 會讀到 pre-refresh 的 support-aware 舊 artifact，造成 exact-supported 已恢復但 `feature_profile_meta.source` 仍停在 `bull_4h_pocket_ablation.support_aware_profile` 的假 blocker。若 leaderboard 仍選到不同 profile，probe / heartbeat summary 必須把狀態明確標成 `post_threshold_profile_governance_stalled`，而不是繼續沿用 pre-threshold fallback 語義。Heartbeat #735 再補 **bucket-evidence comparison contract**：`bull_4h_pocket_ablation.json.support_pathology_summary` 不得只停在 gap / route 描述；還必須 machine-read `bucket_evidence_comparison = {exact_live_lane, exact_bucket_proxy, broader_same_bucket}` 與 `bucket_comparison_takeaway`，讓 heartbeat 能直接比較 **q85 exact lane / q65 proxy / broader q65 spillover**，判定下一輪該優先追 bucket 邊界還是 spillover 汙染，而不是每輪重新人工比對 artifact。Heartbeat #737 再補 **proxy-boundary diagnostics contract**：同一份 artifact 也必須輸出 `proxy_boundary_diagnostics = {recent_exact_current_bucket, recent_exact_live_lane, historical_exact_bucket_proxy, recent_broader_same_bucket, proxy_vs_current_live_bucket, exact_live_lane_vs_current_live_bucket, broader_same_bucket_vs_current_live_bucket, proxy_boundary_verdict, proxy_boundary_reason}`，讓 heartbeat 能 machine-read「proxy cohort 是太寬、還是其實跟 exact bucket 接近但只是 support 仍不足」。Heartbeat #738 再補 **exact-lane toxic sub-bucket contract**：同一份 artifact 與 fast heartbeat summary 還必須同步輸出 `exact_lane_bucket_diagnostics = {buckets, toxic_bucket, verdict, reason}`，把 bull exact lane 內的 `q35 / q15 / base_caution_q15 / base_caution_q85` 子 bucket 直接 machine-read 化；若其中某個子 bucket 明顯拖累 current bucket，heartbeat 必須把它視為 lane-internal pathology，而不是只把整條 exact lane 當成單一黑盒。這樣 heartbeat 才能分辨「global CV 最佳」與「live bull blocker 下真正被採用的 production-oriented profile」，避免再用 `core_only` 之類 global winner 假裝已解掉 live pocket 問題。

**Leaderboard feature-profile candidate contract（Heartbeat #726 / #727 / #730 / #734 / #736 / #747）**：`backtesting/model_leaderboard.py` 與 `/api/models/leaderboard` 不得再默默用單一 dense `current_full` 特徵集評分所有模型。leaderboard 現在必須至少把 **`core_only`、support-aware `core_plus_macro`、`current_full`** 納入正式候選比較，並把 `selected_feature_profile / selected_feature_profile_source / feature_profiles_evaluated / feature_profile_support_cohort / feature_profile_support_rows / feature_profile_exact_live_bucket_rows` 一起序列化到 ranking payload。Heartbeat #747 再補 **profile-split governance contract**：`scripts/hb_leaderboard_candidate_probe.py`、`hb_parallel_runner.py` summary、`feature_group_ablation.json`、`bull_4h_pocket_ablation.json` 不得只輸出 profile 名稱；還必須 machine-read `profile_split / global_profile_role / production_profile_role`，明確區分 **global shrinkage winner** 與 **bull exact-supported production winner**，避免 heartbeat 再把 `core_only` vs `core_plus_macro_plus_4h_structure_shift` 誤判成 drift 或未解 parity blocker。Heartbeat #1024 再補 **governance-contract contract**：除了 `profile_split`，probe 與 heartbeat summary 還必須同步輸出單一 `governance_contract={verdict,current_closure,treat_as_parity_blocker,recommended_action,...}`，把 `leaderboard_global_winner_vs_train_support_fallback` 明確定義成**健康雙角色治理**或**post-threshold leaderboard sync blocker**，避免文件層與 machine-read 層再次各說各話。Heartbeat #fast（2026-04-15 21:16 UTC）再補 **support-progress contract**：當 current live q35 exact bucket 仍低於 `minimum_support_rows` 時，candidate probe / heartbeat summary 不得只留下 `live_current_structure_bucket_rows`；還必須同步輸出 `support_progress={status,reason,current_rows,previous_rows,delta_vs_previous,stagnant_run_count,stalled_support_accumulation,escalate_to_blocker,history}`，讓 heartbeat 能 machine-read 判斷 support 是仍在累積、缺少可比歷史，還是已進入 `#PROFILE_GOVERNANCE_STALLED` 候選 blocker。**Heartbeat #fast（2026-04-15 21:56 UTC）再補歷史承接約束**：`scripts/hb_leaderboard_candidate_probe.py` 在計算 `support_progress` 時，不得因為當前 run label 與舊 summary 都是 `fast` 就把上一輪 fast summary 去重掉；同時也必須允許從舊 `governance_contract.support_governance_route` / `minimum_support_rows` 回填 legacy summary 的 comparability。否則 probe 會把明明已經 `13 -> 11` 的 q35 exact support regression 誤報成 `no_recent_comparable_history`。Heartbeat #727 再把這條 contract 升級成 **blocker-aware ranking**：當候選 profile 依賴 `support_cohort`，但 `feature_profile_exact_live_bucket_rows <= 0`（或 support rows 低於 minimum support）時，leaderboard 必須把該 candidate 標成 `selected_feature_profile_blocker_*` / `feature_profile_candidate_diagnostics[*].blocker_*`，並在排序上降級，避免 0-support exact bucket 的 support-aware fallback 繼續壓過 global shrinkage winner。Heartbeat #730 再補 **governance-route 透明化**：`scripts/hb_leaderboard_candidate_probe.py` 必須額外輸出 `support_governance_route`、`bull_exact_live_lane_proxy_*`、`bull_live_exact_bucket_proxy_*`，讓 heartbeat 能 machine-read「雖然 exact bucket 仍 0，但目前可用的治理代理樣本是 exact-lane proxy 還是 exact-bucket proxy」，避免文件與 probe 又退回只會說 `unsupported_exact_live_structure_bucket` 卻看不見下一條治理路徑。Heartbeat #734 再補 **under-minimum exact-bucket route**：當 exact live bucket 已有樣本但仍低於 `minimum_support_rows`，probe 不得再把它誤標成 `exact_live_bucket_supported`；必須顯式輸出 `support_governance_route=exact_live_bucket_present_but_below_minimum`，並同步帶出 `minimum_support_rows / live_current_structure_bucket_gap_to_minimum / exact_bucket_root_cause / support_blocker_state`，讓 heartbeat 能分清「已出現但不足支持」與「真的已獲支持」。Heartbeat #736 再鎖一條 **under-minimum blocker-state 對齊約束**：只要 `exact_live_bucket_rows > 0` 但仍 `< minimum_support_rows`，`support_blocker_state` 必須維持 `exact_lane_proxy_fallback_only`（即使 exact-bucket proxy 已達 minimum），避免 artifact / probe / docs 把「已有少量 exact rows」誤說成 `exact_missing`。此時 `support_governance_route` 仍必須維持 `exact_live_bucket_present_but_below_minimum`，讓 blocker 根因與可用 proxy cohort 同時可見。 

**Predictor probe contract（Heartbeat #634 / #635 / #691 / #692 / #693 / #1007 / #1008）**：repo 內必須保留可直接重跑的 live inference probe（目前為 `scripts/hb_predict_probe.py`），固定輸出 `target_col / used_model / canonical 4H feature non-null count / 4H lag non-null count`。這個 probe 必須能在 repo 根目錄直接用 `python scripts/hb_predict_probe.py` 執行，不得要求 heartbeat 額外手補 `PYTHONPATH=.`；否則文件會宣稱可重跑、實際上卻只在特定 shell 前提下可用。Heartbeat 不可再引用一次性臨時 probe 檔名作為唯一驗證證據。Heartbeat #691 再補上持久化約束：fast heartbeat 必須把 probe JSON 寫到 `data/live_predict_probe.json` 並摘取成 `live_predictor_diagnostics`，讓 auto-propose / ISSUES / heartbeat summary 能直接引用同一份 live runtime contract。Heartbeat #692 再補 **scope-matrix 約束**：probe payload 還必須輸出 `decision_quality_scope_diagnostics`，至少覆蓋 `regime_gate+entry_quality_label`、`regime_label+entry_quality_label`、`entry_quality_label`、`global` 等 lane 的 rows / alerts / recent-pathology 摘要，讓 live-path blocker 可以直接比較「更窄 lane 更糟」還是「只有廣 scope 壞掉」，避免 heartbeat 再次退回 ad-hoc 腳本調查。Heartbeat #693 再補 **scope-consensus 約束**：`decision_quality_scope_diagnostics` 不得只是一堆平行 lane rows；它還必須輸出 `pathology_consensus={shared_top_shift_features, worst_pathology_scope, pathology_scopes}`，把多個 pathological scopes 共同指向的 4H collapse feature（目前為 `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`）與最差 lane 一起 machine-check 化，確保後續 heartbeat 直接沿 shared root-cause 做 patch，而不是反覆做 ad-hoc scope 比較。**Heartbeat #1007 再補 circuit-breaker propagation 約束**：當 predictor 在 decision-quality contract 之前就觸發 `CIRCUIT_BREAKER`，probe JSON 仍必須保留 `reason / streak / win_rate / allowed_layers`，讓 heartbeat 能明確區分「目前沒有 scope」是因為 live path 被 circuit breaker 先擋下，而不是 q15/q35 校準或 support artifact 壞掉。**Heartbeat #1008 再補 breaker-horizon 對齊約束**：probe 與 predictor 不得再用「所有 horizons 混在一起」的 labels 來決定 live breaker；`CIRCUIT_BREAKER` 必須對齊 canonical live `decision_quality_horizon_minutes`（目前 1440m），而 probe / artifact 也必須同步輸出 `triggered_by / recent_window_win_rate / window_size / horizon_minutes`，避免 240m tail labels 假性觸發 1440m live runtime blocker。

**Heartbeat drilldown artifact contract（Heartbeat #720 / #721 / #1006 / #1007）**：除了完整 probe JSON，repo 也必須保留一份**可讀、可重跑、可比較 exact-vs-broader lane** 的摘要 artifact（目前為 `scripts/live_decision_quality_drilldown.py` → `data/live_decision_quality_drilldown.json` / `docs/analysis/live_decision_quality_drilldown.md`）。這份 artifact 的目的不是取代 probe，而是把 chosen scope、exact live lane、narrow same-regime lane、broader same-gate fallback 與 shared 4H collapse shifts 放到同一個固定 schema，讓 heartbeat 能快速判斷：問題是 exact lane support 不足、same-regime pathology、還是 spillover lane 汙染。**Heartbeat #721 再補一條執行約束**：`scripts/hb_parallel_runner.py --fast` 必須在 `hb_predict_probe.py` 之後自動重跑這份 drilldown artifact，並把 `json / markdown / chosen_scope / worst_pathology_scope` 寫進 heartbeat summary，避免 heartbeat 繼續引用舊的 live-path snapshot。**Heartbeat #1006 再補 gap-attribution contract**：drilldown artifact 不得只列 `entry_quality_components` 讓人手動推理；它現在還必須 machine-read `component_gap_attribution = {remaining_gap_to_floor, best_single_component, best_single_component_required_score_delta, single_component_floor_crossers, bias50_floor_counterfactual}`。目的是讓 heartbeat 直接回答「現在卡 floor 的首要 component 是誰、單點修補是否足夠、bias50 全放鬆的上限會到哪」，避免下一輪又退回人工比對 component 表格。**Heartbeat #1007 再補 runtime-blocker contract**：若 live predictor 在 decision-quality contract 之前已被 `CIRCUIT_BREAKER` 擋下，drilldown artifact 不得再回填假的 `trade_floor_gap=0.55` 或假裝有可比較 scope；它必須 machine-read `runtime_blocker` 與 `component_gap_attribution.unavailable_reason`，把 q35/q15 分析降級成 background research，而不是誤包裝成當前可部署的 live lane root cause。

**Feature-family ablation contract（Heartbeat #720 / #721）**：repo 內必須保留可直接重跑的 feature-family shrinkage 分析（目前為 `scripts/feature_group_ablation.py`），固定輸出 `data/feature_group_ablation.json` 與 `docs/analysis/feature_group_ablation.md`。這份 artifact 的用途不是模型最終訓練，而是讓 heartbeat 每輪都能 machine-check：`current_full` 是否仍值得保留、哪一個 family removal 能提升 `cv_mean / cv_std / cv_worst`、以及 bull/bear top-decile 表現是否因 feature family 改動而受損。**Heartbeat #721 再補 bull blocker 治理約束**：artifact 不能只輸出 generic family ranking；還必須同步輸出 `recommended_profile`、bull collapse 4H watchlist、`bull_top10`，以及 targeted profiles（例如 `current_full_no_bull_collapse_4h` / `core_macro_plus_stable_4h`），讓 heartbeat 能直接驗證「bull live blocker 是否可由簡單 4H 刪除修好」，避免又回到只看整體 accuracy 的假收斂。沒有這層 artifact，heartbeat 很容易回到「全量 feature 當預設」的假進度。

**Training warning/logging hygiene contract（Heartbeat #634 / #720）**：`model/train.py` 的 cross-feature engineering 不可再用大量逐欄 `frame.insert` 方式製造 pandas fragmentation warnings；training stderr 應盡量只保留真實失敗訊號。同時 recent-vs-global IC log 必須分別輸出真實 `tw_ic_summary` 與 `core_ic_summary`，避免 heartbeat 被假觀測污染。Heartbeat #720 再補一條實作約束：merge suffix 正規化（如 `_ensure_regime_label_column()`）也不得重新引入 pandas fragmentation warning，因為這會污染 feature shrinkage / ablation 類診斷腳本的 stderr。
### 5. 回測層
驗證不同特徵組合、不同市場狀態與不同入場／加碼／出場閾值下的表現。

**Strategy Lab runtime contract（2026-04）**：正式回測工作區為 `/lab`。前後端目前採用：
- `/api/strategies/run_async` + `/api/strategies/jobs/{job_id}` 背景任務模式
- 頁面上方統一 progress bar 顯示真實回測進度
- 圖表資料採用 local cache + incremental kline append，避免切頁或 refresh 時整包重抓
- price/equity stacked synchronized charts 為正式視覺契約，舊 `/backtest` 只保留 redirect，不再作為獨立工作區
- model leaderboard 現在保留 `deployment_profile`，並用更接近 OOS 高信念部署的 lane 來評估模型，而不是把所有模型都硬塞進單一 entry 規則
- **Runtime blocker sync（Heartbeat 2026-04-17）**：Strategy Lab 也必須直接讀 `/api/status` 的 `execution_reconciliation / execution_surface_contract / execution_metadata_smoke`，至少把 summary-level runtime blocker、metadata freshness 與 canonical execution route 提示顯示在回測工作區，避免使用者把 DQ / backtest 工作區誤讀成 live-ready execution truth

### 6. 可視化層
顯示每個特徵的 IC、勝率、風險貢獻、spot-long 勝率、回測摘要與會議整理。

### 7. Execution runtime surface
手動交易與 execution readiness 的正式 surface 目前由 `/api/status`、`/api/trade`、`Dashboard` 共用。

**Execution runtime visibility contract（Heartbeat 2026-04-16）**：`server/routes/api.py::api_status()` 建立 `ExecutionService` 時必須帶入 `db_session=get_db()`，不可只用 config-only summary。原因是 `daily_loss_ratio / daily_loss_halt / recent reject` 依賴 `TradeHistory` 與 runtime 狀態；若少了 DB session，Dashboard 看到的 guardrail 會變成假健康。

**Account snapshot detail contract（Heartbeat 2026-04-17）**：`AccountSyncService.snapshot()` 不得只回傳 balance / positions / open_orders 原始列表。它現在還必須同步回傳 `captured_at`、`requested_symbol`、`normalized_symbol`、`position_count`、`open_order_count`、`degraded`、`operator_message`、`recovery_hint`，讓 Dashboard 的 canonical execution surface 可以直接判斷目前看到的是 fresh runtime truth 還是 degraded snapshot，避免空列表被誤讀成「真的沒有倉位 / 掛單」。

**Execution reconciliation summary contract（Heartbeat 2026-04-17）**：`server/routes/api.py::api_status()` 現在還必須輸出 `execution_reconciliation`，把 account snapshot、runtime `last_order`、trade_history 最新列、open_orders 對帳成 machine-readable summary。最低欄位必須包含：`status / summary / issues / account_snapshot.freshness / symbol_scope / trade_history_alignment / open_order_alignment`。Heartbeat 2026-04-17 再補 **`lifecycle_audit / recovery_state`**：summary artifact 不得只說 mismatch 與否，還必須 machine-read `stage / runtime_state / trade_history_state / matched_open_order_state / restart_replay_required / operator_action / recovery_status`，讓 Dashboard 與 Strategy Lab 都能直接顯示「目前是 no-runtime-order、open 缺 snapshot、terminal 已對帳，還是需要 trade-history replay」。本輪再補 **`lifecycle_timeline`**：`ExecutionService` 會把 `validation_passed / venue_ack / trade_history_persisted / rejected / runtime_failure` 寫進 `order_lifecycle_events`，`/api/status` 會依 `order_id / client_order_id` 回放最新 timeline，Dashboard 與 Strategy Lab 可直接顯示 replay key、最新 event 與近幾筆 lifecycle 軌跡。**Heartbeat 2026-04-17 13:25 CST 再補 `artifact_checklist_summary / artifact_checklist[]`**：summary artifact 不得再只停在 replay verdict 與 timeline；它現在還必須 machine-read per-order closure checklist，至少覆蓋 `validation_passed / venue_ack / trade_history_persisted / partial_fill / cancel / terminal_state / restart_replay` 的 `status / observed / count / summary / evidence`，讓 operator 直接知道缺哪個 artifact，而不是手動比對多個欄位。**Heartbeat 2026-04-17 本輪再補 `artifact_provenance_summary / provenance_level`**：checklist 不得把 dry-run、internal DB evidence、真實 venue artifact 混成同一種「已觀察到」。每個 checklist item 與總結現在都必須明確區分 `venue_backed / dry_run_only / internal_only / missing`，避免 Dashboard / Strategy Lab 把 replay baseline ready 誤讀成已具備真實 Binance/OKX path closure。**Heartbeat 2026-04-17 本輪再補 `venue_lanes[].operator_action_summary / operator_instruction / verify_instruction / operator_next_check / remediation_focus / remediation_priority`**：lane drilldown 不得只停在「看到缺口」。每個 lane 現在都必須直接給出 operator-grade remediation contract，明確回答：先補 baseline、先抓 partial_fill/cancel path、還是先把 internal-only proof 升級成 venue-backed artifact；同時附上 verify step，讓 Dashboard / Strategy Lab 可以直接顯示「下一步做什麼、做完怎麼驗證」，而不是再把 remediation 留給人工推理。**Heartbeat 2026-04-17 14:48 CST 再補 `venue_lanes[].artifact_drilldown_summary / timeline_summary / timeline_events / artifacts`**：execution reconciliation 不得只提供 lane 卡片摘要；每個 venue lane 現在都必須攜帶自己的 filtered artifact subset 與 filtered timeline，讓 Dashboard / Strategy Lab 能直接在 Binance / OKX / unscoped lane 內看 baseline 缺口、path artifact 與最近 timeline，而不是再回到 mixed global timeline 手動比對。這仍不是完整 venue-side ack/open/partial-fill/fill/cancel event sourcing；真正的 exchange fill/cancel 回放仍是下一個 P0。

**Manual trade reject contract（Heartbeat 2026-04-16）**：`/api/trade` 的 reject path 必須保留 structured payload `detail={code,message,context}`，而前端 transport (`web/src/hooks/useApi.ts`) 不得把 object detail 直接變成 `[object Object]`。若 guardrail 是真的、但 UI 只顯示無意義字串，等同 execution surface 未落地。

**Manual trade success contract（Heartbeat 2026-04-16）**：`/api/trade` 成功回應不可只帶 order id。它現在必須同步帶回 `guardrails` 與 `normalization={requested, normalized, contract}`，讓 manual trade call site 與 Dashboard/status 面板同時看到：
- 原始輸入 qty / price
- venue normalization 後的合法 qty / price
- 此次委託所依據的 `step_size / tick_size / min_qty / min_cost` contract

同一份 normalization 摘要也必須落到 runtime `last_order`，確保 `/api/status` 刷新後仍能回放最近成功路徑的合法值，而不是只剩 `qty/status`。

**Execution market-rules contract（Heartbeat 2026-04-16 13:00 UTC）**：`execution/exchanges/binance_adapter.py`、`execution/exchanges/okx_adapter.py`、`execution/execution_service.py` 必須共享同一套 venue granularity semantics。adapter `market_rules()` 現在不只回傳 `min_qty / min_cost / amount_precision / price_precision`，還必須回傳：
- `step_size`
- `tick_size`
- `qty_contract`
- `price_contract`

`ExecutionService._validate_order_request()` 不得再只「先 round 再送單」；只要使用者輸入的 `qty/price` 與 `step_size / tick_size / precision` 不一致，就必須在 pre-trade lane 直接結構化拒絕，至少覆蓋：
- `qty_step_mismatch`
- `qty_precision_mismatch`
- `price_tick_mismatch`
- `price_precision_mismatch`

reject context 也必須保留 `raw_value / adjusted_value / delta / rules`，讓上層 API / UI 能把「原始值 → 合法值 → 差額 → 規則來源」完整暴露給操作者，而不是等 exchange runtime rejection 才知道 granularity 不合法。

**Manual trade runtime closure contract（Heartbeat 2026-04-16 13:19 UTC）**：`web/src/pages/Dashboard.tsx` 的 manual trade callback 不得再只送出 `/api/trade` 然後等待輪詢。成功與失敗兩條路都必須 **主動 refresh `/api/status`**，並把最新 `guardrails / last_reject / last_order` 拉回同一個操作閉環。Dashboard 也必須保留一個 operator-facing **Guardrail context 面板**，把最近 reject 的 `field / raw_value / adjusted_value / delta / rules` 轉成可讀資訊；否則即使 structured reject payload 正確存在，execution surface 仍不算真正落地。

**Execution metadata smoke contract（Heartbeat 2026-04-16 14:03 UTC）**：execution readiness 不得只靠 unit tests 或 config 內的 venue enablement 敘事。repo 必須保留一條 **read-only metadata smoke lane**（目前為 `scripts/execution_metadata_smoke.py`），直接向 Binance / OKX 公開 market metadata 抽取 `step_size / tick_size / min_qty / min_cost / precision / qty_contract / price_contract`，並把結果落到 `data/execution_metadata_smoke.json`。這條 lane 的用途是驗證「真實 venue metadata 與 ExecutionService / Dashboard 顯示契約一致」，而且即使 venue 在 config 中 disabled，也必須能以 public metadata 方式驗證，不得因未開 live trading 就跳過 contract smoke。

**Execution metadata runtime-surface contract（Heartbeat 2026-04-16 14:25 UTC）**：metadata smoke 不可停留在離線 JSON artifact。`server/routes/api.py::api_status()` 現在必須把最近一次 `data/execution_metadata_smoke.json` 摘要序列化為 `execution_metadata_smoke={generated_at, symbol, ok_count, venues_checked, venues[]}`，而 `web/src/pages/Dashboard.tsx` 必須直接渲染 venue-level `step/tick/min_qty/min_cost` 摘要。若 artifact 缺失或解析失敗，runtime surface 必須明確暴露 unavailable/error 狀態，而不是默默假裝 readiness 健康。

**Execution metadata freshness contract（Heartbeat 2026-04-16 14:49 UTC）**：`execution_metadata_smoke` 不得只顯示時間戳。`server/routes/api.py::_load_execution_metadata_smoke_summary()` 現在必須序列化 `freshness={status, label, reason, age_minutes, stale_after_minutes}`，其中狀態只允許 `fresh | stale | unavailable`；`web/src/pages/Dashboard.tsx` 必須渲染相同 badge 與 age policy（例如 `smoke freshness FRESH`、`artifact age 7.9m · stale after 30m`），讓 operator 能直接判讀 smoke 是否過期，而不是自行估算時間差。

**Execution metadata auto-refresh governance contract（Heartbeat 2026-04-16 15:05 UTC，更新於 17:26 UTC）**：stale metadata smoke 不可只停留在 badge 告警。`server/routes/api.py::api_status()` 現在必須在 `freshness in {stale, unavailable}` 時自動嘗試重跑 read-only `run_metadata_smoke()`，並以單一治理 payload 序列化 `governance={status, operator_action, operator_message, refresh_command, escalation_message, auto_refresh, background_monitor, external_monitor}`；其中 `auto_refresh` 至少要帶 `status / reason / attempted_at / completed_at / next_retry_at / cooldown_seconds / error`，並套用 5 分鐘 cooldown，避免 `/api/status` 輪詢把 venue metadata lane 打爆。**Heartbeat 2026-04-16 15:34 UTC 再加一條 process-internal background governance contract**：`server/main.py` 啟動 FastAPI 後，必須額外啟動常駐背景監看器，每 60 秒執行一次 `run_execution_metadata_smoke_background_governance()`；它會把 `background_monitor={status, reason, checked_at, freshness_status, governance_status, error, interval_seconds}` 寫回 runtime status 與 governance payload，讓 operator 區分「靠 `/api/status` 被動 refresh」與「API process 內主動背景監看」。**Heartbeat 2026-04-16 15:58 UTC 再加一條 process-external governance contract**：repo 內必須保留可被 cron / scheduler / pager 直接呼叫的 `scripts/execution_metadata_external_monitor.py`，它會把最近一次外部治理結果寫成 `data/execution_metadata_external_monitor.json`，並由 `/api/status` / Dashboard 以 `external_monitor={status, reason, checked_at, freshness_status, governance_status, error, interval_seconds, command, freshness, install_contract, ticking_state}` 顯示。**Heartbeat 2026-04-16 16:21 UTC 再加一條 host-install contract，並於 16:42 UTC 升級為 installed-state contract、17:05 UTC 升級為 shell-safe ticking contract、17:26 UTC 升級為 explicit ticking-state contract**：repo 內還必須保留 `scripts/execution_metadata_external_monitor_install.py` 與 `data/execution_metadata_external_monitor_install_contract.json`，把 `preferred_host_lane / user_crontab.install_command / user_crontab.verify_command / systemd_user.timer_file / fallback.command` 持久化到 artifact；當 host-level scheduler 已真正安裝時，artifact 與 Dashboard 還必須同步 machine-read `install_status={status, installed, active_lane, checked_at, lanes.*}` 與 `ticking_state={status, reason, message, active_lane, freshness_status, age_minutes, stale_after_minutes}`，其中 `status` 只允許 `install-ready / installed / observed-ticking / installed-but-not-ticking`，避免 operator 再手動比對 install status 與 freshness 才知道 scheduler 有沒有真的在 tick。
明確區分 `install-ready`、`installed` 與後續要觀察的 `observed-ticking`。對 `user_crontab` lane，install / fallback / runtime `command` 不得再依賴 `source venv/bin/activate` 這類只在 bash 可用的 shell-specific 寫法；必須改用 **直接 venv python 絕對路徑**（或等價的 shell-safe command），否則 cron 會由 `/bin/sh` 執行失敗、卻讓 scheduler 表面上仍顯示 installed。這條 lane 的目的不是取代 API 內 background monitor，而是在 API process 掛掉時仍保有一條 process-independent metadata governance 路徑。注意：這條 contract 只治理 metadata smoke freshness / install state，不代表 live/canary order-level ready。

**Execution route split contract（Heartbeat 2026-04-16 16:21 UTC，更新於 17:49 UTC）**：目前只有 `web/src/pages/Dashboard.tsx` 是 **canonical execution route**，因為它完整消費 `/api/status + guardrails + metadata governance + external install/fallback contract`。`server/routes/api.py::api_status()` 現在還必須 machine-read 輸出 `execution_surface_contract={canonical_execution_route, canonical_surface_label, shortcut_surface, readiness_scope, live_ready, live_ready_blockers, operator_message}`，讓 operator 不必再靠文件或文案猜測 route 邊界。`web/src/components/SignalBanner.tsx` 現階段只能扮演快捷下單 / automation toggle lane，不得再被描述成完整 execution governance surface；它也必須保留「回到 Dashboard 檢查完整 Execution 狀態」的明示導引。若未來要把 SignalBanner 升級為第二條 route，必須同步接入 `/api/status` refresh、guardrail context、stale governance、install contract / ticking-state 顯示與對應 regression tests；在那之前，Dashboard 才是唯一 canonical runtime surface，而 readiness 敘事也必須維持在 governance / visibility closure，不得誤升級成 live/canary ready。

**Chart prop stability contract（Heartbeat 2026-04-16 14:49 UTC）**：`web/src/components/CandlestickChart.tsx` 不得再用 inline `[]` 當 `tradeMarkers / equityCurve / scoreSeries` 的 default props。這些空陣列若每次 render 都重新配置，會讓依賴它們的 `useEffect` 在 progress-driven rerender 中重複觸發，造成 browser runtime 出現 `Maximum update depth exceeded`。固定 contract 是使用 module-level stable empty arrays，確保 Dashboard / Strategy Lab 的圖表在無 trade/equity props 時也不會進入 render loop。

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

> 命名層面現在以 **市場語義 / 特徵語義** 為主，不再建議用人格化特徵名當作對外主描述。

| 類別 | 代表欄位 | 主軸 | 資料源 | 用途 |
|---|---|---|---|---|
| 趨勢 / 動能 | `feat_eye`, `feat_ear`, `feat_mind` | 方向、節奏、中期動量 | K 線 / 報酬 / funding proxy | 判斷主趨勢與中期風險 |
| 均值回歸 / 過熱 | `feat_nose`, `feat_tongue`, `feat_aura` | 過熱、偏離、回歸張力 | K 線衍生 / 複合特徵 | 判斷反轉或拉回機率 |
| 結構 / 波動 | `feat_body`, `feat_pulse` | range 位置、量能與壓力 | breakout / funding / OI / liquidation | 判斷所處階段與擁擠度 |
| 4H 結構 | `feat_4h_bias50`, `feat_4h_bias200`, `feat_4h_dist_swing_low`, `feat_4h_dist_bb_lower` | 高時間框架背景 | 4H 結構特徵 | 做 regime gate 與結構 veto |
| 技術延伸 | `feat_nw_width`, `feat_nw_slope`, `feat_adx`, `feat_choppiness`, `feat_donchian_pos` | 技術狀態與市場型態 | OHLCV / indicator engine | 改善短線 entry quality |
| 宏觀 / 外部 | `feat_vix`, `feat_dxy`, `feat_nq_return_*` | risk-on / risk-off | Macro / futures | 判斷外部風險背景 |
| 研究型 sparse-source | `feat_claw`, `feat_fin_netflow`, `feat_fang_pcr`, `feat_web_whale`, `feat_scales_ssr`, `feat_nest_pred` | 額外 alpha 線索 | 稀疏來源 / snapshot archive | 僅作 research overlay / veto 候選 |

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

