# ISSUES.md — Current State Only

_最後更新：2026-04-21 04:07:59 CST_

只保留目前有效問題；由 heartbeat runner overwrite sync，避免 current-state markdown 落後 issues.json / live artifacts。

---

## 當前主線事實
- **最新 fast heartbeat #fast 已完成 collect + diagnostics refresh**
  - `Raw=31298 / Features=22716 / Labels=63103`
  - `simulated_pyramid_win=57.23%`
- **canonical current-live blocker 已切到 current-live exact-support truth**
  - `deployment_blocker=under_minimum_exact_live_structure_bucket` / `streak=None` / `recent_window_wins=None/None` / `additional_recent_window_wins_needed=—`
  - `current_live_structure_bucket=CAUTION|structure_quality_caution|q35` / `support=12/50` / `gap=38` / `support_route_verdict=exact_bucket_present_but_below_minimum`
- **recent canonical window 仍是 distribution pathology**
  - `window=500` / `win_rate=11.2%` / `dominant_regime=bull(85.4%)` / `avg_quality=-0.1694` / `avg_pnl=-0.0061` / `alerts=label_imbalance,regime_shift`
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- **source / venue blockers 仍開啟**
  - `blocked_sparse_features=8` / `{'archive_required': 3, 'snapshot_only': 4, 'short_window_public_api': 1}`
  - fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=2768` / `archive_window_coverage_pct=0.0`
  - venue：`live exchange credential / order ack lifecycle / fill lifecycle` 尚未有 runtime-backed proof
- **heartbeat current-state docs overwrite sync 已自動化**
  - `scripts/hb_parallel_runner.py` 現在會在 `auto_propose_fixes.py` 後自動覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 目的：避免 markdown docs 落後 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json`，讓 cron 心跳真正完成 docs overwrite 閉環
- **Dashboard / Strategy Lab 的 compact live pathology 卡已補上 current bucket support 可視性**
  - 當 `exact live lane rows=0` 但 same-bucket support 已累積時，摘要卡現在會直接顯示 `exact lane rows 0 · current bucket 12/50`
  - 目的：避免 operator 在 summary surface 把「exact lane 無 rows」誤讀成「current bucket support 也是 0」，維持 `under_minimum_exact_live_structure_bucket` 的 blocker 真相

---

## Open Issues

### P0. current live bucket CAUTION|structure_quality_caution|q35 exact support remains under minimum and remains the deployment blocker (12/50)
- 目前真相：`deployment_blocker=under_minimum_exact_live_structure_bucket` / `bucket=CAUTION|structure_quality_caution|q35` / `support=12/50` / `gap=38` / `runtime_closure_state=patch_active_but_execution_blocked`
- same-bucket truth：`support_route_verdict=exact_bucket_present_but_below_minimum` / `support_governance_route=exact_live_bucket_present_but_below_minimum` / `recommended_patch=core_plus_macro_plus_all_4h` / `recommended_patch_status=reference_only_until_exact_support_ready` / `reference_scope=bull|CAUTION`
- 下一步：把 current-live blocker 語義切到 exact-support truth；在 current live bucket 補滿 minimum rows 前，不要把 proxy rows、reference patch、或 breaker 舊敘事誤當成已解除 blocker。
- 驗證：
  - browser /
  - browser /execution
  - browser /execution/status
  - browser /lab
  - python scripts/hb_predict_probe.py
  - python scripts/live_decision_quality_drilldown.py

### P0. recent canonical window 500 rows = distribution_pathology
- 目前真相：`window=500` / `win_rate=11.2%` / `dominant_regime=bull(85.4%)` / `avg_quality=-0.1694` / `avg_pnl=-0.0061`
- 病態切片：`alerts=label_imbalance,regime_shift` / `tail_streak=50` / `low_variance=9` / `low_distinct=10` / `null_heavy=10`
- 下一步：直接對 recent canonical rows 做 feature variance / distinct-count / target-path drill-down；維持 decision-quality guardrails，並檢查 calibration scope 是否仍被病態 slice 稀釋。 recent_window=500, alerts=['label_imbalance', 'regime_shift'], win_rate=0.1120, delta_vs_full=-0.5130, dominant_regime=bull(85.40%), interpretation=distribution_pathology, avg_pnl=-0.0061, avg_quality=-0.1694, avg_dd_penalty=0.3196, spot_long_win_rate=0.0100, feature_diag=variance:9/56, frozen:0, compressed:9, expected_static:3, overlay_only:1, unexpected_frozen:0, distinct:10, null_heavy:10, tail_streak=50x1 since 2026-04-19 10:13:18.192660 -> 2026-04-19 20:54:30.222392, adverse_streak=213x0 since 2026-04-17 15:30:13.526092 -> 2026-04-18 13:43:25.809469, prev_win_rate=0.734, delta_vs_prev=-0.622, prev_quality=0.3267, quality_delta_vs_prev=-0.4961, prev_pnl=0.0053, pnl_delta_vs_prev=-0.0114, top_shift_examples=feat_eye(1.0054→-1.9143,Δσ=0.7612)/feat_local_top_score(0.4195→0.2707,Δσ=0.6621)/feat_local_bottom_score(0.3015→0.438,Δσ=0.5974), new_compressed=feat_vwap_dev, compressed_examples=feat_body(0.0001/500)/feat_ear(0.0065/498)/feat_tongue(0.0099/500), expected_static_examples=feat_dxy[weekend_macro_market_closed]/feat_nq_return_24h[weekend_macro_market_closed]/feat_vix[weekend_macro_market_closed], overlay_only_examples=feat_scales_ssr[research_sparse_source], distinct_examples=feat_4h_dist_swing_high(0/0)/feat_chorus(0/0)/feat_fin_netflow(0/0), null_examples=feat_4h_dist_swing_high(0.0)/feat_chorus(0.0)/feat_fin_netflow(0.0), recent_examples=2026-04-19 20:19:01.725188:1:chop:0.6273/2026-04-19 20:20:52.206214:1:chop:0.6142/2026-04-19 20:54:30.222392:1:chop:0.6106, adverse_examples=2026-04-18 13:00:00.000000:0:bull:-0.2342/2026-04-18 13:36:43.970223:0:bull:-0.2119/2026-04-18 13:43:25.809469:0:bull:-0.2137
- 驗證：
  - python scripts/recent_drift_report.py
  - python scripts/hb_predict_probe.py

### P1. support-aware core_plus_macro_plus_all_4h patch must stay visible but reference-only
- 目前真相：`bucket=CAUTION|structure_quality_caution|q35` / `support=12/50` / `gap=38` / `support_route_verdict=exact_bucket_present_but_below_minimum` / `governance_route=exact_live_bucket_present_but_below_minimum`
- 下一步：Keep the same recommended_patch summary across /api/status, /lab, hb_predict_probe.py, live_decision_quality_drilldown.py, and docs; do not promote it from reference-only until current-live exact support reaches the minimum rows.

### P1. venue readiness is still unverified
- 目前真相：`binance=config enabled + public-only + metadata OK` / `okx=config disabled + public-only + metadata OK` / `missing_runtime_proof=live exchange credential, order ack lifecycle, fill lifecycle`
- 下一步：Keep per-venue blockers explicitly visible on Dashboard, /lab, and /execution/status until credentials, order ack lifecycle, and fill lifecycle each have runtime-backed proof.
- 驗證：
  - browser /execution
  - browser /execution/status
  - browser /lab
  - data/execution_metadata_smoke.json

### P1. fin_netflow remains source_auth_blocked because COINGLASS_API_KEY is missing
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=2768` / `archive_window_coverage_pct=0.0`
- 下一步：Configure COINGLASS_API_KEY, then keep heartbeat collection running until successful ETF-flow snapshots replace auth_missing rows and coverage starts to move.
- 驗證：
  - data/execution_metadata_smoke.json
  - /api/features/coverage

### P1. leaderboard comparable rows are back; keep the recent-window contract stable and cron-safe
- 目前真相：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- 下一步：Keep /api/models/leaderboard and Strategy Lab aligned on latest bounded walk-forward plus the recent-two-year backtest policy; do not regress to placeholder-only or ambiguous backtest windows.
- 驗證：
  - browser /lab
  - curl http://127.0.0.1:8000/api/models/leaderboard
  - pytest tests/test_model_leaderboard.py tests/test_strategy_lab.py tests/test_frontend_decision_contract.py -q

---

## Current Priority
1. **維持 current-live exact-support blocker truth，同時保留 current live bucket support rows 可 machine-read**
2. **持續沿 recent canonical pathological slice 追根因，不要 generic 化 blocker**
3. **守住 current live bucket support / reference-only patch、leaderboard dual-role governance、venue/source blockers 可見性**
4. **讓 heartbeat 自動 overwrite sync current-state docs，不再把 docs drift 留給人工補寫**
