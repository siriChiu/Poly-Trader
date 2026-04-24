# ISSUES.md — Current State Only

_最後更新：2026-04-24 09:51:56 CST_

只保留目前有效問題；由 heartbeat runner overwrite sync，避免 current-state markdown 落後 issues.json / live artifacts。

---

## 當前主線事實
- **最新 fast heartbeat #20260424n 已完成 collect + diagnostics refresh**
  - `Raw=32134 / Features=23552 / Labels=64721`
  - 歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`
  - `simulated_pyramid_win=56.94%`
- **canonical current-live blocker 已切到 current-live exact-support truth**
  - `deployment_blocker=unsupported_exact_live_structure_bucket` / `streak=None` / `recent_window_wins=None/None` / `additional_recent_window_wins_needed=—`
  - `current_live_structure_bucket=BLOCK|bull_high_bias200_overheat_block|q35` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_unsupported_block`
- **recent canonical diagnostics 已刷新**
  - `latest_window=500` / `win_rate=45.0%` / `dominant_regime=bull(99.6%)` / `avg_quality=+0.0673` / `avg_pnl=0.0000` / `alerts=regime_concentration,regime_shift`
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- **source / venue blockers 仍開啟**
  - `blocked_sparse_features=8` / `{'archive_required': 3, 'snapshot_only': 4, 'short_window_public_api': 1}`
  - fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3602` / `archive_window_coverage_pct=0.0`
  - venue：`live exchange credential / order ack lifecycle / fill lifecycle` 尚未有 runtime-backed proof
- **heartbeat current-state docs overwrite sync 已自動化**
  - `scripts/hb_parallel_runner.py` 現在會在 `auto_propose_fixes.py` 後自動覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 目的：避免 markdown docs 落後 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json`，讓 cron 心跳真正完成 docs overwrite 閉環
- **operator-facing copy hygiene 已補強到 Execution Console / Strategy Lab**
  - Execution Console 的 run / sleeve / profile placeholders 已 humanize 成中文 operator copy
  - Strategy Lab 策略排行榜的 sleeve filter / badge / labels 不再露出 raw `sleeve` 英文 token；由 `tests/test_frontend_decision_contract.py` 與 `npm run build` 鎖住

---

## Open Issues

### P0. current live bucket BLOCK|bull_high_bias200_overheat_block|q35 exact support is missing and remains the deployment blocker (0/50)
- 目前真相：`deployment_blocker=unsupported_exact_live_structure_bucket` / `bucket=BLOCK|bull_high_bias200_overheat_block|q35` / `support=0/50` / `gap=50` / `runtime_closure_state=patch_inactive_or_blocked`
- same-bucket truth：`support_route_verdict=exact_bucket_unsupported_block` / `support_governance_route=no_support_proxy` / `recommended_patch=core_plus_macro_plus_all_4h` / `recommended_patch_status=reference_only_non_current_live_scope` / `reference_scope=bull|CAUTION`
- 下一步：把 current-live blocker 語義切到 exact-support truth；在 current live bucket 補滿 minimum rows 前，不要把 proxy rows、reference patch、或 breaker 舊敘事誤當成已解除 blocker。

### P0. recent canonical window 500 rows = regime_concentration
- 目前真相：`window=500` / `win_rate=45.0%` / `dominant_regime=bull(99.6%)` / `avg_quality=+0.0673` / `avg_pnl=0.0000` / `alerts=regime_concentration,regime_shift`
- 病態切片：`alerts=regime_concentration,regime_shift` / `tail_streak=24x1` / `adverse_streak=44x0` / `top_shift=feat_4h_bb_pct_b,feat_4h_dist_bb_lower,feat_4h_bias20` / `new_compressed=feat_vix`
- 下一步：直接對 recent canonical rows 做 feature variance / distinct-count / target-path drill-down；目前 `feature_diag=variance 11/56, compressed 11, distinct 10, null_heavy 10`，sibling-window 對比 `WR 57.8%→45.0% / quality 0.2498→0.0673 / pnl 0.0067→0.0000`，top shifts=`feat_4h_bb_pct_b / feat_4h_dist_bb_lower / feat_4h_bias20`，new compressed=`feat_vix`。
- 驗證：
  - python scripts/recent_drift_report.py
  - python scripts/hb_predict_probe.py

### P1. support-aware core_plus_macro_plus_all_4h patch must stay visible but reference-only outside current live scope
- 目前真相：`bucket=BLOCK|bull_high_bias200_overheat_block|q35` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_unsupported_block` / `governance_route=no_support_proxy`
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
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3602` / `archive_window_coverage_pct=0.0`
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
- 目前真相：`bucket=BLOCK|bull_high_bias200_overheat_block|q35` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_unsupported_block` / `overall_verdict=bias50_formula_may_be_too_harsh` / `redesign_verdict=base_stack_redesign_discriminative_reweight_still_below_floor` / `remaining_gap_to_floor=0.159`
- q35 scaling audit 已指出目前不是單點 bias50 closure：`overall_verdict=bias50_formula_may_be_too_harsh` / `redesign_verdict=base_stack_redesign_discriminative_reweight_still_below_floor` / `remaining_gap_to_floor=0.159`
- 下一步：把 q35 scaling audit 的 overall_verdict / redesign verdict / gap-to-floor 同步到 docs/probe/issues；在 exact support 未就緒、且 redesign 仍無正 discrimination floor-cross 之前，禁止把 bias50 單點 uplift 或結構 uplift 當成 closure。 即使做 support-aware / discriminative base-stack redesign，current row 仍無法跨過 trade floor；下一輪必須升級為 bull q35 no-deploy governance blocker，禁止再把結構 uplift、單點 bias50 或 base-stack 權重微調當成主 closure。

---

## Current Priority
1. **維持 current-live exact-support blocker truth，同時保留 current live bucket support rows 可 machine-read**
2. **持續沿 recent canonical pathological slice 追根因，不要 generic 化 blocker**
3. **守住 current live bucket support / reference-only patch、leaderboard dual-role governance、venue/source blockers 可見性**
4. **讓 heartbeat 自動 overwrite sync current-state docs，不再把 docs drift 留給人工補寫**
