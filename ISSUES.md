# ISSUES.md — Current State Only

_最後更新：2026-04-19 01:32 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **canonical model leaderboard 的 deployment profile 已真正進入 code-backed product surface**：最新 `hb_leaderboard_candidate_probe.py` 與 `hb_model_leaderboard_api_probe.py` 都顯示 top row 為 `stable_turning_point_bull_chop_strict_v1 / code_backed_promoted_from_scan`；`/api/models/leaderboard` 目前為 `stale=false / count=5 / comparable_count=5 / placeholder_count=1`。
- **leaderboard governance probe 已 fresh，且 API / Strategy Lab 可讀到 exact-supported split 語義**：`server/routes/api.py` 現在把 `leaderboard_governance` 一起序列化到 `/api/models/leaderboard`；`StrategyLab.tsx` 已顯示 `Global 排名` vs `Production 配置`，不再只剩 artifact-only profile 名稱。
- **current-live blocker 仍是 canonical circuit breaker，不是 q15 support shortage**：最新 `hb_predict_probe.py` 顯示 `deployment_blocker=circuit_breaker_active`、`streak=102`、`recent 50 wins=0/50`、`allowed_layers=0`。同時 current live bucket 已明確為 `CAUTION|structure_quality_caution|q15`，`support_route_verdict=exact_bucket_supported`、`current_live_structure_bucket_rows=66 >= minimum_support_rows=50`；support shortage 已不是主 blocker。
- **recent canonical tail 已惡化成 102 連敗，且 primary drift 已收斂到最近 100 rows 的 bull-only pathology**：最新 `recent_drift_report.json` 顯示 primary window `100`、`wins=0/100`、`constant_target=true`、`dominant_regime=bull (100%)`、`avg_simulated_quality=-0.2841`。`q15_support_audit.json` 同時指出 `best_single_component=feat_4h_bias50`、`remaining_gap_to_floor=0.1707`，代表下一步 patch 應直接鎖定 bull q15 pocket 與 bias50 floor gap。
- **P1 主線已從「scan_backed_best 需要 promotion」切到「post-threshold leaderboard governance 仍未同步」**：最新 candidate probe 為 `dual_profile_state=post_threshold_profile_governance_stalled`、`governance_contract=post_threshold_governance_contract_needs_leaderboard_sync`。也就是 deployment profile promotion 已完成，但 leaderboard global winner 仍是 `core_only`，而 train/runtime production profile 已是 `core_plus_macro_plus_4h_structure_shift` 的 exact-supported lane，兩者尚未完成 post-threshold 治理收斂。

---

## Open Issues

### P0. canonical circuit breaker active — current live path remains non-deployable
**現況**
- `deployment_blocker=circuit_breaker_active`
- `horizon=1440m`
- `recent_window=50`
- `current_recent_window_wins=0`
- `required_recent_window_wins=15`
- `additional_recent_window_wins_needed=15`
- `streak=102`
- `allowed_layers=0`
- current live lane 已明確為 `CAUTION|structure_quality_caution|q15`
- `support_route_verdict=exact_bucket_supported`、`current_live_structure_bucket_rows=66 / minimum_support_rows=50`

**風險**
- 若 heartbeat / UI 再把 q15 support shortage 當主 blocker，operator 會誤判 current-live 真相。
- breaker 未解除前，任何 exact-support、leaderboard comparable row、或 deployment profile 升級都不能視為 live deployment closure。

**下一步**
- 繼續以 `hb_predict_probe.py`、`hb_circuit_breaker_audit.py`、`recent_drift_report.py` 鎖定 release math。
- 驗證：`python scripts/hb_parallel_runner.py --fast`、`python scripts/hb_predict_probe.py`、`python scripts/hb_circuit_breaker_audit.py fast`、`/api/status`。

### P0. recent canonical tail remains pathological (102 consecutive simulated_pyramid_win=0)
**現況**
- `102` 連續 `simulated_pyramid_win=0`
- primary drift window = `100`
- `interpretation=distribution_pathology`
- `dominant_regime=bull (100%)`
- recent `100` win rate = `0.0000`
- `avg_simulated_quality=-0.2841`
- `best_single_component=feat_4h_bias50`
- `remaining_gap_to_floor=0.1707`

**風險**
- 若不把 bull-dominated pathology 轉成可重跑 patch，breaker 只會持續惡化。
- 即使 q15 support 已達標，若 tail distribution 不改善，runtime 仍會被 breaker 壓死；trade floor 只會成為 breaker 解除後的下一層 blocker。

**下一步**
- 直接對 recent `50 / 100 / 1000` canonical rows 做 q15 bull pocket root-cause，優先鎖定 `feat_4h_bias50` 與 sibling-window 結構 shift。
- 驗證：`recent_drift_report.py`、`hb_predict_probe.py`、新增 regression test 鎖住 bull pathology patch。

### P1. post-threshold leaderboard governance still needs sync after exact support recovery
**現況**
- candidate probe：`dual_profile_state=post_threshold_profile_governance_stalled`
- governance：`post_threshold_governance_contract_needs_leaderboard_sync`
- `support_route_verdict=exact_bucket_supported`
- `current_live_structure_bucket=CAUTION|structure_quality_caution|q15`
- `current_live_structure_bucket_rows=66 / minimum_support_rows=50`
- leaderboard global winner：`core_only`
- train/runtime production profile：`core_plus_macro_plus_4h_structure_shift`
- top model deployment profile：`stable_turning_point_bull_chop_strict_v1 / code_backed_promoted_from_scan`

**風險**
- 若 leaderboard 仍只保留 global shrinkage winner，而沒有把 exact-supported production profile 的治理角色講清楚，operator 會把 current live lane 誤讀成已完全收斂，或反過來把健康分工誤判成 parity drift。
- 文件若還停在舊的 `scan_backed_best needs promotion` 敘事，會再次與 runtime truth 失配。

**下一步**
- 把 leaderboard / heartbeat summary / docs / operator payload 的 current-state 敘事切到 `post-threshold governance sync`，讓 `global ranking winner` 與 `production profile` 都可被明確讀到。
- 驗證：`python scripts/hb_leaderboard_candidate_probe.py`、`python scripts/hb_model_leaderboard_api_probe.py`、`python -m pytest tests/test_model_leaderboard_api_cache.py tests/test_frontend_decision_contract.py -q`。

### P1. execution / venue readiness still blocks true live operations after breaker clears
**現況**
- `/lab` 與 `/api/status` 仍顯示：`live exchange credential 尚未驗證 · order ack lifecycle 尚未驗證 · fill lifecycle 尚未驗證`
- `readiness_scope=runtime_governance_visibility_only`

**風險**
- 即使 breaker 解除、q15 support 恢復、leaderboard surface 更清楚，operator 仍不能把 blocker 消失誤讀成可實盤。

**下一步**
- 維持 venue blocker 在 operator surfaces 的可見性，直到 credentials / order ack / fill recovery 都有 runtime 證據。
- 驗證：`/api/status` payload、`/execution/status`。

---

## Not Issues
- **`scan_backed_best` deployment profile promotion**：已修復；最新 top model deployment 已是 `stable_turning_point_bull_chop_strict_v1 / code_backed_promoted_from_scan`。
- **leaderboard stale cache 缺少 selection fields**：已修復；probe 會在 cache 缺欄位時自動 live rebuild，且 API cache 現在為 fresh。
- **current q15 exact-support shortage**：已不是主 blocker；最新 `support_route_verdict=exact_bucket_supported`、`66 >= 50`。

---

## Current Priority
1. **維持 breaker release math 作為唯一 current-live 真相**
2. **把 bull-dominated recent tail pathology 轉成可驗證 patch**
3. **完成 exact-supported post-threshold leaderboard governance sync**
4. **持續保留 venue readiness blocker，禁止任何 live-ready 假象**
