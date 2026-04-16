# ROADMAP.md — Current Plan Only

_最後更新：2026-04-17 02:43 +08:00_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- heartbeat 主線已切到產品化，不再把重點放在研究報告
- execution foundation 已具備：
  - `ExecutionService`
  - `AccountSyncService`
  - `BinanceAdapter`
  - `OKXAdapter`
- execution guardrails 第一版已落地：
  - symbol normalization
  - precision / step / tick validation
  - min_qty / min_notional reject
  - kill switch
  - daily loss halt
  - failure halt
- `/api/status` 已集中帶出 execution / account / continuity / metadata smoke
- Dashboard execution surface 已升級為可檢查 runtime truth 的 detail 面板：
  - snapshot freshness
  - requested / normalized symbol
  - positions / open orders detail
  - recent normalization replay
  - degraded / recovery hint

---

## 主目標

### 目標 A：把 execution 從「看得到」推進到「對得上」
重點：
- restart reconciliation
- open orders / positions / trade history mismatch diagnostics
- fill replay / order lifecycle audit

### 目標 B：把 Binance 做成第一個可驗證 canary venue
重點：
- credential verification
- order ack / fill lifecycle evidence
- canary sizing policy

### 目標 C：讓 Strategy Lab / Dashboard / execution 共用同一套 runtime 治理語義
重點：
- reconciliation artifact 進 `/api/status`
- 必要欄位同步到 Strategy Lab / backtest summary
- 文件保持 current-state-only

---

## 下一步
1. 新增 reconciliation summary 與 mismatch diagnostics
2. 驗證 Binance canary 的 credential / ack / fill path
3. 決定哪些 reconciliation 欄位要同步到 Strategy Lab / API summary

---

## 成功標準
- Dashboard 不只看得到執行狀態，還能說明是否與 venue / trade history 一致
- Binance 可以用真實 runtime 證據證明 canary-ready，而不是文件宣稱
- Strategy Lab / Dashboard / execution 對同一筆決策與執行路徑講同一套語義
