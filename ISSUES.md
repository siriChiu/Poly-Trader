# ISSUES.md — Current State Only

_最後更新：2026-04-21 10:59:14 CST_

只保留目前有效問題；由 heartbeat runner overwrite sync，避免 current-state markdown 落後 issues.json / live artifacts。

---

## 當前主線事實
- **最新 fast heartbeat #fast 已完成 collect + diagnostics refresh**
  - `Raw=31350 / Features=22768 / Labels=63182`
  - `simulated_pyramid_win=57.22%`
- **canonical current-live blocker 以 latest runtime truth 為主**
  - `deployment_blocker=exact_live_lane_toxic_sub_bucket_current_bucket` / `streak=None` / `recent_window_wins=None/None` / `additional_recent_window_wins_needed=—`
  - `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=88/50` / `gap=0` / `support_route_verdict=exact_bucket_supported`
- **recent canonical window 仍是 distribution pathology**
  - `window=500` / `win_rate=18.0%` / `dominant_regime=bull(78.6%)` / `avg_quality=-0.1048` / `avg_pnl=-0.0040` / `alerts=label_imbalance,regime_shift`
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- **source / venue blockers 仍開啟**
  - `blocked_sparse_features=8` / `{'archive_required': 3, 'snapshot_only': 4, 'short_window_public_api': 1}`
  - fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=2820` / `archive_window_coverage_pct=0.0`
  - venue：`live exchange credential / order ack lifecycle / fill lifecycle` 尚未有 runtime-backed proof
- **heartbeat current-state docs overwrite sync 已自動化**
  - `scripts/hb_parallel_runner.py` 現在會在 `auto_propose_fixes.py` 後自動覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 目的：避免 markdown docs 落後 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json`，讓 cron 心跳真正完成 docs overwrite 閉環

---

## Open Issues

### P0. current-live deployment blocker is exact_live_lane_toxic_sub_bucket_current_bucket
- 目前真相：`deployment_blocker=exact_live_lane_toxic_sub_bucket_current_bucket` / `bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=88/50` / `gap=0` / `runtime_closure_state=deployment_guardrail_blocks_trade`
- same-bucket truth：`support_route_verdict=exact_bucket_supported` / `support_governance_route=exact_live_bucket_supported` / `recommended_patch=None` / `recommended_patch_status=None` / `reference_scope=—`
- 下一步：把 current-live blocker 真相維持在 API / UI / docs；不要讓舊 breaker / support 敘事覆蓋最新 runtime truth。

### P0. recent canonical window 500 rows = distribution_pathology
- 目前真相：`window=500` / `win_rate=18.0%` / `dominant_regime=bull(78.6%)` / `avg_quality=-0.1048` / `avg_pnl=-0.0040`
- 病態切片：`alerts=label_imbalance,regime_shift` / `tail_streak=84` / `low_variance=8` / `low_distinct=10` / `null_heavy=10`
- 下一步：直接對 recent canonical rows 做 feature variance / distinct-count / target-path drill-down；維持 decision-quality guardrails，並檢查 calibration scope 是否仍被病態 slice 稀釋。 recent_window=500, alerts=['label_imbalance', 'regime_shift'], win_rate=0.1800, delta_vs_full=-0.4456, dominant_regime=bull(78.60%), interpretation=distribution_pathology, avg_pnl=-0.0040, avg_quality=-0.1048, avg_dd_penalty=0.3004, spot_long_win_rate=0.0780, feature_diag=variance:8/56, frozen:0, compressed:8, expected_static:2, overlay_only:1, unexpected_frozen:0, distinct:10, null_heavy:10, tail_streak=84x1 since 2026-04-19 10:13:18.192660 -> 2026-04-20 03:33:44.459733, adverse_streak=191x0 since 2026-04-18 14:33:06.990329 -> 2026-04-19 01:10:17.732530, prev_win_rate=0.666, delta_vs_prev=-0.486, prev_quality=0.2787, quality_delta_vs_prev=-0.3835, prev_pnl=0.0042, pnl_delta_vs_prev=-0.0082, top_shift_examples=feat_eye(0.7644→-2.0482,Δσ=0.7324)/feat_local_top_score(0.4182→0.2642,Δσ=0.6855)/feat_4h_vol_ratio(0.711→0.3391,Δσ=0.6672), new_compressed=feat_vwap_dev, compressed_examples=feat_body(0.0001/500)/feat_ear(0.0076/498)/feat_vix(0.0097/33), expected_static_examples=feat_dxy[weekend_macro_market_closed]/feat_vix[weekend_macro_market_closed], overlay_only_examples=feat_scales_ssr[research_sparse_source], distinct_examples=feat_4h_dist_swing_high(0/0)/feat_chorus(0/0)/feat_fin_netflow(0/0), null_examples=feat_4h_dist_swing_high(0.0)/feat_chorus(0.0)/feat_fin_netflow(0.0), recent_examples=2026-04-20 03:29:42.222213:1:chop:0.6795/2026-04-20 03:31:01.545462:1:chop:0.6731/2026-04-20 03:33:44.459733:1:chop:0.6866, adverse_examples=2026-04-19 00:40:09.929353:0:bull:-0.2753/2026-04-19 01:01:04.227452:0:bull:-0.3173/2026-04-19 01:10:17.732530:0:bull:-0.2383
- 驗證：
  - python scripts/recent_drift_report.py
  - python scripts/hb_predict_probe.py

### P1. venue readiness is still unverified
- 目前真相：`binance=config enabled + public-only + metadata OK` / `okx=config disabled + public-only + metadata OK` / `missing_runtime_proof=live exchange credential, order ack lifecycle, fill lifecycle`
- 下一步：Keep per-venue blockers explicitly visible on Dashboard, /lab, and /execution/status until credentials, order ack lifecycle, and fill lifecycle each have runtime-backed proof.
- 驗證：
  - browser /execution
  - browser /execution/status
  - browser /lab
  - data/execution_metadata_smoke.json

### P1. fin_netflow remains source_auth_blocked because COINGLASS_API_KEY is missing
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=2820` / `archive_window_coverage_pct=0.0`
- 下一步：Configure COINGLASS_API_KEY, then keep heartbeat collection running until successful ETF-flow snapshots replace auth_missing rows and coverage starts to move.
- 驗證：
  - data/execution_metadata_smoke.json
  - /api/features/coverage

### P1. leaderboard comparable rows are back; keep the recent-window contract stable and cron-safe
- 目前真相：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- 下一步：Keep /api/models/leaderboard and Strategy Lab aligned on latest bounded walk-forward plus the recent-two-year backtest policy; do not regress to placeholder-only or ambiguous backtest windows.
- 驗證：
  - browser /lab
  - curl http://127.0.0.1:<active-backend>/api/models/leaderboard
  - pytest tests/test_model_leaderboard.py tests/test_strategy_lab.py tests/test_frontend_decision_contract.py -q

---

## Current Priority
1. **維持 current-live blocker truth（exact_live_lane_toxic_sub_bucket_current_bucket），同時保留 q15 current-live bucket support rows 可 machine-read**
2. **持續沿 recent canonical pathological slice 追根因，不要 generic 化 blocker**
3. **守住 q15 current-live bucket support / reference-only patch、leaderboard dual-role governance、venue/source blockers 可見性**
4. **讓 heartbeat 自動 overwrite sync current-state docs，不再把 docs drift 留給人工補寫**
