# ISSUES.md — Current State Only

_最後更新：2026-04-24 21:55:53 CST_

只保留目前有效問題；由 heartbeat runner overwrite sync，避免 current-state markdown 落後 issues.json / live artifacts。

---

## 當前主線事實
- **最新 fast heartbeat #20260424_214420 已完成 collect + diagnostics refresh**
  - `Raw=32181 / Features=23599 / Labels=64896`
  - 歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`
  - `simulated_pyramid_win=57.00%`
- **canonical current-live blocker 已切到 current-live exact-support truth**
  - `deployment_blocker=under_minimum_exact_live_structure_bucket` / `streak=None` / `recent_window_wins=None/None` / `additional_recent_window_wins_needed=—`
  - `current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15` / `support=33/50` / `gap=17` / `support_route_verdict=exact_bucket_present_but_below_minimum`
  - support progress：`status=semantic_rebaseline_under_minimum` / `regression_basis=legacy_or_different_semantic_signature` / `legacy_supported_reference=199/50@20260423i`
- **recent canonical diagnostics 已刷新**
  - `latest_window=100` / `win_rate=79.0%` / `dominant_regime=bull(100.0%)` / `avg_quality=+0.3441` / `avg_pnl=+0.0042` / `alerts=regime_concentration,regime_shift`
  - `blocking_window=500` / `win_rate=53.2%` / `dominant_regime=bull(99.6%)` / `avg_quality=+0.1080` / `avg_pnl=+0.0003` / `alerts=regime_concentration,regime_shift`
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- **source / venue blockers 仍開啟**
  - `blocked_sparse_features=8` / `{'archive_required': 3, 'snapshot_only': 4, 'short_window_public_api': 1}`
  - fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3649` / `archive_window_coverage_pct=0.0`
  - venue：`live exchange credential / order ack lifecycle / fill lifecycle` 尚未有 runtime-backed proof
- **heartbeat current-state docs overwrite sync 已自動化**
  - `scripts/hb_parallel_runner.py` 現在會在 `auto_propose_fixes.py` 後自動覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 目的：避免 markdown docs 落後 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json`，讓 cron 心跳真正完成 docs overwrite 閉環
- **本輪 operator-facing q15 semantic rebaseline copy 已產品化**
  - Dashboard、`/execution/status`、`/lab` 現在直接顯示 `舊版已就緒參考 #20260423i · 199 筆 · 基準 舊語義或不同語義簽章 · 支持語義 v2 · 1440m · 金字塔勝率`
  - 目的：避免 operator 把 legacy 199/50 舊語義 support 誤讀成當前 q15 33/50 已解除；support_identity / regression_basis / legacy_supported_reference 已在 UI 可見

---

## Open Issues

### P0. current live bucket BLOCK|bull_q15_bias50_overextended_block|q15 exact support remains under minimum and remains the deployment blocker (33/50)
- 目前真相：`deployment_blocker=under_minimum_exact_live_structure_bucket` / `bucket=BLOCK|bull_q15_bias50_overextended_block|q15` / `support=33/50` / `gap=17` / `runtime_closure_state=patch_inactive_or_blocked`
- same-bucket truth：`support_route_verdict=exact_bucket_present_but_below_minimum` / `support_governance_route=exact_live_bucket_present_but_below_minimum` / `recommended_patch=core_plus_macro_plus_all_4h` / `recommended_patch_status=reference_only_non_current_live_scope` / `reference_scope=bull|CAUTION`
- support progress：`status=semantic_rebaseline_under_minimum` / `regression_basis=legacy_or_different_semantic_signature` / `legacy_supported_reference=199/50@20260423i`
- 下一步：把 current-live blocker 語義切到 exact-support truth；在 current live bucket 補滿 minimum rows 前，不要把 proxy rows、reference patch、或 breaker 舊敘事誤當成已解除 blocker。

### P0. recent canonical window 500 rows = regime_concentration
- 目前真相：`window=500` / `win_rate=53.2%` / `dominant_regime=bull(99.6%)` / `avg_quality=+0.1080` / `avg_pnl=+0.0003` / `alerts=regime_concentration,regime_shift`
- latest diagnostics：`latest_window=100` / `win_rate=79.0%` / `dominant_regime=bull(100.0%)` / `avg_quality=+0.3441` / `avg_pnl=+0.0042` / `alerts=regime_concentration,regime_shift`
- 病態切片：`alerts=regime_concentration,regime_shift` / `tail_streak=23x1` / `top_shift=feat_4h_macd_hist,feat_4h_dist_bb_lower,feat_4h_vol_ratio` / `new_compressed=None`
- 下一步：直接對 recent canonical rows 做 feature variance / distinct-count / target-path drill-down；維持 decision-quality guardrails，並檢查 calibration scope 是否仍被病態 slice 稀釋。具體 window / alerts / feature shifts 只保留在 machine-readable summary 與 recent_drift_report artifact，避免 ISSUES.md / ROADMAP.md 被長篇 telemetry 污染。
- 驗證：
  - python scripts/recent_drift_report.py
  - python scripts/hb_predict_probe.py

### P1. support-aware core_plus_macro_plus_all_4h patch must stay visible but reference-only outside current live scope
- 目前真相：`bucket=BLOCK|bull_q15_bias50_overextended_block|q15` / `support=33/50` / `gap=17` / `support_route_verdict=exact_bucket_present_but_below_minimum` / `governance_route=exact_live_bucket_present_but_below_minimum`
- support progress：`status=semantic_rebaseline_under_minimum` / `regression_basis=legacy_or_different_semantic_signature` / `legacy_supported_reference=199/50@20260423i`
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
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3649` / `archive_window_coverage_pct=0.0`
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

### P1. q15 exact support under minimum after semantic rebaseline while breaker is clear (33/50)
- 目前真相：`bucket=BLOCK|bull_q15_bias50_overextended_block|q15` / `support=33/50` / `gap=17` / `support_route_verdict=exact_bucket_present_but_below_minimum` / `governance_route=exact_live_bucket_present_but_below_minimum` / `breaker_context=breaker_clear`
- support progress：`status=semantic_rebaseline_under_minimum` / `regression_basis=legacy_or_different_semantic_signature` / `legacy_supported_reference=199/50@20260423i`
- 本輪產品化修正：Dashboard、`/execution/status`、`/lab` 已用 shared `runtimeCopy` 顯示 `舊版已就緒參考 #20260423i · 199 筆 · 基準 舊語義或不同語義簽章 · 支持語義 v2 · 1440m · 金字塔勝率`，不再把 `simulated_pyramid_win` raw token 或 legacy support 藏在 JSON。
- 下一步：Treat legacy supported rows as reference-only: keep support_identity/regression_basis/legacy_supported_reference visible in probe/API/UI/docs, keep the current-live exact-support blocker open, and do not describe this as same-identity support regression unless the semantic signature matches.
- 驗證：
  - `python -m pytest tests/test_frontend_decision_contract.py -q`
  - `cd web && npm run build`
  - browser `/`、`/execution/status`、`/lab` DOM 均出現 `舊版已就緒參考 #20260423i`、`支持語義 v2`、`金字塔勝率`，且不再出現 raw `simulated_pyramid_win`

---

## Current Priority
1. **維持 current-live exact-support blocker truth，同時保留 q15 current-live bucket support rows 可 machine-read**
2. **持續沿 recent canonical pathological slice 追根因，不要 generic 化 blocker**
3. **守住 q15 current-live bucket support / reference-only patch、leaderboard dual-role governance、venue/source blockers 可見性**
4. **讓 heartbeat 自動 overwrite sync current-state docs，不再把 docs drift 留給人工補寫**
