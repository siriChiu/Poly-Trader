# ROADMAP.md — Current Plan Only

_最後更新：2026-04-17 15:08 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- `venue_lanes[]` 已從 lane summary / drilldown 升級為 **operator remediation contract**
- `/api/status.execution_reconciliation.lifecycle_contract.venue_lanes[]` 已新增：
  - `operator_action_summary`
  - `operator_instruction`
  - `verify_instruction`
  - `operator_next_check`
  - `remediation_focus`
  - `remediation_priority`
- Dashboard execution runtime surface 已直接顯示 per-lane remediation
- Strategy Lab runtime blocker sync surface 已同步顯示相同 remediation contract
- regression / build 已驗證：
  - `source venv/bin/activate && python -m pytest tests/test_server_startup.py tests/test_frontend_decision_contract.py -q`
  - `cd web && npm run build`
- fast heartbeat 已再次確認資料管線仍在前進：`Raw +1 / Features +1 / Labels +28`

---

## 主目標

### 目標 A：把 Binance lane 從「可觀測 + 可修復」推進到真實 venue-backed path closure
重點：
- 現在 lane 已會告訴 operator 要補哪個 artifact、怎麼驗證
- 下一步不是再補 UI，而是拿到真實 Binance `partial_fill / cancel_ack / canceled / restart replay`

成功標準：
- Binance lane 進入 `venue_backed_path_ready`
- provenance 不再只有 `dry_run_only / internal_only`
- `/api/status`、Dashboard、Strategy Lab 對同一條 Binance lane 顯示一致真相

### 目標 B：維持 blocker-first / breaker-first truth
重點：
- remediation surface 變強，不代表 deployment blocker 下降
- lane closure、operator remediation、deployment blocker 必須持續語義分離

成功標準：
- Dashboard / Strategy Lab 仍先表達 breaker / blocker，再表達 lane closure
- 任一 surface 都不會把 remediation 誤包裝成 live readiness

### 目標 C：解除 production-adjacent sparse-source blockers
重點：
- fast heartbeat 顯示 blocked sparse features 仍有 8 個
- `fin_netflow` 仍被 `COINGLASS_API_KEY` 缺失卡住

成功標準：
- 至少解除 `fin_netflow` 的 auth blocker
- 明確分層哪些 sparse features 可進 production decision、哪些維持 research/overlay

---

## 下一步
1. 實際補出 **Binance venue-backed partial_fill / cancel / restart replay** artifact，關閉 execution lane P0
2. 驗證 **Dashboard / Strategy Lab 仍維持 blocker-first**，避免 remediation surface 造成 readiness 誤判
3. 補 **CoinGlass auth**，先解除 `fin_netflow` live fetch blocker

---

## 成功標準
- execution reconciliation 具備：**單一真相 + lane drilldown + operator remediation + 真實 venue-backed path closure**
- Dashboard / Strategy Lab / `/api/status` 對 execution readiness、blocker、lane remediation 保持同一套語義
- sparse-source maturity 不再污染產品化敘事，production / research feature 邊界清楚
