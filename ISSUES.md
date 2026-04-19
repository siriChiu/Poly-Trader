# ISSUES.md — Current State Only

_最後更新：2026-04-19 09:36 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **fast heartbeat `#20260419h` + collect 成功**：`Raw=31081 (+1) / Features=22499 (+1) / Labels=62573 (+1)`；`240m` 與 `1440m` freshness 仍屬 lookahead 預期 lag，資料管線不是 frozen。
- **本輪產品化 patch 已修復 current-state issue drift**：`scripts/auto_propose_fixes.py` 現在會優先用 `live_predict_probe.json` 的 `support_route_verdict` 改寫 canonical q15 issue，並把 `current_live_structure_bucket / current_live_structure_bucket_rows / gap_to_minimum / runtime_closure_state` 回寫到 breaker issue；`issues.json` 不再停在上一輪的 bull q15 bucket 與錯誤 route。
- **canonical current-live 唯一 deployment blocker 仍是 circuit breaker**：`deployment_blocker=circuit_breaker_active`、`streak=240`、`recent 50 wins=0/50`、`additional_recent_window_wins_needed=15`、`allowed_layers=0`、`runtime_closure_state=circuit_breaker_active`。
- **current live bucket 已切到 `CAUTION|base_caution_regime_or_bias|q15`**：`regime=chop`、`gate=CAUTION`、`entry_quality=0.3948 (D)`；q15 exact support 目前 `0/50`，`support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`，`support_governance_route=exact_live_bucket_proxy_available`，`support_progress.status=no_recent_comparable_history`。
- **live decision-quality pathology 仍嚴重**：exact live lane `rows=0`；broader spillover 為 `bull|BLOCK` 且 `199 rows / WR 0.0% / 品質 -0.285 / PnL -1.00%`；recent canonical `100` rows 仍是 `100x0`、`dominant_regime=bull(100%)`、`interpretation=distribution_pathology`。
- **venue readiness truth 仍可見但未 closure**：`/lab` 與 `/execution/status` 都能看到 `current live blocker`、`support 0 / 50`、Binance/OKX per-venue readiness 與 `metadata OK`；缺的仍是 `live exchange credential / order ack lifecycle / fill lifecycle` proof。
- **fin_netflow 仍是 source_auth_blocked**：CoinGlass ETF flow 仍因 `COINGLASS_API_KEY` 缺失而 `auth_missing`；forward archive 已持續累積（>2550 snapshots），但 coverage 仍是 `0.0%`。

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
**現況**
- `deployment_blocker=circuit_breaker_active`
- `recent_window=50`
- `current_recent_window_wins=0`
- `required_recent_window_wins=15`
- `additional_recent_window_wins_needed=15`
- `streak=240`
- `allowed_layers=0`
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`
- `runtime_closure_state=circuit_breaker_active`

**風險**
- 只要任何 surface 把 q15 support / spillover / venue blockers 排到 breaker 前面，operator 就會失去唯一 current-live blocker 真相。

**下一步**
- 維持 breaker-first truth 在 `hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`/lab`、`/execution/status`、`issues.json`、`ISSUES.md` 一致。
- 驗證：`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、browser `/lab`、browser `/execution/status`。

### P1. q15 exact support remains under minimum under breaker
**現況**
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`
- `live_current_structure_bucket_rows=0`
- `minimum_support_rows=50`
- `gap_to_minimum=50`
- `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`
- `support_governance_route=exact_live_bucket_proxy_available`
- `support_progress.status=no_recent_comparable_history`
- `leaderboard_selected_profile=core_only`
- `train_selected_profile=core_plus_macro`
- `governance_contract=dual_role_governance_active`

**風險**
- 若 probe / docs / issues 只剩 generic `under minimum`，卻看不到 `exact bucket missing` 與 `proxy available` 的分離語義，operator 會誤判成可直接拿 proxy lane 當部署 closure。

**下一步**
- 維持 `0/50 + exact_bucket_missing_exact_lane_proxy_only + exact_live_bucket_proxy_available` 在 probe / API / UI / docs / `issues.json` 一致 machine-read。
- 驗證：`python scripts/hb_q15_support_audit.py`、`python scripts/hb_predict_probe.py`、browser `/lab`、browser `/execution/status`。

### P1. exact-live-lane vs broader spillover truth must stay visible
**現況**
- exact live lane：`rows=0`、`current bucket=CAUTION|base_caution_regime_or_bias|q15`
- broader spillover：`bull|BLOCK`、`199 rows`、`WR 0.0%`、`avg_quality=-0.2853`、`avg_pnl=-1.00%`
- top 4H shifts：`feat_4h_bias200`、`feat_4h_dist_bb_lower`、`feat_4h_dist_swing_low`
- current live pathology summary **沒有** bull-specific reference patch；舊的 `core_plus_macro reference-only` 敘事已不是 current-live truth

**風險**
- 若 UI / docs 再把 exact lane 與 bull spillover 混成單一 current-live 真相，就會把 broader toxic rows 誤包裝成 current q15 bucket 根因或補丁依據。

**下一步**
- 維持 `exact live lane rows=0` 與 `bull|BLOCK spillover=199 rows` 在 `live_decision_quality_drilldown.py`、`/lab`、`/execution/status` 一致可見。
- 驗證：`python scripts/live_decision_quality_drilldown.py`、browser `/lab`、browser `/execution/status`。

### P1. venue readiness is still unverified
**現況**
- `binance`: `config enabled + public-only`
- `okx`: `config disabled + public-only`
- `/lab`、Dashboard、`/execution/status` 都可見 per-venue readiness truth
- 缺的 runtime proof 仍是：`live exchange credential`、`order ack lifecycle`、`fill lifecycle`

**風險**
- breaker 未來解除後，若 venue blockers 被弱化成單一摘要字串，使用者會被誤導成已可實盤。

**下一步**
- 持續保留 per-venue cards 與 venue blockers，直到 credentials / ack / fill 都有 runtime-backed proof。
- 驗證：browser `/lab`、browser `/execution/status`、`data/execution_metadata_smoke.json`。

### P1. fin_netflow source_auth_blocked remains open
**現況**
- `fin_netflow`: `source_auth_blocked`
- `latest_status=auth_missing`
- blocker 根因：`COINGLASS_API_KEY is missing`
- forward archive 已持續累積，但 `archive_window_coverage_pct=0.0%`

**風險**
- Feature coverage 會持續呈現假前進：archive 在長、但 live fetch 仍失敗，資料實際不可用。

**下一步**
- 配置 `COINGLASS_API_KEY`，先讓 ETF flow source 從 `auth_missing` 轉成成功 snapshot，再評估是否需要歷史 backfill。
- 驗證：`data/heartbeat_20260419h_summary.json` source blockers、`/api/features/coverage`。

### P1. model stability and live DQ robustness still need work
**現況**
- `cv_accuracy=60.8%`
- `cv_std=12.5pp`
- `cv_worst=44.5%`
- live path 仍落在 `label=D / layers=0`

**風險**
- 即使 breaker 未來解除，若 profile robustness 沒改善，runtime 仍只會把 current bucket 壓回 0 layers。

**下一步**
- 優先比較 shrinkage / support-aware profiles 與 current bucket robustness，避免把治理 blocker 誤當單純 parity 問題。
- 驗證：`data/leaderboard_feature_profile_probe.json`、`data/bull_4h_pocket_ablation.json`、`data/live_predict_probe.json`。

---

## Not Issues
- **data pipeline frozen**：不是；本輪 collect 實際新增 `+1 raw / +1 features / +1 labels`。
- **240m / 1440m freshness lag**：不是 blocker；目前仍屬 lookahead horizon 的 expected lag。
- **上一輪 bull q15 `1/50 + core_plus_macro reference-only patch`**：不是 current truth；目前 current live bucket 已切到 `chop + CAUTION + q15`，support 回到 `0/50`，live pathology summary 也不再帶 bull-specific patch。
- **browser runtime regression**：不是；本輪 `/lab` 與 `/execution/status` 均能看到 breaker-first truth、support `0 / 50`、venue blockers，且無 JS exception。

---

## Current Priority
1. **維持 breaker-first truth，讓 current-live blocker 始終是 release math，而不是 q15/support/spillover/venue 雜訊**
2. **維持 q15 `0/50 + exact_bucket_missing_exact_lane_proxy_only + exact_live_bucket_proxy_available` 在 breaker path 下仍完整 machine-read**
3. **維持 exact live lane `0 rows` vs `bull|BLOCK spillover 199 rows` 的對照，不讓 broader toxic pocket 汙染 current-live 敘事**
4. **持續保留 per-venue readiness cards 與 venue blockers，直到 credentials / ack / fill 有 runtime proof**
5. **解除 `fin_netflow` 的 `source_auth_blocked`（COINGLASS_API_KEY）以避免 sparse-source 假前進**
