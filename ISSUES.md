# ISSUES.md — Current State Only

_最後更新：2026-04-18 21:46 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **本輪 heartbeat #20260418f 已完成閉環**：`Raw=30887 / Features=22305 / Labels=62193`，`simulated_pyramid_win=0.5788`，`Global IC=14/30`，`TW-IC=30/30`。
- **current-live blocker 已切回 canonical circuit breaker**：`hb_predict_probe.py` 顯示 `signal=CIRCUIT_BREAKER`、`deployment_blocker=circuit_breaker_active`、`allowed_layers=0`、`allowed_layers_reason=circuit_breaker_blocks_trade`；release math 為 `recent 50 至少 15 勝`，目前只有 `4/50`，仍差 `11` 勝，且 `streak` 必須保持 `< 50`（目前 `45`）。
- **q15 / q35 已不是 current-live 主 blocker**：在 breaker 啟用下，`q15_support_audit` / `q15_bucket_root_cause` / `q35_scaling_audit` 都降級為 background reference，不得再把舊的 `q15 patch-active` 敘事當成 current-state truth。
- **operator surfaces 已同步 breaker truth**：瀏覽器驗證 `http://127.0.0.1:5173/execution` 與 `/execution/status` 都顯示 `circuit_breaker_active`、`circuit_breaker_blocks_trade`、`layers — → 0`，並保留 venue readiness blocker：`live exchange credential 尚未驗證 · order ack lifecycle 尚未驗證 · fill lifecycle 尚未驗證`。
- **canonical leaderboard 仍不可部署**：瀏覽器 `fetch('/api/models/leaderboard')` 回傳 `count=0 / comparable_count=0 / placeholder_count=4 / stale=true / refreshing=true / refresh_reason=cache_stale`；Strategy Lab 仍必須維持 placeholder-only 語氣。
- **recent tail pathology 仍明確存在**：`recent_drift_report.py` 主視窗為最近 `1000` 筆，`interpretation=distribution_pathology`，`dominant_regime=bull 88.8%`，最新尾端已擴大到 **45 連續 `simulated_pyramid_win=0`**。
- **稀疏來源 blocker 尚未清空**：仍有 `8` 個 blocked sparse features；其中 `fin_netflow` 最新狀態仍是 `auth_missing`（缺 `COINGLASS_API_KEY`）。

---

## Open Issues

### P0. canonical circuit breaker active — current live path remains non-deployable
**現況**
- `signal=CIRCUIT_BREAKER`
- `deployment_blocker=circuit_breaker_active`
- `allowed_layers=0`
- `recent_window=50`
- `current_recent_window_wins=4`
- `required_recent_window_wins=15`
- `additional_recent_window_wins_needed=11`
- `streak=45`

**風險**
- 若繼續沿用 q15/q35 的舊 blocker 敘事，operator 會誤判當前主 blocker，導致 patch 順序錯誤。
- 在 breaker 未解除前，任何 q15 floor-gap / support patch 都不能當成 current-live deployment closure。

**下一步**
- 以 `hb_circuit_breaker_audit.py`、`hb_predict_probe.py`、`recent_drift_report.py` 為主，先把 recent 50 / recent 1000 的 canonical tail pathology 說清楚並追 release math。
- 驗證方式：`python scripts/hb_parallel_runner.py --fast --hb <N>`、`python scripts/hb_predict_probe.py`、`python scripts/hb_circuit_breaker_audit.py <N>`、瀏覽器 `/execution` + `/execution/status`。

### P0. recent canonical tail is still pathological (45-loss streak, 1000-row bull-dominated pathology)
**現況**
- `45` 連續 `simulated_pyramid_win=0`
- recent drift primary window = `1000`
- `interpretation=distribution_pathology`
- `dominant_regime=bull (88.8%)`
- `win_rate=0.8450` on the pathological slice, but tail release condition for live breaker remains broken (`4/50` wins only)

**風險**
- 若只看全域 / TW-IC 改善，會錯把最近 bull pocket 的 label imbalance 當成可部署優勢，實際 live 仍被 breaker 壓死。
- 若不先修 tail pathology，breaker release math 只會越來越難解。

**下一步**
- 直接檢查 recent 50 / 100 / 1000 canonical rows 的 target path、regime mix、4H shift 與 release-window examples，定位為何 recent 50 持續失敗。
- 驗證方式：`recent_drift_report.py`、`hb_predict_probe.py`、`hb_circuit_breaker_audit.py`、必要時追加針對 recent tail 的診斷腳本與回歸測試。

### P1. canonical model leaderboard is still placeholder-only
**現況**
- `/api/models/leaderboard`：`count=0 / comparable_count=0 / placeholder_count=4`
- `stale=true / refreshing=true / refresh_reason=cache_stale`
- Strategy Lab 目前仍不能回答「哪個 canonical 模型可部署」

**風險**
- 若背景重算完成後仍沒有 comparable row，Strategy Lab 只能繼續提供誠實的空榜，無法支援產品化部署決策。
- 若前端先拿 placeholder 排名充當正式答案，會再次產生雙真相。

**下一步**
- 讓 canonical leaderboard 真正產生 `comparable_count > 0` 的 row；在此之前，前端與 API 都必須維持 placeholder-only warning。
- 驗證方式：`/api/models/leaderboard` payload、Strategy Lab `/lab`、必要時 `hb_model_leaderboard_api_probe.py`。

### P1. venue readiness still blocks true live operations after breaker clears
**現況**
- `/execution` 與 `/execution/status` 均顯示：`live exchange credential 尚未驗證 · order ack lifecycle 尚未驗證 · fill lifecycle 尚未驗證`

**風險**
- 即使 breaker 解除，若 venue lifecycle 未驗證，operator 仍不能把 UI blocker 消失誤讀成可實盤。

**下一步**
- 維持 venue blocker 在 operator surfaces 的可見性，直到 credentials / order ack / fill recovery 全部有 runtime 證據。
- 驗證方式：瀏覽器 `/execution`、`/execution/status`、相關 API / reconciliation artifacts。

---

## Not Issues
- **q15 patch-active / execution-blocked**：本輪不是 current-live 主 blocker；breaker 已先行接管 current-live truth。
- **q35 scaling lane**：本輪 `q35_scaling_audit` 結論為 `reference_only_current_bucket_outside_q35`，目前僅屬 background research。
- **Execution route reachability**：`/execution` 與 `/execution/status` 本輪已在瀏覽器成功打開，且能看到最新 breaker / venue blocker truth。

---

## Current Priority
1. **先解 circuit breaker current-live blocker，停止沿用舊 q15/q35 blocker 敘事**
2. **把 recent canonical tail pathology 轉成可修的 release-math root cause**
3. **讓 canonical leaderboard 產生至少一條 comparable row，同時維持 placeholder-only honesty 直到真的有 row**
4. **在 1/2/3 之前，持續保留 venue readiness blocker，禁止誤報 live-ready**
