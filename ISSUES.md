# ISSUES.md — Current State Only

_最後更新：2026-04-19 21:40:43 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **本輪 heartbeat #20260419aj 已完成 fast collect + verify 閉環**：`Raw=31142 (+1) / Features=22560 (+1) / Labels=62671 (+3)`；active horizons `240m / 1440m` freshness 都是 `expected_horizon_lag`，資料管線不是 frozen。
- **本輪產品化 patch 已落地：rows-aware support-route truth**
  - `model/predictor.py::_summarize_structure_bucket_support_route()` 不再把 `exact_bucket_supported_*` mode hint 直接當成 support closure；現在必須先看 `current_live_structure_bucket_rows` 是否達到 `minimum_support_rows`。
  - 這修掉了 current live `q35` exact bucket 只有 `1/50` 時，probe / drilldown 仍假性顯示 `exact_bucket_supported` 的 false-open bug。
  - regression 已補齊：`tests/test_api_feature_history_and_predictor.py::test_summarize_structure_bucket_support_route_does_not_false_open_below_minimum_support`。
- **驗證證據已齊**
  - `pytest tests/test_api_feature_history_and_predictor.py tests/test_hb_predict_probe.py -q` = `80 passed`
  - `python scripts/hb_parallel_runner.py --fast --hb 20260419aj` 完成 collect / IC / drift / probe / auto-propose 閉環
  - `data/live_predict_probe.json` 與 `data/live_decision_quality_drilldown.json` 現在一致顯示：`support_route_verdict=exact_bucket_present_but_below_minimum`、`current_live_structure_bucket=CAUTION|structure_quality_caution|q35`、`current_live_structure_bucket_rows=1`、`minimum_support_rows=50`、`gap_to_minimum=49`
  - `recommended_patch=core_plus_macro` 仍正確維持 `reference_only_until_exact_support_ready`，不再被錯誤包裝成 support 已 closure
- **canonical current-live 唯一 deployment blocker 仍是 circuit breaker**：`deployment_blocker=circuit_breaker_active`、`recent 50 wins=1/50`、`additional_recent_window_wins_needed=14`、`streak=1`、`allowed_layers=0`、`runtime_closure_state=circuit_breaker_active`。
- **current live support truth 已切回 rows-aware q35 語義**：`current_live_structure_bucket=CAUTION|structure_quality_caution|q35`、`current_live_structure_bucket_rows=1`、`minimum_support_rows=50`、`support_route_verdict=exact_bucket_present_but_below_minimum`、`support_governance_route=exact_live_bucket_present_but_below_minimum`、`remaining_gap_to_floor=0.1963`、`best_single_component=feat_4h_bias50`。
- **recent canonical 250 rows 仍是 distribution pathology**：`win_rate=0.0040`、`dominant_regime=bull(100%)`、`avg_pnl=-0.0099`、`avg_quality=-0.2816`、`avg_drawdown_penalty=0.3739`、`adverse_streak=248x0`；top shifts=`feat_4h_bb_pct_b`、`feat_4h_bias20`、`feat_eye`；new compressed=`feat_vwap_dev`。
- **leaderboard recent-window contract 仍一致**：`/api/models/leaderboard` / probe / docs 目前都是 `count=6 / comparable_count=6 / placeholder_count=0`；top row=`rule_baseline / core_only / scan_backed_best`；`governance=dual_role_governance_active`、`closure=global_ranking_vs_support_aware_production_split`。
- **support-aware patch 仍是 reference-only**：`recommended_patch=core_plus_macro`、`recommended_patch_status=reference_only_until_exact_support_ready`、`reference_patch_scope=bull|CAUTION`、`support_route_verdict=exact_bucket_present_but_below_minimum`、`gap_to_minimum=49`。
- **venue / source blockers 仍未 closure**：Binance / OKX 仍缺 `live exchange credential / order ack lifecycle / fill lifecycle`；`fin_netflow` 仍是 `source_auth_blocked`，根因是 `COINGLASS_API_KEY` 缺失，`archive_window_coverage_pct=0.0%`。

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
**現況**
- `deployment_blocker=circuit_breaker_active`
- `recent_window=50`
- `current_recent_window_wins=1`
- `required_recent_window_wins=15`
- `additional_recent_window_wins_needed=14`
- `streak=1`
- `allowed_layers=0`
- `runtime_closure_state=circuit_breaker_active`

**風險**
- 若 `/`、`/execution`、`/execution/status`、`/lab`、probe、drilldown、docs 任一 surface 再把 q35 support、spillover patch 或 venue 摘要排到 breaker release math 前面，operator 會失去唯一 current-live blocker 真相。

**下一步**
- 維持 breaker-first truth 在 `/`、`/execution`、`/execution/status`、`/lab`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`issues.json`、`ISSUES.md` 一致。
- 驗證：browser `/lab`、browser `/execution/status`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`。

### P0. recent canonical 250 rows remains a distribution pathology
**現況**
- `recent_window=250`
- `win_rate=0.0040`
- `dominant_regime=bull`
- `dominant_regime_share=1.0000`
- `avg_pnl=-0.0099`
- `avg_quality=-0.2816`
- `avg_drawdown_penalty=0.3739`
- `alerts=['label_imbalance','regime_concentration','regime_shift']`
- `adverse_streak=248x0`
- top feature shifts=`feat_4h_bb_pct_b`、`feat_4h_bias20`、`feat_eye`
- new compressed=`feat_vwap_dev`

**風險**
- 若 breaker 根因被 broader leaderboard、venue readiness、或 generic model-stability 討論稀釋，修復會再次偏離 pathological slice 本身。

**下一步**
- 以 recent canonical rows 為主做 feature variance / target-path / gate-path drilldown，不要再把 blocker 重述成 generic leaderboard 或 venue 問題。
- 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`。

### P1. current-live q35 exact support remains under minimum under breaker (1/50)
**現況**
- `current_live_structure_bucket=CAUTION|structure_quality_caution|q35`
- `current_live_structure_bucket_rows=1`
- `minimum_support_rows=50`
- `gap_to_minimum=49`
- `support_route_verdict=exact_bucket_present_but_below_minimum`
- `support_governance_route=exact_live_bucket_present_but_below_minimum`
- `remaining_gap_to_floor=0.1963`
- `best_single_component=feat_4h_bias50`
- `recommended_patch=core_plus_macro`
- `recommended_patch_status=reference_only_until_exact_support_ready`

**風險**
- 若 probe / docs / UI 再退回舊的 `exact_bucket_supported` 語義，或把 `1/50` 說成 support 已 closure，operator 會把 reference-only patch 誤判成 deployable runtime fix。

**下一步**
- 維持 `1/50 + exact_bucket_present_but_below_minimum + reference_only_until_exact_support_ready` 在 probe / drilldown / API / UI / docs 一致 machine-read。
- 驗證：`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、`python scripts/hb_parallel_runner.py --fast --hb <run>`。

### P1. leaderboard recent-window contract is stable again; keep runtime + docs in sync
**現況**
- `/api/models/leaderboard`: `count=6`、`comparable_count=6`、`placeholder_count=0`
- top row=`rule_baseline / core_only / scan_backed_best`
- governance=`dual_role_governance_active`
- closure=`global_ranking_vs_support_aware_production_split`
- `leaderboard_payload_source=latest_persisted_snapshot`

**風險**
- 若 runtime 或 probe 再讓舊快照或過期 cache 遮蔽 current truth，Strategy Lab / docs 會重新出現 split-brain：API 與 current-state 對 top model / profile 說出不同真相。

**下一步**
- 維持 cache-vs-snapshot freshness arbitration、latest bounded walk-forward、與 probe-driven current-state sync；避免 placeholder-only / stale top model 回歸。
- 驗證：`pytest tests/test_model_leaderboard.py tests/test_hb_leaderboard_candidate_probe.py tests/test_auto_propose_fixes.py -q`、`curl http://127.0.0.1:8000/api/models/leaderboard`、browser `/lab`。

### P1. venue readiness is still unverified
**現況**
- `binance`: `config enabled + public-only + metadata OK`
- `okx`: `config disabled + public-only + metadata OK`
- 缺的 runtime proof：`live exchange credential`、`order ack lifecycle`、`fill lifecycle`

**風險**
- breaker 未來解除後，若 venue blockers 被弱化成摘要字串或完全消失，使用者會被誤導成已可實盤。

**下一步**
- 持續保留 per-venue blockers，但它們必須永遠位於 breaker-first current blocker 之後。
- 驗證：browser `/execution`、browser `/execution/status`、browser `/lab`、`data/execution_metadata_smoke.json`。

### P1. fin_netflow source_auth_blocked remains open
**現況**
- `fin_netflow=source_auth_blocked`
- `latest_status=auth_missing`
- blocker 根因：`COINGLASS_API_KEY is missing`
- `forward_archive_rows=2613`
- `archive_window_coverage_pct=0.0%`

**風險**
- Feature coverage 會持續呈現假前進：archive 在長，但 live fetch 仍失敗，資料實際不可用。

**下一步**
- 配置 `COINGLASS_API_KEY`，先讓 ETF flow source 從 `auth_missing` 轉成成功 snapshot，再評估是否需要歷史 backfill。
- 驗證：`data/execution_metadata_smoke.json`、`/api/features/coverage`、下輪 heartbeat source blockers。

---

## Not Issues
- **data pipeline frozen**：不是；本輪 collect 實際新增 `+1 raw / +1 features / +3 labels`，且 active horizons freshness 仍屬 expected lag。
- **current live q35 support 已 closure**：不是；本輪 rows-aware patch 與 live artifacts 已證明 current live exact bucket 只有 `1/50`，必須維持 `exact_bucket_present_but_below_minimum`。
- **leaderboard split-brain**：不是 current issue；probe / API / docs 目前一致顯示 `rule_baseline / core_only / scan_backed_best`。
- **reference-only patch 消失**：不是 current issue；`core_plus_macro` 仍在 probe / drilldown / issues.json 可見，且 status 正確為 `reference_only_until_exact_support_ready`。

---

## Current Priority
1. **維持 breaker-first truth across `/` / `/execution` / `/execution/status` / `/lab` / probe / drilldown / docs**
2. **把 current-live q35 `1/50` support truth 與 reference-only `core_plus_macro` patch 一起 machine-read，避免再退回假 closure**
3. **把 recent canonical 250-row pathology 當成 breaker 根因持續鑽深，不被 broader leaderboard / venue 討論稀釋**
4. **守住 leaderboard recent-window contract：runtime API、persisted snapshot、probe、`issues.json`、browser `/lab` 同步顯示同一個 top model / profile 真相**
5. **持續保留 per-venue blockers 與 source auth blockers，可見直到 credentials / ack / fill / CoinGlass auth 真正 closure**
