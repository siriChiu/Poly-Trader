# ISSUES.md — Current State Only

_最後更新：2026-04-22 17:41:54 CST_

只保留目前有效問題；本輪已覆寫同步 current-state truth，避免 markdown docs 落後 live artifacts / runtime surface。

---

## 當前主線事實
- **current-live blocker 真相維持一致**
  - `deployment_blocker=unsupported_exact_live_structure_bucket`
  - `current_live_structure_bucket=BLOCK|bull_high_bias200_overheat_block|q35`
  - `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_unsupported_block` / `support_governance_route=no_support_proxy`
  - `recommended_patch=core_plus_macro_plus_all_4h` / `recommended_patch_status=reference_only_non_current_live_scope` / `reference_scope=bull|CAUTION`
- **recent canonical drift 最新 machine-read 已刷新**
  - `latest_window=250` / `win_rate=82.8%` / `dominant_regime=chop(57.6%)` / `avg_quality=+0.4434` / `avg_pnl=+0.0117` / `alerts=label_imbalance`
  - `blocking_window=1000` / `win_rate=39.4%` / `dominant_regime=bull(81.3%)` / `avg_quality=+0.0804` / `avg_pnl=+0.0008` / `alerts=regime_shift`
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h`
  - `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- **本輪已修復 local dev backend lane split-brain**
  - `/health` 新增 `runtime_build={process_started_at, git_head_commit, head_sync_status}`，可 machine-read backend code freshness
  - `web/src/hooks/useApi.ts` prewarm 現在優先 `current_head_commit` lane，避免 stale stable lane 壓過 fresh code lane
  - browser 驗證：`poly_trader.active_api_base` 只會落在 `head_sync_status=current_head_commit` 的 lane（本輪 `/`、`/lab` 觀察到 `:8000`；未再看到 stale lane 被選中）
  - runtime 驗證：`:8000` / `:8001` 目前都回 `head_sync_status=current_head_commit`，`/api/status` blocker / bucket / patch status 已對齊
- **source / venue blockers 仍開啟**
  - `fin_netflow=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=2976` / `archive_window_coverage_pct=0.0`
  - venue 仍缺 `live exchange credential / order ack lifecycle / fill lifecycle` runtime-backed proof

---

## Open Issues

### P0. current live bucket BLOCK|bull_high_bias200_overheat_block|q35 exact support is missing and remains the deployment blocker (0/50)
- 真相：`deployment_blocker=unsupported_exact_live_structure_bucket` / `runtime_closure_state=patch_inactive_or_blocked`
- same-bucket truth：`support_route_verdict=exact_bucket_unsupported_block` / `support_governance_route=no_support_proxy` / `recommended_patch_status=reference_only_non_current_live_scope`
- 下一步：在 current live bucket 補滿 minimum rows 前，維持 exact-support blocker 作為唯一 current-live deployment blocker；禁止把 proxy rows、reference patch、或舊 breaker 敘事誤當成 closure。
- 驗證：`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、browser `/execution/status`、browser `/lab`

### P0. recent canonical window 1000 rows = regime_concentration
- 真相：`window=1000` / `win_rate=39.4%` / `dominant_regime=bull(81.3%)` / `avg_quality=+0.0804` / `avg_pnl=+0.0008` / `alerts=regime_shift`
- 對照：`latest_window=250` 反而是 `win_rate=82.8%` / `dominant_regime=chop(57.6%)` / `alerts=label_imbalance`
- 下一步：直接沿 `recent_drift_report` 的 target-path / sibling-window / top-shift 證據往下鑽，避免回退成 generic leaderboard / venue 摘要。
- 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`

### P1. support-aware core_plus_macro_plus_all_4h patch must stay visible but reference-only outside current live scope
- 真相：reference patch 來自 `bull|CAUTION` spillover，而 current live 是 `bull|BLOCK`
- 真相：`recommended_patch=core_plus_macro_plus_all_4h` / `recommended_patch_status=reference_only_non_current_live_scope` / `gap_to_minimum=50`
- 下一步：守住 `/api/status`、probe、drilldown、Dashboard、Strategy Lab、docs 的同一份 patch truth；不得把 spillover/reference patch 誤升級成 current-live deploy patch。

### P1. venue readiness is still unverified
- 真相：`binance=config enabled + public-only + metadata OK` / `okx=config disabled + public-only + metadata OK`
- 缺口：`live exchange credential` / `order ack lifecycle` / `fill lifecycle` 尚無 runtime-backed proof
- 驗證：browser `/execution`、browser `/execution/status`、browser `/lab`、`data/execution_metadata_smoke.json`

### P1. fin_netflow remains source_auth_blocked because COINGLASS_API_KEY is missing
- 真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `archive_window_coverage_pct=0.0`
- 下一步：補上 `COINGLASS_API_KEY`，並持續跑 collect / coverage 直到 auth_missing 被成功 snapshot 取代。

### P1. leaderboard comparable rows are back; keep the recent-window contract stable and cron-safe
- 真相：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h`
- 真相：`governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- 驗證：browser `/lab`、`curl http://127.0.0.1:<active-backend>/api/models/leaderboard`、`pytest tests/test_model_leaderboard.py tests/test_strategy_lab.py tests/test_frontend_decision_contract.py -q`

### P1. q35 lane still needs formula review / base-stack redesign before deploy
- 真相：`overall_verdict=bias50_formula_may_be_too_harsh` / `redesign_verdict=base_stack_redesign_candidate_grid_empty` / `remaining_gap_to_floor=0.2027`
- 下一步：在 exact support 未就緒、且 redesign 尚無正 discrimination floor-cross 之前，禁止把 bias50 單點 uplift 或結構 uplift 當成 closure。

---

## Current Priority
1. **維持 current-live exact-support blocker truth，同時保留 current live bucket support rows 可 machine-read**
2. **持續沿 recent canonical pathological slice 追根因，不要 generic 化 blocker**
3. **守住 current live bucket support / reference-only patch、leaderboard dual-role governance、venue/source blockers 可見性**
4. **守住 runtime lane freshness guard 與 docs overwrite sync，避免 stale backend lane 再次覆蓋 current blocker truth**
