# ISSUES.md — Current State Only

_最後更新：2026-04-20 18:31:12 CST_

只保留目前有效問題；由 heartbeat runner overwrite sync，避免 current-state markdown 落後 issues.json / live artifacts。

---

## 當前主線事實
- **最新 fast heartbeat #fast 已完成 collect + diagnostics refresh**
  - `Raw=31252 / Features=22670 / Labels=63021`
  - `simulated_pyramid_win=57.16%`
- **canonical current-live blocker 仍是 breaker-first truth**
  - `deployment_blocker=circuit_breaker_active` / `streak=0` / `recent_window_wins=13/50` / `additional_recent_window_wins_needed=2`
  - `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q35` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`
- **recent canonical window 仍是 distribution pathology**
  - `window=500` / `win_rate=3.2%` / `dominant_regime=bull(91.0%)` / `avg_quality=-0.2295` / `avg_pnl=-0.0079` / `alerts=label_imbalance,regime_concentration,regime_shift`
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- **source / venue blockers 仍開啟**
  - `blocked_sparse_features=8` / `{'archive_required': 3, 'snapshot_only': 4, 'short_window_public_api': 1}`
  - fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=2723` / `archive_window_coverage_pct=0.0`
  - venue：`live exchange credential / order ack lifecycle / fill lifecycle` 尚未有 runtime-backed proof
- **`/api/predict/confidence` 已跟上 live probe overlay truth**
  - `server/routes/api.py:get_confidence_prediction()` 現在會在 q15 audit enrich 後再 overlay fresh `data/live_predict_probe.json`
  - 目的：讓 Dashboard / Strategy Lab / 其他 confidence consumers 與 `/api/status` 共用同一份 current-live bucket / breaker / support truth，不再回退到舊 q15 或 stale runtime blocker
- **heartbeat current-state docs overwrite sync 已自動化**
  - `scripts/hb_parallel_runner.py` 現在會在 `auto_propose_fixes.py` 後自動覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 目的：避免 markdown docs 落後 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json`，讓 cron 心跳真正完成 docs overwrite 閉環

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
- 目前真相：`deployment_blocker=circuit_breaker_active` / `streak=0` / `recent 50 wins=13/50` / `additional_recent_window_wins_needed=2`
- same-bucket truth：`bucket=CAUTION|base_caution_regime_or_bias|q35` / `support=0/50` / `support_route_verdict=exact_bucket_unsupported_block` / `support_governance_route=exact_live_lane_proxy_available`
- 下一步：先把 current-live blocker 語義切回 circuit breaker release math；在 breaker 未解除前，不要把 q15/q35 support 或 floor-gap 當成本輪主 blocker。 recent 50 需至少 15 勝，當前 13 勝，還差 2 勝；同時 streak 必須 < 50。
- 驗證：
  - browser /
  - browser /execution
  - browser /execution/status
  - browser /lab
  - python scripts/hb_predict_probe.py
  - python scripts/live_decision_quality_drilldown.py

### P0. recent canonical 250 rows remains a distribution pathology
- 目前真相：`window=500` / `win_rate=3.2%` / `dominant_regime=bull(91.0%)` / `avg_quality=-0.2295` / `avg_pnl=-0.0079`
- 病態切片：`alerts=label_imbalance,regime_concentration,regime_shift` / `tail_streak=10` / `low_variance=9` / `low_distinct=10` / `null_heavy=10`
- 下一步：直接對 recent canonical rows 做 feature variance / distinct-count / target-path drill-down；維持 decision-quality guardrails，並檢查 calibration scope 是否仍被病態 slice 稀釋。 recent_window=500, alerts=['label_imbalance', 'regime_concentration', 'regime_shift'], win_rate=0.0320, delta_vs_full=-0.5924, dominant_regime=bull(91.00%), interpretation=distribution_pathology, avg_pnl=-0.0079, avg_quality=-0.2295, avg_dd_penalty=0.3214, spot_long_win_rate=0.0000, feature_diag=variance:9/56, frozen:0, compressed:9, expected_static:3, overlay_only:1, unexpected_frozen:0, distinct:10, null_heavy:10, tail_streak=10x1 since 2026-04-19 10:13:18.192660 -> 2026-04-19 11:23:45.334219, adverse_streak=253x0 since 2026-04-17 14:07:40.269245 -> 2026-04-18 13:43:25.809469, prev_win_rate=0.814, delta_vs_prev=-0.782, prev_quality=0.385, quality_delta_vs_prev=-0.6145, prev_pnl=0.0068, pnl_delta_vs_prev=-0.0147, top_shift_examples=feat_eye(0.7758→-1.6522,Δσ=0.6339)/feat_vwap_dev(-0.2556→-0.1492,Δσ=0.4717)/feat_4h_bias200(6.2579→8.6687,Δσ=0.4403), new_compressed=feat_vwap_dev, compressed_examples=feat_body(0.0/500)/feat_ear(0.0062/498)/feat_tongue(0.0084/500), expected_static_examples=feat_dxy[weekend_macro_market_closed]/feat_nq_return_24h[weekend_macro_market_closed]/feat_vix[weekend_macro_market_closed], overlay_only_examples=feat_scales_ssr[research_sparse_source], distinct_examples=feat_4h_dist_swing_high(0/0)/feat_chorus(0/0)/feat_fin_netflow(0/0), null_examples=feat_4h_dist_swing_high(0.0)/feat_chorus(0.0)/feat_fin_netflow(0.0), recent_examples=2026-04-19 11:17:47.284264:1:chop:0.4169/2026-04-19 11:22:25.792774:1:chop:0.4558/2026-04-19 11:23:45.334219:1:chop:0.4807, adverse_examples=2026-04-18 13:00:00.000000:0:bull:-0.2342/2026-04-18 13:36:43.970223:0:bull:-0.2119/2026-04-18 13:43:25.809469:0:bull:-0.2137
- 驗證：
  - python scripts/recent_drift_report.py
  - python scripts/hb_predict_probe.py

### P1. support-aware core_plus_macro_plus_all_4h patch must stay visible but reference-only
- 目前真相：`bucket=CAUTION|base_caution_regime_or_bias|q35` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only` / `governance_route=exact_live_lane_proxy_available`
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
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=2723` / `archive_window_coverage_pct=0.0`
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
1. **維持 breaker-first truth，同時保留 current live bucket support rows 可 machine-read**
2. **持續沿 recent canonical pathological slice 追根因，不要 generic 化 blocker**
3. **守住 current live bucket support / reference-only patch、leaderboard dual-role governance、venue/source blockers 可見性**
4. **讓 heartbeat 自動 overwrite sync current-state docs，不再把 docs drift 留給人工補寫**
