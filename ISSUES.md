# ISSUES.md — Current State Only

_最後更新：2026-04-18 23:27 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **本輪已把 canonical model leaderboard 從 placeholder-only 推進到可比較狀態**：`/api/models/leaderboard` 最新為 `count=5 / comparable_count=5 / placeholder_count=1`，warning 變成 `已自動分離 1 個 no-trade placeholder`。目前 top rows 為：
  - `logistic_regression / scan_backed_best / overall_score=0.7723 / avg_roi=0.0092 / avg_trades=3.5`
  - `catboost / scan_backed_best / overall_score=0.7175 / avg_roi=0.0175 / avg_trades=5.25`
  - `xgboost / scan_backed_best / overall_score=0.7003 / avg_roi=0.0187 / avg_trades=6.25`
- **P1 placeholder-only 主 blocker 已解除**：ModelLeaderboard 現在會把 `strategy_param_scan` 的最佳參數作為 `scan_backed_best` deployment profile candidate 納入 canonical 評估，因此不再只有空榜 fallback。
- **current-live blocker 已明確收斂成 canonical circuit breaker**：`hb_predict_probe.py` 最新結果為 `deployment_blocker=circuit_breaker_active`、`streak=74`、`recent 50 wins=0/50`、`additional_recent_window_wins_needed=15`、`allowed_layers=0`；q15/q35 support 敘事不再蓋過 breaker release math。
- **q15 support audit 目前被 runtime blocker 先行短路**：最新 `hb_q15_support_audit.py` 顯示 `support_route_verdict=insufficient_support_everywhere`、`component_experiment_verdict=runtime_blocker_preempts_component_experiment`；也就是說，在 breaker 未解除前，不應再把 q15 support/component patch 當成本輪主 blocker。
- **Strategy Lab snapshot history / fallback workflow 仍可用**：`/lab` 仍能顯示 snapshot history 與 scan-backed candidates；P1 現在從「沒有 comparable row」轉成「scan_backed_best 需要進一步產品化 / 穩定化」。
- **execution / venue readiness 仍未 closure**：即使 breaker 將來解除，`/api/status` 仍需保留 `live exchange credential / order ack / fill lifecycle` 未驗證的 blocker。

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
- `streak=74`
- `allowed_layers=0`

**風險**
- 若 heartbeat / docs / UI 再把 q15/q35 / floor-gap 敘事當成本輪主 blocker，operator 會誤判 current-live 真相。
- breaker 未解除前，任何 support / component patch / comparable leaderboard row 都不能視為 deployment closure。

**下一步**
- 以 `hb_predict_probe.py`、`hb_circuit_breaker_audit.py`、`recent_drift_report.py` 持續鎖定 breaker release math。
- 驗證：`python scripts/hb_parallel_runner.py --fast`、`python scripts/hb_predict_probe.py`、`python scripts/hb_circuit_breaker_audit.py fast`、瀏覽器 `/execution/status`。

### P0. recent canonical tail remains pathological (74-loss streak, bull-dominated 1000-row pathology)
**現況**
- `74` 連續 `simulated_pyramid_win=0`
- primary drift window = `1000`
- `interpretation=distribution_pathology`
- `dominant_regime=bull (91.7%)`
- recent `100` win rate 僅 `0.2500`

**風險**
- 若不拆出 tail root cause，breaker release math 只會繼續惡化。
- 若只看全域/TW-IC 或新恢復的 comparable leaderboard rows，仍可能高估當前 live 可部署性。

**下一步**
- 直接針對 recent `50 / 100 / 1000` canonical rows 做 target path、regime mix、4H shift 與 release-window examples drill-down，並把結果轉成 regression patch。
- 驗證：`recent_drift_report.py`、`hb_predict_probe.py`、必要時新增 regression test 鎖住 tail-pathology root cause。

### P1. scan_backed_best has restored comparable rows, but still needs graduation into a stable code-backed deployment profile
**現況**
- canonical leaderboard 已有 `5` 條 comparable rows
- 當前可比較 rows 的 `deployment_profile` 全為 `scan_backed_best`
- 代表 scan winner 參數確實有效，但目前仍主要依賴 artifact-backed params，而不是明確沉澱為穩定的 code-backed canonical profile

**風險**
- 若 scan artifact 過期或不一致，canonical leaderboard 可能再次退化。
- operator 現在能看到可比較 rows，但 deployment profile 名稱仍偏工程導向，不夠產品化。

**下一步**
- 將 `scan_backed_best` 的有效參數沉澱為清楚命名、可維護的 stable deployment profiles，避免長期依賴 artifact 驅動。
- 驗證：`/api/models/leaderboard` 仍保持 `comparable_count > 0`，且 profile 命名 / source 對 operator 可理解。

### P1. execution / venue readiness still blocks true live operations after breaker clears
**現況**
- `/api/status` 仍顯示：`live exchange credential 尚未驗證 · order ack lifecycle 尚未驗證 · fill lifecycle 尚未驗證`
- `readiness_scope=runtime_governance_visibility_only`

**風險**
- 即使 breaker 解除，若 venue lifecycle 尚未 closure，operator 仍不能把 blocker 消失誤讀成可實盤。

**下一步**
- 維持 venue blocker 在 operator surfaces 的可見性，直到 credentials / order ack / fill recovery 都有 runtime 證據。
- 驗證：瀏覽器 `/execution/status`、`/execution`，以及 `/api/status` payload。

---

## Not Issues
- **canonical model leaderboard placeholder-only**：已修復；現在已有 `count=5 / comparable_count=5`。
- **Strategy Lab leaderboard snapshot duplicate-key warning**：已修復；`snapshot_history` 有 stable `id`，`/lab` console 乾淨。
- **舊 q15/q35 support 敘事主導 current-live blocker**：本輪已切回 `circuit_breaker_active` 為唯一 current-live 真相。

---

## Current Priority
1. **先解 canonical circuit breaker release math，停止所有舊 blocker 敘事回滲**
2. **把 recent canonical tail pathology 轉成可修的 root cause / regression patch**
3. **把 `scan_backed_best` 升級成穩定、可維護的 code-backed deployment profile，同時保持 `comparable_count > 0`**
4. **持續保留 venue readiness blocker，禁止任何 live-ready 假象**
