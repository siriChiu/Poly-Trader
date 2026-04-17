# ROADMAP.md — Current Plan Only

_最後更新：2026-04-17 14:05 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- `/api/status.execution_reconciliation.lifecycle_contract` 已新增 `artifact_provenance_summary + provenance_level`
- execution checklist 現在可明確區分 `venue_backed / dry_run_only / internal_only / missing`
- Dashboard execution reconciliation surface 已同步顯示 artifact provenance summary / proof
- Strategy Lab runtime blocker sync surface 已同步顯示 artifact provenance summary / proof
- focused regression 驗證通過：
  - `python -m pytest tests/test_server_startup.py -q -k 'execution_reconciliation_summary_marks_healthy_match or execution_reconciliation_summary_without_runtime_order_is_idle or execution_reconciliation_summary_includes_lifecycle_timeline or venue_backed_artifact_provenance'`
  - `python -m pytest tests/test_frontend_decision_contract.py -q`
- 前端 build 驗證通過：`npm run build`

---

## 主目標

### 目標 A：把 execution closure 從「有 checklist」推進到「有真實 venue artifact」
重點：
- 現在 checklist 已能區分 proof 層級，但還沒有真實 Binance / OKX partial-fill / cancel / replay artifact
- 下一步不是再補 summary，而是讓 `venue_backed` 真正出現在 execution path closure

成功標準：
- checklist/provenance 可直接指出真實 venue-side partial-fill / cancel / replay artifact
- `/api/status`、Dashboard、Strategy Lab 對同一筆 order 顯示一致的 venue-backed closure
- `replay_verdict = replay_artifacts_observed` 有真實 venue 證據支撐，而不是 dry-run / internal-only

### 目標 B：維持 execution closure 與 deployment blocker 的語義分離
重點：
- provenance patch 提高了 closure 真實性辨識，但不代表 breaker 已解除
- 所有 surface 必須持續維持 blocker-first / breaker-first truth

成功標準：
- execution artifact closure 前進時，不會稀釋 canonical circuit breaker 呈現順序
- operator 可同時看懂 recovery 進度與 deployment blocker，且知道兩者不是同一件事

### 目標 C：把 provenance 再升級成逐筆 venue proof chain / timeline closure
重點：
- 現在已有 provenance summary，但 evidence 仍偏 latest event
- 下一步應把每個 artifact 的 timestamp/source/exchange/provenance 往完整 proof chain 推進

成功標準：
- UI 能明確指出每個 artifact 的 proof chain，而不只是一句 provenance summary
- Binance / OKX 可以各自顯示 venue-specific closure timeline

---

## 下一步
1. 以 Binance 為第一 venue，補上真實 `partial_fill / cancel / restart replay` artifact，讓 provenance 出現 `venue_backed`
2. 把 artifact provenance 推進成逐筆 venue proof chain / timeline closure
3. 在 execution patch 持續推進時，持續驗證 canonical circuit breaker / deployment blocker 沒被 execution 敘事稀釋

---

## 成功標準
- execution replay contract 具備 **單一真相 + per-order checklist + provenance truth + 真實 venue artifact closure**
- Dashboard / Strategy Lab / `/api/status` 對 recovery readiness 呈現一致，不再把 dry-run/internal evidence 誤讀成 venue-ready
- execution recovery 與 live deployment blocker 維持 **語義分離、順序正確、不互相污染**
