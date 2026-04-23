# ISSUES.md — Current State Only

_最後更新：2026-04-24 01:22:45 CST_

只保留目前有效問題；由 heartbeat runner overwrite sync，避免 current-state markdown 落後 issues.json / live artifacts。

---

## 當前主線事實
- **最新 fast heartbeat #fast 已完成 collect + diagnostics refresh**
  - `Raw=32081 / Features=23499 / Labels=64291`
  - 歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`
  - `simulated_pyramid_win=57.04%`
- **canonical current-live blocker 仍是 breaker-first truth**
  - `deployment_blocker=circuit_breaker_active` / `streak=3` / `recent_window_wins=7/50` / `additional_recent_window_wins_needed=8`
  - `current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_proxy_reference_only`
- **recent canonical diagnostics 已刷新**
  - `latest_window=100` / `win_rate=45.0%` / `dominant_regime=bull(100.0%)` / `avg_quality=+0.1441` / `avg_pnl=+0.0014` / `alerts=regime_concentration,regime_shift`
  - `blocking_window=1000` / `win_rate=41.7%` / `dominant_regime=bull(80.4%)` / `avg_quality=+0.1189` / `avg_pnl=+0.0030` / `alerts=regime_shift`
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- **source / venue blockers 仍開啟**
  - `blocked_sparse_features=8` / `{'archive_required': 3, 'snapshot_only': 4, 'short_window_public_api': 1}`
  - fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3549` / `archive_window_coverage_pct=0.0`
  - venue：`live exchange credential / order ack lifecycle / fill lifecycle` 尚未有 runtime-backed proof
- **heartbeat current-state docs overwrite sync 已自動化**
  - `scripts/hb_parallel_runner.py` 現在會在 `auto_propose_fixes.py` 後自動覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 目的：避免 markdown docs 落後 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json`，讓 cron 心跳真正完成 docs overwrite 閉環
- **Strategy Lab same-origin workspace fetch 已補上 timeout + direct-backend failover**
  - `web/src/pages/StrategyLab.tsx` 現在會先嘗試 same-origin `/api/*`，若 Vite proxy / shell route 卡住超過 `2.5s` 就 abort 並 fallback 到 active backend，不再讓工作區初始化被單一路徑卡死
  - 驗證：`pytest tests/test_model_leaderboard.py tests/test_strategy_lab.py tests/test_frontend_decision_contract.py tests/test_strategy_lab_uniqueness_contract.py -q`、`cd web && npm run build`、browser `/lab` 最終回到 `▶ 執行回測`

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
- 目前真相：`deployment_blocker=circuit_breaker_active` / `streak=3` / `recent 50 wins=7/50` / `additional_recent_window_wins_needed=8`
- same-bucket truth：`bucket=BLOCK|bull_q15_bias50_overextended_block|q15` / `support=0/50` / `support_route_verdict=exact_bucket_missing_proxy_reference_only` / `support_governance_route=exact_live_bucket_proxy_available`
- 下一步：先把 current-live blocker 語義切回 circuit breaker release math；在 breaker 未解除前，不要把 q15/q35 support 或 floor-gap 當成本輪主 blocker。 recent 50 需至少 15 勝，當前 7 勝，還差 8 勝；同時 streak 必須 < 50。

### P0. recent canonical window 1000 rows = regime_concentration
- 目前真相：`window=1000` / `win_rate=41.7%` / `dominant_regime=bull(80.4%)` / `avg_quality=+0.1189` / `avg_pnl=+0.0030` / `alerts=regime_shift`
- latest diagnostics：`latest_window=100` / `win_rate=45.0%` / `dominant_regime=bull(100.0%)` / `avg_quality=+0.1441` / `avg_pnl=+0.0014` / `alerts=regime_concentration,regime_shift`
- 病態切片：`alerts=regime_shift` / `tail_streak=3x0` / `top_shift=feat_vwap_dev,feat_4h_bias200,feat_eye` / `new_compressed=feat_4h_bias200`
- 下一步：直接對 recent canonical 1000-row bull concentration pocket 做 variance / distinct-count / target-path drill-down；維持 decision-quality guardrails，並檢查 calibration scope 是否仍被這個 toxic bull slice 稀釋。 recent_window=1000, alerts=['regime_shift'], win_rate=0.4170, dominant_regime=bull(80.40%), avg_pnl=+0.0030, avg_quality=0.1189, avg_dd_penalty=0.2388, spot_long_win_rate=0.3010, top_shift=feat_vwap_dev/feat_4h_bias200/feat_eye, tail_streak=3x0, adverse_streak=273x0。
- 驗證：
  - python scripts/recent_drift_report.py
  - python scripts/hb_predict_probe.py

### P1. support-aware core_plus_macro_plus_all_4h patch must stay visible but reference-only outside current live scope
- 目前真相：`bucket=BLOCK|bull_q15_bias50_overextended_block|q15` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_proxy_reference_only` / `governance_route=exact_live_bucket_proxy_available`
- 下一步：Keep the same recommended_patch summary across /api/status, /lab, hb_predict_probe.py, live_decision_quality_drilldown.py, and docs; the patch describes a spillover/broader lane rather than the current live scope, so do not promote it to a deployable runtime patch even though exact support is available.

### P1. venue readiness is still unverified
- 目前真相：`binance=config enabled + public-only + metadata OK` / `okx=config disabled + public-only + metadata OK` / `missing_runtime_proof=live exchange credential, order ack lifecycle, fill lifecycle`
- 下一步：Keep per-venue blockers explicitly visible on Dashboard, /lab, and /execution/status until credentials, order ack lifecycle, and fill lifecycle each have runtime-backed proof.
- 驗證：
  - browser /execution
  - browser /execution/status
  - browser /lab
  - data/execution_metadata_smoke.json

### P1. fin_netflow remains source_auth_blocked because COINGLASS_API_KEY is missing
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3549` / `archive_window_coverage_pct=0.0`
- 下一步：Configure COINGLASS_API_KEY, then keep heartbeat collection running until successful ETF-flow snapshots replace auth_missing rows and coverage starts to move.
- 驗證：
  - data/execution_metadata_smoke.json
  - /api/features/coverage

### P1. leaderboard comparable rows are back; keep the recent-window contract stable and cron-safe
- 目前真相：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- 下一步：Keep /api/models/leaderboard and Strategy Lab aligned on latest bounded walk-forward plus the recent-two-year backtest policy; do not regress to placeholder-only or ambiguous backtest windows.
- 驗證：
  - browser /lab
  - curl http://127.0.0.1:<active-backend>/api/models/leaderboard
  - pytest tests/test_model_leaderboard.py tests/test_strategy_lab.py tests/test_frontend_decision_contract.py -q

### P1. q15 exact support regressed back under minimum under breaker (0/50)
- 目前真相：`bucket=BLOCK|bull_q15_bias50_overextended_block|q15` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_proxy_reference_only` / `governance_route=exact_live_bucket_proxy_available`
- 下一步：Treat this as support regression, not ordinary stagnation: keep support_route_verdict/support_progress/minimum_support_rows/gap_to_minimum plus the last-supported reference visible in probe/API/UI/docs, and verify why the current bucket fell back under minimum.

---

## Current Priority
1. **維持 breaker-first truth，同時保留 q15 current-live bucket support rows 可 machine-read**
2. **持續沿 recent canonical pathological slice 追根因，不要 generic 化 blocker**
3. **守住 q15 current-live bucket support / reference-only patch、leaderboard dual-role governance、venue/source blockers 可見性**
4. **讓 heartbeat 自動 overwrite sync current-state docs，不再把 docs drift 留給人工補寫**
