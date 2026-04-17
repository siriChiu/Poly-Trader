# ROADMAP.md — Current Plan Only

_最後更新：2026-04-17 09:12 UTC_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- 把 **circuit breaker 與 recent pathology** 綁成同一個 runtime contract：
  - `model/predictor.py` 的 breaker path 現在會同步帶出 `decision_quality_recent_pathology_*`
  - `scripts/hb_predict_probe.py` 的 `runtime_closure_summary` 現在會直接說明 breaker + pathology
  - `/api/status` 的 live runtime closure summary 也會保留同一份 pathology truth
- 驗證通過：
  - `python -m pytest tests/test_api_feature_history_and_predictor.py tests/test_hb_predict_probe.py tests/test_server_startup.py -q` → **78 passed**
- 本輪 heartbeat collect / diagnostics：
  - `Raw=30599 / Features=22017 / Labels=61773`（本輪 +1 / +1 / +1）
  - `Global IC 14/30`
  - `TW-IC 28/30`
  - live `CIRCUIT_BREAKER`：recent 50 = `5/50`，距 release 還差 `10` 勝
  - recent drift：primary window = `500`，`distribution_pathology`，`bull=100%`

---

## 主目標

### 目標 A：保持 breaker-first + pathology-visible canonical runtime truth
重點：
- circuit breaker 仍是真正的 deployment blocker
- 就算先被 breaker 擋下，operator 仍必須同時看到 canonical recent-window pathology
- Runtime / `/api/status` / Dashboard / Strategy Lab 必須維持同一個 blocker + pathology 敘事

成功標準：
- `predictor → hb_predict_probe → /api/status` 都帶出 `decision_quality_recent_pathology_*`
- runtime closure summary 能直接回答「為何被 breaker 擋」與「最近 canonical 視窗哪裡有病灶」

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
- sparse-source 仍需維持 research / blocked 分層，不可污染主 runtime

成功標準：
- 至少解除 `fin_netflow` auth blocker
- production / research / blocked feature 邊界持續清楚

---

## 下一步
1. 以 **canonical recent-window drift root-cause** 作為下一輪主 patch，釐清 bull-only concentration、4H 結構位移與 `feat_dxy/feat_vix` compression 對 runtime sizing 的影響
2. 以 **Binance 真實 venue artifact 鏈** 作為 execution P0，補 partial-fill / cancel / restart replay
3. 補 **CoinGlass auth**，先解除 `fin_netflow` live fetch blocker

---

## 成功標準
- Dashboard / Strategy Lab / API 同時維持 **breaker-first + pathology-visible truth + execution remediation truth**
- execution reconciliation 具備 **單一真相 + operator remediation + 真實 venue-backed path closure**
- feature maturity contract 持續穩定，production / research feature 邊界不再漂移
