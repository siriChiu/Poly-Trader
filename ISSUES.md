# ISSUES.md — Current State Only

_最後更新：2026-04-19 08:14 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **本輪 fast heartbeat `#20260419c` + collect 有真實資料前進**：`Raw=31074 (+2) / Features=22491 (+1) / Labels=62568 (+1)`；`240m` target rows 增至 `22385 (+1)`，`1440m` 仍屬 lookahead 預期 lag，不是 frozen pipeline。
- **本輪產品化 patch 已前進 operator UX**：Strategy Lab `/lab` 與 Dashboard execution summary 現在都直接顯示 per-venue readiness cards；browser `/lab` 已看到 `binance=config enabled + public-only`、`okx=config disabled + public-only`、`metadata OK`、`step/tick/min qty/min cost`、以及 `missing runtime proof`，browser console 無 JS exception。
- **canonical current-live 唯一 deployment blocker 仍是 circuit breaker**：`streak=238`、`recent 50 wins=0/50`、`additional_recent_window_wins_needed=15`、`allowed_layers=0`、`runtime_closure_state=circuit_breaker_active`。
- **current live bucket 仍是 q15 exact support 缺失**：`current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15`、`support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`、`live_current_structure_bucket_rows=0/50`、`gap_to_minimum=50`。
- **spillover patch 仍是 reference-only**：`bull|CAUTION` broader spillover `rows=200 / WR=0.0% / quality=-0.2945 / pnl=-1.09%`，`recommended_patch=core_plus_macro`，`status=reference_only_until_exact_support_ready`。
- **近期 canonical pathology 未改善**：recent `100` rows = `100x0`、`dominant_regime=bull(100%)`、`interpretation=distribution_pathology`、`avg_pnl=-0.0095`、`avg_quality=-0.2870`。
- **venue readiness 仍未 closure，但 visibility 已 productized**：`/lab`、Dashboard、`/execution/status` 都保留 venue blockers；缺的仍是 `live exchange credential / order ack lifecycle / fill lifecycle` runtime proof。
- **fin_netflow 仍是 source_auth_blocked**：latest snapshot `auth_missing`，`forward_archive_rows=2545`，`archive_window_coverage_pct=0.0%`，根因仍是 `COINGLASS_API_KEY` 缺失。

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
- 只要任何 surface 把 q15 support、spillover patch 或 venue blockers 排到 breaker 前面，operator 就會失去唯一 current-live blocker 真相。

**下一步**
- 維持 breaker-first truth 在 `hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`/lab`、`/execution/status`、`issues.json`、`ISSUES.md` 一致。
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
- 若 exact support 仍是 `0/50`，任何把 spillover patch 或 proxy cohort 誤包裝成 deployable patch 的 surface 都會製造假 closure。

**下一步**
- 維持 `0/50 + exact_bucket_missing_exact_lane_proxy_only + gap_to_minimum=50` 在 probe / API / UI / docs 四處一致。
- 驗證：`python scripts/hb_q15_support_audit.py`、`python scripts/hb_predict_probe.py`、browser `/lab`。

### P1. bull|CAUTION spillover patch must remain reference-only until exact support recovers
**現況**
- exact live lane：`0 rows`
- broader spillover：`bull|CAUTION 200 rows / WR=0.0% / quality=-0.2945 / pnl=-1.09%`
- `recommended_patch=core_plus_macro`
- `recommended_patch.status=reference_only_until_exact_support_ready`
- `collapse_features=feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`
- `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`
- `gap_to_minimum=50`

**風險**
- 若任何 surface 把 `reference_only` 誤升級成可部署 patch，current-live blocker 會再次被 broader spillover 假 closure 汙染。

**下一步**
- 維持同一份 `recommended_patch` 在 `/api/status`、`/lab`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、heartbeat summary 一致；只有 exact support 達標後才討論 runtime / training promotion。
- 驗證：`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、targeted pytest、browser `/lab`。

### P1. venue readiness is still unverified
**現況**
- `binance`: `config enabled + public-only`
- `okx`: `config disabled + public-only`
- `/lab` 與 Dashboard 已升級為 per-venue readiness cards；`/execution/status` 保留完整 venue diagnostics
- 缺的 runtime proof 仍是：`live exchange credential`、`order ack lifecycle`、`fill lifecycle`

**風險**
- 即使 breaker 未來解除，若 venue blockers 被弱化成單一字串或從 operator surface 消失，使用者會被誤導成已可實盤。

**下一步**
- 持續保留 per-venue cards 與 venue blockers，直到 credentials / ack / fill 都有 runtime-backed proof。
- 驗證：browser `/lab`、browser `/execution/status`、`data/execution_metadata_smoke.json`。

### P1. fin_netflow source_auth_blocked remains open
**現況**
- `fin_netflow`: `archive_required` + `latest_status=auth_missing`
- blocker 原因：`COINGLASS_API_KEY is missing`
- `forward_archive_rows=2545`
- `archive_window_coverage_pct=0.0%`

**風險**
- Feature coverage 會持續呈現假前進；heartbeat 只能看到 archive ready，但資料實際不可用。

**下一步**
- 配置 `COINGLASS_API_KEY`，讓 CoinGlass ETF flow source 先從 `auth_missing` 轉成成功 snapshots，再評估是否需要歷史 backfill。
- 驗證：`data/heartbeat_20260419c_summary.json` source blockers、`/api/features/coverage`。

---

## Not Issues
- **data pipeline frozen**：不是；本輪 fast heartbeat collect 實際新增 `+2 raw / +1 features / +1 labels`。
- **240m / 1440m freshness lag**：不是 blocker；目前仍屬 canonical lookahead horizon 的 expected lag。
- **spillover patch parity broken**：不是；probe / drilldown / `/lab` 仍維持 `recommended_patch=core_plus_macro` 的單一真相。
- **venue blockers 不可見**：不是；本輪已把 per-venue readiness cards productize 到 `/lab` 與 Dashboard。

---

## Current Priority
1. **維持 breaker-first truth，讓 current-live blocker 始終是 release math，而不是 support / spillover / venue 雜訊**
2. **維持 q15 support `0/50 + gap_to_minimum=50` 在 breaker path 下仍可 machine-read**
3. **維持 `recommended_patch=core_plus_macro` 的 reference-only semantics，不讓 broader spillover 假裝成 exact support closure**
4. **持續保留 per-venue readiness cards 與 venue blockers，直到 credentials / ack / fill 有 runtime proof**
5. **解除 `fin_netflow` 的 `source_auth_blocked`（COINGLASS_API_KEY）以避免 sparse-source 假前進**
