# ISSUES.md — Current State Only

_最後更新：2026-04-17 02:43 +08:00_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留舊流水帳。

---

## 當前主線
Poly-Trader 目前 heartbeat 主線是 **execution / Dashboard / Strategy Lab 的產品化閉環**，不是再追加研究敘事。

本輪已完成一項直接產品化前進：
- Dashboard 現在可直接看到 execution runtime truth / detail：
  - account snapshot 時間
  - requested / normalized symbol
  - 倉位明細
  - open orders 明細
  - 最近委託 requested → normalized → contract 回放
  - degraded / recovery hint

---

## Open Issues

### P0. reconciliation / recovery / audit trail 仍未完成
**現況**
- execution status、guardrails、account snapshot、metadata smoke、continuity 狀態都已集中到 Dashboard canonical surface
- account snapshot 若退化，現在會明示 degraded + recovery hint，而不是只剩空列表

**仍缺**
- restart reconciliation：重啟後如何確認 open orders / positions / trade history 一致
- fill replay / order lifecycle audit
- 對「UI 顯示有單 / venue 已無單」這類偏差的機器可讀診斷

**下一步**
- 做 reconciliation summary + mismatch diagnostics，讓 `/api/status` 不只顯示當下列表，還能顯示「是否對得上」

### P0. execution 雖已有 detail surface，但 canary-ready 還沒被驗證
**現況**
- Binance / OKX adapter、market-rule normalization、kill switch、daily loss halt、failure halt 已存在
- Dashboard 現在已能讓操作者直接檢查 execution 真相，而不是只看摘要數字

**仍缺**
- live credential verification
- order ack lifecycle 實測
- fill lifecycle 實測
- canary sizing policy

**下一步**
- 先把 Binance 做成第一個可驗證 canary venue，再談 live-ready

### P1. Strategy Lab / Dashboard / execution contract 還需要更深的同語義對帳
**現況**
- Dashboard execution surface 已升級，操作者可看到 runtime truth 細節
- Decision-quality / execution guardrails / continuity 在首頁已有可見治理面板

**仍缺**
- Strategy Lab 與 execution runtime 的 reconciliation / recovery 訊號尚未互通
- execution audit trail 尚未成為 leaderboard / backtest / runtime 共用語義

**下一步**
- 補 runtime reconciliation artifact，並決定哪些欄位要同步到 Strategy Lab / API summary

---

## Not Issues
- 不是「沒有 execution layer」：已有 execution service + multi-venue adapters + guardrails
- 不是「Dashboard 只能看摘要」：現在已能直接看 positions / open orders / normalization replay / recovery hint
- 不是「所有問題都在模型」：目前主要 blocker 是 runtime correctness、reconciliation、venue verification

---

## Current Priority
1. reconciliation / recovery / audit trail
2. Binance canary verification
3. order ack + fill lifecycle evidence
4. Strategy Lab / runtime contract sync
