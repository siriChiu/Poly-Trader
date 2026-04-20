# ISSUES.md — Current State Only

_最後更新：2026-04-20 08:30:20 CST_

只保留目前有效問題；heartbeat 與本輪 patch 後的 current-state truth 必須覆蓋同步，不保留歷史流水帳。

---

## 當前主線事實
- **最新 fast heartbeat #fast 已完成 collect + diagnostics refresh**
  - `Raw=31186 / Features=22604 / Labels=62909`
  - `simulated_pyramid_win=57.17%`
- **canonical current-live blocker 仍是 breaker-first truth**
  - `deployment_blocker=circuit_breaker_active` / `streak=191` / `recent_window_wins=0/50` / `additional_recent_window_wins_needed=15`
  - `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q00` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_unsupported_block`
  - `support_governance_route=exact_live_lane_proxy_available` / `recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_until_exact_support_ready`
- **recent canonical window 仍是 distribution pathology**
  - `window=100` / `win_rate=0.0%` / `dominant_regime=bull(100.0%)` / `avg_quality=-0.2363` / `avg_pnl=-0.0095`
  - `alerts=constant_target,regime_concentration,regime_shift` / `tail_streak=100x0`
- **Dashboard dev-runtime WebSocket failover 已修復**
  - 原因：Vite 首次會先打 `ws://127.0.0.1:8000/ws/live`，但 8000 reload lane opening handshake timeout；穩定 lane 在 `8001` 正常。
  - 本輪 patch 後：Dashboard 會對 `8000 → 8001` 做 candidate fallback，不再因單一路徑卡死而長時間顯示假性「離線」。
  - 驗證：browser `/` 已顯示 `即時連線`，且 `current live blocker circuit_breaker_active` / `Metadata freshness=fresh` 可正常落地。
- **source / venue blockers 仍開啟**
  - `blocked_sparse_features=8` / `{'archive_required': 3, 'snapshot_only': 4, 'short_window_public_api': 1}`
  - fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=2657` / `archive_window_coverage_pct=0.0`
  - venue：`live exchange credential / order ack lifecycle / fill lifecycle` 尚未有 runtime-backed proof
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro` / `governance_contract=dual_role_governance_active`

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
- 目前真相：`deployment_blocker=circuit_breaker_active` / `streak=191` / `recent 50 wins=0/50` / `additional_recent_window_wins_needed=15`
- current-live bucket：`bucket=CAUTION|base_caution_regime_or_bias|q00` / `rows=0/50` / `gap=50` / `support_route_verdict=exact_bucket_unsupported_block`
- governance lane：`support_governance_route=exact_live_lane_proxy_available`，但只能支撐 reference-only recommended patch，不可覆蓋 breaker-first truth。
- 下一步：維持 breaker release math 作為唯一 current-live 主 blocker；在 breaker 未解除前，不要把 q15/q35 support 或 floor-gap 升級成主敘事。
- 驗證：browser `/`、browser `/execution`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`

### P0. recent canonical pathological slice still dominates the breaker root cause
- 目前真相：`window=100` / `win_rate=0.0%` / `dominant_regime=bull(100.0%)` / `avg_quality=-0.2363` / `avg_pnl=-0.0095`
- 病態切片：`alerts=constant_target,regime_concentration,regime_shift` / `tail_streak=100x0` / `low_variance=26` / `low_distinct=14` / `null_heavy=10`
- 下一步：繼續沿 recent pathological slice 追 target-path、adverse streak、top feature shifts；不要退回 generic leaderboard / venue 摘要。
- 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`

### P1. support-aware patch must stay visible but reference-only
- 目前真相：`recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_until_exact_support_ready` / `reference_scope=bull|CAUTION`
- live truth：current bucket 仍是 `q00` 且 exact support `0/50`，所以 patch 只能作治理 / 訓練參考，不得包裝成 deployable truth。
- 驗證：`/api/status`、`/execution/status`、`/lab`、`data/live_predict_probe.json`、`data/live_decision_quality_drilldown.json`

### P1. venue readiness is still unverified
- 目前真相：`binance=config enabled + public-only + metadata OK` / `okx=config disabled + public-only + metadata OK`
- 缺口：`live exchange credential / order ack lifecycle / fill lifecycle`
- 下一步：在 Dashboard、Execution Status、Strategy Lab 持續明示 per-venue blockers，直到拿到 runtime-backed proof。
- 驗證：browser `/execution`、browser `/execution/status`、browser `/lab`、`data/execution_metadata_smoke.json`

### P1. fin_netflow remains source_auth_blocked because COINGLASS_API_KEY is missing
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=2657` / `archive_window_coverage_pct=0.0`
- 下一步：補上 `COINGLASS_API_KEY`，讓 forward snapshots 從 auth_missing 轉成成功資料，再觀察 coverage 是否開始前進。
- 驗證：`data/execution_metadata_smoke.json`、`/api/features/coverage`

### P1. leaderboard recent-window contract must remain stable and cron-safe
- 目前真相：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- 下一步：守住 `/api/models/leaderboard` 與 Strategy Lab 的 bounded walk-forward / recent-two-year contract，不回退 placeholder-only 或模糊 backtest window。
- 驗證：browser `/lab`、`curl http://127.0.0.1:8001/api/models/leaderboard`、`pytest tests/test_model_leaderboard.py tests/test_strategy_lab.py tests/test_frontend_decision_contract.py -q`

---

## Current Priority
1. **維持 breaker-first truth，同時保留 current live bucket rows / support route machine-readable**
2. **持續沿 recent canonical pathological slice 追根因，不把 root cause generic 化**
3. **守住 current live bucket reference-only patch、leaderboard dual-role governance、venue/source blockers 可見性**
4. **避免 Dashboard / Strategy Lab 再因 dev-runtime lane failover 出現假性離線或 stale loading**
