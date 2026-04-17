# ROADMAP.md — Current Plan Only

_最後更新：2026-04-18 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- `/execution` 已是獨立 operator surface，承載 run control、manual trade、automation toggle、capital preview
- `ExecutionRun` 已有 stateful start / pause / stop / event log
- run 已能鏡像 runtime / reconciliation / account snapshot / last-order truth
- **本輪完成 shared-symbol ledger preview productization**：
  - `runtime_binding_contract.ownership_boundary`
  - `runtime_binding_snapshot.capital_preview`
  - `runtime_binding_snapshot.shared_symbol_preview`
  - Execution Console 直接顯示 run budget vs shared balance、preview positions、preview open orders
- 已驗證：
  - `source venv/bin/activate && python -m pytest tests/test_execution_run_control.py tests/test_execution_console_overview.py tests/test_frontend_decision_contract.py tests/test_server_startup.py -q`
  - `cd web && npm run build`

---

## 主目標

### 目標 A：把 shared preview 升級成真正的 per-run ledger
重點：
- 本輪已把 ownership boundary 與 shared preview 顯示清楚
- 下一步不是再加文案，而是把 balance / positions / open orders / PnL 真的歸屬到 run

成功標準：
- 每個 run 有自己的 capital / position / open-order attribution
- Execution Console 顯示 per-run realized / unrealized / total PnL
- shared preview 退回輔助資訊，不再是主體

### 目標 B：把 run mirror 升級成 run-owned execution lifecycle
重點：
- run 目前仍是 control-plane + runtime mirror
- 尚未擁有 order lifecycle、venue ack/fill/cancel、restart replay ownership

成功標準：
- `ExecutionRun` 綁到 `ExecutionService`
- lifecycle / recovery / replay / venue artifact 都可在 run scope 驗證
- UI 不再把 mirror 誤讀成 bot owner

### 目標 C：完成 `/execution` 的 operator workflow closure
重點：
- manual trade / automation 已進 `/execution`
- capital actions、strategy snapshot/version、run-owned capital workflow 仍未進來

成功標準：
- capital actions / ledger events 移到 `/execution`
- bot card 顯示 strategy source / snapshot / version
- Dashboard 回到 diagnostics / proof chain，`/execution` 成為主要 operator workspace

### 目標 D：把 venue readiness 推進到 run-owned closure
重點：
- reconciliation / metadata smoke / venue lanes 已可見
- 但 run 還沒有真實 venue-backed artifact ownership

成功標準：
- `/execution` 與 Dashboard 都能 machine-read run-owned venue artifact
- 清楚區分 control-plane beta、shared preview、run-owned runtime、venue-backed closure 四個層級

---

## 下一步
1. **先做 per-run capital / position / open-order / PnL attribution**
   - 驗證：pytest API contract tests + `/execution` 顯示 run-owned ledger，而非 shared preview
2. **再把 `ExecutionRun` 綁到 `ExecutionService` / reconciliation / replay**
   - 驗證：run card 能看到自己的 lifecycle / replay / recovery / venue artifact
3. **最後把 capital actions + strategy snapshot/version 收進 `/execution`**
   - 驗證：`/execution` 成為完整 operator workflow；Dashboard 保持 diagnostics-only

---

## 成功標準
- `/api/execution/overview` + `/api/execution/runs` + `ExecutionService` 一起構成真實 run-owned operator contract
- Execution Console 顯示 per-run capital / positions / open orders / PnL / lifecycle，而不是 shared preview
- run card 的 runtime / reconciliation / venue artifact 屬於該 run 本身
- Binance / OKX readiness 仍以真實 venue evidence 表示，不靠文案假裝 live-ready
