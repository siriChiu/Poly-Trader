# ISSUES.md — Current State Only

_最後更新：2026-04-19 05:16 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **fast heartbeat + collect 本輪成功推進資料面**：`Raw=31062 (+2) / Features=22480 (+2) / Labels=62495 (+27)`；`240m` 與 `1440m` label freshness 都屬於 `expected_horizon_lag`，不是資料管線停擺。
- **Strategy Lab 的 live deployment sync 已完成 blocker split 產品化**：`/lab` 現在分開顯示 `current live blocker` 與 `venue blockers`；瀏覽器驗證看到 `circuit_breaker_active` 與 `live exchange credential / order ack / fill lifecycle` 兩條真相並存，console `0 errors`。
- **breaker path 下的 q15 support-aware governance 已可見**：`hb_predict_probe.py`、`/api/status`、`/lab` 目前都保留 `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only` 與 `support_progress={status=stalled_under_minimum,current_rows=0,minimum_support_rows=50,gap_to_minimum=50,delta_vs_previous=0}`，不再被 breaker 提前遮蔽成空值或舊敘事。
- **current-live 唯一 deployment blocker 仍是 canonical circuit breaker**：`recent 50 wins=0/50`、`additional_recent_window_wins_needed=15`、`streak=235`、`allowed_layers=0`。
- **current live bucket 仍是 q15 exact support 缺失**：`current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15`、`live_current_structure_bucket_rows=0/50`、`support_progress=stalled_under_minimum`。
- **governance split 仍是健康雙角色，而不是 parity drift**：`leaderboard_selected_profile=core_only`、`train/runtime_selected_profile=core_plus_macro`、`governance_contract=dual_role_governance_active`。
- **當前 spillover 真相是 broader `bull|CAUTION` toxic pocket**：`200 rows / WR=0.0% / quality=-0.295 / pnl=-1.10%`；exact live lane `0 rows`，不能再沿用舊的 `41-row exact lane` 敘事。
- **venue readiness 仍未 closure**：`live exchange credential 尚未驗證 · order ack lifecycle 尚未驗證 · fill lifecycle 尚未驗證`。

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
**現況**
- `deployment_blocker=circuit_breaker_active`
- `recent_window=50`
- `current_recent_window_wins=0`
- `required_recent_window_wins=15`
- `additional_recent_window_wins_needed=15`
- `streak=235`
- `allowed_layers=0`

**風險**
- 若任何 surface 把 q15 support、spillover 或 floor-gap 擺到 breaker 前面，operator 會再次失去唯一 blocker 真相。

**下一步**
- 維持 breaker-first truth 在 `/lab`、`/execution/status`、`hb_predict_probe.py` 與 current-state docs 一致。
- 驗證：`venv/bin/python scripts/hb_predict_probe.py`、瀏覽器 `/lab`、瀏覽器 `/execution/status`。

### P1. q15 exact support remains 0/50 and stalled, but support-aware governance is now visible under breaker
**現況**
- `current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15`
- `live_current_structure_bucket_rows=0`
- `minimum_support_rows=50`
- `gap_to_minimum=50`
- `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`
- `support_progress.status=stalled_under_minimum`
- `support_progress.delta_vs_previous=0`
- `support_progress.stagnant_run_count=2`
- `dual_profile_state=leaderboard_global_winner_vs_train_support_fallback`
- `leaderboard_selected_profile=core_only`
- `train_selected_profile=core_plus_macro`

**風險**
- 若 docs / API / UI 又回退成只講 breaker 而不講 support route，下一輪會再次出現 stale support 敘事或把健康的雙角色治理誤報成 parity drift。

**下一步**
- 維持 `0/50 + stalled_under_minimum + exact_live_lane_proxy_available` 在 probe / status / lab / docs 四處一致。
- 驗證：`venv/bin/python scripts/hb_q15_support_audit.py`、`venv/bin/python scripts/hb_predict_probe.py`、瀏覽器 `/lab` 治理卡。

### P1. broader `bull|CAUTION` spillover pathology is still open
**現況**
- exact live lane：`0 rows`
- broader spillover：`bull|CAUTION 200 rows / WR=0.0% / quality=-0.295 / pnl=-1.10%`
- recent pathology：`100x0` constant-target bull tail
- shared shifts：`feat_4h_dist_bb_lower / feat_4h_bb_pct_b / feat_4h_dist_swing_low`

**風險**
- 若不把這個 broader same-regime toxic pocket 轉成正式 gate / calibration / training patch，系統只能停在 fail-close blocker，無法形成可部署修復路徑。

**下一步**
- 直接把 `bull|CAUTION` pocket 做成可重跑的 gate/calibration patch，而不是只停留在 drilldown 可視化。
- 驗證：`data/live_decision_quality_drilldown.json`、`venv/bin/python scripts/hb_predict_probe.py`、targeted pytest、瀏覽器 `/lab` 的 `🧬 Live lane / spillover 對照`。

### P1. venue readiness is still unverified
**現況**
- live exchange credential 未驗證
- order ack lifecycle 未驗證
- fill lifecycle 未驗證

**風險**
- 即使 breaker 未來解除，若 venue blockers 消失得比 runtime artifact 更快，operator 會被誤導成已可實盤。

**下一步**
- 持續把 venue blockers 保留在 `/lab` 與 `/execution/status`，直到 credentials / ack / fill 都有 runtime proof。
- 驗證：瀏覽器 `/lab`、瀏覽器 `/execution/status`、`data/execution_metadata_smoke.json`。

---

## Not Issues
- **Strategy Lab hover 百分比誤顯示**：不是；本輪瀏覽器驗證 `/lab` hover 顯示為 `64.3% / 33.9% / 84.5%`，不再出現 `6425% / 3385% / 8451%`。
- **Strategy Lab live blocker 被 venue blockers 淹沒**：不是；本輪已改成 `current live blocker` 與 `venue blockers` 分卡顯示並完成 browser verify。
- **data pipeline frozen**：不是；本輪 collect 實際新增 `+2 raw / +2 features / +27 labels`。

---

## Current Priority
1. **維持 breaker-first truth，且在 `/lab` / `/execution/status` 清楚分開 current live blocker 與 venue blockers**
2. **維持 `q15 support 0/50 + stalled_under_minimum` 在 breaker path 下仍可 machine-read**
3. **把 `bull|CAUTION` 200-row toxic pocket 轉成正式 gate/calibration/training patch**
4. **持續保留 venue blockers，直到 credentials / ack / fill 都有 runtime proof**
