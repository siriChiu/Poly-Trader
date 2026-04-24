# ISSUES.md — Current State Only

_最後更新：2026-04-24 13:04:14 CST_

只保留目前有效問題；由 heartbeat runner overwrite sync，避免 current-state markdown 落後 issues.json / live artifacts。

---

## 當前主線事實
- **最新 fast heartbeat #20260424_1300 已完成 collect + diagnostics refresh**
  - `Raw=32149 / Features=23567 / Labels=64827`
  - 歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`
  - `simulated_pyramid_win=56.99%`
- **canonical current-live blocker 已切到 current-live exact-support truth**
  - `deployment_blocker=under_minimum_exact_live_structure_bucket` / `streak=None` / `recent_window_wins=None/None` / `additional_recent_window_wins_needed=—`
  - `current_live_structure_bucket=CAUTION|structure_quality_caution|q15` / `support=4/50` / `gap=46` / `support_route_verdict=exact_bucket_present_but_below_minimum`
- **recent canonical diagnostics 已刷新**
  - `latest_window=100` / `win_rate=89.0%` / `dominant_regime=bull(100.0%)` / `avg_quality=+0.3900` / `avg_pnl=+0.0054` / `alerts=label_imbalance,regime_concentration,regime_shift`
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- **source / venue blockers 仍開啟**
  - `blocked_sparse_features=8` / `{'archive_required': 3, 'snapshot_only': 4, 'short_window_public_api': 1}`
  - fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3617` / `archive_window_coverage_pct=0.0`
  - venue：`live exchange credential / order ack lifecycle / fill lifecycle` 尚未有 runtime-backed proof
- **heartbeat current-state docs overwrite sync 已自動化**
  - `scripts/hb_parallel_runner.py` 現在會在 `auto_propose_fixes.py` 後自動覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 目的：避免 markdown docs 落後 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json`，讓 cron 心跳真正完成 docs overwrite 閉環
- **reference-only patch truth 已升級成 top-level probe/API contract**
  - `hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`/api/status.execution.live_runtime_truth` 現在都直接輸出 `recommended_patch_profile/status/reference_scope/support_route/gap/current_rows/minimum_rows`
  - 當前值：`core_plus_macro_plus_all_4h` / `reference_only_until_exact_support_ready` / `bull|CAUTION` / `exact_bucket_present_but_below_minimum` / `4/50` / `gap=46`

---

## Open Issues

### P0. current live bucket CAUTION|structure_quality_caution|q15 exact support remains under minimum and remains the deployment blocker (4/50)
- 目前真相：`deployment_blocker=under_minimum_exact_live_structure_bucket` / `bucket=CAUTION|structure_quality_caution|q15` / `support=4/50` / `gap=46` / `runtime_closure_state=patch_inactive_or_blocked`
- same-bucket truth：`support_route_verdict=exact_bucket_present_but_below_minimum` / `support_governance_route=exact_live_bucket_present_but_below_minimum` / `recommended_patch=core_plus_macro_plus_all_4h` / `recommended_patch_status=reference_only_until_exact_support_ready` / `reference_scope=bull|CAUTION`
- 下一步：把 current-live blocker 語義切到 exact-support truth；在 current live bucket 補滿 minimum rows 前，不要把 proxy rows、reference patch、或 breaker 舊敘事誤當成已解除 blocker。

### P0. recent canonical window 100 rows = distribution_pathology
- 目前真相：`window=100` / `win_rate=89.0%` / `dominant_regime=bull(100.0%)` / `avg_quality=+0.3900` / `avg_pnl=+0.0054` / `alerts=label_imbalance,regime_concentration,regime_shift`
- 病態切片：`alerts=label_imbalance,regime_concentration,regime_shift` / `tail_streak=11x0` / `top_shift=feat_local_bottom_score,feat_local_top_score,feat_bb_pct_b` / `new_compressed=feat_nw_width`
- 下一步：直接對 recent canonical rows 做 feature variance / distinct-count / target-path drill-down；維持 decision-quality guardrails，並檢查 calibration scope 是否仍被病態 slice 稀釋。 recent_window=100, alerts=['label_imbalance', 'regime_concentration', 'regime_shift'], win_rate=0.8900, delta_vs_full=+0.2652, dominant_regime=bull(100.00%), interpretation=distribution_pathology, avg_pnl=+0.0054, avg_quality=0.3900, avg_dd_penalty=0.2001, spot_long_win_rate=0.0000, feature_diag=variance:27/56, frozen:3, compressed:24, expected_static:3, overlay_only:5, unexpected_frozen:0, distinct:13, null_heavy:10, tail_streak=11x0 since 2026-04-23 04:19:10.717188 -> 2026-04-23 05:29:25.331476, adverse_streak=11x0 since 2026-04-23 04:19:10.717188 -> 2026-04-23 05:29:25.331476, prev_win_rate=0.44, delta_vs_prev=0.45, prev_quality=0.0532, quality_delta_vs_prev=0.3368, prev_pnl=0.0004, pnl_delta_vs_prev=0.005, top_shift_examples=feat_local_bottom_score(0.3431→0.4373,Δσ=0.413)/feat_local_top_score(0.3295→0.2414,Δσ=0.3911)/feat_bb_pct_b(0.3564→0.4664,Δσ=0.3335), new_compressed=feat_nw_width, frozen_examples=feat_4h_ma_order(0.0/1)/feat_nest_pred(0.0/1)/feat_vix(0.0/1), compressed_examples=feat_body(0.0/100)/feat_scales_ssr(0.0025/77)/feat_ear(0.0036/100), expected_static_examples=feat_4h_ma_order[discrete_regime_feature]/feat_dxy[weekday_macro_market_closed]/feat_vix[weekday_macro_market_closed], overlay_only_examples=feat_claw[research_sparse_source]/feat_claw_intensity[research_sparse_source]/feat_fang_pcr[research_sparse_source], distinct_examples=feat_vix(1/1437)/feat_nest_pred(1/20)/feat_4h_ma_order(1/3), null_examples=feat_4h_dist_swing_high(0.0)/feat_chorus(0.0)/feat_fin_netflow(0.0), recent_examples=2026-04-23 05:26:54.874373:0:bull:-0.1255/2026-04-23 05:28:10.563430:0:bull:-0.1275/2026-04-23 05:29:25.331476:0:bull:-0.1286, adverse_examples=2026-04-23 05:26:54.874373:0:bull:-0.1255/2026-04-23 05:28:10.563430:0:bull:-0.1275/2026-04-23 05:29:25.331476:0:bull:-0.1286
- 驗證：
  - python scripts/recent_drift_report.py
  - python scripts/hb_predict_probe.py

### P1. support-aware core_plus_macro_plus_all_4h patch must stay visible but reference-only
- 目前真相：`bucket=CAUTION|structure_quality_caution|q15` / `support=4/50` / `gap=46` / `support_route_verdict=exact_bucket_present_but_below_minimum` / `governance_route=exact_live_bucket_present_but_below_minimum` / `top_level_probe_api_patch_fields=present`
- 下一步：Keep the same recommended_patch summary across /api/status, /lab, hb_predict_probe.py, live_decision_quality_drilldown.py, and docs; do not promote it from reference-only until current-live exact support reaches the minimum rows.
- 驗證：`pytest tests/test_hb_predict_probe.py tests/test_server_startup.py tests/test_frontend_decision_contract.py -q`；`curl /api/status` 應回傳 `recommended_patch_support_route=exact_bucket_present_but_below_minimum` 與 `recommended_patch_gap_to_minimum=46`。

### P1. venue readiness is still unverified
- 目前真相：`binance=config enabled + public-only + metadata OK` / `okx=config disabled + public-only + metadata OK` / `missing_runtime_proof=live exchange credential, order ack lifecycle, fill lifecycle`
- 下一步：Keep per-venue blockers explicitly visible on Dashboard, /lab, and /execution/status until credentials, order ack lifecycle, and fill lifecycle each have runtime-backed proof.
- 驗證：
  - browser /execution
  - browser /execution/status
  - browser /lab
  - data/execution_metadata_smoke.json

### P1. fin_netflow remains source_auth_blocked because COINGLASS_API_KEY is missing
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3617` / `archive_window_coverage_pct=0.0`
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

### P1. q15 exact support regressed under minimum while breaker is clear (4/50)
- 目前真相：`bucket=CAUTION|structure_quality_caution|q15` / `support=4/50` / `gap=46` / `support_route_verdict=exact_bucket_present_but_below_minimum` / `governance_route=exact_live_bucket_present_but_below_minimum` / `breaker_context=breaker_clear`
- 下一步：Treat this as support regression, not ordinary stagnation: keep support_route_verdict/support_progress/minimum_support_rows/gap_to_minimum plus the last-supported reference visible in probe/API/UI/docs, verify why the current bucket fell back under minimum, and keep breaker context explicit.

---

## Current Priority
1. **維持 current-live exact-support blocker truth，同時保留 q15 current-live bucket support rows 可 machine-read**
2. **持續沿 recent canonical pathological slice 追根因，不要 generic 化 blocker**
3. **守住 q15 current-live bucket support / reference-only patch、leaderboard dual-role governance、venue/source blockers 可見性**
4. **讓 heartbeat 自動 overwrite sync current-state docs，不再把 docs drift 留給人工補寫**
