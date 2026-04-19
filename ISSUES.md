# ISSUES.md — Current State Only

_最後更新：2026-04-19 10:01 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **fast heartbeat `#20260419j` + collect 成功**：`Raw=31084 (+1) / Features=22502 (+1) / Labels=62576 (+1)`；`240m` 與 `1440m` freshness 仍屬 lookahead 預期 lag，資料管線不是 frozen。
- **本輪產品化 patch 已修復 breaker streak current-state drift**：`scripts/auto_propose_fixes.py` 移除 `_latest_zero_streak()` 的硬編碼 `LIMIT 200`，並改成 `timestamp DESC, id DESC` 對齊 `hb_circuit_breaker_audit.py`；`#H_AUTO_STREAK` 與 auto-propose 摘要不再卡在假 `200`，本輪已正確刷新為 **241**。
- **canonical current-live 唯一 deployment blocker 仍是 circuit breaker**：`deployment_blocker=circuit_breaker_active`、`streak=241`、`recent 50 wins=0/50`、`additional_recent_window_wins_needed=15`、`allowed_layers=0`、`runtime_closure_state=circuit_breaker_active`。
- **current live bucket 現在是 `BLOCK|bull_q15_bias50_overextended_block|q15`**：`regime=bull`、`gate=BLOCK`、`entry_quality=0.4135 (D)`；q15 exact support 目前 **1/50**，`gap_to_minimum=49`，`support_route_verdict=exact_bucket_present_but_below_minimum`。
- **live decision-quality truth 已是 exact-lane 與 spillover 分離**：`exact_live_lane rows=199 / WR 0.0% / 品質 -0.2855`；同 regime spillover 僅 `1 row / WR 0.0% / 品質 -0.314`；`recommended_patch=core_plus_macro` 仍是 `reference_only_until_exact_support_ready`，不可當成 runtime closure。
- **venue readiness truth 已在 operator surface 可見**：browser 實測 `/lab` 與 `/execution/status` 都顯示 breaker-first truth、q15 support `1/50`、Binance/OKX per-venue cards、以及 `live exchange credential / order ack lifecycle / fill lifecycle` 缺口；本輪未觀察到 JS exception。
- **fin_netflow 仍是 source_auth_blocked**：CoinGlass ETF flow 仍因 `COINGLASS_API_KEY` 缺失而 `auth_missing`；forward archive 已累積 `2555` snapshots，但 `archive_window_coverage_pct=0.0%`。

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
**現況**
- `deployment_blocker=circuit_breaker_active`
- `recent_window=50`
- `current_recent_window_wins=0`
- `required_recent_window_wins=15`
- `additional_recent_window_wins_needed=15`
- `streak=241`
- `allowed_layers=0`
- `current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15`
- `runtime_closure_state=circuit_breaker_active`

**風險**
- 只要任何 surface 把 q15/support/spillover/venue blocker 排到 breaker 前面，operator 就會失去唯一 current-live blocker 真相。

**下一步**
- 維持 breaker-first truth 在 `hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`/lab`、`/execution/status`、`issues.json`、`ISSUES.md` 一致。
- 驗證：`python scripts/hb_parallel_runner.py --fast --hb <N>`、`python scripts/hb_predict_probe.py`、browser `/lab`、browser `/execution/status`。

### P0. auto-propose streak math must stay aligned with canonical breaker math
**現況**
- 本輪已修復：`scripts/auto_propose_fixes.py::_latest_zero_streak()` 不再被 `LIMIT 200` 截斷。
- auto-propose / `issues.json` / heartbeat summary 現在與 `hb_circuit_breaker_audit.py` 對齊為 `streak=241`。
- regression tests 已覆蓋：超過 200 筆 streak、以及 timestamp-vs-insert-order 對齊。

**風險**
- 若這條對齊再次回退，current-state docs 會重新低報 breaker 嚴重度，讓 release math 與 issue tracker 分裂。

**下一步**
- 固定保留 regression tests，並在每輪 heartbeat 檢查 `#H_AUTO_STREAK` 是否與 `live_predict_probe.streak` / `circuit_breaker_audit.aligned_scope.release_condition.current_streak` 一致。
- 驗證：`pytest tests/test_auto_propose_fixes.py -q`、`python scripts/auto_propose_fixes.py`。

### P1. q15 exact support remains under minimum under breaker
**現況**
- `current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15`
- `live_current_structure_bucket_rows=1`
- `minimum_support_rows=50`
- `gap_to_minimum=49`
- `support_route_verdict=exact_bucket_present_but_below_minimum`
- `support_progress.status=stalled_under_minimum`
- `leaderboard_selected_profile=core_only`
- `train_selected_profile=core_plus_macro`
- `governance_contract=dual_role_governance_active`

**風險**
- 若 probe / docs / issues 只剩 generic `under minimum`，卻看不到 current bucket 已是 `bull_q15_bias50_overextended_block|q15` 與 `1/50` 的 machine-read truth，operator 會誤判 support 已 closure。

**下一步**
- 維持 `1/50 + exact_bucket_present_but_below_minimum + stalled_under_minimum` 在 probe / API / UI / docs / `issues.json` 一致 machine-read。
- 驗證：`python scripts/hb_q15_support_audit.py`、`python scripts/hb_predict_probe.py`、browser `/lab`、browser `/execution/status`。

### P1. exact live lane vs broader spillover truth must stay visible
**現況**
- exact live lane：`rows=199`、`WR=0.0%`、`quality=-0.2855`、`current bucket rows=1`
- broader spillover：`bull|BLOCK`、`1 row`、`WR=0.0%`、`quality=-0.314`
- top 4H shifts：`feat_4h_bias200`、`feat_4h_dist_swing_low`、`feat_4h_dist_bb_lower`
- `recommended_patch=core_plus_macro` 仍是 `reference_only_until_exact_support_ready`

**風險**
- 若 UI / docs 再把 exact lane 與 1-row spillover 混成單一 current-live 真相，會把 broader reference patch 誤包裝成 current bucket runtime closure。

**下一步**
- 維持 `/lab`、`/execution/status`、`live_decision_quality_drilldown.py` 對 exact lane / spillover / patch reference 的一致敘事。
- 驗證：`python scripts/live_decision_quality_drilldown.py`、browser `/lab`、browser `/execution/status`。

### P1. venue readiness is still unverified
**現況**
- `binance`: `config enabled + public-only`
- `okx`: `config disabled + public-only`
- `/lab`、`/execution/status` 已可見 per-venue readiness truth
- 缺的 runtime proof 仍是：`live exchange credential`、`order ack lifecycle`、`fill lifecycle`

**風險**
- breaker 未來解除後，若 venue blockers 被弱化成摘要字串，使用者會被誤導成已可實盤。

**下一步**
- 持續保留 per-venue cards 與 venue blockers，直到 credentials / ack / fill 都有 runtime-backed proof。
- 驗證：browser `/lab`、browser `/execution/status`、`data/execution_metadata_smoke.json`。

### P1. fin_netflow source_auth_blocked remains open
**現況**
- `fin_netflow`: `source_auth_blocked`
- `latest_status=auth_missing`
- blocker 根因：`COINGLASS_API_KEY is missing`
- `forward_archive_rows=2555`
- `archive_window_coverage_pct=0.0%`

**風險**
- Feature coverage 會持續呈現假前進：archive 在長、但 live fetch 仍失敗，資料實際不可用。

**下一步**
- 配置 `COINGLASS_API_KEY`，先讓 ETF flow source 從 `auth_missing` 轉成成功 snapshot，再評估是否需要歷史 backfill。
- 驗證：`data/heartbeat_20260419j_summary.json` source blockers、`/api/features/coverage`。

### P1. model stability and live DQ robustness still need work
**現況**
- `cv_accuracy=60.8%`
- `cv_std=12.5pp`
- `cv_worst=44.5%`
- live path 仍落在 `label=D / layers=0`
- recent pathology：`100x0`、`distribution_pathology`、`dominant_regime=bull(100%)`

**風險**
- 即使 breaker 未來解除，若 profile robustness 沒改善，runtime 仍只會把 current bucket 壓回 0 layers。

**下一步**
- 優先比較 shrinkage / support-aware profiles 與 current bucket robustness，避免把治理 blocker 誤當單純 parity 問題。
- 驗證：`data/leaderboard_feature_profile_probe.json`、`data/bull_4h_pocket_ablation.json`、`data/live_predict_probe.json`。

---

## Not Issues
- **data pipeline frozen**：不是；本輪 collect 實際新增 `+1 raw / +1 features / +1 labels`。
- **240m / 1440m freshness lag**：不是 blocker；目前仍屬 lookahead horizon 的 expected lag。
- **`#H_AUTO_STREAK=200`**：不是 current truth；本輪已修復 auto-propose streak truncation，current truth 是 `241`。
- **舊的 `q15 0/50 + exact_bucket_missing_exact_lane_proxy_only`**：不是本輪 current truth；目前 current live bucket 是 `BLOCK|bull_q15_bias50_overextended_block|q15`，support 已進到 `1/50`。
- **browser runtime regression**：不是；本輪 `/lab` 與 `/execution/status` 均可見 breaker-first truth、support `1/50`、venue blockers，且未觀察到 JS exception。

---

## Current Priority
1. **維持 breaker-first truth，讓 current-live blocker 始終是 release math，而不是 q15/support/spillover/venue 雜訊**
2. **維持 q15 `1/50 + exact_bucket_present_but_below_minimum + stalled_under_minimum` 的單一 machine-read 真相**
3. **維持 exact live lane `199 rows` vs spillover `1 row` 與 `core_plus_macro reference-only` patch 可見，不讓 broader reference 汙染 current-live 敘事**
4. **持續保留 per-venue readiness cards 與 venue blockers，直到 credentials / ack / fill 有 runtime proof**
5. **解除 `fin_netflow` 的 `source_auth_blocked`（COINGLASS_API_KEY）以避免 sparse-source 假前進**
