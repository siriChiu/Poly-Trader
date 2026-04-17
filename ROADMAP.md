# ROADMAP.md — Current Plan Only

_最後更新：2026-04-18 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- Heartbeat 主線已從「只做報告」轉向 **Execution / UX 產品化**
- `web/src/App.tsx` 新增 `⚡ 實戰交易` 導航與 `/execution` route
- 新增 `web/src/pages/ExecutionConsole.tsx`，把以下 execution 資訊從 Dashboard 拆成獨立營運視圖：
  - live runtime truth
  - sleeve routing / bot activation
  - account snapshot
  - reconciliation / recovery 摘要
  - metadata / venue readiness
- `/api/status` 現在回傳完整的 execution route split contract：
  - `operations_surface`
  - `diagnostics_surface`
  - `symbol`
  - `timestamp`
  - `account`
- Dashboard / Strategy Lab 已加入前往 Execution Console 的導流與語義同步
- 驗證已完成：
  - `pytest tests/test_server_startup.py tests/test_frontend_decision_contract.py -q`
  - `cd web && npm run build`

---

## 主目標

### 目標 A：把 Execution Console 從 operator-view 升級成真正可營運的 bot console
重點：
- 目前 `/execution` 只有 runtime truth / blocker / snapshot / reconciliation
- 還沒有 bot profile / run lifecycle
- 還沒有 capital allocation / per-bot PnL / start-pause-stop contract

成功標準：
- 新增 execution profiles / runs / events model
- 提供 `/api/execution/*` APIs
- Execution Console 可建立 bot、配置資金、查看 run 狀態、開始 / 暫停 / 停止
- sleeve routing 直接影響 bot activation，而不只是顯示文字

### 目標 B：完成 Dashboard / Strategy Lab / Execution Console / Diagnostics 的資訊架構拆層
重點：
- Dashboard 保留 execution diagnostics / proof chain / guardrail / recovery
- Execution Console 承擔 trading operations
- Strategy Lab 只保留策略研究與 runtime blocker sync
- 不再讓研究頁持續膨脹成另一個 diagnostics wall

成功標準：
- 使用者能明確分辨：研究、營運、診斷三條路徑
- Strategy Lab 不再承載深度 reconciliation / venue lane drilldown
- 後續若新增 Diagnostics workspace，也不會與 Execution Console 重疊

### 目標 C：把可操作入口逐步搬進 Execution Console，但不誇大 live readiness
重點：
- manual trade / capital actions 仍在 Dashboard
- Binance / OKX venue readiness 仍是治理可見性，不是實盤 closure

成功標準：
- Execution Console 顯示清楚的操作入口與 live blockers
- order ack / fill / restart replay 有 venue-backed evidence
- UI 能明確區分「可操作」與「可實盤放量」

---

## 下一步
1. **先做 execution profiles / runs / events + `/api/execution/*`**
   - 驗證：pytest + API contract tests + Execution Console UI 可顯示多 bot card
2. **再把 sleeve routing 接成 bot activation contract**
   - 驗證：active/inactive sleeves 會影響 bot start/stop 可行性與說明
3. **最後把 Strategy Lab 的 execution diagnostics 再瘦身**
   - 驗證：Strategy Lab 僅保留 blocker sync；更深 recovery/proof chain 留在 Dashboard/Diagnostics

---

## 成功標準
- `/execution` 不再只是 status mirror，而是可營運的 bot console
- Dashboard / Strategy Lab / Execution Console 各自只承擔一種主要問題
- `/api/status` 與 `/api/execution/*` 共用同一份 runtime truth，不再出現雙重語義
- Binance / OKX readiness 用真實 venue evidence 表示，而不是靠文案假裝 live-ready
