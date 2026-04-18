# ISSUES.md — Current State Only

_最後更新：2026-04-18 19:50 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **q15 live runtime truth 已完成 fast-runner resync**：`hb_parallel_runner.py --fast` 現在會在 `hb_q15_support_audit` 已判定 `exact_supported_component_experiment_ready`、但先前 probe/drilldown 仍停在 pre-patch 狀態時，自動重跑 `hb_predict_probe.py` 與 `live_decision_quality_drilldown.py`，避免 heartbeat 摘要繼續引用舊的 `patch_inactive_or_blocked` 真相。
- **current live q15 row 現在是 support-closed + patch-active + execution-blocked**：`current_live_structure_bucket=CAUTION|structure_quality_caution|q15`、`support_route_verdict=exact_bucket_supported`、`support_rows=96/50`；resynced live probe 顯示 `q15_exact_supported_component_patch_applied=true`、`entry_quality=0.5501 / C`、`allowed_layers_raw=1`，但最終仍是 `allowed_layers=0 / allowed_layers_reason=decision_quality_below_trade_floor / runtime_closure_state=patch_active_but_execution_blocked`。
- **operator-facing surface 已同步到最新 truth**：瀏覽器驗證 `/execution/status` 與 `data/heartbeat_20260418b_summary.json` 都顯示 `q15 patch active`、`layers 1 → 0`、`support 96 / 50`，不再把 support closure 誤讀成 deployment closure。
- **venue readiness 仍未關閉**：`/execution/status` 主 blocker 仍是 `live exchange credential 尚未驗證 · order ack lifecycle 尚未驗證 · fill lifecycle 尚未驗證`；因此即使 q15 raw path 已開出 1 層 capacity，也不能視為 live-ready deployment。
- **model leaderboard 仍是 placeholder-only**：目前仍是 `count=0 / comparable_count=0 / placeholder_count=6`，warning 仍明確要求不要把 `#1` 當成可部署排名；`leaderboard_feature_profile_probe` 顯示 `dual_role_governance_active / dual_role_split_but_aligned`，所以目前主 blocker 不再是 feature-profile governance drift，而是所有 refresh models 仍沒有產生 trade。

---

## Open Issues

### P0. q15 patch is active, but final execution still resolves to 0 layers
**現況**
- `support_route_verdict=exact_bucket_supported`
- `support_rows=96 / 50`
- `q15_exact_supported_component_patch_applied=true`
- `entry_quality=0.5501 / entry_quality_label=C`
- `allowed_layers_raw=1 / allowed_layers=0`
- `allowed_layers_reason=decision_quality_below_trade_floor`
- `runtime_closure_state=patch_active_but_execution_blocked`
- `/execution/status` 仍同時顯示 venue/product blocker：`live exchange credential 尚未驗證 · order ack lifecycle 尚未驗證 · fill lifecycle 尚未驗證`

**風險**
- 若只看 support closure 或 raw `layers=1`，會誤判為 q15 已可部署；實際上 final execution 與 venue readiness 都尚未 closure。

**下一步**
- 釐清 `q15 patch active` 之後，究竟是 **final decision-quality gate** 還是 **venue readiness** 在扮演主 no-deploy blocker，避免 operator surface 混成單一模糊「blocked」。
- 保持所有 surface 使用 `patch_active_but_execution_blocked` / `layers 1 → 0` 語義，不得回退成 `patch inactive` 或 `support still missing`。
- 驗證方式：`python scripts/hb_parallel_runner.py --fast --hb <N>`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、瀏覽器檢查 `/execution/status`。

### P1. model leaderboard is honest but still unusable for deployment choice
**現況**
- `/api/models/leaderboard` / cache 仍是 `count=0 / comparable_count=0 / placeholder_count=6`
- placeholder-only warning 正常存在
- `leaderboard_feature_profile_probe` 顯示 `dual_role_governance_active / dual_role_split_but_aligned`
- 目前沒有證據顯示 train-vs-leaderboard profile governance 失真；真正 blocker 是 refresh models 全部 `avg_trades=0`

**風險**
- Strategy Lab 雖然不再造假正常排名，但產品仍無法回答「現在哪個模型可部署」。

**下一步**
- 直接追 `avg_trades=0` 的根因：deployment profile、資料窗口、entry rules、或 evaluation path 本身沒有產生 trade。
- 在出現 `comparable_count > 0` 之前，所有 leaderboard/operator surfaces 都必須維持 placeholder-only 語氣。
- 驗證方式：`python scripts/hb_model_leaderboard_api_probe.py` 或等價 cache/API payload 必須至少出現 `comparable_count>0`；否則 warning 不得消失。

---

## Not Issues
- **q15 stale heartbeat summary / drilldown 沒有跟上 support-ready patch**：已修復；fast heartbeat 會在 q15 support audit 說明 patch-ready、但 probe 尚未套用時自動 resync probe + drilldown。
- **q15 support closure 缺失**：已非 blocker；目前 support 是 `96/50 exact_bucket_supported`。
- **leaderboard feature-profile governance drift**：目前 probe 顯示 `dual_role_split_but_aligned`，不是 zero-trade placeholder-only 的主因。

---

## Current Priority
1. **把 q15 從 `patch_active_but_execution_blocked` 推進到真正的 execution/venue closure，或維持明確 no-deploy governance**
2. **找出 leaderboard zero-trade 根因，產生至少一條 comparable deployment row**
