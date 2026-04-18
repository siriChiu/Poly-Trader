# ISSUES.md — Current State Only

_最後更新：2026-04-19 01:35 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **fast heartbeat 已成功完成 collect + diagnostics 閉環**：本輪資料庫來到 `Raw=30954 / Features=22372 / Labels=62279`，相較心跳前增加 `+2 / +2 / +21`；240m 與 1440m label freshness 都是 `expected_horizon_lag`，本輪不是資料管線凍結問題。
- **current-live 主 blocker 仍是 canonical circuit breaker**：`deployment_blocker=circuit_breaker_active`、`recent 50 wins=0/50`、`required_recent_window_wins=15`、`streak=123`、`allowed_layers=0`。
- **current live q15 exact support 仍維持 closure，不是主 blocker**：`current_live_structure_bucket=CAUTION|structure_quality_caution|q15`、`current_live_structure_bucket_rows=55 >= minimum_support_rows=50`、`support_route_verdict=exact_bucket_supported`。
- **recent canonical tail 仍是 bull-dominated pathology**：最近 `100` 筆 `simulated_pyramid_win=0/100`，`win_rate=0.0000`，`dominant_regime=bull (100%)`；相對 sibling window 的主要 shift 仍是 `feat_4h_vol_ratio / feat_4h_bb_pct_b / feat_4h_bias20`，而 current q15 lane 的單點 floor-gap component 仍以 `feat_4h_bias50` 最大。
- **本輪已把 leaderboard governance split 從 probe-only truth 推到 operator surface**：`/api/models/leaderboard` 現在暴露 `leaderboard_governance`，`scripts/hb_model_leaderboard_api_probe.py` 也會 machine-read 同一份 `dual_profile_state / profile_split / governance_contract`；瀏覽器 `/lab` 已顯示治理 banner，明確區分 `Global 排名 = core_only` 與 `Production 配置 = core_plus_macro_plus_4h_structure_shift`，console 無 JS error。
- **execution venue readiness 仍未 closure**：credential、order ack lifecycle、fill lifecycle 仍沒有 live runtime proof；breaker 清除後也不能把系統誤判成 live-ready。

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live blocker
**現況**
- `deployment_blocker=circuit_breaker_active`
- `recent_window=50`
- `current_recent_window_wins=0`
- `required_recent_window_wins=15`
- `additional_recent_window_wins_needed=15`
- `streak=123`
- `allowed_layers=0`

**風險**
- 若 heartbeat / UI 再把 q15 support、q35 scaling 或單點 floor gap 當作主 blocker，operator 會再次失去 current-live 真相。

**下一步**
- 維持 breaker-first truth，並把所有 current-live surface 繼續鎖在 `release math`。
- 驗證：`python scripts/hb_predict_probe.py`、`python scripts/hb_circuit_breaker_audit.py fast`、瀏覽器 `/execution/status`。

### P0. recent bull tail pathology is still unresolved
**現況**
- 最近 `100` 筆 canonical rows 為 `100x0`
- `interpretation=distribution_pathology`
- `dominant_regime=bull (100%)`
- current q15 lane：`entry_quality=0.3715`、`trade_floor_gap=0.1785`
- `best_single_component=feat_4h_bias50`
- sibling-window 主要 shift：`feat_4h_vol_ratio / feat_4h_bb_pct_b / feat_4h_bias20`

**風險**
- breaker 會持續惡化；即使 q15 support 仍達標，runtime 也只會卡在 breaker + trade floor。

**下一步**
- 直接把 bull pathology 轉成 patch：優先檢查 `feat_4h_bias50` 與 4H overextended / vol-ratio / bb 結構 shift 的組合，不再只報告 drift。
- 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`、針對 bull/q15 lane 的 targeted pytest。

### P1. post-threshold leaderboard governance visibility is landed, but governance closure is still open
**現況**
- `/api/models/leaderboard` 已暴露 `leaderboard_governance`
- `scripts/hb_model_leaderboard_api_probe.py` 已輸出 `leaderboard_governance`
- `/lab` 已顯示治理 banner：`Global 排名 = core_only` / `Production 配置 = core_plus_macro_plus_4h_structure_shift`
- candidate probe 仍回報：`dual_profile_state=post_threshold_profile_governance_stalled`
- `governance_contract=post_threshold_governance_contract_needs_leaderboard_sync`

**風險**
- 如果文件或 heartbeat 仍把這個狀態寫成「leaderboard 已完全收斂」，operator 會把健康的可見化進展誤讀成治理 closure。

**下一步**
- 保留 visibility landed 的事實，同時把 remaining issue 明確收斂成「global winner 與 production profile split 尚未關閉」。
- 驗證：`python scripts/hb_leaderboard_candidate_probe.py`、`python scripts/hb_model_leaderboard_api_probe.py`、瀏覽器 `/lab`。

### P1. venue readiness is still unverified
**現況**
- live exchange credential 未驗證
- order ack lifecycle 未驗證
- fill lifecycle 未驗證

**風險**
- 即使 breaker 未來解除、leaderboard surface 更清楚，也不能把 execution surface 誤讀成已可實盤。

**下一步**
- 持續在 operator surface 保留 venue blockers，直到 runtime artifact 證明 credentials / ack / fill 都 closure。
- 驗證：瀏覽器 `/execution`、`/execution/status`，以及 `/api/status` payload。

---

## Not Issues
- **資料管線凍結**：本輪不是；fast heartbeat 已新增 `+2 raw / +2 features / +21 labels`。
- **q15 exact support shortage**：不是；current live q15 exact bucket 仍有 `55 / 50` rows。
- **leaderboard governance 完全看不見**：不是；API、probe、Strategy Lab banner 都已能直接讀到 governance split。剩下的是治理 closure，而不是可見性缺失。

---

## Current Priority
1. **維持 breaker release math 作為唯一 current-live 真相**
2. **把 bull 100x0 canonical tail 轉成可驗證 patch**
3. **把 leaderboard governance 從「已可見」推到真正 closure**
4. **持續保留 venue readiness blocker，禁止任何 live-ready 假象**
