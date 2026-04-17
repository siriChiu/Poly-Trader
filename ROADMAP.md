# ROADMAP.md — Current Plan Only

_最後更新：2026-04-18 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- Heartbeat 主線已從「只做報告」轉向 **Execution / UX 產品化**
- `web/src/App.tsx` 已有 `⚡ 實戰交易` 導航與 `/execution` route
- `web/src/pages/ExecutionConsole.tsx` 已從 Dashboard 拆出營運視圖
- `execution/console_overview.py` + `/api/execution/overview` 已把 runtime truth 轉成 bot profile / capital preview
- `/api/execution/profiles`、`/api/execution/runs`、`start / pause / stop / detail` 已落地 stateful run control beta
- **本輪完成 run × runtime/recovery mirror：**
  - `ExecutionRun.runtime_binding_contract`
  - `ExecutionRun.runtime_binding_snapshot`
  - run card / profile card 顯示 shared-symbol runtime mirror、reconciliation status、last live order、operator action
- 已驗證：
  - `pytest tests/test_server_startup.py tests/test_execution_console_overview.py tests/test_execution_run_control.py tests/test_frontend_decision_contract.py -q`
  - `cd web && npm run build`

---

## 主目標

### 目標 A：把 runtime mirror 升級成真正的 runtime-bound bot lifecycle
重點：
- 現在 run 已可持久化 start / pause / stop / event log
- run 已可鏡像 symbol-scoped runtime / reconciliation
- 但 run 尚未擁有自己的 execution ownership

成功標準：
- `ExecutionRun` 綁到 `ExecutionService`
- 每個 run 都能看到自己的 lifecycle / recovery / order evidence
- UI 不再把 shared-symbol runtime mirror 誤讀成 live bot runtime

### 目標 B：把 shared-symbol preview 升級成 per-bot capital / position / order ledger
重點：
- budget 仍是 preview number
- positions / open orders / trade history 仍是 symbol-shared
- 沒有真正 per-run PnL 與資金占用

成功標準：
- bot profile / run / capital / position / order 可互相對應
- Execution Console 顯示 per-run capital / positions / open orders / PnL
- restart replay 與 reconciliation 可落到 run scope

### 目標 C：把 `/execution` 變成主要 operator workspace
重點：
- run control beta 與 runtime mirror 已經在 `/execution`
- 但 manual trade / capital actions 仍未完全搬過來
- operator workflow 仍分裂在 Dashboard / Execution Console

成功標準：
- manual trade / capital actions 移到 `/execution`
- run card、manual action、capital ledger 同頁完成
- Dashboard 回到 canonical diagnostics / proof-chain surface

### 目標 D：把 venue readiness 從治理可見性推進到 venue-backed closure
重點：
- reconciliation / metadata smoke / venue lanes 已可見
- 但 run 尚未帶真實 venue ack / fill / cancel / replay artifact

成功標準：
- Execution Console 與 Dashboard 都能 machine-read run-scoped venue artifact
- UI 明確區分 control-plane beta、runtime-bound、venue-backed live closure 三個層級

---

## 下一步
1. **先做 per-bot capital / position / order attribution，讓 run 不再只是 shared-symbol mirror**
   - 驗證：pytest API contract tests + Execution Console 顯示 per-run capital / positions / open orders
2. **再把 run lifecycle 綁到 `ExecutionService` / reconciliation / recovery**
   - 驗證：run card 能看到自己的 lifecycle / replay / recovery 狀態，而不是只看全域 symbol 摘要
3. **最後把 manual trade / capital actions 收進 `/execution`，並保持 Dashboard / Strategy Lab IA 收斂**
   - 驗證：`/execution` 成為主要操作入口；Dashboard 回 diagnostics；Strategy Lab 不再承載深度 execution diagnostics

---

## 成功標準
- `/api/execution/overview` + `/api/execution/runs` 一起構成真實、可持久化的 operator contract
- Execution Console 不再只是 preview card，而是可管理 run lifecycle 並看見 runtime / recovery 真相的 trading operations surface
- run card 顯示的 capital / PnL / positions / replay 狀態都屬於該 run 本身，不是 symbol-shared 假對應
- Binance / OKX readiness 仍以真實 venue evidence 表示，不靠文案假裝 live-ready
