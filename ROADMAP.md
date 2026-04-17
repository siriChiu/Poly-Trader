# ROADMAP.md — Current Plan Only

_最後更新：2026-04-18 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- `web/src/App.tsx` 已有 `/execution` route，Execution Console 與 Dashboard 正式分流
- `/api/execution/overview`、`/api/execution/profiles`、`/api/execution/runs` 已形成 stateful run control beta
- run card 已鏡像 shared-symbol runtime / reconciliation / last-order truth
- **本輪完成 `/execution` operator controls**：
  - manual trade（買入 / 減碼）已進 Execution Console
  - automation toggle 已進 Execution Console
  - `/api/automation/toggle` 支援 explicit `enabled=true/false`，保留 legacy toggle fallback
- 已驗證：
  - `source venv/bin/activate && python -m pytest tests/test_server_startup.py tests/test_frontend_decision_contract.py -q`
  - `cd web && npm run build`

---

## 主目標

### 目標 A：把 run mirror 升級成真正的 run-owned execution lifecycle
重點：
- 現在 run 已可持久化 start / pause / stop / event log
- run 已可鏡像 symbol-scoped runtime / reconciliation / last-order truth
- 但 run 尚未綁到 `ExecutionService`，也還沒有自己的 replay / recovery ownership

成功標準：
- `ExecutionRun` 綁到 `ExecutionService`
- 每個 run 都能看到自己的 lifecycle / recovery / replay / order evidence
- UI 不再把 shared-symbol runtime mirror 誤讀成 live bot runtime

### 目標 B：把 shared-symbol preview 升級成 per-run capital / position / order ledger
重點：
- capital 仍是 preview allocation
- positions / open orders / trade history 仍是 symbol-shared
- 沒有真正 per-run PnL 與資金占用

成功標準：
- bot profile / run / capital / position / order 可互相對應
- Execution Console 顯示 per-run capital / positions / open orders / PnL
- restart replay 與 reconciliation 落到 run scope

### 目標 C：完成 `/execution` 的 operator workflow closure
重點：
- manual trade 與 automation toggle 已搬進 `/execution`
- 但 capital actions、ledger events、run-owned capital workflow 尚未進來
- Dashboard 仍需保持 diagnostics-only，不回退成 operator workspace

成功標準：
- capital actions / ledger events 移到 `/execution`
- run card、manual action、capital ledger 同頁完成
- Dashboard 回到 canonical diagnostics / proof-chain surface

### 目標 D：把 venue readiness 從治理可見性推進到 venue-backed closure
重點：
- metadata smoke / reconciliation / venue lanes 已可見
- 但 run 尚未帶真實 venue ack / fill / cancel / replay artifact ownership

成功標準：
- `/execution` 與 Dashboard 都能 machine-read run-scoped venue artifact
- UI 明確區分 control-plane beta、run-owned runtime、venue-backed closure 三個層級

---

## 下一步
1. **先做 per-run capital / position / open-order attribution**
   - 驗證：pytest API contract tests + `/execution` 顯示 run-owned capital / positions / open orders
2. **再把 run lifecycle 綁到 `ExecutionService` / reconciliation / replay**
   - 驗證：run card 能看到自己的 lifecycle / replay / recovery 狀態，而不是只看全域 symbol 摘要
3. **最後把 capital actions / ledger events 收進 `/execution`，並保持 Dashboard diagnostics-only**
   - 驗證：`/execution` 成為主要 operator workspace；Dashboard 只留 diagnostics / proof chain

---

## 成功標準
- `/api/execution/overview` + `/api/execution/runs` 一起構成真實、可持久化的 operator contract
- Execution Console 不再只是 preview + mirror，而是能管理 run lifecycle、manual trade、automation、capital workflow 的 trading operations surface
- run card 顯示的 capital / PnL / positions / replay 狀態都屬於該 run 本身，不是 symbol-shared 假對應
- Binance / OKX readiness 仍以真實 venue evidence 表示，不靠文案假裝 live-ready
