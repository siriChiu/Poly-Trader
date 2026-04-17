# ROADMAP.md — Current Plan Only

_最後更新：2026-04-17 16:34 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- 恢復 **產品 API contract**：
  - `/api/features`
  - `/api/features/coverage`
  - `/api/backtest`
- `features` route 現在重新輸出 canonical feature payload、extended keys 與 `raw_*` 對照欄位
- `features/coverage` route 現在重新輸出 maturity / quality / sparse-source blocker metadata
- `backtest` route 現在重新輸出 canonical decision-quality contract、summary、trade payload
- 驗證通過：
  - `153` 個 backend/productization regression tests PASS
  - `cd web && npm run build` PASS
- fast heartbeat 再次確認資料與診斷：
  - `Raw=30597 / Features=22015 / Labels=61771`
  - `Global IC 14/30`
  - `TW-IC 28/30`
  - live `CIRCUIT_BREAKER`：recent 50 = `4/50`，距 release 還差 `11` 勝

---

## 主目標

### 目標 A：保持 breaker-first canonical runtime truth
重點：
- circuit breaker 仍是真正的 deployment blocker
- 任何 q15/q35/support/component patch 都不能覆蓋 breaker 主敘事

成功標準：
- `/api/predict/confidence`、probe、Dashboard、Strategy Lab 對 blocker 主因保持一致
- operator 能直接看到 release gap 與 release condition

### 目標 B：把 Binance lane 推進到真實 venue-backed path closure
重點：
- lane remediation、timeline、artifact drilldown 已有產品 surface
- 還缺真實 partial-fill / cancel / restart replay artifact

成功標準：
- Binance lane 進入 `venue_backed_path_ready`
- provenance 不再停在 `dry_run_only / internal_only`
- `/api/status`、Dashboard、Strategy Lab 對同一 lane 顯示同一真相

### 目標 C：解除 production-adjacent sparse-source blocker
重點：
- `fin_netflow` 仍被 CoinGlass auth 卡住
- sparse-source 仍需維持 research/blocked 分層，不可污染主 runtime

成功標準：
- 至少解除 `fin_netflow` auth blocker
- production / research / blocked feature 邊界持續清楚

---

## 下一步
1. 以 **canonical tail root-cause + breaker release evidence** 作為下一輪主 patch，補齊 breaker-first runtime governance
2. 以 **Binance 真實 venue artifact 鏈** 作為 execution P0，補 partial-fill / cancel / restart replay
3. 補 **CoinGlass auth**，先解除 `fin_netflow` live fetch blocker

---

## 成功標準
- Dashboard / Strategy Lab / API 同時維持 **breaker-first truth + execution remediation truth**
- execution reconciliation 具備 **單一真相 + operator remediation + 真實 venue-backed path closure**
- feature maturity contract 持續穩定，production / research feature 邊界不再漂移
