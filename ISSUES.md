# ISSUES.md — Current State Only

_最後更新：2026-04-23 12:55:30 CST_

只保留目前有效問題；由 heartbeat overwrite sync，避免 current-state markdown 落後 `issues.json` / live artifacts。

---

## 當前主線事實
- **本輪心跳 #20260423j 已完成 operator-facing blocker truth productization patch**
  - `/`、`/execution`、`/execution/status`、`/lab` 的主 blocker / runtime closure / routing 摘要已改走共用 humanizer，主卡片不再直接漏出 `exact_live_lane_toxic_sub_bucket_current_bucket`、`toxic sub-bucket`、`regime gate`、`blocks trade`
  - browser 驗證：Dashboard、Execution Status、Strategy Lab 主 blocker 區塊皆顯示中文 operator copy；console `0 JS errors`
  - 驗證：`pytest tests/test_frontend_decision_contract.py tests/test_execution_surface_contract.py tests/test_strategy_lab.py -q` → `123 passed`；`cd web && npm run build` → pass
- **資料基線沿用 fast heartbeat #20260423i**
  - `Raw=32031 / Features=23449 / Labels=64018`
  - 歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`
  - `simulated_pyramid_win=57.03%`
- **canonical current-live blocker 仍是 same toxic q15 bucket**
  - `deployment_blocker=exact_live_lane_toxic_sub_bucket_current_bucket`
  - `current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15` / `support=199/50` / `gap=0` / `support_route_verdict=exact_bucket_supported` / `support_governance_route=exact_live_bucket_supported`
  - `runtime_closure_state=deployment_guardrail_blocks_trade` / `entry_quality=0.4266` / `allowed_layers=0`
- **recent canonical diagnostics 已刷新到最新 artifact truth**
  - `latest_window=100` / `win_rate=97.0%` / `dominant_regime=bull(91.0%)` / `avg_quality=+0.6707` / `avg_pnl=+0.0224` / `alerts=label_imbalance,regime_concentration,regime_shift`
  - `blocking_window=1000` / `win_rate=41.7%` / `dominant_regime=bull(80.4%)` / `avg_quality=+0.1189` / `avg_pnl=+0.0030` / `alerts=regime_shift`
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=6` / `top_model=rule_baseline` / `selected_feature_profile=core_only`
  - `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- **source / venue blockers 仍開啟**
  - fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3501` / `archive_window_coverage_pct=0.0`
  - venue：`binance=config enabled + public-only + metadata OK` / `okx=config disabled + public-only + metadata OK`
  - 尚缺 runtime-backed proof：`live exchange credential` / `order ack lifecycle` / `fill lifecycle`

---

## Open Issues

### P0. current-live deployment blocker remains exact_live_lane_toxic_sub_bucket_current_bucket
- 目前真相：`bucket=BLOCK|bull_q15_bias50_overextended_block|q15` / `support=199/50` / `gap=0` / `runtime_closure_state=deployment_guardrail_blocks_trade`
- exact-lane pathology：`current bucket` 本身就是 toxic sub-bucket，`win_rate=0.0` / `quality=-0.2112`；support closure 不能誤讀成 deployment closure
- 本輪前進：operator-facing blocker copy 已在 Dashboard / Execution / Strategy Lab 對齊，沒有再讓 raw machine token 稀釋 blocker truth
- 下一步：沿 q15 bucket root-cause artifact 追 `feat_4h_bb_pct_b` counterfactual / 結構 component 校準，確認是否有合法跨到 q35 的路徑；若沒有，就維持 toxic bucket veto 為唯一 current-live blocker

### P0. recent canonical 1000-row pocket still shows bull regime concentration
- 目前真相：`window=1000` / `win_rate=41.7%` / `dominant_regime=bull(80.4%)` / `avg_quality=+0.1189` / `avg_pnl=+0.0030` / `alerts=regime_shift`
- blocker pocket：`tail_streak=3x0`，但更長的 adverse pocket 仍存在（`273x0`）；最新 top shift 轉成 `feat_vwap_dev / feat_4h_bias200 / feat_eye`
- 下一步：直接對 recent canonical 1000-row bull concentration pocket 做 variance / distinct-count / target-path drill-down；維持 decision-quality guardrails，避免 broader historical average 稀釋 toxic slice
- 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`

### P1. support-aware patch must stay visible but reference-only outside current live scope
- 目前真相：`recommended_patch=core_plus_macro_plus_all_4h` / `recommended_patch_status=reference_only_non_current_live_scope` / `reference_patch_scope=bull|CAUTION`
- 目前 exact support 已 closure，但 current live lane 仍是 `bull|BLOCK` toxic q15 bucket；patch 只能維持治理 / 訓練參考
- 下一步：守住 `/api/status`、Dashboard、Strategy Lab、Execution Status、probe、drilldown 的同一份 reference-only patch 語義

### P1. venue readiness is still metadata-only, not runtime-proven
- 目前真相：Binance / OKX metadata contract 正常，但仍是 `public-only`
- 下一步：在 credentials、order ack、fill lifecycle 有 runtime-backed proof 之前，持續把 venue blockers 放在 operator-facing surfaces

### P1. fin_netflow remains source_auth_blocked
- 目前真相：`COINGLASS_API_KEY` 缺失；`forward_archive_rows=3501` 但 `archive_window_coverage_pct=0.0`
- 下一步：補 key，讓 ETF-flow / fin_netflow 從 auth_missing 轉成有效 snapshot

### P1. leaderboard dual-role governance must remain stable
- 目前真相：`global winner=core_only`，`production profile=core_plus_macro_plus_all_4h`，這是治理分工，不是 parity drift
- 下一步：守住 `/api/models/leaderboard`、Strategy Lab、docs 與 probe 的 dual-role truth，不回退 placeholder-only

---

## Current Priority
1. **維持 toxic q15 bucket = 唯一 current-live blocker，避免任何舊 blocker / support 敘事回流**
2. **沿 recent canonical 1000-row bull concentration pocket 繼續追根因，不讓 broader average 稀釋 blocker**
3. **守住 reference-only patch、venue/source blockers、leaderboard dual-role governance 與 docs overwrite sync**
4. **把 operator-facing blocker truth 維持在 Dashboard / Execution / Strategy Lab 的中文產品語義，不回退 raw machine tokens**
