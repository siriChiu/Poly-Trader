# ISSUES.md — Current State Only

_最後更新：2026-04-19 19:18:06 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **本輪 heartbeat #20260419ae 已完成 fast collect + verify 閉環**：`Raw=31131 (+1) / Features=22549 (+2) / Labels=62643 (+4)`；active horizons `240m / 1440m` freshness 仍是 `expected_horizon_lag`，資料管線不是 frozen。
- **本輪產品化 patch 已落地：Dashboard Execution 摘要改為 breaker-first copy**：`web/src/pages/Dashboard.tsx` 現在先顯示 `current live blocker {deployment_blocker} · {deployment_blocker_reason}`，再分行顯示 `venue blockers`；`tests/test_frontend_decision_contract.py` 新增 regression 鎖住這個順序，避免首頁再把 venue readiness 摘要放到 current-live blocker 前面。
- **本輪 runtime recovery 已完成：127.0.0.1:8000 的 stale uvicorn 已被替換**：舊的 `:8000` 進程對 `/api/status`、`/api/predict/confidence`、`/api/models/leaderboard` 全部 timeout；重啟後三條 API 均恢復 `200 OK`，browser DOM 也已讀到 `current live blocker circuit_breaker_active` 與獨立的 `venue blockers ...` 文案。
- **canonical current-live 唯一 deployment blocker 仍是 circuit breaker**：`deployment_blocker=circuit_breaker_active`、`streak=268`、`recent 50 wins=0/50`、`additional_recent_window_wins_needed=15`、`allowed_layers=0`、`runtime_closure_state=circuit_breaker_active`。
- **current live bucket 維持 `CAUTION|base_caution_regime_or_bias|q15`**：`regime=chop`、`gate=CAUTION`、`entry_quality=0.4381 (D)`；exact support 仍是 `0/50`，`support_route_verdict=exact_bucket_missing_proxy_reference_only`、`support_governance_route=exact_live_bucket_proxy_available`、`support_progress.status=stalled_under_minimum`、`gap_to_minimum=50`、`remaining_gap_to_floor=0.1119`、`best_single_component=feat_4h_bias50`。
- **recent canonical 250 rows 仍是 distribution pathology**：`win_rate=0.0000`、`dominant_regime=bull(100%)`、`avg_pnl=-0.0103`、`avg_quality=-0.2861`、`avg_drawdown_penalty=0.3762`、`tail_streak=250x0`；主 shifts 為 `feat_4h_bb_pct_b`、`feat_4h_bias20`、`feat_4h_rsi14`，新增 `feat_vwap_dev` 壓縮。
- **support-aware patch 仍是 reference-only**：`recommended_patch=core_plus_macro`、`recommended_patch_status=reference_only_until_exact_support_ready`、`reference_scope=bull|CAUTION`、`support_route_verdict=exact_bucket_missing_proxy_reference_only`、`gap_to_minimum=50`。
- **canonical leaderboard / Strategy Lab contract 仍守住**：`/api/models/leaderboard` 為 `count=6 / comparable_count=6 / placeholder_count=0`，`evaluation_fold_window=latest_bounded_walk_forward`、`evaluation_max_folds=4`；top row 仍是 `random_forest / core_only / scan_backed_best`。
- **venue readiness 與 source blockers 仍未 closure**：Binance / OKX 目前只有 metadata proof，缺 `live exchange credential / order ack lifecycle / fill lifecycle`；`fin_netflow` 仍是 `source_auth_blocked`，因 `COINGLASS_API_KEY` 缺失而無法把 `archive_window_coverage_pct` 從 `0.0%` 往前推。
- **驗證證據已齊**：`pytest tests/test_hb_parallel_runner.py tests/test_auto_propose_fixes.py tests/test_frontend_decision_contract.py -q` = `108 passed`；`pytest tests/test_model_leaderboard.py tests/test_strategy_lab.py tests/test_frontend_decision_contract.py -q` = `99 passed`；`cd web && npm run build` 通過；browser DOM 驗證 Dashboard 已顯示 `current live blocker circuit_breaker_active` 並把 `venue blockers` 分開呈現；`curl` / `urllib` 驗證 `:8000` 三條核心 API 皆回 `200`。

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
**現況**
- `deployment_blocker=circuit_breaker_active`
- `streak=268`
- `recent_window=50`
- `current_recent_window_wins=0`
- `required_recent_window_wins=15`
- `additional_recent_window_wins_needed=15`
- `allowed_layers=0`
- `runtime_closure_state=circuit_breaker_active`

**風險**
- 若 `/`、`/execution`、`/execution/status`、`/lab`、probe、drilldown 任一 surface 再把 q15 / venue / spillover 摘要排到 breaker release math 前面，operator 會失去唯一 current-live blocker 真相。

**下一步**
- 維持 breaker-first truth 在 `/`、`/execution`、`/execution/status`、`/lab`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`issues.json`、`ISSUES.md` 一致。
- 驗證：browser `/`、browser `/execution`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`。

### P0. recent canonical 250 rows remains a distribution pathology
**現況**
- `recent_window=250`
- `win_rate=0.0000`
- `dominant_regime=bull`
- `dominant_regime_share=1.0000`
- `avg_pnl=-0.0103`
- `avg_quality=-0.2861`
- `avg_drawdown_penalty=0.3762`
- `alerts=['constant_target','regime_concentration','regime_shift']`
- `tail_streak=250x0`
- top feature shifts：`feat_4h_bb_pct_b`、`feat_4h_bias20`、`feat_4h_rsi14`
- new compressed：`feat_vwap_dev`

**風險**
- 若 breaker 根因被 broader history、leaderboard 勝負或 venue 診斷稀釋，修復會再次偏離 pathological slice 本身。

**下一步**
- 以 recent canonical rows 為主做 feature variance / distinct-count / target-path drilldown，避免把 blocker 誤寫成 generic leaderboard 或 venue 議題。
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
- `remaining_gap_to_floor=0.1119`
- `best_single_component=feat_4h_bias50`
- `governance_contract=dual_role_governance_active`

**風險**
- 若 probe / docs / UI 再退回舊的 support 路由語義，或把 under-breaker q15 診斷說成 deployable，operator 會誤判 exact support lane 與治理路徑。

**下一步**
- 維持 `0/50 + exact_bucket_missing_proxy_reference_only + stalled_under_minimum + gap_to_minimum=50` 在 probe / API / UI / docs / summary 一致 machine-read。
- 驗證：`python scripts/hb_q15_support_audit.py`、`python scripts/hb_predict_probe.py`、`python scripts/hb_parallel_runner.py --fast --hb <run>`、browser `/lab`、browser `/execution/status`。

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

### P1. leaderboard recent-window contract is delivered; keep it stable and runtime-backed
**現況**
- `/api/models/leaderboard`: `count=6`、`comparable_count=6`、`placeholder_count=0`
- `evaluation_fold_window=latest_bounded_walk_forward`
- `evaluation_max_folds=4`
- top model（目前 API）=`random_forest / core_only / scan_backed_best`
- governance state=`dual_role_governance_active`

**風險**
- 若 payload 回退到 placeholder-only、profile governance drift、或 `:8000` runtime 再次 timeout，canonical model surface 會回到不可比較或 UI 無法消費的狀態。

**下一步**
- 維持 `/api/models/leaderboard`、Strategy Lab 工作區與模型排行都使用 latest bounded walk-forward + 兩年預設區間，且 runtime API 必須保持可回應。
- 驗證：`curl http://127.0.0.1:8000/api/models/leaderboard`、browser `/lab`、`pytest tests/test_model_leaderboard.py tests/test_strategy_lab.py tests/test_frontend_decision_contract.py -q`。

### P1. venue readiness is still unverified
**現況**
- `binance`: `config enabled + public-only + metadata OK`
- `okx`: `config disabled + public-only + metadata OK`
- 缺的 runtime proof：`live exchange credential`、`order ack lifecycle`、`fill lifecycle`

**風險**
- breaker 未來解除後，若 venue blockers 被弱化成摘要字串或完全消失，使用者會被誤導成已可實盤。

**下一步**
- 持續保留 per-venue blockers，但它們必須永遠位於 breaker-first current blocker 之後。
- 驗證：browser `/`、browser `/execution`、browser `/execution/status`、browser `/lab`、`data/execution_metadata_smoke.json`。

### P1. fin_netflow source_auth_blocked remains open
**現況**
- `fin_netflow=source_auth_blocked`
- `latest_status=auth_missing`
- blocker 根因：`COINGLASS_API_KEY is missing`
- `forward_archive_rows=2602`
- `archive_window_coverage_pct=0.0%`

**風險**
- Feature coverage 會持續呈現假前進：archive 在長，但 live fetch 仍失敗，資料實際不可用。

**下一步**
- 配置 `COINGLASS_API_KEY`，先讓 ETF flow source 從 `auth_missing` 轉成成功 snapshot，再評估是否需要歷史 backfill。
- 驗證：`data/execution_metadata_smoke.json`、`/api/features/coverage`、下輪 heartbeat source blockers。

---

## Not Issues
- **data pipeline frozen**：不是；本輪 collect 實際新增 `+1 raw / +2 features / +4 labels`，且 active horizons freshness 仍屬 expected lag。
- **Dashboard 把 venue blockers 放在 current-live blocker 前面**：不是 current issue；本輪已用 blocker-first copy + regression test 修復，browser DOM 已看到 `current live blocker circuit_breaker_active` 先於 `venue blockers`。
- **127.0.0.1:8000 API unavailable**：不是 current issue；本輪已替換 stale uvicorn，`/api/status`、`/api/predict/confidence`、`/api/models/leaderboard` 皆恢復 `200 OK`。

---

## Current Priority
1. **維持 breaker-first truth across `/` / `/execution` / `/execution/status` / `/lab` / probe / drilldown**
2. **把 recent canonical 250 rows pathology 當成 breaker 根因持續鑽深，不被 broader history 或 leaderboard 勝負稀釋**
3. **把 q15 `0/50` 與 reference-only `core_plus_macro` patch 一起維持 machine-read，避免 support route / patch visibility 再 drift**
4. **守住 canonical leaderboard comparable rows、dual-role governance、Strategy Lab 兩年回測 contract，以及 `:8000` runtime API 可回應**
5. **持續保留 per-venue blockers 與 source auth blockers，可見直到 credentials / ack / fill / CoinGlass auth 真正 closure**
