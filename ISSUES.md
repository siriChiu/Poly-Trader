# ISSUES.md — Current State Only

_最後更新：2026-04-17 14:05 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留舊流水帳。

---

## 當前主線
本輪 heartbeat 的產品真相是：**execution reconciliation 已不只顯示 checklist，有沒有 artifact 還要分清楚是 `venue_backed`、`dry_run_only` 還是 `internal_only`。** `/api/status.execution_reconciliation.lifecycle_contract` 現在新增 `artifact_provenance_summary + provenance_level`，Dashboard 與 Strategy Lab 也同步顯示 provenance，避免把 replay baseline ready 或 dry-run lifecycle 誤讀成 Binance / OKX 已具備真實 venue closure。

本輪已完成的產品化前進：
- `server/routes/api.py` 為 per-order artifact checklist 新增 provenance contract
- Dashboard execution reconciliation surface 已同步顯示 artifact provenance summary / proof
- Strategy Lab runtime blocker sync surface 已同步顯示 artifact provenance summary / proof
- regression coverage 已補到 `tests/test_server_startup.py` 與 `tests/test_frontend_decision_contract.py`
- 前端 build 已通過：`npm run build`

---

## Open Issues

### P0. Binance / OKX 仍缺真實 partial-fill / cancel / restart-replay artifact
**現況**
- UI 與 API 現在能明確區分 dry-run / internal / venue-backed evidence
- 但目前 machine-readable closure 仍以 baseline event、dry-run lifecycle、trade-history persist 為主
- **真正的 Binance / OKX partial-fill、cancel、restart replay venue artifact 仍未落地**

**風險**
- 若沒有真實 venue artifact，restart 後的 recovery closure 仍只是「對帳更清楚」，不是「venue 實證完成」
- operator 仍不能把目前 execution surface 解讀成 live venue readiness

**下一步**
- 以 Binance 為第一 venue，補上真實 `partial_fill / cancel_ack / canceled / replay` artifact
- 讓 provenance 從 `dry_run_only / internal_only` 真正轉成 `venue_backed`

### P0. Canonical 1440m circuit breaker 仍有效，live runtime 不可部署
**現況**
- 本輪 execution provenance patch 沒有解除 deployment blocker
- live surfaces 仍必須維持 breaker-first truth

**風險**
- 若把 execution UX / provenance 改善誤讀成 live-ready，會讓 operator 高估目前可部署度

**下一步**
- 繼續維持所有 runtime surface 的 blocker-first 順序
- 下一輪若補 venue artifact，也要同步驗證 breaker truth 沒被 execution 敘事稀釋

### P1. Per-order closure 已可分辨證據層級，但還沒有逐筆 venue proof chain
**現況**
- checklist 現在可回答每個 artifact 是 venue-backed、dry-run-only 還是 internal-only
- 但 evidence 仍偏 latest-event/provenance summary，尚未形成完整逐筆 venue timeline proof chain

**風險**
- 當 recovery lane 出問題時，operator 雖知道證據層級，但還不能一路追到完整 venue-side timeline

**下一步**
- 將 provenance 再往 `per-artifact proof chain / venue timeline` 推進
- 讓 Binance / OKX 都能顯示 venue-specific closure lane

---

## Not Issues
- 不是 live blocker 已解除：本輪只是把 artifact 真實性分層，不代表可部署
- 不是 Binance / OKX 已有真實 partial-fill/cancel closure：目前只是把缺口 machine-read 化
- 不是 replay verdict 被取代：本輪是在 checklist 上再加 provenance truth

---

## Current Priority
1. 先補 **Binance 真實 partial-fill / cancel / restart replay artifact**，讓 provenance 真正出現 `venue_backed`
2. 維持 **canonical circuit breaker truth**，避免 execution 產品化 patch 被誤讀成 deployment readiness
3. 把 provenance 繼續推進成 **逐筆 venue proof chain / timeline closure**
