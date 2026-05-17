# ROADMAP.md — Current Plan Only

_最後更新：2026-05-18 01:22:23 CST_

本文件只保留目前產品化計畫與下一輪 gates；不保存歷史流水帳。

---

## 本輪已完成
- Heartbeat `#1314-productization` 完成 collect + diagnostics refresh，runner status=`success`。
- current-live truth 確認：`deployment_blocker=under_minimum_exact_live_structure_bucket`，bucket=`CAUTION|structure_quality_caution|q15`，support=`3/50`，gap=`47`。
- recent drift truth 確認：latest window `100`，wins/losses=`17/83`，win rate=`17.0%`，dominant regime=`bear 84.0%`，alerts=`label_imbalance, regime_shift`。
- **產品化修補已落地**：`/execution/status` 現在在部署診斷與帳戶快照之間渲染 `RecentCanonicalDriftCard`，把 current blocker 與 recent drift 根因放到同一個 canonical diagnostics flow。
- **驗證完成**：
  - `python -m pytest tests/test_frontend_decision_contract.py -q` → `83 passed`
  - `python -m pytest tests/test_server_startup.py -k 'recent_canonical_drift or api_status_includes_runtime_raw' -q` → `3 passed, 51 deselected`
  - `cd web && npm run build` → `tsc && vite build` 成功
  - local `/health` probe：ports `8000/8001` 未啟動；本輪以 artifact + API contract tests + frontend build 驗證，不硬啟 dev runtime。

---

## 主目標
### A. Current-live exact-support blocker 不得被覆蓋
- 現況：q15 exact support `3/50`，gap `47`；`allowed_layers=0`。
- 成功標準：`/api/status`、Dashboard、Strategy Lab、Execution Status、probe、docs 都以 `under_minimum_exact_live_structure_bucket` 為唯一 current-live deployment blocker。
- 下一步：累積或回補同 semantic identity 的 exact current-bucket rows；legacy/broader/proxy rows 僅能 reference-only。

### B. Recent drift/root-cause 要與 blocker 同屏
- 現況：latest 100 window win rate `17.0%`，bear concentration `84.0%`。
- 已完成：Execution Status 補上 recent drift card。
- 下一步：下輪驗證 `/api/status.execution.recent_canonical_drift`、`execution_surface_contract.recent_canonical_drift`、Dashboard、Strategy Lab、Execution Status 一致。

### C. High-conviction Top-K 只能作 shadow lane
- 現況：`deployable_rows=0`，`runtime_blocked_candidate_rows=6`。
- 成功標準：任何 OOS-pass candidate 在 exact support / venue proof / reconciliation proof 未過前都只能 paper/shadow，不可 buy/add exposure。
- 下一步：保留最接近部署候選排序，但 gate 文案必須先顯示 runtime blocker 與 support gap。

### D. Venue/source readiness 補 runtime proof
- 現況：execution metadata smoke `all_ok=false`；venue proof 缺 credential/order-ack/fill lifecycle；sparse sources 有 auth/TLS blockers。
- 成功標準：OKX/Binance 每條 venue lane 有 runtime-backed proof artifact；source auth/TLS 修復後才允許 coverage/backfill gate 推進。

---

## 下一輪 gate
1. 重新跑 heartbeat / probe，確認 q15 support 是否仍 `3/50` 或有同 semantic identity rows 增長。
2. 以 browser 或 live API（若 backend 已啟動）檢查 `/execution/status`：部署診斷 → recent drift → 帳戶快照 的順序必須保持。
3. 驗證 high-conviction Top-K：`deployable_rows` 必須仍由 exact support + venue proof fail-closed 控制。
4. 針對 venue readiness 補一條 runtime-backed proof lane，優先 OKX order preview / ack simulation / cancel simulation。
5. 若 recent drift latest window 仍 `win_rate < 30%` 且 bear concentration 高，下一輪優先做 q15 exact bucket root-cause / evidence accumulation，而不是新增模型。

---

## 成功標準
- Deployment blocker 仍清楚：`under_minimum_exact_live_structure_bucket`。
- q15 support truth 仍清楚：`3/50 gap 47`（或下輪以 fresh artifact 更新）。
- Recent drift truth 已進入 Execution Status canonical diagnostics。
- OOS winner 不可繞過 runtime blocker。
- Docs 每輪 overwrite，且不保留歷史流水帳。
