# ISSUES.md — Current State Only

_最後更新：2026-04-24 11:42:38 CST_

只保留目前有效問題；由 heartbeat runner overwrite sync，避免 current-state markdown 落後 issues.json / live artifacts。

---

## 當前主線事實
- **最新 fast heartbeat #20260424u 已完成 collect + diagnostics refresh**
  - `Raw=32143 / Features=23561 / Labels=64813`
  - 歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`
  - `simulated_pyramid_win=57.01%`
- **canonical current-live blocker 已切到 current-live exact-support truth**
  - `deployment_blocker=unsupported_exact_live_structure_bucket` / `streak=None` / `recent_window_wins=None/None` / `additional_recent_window_wins_needed=—`
  - `current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_proxy_reference_only`
- **recent canonical diagnostics 已刷新**
  - `latest_window=100` / `win_rate=96.0%` / `dominant_regime=bull(100.0%)` / `avg_quality=+0.4247` / `avg_pnl=+0.0059` / `alerts=label_imbalance,regime_concentration,regime_shift`
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- **source / venue blockers 仍開啟**
  - `blocked_sparse_features=8` / `{'archive_required': 3, 'snapshot_only': 4, 'short_window_public_api': 1}`
  - fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3611` / `archive_window_coverage_pct=0.0`
  - venue：`live exchange credential / order ack lifecycle / fill lifecycle` 尚未有 runtime-backed proof
- **heartbeat current-state docs overwrite sync 已自動化**
  - `scripts/hb_parallel_runner.py` 現在會在 `auto_propose_fixes.py` 後自動覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 目的：避免 markdown docs 落後 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json`，讓 cron 心跳真正完成 docs overwrite 閉環
- **本輪 operator UX / Strategy Lab 穩定性 patch 已落地**
  - Dashboard / Bot 營運 / 執行狀態 / Strategy Lab / LivePathologySummaryCard 的 support gap 文案已改為 `缺口`，避免半英文 raw token 進入 operator surface
  - `useApi.ts` 針對 `/api/strategies/leaderboard` 與 `/api/models/leaderboard` 使用 20s request timeout，避免排行榜 current-state payload 偶發超過 8s 時讓 `/lab` 初始化假失敗

---

## Open Issues

### P0. current live bucket BLOCK|bull_q15_bias50_overextended_block|q15 exact support is missing and remains the deployment blocker (0/50)
- 目前真相：`deployment_blocker=unsupported_exact_live_structure_bucket` / `bucket=BLOCK|bull_q15_bias50_overextended_block|q15` / `support=0/50` / `gap=50` / `runtime_closure_state=patch_inactive_or_blocked`
- same-bucket truth：`support_route_verdict=exact_bucket_missing_proxy_reference_only` / `support_governance_route=exact_live_bucket_proxy_available` / `recommended_patch=core_plus_macro_plus_all_4h` / `recommended_patch_status=reference_only_non_current_live_scope` / `reference_scope=bull|CAUTION`
- 下一步：把 current-live blocker 語義切到 exact-support truth；在 current live bucket 補滿 minimum rows 前，不要把 proxy rows、reference patch、或 breaker 舊敘事誤當成已解除 blocker。

### P0. recent canonical window 100 rows = distribution_pathology
- 目前真相：`window=100` / `win_rate=96.0%` / `dominant_regime=bull(100.0%)` / `avg_quality=+0.4247` / `avg_pnl=+0.0059` / `alerts=label_imbalance,regime_concentration,regime_shift`
- 病態切片：`alerts=label_imbalance,regime_concentration,regime_shift` / `tail_streak=4x0` / `top_shift=feat_local_top_score,feat_local_bottom_score,feat_eye` / `new_compressed=feat_nw_width`
- 下一步：直接對 recent canonical rows 做 feature variance / distinct-count / target-path drill-down；維持 decision-quality guardrails，並檢查 calibration scope 是否仍被病態 slice 稀釋。 recent_window=100, alerts=['label_imbalance', 'regime_concentration', 'regime_shift'], win_rate=0.9600, delta_vs_full=+0.3350, dominant_regime=bull(100.00%), interpretation=distribution_pathology, avg_pnl=+0.0059, avg_quality=0.4247, avg_dd_penalty=0.2020, spot_long_win_rate=0.0000, feature_diag=variance:32/56, frozen:5, compressed:27, expected_static:4, overlay_only:5, unexpected_frozen:2, distinct:16, null_heavy:10, tail_streak=4x0 since 2026-04-23 04:19:10.717188 -> 2026-04-23 04:34:03.341889, adverse_streak=4x0 since 2026-04-23 04:19:10.717188 -> 2026-04-23 04:34:03.341889, prev_win_rate=0.37, delta_vs_prev=0.59, prev_quality=0.0142, quality_delta_vs_prev=0.4105, prev_pnl=-0.0, pnl_delta_vs_prev=0.0059, top_shift_examples=feat_local_top_score(0.3687→0.1977,Δσ=0.7594)/feat_local_bottom_score(0.3086→0.4692,Δσ=0.7041)/feat_eye(-0.2333→-1.8432,Δσ=0.4171), new_compressed=feat_nw_width, frozen_examples=feat_4h_ma_order(0.0/1)/feat_nest_pred(0.0/1)/feat_vix(0.0/1), compressed_examples=feat_body(0.0/100)/feat_scales_ssr(0.0016/79)/feat_ear(0.0034/100), expected_static_examples=feat_4h_ma_order[discrete_regime_feature]/feat_dxy[weekday_macro_market_closed]/feat_nq_return_24h[weekday_macro_market_closed], overlay_only_examples=feat_claw[research_sparse_source]/feat_claw_intensity[research_sparse_source]/feat_fang_pcr[research_sparse_source], unexpected_frozen_examples=feat_4h_macd_hist(0.0007/2)/feat_4h_rsi14(0.109/2), distinct_examples=feat_4h_macd_hist(2/4413)/feat_4h_rsi14(2/4412)/feat_4h_vol_ratio(2/4412), null_examples=feat_4h_dist_swing_high(0.0)/feat_chorus(0.0)/feat_fin_netflow(0.0), recent_examples=2026-04-23 04:20:31.656118:0:bull:-0.117/2026-04-23 04:29:59.418541:0:bull:-0.0858/2026-04-23 04:34:03.341889:0:bull:-0.1209, adverse_examples=2026-04-23 04:20:31.656118:0:bull:-0.117/2026-04-23 04:29:59.418541:0:bull:-0.0858/2026-04-23 04:34:03.341889:0:bull:-0.1209
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
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3611` / `archive_window_coverage_pct=0.0`
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
1. **維持 current-live exact-support blocker truth，同時保留 q15 current-live bucket support rows 可 machine-read**
2. **持續沿 recent canonical pathological slice 追根因，不要 generic 化 blocker**
3. **守住 q15 current-live bucket support / reference-only patch、leaderboard dual-role governance、venue/source blockers 可見性**
4. **讓 heartbeat 自動 overwrite sync current-state docs，不再把 docs drift 留給人工補寫**
