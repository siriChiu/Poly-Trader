# ISSUES.md — Current State Only

_最後更新：2026-04-20 04:59:20 CST_

只保留目前有效問題；heartbeat 必須覆寫本檔，不能保留過期敘事。

---

## 當前主線事實
- **Heartbeat #20260420-runtimefallback 已完成 collect + probe + drift + UI fallback 修補驗證**
  - `Raw=31175 / Features=22593 / Labels=62881`
  - `simulated_pyramid_win=57.21%`
  - collect 本輪實際成長：`+1 raw / +1 features / +5 labels`
- **前端 dev-runtime fallback 已落地並驗證**
  - `http://127.0.0.1:8000/api/status` 在 12s watchdog 內 timeout
  - `http://127.0.0.1:8001/api/status` 回 `200`，耗時 `0.2086s`
  - `ws://127.0.0.1:8000/ws/live` opening handshake timeout
  - `ws://127.0.0.1:8001/ws/live` 握手成功，收到 `{"type":"connected"...}`
  - `web/src/hooks/useApi.ts` 現在會持久化 active backend base 並在 `8000/8001` 間做 timeout-aware fallback；`CandlestickChart.tsx` 改走 `fetchApiResponse()`；`Dashboard.tsx` 會在每次 WS retry 時重算 `buildWsUrl()`
- **canonical current-live blocker 仍是 breaker-first truth**
  - `deployment_blocker=circuit_breaker_active`
  - `streak=175`
  - `recent_window_wins=0/50`
  - `additional_recent_window_wins_needed=15`
  - `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`
  - `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`
- **recent canonical pathological slice 仍未解除**
  - `window=100`
  - `win_rate=0.0%`
  - `dominant_regime=bull(100.0%)`
  - `avg_quality=-0.2254`
  - `avg_pnl=-0.0088`
  - `alerts=constant_target,regime_concentration,regime_shift`
  - `tail_streak=100x0`
- **leaderboard / governance / venue / source blocker 仍在 current truth 中**
  - `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro` / `governance_contract=dual_role_governance_active`
  - venue proof 仍缺：`live exchange credential / order ack lifecycle / fill lifecycle`
  - `fin_netflow=source_auth_blocked`，根因仍是 `COINGLASS_API_KEY` 缺失
- **fast heartbeat timeout regression 已重現**
  - `python scripts/hb_parallel_runner.py --fast --hb 20260420-runtimefallback` 在 `>240s` watchdog 內仍未完成
  - timeout 前只跑完：`hb_collect / regime_ic / full_ic / recent_drift_report`
  - 代表 `--fast` 仍未真正收斂成 cron-safe collect/drift/probe/docs lane

---

## 本輪已完成（非 blocker）
- **Dashboard / Strategy Lab 在 Vite dev shell 下不再被單一後端 port 綁死**
  - 修正項：API fallback、圖表請求共用 fallback、Dashboard WebSocket retry 重算 URL
  - 驗證：`pytest tests/test_frontend_decision_contract.py -q`、`cd web && npm run build`、browser `/`、browser `/execution/status`、browser `/lab`

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
- 目前真相：`deployment_blocker=circuit_breaker_active` / `streak=175` / `recent 50 wins=0/50` / `additional_recent_window_wins_needed=15`
- same-bucket truth：`bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`
- 下一步：維持 breaker-first truth；在 breaker 未解除前，不要把 q15/q35 support 或 floor-gap 誤升級成主 blocker。
- 驗證：browser `/`、browser `/execution`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`

### P0. recent canonical 100-row slice remains a distribution pathology
- 目前真相：`window=100` / `win_rate=0.0%` / `dominant_regime=bull(100.0%)` / `avg_quality=-0.2254` / `avg_pnl=-0.0088`
- 病態切片：`alerts=constant_target,regime_concentration,regime_shift` / `tail_streak=100x0` / `variance=28/56` / `distinct=14` / `null_heavy=10`
- 下一步：持續沿 pathological slice 本身追根因，不要稀釋成 generic leaderboard / venue 摘要。
- 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`

### P1. q15 exact support remains under minimum and the patch must stay reference-only
- 目前真相：`bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=0/50` / `gap=50`
- `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`
- `recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_until_exact_support_ready`
- 下一步：保持 probe / API / UI / docs 對 q15 exact support 與 reference-only patch 的同一語義；不要把 proxy / spillover patch 當成可部署 truth。
- 驗證：browser `/`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`

### P1. leaderboard comparable rows are back; keep the recent-window contract stable and cron-safe
- 目前真相：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro` / `governance_contract=dual_role_governance_active`
- 下一步：維持 `/api/models/leaderboard` 與 Strategy Lab 對 recent-two-year / bounded walk-forward 的一致性，不回退 placeholder-only。
- 驗證：browser `/lab`、`curl http://127.0.0.1:8000/api/models/leaderboard`、`pytest tests/test_model_leaderboard.py tests/test_strategy_lab.py tests/test_frontend_decision_contract.py -q`

### P1. venue readiness is still unverified
- 目前真相：`binance=config enabled + public-only + metadata OK` / `okx=config disabled + public-only + metadata OK`
- 缺的 runtime proof：`live exchange credential / order ack lifecycle / fill lifecycle`
- 下一步：在 Dashboard、Strategy Lab、Execution Status 持續保持 per-venue blocker 可見，直到有 runtime-backed proof。
- 驗證：browser `/execution`、browser `/execution/status`、browser `/lab`、`data/execution_metadata_smoke.json`

### P1. fin_netflow remains source_auth_blocked because COINGLASS_API_KEY is missing
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=2646` / `archive_window_coverage_pct=0.0`
- 下一步：配置 `COINGLASS_API_KEY`，再讓 heartbeat collect 持續跑到成功 snapshot 取代 auth_missing rows。
- 驗證：`data/execution_metadata_smoke.json`、`/api/features/coverage`

### P1. fast heartbeat still overruns the bounded cron lane
- 目前真相：`hb_parallel_runner.py --fast` 在 `>240s` watchdog 內仍未完成；timeout 前只跑完 `hb_collect / regime_ic / full_ic / recent_drift_report`
- 下一步：把 candidate evaluation / leaderboard refresh 收斂到更嚴格 timeout 或 opt-in lane，讓 `--fast` 真正只保留 collect/drift/probe/docs 閉環。
- 驗證：`python scripts/hb_parallel_runner.py --fast --hb <test>` 必須在 bounded watchdog 內完成並完成 docs overwrite sync

---

## Current Priority
1. **守住 breaker-first truth，同時讓 `/` 與 `/lab` 在 Vite dev shell 下穩定連到健康 backend lane**
2. **把 fast heartbeat 壓回真正 cron-safe 的 bounded lane**
3. **持續沿 recent 100-row bull pathological slice 與 q15 0/50 exact support 追根因**
4. **維持 leaderboard dual-role governance、venue blockers、fin_netflow auth blocker 可見性**
