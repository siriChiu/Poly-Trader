# ISSUES.md — Current State Only

_最後更新：2026-04-24 21:24:40 CST_

只保留目前有效問題；由 heartbeat runner overwrite sync，避免 current-state markdown 落後 issues.json / live artifacts。

---

## 當前主線事實
- **最新 fast heartbeat #20260424_2111 已完成 collect + diagnostics refresh**
  - `Raw=32179 / Features=23597 / Labels=64891`
  - 歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`
  - `simulated_pyramid_win=57.00%`
- **canonical current-live blocker 已切到 current-live exact-support truth**
  - `deployment_blocker=under_minimum_exact_live_structure_bucket` / `streak=None` / `recent_window_wins=None/None` / `additional_recent_window_wins_needed=—`
  - `current_live_structure_bucket=BLOCK|bull_high_bias200_overheat_block|q35` / `support=5/50` / `gap=45` / `support_route_verdict=exact_bucket_present_but_below_minimum`
- **recent canonical diagnostics 已刷新**
  - `latest_window=100` / `win_rate=79.0%` / `dominant_regime=bull(100.0%)` / `avg_quality=+0.3416` / `avg_pnl=+0.0041` / `alerts=regime_concentration,regime_shift`
  - `blocking_window=500` / `win_rate=52.6%` / `dominant_regime=bull(99.6%)` / `avg_quality=+0.1030` / `avg_pnl=+0.0001` / `alerts=regime_concentration,regime_shift`
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- **source / venue blockers 仍開啟**
  - `blocked_sparse_features=8` / `{'archive_required': 3, 'snapshot_only': 4, 'short_window_public_api': 1}`
  - fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3647` / `archive_window_coverage_pct=0.0`
  - venue：`live exchange credential / order ack lifecycle / fill lifecycle` 尚未有 runtime-backed proof
- **heartbeat current-state docs overwrite sync 已自動化**
  - `scripts/hb_parallel_runner.py` 現在會在 `auto_propose_fixes.py` 後自動覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 目的：避免 markdown docs 落後 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json`，讓 cron 心跳真正完成 docs overwrite 閉環
- **本輪 operator-facing q35 current-bucket 根因 copy 已修正**
  - Dashboard、`/execution/status`、`/lab` 在 current bucket 是 q35 時改顯示 `交易門檻缺口 0.2387 · q35 公式 / 重設仍只屬治理參考`
  - 不再把 q35 current bucket 誤顯示成「近邊界樣本 / 距 q35 還差」，避免 operator 把已在 q35 的 live row 誤讀成 q15 邊界問題

---

## Open Issues

### P0. current live bucket BLOCK|bull_high_bias200_overheat_block|q35 exact support remains under minimum and remains the deployment blocker (5/50)
- 目前真相：`deployment_blocker=under_minimum_exact_live_structure_bucket` / `bucket=BLOCK|bull_high_bias200_overheat_block|q35` / `support=5/50` / `gap=45` / `runtime_closure_state=patch_inactive_or_blocked`
- same-bucket truth：`support_route_verdict=exact_bucket_present_but_below_minimum` / `support_governance_route=exact_live_bucket_present_but_below_minimum` / `recommended_patch=core_plus_macro_plus_all_4h` / `recommended_patch_status=reference_only_non_current_live_scope` / `reference_scope=bull|CAUTION`
- 下一步：把 current-live blocker 語義切到 exact-support truth；在 current live bucket 補滿 minimum rows 前，不要把 proxy rows、reference patch、或 breaker 舊敘事誤當成已解除 blocker。

### P0. recent canonical window 500 rows = regime_concentration
- 目前真相：`window=500` / `win_rate=52.6%` / `dominant_regime=bull(99.6%)` / `avg_quality=+0.1030` / `avg_pnl=+0.0001` / `alerts=regime_concentration,regime_shift`
- latest diagnostics：`latest_window=100` / `win_rate=79.0%` / `dominant_regime=bull(100.0%)` / `avg_quality=+0.3416` / `avg_pnl=+0.0041` / `alerts=regime_concentration,regime_shift`
- 病態切片：`alerts=regime_concentration,regime_shift` / `tail_streak=20x1` / `top_shift=feat_4h_macd_hist,feat_4h_dist_bb_lower,feat_4h_vol_ratio` / `new_compressed=None`
- 下一步：直接對 recent canonical rows 做 feature variance / distinct-count / target-path drill-down；維持 decision-quality guardrails，並檢查 calibration scope 是否仍被病態 slice 稀釋。具體 window / alerts / feature shifts 只保留在 machine-readable summary 與 recent_drift_report artifact，避免 ISSUES.md / ROADMAP.md 被長篇 telemetry 污染。
- 驗證：
  - python scripts/recent_drift_report.py
  - python scripts/hb_predict_probe.py

### P1. support-aware core_plus_macro_plus_all_4h patch must stay visible but reference-only outside current live scope
- 目前真相：`bucket=BLOCK|bull_high_bias200_overheat_block|q35` / `support=5/50` / `gap=45` / `support_route_verdict=exact_bucket_present_but_below_minimum` / `governance_route=exact_live_bucket_present_but_below_minimum`
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
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3647` / `archive_window_coverage_pct=0.0`
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

### P1. q35 lane still needs formula review / base-stack redesign before deploy
- 目前真相：`bucket=BLOCK|bull_high_bias200_overheat_block|q35` / `support=5/50` / `gap=45` / `support_route_verdict=exact_bucket_present_but_below_minimum` / `overall_verdict=bias50_formula_may_be_too_harsh` / `redesign_verdict=base_stack_redesign_discriminative_reweight_still_below_floor` / `runtime_gap_to_floor=0.2387`
- q35 scaling audit 已指出目前不是單點 bias50 closure： `overall_verdict=bias50_formula_may_be_too_harsh` / `redesign_verdict=base_stack_redesign_discriminative_reweight_still_below_floor` / `runtime_gap_to_floor=0.2387` / `redesign_entry_quality=0.2546` / `redesign_allowed_layers=0` / `positive_discriminative_gap=True` / `execution_blocked_after_floor_cross=False`
- 下一步：把 q35 scaling audit 的 overall_verdict / redesign verdict / gap-to-floor 同步到 docs/probe/issues；在 exact support 未就緒、且 redesign 未形成可執行 closure 前，禁止把 bias50 單點 uplift 或結構 uplift 當成 closure。
- 本輪產品化修正：Dashboard、`/execution/status`、`/lab` 已把 q35 current-bucket 根因卡改成交易門檻缺口語義；current bucket 已是 q35 時，不再顯示 q15/q35 邊界差距。
- 驗證：
  - PYTHONPATH=. python -m pytest tests/test_frontend_decision_contract.py -q
  - cd web && npm run build
  - browser `/`、`/execution/status`、`/lab` DOM 均出現 `交易門檻缺口 0.2387`，且 q35 current bucket 不再出現 `近邊界樣本 / 距 q35 還差`

---

## Current Priority
1. **維持 current-live exact-support blocker truth，同時保留 current live bucket support rows 可 machine-read**
2. **持續沿 recent canonical pathological slice 追根因，不要 generic 化 blocker**
3. **守住 current live bucket support / reference-only patch、leaderboard dual-role governance、venue/source blockers 可見性**
4. **讓 heartbeat 自動 overwrite sync current-state docs，不再把 docs drift 留給人工補寫**
