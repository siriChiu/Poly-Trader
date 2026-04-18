# ISSUES.md — Current State Only

_最後更新：2026-04-19 07:48 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **本輪 fast heartbeat + collect 有真實資料推進**：`Raw=31071 (+1) / Features=22489 (+1) / Labels=62567 (+2)`；`240m` 與 `1440m` label lag 仍是 lookahead 預期，不是資料管線停擺。
- **canonical current-live 唯一 deployment blocker 仍是 circuit breaker**：`streak=238`、`recent 50 wins=0/50`、`additional_recent_window_wins_needed=15`、`allowed_layers=0`。
- **current live bucket 仍是 q15 exact support 缺失**：`current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15`、`support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`、`0/50`、`gap_to_minimum=50`。
- **本輪產品化前進已 closure**：`bull|CAUTION` spillover 的 `recommended_patch=core_plus_macro` 現在已在 `/api/status`、Strategy Lab `/lab`、`scripts/hb_predict_probe.py`、`scripts/live_decision_quality_drilldown.py`、`data/live_decision_quality_drilldown.json`、`docs/analysis/live_decision_quality_drilldown.md` 同步 machine-read；狀態一致為 `reference_only_until_exact_support_ready`。
- **browser verify（本輪實測）**：`/lab` 已同時顯示 `current live blocker / venue blockers / recommended patch card / collapse features`；`/execution/status` 已維持 breaker-first truth、`support 0/50`、`binance public-only / okx public-only`；browser console 無 JS exception。
- **近期 canonical pathology 仍是 breaker 根因**：recent `100` rows = `100x0`、`dominant_regime=bull(100%)`、`interpretation=distribution_pathology`、`avg_quality=-0.2870`。
- **venue readiness 仍未 closure**：`binance=config enabled + public-only`、`okx=config disabled + public-only`；`live credential / order ack / fill lifecycle` 仍無 runtime proof。
- **sparse-source auth blocker 仍存在**：`fin_netflow` 仍是 `auth_missing`；`COINGLASS_API_KEY` 未配置，forward archive 只會累積 `auth_missing` snapshots。

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
**現況**
- `deployment_blocker=circuit_breaker_active`
- `recent_window=50`
- `current_recent_window_wins=0`
- `required_recent_window_wins=15`
- `additional_recent_window_wins_needed=15`
- `streak=238`
- `allowed_layers=0`
- `runtime_closure_state=circuit_breaker_active`

**風險**
- 若任何 surface 再把 q15 support、spillover patch 或 venue blockers 排到 breaker 前面，operator 會失去唯一 blocker 真相。

**下一步**
- 維持 breaker-first truth 在 `/lab`、`/execution/status`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`issues.json`、`ISSUES.md` 一致。
- 驗證：`python scripts/hb_predict_probe.py`、browser `/lab`、browser `/execution/status`。

### P1. q15 exact support remains 0/50 and stalled under breaker
**現況**
- `current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15`
- `live_current_structure_bucket_rows=0`
- `minimum_support_rows=50`
- `gap_to_minimum=50`
- `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`
- `support_progress.status=stalled_under_minimum`
- `leaderboard_selected_profile=core_only`
- `train_selected_profile=core_plus_macro`
- `governance_contract=dual_role_governance_active`

**風險**
- 即使 spillover patch 已 productized，若 exact support 仍是 `0/50`，任何把 reference patch 誤讀成 deployable patch 的 surface 都會製造假 closure。

**下一步**
- 維持 `0/50 + exact_bucket_missing_exact_lane_proxy_only + gap_to_minimum=50` 在 probe / API / UI / docs 四處一致。
- 驗證：`python scripts/hb_q15_support_audit.py`、`python scripts/hb_predict_probe.py`、browser `/lab`。

### P1. bull|CAUTION spillover patch parity is done, but the patch must remain reference-only until exact support recovers
**現況**
- exact live lane：`0 rows`
- broader spillover：`bull|CAUTION 200 rows / WR=0.0% / quality=-0.2945 / pnl=-1.09%`
- `recommended_patch=core_plus_macro`
- `recommended_patch.status=reference_only_until_exact_support_ready`
- `collapse_features=feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`
- `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`
- `gap_to_minimum=50`

**風險**
- 若 probe / drilldown / docs 又退回只剩 diagnostics，或把 `reference_only` 誤升級成 deployable patch，operator 會再次看到雙真相。

**下一步**
- 維持同一份 `recommended_patch` 在 `/api/status`、`/lab`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、heartbeat summary 一致；只有 exact support 達標後才討論 runtime / training promotion。
- 驗證：`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、targeted pytest、browser `/lab`。

### P1. venue readiness is still unverified
**現況**
- `binance`: config enabled，但仍是 `public-only`
- `okx`: config disabled，且仍是 `public-only`
- `live exchange credential / order ack lifecycle / fill lifecycle` 都尚未驗證

**風險**
- 即使 breaker 未來解除，若 venue blockers 比 runtime artifact 更快消失，operator 會被誤導成已可實盤。

**下一步**
- 持續把 venue blockers 保留在 `/lab` 與 `/execution/status`，直到 credentials / ack / fill 都有 runtime proof。
- 驗證：browser `/lab`、browser `/execution/status`、`data/execution_metadata_smoke.json`。

### P1. fin_netflow source_auth_blocked remains open
**現況**
- `fin_netflow`: `archive_required` + `latest_status=auth_missing`
- blocker 原因：`COINGLASS_API_KEY is missing`
- forward archive 雖持續累積，但目前只會記錄 `auth_missing` snapshots

**風險**
- feature coverage 會一直呈現假前進；heartbeat 只能反覆看到 archive ready，但資料實際不可用。

**下一步**
- 配置 `COINGLASS_API_KEY`，讓 CoinGlass ETF flow source 先從 `auth_missing` 轉成成功 snapshots，再評估是否需要歷史 backfill。
- 驗證：`data/heartbeat_fast_summary.json` source blockers、`/api/features/coverage`。

---

## Not Issues
- **data pipeline frozen**：不是；本輪 fast heartbeat collect 實際新增 `+1 raw / +1 features / +2 labels`。
- **spillover patch 仍只存在 API / UI**：不是；本輪 probe / drilldown / docs parity 已 closure。
- **240m / 1440m freshness lag**：不是 blocker；目前仍屬 canonical lookahead horizon 的 expected lag。

---

## Current Priority
1. **維持 breaker-first truth，讓 current-live blocker 始終是 release math，而不是 support / spillover / venue 雜訊**
2. **維持 q15 support `0/50 + gap_to_minimum=50` 在 breaker path 下仍可 machine-read**
3. **維持 `recommended_patch=core_plus_macro` 在 API / UI / probe / drilldown / docs 的單一真相，且嚴格保持 `reference_only_until_exact_support_ready`**
4. **持續保留 venue blockers，直到 credentials / ack / fill 都有 runtime proof**
5. **解除 `fin_netflow` 的 `source_auth_blocked`（COINGLASS_API_KEY）以避免 sparse-source 假前進**
