# ISSUES.md — Current State Only

_最後更新：2026-05-18 01:22:23 CST_

本文件只保留目前仍有效的產品化問題與本輪驗證事實；歷史流水帳已移出 current-state issue 面。

---

## 當前產品事實
- **Heartbeat #1314-productization**：runner 成功，`Raw=33499 / Features=24609 / Labels=66808`，`simulated_pyramid_win=56.65%`。
- **唯一 current-live deployment blocker**：`under_minimum_exact_live_structure_bucket`。
- **current live bucket**：`CAUTION|structure_quality_caution|q15`，exact support `3/50`，gap `47`。
- **support route**：`exact_bucket_present_but_below_minimum`；governance route=`exact_live_bucket_present_but_below_minimum`。
- **runtime posture**：`allowed_layers_raw=1 → allowed_layers=0`，reason=`under_minimum_exact_live_structure_bucket`；`runtime_closure_state=patch_inactive_or_blocked`。
- **recent canonical drift**：latest window `100`，wins/losses=`17/83`，win rate=`17.0%`，dominant regime=`bear` (`84.0%`)，alerts=`label_imbalance, regime_shift`。
- **high-conviction Top-K**：`deployable_rows=0`，`risk_qualified_rows=6`，`runtime_blocked_candidate_rows=6`；所有候選仍只能 paper/shadow，不可送單。
- **venue/source readiness**：execution metadata smoke `all_ok=false`，`ok_count=1/2 venues`；OKX/Binance runtime-backed credential/order-ack/fill lifecycle proof 仍未閉環；稀疏來源仍有 auth/TLS blocker，敏感設定以 `[REDACTED]` 顯示。

---

## 本輪已落地產品化修補
### Execution Status 顯示 recent canonical drift（已修）
- 問題：`/execution/status` 已是 canonical diagnostics page，但只顯示部署阻塞、帳戶、venue readiness；recent canonical drift 只在其他 surface / artifact，operator 可能看見 q15 support blocker 卻看不到造成 blocker 的 recent drift 切片。
- 修補：`web/src/pages/ExecutionStatus.tsx` 直接消費 `/api/status` 的 `execution.recent_canonical_drift → execution_surface_contract.recent_canonical_drift → recent_canonical_drift` fallback chain，並在「部署診斷」後、「帳戶快照」前渲染 `RecentCanonicalDriftCard`。
- 鎖定：新增 `tests/test_frontend_decision_contract.py::test_execution_status_surfaces_recent_canonical_drift_between_deployment_and_account_snapshot`，確保卡片位置與 fallback contract 不回退。

---

## Open Issues
### P0 — q15 current-live exact support under minimum blocks deployment
- 現況：`CAUTION|structure_quality_caution|q15` exact support `3/50`，gap `47`。
- 產品要求：任何 UI/API/文件都不得把 broader/proxy/legacy support、OOS candidate、或 venue metadata OK 誤讀成 deployment closure。
- 下一步：累積或回補同 semantic identity 的 exact current-bucket rows；若使用 legacy evidence，必須保留 `reference-only` 與 semantic mismatch 說明。

### P0 — Recent drift/root-cause 必須與 blocker 同屏可見
- 現況：latest 100 window win rate `17.0%`、bear concentration `84.0%`、`label_imbalance + regime_shift`。
- 已修：`/execution/status` 現在與 Dashboard/Strategy Lab 一樣顯示 recent drift card。
- 下一步：下輪若 drift artifact 或 API payload 缺 `primary_window/blocking_window/canonical_tail_root_cause`，升級為產品 blocker。

### P1 — High-conviction Top-K 仍是 runtime-blocked shadow lane
- 現況：`deployable_rows=0`，`runtime_blocked_candidate_rows=6`；最近候選雖有 OOS pass/ROI 線索，但 exact support gate 未過。
- 下一步：維持 paper/shadow-only；只有 exact support、venue proof、reconciliation proof 全過後才允許小流量 canary。

### P1 — OKX/Binance venue readiness 尚未有 runtime-backed proof
- 現況：metadata row 可見，但 credential / order ack / fill lifecycle / restart replay proof 尚未閉環。
- 下一步：補 per-venue proof artifacts；unsupported/disabled venue 必須保持 fail-closed。

### P1 — Sparse source credentials/TLS blockers
- 現況：`fin_netflow` auth missing、`claw/claw_intensity` auth missing、`nest_pred` verified TLS trust failure；forward archive 存在但無法替代成功快照。
- 下一步：修 credentials/TLS trust chain 後再評估 coverage/backfill。

---

## 當前優先序
1. 保持 `under_minimum_exact_live_structure_bucket` 為唯一 current-live deployment blocker。
2. 讓 q15 support `3/50 gap 47` 與 recent drift `17/83, bear 84%` 在 `/api/status`、Dashboard、Strategy Lab、Execution Status、docs 同步可見。
3. 守住 high-conviction Top-K 的 fail-closed shadow-only contract。
4. 補 venue runtime proof 與 sparse source auth/TLS，而不是用 metadata OK 或 broader rows 取代部署閉環。
