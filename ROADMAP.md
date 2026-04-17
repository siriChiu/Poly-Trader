# ROADMAP.md — Current Plan Only

_最後更新：2026-04-17 13:25 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- `/api/status.execution_reconciliation.lifecycle_contract` 已新增 `artifact_checklist_summary + artifact_checklist[]`
- execution lifecycle contract 現在可 machine-read：`validation_passed / venue_ack / trade_history_persisted / partial_fill / cancel / terminal_state / restart_replay`
- Dashboard execution reconciliation surface 已升級成 per-order artifact checklist card
- Strategy Lab runtime blocker sync surface 已同步顯示同一份 checklist，避免 Lab / Dashboard 對 recovery closure 各說各話
- focused pytest 驗證通過：`python -m pytest tests/test_server_startup.py tests/test_frontend_decision_contract.py -q`
- 前端 build 驗證通過：`npm run build`

---

## 主目標

### 目標 A：把 execution recovery 從「缺什麼」推進到「真實 venue artifact closure」
重點：
- 現在 checklist 已能準確指出缺哪個 artifact
- 下一步不是再補 summary，而是讓 Binance 真實 partial-fill / cancel / restart replay artifact 進入 checklist evidence

成功標準：
- checklist evidence 可直接指向真實 venue-side artifact
- `/api/status`、Dashboard、Strategy Lab 對同一筆 order 顯示一致 closure 狀態
- `replay_verdict = replay_artifacts_observed` 有真實 venue 證據支撐

### 目標 B：維持 execution recovery 與 deployment blocker 的語義分離
重點：
- execution checklist 讓 recovery 更可操作，不代表 live breaker 被解除
- 所有 surface 必須持續維持 breaker-first / blocker-first truth

成功標準：
- execution artifact closure 前進時，不會稀釋 canonical live blocker 呈現順序
- operator 可同時看懂 recovery 進度與 deployment blocker，且知道兩者不是同一件事

### 目標 C：把 checklist evidence 升級成逐筆 venue timeline / proof chain
重點：
- 現在已有 per-order checklist，但 evidence 仍偏摘要
- 下一步應把每個 artifact 的 timestamp/source/status 往完整 venue timeline closure 推進

成功標準：
- UI 能明確指出缺的是 validation、venue ack、partial fill、cancel、trade history persist，還是 restart replay proof
- Binance / OKX 可以各自顯示 venue-specific closure timeline

---

## 下一步
1. 以 Binance 為第一 venue，產出真實 partial-fill / cancel / restart replay artifact，接到 checklist evidence
2. 把 per-order checklist evidence 推進成逐筆 venue timeline / proof chain
3. 在 execution patch 持續推進時，持續驗證 canonical circuit breaker / deployment blocker 沒被 execution 敘事稀釋

---

## 成功標準
- execution replay contract 具備 **單一真相 + per-order checklist + 真實 venue artifact closure**
- Dashboard / Strategy Lab / `/api/status` 對 recovery readiness 呈現一致，不再需要人工拼欄位
- execution recovery 與 live deployment blocker 維持 **語義分離、順序正確、不互相污染**
