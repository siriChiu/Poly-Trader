# ISSUES.md — Current State Only

_最後更新：2026-04-17 16:34 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留舊流水帳。

---

## 當前主線
本輪 heartbeat 先修復 **產品 API contract regression**：
- `/api/features` 已恢復輸出 canonical feature payload，包含 extended keys 與 `raw_*` 對照欄位
- `/api/features/coverage` 已恢復輸出 maturity / quality / sparse-source blocker contract
- `/api/backtest` 已恢復 canonical decision-quality summary 與 trade payload，避免 Dashboard / Strategy Lab /測試基線繼續依賴缺失路由

本輪實測事實：
- backend regression：`python -m pytest tests/test_api_feature_history_and_predictor.py tests/test_hb_parallel_runner.py tests/test_hb_predict_probe.py tests/test_live_decision_quality_drilldown.py tests/test_hb_leaderboard_candidate_probe.py tests/test_frontend_decision_contract.py tests/test_server_startup.py tests/test_execution_service.py -q` → **153 passed**
- frontend build：`cd web && npm run build` → **PASS**
- fast heartbeat：`Raw=30597 / Features=22015 / Labels=61771`
- canonical diagnostics：`Global IC 14/30 pass`、`TW-IC 28/30 pass`
- live predictor：`CIRCUIT_BREAKER`，canonical 1440m recent 50 只贏 `4/50`，距 release 還差 `11` 勝
- sparse-source blockers：仍有 `8` 個，`fin_netflow` 仍被 `COINGLASS_API_KEY` 缺失卡住

---

## Open Issues

### P0. Circuit breaker 仍是 live deployment blocker
**現況**
- live predictor 明確回傳 `deployment_blocker=circuit_breaker_active`
- canonical 1440m recent 50 win rate = `8%`，release floor = `30%`
- release condition 已可被 probe / docs / Dashboard contract 正確描述

**風險**
- 若任何 surface 把 support/component patch 誤讀成 breaker 已解除，會產生錯誤部署判斷

**下一步**
- 繼續維持 breaker-first truth
- 下一輪優先做 canonical tail root-cause / release evidence，而不是放寬 blocker

### P0. Binance / OKX 仍缺真實 venue-backed partial-fill / cancel / restart-replay artifact
**現況**
- execution lane remediation surface、lane drilldown、timeline、operator instruction 已存在
- 但真實交易所 artifact 仍不足，closure 仍偏 baseline-ready / dry-run-ready

**風險**
- UI 已具有產品感，但沒有 venue-backed artifact 仍不能宣稱 live-ready execution

**下一步**
- 先補 Binance 真實 partial-fill / cancel / restart replay 證據鏈
- 驗證 `/api/status`、Dashboard、Strategy Lab 對同一條 lane 的 truth 完全一致

### P1. Sparse-source readiness 仍被 auth / 歷史缺口阻塞
**現況**
- blocked sparse features = `8`
- `fin_netflow` 仍為 `source_auth_blocked`，根因是 `COINGLASS_API_KEY` 缺失
- forward archive 雖已 ready，但 auth-blocked lane 仍無法進 production decision path

**風險**
- 若 production / research feature 邊界不清楚，會污染產品敘事與 operator 預期

**下一步**
- 解除 CoinGlass auth blocker
- 繼續把 sparse-source 嚴格留在 research / blocked 層，不可滲入 core runtime 決策

---

## Not Issues
- 不是 `/api/features` / `/api/features/coverage` / `/api/backtest` contract 缺失：本輪已恢復
- 不是前端 build 或核心 regression 失敗：本輪測試與 build 均通過
- 不是 breaker 已解除：canonical 1440m live breaker 仍 active

---

## Current Priority
1. 維持 **breaker-first / blocker-first truth**，禁止任何 patch/support 敘事蓋過 circuit breaker
2. 補出 **Binance 真實 venue-backed artifact 鏈**，關閉 execution lane P0
3. 解除 **CoinGlass auth blocker**，讓 sparse-source maturity 分層回到可持續狀態
