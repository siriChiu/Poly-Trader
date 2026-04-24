# ISSUES.md — Current State Only

_最後更新：2026-04-24 08:47:18 CST_

只保留目前有效問題；由 heartbeat runner overwrite sync，避免 current-state markdown 落後 issues.json / live artifacts。

---

## 當前主線事實
- **最新 fast heartbeat #fast 已完成 collect + diagnostics refresh**
  - `Raw=32130 / Features=23548 / Labels=64648`
  - 歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`
  - `simulated_pyramid_win=56.96%`
- **canonical current-live blocker 已切到 current-live exact-support truth**
  - `deployment_blocker=unsupported_exact_live_structure_bucket` / `streak=None` / `recent_window_wins=None/None` / `additional_recent_window_wins_needed=—`
  - `current_live_structure_bucket=BLOCK|bull_high_bias200_overheat_block|q35` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_unsupported_block`
- **recent canonical diagnostics 已刷新**
  - `latest_window=100` / `win_rate=44.0%` / `dominant_regime=bull(99.0%)` / `avg_quality=+0.0550` / `avg_pnl=+0.0001` / `alerts=regime_concentration,regime_shift`
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- **source / venue blockers 仍開啟**
  - `blocked_sparse_features=8` / `{'archive_required': 3, 'snapshot_only': 4, 'short_window_public_api': 1}`
  - fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3598` / `archive_window_coverage_pct=0.0`
  - venue：`live exchange credential / order ack lifecycle / fill lifecycle` 尚未有 runtime-backed proof
- **heartbeat current-state docs overwrite sync 已自動化**
  - `scripts/hb_parallel_runner.py` 現在會在 `auto_propose_fixes.py` 後自動覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 目的：避免 markdown docs 落後 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json`，讓 cron 心跳真正完成 docs overwrite 閉環
- **execution operator-facing copy 已完成本輪 productization 清理**
  - `pytest tests/test_execution_console_overview.py tests/test_frontend_decision_contract.py tests/test_execution_surface_contract.py -q` → `78 passed`
  - browser `/`、`/execution`、`/execution/status`、`/lab` DOM substring check：`blocker / bucket / patch / run / beta = 0`，並保留 `unsupported_exact_live_structure_bucket + 0/50 + venue blockers` 的 blocker-first truth

---

## Open Issues

### P0. current live bucket BLOCK|bull_high_bias200_overheat_block|q35 exact support is missing and remains the deployment blocker (0/50)
- 目前真相：`deployment_blocker=unsupported_exact_live_structure_bucket` / `bucket=BLOCK|bull_high_bias200_overheat_block|q35` / `support=0/50` / `gap=50` / `runtime_closure_state=patch_inactive_or_blocked`
- same-bucket truth：`support_route_verdict=exact_bucket_unsupported_block` / `support_governance_route=no_support_proxy` / `recommended_patch=core_plus_macro_plus_all_4h` / `recommended_patch_status=reference_only_non_current_live_scope` / `reference_scope=bull|CAUTION`
- 下一步：把 current-live blocker 語義切到 exact-support truth；在 current live bucket 補滿 minimum rows 前，不要把 proxy rows、reference patch、或 breaker 舊敘事誤當成已解除 blocker。

### P0. recent canonical window 100 rows = regime_concentration
- 目前真相：`window=100` / `win_rate=44.0%` / `dominant_regime=bull(99.0%)` / `avg_quality=+0.0550` / `avg_pnl=+0.0001` / `alerts=regime_concentration,regime_shift`
- 病態切片：`alerts=regime_concentration,regime_shift` / `tail_streak=—` / `top_shift=feat_4h_vol_ratio,feat_4h_rsi14,feat_4h_bias20` / `new_compressed=feat_atr_pct`
- 下一步：直接對 recent canonical rows 做 feature variance / distinct-count / target-path drill-down；維持 decision-quality guardrails，並檢查 calibration scope 是否仍被病態 slice 稀釋。 recent_window=100, alerts=['regime_concentration', 'regime_shift'], win_rate=0.4400, delta_vs_full=-0.1845, dominant_regime=bull(99.00%), interpretation=regime_concentration, avg_pnl=+0.0001, avg_quality=0.0550, avg_dd_penalty=0.3191, spot_long_win_rate=0.0000, feature_diag=variance:26/56, frozen:5, compressed:21, expected_static:3, overlay_only:5, unexpected_frozen:2, distinct:16, null_heavy:10, tail_streak=3x1 since 2026-04-23 01:43:40.165068 -> 2026-04-23 01:44:54.049840, adverse_streak=39x0 since 2026-04-23 00:24:20.626551 -> 2026-04-23 01:11:11.317375, prev_win_rate=0.57, delta_vs_prev=-0.13, prev_quality=0.0857, quality_delta_vs_prev=-0.0307, prev_pnl=-0.001, pnl_delta_vs_prev=0.0011, top_shift_examples=feat_4h_vol_ratio(2.6747→1.3607,Δσ=2.1409)/feat_4h_rsi14(66.0455→61.086,Δσ=0.414)/feat_4h_bias20(2.6853→1.9761,Δσ=0.3164), new_compressed=feat_atr_pct, frozen_examples=feat_4h_ma_order(0.0/1)/feat_nest_pred(0.0/1)/feat_vix(0.0/1), compressed_examples=feat_body(0.0/100)/feat_ear(0.0046/99)/feat_tongue(0.0076/100), expected_static_examples=feat_4h_ma_order[discrete_regime_feature]/feat_dxy[weekday_macro_market_closed]/feat_vix[weekday_macro_market_closed], overlay_only_examples=feat_claw[research_sparse_source]/feat_claw_intensity[research_sparse_source]/feat_fang_pcr[research_sparse_source], unexpected_frozen_examples=feat_4h_macd_hist(0.031/2)/feat_4h_rsi14(0.1221/2), distinct_examples=feat_4h_macd_hist(2/4412)/feat_4h_rsi14(2/4411)/feat_4h_vol_ratio(2/4411), null_examples=feat_4h_dist_swing_high(0.0)/feat_chorus(0.0)/feat_fin_netflow(0.0), recent_examples=2026-04-23 01:43:40.165068:1:bull:0.2978/2026-04-23 01:44:28.040425:1:bull:0.3071/2026-04-23 01:44:54.049840:1:bull:0.3097, adverse_examples=2026-04-23 01:08:40.001619:0:bull:-0.1709/2026-04-23 01:09:56.370518:0:bull:-0.1716/2026-04-23 01:11:11.317375:0:bull:-0.1617
- 驗證：
  - python scripts/recent_drift_report.py
  - python scripts/hb_predict_probe.py

### P1. support-aware core_plus_macro_plus_all_4h patch must stay visible but reference-only outside current live scope
- 目前真相：`bucket=BLOCK|bull_high_bias200_overheat_block|q35` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_unsupported_block` / `governance_route=no_support_proxy`
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
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3598` / `archive_window_coverage_pct=0.0`
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

### P1. q35 lane still needs formula review / base-stack redesign before deploy
- 目前真相：`bucket=BLOCK|bull_high_bias200_overheat_block|q35` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_unsupported_block` / `overall_verdict=bias50_formula_may_be_too_harsh` / `redesign_verdict=base_stack_redesign_discriminative_reweight_still_below_floor` / `remaining_gap_to_floor=0.205`
- q35 scaling audit 已指出目前不是單點 bias50 closure：`overall_verdict=bias50_formula_may_be_too_harsh` / `redesign_verdict=base_stack_redesign_discriminative_reweight_still_below_floor` / `remaining_gap_to_floor=0.205`
- 下一步：把 q35 scaling audit 的 overall_verdict / redesign verdict / gap-to-floor 同步到 docs/probe/issues；在 exact support 未就緒、且 redesign 仍無正 discrimination floor-cross 之前，禁止把 bias50 單點 uplift 或結構 uplift 當成 closure。 即使做 support-aware / discriminative base-stack redesign，current row 仍無法跨過 trade floor；下一輪必須升級為 bull q35 no-deploy governance blocker，禁止再把結構 uplift、單點 bias50 或 base-stack 權重微調當成主 closure。

---

## Current Priority
1. **維持 current-live exact-support blocker truth，同時保留 current live bucket support rows 可 machine-read**
2. **持續沿 recent canonical pathological slice 追根因，不要 generic 化 blocker**
3. **守住 current live bucket support / reference-only patch、leaderboard dual-role governance、venue/source blockers 可見性**
4. **讓 heartbeat 自動 overwrite sync current-state docs，不再把 docs drift 留給人工補寫**
