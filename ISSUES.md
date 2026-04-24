# ISSUES.md — Current State Only

_最後更新：2026-04-24 16:04:07 CST_

只保留目前有效問題；由 heartbeat runner overwrite sync，避免 current-state markdown 落後 issues.json / live artifacts。

---

## 當前主線事實
- **最新 fast heartbeat #20260424_1602 已完成 collect + diagnostics refresh**
  - `Raw=32161 / Features=23579 / Labels=64852`
  - 歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`
  - `simulated_pyramid_win=56.98%`
- **canonical current-live blocker 已切到 current-live exact-support truth**
  - `deployment_blocker=unsupported_exact_live_structure_bucket` / `streak=None` / `recent_window_wins=None/None` / `additional_recent_window_wins_needed=—`
  - `current_live_structure_bucket=CAUTION|structure_quality_caution|q15` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_proxy_reference_only`
- **recent canonical diagnostics 已刷新**
  - `latest_window=100` / `win_rate=79.0%` / `dominant_regime=bull(100.0%)` / `avg_quality=+0.3318` / `avg_pnl=+0.0045` / `alerts=regime_concentration,regime_shift`
  - `blocking_window=500` / `win_rate=50.0%` / `dominant_regime=bull(99.6%)` / `avg_quality=+0.0817` / `avg_pnl=-0.0002` / `alerts=regime_concentration,regime_shift`
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- **source / venue blockers 仍開啟**
  - `blocked_sparse_features=8` / `{'archive_required': 3, 'snapshot_only': 4, 'short_window_public_api': 1}`
  - fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3629` / `archive_window_coverage_pct=0.0`
  - venue：`live exchange credential / order ack lifecycle / fill lifecycle` 尚未有 runtime-backed proof
- **heartbeat current-state docs overwrite sync 已自動化**
  - `scripts/hb_parallel_runner.py` 現在會在 `auto_propose_fixes.py` 後自動覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 目的：避免 markdown docs 落後 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json`，讓 cron 心跳真正完成 docs overwrite 閉環
- **本輪產品化 patch 已落地**
  - Dashboard ConfidenceIndicator 直接顯示 `current_bucket_root_cause`（候選修補方案 / 近邊界樣本 / q35 邊界缺口），不再讓首頁只剩 generic q15/q35 摘要。
  - `hb_parallel_runner.py` full-mode candidate-eval lanes 可在 bounded label drift 下沿用 fresh governance artifact，並對 feature-group / bull-pocket / leaderboard candidate lanes 設定 full-mode timeout，避免單一 silent ablation 吃完整輪 heartbeat 預算。

---

## Open Issues

### P0. current live bucket CAUTION|structure_quality_caution|q15 exact support is missing and remains the deployment blocker (0/50)
- 目前真相：`deployment_blocker=unsupported_exact_live_structure_bucket` / `bucket=CAUTION|structure_quality_caution|q15` / `support=0/50` / `gap=50` / `runtime_closure_state=patch_inactive_or_blocked`
- same-bucket truth：`support_route_verdict=exact_bucket_missing_proxy_reference_only` / `support_governance_route=exact_live_bucket_proxy_available` / `recommended_patch=core_plus_macro_plus_all_4h` / `recommended_patch_status=reference_only_until_exact_support_ready` / `reference_scope=bull|CAUTION`
- 下一步：把 current-live blocker 語義切到 exact-support truth；在 current live bucket 補滿 minimum rows 前，不要把 proxy rows、reference patch、或 breaker 舊敘事誤當成已解除 blocker。

### P0. recent canonical window 500 rows = regime_concentration
- 目前真相：`window=500` / `win_rate=50.0%` / `dominant_regime=bull(99.6%)` / `avg_quality=+0.0817` / `avg_pnl=-0.0002` / `alerts=regime_concentration,regime_shift`
- latest diagnostics：`latest_window=100` / `win_rate=79.0%` / `dominant_regime=bull(100.0%)` / `avg_quality=+0.3318` / `avg_pnl=+0.0045` / `alerts=regime_concentration,regime_shift`
- 病態切片：`alerts=regime_concentration,regime_shift` / `tail_streak=21x0` / `top_shift=feat_4h_macd_hist,feat_4h_dist_bb_lower,feat_4h_vol_ratio` / `new_compressed=feat_vix`
- 下一步：直接對 recent canonical rows 做 feature variance / distinct-count / target-path drill-down；維持 decision-quality guardrails，並檢查 calibration scope 是否仍被病態 slice 稀釋。具體 window / alerts / feature shifts 只保留在 machine-readable summary 與 recent_drift_report artifact，避免 ISSUES.md / ROADMAP.md 被長篇 telemetry 污染。
- 驗證：
  - python scripts/recent_drift_report.py
  - python scripts/hb_predict_probe.py

### P1. support-aware core_plus_macro_plus_all_4h patch must stay visible but reference-only
- 目前真相：`bucket=CAUTION|structure_quality_caution|q15` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_proxy_reference_only` / `governance_route=exact_live_bucket_proxy_available`
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
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3629` / `archive_window_coverage_pct=0.0`
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

### P1. q15 exact support regressed under minimum while breaker is clear (0/50)
- 目前真相：`bucket=CAUTION|structure_quality_caution|q15` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_proxy_reference_only` / `governance_route=exact_live_bucket_proxy_available` / `breaker_context=breaker_clear`
- 下一步：Treat this as support regression, not ordinary stagnation: keep support_route_verdict/support_progress/minimum_support_rows/gap_to_minimum plus the last-supported reference visible in probe/API/UI/docs, verify why the current bucket fell back under minimum, and keep breaker context explicit.

---

## Current Priority
1. **維持 current-live exact-support blocker truth，同時保留 q15 current-live bucket support rows 可 machine-read**
2. **持續沿 recent canonical pathological slice 追根因，不要 generic 化 blocker**
3. **守住 q15 current-live bucket support / reference-only patch、leaderboard dual-role governance、venue/source blockers 可見性**
4. **讓 heartbeat 自動 overwrite sync current-state docs，不再把 docs drift 留給人工補寫**
