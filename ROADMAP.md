# ROADMAP.md — Current Plan Only

_最後更新：2026-04-18 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- Heartbeat 主線已從「只做報告」轉向 **Execution / UX 產品化**
- `web/src/App.tsx` 已有 `⚡ 實戰交易` 導航與 `/execution` route
- `web/src/pages/ExecutionConsole.tsx` 已從 Dashboard 拆出營運視圖
- 本輪新增 `execution/console_overview.py` 與 `/api/execution/overview`
- Execution Console 現在可直接顯示：
  - bot profile cards
  - preview-only start contract
  - equal-split active sleeve capital preview
  - next operator action
- `ARCHITECTURE.md` 已同步新增 execution overview contract
- 驗證已完成：
  - `pytest tests/test_execution_console_overview.py tests/test_server_startup.py tests/test_frontend_decision_contract.py -q`
  - `cd web && npm run build`

---

## 主目標

### 目標 A：把 bot profile preview 升級成真正可操作的 run lifecycle
重點：
- 現在 `/api/execution/overview` 只提供 read-only preview
- start / pause / stop mutation 還不存在
- per-run event log / operator replay 還沒有正式 contract

成功標準：
- 新增 `/api/execution/runs` 與 start / pause / stop API
- run state 有 machine-readable event log
- Execution Console 可看到真實 run status，而不是 preview-only status

### 目標 B：把 capital preview 升級成 per-bot capital / position ledger
重點：
- 現在 deployable capital 只先用 `check_position_size()` 計算總量
- active sleeves 先用 `equal_split_active_sleeves` 做 preview budget
- positions / open orders 仍是 symbol-shared 視角

成功標準：
- bot profile / run / position / open order 可互相對應
- Execution Console 顯示每個 bot 的資金、持倉、掛單、PnL
- restart replay 與 reconciliation 可落到 per-bot scope

### 目標 C：把 Execution Console 變成真正操作入口，同時完成 IA 拆層
重點：
- manual trade / capital action 仍留在 Dashboard
- Strategy Lab 仍承載過多 execution diagnostics
- Dashboard / Execution Console / Strategy Lab 的分工尚未完全收斂

成功標準：
- manual trade / capital action 移到 `/execution`
- Strategy Lab 只保留研究 + runtime blocker sync
- Dashboard 保留 proof chain / recovery / venue diagnostics

### 目標 D：把 Binance / OKX readiness 從治理可見性推進到 venue-backed closure
重點：
- `live_ready` 仍為 false
- order ack / fill / cancel / restart replay 還缺真實 venue artifact

成功標準：
- Execution Console 與 Dashboard 都能 machine-read venue-backed closure evidence
- UI 明確區分 preview planning、可操作、可實盤放量三個層級

---

## 下一步
1. **先做 `/api/execution/runs` + start / pause / stop + event log**
   - 驗證：pytest API contract tests + Execution Console 顯示真實 run status
2. **再做 per-bot capital / position / order attribution**
   - 驗證：每張 bot card 都能顯示自己的 capital / positions / open orders / PnL
3. **最後搬 manual controls 並繼續瘦身 Strategy Lab diagnostics**
   - 驗證：`/execution` 成為主要操作入口；Strategy Lab 不再承載深度 proof-chain

---

## 成功標準
- `/api/execution/overview` 不再只是 preview-only，而是能銜接真實 run lifecycle
- Execution Console 不再只是 operator-view + preview card，而是可營運的 bot console
- Dashboard / Execution Console / Strategy Lab 各自只承擔一種主要問題
- Binance / OKX readiness 仍用真實 venue evidence 表示，不靠文案假裝 live-ready
