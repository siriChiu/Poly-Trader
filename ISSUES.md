# ISSUES.md — Current State Only

_最後更新：2026-04-18 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留舊流水帳。

---

## 當前主線
目前最重要的進展是：**Execution Console 已從 stateful run control beta 再往前推進到「run × runtime/recovery 鏡像」階段。**

本輪已完成：
- `ExecutionRun` 回傳新增 `runtime_binding_contract`
- `ExecutionRun` 回傳新增 `runtime_binding_snapshot`
- `/api/execution/runs` 與 `/api/execution/runs/{id}` 現在會把 **symbol-scoped runtime truth / account snapshot / reconciliation / guardrails** 鏡像到 run card
- Execution Console 現在會直接顯示：
  - shared-symbol runtime mirror 摘要
  - reconciliation status
  - last live order
  - operator action
- `profile_cards[].current_run` 與獨立 run list 已同步帶出這組鏡像 contract

已驗證：
- `pytest tests/test_server_startup.py tests/test_execution_console_overview.py tests/test_execution_run_control.py tests/test_frontend_decision_contract.py -q`
- `cd web && npm run build`

**目前定位必須講清楚：這仍是 control-plane beta + shared-symbol runtime mirror，不是 per-bot live runtime。**
run 已能看到 runtime / recovery 真相，但資金、倉位、掛單、成交與 replay ownership 仍未真正歸屬到單一 run。

---

## Open Issues

### P0. Run 已有 runtime mirror，但仍不是 per-bot runtime owner
**現況**
- run 已可持久化 start / pause / stop / event log
- run 已可鏡像 `/api/status` 的 symbol-scoped runtime / reconciliation
- 但 `runtime_binding_status` 仍是 `control_plane_only`，run 只是看到 shared-symbol 真相，不是擁有自己的 runtime

**風險**
- 若把 runtime mirror 誤讀成真正 run ownership，會再次產生「看起來像 bot console，底層仍是 shared execution surface」的假產品化

**下一步**
- 把 `ExecutionRun` 綁到 `ExecutionService`
- 讓 run 讀到自己的 lifecycle / recovery / order evidence，而不是全域 symbol 摘要
- 將 runtime mirror 升級成真正 run-bound contract

### P0. 資金 / 倉位 / 掛單仍是 shared-symbol preview，不是 per-bot ledger
**現況**
- budget 仍來自 `check_position_size()` + `equal_split_active_sleeves`
- run card 看到的是 shared-symbol position / open-order / last-order 鏡像
- 沒有真正 per-run capital / position / order attribution

**風險**
- 沒有 per-bot ledger，就無法做真 PnL、真資金占用、真 restart replay ownership

**下一步**
- 建立 per-bot capital attribution
- 把 positions / open orders / trade history 對應到 run / profile
- 讓 Execution Console 顯示真實 per-run capital / PnL，而不是 preview budget

### P1. Manual trade / capital actions 仍未收進 `/execution`
**現況**
- `/execution` 已有 bot card、run control、runtime mirror
- 但手動交易與資金操作入口仍未集中到同一頁

**風險**
- operator workflow 仍分裂在 Dashboard 與 Execution Console

**下一步**
- 把 manual trade / capital actions 移到 `/execution`
- 讓 run card、manual action、capital ledger 同頁完成

### P1. Strategy Lab 仍保留過多 execution diagnostics
**現況**
- Dashboard / Execution Console / Strategy Lab 的分工已比之前清楚
- 但 Strategy Lab 仍殘留部分 execution diagnostics 與治理提示

**風險**
- 研究頁與營運頁的心智模型仍未完全切乾淨

**下一步**
- 繼續把 execution diagnostics 收斂回 Dashboard / Execution Console
- Strategy Lab 只保留研究與 runtime blocker sync

### P1. Binance / OKX readiness 仍是治理可見性，不是 venue-backed closure
**現況**
- reconciliation / metadata smoke / venue lanes 已可見
- run 尚未擁有真實 venue ack / fill / cancel / restart replay artifact ownership

**風險**
- 即使 run card 更像產品，也不能誤寫成已可實盤放量

**下一步**
- 補真實 venue-backed ack / fill / cancel / restart replay artifact
- 讓 run card 與 venue readiness 一起顯示「可控」vs「可實盤」的明確邊界

---

## Not Issues
- 不是把 shared-symbol runtime mirror 包裝成 per-bot runtime
- 不是把 equal-split budget 當成正式資金帳本
- 不是只增加控制按鈕卻沒有 runtime / recovery 真相
- 不是為了增加 run 數量去放寬 gate / threshold

---

## Current Priority
1. **把 runtime mirror 升級成 run-bound execution ownership**
2. **把 shared-symbol capital / position / order preview 升級成 per-bot ledger**
3. **把 manual trade / capital actions 收進 `/execution`，完成 operator workflow 集中**
