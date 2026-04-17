# ROADMAP.md — Current Plan Only

_最後更新：2026-04-17 09:38 UTC_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- **Fast heartbeat cron-safe productization**：
  - `scripts/hb_parallel_runner.py` 新增 fast-mode serial timeout budget
  - drift / q35 / ablation / leaderboard / q15 類 serial diagnostics 即使 timeout，runner 仍會繼續閉環並沿用最新 artifact summary
  - fast heartbeat 不再因單一步驟卡死整輪 cron
- 驗證通過：
  - `python -m pytest tests/test_hb_parallel_runner.py -q` → **39 passed**
  - `python -m pytest tests/test_execution_service.py tests/test_frontend_decision_contract.py tests/test_server_startup.py tests/test_api_feature_history_and_predictor.py -q` → **91 passed**
- 本輪 runtime / diagnostics：
  - `python scripts/hb_parallel_runner.py --fast` ✅ 完成（約 **196s**）
  - `Raw=30601 / Features=22019 / Labels=61774`
  - `Global IC 14/30`
  - `TW-IC 28/30`
  - live `CIRCUIT_BREAKER`：recent 50 = `6/50`，距 release 還差 `9` 勝
  - recent drift：primary window = `500`，`distribution_pathology`，`bull=100%`

---

## 主目標

### 目標 A：保持 breaker-first canonical runtime truth
重點：
- `circuit_breaker_active` 仍是真正 deployment blocker
- probe / drilldown / `/api/status` / UI 必須維持同一個 blocker truth
- 不讓 q35 / profile / sparse-source 議題蓋掉 live canonical blocker

成功標準：
- recent 50 win rate 回到 `>= 30%`
- release condition 在所有主要 surface 顯示一致
- heartbeat summary 能直接回答距 release 還差多少勝

### 目標 B：把 q35 / current-bucket governance 從研究態推到可部署前置驗證
重點：
- current live structure bucket support 仍不足
- q35 redesign 仍只能當 runtime candidate，不能提前宣稱 deployment closure
- leaderboard global winner vs train support-aware fallback 必須維持 machine-read 一致

成功標準：
- current live exact bucket support 達到 minimum support rows
- support-aware / runtime / leaderboard 三條治理語義一致
- exact support 未達標前，所有 surface 都明確標示 reference-only / blocked

### 目標 C：把 Binance execution lane 推進到真實 venue-backed closure
重點：
- 不再只停在 runtime/product surface 完整
- 補足 partial-fill / cancel / restart-replay 真實 artifact 鏈

成功標準：
- Binance lane 進入 `venue_backed_path_ready`
- `/api/status`、Dashboard、Strategy Lab 對同一 lane 顯示同一 execution truth
- provenance 不再停在 dry-run / internal-only

### 目標 D：解除 production-adjacent sparse auth blocker
重點：
- `fin_netflow` 仍被 CoinGlass auth 卡住
- sparse-source 必須繼續維持 research / blocked 分層

成功標準：
- `COINGLASS_API_KEY` 補齊後，`fin_netflow` 從 `source_auth_blocked` 升級到可評估狀態
- production / research / blocked feature 邊界持續清楚

---

## 下一步
1. **Breaker release root-cause**：直接追 canonical recent 50/500 的 tail evidence，驗證從 `6/50` 提升到 release floor 的必要條件
2. **Q35 / support-aware governance**：累積 current live bucket exact support，確認何時才有資格從 runtime candidate 升級到 deployment 驗證
3. **Binance venue artifacts**：補 partial-fill / cancel / restart-replay 真實證據鏈

---

## 成功標準
- fast heartbeat 維持 **cron-safe + machine-readable + fail-soft**，不再因單一步驟卡死
- Dashboard / Strategy Lab / API / probe 持續維持 **breaker-first + runtime-truth 一致**
- execution lane 具備 **真實 venue-backed artifact**，而不只是產品外觀完整
- support-aware governance 與 sparse-source maturity 邊界持續穩定，不再漂移
