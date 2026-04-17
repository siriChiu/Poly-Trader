# ISSUES.md — Current State Only

_最後更新：2026-04-17 14:48 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留舊流水帳。

---

## 當前主線
本輪 heartbeat 已把 execution reconciliation 從「venue lane 摘要卡」推進到 **lane-level filtered drilldown**。`/api/status.execution_reconciliation.lifecycle_contract.venue_lanes[]` 現在除了 lane summary，還會額外輸出：
- `artifact_drilldown_summary`
- `timeline_summary`
- `timeline_events[]`
- `artifacts[]`

Dashboard 與 Strategy Lab 已同步顯示 **Binance / OKX / Unscoped internal** 各自的 lane drilldown，operator 可以直接在 lane 卡片內看到：
- 該 lane 缺哪些 baseline / required artifact
- 該 lane 最近 3 筆 filtered timeline event
- 該 lane 自己的 artifact subset，而不是混用 global timeline

本輪已完成的產品化前進：
- `server/routes/api.py` 新增 lane-level filtered artifact / timeline contract
- Dashboard execution runtime surface 新增 lane drilldown 區塊
- Strategy Lab runtime blocker sync surface 新增同一套 lane drilldown
- `tests/test_server_startup.py` 補 lane drilldown contract regression
- `tests/test_frontend_decision_contract.py` 補 Dashboard / Strategy Lab lane drilldown regression
- 驗證已通過：
  - `source venv/bin/activate && python -m pytest tests/test_server_startup.py tests/test_frontend_decision_contract.py -q`
  - `cd web && npm run build`

---

## Open Issues

### P0. Binance / OKX 仍缺真實 venue-backed partial-fill / cancel / restart-replay artifact
**現況**
- lane-level drilldown 已能精確指出每個 venue lane 的缺口
- 但 closure 仍主要停留在 internal / dry-run / baseline-ready，尚未拿到真實交易所 path artifact 鏈

**風險**
- UI 現在更透明，但不能把「可觀測」誤讀成「已 live-ready」
- 沒有真實 venue artifact，reconciliation 仍是 governance closure，不是交易所實證 closure

**下一步**
- 以 Binance 為第一 venue，補 `partial_fill / cancel_ack / canceled / restart replay` 的真實 artifact
- 讓 lane status 從 `baseline_ready_missing_path` / `path_observed_internal_only` 進到真正 `venue_backed_path_ready`

### P0. Canonical 1440m circuit breaker 仍有效，所有 surface 必須維持 blocker-first truth
**現況**
- 本輪補的是 execution lane drilldown，不是 breaker release
- Dashboard / Strategy Lab 仍必須先表達 circuit breaker / deployment blocker，再談 lane closure

**風險**
- 如果 lane drilldown 視覺比 blocker 更顯眼，operator 可能誤以為 execution readiness 已高於 deployment blocker

**下一步**
- 下一輪補真實 venue artifact 時，同步驗證 blocker-first 排序與文案仍然先於 lane closure
- 任一 surface 若讓 closure 敘事蓋過 breaker，立即視為 regression

### P1. Lane drilldown 已有讀取能力，但還沒有 operator-grade remediation action
**現況**
- lane 卡片已能看 filtered artifact / timeline
- 但目前仍停在「看見問題」，尚未把每個 lane 的下一步升級成更具體的操作指令或 remediation flow

**風險**
- operator 雖然知道哪個 lane 卡住，仍可能需要人工推理下一個修復動作

**下一步**
- 把 `operator_next_artifact` 進一步對齊成 per-lane remediation 指令 / 檢查入口
- 讓 Dashboard / Strategy Lab 能直接回答「下一步該補哪個 artifact、看哪條 timeline」

---

## Not Issues
- 不是 breaker 已解除：本輪只補 execution reconciliation 的 lane drilldown 能見度
- 不是 Binance / OKX 已 live-ready：真實 venue-backed path artifact 仍缺
- 不是 Strategy Lab 已成 execution canonical route：canonical execution route 仍是 Dashboard

---

## Current Priority
1. 先補 **Binance 真實 partial-fill / cancel / restart replay artifact**，把 lane 從可觀測推進到真實 venue-backed closure
2. 維持 **canonical circuit breaker / deployment blocker truth**，避免 lane drilldown 被誤讀成 live readiness
3. 把 **lane drilldown 升級成 operator remediation surface**，讓下一步動作不再靠人工推理
