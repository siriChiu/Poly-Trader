# ROADMAP.md — Current Plan Only

_最後更新：2026-04-18 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- `/execution` 已是獨立 operator surface，承載 run control、manual trade、automation toggle、capital preview
- `ExecutionRun` 已有 stateful start / pause / stop / event log
- run 已能鏡像 runtime / reconciliation / account snapshot / last-order truth
- shared-symbol preview 邊界已 machine-read 化並顯示到 `/execution`
- **本輪完成 strategy snapshot / version surface closure**：
  - `GET /api/execution/strategies/source`
  - `/api/execution/overview` 的 `strategy_source_summary`
  - profile card `strategy_binding`
  - run card `strategy_binding`
  - 未覆蓋 sleeve 以 `missing_saved_strategy` 明示，而不是隱性預設
- 已驗證：
  - `source venv/bin/activate && python -m pytest tests/test_execution_run_control.py tests/test_execution_console_overview.py tests/test_frontend_decision_contract.py tests/test_server_startup.py -q`
  - `cd web && npm run build`

---

## 主目標

### 目標 A：把 shared preview 升級成真正的 per-run ledger
重點：
- 目前 `/execution` 已能清楚顯示 strategy version 與 shared preview 邊界
- 下一步不是再補文案，而是把 balance / positions / open orders / PnL 真的歸屬到 run

成功標準：
- 每個 run 有自己的 capital / position / open-order attribution
- Execution Console 顯示 per-run realized / unrealized / total PnL
- shared preview 退回輔助資訊，不再是主體

### 目標 B：把 run mirror 升級成 run-owned execution lifecycle
重點：
- run 目前仍是 control-plane + runtime mirror + strategy version visibility
- 尚未擁有 order lifecycle、venue ack / fill / cancel、restart replay ownership

成功標準：
- `ExecutionRun` 綁到 `ExecutionService`
- lifecycle / recovery / replay / venue artifact 都可在 run scope 驗證
- UI 不再把 mirror 誤讀成 bot owner

### 目標 C：完成 `/execution` 的 operator workflow closure
重點：
- manual trade / automation 已進 `/execution`
- strategy source / snapshot 已可見
- capital actions 與缺失 strategy coverage 的補齊流程仍未進來

成功標準：
- capital actions / ledger events 移到 `/execution`
- operator 能直接處理 missing strategy snapshot coverage
- `/execution` 成為完整 operator workflow；Dashboard 保持 diagnostics-only

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
2. **再把 `ExecutionRun` 綁到 `ExecutionService` / reconciliation / replay / venue artifact**
   - 驗證：run card 能看到自己的 lifecycle / replay / recovery / venue evidence
3. **最後把 capital actions + strategy coverage closure 收進 `/execution`**
   - 驗證：operator 不必離開 `/execution` 就能完成資金操作與缺失 strategy snapshot 補齊

---

## 成功標準
- `/api/execution/overview` + `/api/execution/runs` + `/api/execution/strategies/source` + `ExecutionService` 一起構成真實 run-owned operator contract
- Execution Console 顯示 per-run capital / positions / open orders / PnL / lifecycle / strategy binding，而不是 shared preview 拼裝畫面
- run card 的 runtime / reconciliation / venue artifact 屬於該 run 本身
- Binance / OKX readiness 仍以真實 venue evidence 表示，不靠文案假裝 live-ready
