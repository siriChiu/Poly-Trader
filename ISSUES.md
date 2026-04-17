# ISSUES.md — Current State Only

_最後更新：2026-04-17 13:25 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留舊流水帳。

---

## 當前主線
本輪 heartbeat 的產品真相是：**execution reconciliation 已從 summary-only 升級成 machine-readable per-order artifact checklist contract。** `/api/status.execution_reconciliation.lifecycle_contract` 現在不只回傳 `replay_verdict`，還會同步回傳 `artifact_checklist_summary + artifact_checklist[]`，把 `validation_passed → venue_ack → trade_history_persisted → partial fill / cancel → restart replay` 的 closure 狀態直接機器可讀化；Dashboard 與 Strategy Lab 也已同步顯示這份 checklist，operator 不必再從零散欄位手動拼出缺哪個證據。

本輪已完成的產品化前進：
- `server/routes/api.py` 新增 execution lifecycle `artifact_checklist_summary` 與 `artifact_checklist[]`
- Dashboard execution reconciliation surface 已升級為 per-order artifact checklist card
- Strategy Lab runtime blocker sync surface 已同步顯示同一份 artifact checklist
- regression coverage 已補到 `tests/test_server_startup.py` 與 `tests/test_frontend_decision_contract.py`
- 前端 build 已通過：`npm run build`

---

## Open Issues

### P0. Binance / OKX 仍缺真實 partial-fill / cancel / restart-replay artifact
**現況**
- 現在已可 machine-read 哪一段 lifecycle 缺證據
- 但 checklist 目前吃到的仍主要是 runtime / DB 內已存在 artifact；**還沒有新增真實 venue partial-fill / cancel / restart replay 實證**
- `baseline_replay_ready_missing_path_artifacts` 仍表示：基線 replay ready，但 execution path closure 尚未完成

**風險**
- 若沒有真實 venue artifact，restart 後的 replay closure 仍無法被實證驗證
- UI 雖更清楚，但底層 recovery closure 仍可能只是假健康

**下一步**
- 以 Binance 為第一 venue，補 partial fill / cancel / restart replay artifact
- 讓 checklist evidence 能直接指向真實 venue-side event，而不只是內部 summary

### P0. Canonical 1440m circuit breaker 仍有效，live runtime 不可部署
**現況**
- 本輪 execution checklist patch 沒有解除 deployment blocker
- live surfaces 仍必須維持 breaker-first truth

**風險**
- 若把 execution UX 改善誤讀成 live-ready，會讓 operator 高估可部署度

**下一步**
- 保持所有 runtime surface 明確區分：`execution recovery clarity` ≠ `live deployment ready`
- 下一輪若補 venue artifact，也要同步驗證 breaker truth 沒被稀釋

### P1. Per-order checklist 已上線，但 evidence 還沒進到「逐筆 venue timeline closure」
**現況**
- Dashboard / Strategy Lab 已能顯示 per-order checklist
- 目前 checklist evidence 仍偏向 event/status/timestamp 摘要，尚未形成完整 venue-side timeline closure（validation → ack → partial fill/cancel → persisted → restart replay）

**風險**
- 當 venue recovery 出問題時，operator 雖知道缺哪個 artifact，但還不能一路追到完整 venue-side evidence 鏈

**下一步**
- 將 checklist evidence 擴成更完整的 per-order timeline / proof chain
- 讓 Binance / OKX 可各自顯示 venue-specific closure 狀態

---

## Not Issues
- 不是 replay verdict 被取代：本輪是在 replay verdict 之上補了 per-order artifact checklist
- 不是 live blocker 已解除：execution visibility 變清楚，不代表可部署
- 不是真實 venue partial-fill / cancel artifact 已補齊：本輪先補的是 contract 與 operator UX

---

## Current Priority
1. 先補 **Binance 真實 partial-fill / cancel / restart replay artifact**，讓 checklist 從「對帳真相」升級成「實證 closure」
2. 維持 **canonical circuit breaker truth**，避免 execution 產品化 patch 被誤讀成 deployment readiness
3. 把 checklist evidence 繼續推進成 **逐筆 venue timeline / proof chain**
