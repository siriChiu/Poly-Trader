# ISSUES.md — Current State Only

_最後更新：2026-04-24 07:57:07 CST_

只保留目前有效問題；由 heartbeat runner overwrite sync，避免 current-state markdown 落後 issues.json / live artifacts。

---

## 當前主線事實
- **最新 fast heartbeat #20260424k 已完成 collect + diagnostics refresh**
  - `Raw=32124 / Features=23542 / Labels=64594`
  - 歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`
  - `simulated_pyramid_win=56.95%`
- **canonical current-live blocker 仍是 breaker-first truth**
  - `deployment_blocker=circuit_breaker_active` / `streak=25` / `recent_window_wins=12/50` / `additional_recent_window_wins_needed=3`
  - `current_live_structure_bucket=BLOCK|bull_high_bias200_overheat_block|q35` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_unsupported_block`
- **recent canonical diagnostics 已刷新**
  - `latest_window=250` / `win_rate=40.8%` / `dominant_regime=bull(99.2%)` / `avg_quality=+0.0057` / `avg_pnl=-0.0015` / `alerts=regime_concentration,regime_shift`
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- **source / venue blockers 仍開啟**
  - `blocked_sparse_features=8` / `{'archive_required': 3, 'snapshot_only': 4, 'short_window_public_api': 1}`
  - fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3592` / `archive_window_coverage_pct=0.0`
  - venue：`live exchange credential / order ack lifecycle / fill lifecycle` 尚未有 runtime-backed proof
- **heartbeat current-state docs overwrite sync 已自動化**
  - `scripts/hb_parallel_runner.py` 現在會在 `auto_propose_fixes.py` 後自動覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 目的：避免 markdown docs 落後 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json`，讓 cron 心跳真正完成 docs overwrite 閉環

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
- 目前真相：`deployment_blocker=circuit_breaker_active` / `streak=25` / `recent 50 wins=12/50` / `additional_recent_window_wins_needed=3`
- same-bucket truth：`bucket=BLOCK|bull_high_bias200_overheat_block|q35` / `support=0/50` / `support_route_verdict=exact_bucket_unsupported_block` / `support_governance_route=exact_live_bucket_proxy_available`
- 下一步：先把 current-live blocker 語義切回 circuit breaker release math；在 breaker 未解除前，不要把 q15/q35 support 或 floor-gap 當成本輪主 blocker。 recent 50 需至少 15 勝，當前 12 勝，還差 3 勝；同時 streak 必須 < 50。

### P0. recent canonical window 250 rows = regime_concentration
- 目前真相：`window=250` / `win_rate=40.8%` / `dominant_regime=bull(99.2%)` / `avg_quality=+0.0057` / `avg_pnl=-0.0015` / `alerts=regime_concentration,regime_shift`
- 病態切片：`alerts=regime_concentration,regime_shift` / `tail_streak=—` / `top_shift=feat_4h_vol_ratio,feat_4h_dist_bb_lower,feat_4h_macd_hist` / `new_compressed=feat_vwap_dev`
- 下一步：直接對 recent canonical rows 做 feature variance / distinct-count / target-path drill-down；維持 decision-quality guardrails，並檢查 calibration scope 是否仍被病態 slice 稀釋。 recent_window=250, alerts=['regime_concentration', 'regime_shift'], win_rate=0.4080, delta_vs_full=-0.2163, dominant_regime=bull(99.20%), interpretation=regime_concentration, avg_pnl=-0.0015, avg_quality=0.0057, avg_dd_penalty=0.3581, spot_long_win_rate=0.0000, feature_diag=variance:19/56, frozen:1, compressed:18, expected_static:1, overlay_only:3, unexpected_frozen:1, distinct:13, null_heavy:10, tail_streak=25x0 since 2026-04-23 00:24:20.626551 -> 2026-04-23 00:54:54.276671, adverse_streak=42x0 since 2026-04-22 19:13:12.457788 -> 2026-04-22 20:01:51.719779, prev_win_rate=0.696, delta_vs_prev=-0.288, prev_quality=0.361, quality_delta_vs_prev=-0.3553, prev_pnl=0.0106, pnl_delta_vs_prev=-0.0121, top_shift_examples=feat_4h_vol_ratio(1.0912→2.0421,Δσ=1.548)/feat_4h_dist_bb_lower(4.1815→6.9204,Δσ=0.8601)/feat_4h_macd_hist(-29.9767→541.3238,Δσ=0.8551), new_frozen=feat_4h_macd_hist, new_compressed=feat_vwap_dev, frozen_examples=feat_4h_macd_hist(0.132/4), compressed_examples=feat_body(0.0/249)/feat_ear(0.0041/249)/feat_tongue(0.0067/249), expected_static_examples=feat_4h_ma_order[discrete_regime_feature], overlay_only_examples=feat_claw_intensity[research_sparse_source]/feat_fang_pcr[research_sparse_source]/feat_scales_ssr[research_sparse_source], unexpected_frozen_examples=feat_4h_macd_hist(0.132/4), distinct_examples=feat_4h_macd_hist(4/4412)/feat_4h_rsi14(4/4411)/feat_4h_vol_ratio(4/4411), null_examples=feat_4h_dist_swing_high(0.0)/feat_chorus(0.0)/feat_fin_netflow(0.0), recent_examples=2026-04-23 00:52:18.020918:0:bull:-0.1978/2026-04-23 00:53:33.457943:0:bull:-0.1988/2026-04-23 00:54:54.276671:0:bull:-0.1798, adverse_examples=2026-04-22 19:59:15.257953:0:bull:-0.2219/2026-04-22 20:00:35.598937:0:bull:-0.1852/2026-04-22 20:01:51.719779:0:bull:-0.1923
- 驗證：
  - python scripts/recent_drift_report.py
  - python scripts/hb_predict_probe.py

### P1. support-aware core_plus_macro_plus_all_4h patch must stay visible but reference-only outside current live scope
- 目前真相：`bucket=BLOCK|bull_high_bias200_overheat_block|q35` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_unsupported_block` / `governance_route=exact_live_bucket_proxy_available`
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
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3592` / `archive_window_coverage_pct=0.0`
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

---

## Current Priority
1. **維持 breaker-first truth，同時保留 current live bucket support rows 可 machine-read**
2. **持續沿 recent canonical pathological slice 追根因，不要 generic 化 blocker**
3. **守住 current live bucket support / reference-only patch、leaderboard dual-role governance、venue/source blockers 可見性**
4. **讓 heartbeat 自動 overwrite sync current-state docs，不再把 docs drift 留給人工補寫**
