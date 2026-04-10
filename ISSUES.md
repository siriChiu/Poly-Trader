# ISSUES.md — 問題追蹤

*最後更新：2026-04-10 23:36 UTC — Heartbeat #648（push maturity-aware semantics into Dashboard radar + AdviceCard, re-verify closed-loop heartbeat on fresh canonical data）*

## 📊 系統健康狀態 v4.61

| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw | **20,377** | 🟢 `python scripts/hb_parallel_runner.py --fast --hb 647` 本輪新增 **+1**；raw continuity repair 仍未觸發 bridge |
| Features | **11,806** | 🟢 fast heartbeat 本輪新增 **+1**；canonical 4H / lag feature path 仍可正常推進 |
| Labels | **40,766** | 🟢 本輪 240m labels 維持 **11,603 target rows**、1440m 維持 **11,156**；freshness 仍在 expected horizon lag 內 |
|| simulated_pyramid_win (DB overall) | **57.29%** | 🟢 canonical DB 整體口徑；fast heartbeat collect summary `simulated_win=0.5729` |
|| simulated_pyramid_win (`full_ic.py` / `regime_aware_ic.py` sample) | **64.24%** | 🟢 分析樣本 n=11,026 |
| spot_long_win | **33.21%** | 🟡 legacy 比較口徑，非主 target |
| 全域 IC | **13/30** | 🟢 canonical diagnostics 維持；Aura/Mind/VIX/DXY/4H features 仍是主要通過來源 |
| TW-IC | **16/30** | 🟢 recent-weighted 診斷維持 macro + 4H 優勢 |
| Regime IC | **Bear 6/8 / Bull 6/8 / Chop 5/8 / Neutral 21 rows** | 🟢 canonical simulated target 維持；chop 仍只有 5/8，尚未升級成新 blocker |
| 模型 / 決策語義 | **live predictor = `phase16_baseline_v2`; model leaderboard + strategy leaderboard/detail + active strategy summary now expose canonical decision-quality fields** | 🟢 `/predict/confidence` / `hb_predict_probe.py` 持續回傳 `expected_win_rate / expected_pyramid_quality / expected_drawdown_penalty / expected_time_underwater / decision_quality_score`；本輪 `/api/strategies/{name}` / `/api/strategies/run` 也固定帶 `decision_contract`，Strategy Lab active summary 不再只停在 ROI/PF |
| Verification | **33 pytest + npm build + fast heartbeat** | ✅ 本輪已重驗證 |

## 🎯 當前戰略問題（高準確度 / 高勝率 / 低回撤）

### #DECISION_QUALITY_GAP（持續 P0，但本輪再推進）
- **現象**：canonical target 與 label DB 已對齊後，真正缺口變成 live predictor / leaderboard / API / 前端摘要 是否使用**同一套** decision-quality semantics，而不是 predictor 說一套、ranking 仍靠 proxy 分數排序。
- **本輪修復**：Heartbeat #642 已把 `backtesting/model_leaderboard.py` / `server/routes/api.py` 接到 canonical decision-quality contract；Heartbeat #643 把 `web/src/pages/StrategyLab.tsx` 的**模型排行榜**切到 canonical quality semantics；Heartbeat #644 再把 `server/routes/api.py::api_strategy_leaderboard()`、`api_get_strategy()` 與 `web/src/pages/StrategyLab.tsx` 的**策略排行榜主表**一起切到 `avg_decision_quality_score / avg_expected_win_rate / avg_expected_drawdown_penalty / avg_expected_time_underwater / avg_allowed_layers / avg_entry_quality`；Heartbeat #645 再把 **active strategy summary** 與 `/api/strategies/run` / `/api/strategies/{name}` payload 一起補上 `decision_contract`（target label / sort semantics / horizon），讓使用者一選策略或剛跑完回測，就直接看到 canonical DQ / 預期勝率 / DD/UW 語義，而不是退回 ROI/PF-only summary。
- **本輪證據**：`python scripts/hb_parallel_runner.py --fast --hb 645` → Raw **20375** / Features **11804** / Labels **40757**；`python -m pytest tests/test_strategy_lab.py -q` → **10 passed**；`cd web && npm run build` ✅。新增 regression test 確認 `_decorate_strategy_entry()` 會附帶 `decision_contract`，避免 detail payload 再回退成缺語義狀態。
- **剩餘風險**：這仍是 **historical calibration layer + leaderboard-side aggregation**，不是直接訓練出的多目標 live head；saved-strategy comparison / side-by-side compare flow 仍未把 canonical decision-quality 欄位提升成第一層比較語義。
- **建議方向**：下一輪把 saved-strategy comparison 視圖也切到 `decision_quality_score + drawdown_penalty + time_underwater + allowed_layers` 語義，讓主表、active summary、詳情與 compare flow 完整一致。

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

### #LEADERBOARD_OBJECTIVE_MISMATCH（部分修復，降為 P1 follow-up）
- **現象**：Heartbeat #638 已把 `backtesting/model_leaderboard.py` 的 composite score 從偏 **ROI / test accuracy gap / ROI 波動**，改成更偏向 **勝率 / 最大回撤 / PF / regime stability / trade quality / trade count** 的複合排序，並把這些 component fields 經由 API payload 一起輸出。
- **本輪修復**：新增 fold/model 層級的 `avg_entry_quality`、`avg_allowed_layers`、`avg_trade_quality`、`regime_stability_score`、`max_drawdown_score`、`profit_factor_score`、`overfit_penalty` 等欄位；`tests/test_model_leaderboard.py` 與 `tests/test_api.py` 共 **20 passed**，證明 API 序列化與 ranking contract 已更新。
- **剩餘缺口**：目前 trade quality 仍是 **backtest-side proxy**，尚未直接使用 `win + pnl_quality + drawdown_penalty + time_underwater` 的完整 canonical decision-quality target，也尚未把 regime breakdown / leaderboard UI 主排序文字一起更新成同一語義。
- **下一步方向**：把 labeling 端的 canonical quality target 明確接進 leaderboard / predictor，共用同一組 decision-quality contract，而不是讓 leaderboard 停留在 proxy 分數。

### #DYNAMIC_WINDOW_NOT_DISTRIBUTION_AWARE（持續 P1）
- **現象**：Dynamic Window 最近窗已知不是 merge bug，而是 canonical recent labels 在某些窗口內高度偏斜甚至 constant。
- **風險**：近期 evaluation 容易給出假 blocker 或假優勢，進一步誤導模型與特徵排序。
- **建議方向**：把 recent-window 評估升級成 **distribution-aware / regime-aware**，顯示 label balance 與 constant-target guardrail。

### 實作計畫
- `docs/plans/2026-04-10-phase-16-implementation-plan.md`

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
