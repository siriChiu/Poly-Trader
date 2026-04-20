# ISSUES.md — Current State Only

_最後更新：2026-04-20 19:17:47 CST_

只保留目前有效問題；由 heartbeat / product patch overwrite sync，避免 current-state markdown 落後 issues.json / live artifacts。

---

## 當前主線事實
- **最新 fast heartbeat #fast 已完成 collect + diagnostics refresh**
  - `Raw=31254 / Features=22672 / Labels=63024`
  - `simulated_pyramid_win=57.16%`
- **canonical current-live blocker 仍是 breaker-first truth**
  - `deployment_blocker=circuit_breaker_active` / `streak=0` / `recent_window_wins=14/50` / `additional_recent_window_wins_needed=1`
  - `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q35` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`
- **recent canonical window 仍是 distribution pathology**
  - `window=500` / `win_rate=3.6%` / `dominant_regime=bull(90.6%)` / `avg_quality=-0.2266` / `avg_pnl=-0.0078` / `alerts=label_imbalance,regime_concentration,regime_shift`
- **Strategy Lab 回測實際區間空白已修復**
  - legacy saved strategies 即使遺失 `last_results.backtest_range`，後端現在也會從 `definition.params.backtest_range + chart_context` 補回 `requested/effective/available`
  - `/lab` 的「實際區間」現在會 fallback 到 effective → requested → strategy definition → chart context，不再顯示 `— → —`
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- **source / venue blockers 仍開啟**
  - `blocked_sparse_features=8` / `{'archive_required': 3, 'snapshot_only': 4, 'short_window_public_api': 1}`
  - fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=2725` / `archive_window_coverage_pct=0.0`
  - venue：`live exchange credential / order ack lifecycle / fill lifecycle` 尚未有 runtime-backed proof

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
- 目前真相：`deployment_blocker=circuit_breaker_active` / `streak=0` / `recent 50 wins=14/50` / `additional_recent_window_wins_needed=1`
- same-bucket truth：`bucket=CAUTION|base_caution_regime_or_bias|q35` / `support=0/50` / `support_route_verdict=exact_bucket_unsupported_block` / `support_governance_route=exact_live_lane_proxy_available`
- 下一步：先把 current-live blocker 語義切回 circuit breaker release math；在 breaker 未解除前，不要把 q15/q35 support 或 floor-gap 當成本輪主 blocker。recent 50 需至少 15 勝，當前 14 勝，還差 1 勝；同時 streak 必須 < 50。
- 驗證：browser `/`、browser `/execution`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`

### P0. recent canonical 500 rows remains a distribution pathology
- 目前真相：`window=500` / `win_rate=3.6%` / `dominant_regime=bull(90.6%)` / `avg_quality=-0.2266` / `avg_pnl=-0.0078`
- 病態切片：`alerts=label_imbalance,regime_concentration,regime_shift` / `tail_streak=12` / `low_variance=9` / `low_distinct=10` / `null_heavy=10`
- 下一步：直接對 recent canonical rows 做 feature variance / distinct-count / target-path drill-down；維持 decision-quality guardrails，並檢查 calibration scope 是否仍被病態 slice 稀釋。
- 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`

### P1. support-aware core_plus_macro_plus_all_4h patch must stay visible but reference-only
- 目前真相：`bucket=CAUTION|base_caution_regime_or_bias|q35` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only` / `governance_route=exact_live_lane_proxy_available`
- 下一步：Keep the same recommended_patch summary across `/api/status`、`/lab`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、docs；在 exact support 達標前不得把它升級為 deployable truth。

### P1. venue readiness is still unverified
- 目前真相：`binance=config enabled + public-only + metadata OK` / `okx=config disabled + public-only + metadata OK` / `missing_runtime_proof=live exchange credential, order ack lifecycle, fill lifecycle`
- 下一步：Keep per-venue blockers explicitly visible on Dashboard、`/lab`、`/execution/status`，直到 credentials、order ack lifecycle、fill lifecycle 都有 runtime-backed proof。
- 驗證：browser `/execution`、browser `/execution/status`、browser `/lab`、`data/execution_metadata_smoke.json`

### P1. fin_netflow remains source_auth_blocked because COINGLASS_API_KEY is missing
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=2725` / `archive_window_coverage_pct=0.0`
- 下一步：補上 `COINGLASS_API_KEY`，讓 ETF-flow snapshots 從 `auth_missing` 轉為成功資料，coverage 才會開始推進。
- 驗證：`data/execution_metadata_smoke.json`、`/api/features/coverage`

### P1. keep Strategy Lab recent-window / actual-range contract stable and cron-safe
- 目前真相：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- 本輪已修復：legacy saved strategies 缺 `backtest_range` 時，`/api/strategies/*` 與 `/lab` 不再把實際區間顯示成空白。
- 下一步：Keep `/api/models/leaderboard`、`/api/strategies/leaderboard`、Strategy Lab 的最近兩年 / 實際區間 contract 一致；不要回退成 placeholder-only、短窗假回測、或 `— → —` 空白區間。
- 驗證：browser `/lab`、`python scripts/hb_strategy_range_probe.py`、`pytest tests/test_strategy_lab.py tests/test_strategy_lab_date_range_contract.py tests/test_frontend_decision_contract.py tests/test_model_leaderboard.py -q`

---

## Current Priority
1. **維持 breaker-first truth，同時保留 current live bucket support rows 可 machine-read**
2. **持續沿 recent canonical pathological slice 追根因，不要 generic 化 blocker**
3. **守住 current live bucket support / reference-only patch、leaderboard dual-role governance、Strategy Lab 實際區間 contract、venue/source blockers 可見性**
4. **讓 heartbeat 與 product patch 持續 overwrite sync current-state docs，不再把 docs drift 留給人工補寫**
