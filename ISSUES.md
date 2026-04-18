# ISSUES.md — Current State Only

_最後更新：2026-04-19 02:58 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **fast heartbeat 仍維持 collect + diagnostics 閉環**：本輪資料庫來到 `Raw=31031 / Features=22449 / Labels=62297`，相較心跳前增加 `+2 / +2 / +11`；240m 與 1440m label freshness 仍是 `expected_horizon_lag`，本輪不是資料管線凍結問題。
- **本輪已落地 bull q15 bias50 fail-close veto**：`model/predictor.py` 與 `backtesting/strategy_lab.py` 現在都會把 `0.15 <= structure_quality < 0.35 且 feat_4h_bias50 >= 1.8` 的 bull q15 弱結構 pocket 直接封成 `BLOCK|bull_q15_bias50_overextended_block|q15`，避免再把 stretched q15 bounce 誤包裝成 live `CAUTION` 入口。
- **本輪已把 exact-live-lane vs spillover 真相推到 Dashboard / Strategy Lab**：`/api/status` 新增 `decision_quality_scope_pathology_summary`，瀏覽器 `http://127.0.0.1:5173/` 與 `/lab` 都已直接顯示 `🧬 Live lane / spillover 對照` 卡片，console 無 JS error。
- **current-live 主 blocker 仍是 canonical circuit breaker**：`deployment_blocker=circuit_breaker_active`、`recent 50 wins=0/50`、`required_recent_window_wins=15`、`streak=137`、`allowed_layers=0`。
- **recent bull pathology 仍未 closure，但 root cause 已更清楚**：current exact live lane `41` rows 仍是正向樣本（`WR=100% / quality=0.697`），真正拖垮 runtime 的是更寬的 same-regime spillover：`bull|ALLOW` 額外 `159` rows 只有 `WR=0% / quality=-0.276 / pnl=-1.03%`；recent canonical `100` 筆仍是 `100x0`。
- **leaderboard / train 治理語義已從「exact-supported」回退成 stale-under-minimum**：`live_current_structure_bucket_rows=41 < minimum_support_rows=50`，`dual_profile_state=train_exact_supported_profile_stale_under_minimum`，`governance_contract=train_profile_contract_stale_against_current_support`；`/api/models/leaderboard` 目前 `comparable_count=0 / placeholder_count=4`，不能把排行榜 #1 當成可部署排名。
- **direct candidate probe 仍 timeout-prone**：`python scripts/hb_leaderboard_candidate_probe.py` 在本機直接執行仍超時；但 `hb_model_leaderboard_api_probe.py` 可穩定讀到 cache 與 governance payload，因此目前是 probe/runtime 成本問題，不是 API contract 缺失。
- **execution venue readiness 仍未 closure**：credential、order ack lifecycle、fill lifecycle 都還沒有 live runtime proof；breaker 清除後也不能把系統誤判成 live-ready。

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
**現況**
- `deployment_blocker=circuit_breaker_active`
- `recent_window=50`
- `current_recent_window_wins=0`
- `required_recent_window_wins=15`
- `additional_recent_window_wins_needed=15`
- `streak=137`
- `allowed_layers=0`

**風險**
- 若 heartbeat / UI 再把 q15 support、q35 scaling、或單點 component gap 當成主 blocker，operator 會再次失去 current-live 真相。

**下一步**
- 維持 breaker-first truth，所有 current-live surface 繼續以 `release math` 作唯一 deployment blocker。
- 驗證：`python scripts/hb_predict_probe.py`、`python scripts/hb_circuit_breaker_audit.py fast`、瀏覽器 `/` 與 `/lab` 的 live blocker/runtime closure。

### P0. recent bull spillover pathology is still unresolved even after q15 bias50 fail-close
**現況**
- recent canonical `100` rows：`100x0`、`win_rate=0.0000`
- current live bucket：`BLOCK|bull_q15_bias50_overextended_block|q15`
- exact live lane：`41 rows / WR=100% / quality=0.697`
- broader spillover：`bull|ALLOW` 額外 `159 rows / WR=0% / quality=-0.276 / pnl=-1.03%`
- top shifts：`feat_4h_bias200 / feat_4h_dist_swing_low / feat_4h_dist_bb_lower`

**風險**
- 若不把 spillover pocket 轉成正式 gate/calibration/training patch，breaker 會繼續被 recent bull tail 拖住。

**下一步**
- 直接用 `exact live lane vs broader spillover` 對照來追 root cause，優先處理 bull|ALLOW spillover 為何仍被 broader scope 吃進來。
- 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`、targeted pytest、瀏覽器 `/` 與 `/lab` 的 pathology card。

### P1. leaderboard/train governance is stale against current support truth
**現況**
- `dual_profile_state=train_exact_supported_profile_stale_under_minimum`
- `governance_contract=train_profile_contract_stale_against_current_support`
- `live_current_structure_bucket_rows=41 / minimum_support_rows=50`
- `/api/models/leaderboard`: `comparable_count=0 / placeholder_count=4`
- `hb_leaderboard_candidate_probe.py` 本輪直接執行 timeout；`hb_model_leaderboard_api_probe.py` 仍可 machine-read governance payload

**風險**
- train/runtime 還在沿用舊的 exact-supported production profile 敘事，會讓 operator 誤以為 production profile 已 closure。

**下一步**
- 重新刷新 support-aware profile / train metadata / candidate probe，讓 production-profile 敘事回到 `under minimum support` 的最新真相。
- 驗證：`python scripts/hb_model_leaderboard_api_probe.py`、`python scripts/hb_leaderboard_candidate_probe.py`、`pytest tests/test_model_leaderboard_api_cache.py -q`、瀏覽器 `/lab`。

### P1. venue readiness is still unverified
**現況**
- live exchange credential 未驗證
- order ack lifecycle 未驗證
- fill lifecycle 未驗證

**風險**
- 即使 breaker 未來解除、leaderboard 與 gate 語義更清楚，也不能把 execution surface 誤讀成已可實盤。

**下一步**
- 持續在 operator surface 保留 venue blockers，直到 runtime artifact 證明 credentials / ack / fill 都 closure。
- 驗證：瀏覽器 `/execution`、`/execution/status`，以及 `/api/status` payload。

---

## Not Issues
- **資料管線凍結**：不是；本輪 fast heartbeat 已新增 `+2 raw / +2 features / +11 labels`。
- **live pathology surface 缺失**：不是；Dashboard 與 Strategy Lab 都已直接顯示 `🧬 Live lane / spillover 對照`。
- **q35 scaling 是 current-live 主 blocker**：不是；目前 current live bucket 已經是 `BLOCK|bull_q15_bias50_overextended_block|q15`，q35 audit 只剩 reference-only。

---

## Current Priority
1. **維持 breaker release math 作為唯一 current-live blocker**
2. **把 bull exact-lane vs spillover 對照轉成正式 root-cause patch**
3. **把 train / leaderboard 的 stale exact-supported profile 敘事刷新回 under-minimum-support 真相**
4. **持續保留 venue readiness blocker，禁止任何 live-ready 假象**
