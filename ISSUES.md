# ISSUES.md — Current State Only

_最後更新：2026-04-21 13:19:21 CST_

只保留目前有效問題；current-state markdown 必須對齊最新 live artifacts、驗證證據與本輪已落地 patch。

---

## 當前主線事實
- **最新 fast heartbeat #20260421-1305 已完成 collect + diagnostics refresh**
  - `Raw=31360 / Features=22778 / Labels=63219`
  - `simulated_pyramid_win=57.21%`
- **canonical current-live blocker 仍是 exact-support truth**
  - `deployment_blocker=under_minimum_exact_live_structure_bucket`
  - `current_live_structure_bucket=CAUTION|structure_quality_caution|q35`
  - `support=12/50` / `gap=38` / `support_route_verdict=exact_bucket_present_but_below_minimum`
  - `runtime_closure_state=patch_active_but_execution_blocked`
- **operator-facing surfaces 已補齊 support route / governance route 同步 copy**
  - Dashboard、`/execution/status`、`/lab`、`LivePathologySummaryCard` 現在都同時顯示 `support_route_verdict` 與 `support_governance_route`
  - 驗證：`pytest tests/test_frontend_decision_contract.py tests/test_server_startup.py tests/test_strategy_lab.py -q` → `124 passed`
  - 驗證：`cd web && npm run build` ✅；browser `/`、`/execution/status`、`/lab` 均可看到 support/governance route 文案
- **recent canonical pathology 仍未解除**
  - `recent_100: win_rate=97.0% / dominant_regime=chop(88.0%) / alerts=label_imbalance,regime_shift`
  - `recent_500: win_rate=20.6% / dominant_regime=bull(76.0%) / interpretation=regime_concentration`
- **leaderboard / venue / source blockers 仍存在**
  - `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro`
  - venue runtime proof 仍缺：`live exchange credential / order ack lifecycle / fill lifecycle`
  - `fin_netflow=source_auth_blocked` / `COINGLASS_API_KEY missing`
- **fast heartbeat 在 candidate-eval lane 喚醒時仍可能超出 cron budget**
  - `heartbeat=20260421-1305` / `elapsed=68.9s` / `timed_out_lanes=['feature_group_ablation']`

---

## Open Issues

### P0. current live bucket CAUTION|structure_quality_caution|q35 exact support remains under minimum and is still the deployment blocker (12/50)
- 目前真相：`deployment_blocker=under_minimum_exact_live_structure_bucket` / `support=12/50` / `gap=38` / `runtime_closure_state=patch_active_but_execution_blocked`
- same-bucket truth：`support_route_verdict=exact_bucket_present_but_below_minimum` / `support_governance_route=exact_live_bucket_present_but_below_minimum` / `recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_until_exact_support_ready`
- 下一步：在 support 補滿 minimum rows 前，持續把 exact-support blocker 當唯一 current-live blocker；不得把 proxy rows、reference patch 或 breaker 舊敘事誤判成可部署。

### P0. recent canonical pathological slice still dominates root-cause work
- 目前真相：`recent_100=97.0% chop-heavy pathology`，但 `recent_500=20.6% bull-heavy regime concentration` 仍是主要風險敘事
- 病態訊號：`alerts=label_imbalance,regime_shift` / `tail_streak=97` / `low_variance=11` / `low_distinct=11` / `null_heavy=10`
- 下一步：沿 `recent_drift_report.py` + `hb_predict_probe.py` 追 feature variance / distinct-count / target-path / top-shift，不要退回 generic leaderboard 或 venue 摘要。

### P1. support-aware patch must stay reference-only, and support/governance route visibility must not regress
- 目前真相：operator surfaces 已同步顯示 `support_route_verdict` + `support_governance_route`；compact/full pathology cards 都已帶入同一組治理文案
- 驗證鎖：`124 passed` targeted pytest + `npm run build` + browser `/` `/execution/status` `/lab`
- 下一步：維持 `recommended_patch=core_plus_macro_plus_all_4h` 僅作 `reference_only_until_exact_support_ready`；若任一 surface 再丟失 support/governance route 或把 patch 誤升級成 deployable，即回升 P0。

### P1. venue readiness is still unverified
- 目前真相：`binance=config enabled + public-only + metadata OK` / `okx=config disabled + public-only + metadata OK`
- 缺口：`live exchange credential` / `order ack lifecycle` / `fill lifecycle` 尚未有 runtime-backed proof
- 下一步：在 Dashboard、`/execution/status`、`/lab` 保持 per-venue blockers 可見，直到三項 proof 全部補齊。

### P1. fast heartbeat still overruns cron budget when candidate-eval lane wakes up
- 目前真相：`elapsed_seconds=68.9` / `timed_out_lanes=['feature_group_ablation']`
- 下一步：把 `--fast` 嚴格限制在 collect / drift / probe / docs lanes；candidate / leaderboard refresh 必須更短 timeout 或改成 opt-in。

### P1. fin_netflow remains source_auth_blocked because COINGLASS_API_KEY is missing
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=2830` / `archive_window_coverage_pct=0.0`
- 下一步：補齊 `COINGLASS_API_KEY`，讓後續 heartbeat 把 `auth_missing` 快照替換成可用 ETF-flow rows。

### P1. leaderboard contract is healthy now, but must stay aligned with recent-window policy and support-aware governance
- 目前真相：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro` / `governance_contract=dual_role_governance_active`
- 下一步：維持 `/api/models/leaderboard` 與 Strategy Lab 的最近兩年 bounded walk-forward 合約，不可回退成 placeholder-only 或模糊 backtest window。

---

## Current Priority
1. **維持 exact-support blocker 為唯一 current-live blocker，直到 q35 support 12/50 補滿 50/50**
2. **持續沿 recent canonical pathological slice 追根因，不要 generic 化**
3. **守住 support/governance route 可見性與 reference-only patch 治理，不讓 UI / docs / probe 再分裂**
4. **把 fast heartbeat 壓回 cron-safe budget，避免 candidate lane 再拖垮 fast mode**
