# ISSUES.md — Current State Only

_最後更新：2026-04-17 02:46 +08:00_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留舊流水帳。

---

## 當前主線
Poly-Trader 目前 heartbeat 主線是 **execution / Dashboard / Strategy Lab 的產品化閉環**。

本輪已完成的直接產品化前進：
- `/api/status` 新增 **execution reconciliation summary**
- Dashboard 新增 **Execution reconciliation / recovery** 區塊
- runtime `last_order` 現在保留 `order_id / client_order_id`
- 對帳面板可直接顯示：
  - snapshot freshness
  - symbol scope 對齊
  - trade history 對帳狀態
  - open-order audit 狀態
  - current issues / mismatch reason

---

## Open Issues

### P0. execution reconciliation 仍只有 summary，還不是完整 lifecycle audit
**現況**
- runtime / account snapshot / trade history / open-order 對帳摘要已可由 `/api/status` 與 Dashboard 直接看到
- 若 snapshot stale、account degraded、trade_history mismatch、open order 缺失，現在已有 machine-readable issue surface

**仍缺**
- restart reconciliation：重啟後 open orders / positions / trade history 是否真正回放一致
- fill replay / partial-fill lifecycle
- venue ack → open → fill / cancel 的完整狀態機證據

**下一步**
- 補 `order lifecycle audit trail` 與 restart 後的 reconciliation replay

### P0. Binance canary readiness 仍未驗證
**現況**
- Binance / OKX adapter、market-rule normalization、kill switch、daily loss halt、failure halt 已存在
- Metadata smoke 與 execution reconciliation 已讓 operator 更容易看出 surface 是否可信

**仍缺**
- live credential verification
- 真實 order ack evidence
- 真實 fill / cancel evidence
- canary sizing policy

**下一步**
- 先做 Binance credential + ack/fill smoke，再談 live-ready

### P1. Strategy Lab / execution runtime 還沒共用 reconciliation 語義
**現況**
- Dashboard 已有 reconciliation / recovery product surface
- Strategy Lab 仍以 decision-quality / backtest contract 為主，尚未消費 runtime reconciliation artifact

**仍缺**
- Strategy Lab / leaderboard / strategy summary 尚未顯示 execution reconciliation blocker
- runtime mismatch 還不能直接回流成策略治理訊號

**下一步**
- 決定哪些 reconciliation 欄位要同步到 Strategy Lab / summary surfaces

---

## Not Issues
- 不是「Dashboard 只能看摘要」：現在已可看 runtime truth detail + reconciliation summary
- 不是「execution surface 完全缺失」：已有 execution service、account snapshot、metadata smoke、reconciliation summary
- 不是「主要問題都在模型」：目前主 blocker 是 execution correctness、recovery、canary verification

---

## Current Priority
1. order lifecycle audit / restart reconciliation
2. Binance canary credential + ack/fill verification
3. Strategy Lab / runtime reconciliation contract sync
