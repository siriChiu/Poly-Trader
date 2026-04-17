# ROADMAP.md — Current Plan Only

_最後更新：2026-04-17 09:54 UTC_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- **API runtime closure release-math productization**：
  - `server/routes/api.py` 的 circuit-breaker `runtime_closure_summary` 已補上 **recent window / release floor / current wins / additional wins needed**
  - `/api/status` 與其 operator surface 不再只說 blocker 名稱，而是直接回答距 release 還差多少
  - regression 已在 `tests/test_server_startup.py` 鎖住，避免之後回退成 generic blocker 文案
- **本輪 fast heartbeat 完成**：
  - `python scripts/hb_parallel_runner.py --fast` ✅ 完成（約 **183s**）
  - `Raw=30602 / Features=22020 / Labels=61775`（本輪 `+1 / +1 / +1`）
  - `Global IC 14/30`
  - `TW-IC 28/30`
  - live `CIRCUIT_BREAKER`：recent 50 = `7/50`，距 release 還差 `8` 勝
  - breaker audit：`canonical_breaker_active`
  - recent drift：primary window=`500`，`distribution_pathology`，`bull=100%`
- 驗證通過：
  - `python -m pytest tests/test_server_startup.py -q` → **23 passed**
  - `python -m pytest tests/test_execution_service.py tests/test_frontend_decision_contract.py tests/test_api_feature_history_and_predictor.py tests/test_hb_parallel_runner.py -q` → **107 passed**

---

## 主目標

### 目標 A：保持 breaker-first canonical runtime truth
重點：
- `circuit_breaker_active` 仍是真正 deployment blocker
- `/api/status`、probe、drilldown、Dashboard、Strategy Lab 必須維持同一個 blocker truth
- 所有主要 surface 都必須直接回答「距 release 還差多少」

成功標準：
- recent 50 win rate 回到 `>= 30%`
- 所有主要 surface 一致顯示 release condition 與 remaining gap
- heartbeat summary 能直接回答距 release 還差多少勝

### 目標 B：收斂 recent canonical distribution pathology
重點：
- current primary pathology 仍是 recent 500 bull concentration
- 必須把 high win-rate 與 true deployment readiness 分離
- recent-window root-cause 要回到 canonical tail / 4H structure / macro compression 的機器可讀證據

成功標準：
- recent pathology 不再是 `distribution_pathology`
- 同一批 canonical recent-window diagnostics 在 heartbeat / probe / docs 一致
- 不再需要靠 guardrail 把同一個 bull-only pocket 一直擋下

### 目標 C：把 q35 / support-aware governance 留在 reference-only，直到 breaker 解除
重點：
- q35 redesign、profile split、support-aware fallback 都不得蓋過 breaker-first 主線
- 目前 exact support 仍不足，live row structure-quality 也未收斂

成功標準：
- breaker 未解除前，所有 q35/support-aware surface 都維持 blocked/reference-only 語義
- exact support 到達 minimum support rows 後，再進 deployment 級驗證

### 目標 D：把 Binance execution lane 推進到真實 venue-backed closure
重點：
- 不再只停在 runtime/product surface 完整
- 補 partial-fill / cancel / restart-replay 真實 artifact 鏈

成功標準：
- Binance lane 進入 `venue_backed_path_ready`
- `/api/status`、Dashboard、Strategy Lab 對同一 lane 顯示同一 execution truth
- provenance 不再停在 dry-run / internal-only

---

## 下一步
1. **Breaker release root-cause**：直接追 canonical recent 50/500 tail evidence，驗證從 `7/50` 提升到 release floor 的必要條件
2. **Recent-pathology contraction**：對 bull-only recent slice 做結構／macro compression root-cause，避免把局部高勝率誤判成 readiness
3. **Binance venue artifacts**：補 partial-fill / cancel / restart-replay 真實證據鏈

---

## 成功標準
- `/api/status`、Dashboard、Strategy Lab、probe 對 breaker release math 維持 **同一套 runtime truth**
- fast heartbeat 維持 **cron-safe + machine-readable + fail-soft**，同時明確標示 timeout artifact 的 freshness 風險
- recent canonical pathology 被縮小或明確解釋，不再是 deployment blocker 的黑盒子
- execution lane 具備 **真實 venue-backed artifact**，而不只是產品外觀完整
