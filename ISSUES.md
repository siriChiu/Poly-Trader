# ISSUES.md — Current State Only

_最後更新：2026-04-19 06:49 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **本輪 fast heartbeat + collect 有真實資料推進**：`Raw=31067 (+1) / Features=22485 (+1) / Labels=62564 (+1)`；`240m` 與 `1440m` freshness 仍屬 lookahead 預期，不是資料管線停擺。
- **current-live 唯一 deployment blocker 仍是 canonical circuit breaker**：`streak=237`、`recent 50 wins=0/50`、`additional_recent_window_wins_needed=15`、`allowed_layers=0`。
- **current live bucket 仍是 q15 exact support 缺失**：`current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15`、`live_current_structure_bucket_rows=0/50`、`support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`。
- **broader spillover 真相仍是 bull|CAUTION toxic pocket**：`200 rows / WR=0.0% / quality=-0.2947 / pnl=-1.09% / dd_penalty=38.17% / time_underwater=81.8%`；exact live lane 仍 `0 rows`，不能把 spillover 當成 exact live 代理放行。
- **本輪產品化前進**：`model/predictor.py` 現在在 exact live lane `0 rows` 時，仍會用 `current_live_row_gate_inputs` 輸出 spillover 對照與 top 4H shifts；`/lab` 與 `/execution/status` 已 browser verify 可看到 `exact-vs-spillover` 與 `feat_4h_bias200 / feat_4h_dist_bb_lower / feat_4h_dist_swing_low` 差異，不再只剩空白 `—` 對照。
- **venue readiness 仍未 closure**：`binance=config enabled + public-only`、`okx=config disabled + public-only`；`live exchange credential / order ack lifecycle / fill lifecycle` 仍無 runtime proof。

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
**現況**
- `deployment_blocker=circuit_breaker_active`
- `recent_window=50`
- `current_recent_window_wins=0`
- `required_recent_window_wins=15`
- `additional_recent_window_wins_needed=15`
- `streak=237`
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
- `support_progress.status=no_recent_comparable_history`
- `leaderboard_selected_profile=core_only`
- `train_selected_profile=core_plus_macro`
- `governance_contract=dual_role_governance_active`

**風險**
- 若 breaker path 下 support metadata 又被遮蔽成空值或 stale 舊敘事，current bucket 治理會再次失真。

**下一步**
- 維持 `0/50 + exact_bucket_missing_exact_lane_proxy_only + gap_to_minimum=50` 在 probe / API / UI / docs 四處一致。
- 驗證：`python scripts/hb_q15_support_audit.py`、`python scripts/hb_predict_probe.py`、browser `/lab`。

### P1. broader `bull|CAUTION` spillover pathology is still open, but exact-vs-spillover contrast no longer disappears when exact rows are 0
**現況**
- exact live lane：`0 rows`
- broader spillover：`bull|CAUTION 200 rows / WR=0.0% / quality=-0.2947 / pnl=-1.09%`
- `feature_shift_reference=current_live_row_gate_inputs`
- browser `/lab` 與 `/execution/status` 已可直接看到 top 4H shifts：`feat_4h_bias200`、`feat_4h_dist_bb_lower`、`feat_4h_dist_swing_low`

**風險**
- 雖然 operator 已看得到 spillover 與 current live row 的結構差異，但真正的 gate / calibration / training 修復仍未落地，toxic pocket 依然只被 fail-close 擋下。

**下一步**
- 把 `bull|CAUTION` pocket 轉成可重跑的 gate/calibration/training patch，而不是只停留在對照卡。
- 驗證：`data/live_decision_quality_drilldown.json`、`python scripts/hb_predict_probe.py`、targeted pytest、browser `/lab`。

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
- **data pipeline frozen**：不是；本輪 collect 實際新增 `+1 raw / +1 features / +1 labels`。
- **exact-vs-spillover 對照缺失**：不是；本輪已修成在 exact live lane `0 rows` 時仍以 current live gate inputs 當 reference，UI 可見 top 4H shifts。
- **Strategy Lab / Execution Status blocker split 缺失**：不是；本輪 browser verify 看到 `circuit_breaker_active`、`support 0/50`、`venue blockers`、`bull|CAUTION spillover`，且無 JS exception。

---

## Current Priority
1. **維持 breaker-first truth，讓 current-live blocker 始終是 release math，而不是 support / spillover / venue 雜訊**
2. **維持 q15 support `0/50 + gap_to_minimum=50` 在 breaker path 下仍可 machine-read**
3. **把 `bull|CAUTION` 200-row toxic pocket 從 diagnostics 轉成正式 gate/calibration/training patch**
4. **持續保留 venue blockers，直到 credentials / ack / fill 都有 runtime proof**
