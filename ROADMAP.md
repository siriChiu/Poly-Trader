# ROADMAP.md — Current Plan Only

_最後更新：2026-04-17 14:48 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- `/api/status.execution_reconciliation.lifecycle_contract.venue_lanes[]` 已新增 `artifact_drilldown_summary / timeline_summary / timeline_events / artifacts`
- Dashboard execution runtime surface 已從 lane summary 升級到 lane-level filtered drilldown
- Strategy Lab runtime blocker sync surface 已同步顯示相同 lane drilldown contract
- regression coverage 已補到：
  - `tests/test_server_startup.py`
  - `tests/test_frontend_decision_contract.py`
- focused verification 已通過：
  - `source venv/bin/activate && python -m pytest tests/test_server_startup.py tests/test_frontend_decision_contract.py -q`
  - `cd web && npm run build`

---

## 主目標

### 目標 A：把 Binance lane 從可觀測 drilldown 推進到真實 venue-backed path closure
重點：
- 現在已能直接看到 Binance lane 自己的 artifact subset 與 timeline
- 下一步不是再加摘要，而是補出真實 `partial_fill / cancel_ack / canceled / restart replay`

成功標準：
- Binance lane 顯示真實 `venue_backed` path artifact，而不是只有 internal / dry-run
- `/api/status`、Dashboard、Strategy Lab 對同一條 Binance lane 顯示一致 closure truth
- `operator_next_artifact` 可被真實 venue artifact 關閉，而不是長期停在 generic path gap

### 目標 B：維持 lane drilldown 與 deployment blocker 的語義分離
重點：
- lane drilldown 前進，不代表 circuit breaker / deployment blocker 已解除
- 所有 surface 必須持續維持 blocker-first / breaker-first truth

成功標準：
- 即使 lane drilldown 更完整，breaker / deployment blocker 仍先於 closure 敘事顯示
- operator 能同時看懂 lane closure 與 deployment blocker，且不會把兩者混成同一件事

### 目標 C：把 lane drilldown 升級成 operator remediation surface
重點：
- 現在能看見 lane 自己的 artifact / timeline
- 下一步要把它變成可操作的 remediation 入口，而不是只是一個 debug 卡片

成功標準：
- 每個 lane 都能清楚回答下一個 remediation 動作
- operator 不需要再回到 mixed global timeline 手動推理 lane 問題
- Dashboard / Strategy Lab 對每個 lane 的 remediation 語義一致

---

## 下一步
1. 以 Binance 為第一 venue，補上真實 `partial_fill / cancel_ack / canceled / restart replay` artifact
2. 驗證 lane drilldown 前進時，**canonical circuit breaker / deployment blocker** 仍維持 blocker-first 呈現
3. 把 `operator_next_artifact` 往 **per-lane remediation instruction** 推進，讓 lane drilldown 變成可操作 surface

---

## 成功標準
- execution reconciliation 具備 **單一真相 + per-order checklist + proof chain + venue-specific lane drilldown + 真實 venue-backed path closure**
- Dashboard / Strategy Lab / `/api/status` 對 recovery readiness 呈現一致，不再要求 operator 從 mixed timeline 手動拆 lane
- execution lane observability 與 live deployment blocker 維持 **語義分離、順序正確、不互相污染**
