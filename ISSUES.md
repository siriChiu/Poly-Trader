# ISSUES.md — Current State Only

_最後更新：2026-04-18 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留舊流水帳。

---

## 當前主線
目前最重要的進展是：**Execution Console 第一版已從 Dashboard 拆出來，並直接吃 `/api/status` 的 runtime truth。**

本輪已完成：
- `web/src/App.tsx` 新增 `⚡ 實戰交易` 導航與 `/execution` route
- `web/src/pages/ExecutionConsole.tsx` 落地第一版營運視圖：
  - live runtime truth
  - sleeve routing / bot activation
  - account snapshot
  - reconciliation / recovery 摘要
  - metadata / venue readiness
- `/api/status` 現在明確回傳：
  - `symbol`
  - `timestamp`
  - `account`
  - `execution_surface_contract.operations_surface`
  - `execution_surface_contract.diagnostics_surface`
- Dashboard / Strategy Lab 已能明確導向 Execution Console，而不是只說「未來會有」

這代表 Poly-Trader 已不再只有 Dashboard 這個混合型 execution surface；**營運視圖與診斷視圖開始真正拆層**。

---

## Open Issues

### P0. Execution Console 仍是 operator-view shell，尚未接上 bot lifecycle / capital allocation
**現況**
- `/execution` 已存在，但目前仍以 runtime truth / snapshot / blocker / reconciliation 為主
- sleeve routing 已可視化，但還沒有真的 bot profile / run / start / pause / stop contract
- 也還沒有 per-bot capital、PnL、run status 卡片

**風險**
- 使用者已能進入實戰頁，但還不能在同一頁完成真正的策略營運閉環
- 若太早把它包裝成完整 execution console，會誤導成「已可多 bot 營運」

**下一步**
- 新增 execution profiles / runs / events 資料模型與 `/api/execution/*` APIs
- 把 sleeve routing 從「顯示建議 active sleeves」升級成「實際 bot activation contract」
- 將資金配置、run status、PnL 明確落到 bot card

### P0. Diagnostics 與 operations 雖已拆第一刀，但 Strategy Lab 仍帶太多 execution proof-chain 內容
**現況**
- Dashboard 仍是 canonical diagnostics / proof-chain surface
- Strategy Lab 已新增前往 Execution Console 的連結
- 但 Strategy Lab 仍承載大量 reconciliation / lifecycle / venue lane 細節

**風險**
- 研究頁、營運頁、診斷頁三種心智仍未完全切乾淨
- 後續若再加入 bot lifecycle，資訊架構會再次打結

**下一步**
- 把 Strategy Lab 保留在 runtime blocker sync / strategy context
- 將 deeper reconciliation / venue lane drilldown 收斂到 Dashboard 或獨立 Diagnostics workspace

### P1. 手動交易 controls 仍留在 Dashboard，尚未搬進 Execution Console
**現況**
- Execution Console 已有 route contract / blocker truth / account snapshot
- 但真正可操作的 manual trade controls 仍在 Dashboard

**風險**
- 營運入口與操作入口分裂，Execution Console 仍不像完整的交易工作區

**下一步**
- 等 execution profile/run contract 定型後，把 manual trade / capital actions 一起搬到 `/execution`
- Dashboard 保留 proof chain、guardrail、recovery、artifact drilldown

### P1. Binance / OKX readiness 仍停留在治理可見性，不是 live-ready
**現況**
- metadata smoke / reconciliation / guardrail surface 已可見
- `live_ready` 仍為 false；order ack / fill lifecycle 尚未被實證關閉

**風險**
- UI 若只看到 execution route 擴充，容易誤讀成 venue 已可實盤放量

**下一步**
- 繼續補 order ack / fill / restart replay 的 venue-backed evidence
- 讓 Execution Console 顯示「可操作」與「可實盤」的明確分界

---

## Not Issues
- 不是再把更多 diagnostics 卡片塞回 Strategy Lab 或 Execution Console
- 不是靠降低 gate / confidence / entry threshold 來製造更多交易動作
- 不是把 `/execution` 做成 Dashboard 的文字鏡像後就宣稱產品化完成

---

## Current Priority
1. 把 **Execution Console 接上 bot profile/run lifecycle + capital allocation**
2. 把 **Strategy Lab 的 execution diagnostics 再瘦身，完成 IA 拆層**
3. 把 **Binance / OKX 的 venue-backed execution evidence** 從治理可見性推進到可操作驗證
