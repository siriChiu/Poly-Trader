# ISSUES.md — Current State Only

_最後更新：2026-04-23 12:00:28 CST_

只保留目前有效問題；由 heartbeat runner overwrite sync，避免 current-state markdown 落後 issues.json / live artifacts。

---

## 當前主線事實
- **最新 fast heartbeat #20260423g 已完成 collect + diagnostics refresh**
  - `Raw=31976 / Features=23394 / Labels=63946`
  - 歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`
  - `simulated_pyramid_win=57.11%`
- **canonical current-live blocker 以 latest runtime truth 為主**
  - `deployment_blocker=decision_quality_below_trade_floor` / `streak=None` / `recent_window_wins=None/None` / `additional_recent_window_wins_needed=—`
  - `current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15` / `support=206/50` / `gap=0` / `support_route_verdict=exact_bucket_supported`
- **recent canonical diagnostics 已刷新**
  - `latest_window=100` / `win_rate=100.0%` / `dominant_regime=bull(91.0%)` / `avg_quality=+0.6889` / `avg_pnl=+0.0234` / `alerts=constant_target,regime_concentration,regime_shift`
  - `blocking_window=1000` / `win_rate=39.4%` / `dominant_regime=bull(81.3%)` / `avg_quality=+0.0814` / `avg_pnl=+0.0009` / `alerts=regime_shift`
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=6` / `top_model=random_forest` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- **Strategy Lab 工作區初始化安全性已補強**
  - 預設工作區名稱若撞到既有 `My Strategy`，會自動改成唯一名稱（例如 `My Strategy #2`），避免手動策略誤覆蓋
  - cached `selectedStrategy` 會在 leaderboard fallback 前先回填到左側表單與工作區，避免重整後被第一名策略蓋掉 operator context
- **source / venue blockers 仍開啟**
  - `blocked_sparse_features=8` / `{'archive_required': 3, 'snapshot_only': 4, 'short_window_public_api': 1}`
  - fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3446` / `archive_window_coverage_pct=0.0`
  - venue：`live exchange credential / order ack lifecycle / fill lifecycle` 尚未有 runtime-backed proof
- **heartbeat current-state docs overwrite sync 已自動化**
  - `scripts/hb_parallel_runner.py` 現在會在 `auto_propose_fixes.py` 後自動覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 目的：避免 markdown docs 落後 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json`，讓 cron 心跳真正完成 docs overwrite 閉環

---

## Open Issues

### P0. current-live deployment blocker is decision_quality_below_trade_floor
- 目前真相：`deployment_blocker=decision_quality_below_trade_floor` / `bucket=BLOCK|bull_q15_bias50_overextended_block|q15` / `support=206/50` / `gap=0` / `runtime_closure_state=support_closed_but_trade_floor_blocked`
- same-bucket truth：`support_route_verdict=exact_bucket_supported` / `support_governance_route=exact_live_bucket_supported` / `recommended_patch=core_plus_macro_plus_all_4h` / `recommended_patch_status=reference_only_non_current_live_scope` / `reference_scope=bull|CAUTION`
- 下一步：把 current-live blocker 真相維持在 API / UI / docs；不要讓舊 breaker / support 敘事覆蓋最新 runtime truth。

### P0. recent canonical window 1000 rows = regime_concentration
- 目前真相：`window=1000` / `win_rate=39.4%` / `dominant_regime=bull(81.3%)` / `avg_quality=+0.0814` / `avg_pnl=+0.0009` / `alerts=regime_shift`
- latest diagnostics：`latest_window=100` / `win_rate=100.0%` / `dominant_regime=bull(91.0%)` / `avg_quality=+0.6889` / `avg_pnl=+0.0234` / `alerts=constant_target,regime_concentration,regime_shift`
- 病態切片：`alerts=regime_shift` / `tail_streak=64x1` / `top_shift=feat_4h_bias200,feat_vwap_dev,feat_dxy` / `new_compressed=feat_vix`
- 下一步：直接對 recent canonical rows 做 feature variance / distinct-count / target-path drill-down；維持 decision-quality guardrails，並檢查 calibration scope 是否仍被病態 slice 稀釋。 recent_window=1000, alerts=['regime_shift'], win_rate=0.3940, delta_vs_full=-0.2326, dominant_regime=bull(81.30%), interpretation=regime_concentration, avg_pnl=+0.0009, avg_quality=0.0814, avg_dd_penalty=0.2414, spot_long_win_rate=0.1990, feature_diag=variance:7/56, frozen:0, compressed:7, expected_static:0, overlay_only:1, unexpected_frozen:0, distinct:10, null_heavy:10, tail_streak=64x1 since 2026-04-21 00:05:39.160858 -> 2026-04-21 10:59:35.681689, adverse_streak=273x0 since 2026-04-17 13:41:12.414408 -> 2026-04-18 13:43:25.809469, prev_win_rate=0.934, delta_vs_prev=-0.54, prev_quality=0.5441, quality_delta_vs_prev=-0.4627, prev_pnl=0.0146, pnl_delta_vs_prev=-0.0137, top_shift_examples=feat_4h_bias200(4.2831→7.7176,Δσ=0.6287)/feat_vwap_dev(-0.3083→-0.1728,Δσ=0.6031)/feat_dxy(98.4696→98.1349,Δσ=0.3232), new_compressed=feat_vix, compressed_examples=feat_body(0.0001/998)/feat_ear(0.0104/996)/feat_tongue(0.0145/997), overlay_only_examples=feat_scales_ssr[research_sparse_source], distinct_examples=feat_4h_dist_swing_high(0/0)/feat_chorus(0/0)/feat_fin_netflow(0/0), null_examples=feat_4h_dist_swing_high(0.0)/feat_chorus(0.0)/feat_fin_netflow(0.0), recent_examples=2026-04-21 10:30:36.408135:1:bull:0.6038/2026-04-21 10:42:49.680698:1:bull:0.6106/2026-04-21 10:59:35.681689:1:bull:0.5758, adverse_examples=2026-04-18 13:00:00.000000:0:bull:-0.2342/2026-04-18 13:36:43.970223:0:bull:-0.2119/2026-04-18 13:43:25.809469:0:bull:-0.2137
- 驗證：
  - python scripts/recent_drift_report.py
  - python scripts/hb_predict_probe.py

### P1. support-aware core_plus_macro_plus_all_4h patch must stay visible but reference-only outside current live scope
- 目前真相：`bucket=BLOCK|bull_q15_bias50_overextended_block|q15` / `support=206/50` / `gap=0` / `support_route_verdict=exact_bucket_supported` / `governance_route=exact_live_bucket_supported`
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
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3446` / `archive_window_coverage_pct=0.0`
- 下一步：Configure COINGLASS_API_KEY, then keep heartbeat collection running until successful ETF-flow snapshots replace auth_missing rows and coverage starts to move.
- 驗證：
  - data/execution_metadata_smoke.json
  - /api/features/coverage

### P1. leaderboard comparable rows are back; keep the recent-window contract stable and cron-safe
- 目前真相：`leaderboard_count=6` / `top_model=random_forest` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- Strategy Lab workspace safety：duplicate `My Strategy` 預設名稱會自動改成唯一名稱；cached `selectedStrategy` 會在 leaderboard fallback 前先回填，避免重整後被第一名策略覆蓋工作區語境。
- 下一步：Keep /api/models/leaderboard and Strategy Lab aligned on latest bounded walk-forward plus the recent-two-year backtest policy；同時守住工作區初始化 safety，不要再讓預設名稱 collision 或 cached selection 被初始化流程覆蓋。
- 驗證：
  - browser /lab
  - curl http://127.0.0.1:<active-backend>/api/models/leaderboard
  - pytest tests/test_strategy_lab_manual_model_and_auto_contract.py -q
  - cd web && npm run build

---

## Current Priority
1. **維持 current-live blocker truth（decision_quality_below_trade_floor），同時保留 q15 current-live bucket support rows 可 machine-read**
2. **持續沿 recent canonical pathological slice 追根因，不要 generic 化 blocker**
3. **守住 q15 current-live bucket support / reference-only patch、leaderboard dual-role governance、Strategy Lab workspace safety、venue/source blockers 可見性**
4. **讓 heartbeat 自動 overwrite sync current-state docs，不再把 docs drift 留給人工補寫**
