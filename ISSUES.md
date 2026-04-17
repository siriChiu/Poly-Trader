# ISSUES.md — Current State Only

_最後更新：2026-04-17 15:08 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留舊流水帳。

---

## 當前主線
本輪 heartbeat 已把 execution reconciliation 的 venue lane 從「看得到 drilldown」推進到 **operator-grade remediation surface**：
- `/api/status.execution_reconciliation.lifecycle_contract.venue_lanes[]` 現在新增：
  - `operator_action_summary`
  - `operator_instruction`
  - `verify_instruction`
  - `operator_next_check`
  - `remediation_focus`
  - `remediation_priority`
- Dashboard / Strategy Lab 已直接顯示每個 lane 的：
  - 先做什麼
  - 做完怎麼驗證
  - 下一個檢查點
  - remediation priority / focus
- regression / build 已通過：
  - `source venv/bin/activate && python -m pytest tests/test_server_startup.py tests/test_frontend_decision_contract.py -q`
  - `cd web && npm run build`

本輪 heartbeat 實測事實（fast collect + IC diagnostics）：
- collect 成功：`Raw +1 / Features +1 / Labels +28`
- 目前 DB：`Raw=30593 / Features=22011 / Labels=61768`
- canonical diagnostics：`Global IC 14/30 pass`、`TW-IC 28/30 pass`
- source blockers 仍有 `8` 個；其中 `fin_netflow` 仍被 `COINGLASS_API_KEY` 缺失卡住

---

## Open Issues

### P0. Binance / OKX 仍缺真實 venue-backed partial-fill / cancel / restart-replay artifact
**現況**
- lane remediation surface 已能直接告訴 operator 每個 lane 要補什麼
- 但 closure 仍主要停在 baseline-ready / internal-only / dry-run-ready
- 目前還沒有足夠的真實交易所 `partial_fill / cancel_ack / canceled / restart replay` artifact 鏈

**風險**
- UI 現在更像產品，但若沒有真實 venue artifact，仍然只是治理與可觀測性 closure，不是 live readiness
- 容易把「知道缺什麼」誤讀成「已經打通 venue path」

**下一步**
- 以 Binance 為第一 lane，實際打出可重放的 `partial_fill / cancel_ack / canceled / restart replay`
- 讓 lane status 從 `baseline_ready_missing_path` / `path_observed_internal_only` 進到 `venue_backed_path_ready`
- 驗證 `/api/status`、Dashboard、Strategy Lab 三者對同一 lane 的 truth 完全一致

### P0. Breaker-first truth 不能被 remediation/drilldown 蓋過
**現況**
- lane remediation 現在更清楚
- 但 canonical deployment blocker / circuit breaker 仍必須優先於 lane closure 敘事

**風險**
- 如果 operator 先看到某個 lane 的 remediation 已很完整，可能誤判成 deployment blocker 已下降

**下一步**
- 下一輪補 venue-backed artifact 時，同步驗證 Dashboard / Strategy Lab 仍維持 blocker-first 順序
- 任一 surface 若讓 remediation lane 比 blocker 更像主結論，視為 regression

### P1. Sparse-source readiness 仍被 auth / 歷史缺口阻塞
**現況**
- fast heartbeat 顯示 blocked features = 8
- `fin_netflow` 仍因 `COINGLASS_API_KEY` 缺失而 `source_auth_blocked`
- 其餘 archive-required / snapshot-only 特徵仍未完成歷史閉環

**風險**
- 雖然近期 canonical IC 很強，但 source maturity 不完整時，FeatureChart / live overlay / future product claims 仍會失真

**下一步**
- 補齊 CoinGlass auth，先解除 `fin_netflow` live fetch blocker
- 釐清哪些 blocked sparse features 要進 production decision path，哪些只保留 research/overlay

---

## Not Issues
- 不是 execution reconciliation 還只有摘要卡：lane drilldown + remediation 已落地
- 不是 Binance / OKX 已 live-ready：真實 venue-backed path artifact 仍缺
- 不是 breaker 已解除：本輪只補 operator remediation surface，沒有改 breaker release 條件

---

## Current Priority
1. 先用 **Binance 真實 partial-fill / cancel / restart replay artifact** 關閉 lane-level P0
2. 維持 **breaker-first / blocker-first truth**，避免 remediation UI 被誤讀成 live readiness
3. 補 **CoinGlass auth + sparse-source maturity**，避免 research source 混入產品敘事
