# ISSUES.md — Current State Only

_最後更新：2026-04-21 12:26:52 CST_

只保留目前有效問題；由 heartbeat runner overwrite sync，避免 current-state markdown 落後 issues.json / live artifacts。

---

## 當前主線事實
- **最新 fast heartbeat #20260421-1224 已完成 collect + diagnostics refresh**
  - `Raw=31356 / Features=22774 / Labels=63208`
  - `simulated_pyramid_win=57.21%`
- **canonical current-live blocker 以 latest runtime truth 為主**
  - `deployment_blocker=exact_live_lane_toxic_sub_bucket_current_bucket` / `streak=None` / `recent_window_wins=None/None` / `additional_recent_window_wins_needed=—`
  - `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=97/50` / `gap=0` / `support_route_verdict=exact_bucket_supported`
- **recent canonical window 仍是 distribution pathology**
  - `window=500` / `win_rate=19.8%` / `dominant_regime=bull(76.8%)` / `avg_quality=-0.0868` / `avg_pnl=-0.0034` / `alerts=label_imbalance,regime_shift`
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- **source / venue blockers 仍開啟**
  - `blocked_sparse_features=8` / `{'archive_required': 3, 'snapshot_only': 4, 'short_window_public_api': 1}`
  - fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=2826` / `archive_window_coverage_pct=0.0`
  - venue：`live exchange credential / order ack lifecycle / fill lifecycle` 尚未有 runtime-backed proof
- **heartbeat current-state docs overwrite sync 已自動化**
  - `scripts/hb_parallel_runner.py` 現在會在 `auto_propose_fixes.py` 後自動覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 目的：避免 markdown docs 落後 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json`，讓 cron 心跳真正完成 docs overwrite 閉環
- **Execution operator surfaces 已補齊 support 對齊可見性**
  - `/execution` 與 `/execution/status` 現在同時顯示 `support=current bucket rows/minimum` 與 `runtime/calibration` 計數
  - 目的：避免 exact-support 對齊被單一 badge 藏起來，讓 operator 直接看見 runtime 與 calibration 是否一致

---

## Open Issues

### P0. current-live deployment blocker is exact_live_lane_toxic_sub_bucket_current_bucket
- 目前真相：`deployment_blocker=exact_live_lane_toxic_sub_bucket_current_bucket` / `bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=97/50` / `gap=0` / `runtime_closure_state=deployment_guardrail_blocks_trade`
- same-bucket truth：`support_route_verdict=exact_bucket_supported` / `support_governance_route=exact_live_bucket_supported` / `recommended_patch=None` / `recommended_patch_status=None` / `reference_scope=—`
- 下一步：把 current-live blocker 真相維持在 API / UI / docs；不要讓舊 breaker / support 敘事覆蓋最新 runtime truth。

### P0. recent canonical window 500 rows = distribution_pathology
- 目前真相：`window=500` / `win_rate=19.8%` / `dominant_regime=bull(76.8%)` / `avg_quality=-0.0868` / `avg_pnl=-0.0034`
- 病態切片：`alerts=label_imbalance,regime_shift` / `tail_streak=93` / `low_variance=8` / `low_distinct=10` / `null_heavy=10`
- 下一步：直接對 recent canonical rows 做 feature variance / distinct-count / target-path drill-down；維持 decision-quality guardrails，並檢查 calibration scope 是否仍被病態 slice 稀釋。 recent_window=500, alerts=['label_imbalance', 'regime_shift'], win_rate=0.1980, delta_vs_full=-0.4277, dominant_regime=bull(76.80%), interpretation=distribution_pathology, avg_pnl=-0.0034, avg_quality=-0.0868, avg_dd_penalty=0.2950, spot_long_win_rate=0.0960, feature_diag=variance:8/56, frozen:0, compressed:8, expected_static:2, overlay_only:1, unexpected_frozen:0, distinct:10, null_heavy:10, tail_streak=93x1 since 2026-04-19 10:13:18.192660 -> 2026-04-20 05:20:20.413713, adverse_streak=191x0 since 2026-04-18 14:33:06.990329 -> 2026-04-19 01:10:17.732530, prev_win_rate=0.648, delta_vs_prev=-0.45, prev_quality=0.2652, quality_delta_vs_prev=-0.352, prev_pnl=0.0038, pnl_delta_vs_prev=-0.0072, top_shift_examples=feat_4h_vol_ratio(0.7236→0.3276,Δσ=0.7105)/feat_eye(0.6685→-1.9964,Δσ=0.694)/feat_local_top_score(0.4137→0.268,Δσ=0.6487), new_compressed=feat_vwap_dev, compressed_examples=feat_body(0.0001/500)/feat_ear(0.0077/498)/feat_vix(0.0096/33), expected_static_examples=feat_dxy[weekend_macro_market_closed]/feat_vix[weekend_macro_market_closed], overlay_only_examples=feat_scales_ssr[research_sparse_source], distinct_examples=feat_4h_dist_swing_high(0/0)/feat_chorus(0/0)/feat_fin_netflow(0/0), null_examples=feat_4h_dist_swing_high(0.0)/feat_chorus(0.0)/feat_fin_netflow(0.0), recent_examples=2026-04-20 04:37:25.630966:1:chop:0.6919/2026-04-20 05:02:10.161496:1:chop:0.6878/2026-04-20 05:20:20.413713:1:chop:0.7076, adverse_examples=2026-04-19 00:40:09.929353:0:bull:-0.2753/2026-04-19 01:01:04.227452:0:bull:-0.3173/2026-04-19 01:10:17.732530:0:bull:-0.2383
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
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=2826` / `archive_window_coverage_pct=0.0`
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
