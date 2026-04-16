# ROADMAP.md — Current Plan Only

_最後更新：2026-04-17 02:46 +08:00_

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
- Dashboard execution surface 已可檢查 runtime truth detail
- **本輪新增 execution reconciliation summary**：
  - snapshot freshness
  - symbol scope alignment
  - trade history alignment
  - open-order audit
  - issue list / mismatch reason

---

## 主目標

### 目標 A：把 execution 從「summary 對得上」推進到「lifecycle 對得上」
重點：
- restart reconciliation
- order ack → open → fill / cancel audit trail
- partial fill / replay evidence

### 目標 B：把 Binance 做成第一個可驗證 canary venue
重點：
- credential verification
- live ack/fill smoke
- canary sizing policy

### 目標 C：讓 Strategy Lab / Dashboard / execution 共用同一套治理語義
重點：
- reconciliation artifact 進 Strategy Lab / summary
- runtime blocker 與策略治理語義同步
- 文件保持 current-state-only

---

## 下一步
1. 建立 order lifecycle audit artifact，覆蓋 ack/open/fill/cancel 與 restart replay
2. 驗證 Binance credential / ack / fill path，收集真實 runtime 證據
3. 把 reconciliation blocker 同步到 Strategy Lab / summary surfaces

---

## 成功標準
- Dashboard 不只顯示 account truth，還能 machine-check 是否與 trade history / open orders 對得上
- Binance 可以用真實 runtime 證據證明 canary-ready，而不是文件宣稱
- Strategy Lab / Dashboard / execution 對同一筆決策與執行風險講同一套語義
