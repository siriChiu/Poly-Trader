# ISSUES.md — Current State Only

_最後更新：2026-04-20 12:46:40 CST_

只保留目前有效問題；由 heartbeat runner / current-state docs overwrite sync 維持與 issues.json / live artifacts 一致。

---

## 當前主線事實
- **最新 fast heartbeat #fast 已完成 collect + diagnostics refresh**
  - `Raw=31214 / Features=22632 / Labels=62947`
  - `simulated_pyramid_win=57.17%`
- **canonical current-live blocker 仍是 breaker-first truth**
  - `deployment_blocker=circuit_breaker_active` / `streak=15` / `recent_window_wins=3/50` / `additional_recent_window_wins_needed=12`
  - `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=11/50` / `gap=39` / `support_route_verdict=exact_bucket_present_but_below_minimum`
- **recent canonical window 仍是 distribution pathology**
  - `window=250` / `win_rate=1.6%` / `dominant_regime=bull(95.6%)` / `avg_quality=-0.2119` / `avg_pnl=-0.0066` / `alerts=label_imbalance,regime_concentration,regime_shift`
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- **venue/source blockers 仍開啟，但 operator-facing wording 已 productized**
  - fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=2685` / `archive_window_coverage_pct=0.0`
  - venue：`live exchange credential / order ack lifecycle / fill lifecycle` 仍未有 runtime-backed proof
  - `VenueReadinessSummary`、Dashboard、Strategy Lab、Execution Status 已不再把 public-only / disabled venue 渲染成泛化 `OK`；改為 `READ-ONLY` / `DISABLED`，並把 `metadata contract OK` 降為次層語義
  - Dashboard / Execution Status 的帳戶資金卡在 public-only 模式下會明確顯示 `public-only / metadata only` 與 `private balance unavailable until exchange credentials are configured`，避免 `— USDT` 假陰性
- **heartbeat current-state docs overwrite sync 仍有效**
  - `scripts/hb_parallel_runner.py` 會在 `auto_propose_fixes.py` 後自動覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
- 目前真相：`deployment_blocker=circuit_breaker_active` / `streak=15` / `recent 50 wins=3/50` / `additional_recent_window_wins_needed=12`
- same-bucket truth：`bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=11/50` / `support_route_verdict=exact_bucket_present_but_below_minimum` / `support_governance_route=exact_live_lane_proxy_available`
- 下一步：先把 current-live blocker 語義切回 circuit breaker release math；在 breaker 未解除前，不要把 q15/q35 support 或 floor-gap 當成本輪主 blocker。recent 50 需至少 15 勝，當前 3 勝，還差 12 勝；同時 streak 必須 < 50。
- 驗證：browser `/`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`

### P0. recent canonical 250 rows remains a distribution pathology
- 目前真相：`window=250` / `win_rate=1.6%` / `dominant_regime=bull(95.6%)` / `avg_quality=-0.2119` / `avg_pnl=-0.0066`
- 病態切片：`alerts=label_imbalance,regime_concentration,regime_shift` / `tail_streak=15` / `low_variance=11` / `low_distinct=13` / `null_heavy=10`
- 下一步：直接對 recent canonical rows 做 feature variance / distinct-count / target-path drill-down；維持 decision-quality guardrails，並檢查 calibration scope 是否仍被病態 slice 稀釋。
- 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`

### P1. venue readiness is still unverified
- 目前真相：`binance=config enabled + public-only + metadata OK` / `okx=config disabled + public-only + metadata OK` / `missing_runtime_proof=live exchange credential, order ack lifecycle, fill lifecycle`
- 已完成：operator-facing UI 不再把 public-only / disabled venue 誤標成泛化 `OK`；READ-ONLY / DISABLED + metadata contract wording 已在 Dashboard、Strategy Lab、Execution Status 對齊。
- 下一步：Keep per-venue blockers explicitly visible until credentials, order ack lifecycle, and fill lifecycle each have runtime-backed proof；不要讓 metadata smoke 成功被誤讀成 live-ready。
- 驗證：browser `/`、browser `/execution/status`、browser `/lab`、`data/execution_metadata_smoke.json`

### P1. support-aware core_plus_macro_plus_all_4h patch must stay visible but reference-only
- 目前真相：`bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=11/50` / `gap=39` / `support_route_verdict=exact_bucket_present_but_below_minimum` / `governance_route=exact_live_lane_proxy_available`
- 下一步：Keep the same recommended_patch summary across /api/status, /lab, hb_predict_probe.py, live_decision_quality_drilldown.py, and docs; do not promote it from reference-only until current-live exact support reaches the minimum rows.

### P1. fin_netflow remains source_auth_blocked because COINGLASS_API_KEY is missing
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=2685` / `archive_window_coverage_pct=0.0`
- 下一步：Configure COINGLASS_API_KEY, then keep heartbeat collection running until successful ETF-flow snapshots replace auth_missing rows and coverage starts to move.
- 驗證：`data/execution_metadata_smoke.json`、`/api/features/coverage`

### P1. leaderboard comparable rows are back; keep the recent-window contract stable and cron-safe
- 目前真相：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- 下一步：Keep /api/models/leaderboard and Strategy Lab aligned on latest bounded walk-forward plus the recent-two-year backtest policy; do not regress to placeholder-only or ambiguous backtest windows.
- 驗證：browser `/lab`、`curl http://127.0.0.1:8000/api/models/leaderboard`、`pytest tests/test_model_leaderboard.py tests/test_strategy_lab.py tests/test_frontend_decision_contract.py -q`

### P1. q15 exact support remains under minimum under breaker (11/50)
- 目前真相：`bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=11/50` / `gap=39` / `support_route_verdict=exact_bucket_present_but_below_minimum` / `governance_route=exact_live_lane_proxy_available`
- 下一步：Keep support_route_verdict/support_progress/minimum_support_rows/gap_to_minimum visible in probe/API/UI/docs even when circuit_breaker_active is the primary blocker.

---

## Current Priority
1. **維持 breaker-first truth，同時保留 q15 current-live bucket support rows 可 machine-read**
2. **持續沿 recent canonical pathological slice 追根因，不要 generic 化 blocker**
3. **守住 q15 current-live bucket support / reference-only patch、leaderboard dual-role governance、venue/source blockers 可見性**
4. **守住 operator-facing venue / account wording：public-only ≠ OK，缺 private creds ≠ 餘額未知**
