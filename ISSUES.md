# ISSUES.md — Current State Only

_最後更新：2026-04-17 09:38 UTC_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留舊流水帳。

---

## 當前主線
本輪 heartbeat 先修 **fast heartbeat 會被長時間 serial governance 腳本拖住** 的產品化問題：
- `scripts/hb_parallel_runner.py` 新增 fast-mode serial timeout budget
- fast mode 單一步驟 timeout 時，runner 不中斷，改沿用最新已落地 artifact 繼續 machine-read summary
- 這讓 cron fast heartbeat 回到 **可結束、可交付、可維運**，而不是被 drift / q35 / ablation 類腳本無限拉長

本輪實測事實：
- runtime：`python scripts/hb_parallel_runner.py --fast` ✅ 完成（09:34:29 → 09:37:45 UTC，約 **196s**）
- collect：`Raw=30601 / Features=22019 / Labels=61774`，本輪 **+1 / +1 / +0**
- canonical diagnostics：`Global IC 14/30`、`TW-IC 28/30`
- live predictor：`CIRCUIT_BREAKER`，canonical 1440m recent 50 只贏 `6/50`，距 release 還差 `9` 勝
- drift：primary window=`500`，`distribution_pathology`，`bull=100%`，`win_rate=0.806`
- targeted regression：
  - `python -m pytest tests/test_hb_parallel_runner.py -q` → **39 passed**
  - `python -m pytest tests/test_execution_service.py tests/test_frontend_decision_contract.py tests/test_server_startup.py tests/test_api_feature_history_and_predictor.py -q` → **91 passed**

---

## Open Issues

### P0. Circuit breaker 仍是 live deployment blocker
**現況**
- canonical 1440m recent 50 = `6/50`
- recent win rate = `12%`，仍低於 release floor `30%`
- probe / drilldown / `/api/status` 目前都已能說清楚 blocker 是 `circuit_breaker_active`

**風險**
- 任何把 q35 / profile / bull-pocket 議題包裝成主 blocker 的敘事，都會掩蓋真正 live blocker

**下一步**
- 優先追 canonical tail root-cause 與 release evidence
- breaker 未解除前，不得把任何 runtime candidate 包裝成 deployable

### P0. Recent canonical window 仍是 distribution pathology，不可誤讀成 readiness
**現況**
- primary drift window=`500`
- `bull=100%`
- `win_rate=0.806`、`avg_quality=0.3406`
- sibling-window 對比顯示 `feat_4h_bias20 / feat_4h_ma_order / feat_4h_bb_pct_b` 位移，並新增 `feat_dxy / feat_vix` compression

**風險**
- 若只看高 win-rate，容易把 bull-only concentration 誤判成 deployment readiness

**下一步**
- 直接針對 canonical recent-window 做 root-cause drill-down
- 維持 decision-quality guardrails，不因局部高分放寬 runtime

### P0. Current live q35 / support-aware governance 仍未收斂
**現況**
- leaderboard candidate probe 仍顯示 `dual_role_governance_active`
- `leaderboard=core_only`，`train=core_plus_macro`
- current live structure bucket support 仍不足（summary 顯示 gap to minimum = `50`）
- q35 redesign 仍屬 runtime candidate，不是 deployment closure

**風險**
- 若 exact support 未達標，就把 redesign 或 profile split 說成已 closure，會造成假產品化

**下一步**
- 在 breaker-first 前提下，持續累積 exact support / current-bucket evidence
- 只有 support-ready 後，才進入 deployment 級驗證

### P1. Binance / OKX 仍缺真實 venue-backed partial-fill / cancel / restart-replay artifact
**現況**
- runtime truth、drilldown、Dashboard / Strategy Lab 決策語義已有產品 surface
- 但真實交易所 artifact 鏈仍不足，尚不能宣稱 live-ready execution

**風險**
- UI 看起來像產品，不代表 execution closure 已完成

**下一步**
- 補 Binance 真實 venue-backed artifact 鏈
- 驗證 `/api/status`、Dashboard、Strategy Lab 對同一 lane 的 execution truth 完全一致

### P1. Sparse-source readiness 仍被 auth / 歷史缺口阻塞
**現況**
- blocked sparse features = `8`
- `fin_netflow` 仍為 `source_auth_blocked`
- 根因：`COINGLASS_API_KEY` 缺失

**風險**
- production / research feature 邊界若不清楚，會污染 operator 對主 runtime 的判讀

**下一步**
- 解除 CoinGlass auth blocker
- 繼續把 sparse-source 嚴格留在 research / blocked 層

---

## Not Issues
- 不是 fast heartbeat 仍會無限制拖長：本輪已加入 fast serial timeout budget，且實跑完成
- 不是 collect pipeline 停住：本輪 `raw/features` 皆有新增
- 不是主要產品面 regression：本輪關鍵 regression **130 tests passed**
- 不是 breaker 已解除：live canonical breaker 仍 active

---

## Current Priority
1. 維持 **breaker-first**，直接追 `6/50 → 15/50` 的 canonical release 證據與 root-cause
2. 在 breaker 不鬆動前，繼續收斂 **q35 / current-bucket support-aware governance**，禁止假 closure
3. 補 **Binance 真實 venue artifact 鏈**，把 execution lane 從 product-like 推到 venue-backed
4. 解除 **CoinGlass auth blocker**，但不得讓 sparse-source 議題蓋過 P0 live blocker
