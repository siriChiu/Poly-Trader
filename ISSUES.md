# ISSUES.md — Current State Only

_最後更新：2026-04-18 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留舊流水帳。

---

## 當前主線
目前最重要的進展是：**Execution Console 已不只看 `/api/status`；現在新增 `/api/execution/overview`，把 bot profile / capital preview 變成 machine-readable contract。**

本輪已完成：
- 新增 `execution/console_overview.py`
- 新增 `/api/execution/overview`
- `web/src/pages/ExecutionConsole.tsx` 現在會直接顯示：
  - bot profile cards
  - preview-only start contract
  - equal-split active sleeve capital preview
  - next operator action
- 已把這個 contract 回寫到 `ARCHITECTURE.md`
- 驗證完成：
  - `pytest tests/test_execution_console_overview.py tests/test_server_startup.py tests/test_frontend_decision_contract.py -q`
  - `cd web && npm run build`

這代表 Poly-Trader 的 Execution Console 已從「只有 runtime / blocker / snapshot」前進到 **第一版 bot/card/capital 規劃面**；但它仍是 **preview-only operations contract**，不是可直接 start/pause/stop 的真 bot control plane。

---

## Open Issues

### P0. `/api/execution/overview` 仍是 preview-only，mutable bot lifecycle 尚未落地
**現況**
- 已有 machine-readable bot profile cards 與 capital preview
- 但還沒有真正的 `/api/execution/runs` / start / pause / stop mutation contract
- `control_contract` 目前仍明確標示 `preview_only`

**風險**
- 若把這批卡片誤讀成真 bot lifecycle，就會產生「看起來可營運、實際不能控 bot」的假產品化

**下一步**
- 新增 `/api/execution/runs` 與真正的 start / pause / stop API
- 為 run lifecycle 建立 event log 與 operator replay surface
- 讓 Execution Console 能看到真實 run state，而不是 preview state

### P0. 資金分配仍是 shared-symbol preview，不是 per-bot ledger
**現況**
- 本輪 capital preview 先用 `risk_control.check_position_size()` 算 deployable capital
- active sleeves 目前只做 `equal_split_active_sleeves` 預覽分配
- 持倉 / 掛單仍是 symbol-scoped shared view，還不能歸屬到各 bot

**風險**
- 沒有 per-bot capital / position attribution，就無法做真 PnL、真 run ownership、真 restart replay

**下一步**
- 建立 per-bot capital ledger / position attribution
- 讓 open orders / positions / last order 可以對應到 bot profile/run
- 把 equal-split preview 升級成真正可追蹤的資金配置契約

### P1. Manual trade controls 仍在 Dashboard，Execution Console 還不是完整操作入口
**現況**
- `/execution` 已有 bot profile preview、runtime truth、reconciliation、venue readiness
- 但實際 manual trade / capital action 還沒搬過來

**風險**
- 營運資訊與操作入口仍分裂，Execution Console 還不像完整的 trading workspace

**下一步**
- 將 manual trade / capital action 搬進 `/execution`
- 讓操作入口與 bot run card 同頁呈現

### P1. Strategy Lab 仍承載過多 execution diagnostics
**現況**
- Strategy Lab 已同步 runtime blocker / sleeve activation truth
- 但 proof-chain / reconciliation / venue lane 內容仍然偏多

**風險**
- 研究頁、營運頁、診斷頁的資訊架構仍未完全切乾淨

**下一步**
- 繼續把深度 execution diagnostics 收斂回 Dashboard / Diagnostics
- Strategy Lab 只保留策略研究與 runtime blocker sync

### P1. Binance / OKX readiness 仍是治理可見性，不是 venue-backed live closure
**現況**
- metadata smoke、reconciliation、venue lane remediation 已可見
- `live_ready` 仍為 false；order ack / fill / restart replay 仍未完成 venue-backed closure

**風險**
- 即使 Execution Console 更像產品，也不能把它誤寫成已可實盤放量

**下一步**
- 補真實 venue-backed ack / fill / cancel / restart replay artifact
- 讓 bot card 與 venue readiness 一起顯示「可規劃」vs「可實盤」的明確分界

---

## Not Issues
- 不是把 preview-only bot cards 包裝成已可控 bot runtime
- 不是把 equal-split capital preview 當成最終正式風控模型
- 不是再把更多 proof-chain 卡片塞回 Execution Console 或 Strategy Lab
- 不是只擴充 `/api/execution/*` 命名空間卻沒有 machine-readable operator contract

---

## Current Priority
1. **落地真正的 `/api/execution/runs` + start / pause / stop + event log**
2. **把 shared-symbol capital / position preview 升級成 per-bot ledger / attribution**
3. **把 manual trade controls 移到 `/execution`，並繼續瘦身 Strategy Lab diagnostics**
