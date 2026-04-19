# ISSUES.md — Current State Only

_最後更新：2026-04-19 21:03:53 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **本輪 heartbeat #20260419ah 已完成 fast collect + verify 閉環**：`Raw=31140 (+1) / Features=22558 (+1) / Labels=62665 (+4)`；active horizons `240m / 1440m` freshness 仍是 `expected_horizon_lag`，資料管線不是 frozen。
- **本輪產品化 patch 已落地：leaderboard freshness arbitration**
  - `server/routes/api.py::_load_model_leaderboard_cache_file()` 現在會同時比較 disk cache 與最新 persisted snapshot，永遠採用 `updated_at` 較新的 payload；舊但非空的 cache 不再覆蓋更新的 snapshot。
  - `scripts/hb_leaderboard_candidate_probe.py::_load_leaderboard_payload()` 也同步採用同一 freshness 規則，避免 probe / `issues.json` / current-state docs 還停在舊排行榜。
  - regression 已補齊：`tests/test_model_leaderboard.py` 與 `tests/test_hb_leaderboard_candidate_probe.py` 新增「newer snapshot beats older cache」測試。
- **驗證證據已齊**
  - `pytest tests/test_auto_propose_fixes.py tests/test_model_leaderboard.py tests/test_hb_leaderboard_candidate_probe.py -q` = `85 passed`
  - `python scripts/hb_parallel_runner.py --fast --hb 20260419ah` 完成 collect / IC / drift / probe / auto-propose 閉環
  - `curl http://127.0.0.1:8000/api/models/leaderboard` = `count=6 / comparable_count=6 / placeholder_count=0 / top=rule_baseline / core_only / scan_backed_best`
  - browser `/lab` 與 `/execution/status` 已驗證 breaker-first truth：`current live blocker=circuit_breaker_active`、venue blockers 分開顯示、`support 0/50` 與 `layers 0→0` 可讀
- **canonical current-live 唯一 deployment blocker 仍是 circuit breaker**：`deployment_blocker=circuit_breaker_active`、`streak=273`、`recent 50 wins=0/50`、`additional_recent_window_wins_needed=15`、`allowed_layers=0`、`runtime_closure_state=circuit_breaker_active`。
- **current live bucket 維持 `CAUTION|base_caution_regime_or_bias|q15`**：`regime=chop`、`gate=CAUTION`、`entry_quality=0.3285 (D)`；exact support 仍是 `0/50`，`support_route_verdict=exact_bucket_missing_proxy_reference_only`、`support_governance_route=exact_live_bucket_proxy_available`、`remaining_gap_to_floor=0.2215`、`best_single_component=feat_4h_bias50`。
- **recent canonical 250 rows 仍是 distribution pathology**：`win_rate=0.0000`、`dominant_regime=bull(100%)`、`avg_pnl=-0.0101`、`avg_quality=-0.2845`、`avg_drawdown_penalty=0.3744`、`tail_streak=250x0`；top shifts=`feat_4h_bb_pct_b`、`feat_4h_bias20`、`feat_4h_bias50`；new compressed=`feat_vwap_dev`。
- **leaderboard recent-window contract 目前一致**：`/api/models/leaderboard` 與 `data/leaderboard_feature_profile_probe.json` 都是 `count=6 / comparable_count=6 / placeholder_count=0`；top row=`rule_baseline / core_only / scan_backed_best`；`governance=dual_role_governance_active`、`closure=global_ranking_vs_support_aware_production_split`、`leaderboard_payload_source=live_rebuild`。
- **support-aware patch 仍是 reference-only**：`recommended_patch=core_plus_macro`、`recommended_patch_status=reference_only_until_exact_support_ready`、`reference_scope=bull|CAUTION`、`gap_to_minimum=50`。
- **venue / source blockers 仍未 closure**：Binance / OKX 仍缺 `live exchange credential / order ack lifecycle / fill lifecycle`；`fin_netflow` 仍是 `source_auth_blocked`，根因是 `COINGLASS_API_KEY` 缺失，forward archive rows=`2611`，`archive_window_coverage_pct=0.0%`。

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
**現況**
- `deployment_blocker=circuit_breaker_active`
- `streak=273`
- `recent_window=50`
- `current_recent_window_wins=0`
- `required_recent_window_wins=15`
- `additional_recent_window_wins_needed=15`
- `allowed_layers=0`
- `runtime_closure_state=circuit_breaker_active`

**風險**
- 若 `/`、`/execution`、`/execution/status`、`/lab`、probe、drilldown、docs 任一 surface 再把 q15 / spillover / venue 摘要排到 breaker release math 前面，operator 會失去唯一 current-live blocker 真相。

**下一步**
- 維持 breaker-first truth 在 `/`、`/execution`、`/execution/status`、`/lab`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`issues.json`、`ISSUES.md` 一致。
- 驗證：browser `/lab`、browser `/execution/status`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`。

### P0. recent canonical 250 rows remains a distribution pathology
**現況**
- `recent_window=250`
- `win_rate=0.0000`
- `dominant_regime=bull`
- `dominant_regime_share=1.0000`
- `avg_pnl=-0.0101`
- `avg_quality=-0.2845`
- `avg_drawdown_penalty=0.3744`
- `alerts=['constant_target','regime_concentration','regime_shift']`
- `tail_streak=250x0`
- top feature shifts=`feat_4h_bb_pct_b`、`feat_4h_bias20`、`feat_4h_bias50`
- new compressed=`feat_vwap_dev`

**風險**
- 若 breaker 根因被 broader leaderboard、venue readiness、或 generic model-stability 討論稀釋，修復會再次偏離 pathological slice 本身。

**下一步**
- 以 recent canonical rows 為主做 feature variance / target-path / gate-path drilldown，不要再把 blocker 重述成 generic leaderboard 或 venue 問題。
- 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`。

### P1. q15 exact support remains under minimum under breaker (0/50)
**現況**
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`
- `live_current_structure_bucket_rows=0`
- `minimum_support_rows=50`
- `gap_to_minimum=50`
- `support_route_verdict=exact_bucket_missing_proxy_reference_only`
- `support_governance_route=exact_live_bucket_proxy_available`
- `support_progress.status=stalled_under_minimum`
- `remaining_gap_to_floor=0.2215`
- `best_single_component=feat_4h_bias50`
- `governance_contract=dual_role_governance_active`

**風險**
- 若 probe / docs / UI 再退回舊 support 路由語義，或把 under-breaker q15 診斷說成 deployable，operator 會誤判 exact support lane 與治理路徑。

**下一步**
- 維持 `0/50 + exact_bucket_missing_proxy_reference_only + stalled_under_minimum + gap_to_minimum=50` 在 probe / API / UI / docs / summary 一致 machine-read。
- 驗證：`python scripts/hb_q15_support_audit.py`、`python scripts/hb_predict_probe.py`、browser `/lab`、browser `/execution/status`。

### P1. leaderboard recent-window contract is stable again; keep runtime + docs in sync
**現況**
- `/api/models/leaderboard`: `count=6`、`comparable_count=6`、`placeholder_count=0`
- top row=`rule_baseline / core_only / scan_backed_best`
- governance=`dual_role_governance_active`
- closure=`global_ranking_vs_support_aware_production_split`
- `leaderboard_payload_source=live_rebuild`
- freshness arbitration 已落地：newer snapshot 會勝過 older rowful cache

**風險**
- 若 runtime 或 probe 再讓舊但非空的 cache 遮蔽較新的 snapshot，Strategy Lab / docs 會重新出現 split-brain：API 與 current-state 對 top model / profile 說出不同真相。

**下一步**
- 維持 cache-vs-snapshot freshness arbitration、latest bounded walk-forward、與 probe-driven current-state sync；避免 placeholder-only / stale top model 回歸。
- 驗證：`pytest tests/test_auto_propose_fixes.py tests/test_model_leaderboard.py tests/test_hb_leaderboard_candidate_probe.py -q`、`curl http://127.0.0.1:8000/api/models/leaderboard`、browser `/lab`。

### P1. support-aware `core_plus_macro` patch must stay visible but reference-only
**現況**
- `recommended_patch=core_plus_macro`
- `recommended_patch_status=reference_only_until_exact_support_ready`
- `reference_scope=bull|CAUTION`
- `support_route_verdict=exact_bucket_missing_proxy_reference_only`
- `gap_to_minimum=50`

**風險**
- 若 `recommended_patch` 消失或被升級成 deployable，operator 會失去唯一 support-aware 治理方向，或被誤導成 runtime 已可放行。

**下一步**
- 維持 `recommended_patch` 在 `/api/status`、`/lab`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`issues.json`、`ISSUES.md` 一致；只允許 `reference-only`，直到 exact support 達標。
- 驗證：`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、browser `/lab`。

### P1. venue readiness is still unverified
**現況**
- `binance`: `config enabled + public-only + metadata OK`
- `okx`: `config disabled + public-only + metadata OK`
- 缺的 runtime proof：`live exchange credential`、`order ack lifecycle`、`fill lifecycle`

**風險**
- breaker 未來解除後，若 venue blockers 被弱化成摘要字串或完全消失，使用者會被誤導成已可實盤。

**下一步**
- 持續保留 per-venue blockers，但它們必須永遠位於 breaker-first current blocker 之後。
- 驗證：browser `/lab`、browser `/execution/status`、`data/execution_metadata_smoke.json`。

### P1. fin_netflow source_auth_blocked remains open
**現況**
- `fin_netflow=source_auth_blocked`
- `latest_status=auth_missing`
- blocker 根因：`COINGLASS_API_KEY is missing`
- `forward_archive_rows=2611`
- `archive_window_coverage_pct=0.0%`

**風險**
- Feature coverage 會持續呈現假前進：archive 在長，但 live fetch 仍失敗，資料實際不可用。

**下一步**
- 配置 `COINGLASS_API_KEY`，先讓 ETF flow source 從 `auth_missing` 轉成成功 snapshot，再評估是否需要歷史 backfill。
- 驗證：`data/execution_metadata_smoke.json`、`/api/features/coverage`、下輪 heartbeat source blockers。

---

## Not Issues
- **data pipeline frozen**：不是；本輪 collect 實際新增 `+1 raw / +1 features / +4 labels`，且 active horizons freshness 仍屬 expected lag。
- **leaderboard 被舊 cache 遮蔽新 snapshot**：不是 current issue；本輪已補 freshness arbitration，`/api/models/leaderboard`、probe、`issues.json` 已一致顯示 `rule_baseline / core_only / scan_backed_best`。
- **Strategy Lab / 執行狀態缺 breaker-first truth**：不是 current issue；browser `/lab` 與 `/execution/status` 已顯示 `current live blocker circuit_breaker_active`，且 venue blockers / runtime closure 分開呈現。
- **127.0.0.1:8000 API unavailable**：不是 current issue；`/api/status`、`/api/predict/confidence`、`/api/models/leaderboard` 皆可回應。

---

## Current Priority
1. **維持 breaker-first truth across `/` / `/execution` / `/execution/status` / `/lab` / probe / drilldown / docs**
2. **把 recent canonical 250 rows pathology 當成 breaker 根因持續鑽深，不被 broader leaderboard / venue 討論稀釋**
3. **維持 q15 `0/50` 與 reference-only `core_plus_macro` patch 一起 machine-read，避免 support route / patch visibility 再 drift**
4. **守住 leaderboard recent-window contract：runtime API、persisted snapshot、probe、`issues.json`、browser `/lab` 同步顯示同一個 top model / profile 真相**
5. **持續保留 per-venue blockers 與 source auth blockers，可見直到 credentials / ack / fill / CoinGlass auth 真正 closure**
