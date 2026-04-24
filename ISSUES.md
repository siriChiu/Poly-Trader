# ISSUES.md — Current State Only

_最後更新：2026-04-25 02:42:59 CST_

只保留目前有效問題；由 heartbeat runner overwrite sync，避免 current-state markdown 落後 issues.json / live artifacts。

---

## 當前主線事實
- **最新 full heartbeat #20260425_022713 已完成 collect + diagnostics refresh**
  - `Raw=32192 / Features=23610 / Labels=64928`
  - 歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`
  - `simulated_pyramid_win=56.98%`
- **canonical current-live blocker 以 latest runtime truth 為主**
  - `deployment_blocker=decision_quality_below_trade_floor` / `streak=None` / `recent_window_wins=None/None` / `additional_recent_window_wins_needed=—`
  - `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=123/50` / `gap=0` / `support_route_verdict=exact_bucket_supported`
  - support progress：`status=exact_supported` / `regression_basis=current_identity` / `legacy_supported_reference=121/50@20260424a`
- **recent canonical diagnostics 已刷新**
  - `latest_window=500` / `win_rate=53.4%` / `dominant_regime=bull(99.4%)` / `avg_quality=+0.1145` / `avg_pnl=+0.0005` / `alerts=regime_concentration,regime_shift`
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- **candidate governance refresh 仍有 stale fallback 風險**
  - `feature_group_ablation=timeout→fallback(42.9h) / bull_4h_pocket_ablation=timeout→fallback(42.9h) / hb_leaderboard_candidate_probe=cached(0.0h)`
- **source / venue blockers 仍開啟**
  - `blocked_sparse_features=8` / `{'archive_required': 3, 'snapshot_only': 4, 'short_window_public_api': 1}`
  - fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3659` / `archive_window_coverage_pct=0.0`
  - venue：`live exchange credential / order ack lifecycle / fill lifecycle` 尚未有 runtime-backed proof
- **heartbeat current-state docs overwrite sync 已自動化**
  - `scripts/hb_parallel_runner.py` 現在會在 `auto_propose_fixes.py` 後自動覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 目的：避免 markdown docs 落後 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json`，讓 cron 心跳真正完成 docs overwrite 閉環

---

## Open Issues

### P1. current live bucket CAUTION|base_caution_regime_or_bias|q15 is exact-supported but remains hold-only below the trade floor
- 目前真相：`deployment_blocker=decision_quality_below_trade_floor` / `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15` / `current_live_structure_bucket_rows=123` / `minimum_support_rows=50` / `gap_to_minimum=0` / `support_route_verdict=exact_bucket_supported`
- 下一步：把這個狀態視為正常 no-deploy risk posture 而非 release-blocking support failure：保留 allowed_layers=0 / trade_floor_gap / support metrics，僅在 exact-supported component experiment 通過 discrimination 與 runtime guardrail 後才重新開放下單。

### P1. venue readiness is still unverified
- 目前真相：`binance=config enabled + public-only + metadata OK` / `okx=config disabled + public-only + metadata OK` / `missing_runtime_proof=live exchange credential, order ack lifecycle, fill lifecycle`
- 下一步：Keep per-venue blockers explicitly visible on Dashboard, /lab, and /execution/status until credentials, order ack lifecycle, and fill lifecycle each have runtime-backed proof.
- 驗證：
  - browser /execution
  - browser /execution/status
  - browser /lab
  - data/execution_metadata_smoke.json

### P1. fin_netflow remains source_auth_blocked because COINGLASS_API_KEY is missing
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3659` / `archive_window_coverage_pct=0.0`
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

### P1. recent canonical window 500 rows = regime_concentration but current live regime is outside the blocker pocket
- 目前真相：`window=500` / `interpretation=regime_concentration` / `win_rate=0.534` / `dominant_regime=bull` / `dominant_regime_share=0.994` / `avg_pnl=0.0005`
- 下一步：保留 recent canonical drift 監控與 blocker-window evidence；目前 live predictor 沒有套用 recent pathology guardrail，且 current live regime 不等於 blocker dominant regime，因此降為 P1 監控，不得當成 deployment closure。

### P1. candidate governance artifacts fell back after refresh timeouts
- 目前真相：`heartbeat=20260425_022713` / `timed_out_lanes=feature_group_ablation, bull_4h_pocket_ablation` / `stale_fallback_lanes=feature_group_ablation, bull_4h_pocket_ablation` / `artifact_age_hours_by_lane={'feature_group_ablation': 42.88, 'bull_4h_pocket_ablation': 42.88}` / `refresh_required=True`
- 下一步：把 feature shrinkage / bull pocket candidate refresh 從 silent full rebuild 改成可完成的 bounded/live-context-only lane；在刷新完成前，leaderboard / training governance 必須把 stale fallback 標成 reference-only，不可當成 fresh production truth。
- 驗證：
  - source venv/bin/activate && python -m pytest tests/test_hb_parallel_runner.py -q
  - python scripts/hb_parallel_runner.py --hb <next_full_run>
  - check data/heartbeat_<run>_summary.json serial_results candidate lanes

---

## Current Priority
1. **維持 current-live blocker truth（decision_quality_below_trade_floor），同時保留 q15 current-live bucket support rows 可 machine-read**
2. **持續沿 recent canonical pathological slice 追根因，不要 generic 化 blocker**
3. **守住 q15 current-live bucket support truth / blocker truth、leaderboard dual-role governance、venue/source blockers 可見性**
4. **讓 heartbeat 自動 overwrite sync current-state docs，不再把 docs drift 留給人工補寫**
