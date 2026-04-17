# ROADMAP.md — Current Plan Only

_最後更新：2026-04-17 13:10 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- Strategy Lab live runtime 區塊已升級成 **canonical breaker-first** 呈現：同時顯示 `runtime_closure_state / runtime_closure_summary`、recent-50 release window、required wins、release gap、streak guardrail
- SignalBanner 快捷面板已同步 canonical breaker release math，不再只停留在 q15 patch 文案
- 兩個前端 surface 都新增明確治理文案：**不要把 support / component patch 當成 breaker release 替代品**
- regression coverage 已補到 `tests/test_frontend_decision_contract.py`
- 前端 build 驗證通過：`npm run build`
- runtime probes 重新確認 canonical blocker 未變：
  - `python scripts/hb_predict_probe.py`
  - `python scripts/live_decision_quality_drilldown.py`
  - `python scripts/hb_circuit_breaker_audit.py`
- 最新 runtime truth：仍是 `CIRCUIT_BREAKER`，canonical 1440m release gap = `14 wins`

---

## 主目標

### 目標 A：解除 canonical 1440m circuit breaker 的真正 root cause
重點：
- UI / API 主語義已收斂到 breaker-first；下一步不能再做 presentation-only patch
- 要直接產出 1440m recent-50 為何 `1/50` 的 canonical path artifact，讓 release condition 可被操作

成功標準：
- heartbeat 能指出 recent-50 tail pathology 的可執行 root cause，而不是只重述 breaker
- `/api/predict/confidence`、Dashboard、Strategy Lab、probe、summary 都顯示同一組 canonical release math
- breaker 未解除前，任何 q15/q35 patch 都不會被表述成 deploy-ready

### 目標 B：完成 Binance execution lifecycle replay closure
重點：
- 目前 execution surface 已有 lifecycle / reconciliation 可見性
- 下一步要補 partial fill / cancel / restart replay artifact，建立 recovery 可驗證證據

成功標準：
- `/api/status.execution_reconciliation.lifecycle_contract` 可展示真實 partial fill / cancel / restart replay artifact
- Dashboard / Strategy Lab / `/api/status` 對同一筆 order 顯示一致 lifecycle replay verdict
- operator 能根據 artifact 判斷 restart replay 是否完成，而不是只看狀態字串

### 目標 C：持續硬化 lane-boundary contract
重點：
- 本輪已證明前端 surface 也必須以 canonical breaker truth 為先，不能讓 local patch 敘事覆蓋主 blocker
- 下一步要把所有 runtime override 都收斂成明確 structure-bucket / scope guard

成功標準：
- q15 / q35 / broader-scope override 都有明確 lane guard
- 每個 override 都有 regression test 保證不會污染其他 lane
- live runtime sizing / entry quality / support verdict 不再出現跨-lane 漂移

---

## 下一步
1. 為 canonical 1440m breaker 補 tail-path root-cause artifact，直接解釋 recent 50 為何只剩 `1/50`
2. 以 Binance 為第一 venue，完成 partial fill / cancel / restart replay artifact 與 UI/API 同步顯示
3. 清查其餘 runtime override 是否仍有跨-lane leakage，補齊 lane-boundary regression tests

---

## 成功標準
- breaker 在解除前都維持 **單一 canonical truth**，不會被局部 lane patch 稀釋
- execution lifecycle 具備 **可 replay、可驗證、可恢復** 的 artifact，而非只有狀態可見
- q15 / q35 / runtime override 全部具備 **硬邊界 lane contract**，不再互相污染
