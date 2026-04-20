# ISSUES.md — Current State Only

_最後更新：2026-04-20 13:56:02 CST_

只保留目前有效問題；由 heartbeat runner overwrite sync，避免 current-state markdown 落後 issues.json / live artifacts。

---

## 當前主線事實
- **最新 fast heartbeat #fast 已完成 collect + diagnostics refresh**
  - `Raw=31222 / Features=22640 / Labels=62956`
  - `simulated_pyramid_win=57.16%`
- **canonical current-live blocker 仍是 breaker-first truth**
  - `deployment_blocker=circuit_breaker_active` / `streak=18` / `recent_window_wins=3/50` / `additional_recent_window_wins_needed=12`
  - `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=14/50` / `gap=36` / `support_route_verdict=exact_bucket_present_but_below_minimum`
- **recent canonical window 仍是 distribution pathology**
  - `window=250` / `win_rate=1.6%` / `dominant_regime=bull(94.4%)` / `avg_quality=-0.2106` / `avg_pnl=-0.0066` / `alerts=label_imbalance,regime_concentration,regime_shift`
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- **source / venue blockers 仍開啟**
  - `blocked_sparse_features=8` / `{'archive_required': 3, 'snapshot_only': 4, 'short_window_public_api': 1}`
  - fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=2693` / `archive_window_coverage_pct=0.0`
  - venue：`live exchange credential / order ack lifecycle / fill lifecycle` 尚未有 runtime-backed proof
- **heartbeat current-state docs overwrite sync 已自動化**
  - `scripts/hb_parallel_runner.py` 現在會在 `auto_propose_fixes.py` 後自動覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 目的：避免 markdown docs 落後 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json`，讓 cron 心跳真正完成 docs overwrite 閉環
- **Strategy Lab 初始空排行榜 recovery 已補強**
  - `web/src/pages/StrategyLab.tsx` 現在會在 `/api/strategies/leaderboard` 首輪 timeout/空 payload 時退回 same-origin fetch，且在策略列表為空時自動重試與回填第一個策略
  - browser `/lab` 已驗證：`全部 sleeves · 6`，workspace 會自動載入 `Auto Leaderboard · 重掃 xgboost Hybrid #01`，不再卡在 `My Strategy / 0 策略`

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
- 目前真相：`deployment_blocker=circuit_breaker_active` / `streak=18` / `recent 50 wins=3/50` / `additional_recent_window_wins_needed=12`
- same-bucket truth：`bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=0/50` / `support_route_verdict=exact_bucket_present_but_below_minimum` / `support_governance_route=exact_live_lane_proxy_available`
- 下一步：先把 current-live blocker 語義切回 circuit breaker release math；在 breaker 未解除前，不要把 q15/q35 support 或 floor-gap 當成本輪主 blocker。 recent 50 需至少 15 勝，當前 3 勝，還差 12 勝；同時 streak 必須 < 50。
- 驗證：
  - browser /
  - browser /execution
  - browser /execution/status
  - browser /lab
  - python scripts/hb_predict_probe.py
  - python scripts/live_decision_quality_drilldown.py

### P0. recent canonical 250 rows remains a distribution pathology
- 目前真相：`window=250` / `win_rate=1.6%` / `dominant_regime=bull(94.4%)` / `avg_quality=-0.2106` / `avg_pnl=-0.0066`
- 病態切片：`alerts=label_imbalance,regime_concentration,regime_shift` / `tail_streak=18` / `low_variance=12` / `low_distinct=13` / `null_heavy=10`
- 下一步：直接對 recent canonical rows 做 feature variance / distinct-count / target-path drill-down；維持 decision-quality guardrails，並檢查 calibration scope 是否仍被病態 slice 稀釋。 recent_window=250, alerts=['label_imbalance', 'regime_concentration', 'regime_shift'], win_rate=0.0160, delta_vs_full=-0.6087, dominant_regime=bull(94.40%), interpretation=distribution_pathology, avg_pnl=-0.0066, avg_quality=-0.2106, avg_dd_penalty=0.2666, spot_long_win_rate=0.0000, feature_diag=variance:12/56, frozen:3, compressed:9, expected_static:4, overlay_only:1, unexpected_frozen:0, distinct:13, null_heavy:10, tail_streak=18x0 since 2026-04-19 02:56:07.174860 -> 2026-04-19 06:47:15.452349, adverse_streak=191x0 since 2026-04-18 14:33:06.990329 -> 2026-04-19 01:10:17.732530, prev_win_rate=0.04, delta_vs_prev=-0.024, prev_quality=-0.2426, quality_delta_vs_prev=0.032, prev_pnl=-0.0093, pnl_delta_vs_prev=0.0027, top_shift_examples=feat_4h_bb_pct_b(1.025→0.2712,Δσ=2.342)/feat_4h_bias20(3.1729→0.4037,Δσ=1.6746)/feat_4h_rsi14(70.1213→55.5347,Δσ=1.4538), new_compressed=feat_atr_pct, frozen_examples=feat_vix(0.0/1)/feat_dxy(0.0075/3)/feat_nq_return_1h(0.0445/3), compressed_examples=feat_body(0.0/250)/feat_ear(0.0058/248)/feat_tongue(0.0087/250), expected_static_examples=feat_dxy[weekend_macro_market_closed]/feat_nq_return_1h[weekend_macro_market_closed]/feat_nq_return_24h[weekend_macro_market_closed], overlay_only_examples=feat_scales_ssr[research_sparse_source], distinct_examples=feat_vix(1/1435)/feat_dxy(3/3304)/feat_nq_return_1h(3/2864), null_examples=feat_4h_dist_swing_high(0.0)/feat_chorus(0.0)/feat_fin_netflow(0.0), recent_examples=2026-04-19 05:47:02.289562:0:chop:-0.1687/2026-04-19 06:28:27.509197:0:chop:-0.1935/2026-04-19 06:47:15.452349:0:chop:-0.1885, adverse_examples=2026-04-19 00:40:09.929353:0:bull:-0.2753/2026-04-19 01:01:04.227452:0:bull:-0.3173/2026-04-19 01:10:17.732530:0:bull:-0.2383
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
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=2693` / `archive_window_coverage_pct=0.0`
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

### P1. q15 exact support remains under minimum under breaker (0/50)
- 目前真相：`bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=14/50` / `gap=36` / `support_route_verdict=exact_bucket_present_but_below_minimum` / `governance_route=exact_live_lane_proxy_available`
- 下一步：Keep support_route_verdict/support_progress/minimum_support_rows/gap_to_minimum visible in probe/API/UI/docs even when circuit_breaker_active is the primary blocker.

---

## Current Priority
1. **維持 breaker-first truth，同時保留 q15 current-live bucket support rows 可 machine-read**
2. **持續沿 recent canonical pathological slice 追根因，不要 generic 化 blocker**
3. **守住 q15 current-live bucket support / reference-only patch、leaderboard dual-role governance、venue/source blockers 可見性**
4. **讓 heartbeat 自動 overwrite sync current-state docs，不再把 docs drift 留給人工補寫**
