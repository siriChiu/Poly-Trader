# ISSUES.md — Current State Only

_最後更新：2026-04-18 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留舊流水帳。

---

## 當前主線
目前最重要的進展是：**Execution Console 已從「run × runtime/recovery mirror」再往前推到「operator controls 進 `/execution`」階段。**

本輪已完成：
- `/execution` 現在直接承載 **manual trade controls**（買入 / 減碼）
- `/execution` 現在直接承載 **automation toggle**，不再只靠 Dashboard shortcut
- `/api/automation/toggle` 現在支援 **explicit `enabled=true/false`**，避免 operator surface 只能 blind toggle
- `Dashboard` 仍保留 canonical diagnostics / guardrail / recovery proof chain；`/execution` 負責 operator workflow

已驗證：
- `source venv/bin/activate && python -m pytest tests/test_server_startup.py tests/test_frontend_decision_contract.py -q`
- `cd web && npm run build`

**目前定位必須講清楚：這仍是 operations-beta，不是 live-ready execution closure。**
manual trade / automation controls 已集中到 `/execution`，但 capital / position / open-order / replay ownership 仍不是 per-run ledger。

---

## Open Issues

### P0. Run 仍是 runtime mirror，不是 per-bot runtime owner
**現況**
- `ExecutionRun` 已可 start / pause / stop，並鏡像 symbol-scoped runtime / reconciliation / last order
- `runtime_binding_status` 仍是 `control_plane_only`
- run card 看到的仍是 shared-symbol truth，不是 run 自己擁有的 execution lifecycle

**風險**
- 若把 mirror 誤讀成 ownership，會再次出現「UI 看起來像 bot console，底層其實還是 shared execution surface」的假產品化

**下一步**
- 把 `ExecutionRun` 綁到 `ExecutionService`
- 讓 lifecycle / recovery / replay / order evidence 落到 run scope
- 將 runtime mirror 升級成真正 run-bound contract

### P0. Capital / position / open-order 仍是 shared-symbol preview
**現況**
- `/execution` 已能顯示 capital preview、account snapshot、manual trade controls、automation toggle
- 但 budget 仍來自 preview allocation，positions / open orders / trade history 仍是 symbol-shared
- 尚無真正 per-run capital attribution、PnL、restart replay ownership

**風險**
- 沒有 per-bot ledger，就無法把 operator actions、資金占用與實際風控閉環到單一 run

**下一步**
- 建立 per-run capital / position / order attribution
- 讓 Execution Console 顯示真實 per-run capital、PnL、open orders，而不是 shared preview

### P1. Capital actions 尚未進 `/execution`
**現況**
- manual trade 與 automation toggle 已搬到 `/execution`
- 但充值 / 提現 / 調整部署資金 / run-owned ledger action 仍未有正式 operator contract

**風險**
- operator workflow 還沒真正收斂成單頁閉環；目前只完成交易控制，尚未完成資金控制

**下一步**
- 把 capital actions 與 ledger events 納入 `/execution`
- 讓 manual trade / capital action / run ledger 成為同一頁工作流

### P1. Binance / OKX readiness 仍缺 venue-backed closure
**現況**
- metadata smoke、reconciliation、lane drilldown 已可見
- 但 run 尚未擁有真實 venue ack / fill / cancel / restart replay artifact ownership

**風險**
- 即使 `/execution` 更像 operator workspace，也不能誤寫成可實盤放量

**下一步**
- 把 venue-backed ack / fill / cancel / replay artifact 綁到 run scope
- 讓 `/execution` 與 Dashboard 都能明確分辨 control-plane beta vs venue-backed closure

---

## Not Issues
- 不是把 `/execution` 的 manual controls 包裝成 per-bot ledger 完成
- 不是把 shared-symbol capital preview 當成正式資金帳本
- 不是把 runtime mirror 誤寫成 run ownership
- 不是因為有 automation toggle 就宣稱 live-ready

---

## Current Priority
1. **把 run mirror 升級成 run-owned execution lifecycle**
2. **把 shared-symbol capital / position / open-order preview 升級成 per-run ledger**
3. **把 capital actions 收進 `/execution`，完成 operator workflow 集中**
4. **補齊 Binance / OKX venue-backed closure evidence**
