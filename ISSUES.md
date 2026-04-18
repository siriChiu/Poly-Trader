# ISSUES.md — Current State Only

_最後更新：2026-04-19 06:02 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **本輪 fast heartbeat + collect 仍有真實資料推進**：`Raw=31064 (+1) / Features=22482 (+1) / Labels=62538 (+15)`；`240m` 與 `1440m` freshness 仍屬 `expected_horizon_lag`，不是資料管線停擺。
- **current-state issue governance 已修正**：`scripts/issues.py` 現在會把 canonical issue 與等價 auto issue 去重合併；`issues.json` 不再同時保留 `P0_circuit_breaker_active` + `#H_AUTO_CIRCUIT_BREAKER`、`P1_q15_exact_support_stalled_under_breaker` + `#H_AUTO_CURRENT_BUCKET_SUPPORT` 兩套重複 blocker。
- **Strategy Lab / Execution Status 本輪再次 browser verify**：`/lab` 與 `/execution/status` 都顯示 breaker-first truth、q15 support `0/50`、venue blockers，browser console `0 errors`。
- **current-live 唯一 deployment blocker 仍是 canonical circuit breaker**：`recent 50 wins=0/50`、`additional_recent_window_wins_needed=15`、`streak=236`、`allowed_layers=0`。
- **current live bucket 仍是 q15 exact support 缺失**：`current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15`、`live_current_structure_bucket_rows=0/50`、`support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`、`support_progress=stalled_under_minimum`。
- **broader spillover 真相仍是 bull|CAUTION toxic pocket**：`200 rows / WR=0.0% / quality=-0.295 / pnl=-1.09%`；exact live lane 仍 `0 rows`，不能再拿 spillover 當成 exact live 代理放行。
- **venue readiness 仍未 closure**：`binance=config enabled + public-only`、`okx=config disabled + public-only`；`live exchange credential / order ack lifecycle / fill lifecycle` 都還沒有 runtime proof。

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
**現況**
- `deployment_blocker=circuit_breaker_active`
- `recent_window=50`
- `current_recent_window_wins=0`
- `required_recent_window_wins=15`
- `additional_recent_window_wins_needed=15`
- `streak=236`
- `allowed_layers=0`

**風險**
- 若任何 surface 再把 q15 support、spillover 或 venue blockers 放到 breaker 前面，operator 會再次失去唯一 blocker 真相。

**下一步**
- 維持 breaker-first truth 在 `/lab`、`/execution/status`、`hb_predict_probe.py`、`issues.json`、`ISSUES.md` 一致。
- 驗證：`python scripts/hb_predict_probe.py`、browser `/lab`、browser `/execution/status`。

### P1. q15 exact support remains 0/50 and stalled, but support-aware governance is visible under breaker
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
- 若 breaker path 下 support metadata 又被遮蔽成空值或舊敘事，current bucket 治理會再次失真。

**下一步**
- 維持 `0/50 + stalled_under_minimum + exact_live_lane_proxy_available` 在 probe / API / UI / docs 四處一致。
- 驗證：`python scripts/hb_q15_support_audit.py`、`python scripts/hb_predict_probe.py`、browser `/lab` 治理卡。

### P1. broader `bull|CAUTION` spillover pathology is still open
**現況**
- exact live lane：`0 rows`
- broader spillover：`bull|CAUTION 200 rows / WR=0.0% / quality=-0.295 / pnl=-1.09%`
- recent pathology：`100x0` canonical tail
- shared shifts：`feat_4h_dist_bb_lower / feat_4h_bb_pct_b / feat_4h_dist_swing_low`

**風險**
- 若這個 broader same-regime toxic pocket 仍只停留在 drilldown 報告，系統會卡在 fail-close blocker，沒有正式的 gate / calibration / training 修復路徑。

**下一步**
- 把 `bull|CAUTION` pocket 轉成可重跑的 gate/calibration/training patch，而不是只停留在可視化。
- 驗證：`data/live_decision_quality_drilldown.json`、`python scripts/hb_predict_probe.py`、targeted pytest、browser `/lab` 的 `🧬 Live lane / spillover 對照`。

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

---

## Not Issues
- **data pipeline frozen**：不是；本輪 collect 實際新增 `+1 raw / +1 features / +15 labels`。
- **Strategy Lab / Execution Status blocker truth 缺失**：不是；本輪 browser verify 已看到 `circuit_breaker_active`、`support 0/50`、`venue blockers`、`bull|CAUTION spillover`，且 console `0 errors`。
- **issues.json current-state 被重複 auto issue 汙染**：本輪已修正；canonical breaker / support issue 會吸收等價 auto issue，不再雙寫。

---

## Current Priority
1. **維持 breaker-first truth，讓 current-live blocker 始終是 release math，而不是 support / spillover / venue 雜訊**
2. **維持 q15 support `0/50 + stalled_under_minimum` 在 breaker path 下仍可 machine-read**
3. **把 `bull|CAUTION` 200-row toxic pocket 轉成正式 gate/calibration/training patch**
4. **持續保留 venue blockers，直到 credentials / ack / fill 都有 runtime proof**
