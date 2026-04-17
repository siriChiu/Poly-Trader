# ISSUES.md — Current State Only

_最後更新：2026-04-18 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留舊流水帳。

---

## 當前主線
本輪把 `/execution` 往前推到 **shared-symbol ledger preview 可操作、可辨識邊界** 的狀態：
- `ExecutionRun.runtime_binding_contract` 現在帶 `ownership_boundary`
- `ExecutionRun.runtime_binding_snapshot` 現在帶 `capital_preview` 與 `shared_symbol_preview`
- Execution Console run/profile 卡現在直接顯示：
  - run budget vs shared balance
  - preview positions / preview open orders
  - ownership boundary（明確標示仍是 shared preview，不是假 per-bot ledger）

已驗證：
- `source venv/bin/activate && python -m pytest tests/test_execution_run_control.py tests/test_execution_console_overview.py tests/test_frontend_decision_contract.py tests/test_server_startup.py -q`
- `cd web && npm run build`

**目前定位仍必須講清楚：這是 operator-beta + shared preview clarity，不是 per-run ledger closure。**

---

## Open Issues

### P0. Run 仍不是 `ExecutionService` 的真正 runtime owner
**現況**
- run 已有 start / pause / stop / event log
- run 已能鏡像 runtime / reconciliation / shared-symbol ledger preview
- 但 run 還沒有真正擁有 order lifecycle、venue ack/fill/cancel、restart replay

**風險**
- 若把 mirror + preview 誤讀成 ownership，UI 仍會產生假產品化

**下一步**
- 把 `ExecutionRun` 綁到 `ExecutionService`
- 讓 lifecycle / recovery / replay / order evidence 落到 run scope

### P0. Capital / position / open-order 仍是 shared-symbol preview，沒有 per-run attribution
**現況**
- 本輪已把 shared preview 邊界 machine-read 化並顯示到 `/execution`
- 但 balance / positions / open orders / PnL 仍不是 per-run ledger
- 沒有真正 per-run 資金占用、已實現/未實現 PnL、open-order ownership

**風險**
- operator 能看懂「目前不是 run-owned」，但仍無法直接用單一 run 做資金/績效閉環

**下一步**
- 建立 per-run capital / position / open-order attribution
- 補 run-owned realized / unrealized / total PnL

### P1. `/execution` 還缺 capital actions 與策略快照
**現況**
- manual trade / automation toggle 已在 `/execution`
- 但充值 / 提現 / 調整部署資金 / strategy snapshot/version 仍未形成正式 operator contract

**風險**
- Execution Console 仍像操作台 beta，而不是完整 bot operations workspace

**下一步**
- 把 capital actions 收進 `/execution`
- 顯示 strategy source / snapshot / version，避免 run identity 模糊

### P1. Binance / OKX readiness 仍缺 venue-backed closure
**現況**
- reconciliation、metadata smoke、venue lanes 已可見
- 但 run 尚未擁有真實 venue-backed ack / fill / cancel / replay artifact ownership

**風險**
- 不能把現在的 surface 寫成 live-ready

**下一步**
- 將 venue-backed artifact 與 run scope 對齊
- 讓 `/execution` 與 Dashboard 都能直接顯示 run-owned venue closure

---

## Not Issues
- 不是把 shared-symbol preview 顯示得更完整，就等於 per-run ledger 完成
- 不是有 run event log，就等於 run 已擁有 execution lifecycle
- 不是有 manual trade / automation controls，就等於 execution console 已 live-ready

---

## Current Priority
1. **把 shared preview 升級成 per-run capital / position / open-order / PnL attribution**
2. **把 `ExecutionRun` 綁到 `ExecutionService`，形成 run-owned lifecycle / replay / recovery**
3. **把 capital actions 與 strategy snapshot/version 收進 `/execution`**
4. **補齊 Binance / OKX venue-backed closure evidence**
