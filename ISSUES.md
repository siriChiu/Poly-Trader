# ISSUES.md — Current State Only

_最後更新：2026-04-17 09:54 UTC_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留舊流水帳。

---

## 當前主線
本輪 heartbeat 先修 **API runtime closure summary 必須直接說出 circuit breaker release math** 的產品化缺口：
- `server/routes/api.py` 的 `runtime_closure_summary` 現在不只說「被 breaker 擋下」，還會直接帶出 **recent window / required floor / 當前 wins / 還差幾勝**
- 目的：讓 `/api/status` 與其所有 operator surface 在 breaker active 時，直接回答「距 release 還差多少」，而不是只剩 generic blocker 文案
- targeted regression 已鎖住這個 contract，避免之後回退成只報 blocker 名稱

本輪實測事實：
- runtime：`python scripts/hb_parallel_runner.py --fast` ✅ 完成（09:51:08 → 09:54:11 UTC，約 **183s**）
- collect：`Raw=30602 / Features=22020 / Labels=61775`，本輪 **+1 / +1 / +1**
- canonical diagnostics：`Global IC 14/30`、`TW-IC 28/30`
- live predictor：`CIRCUIT_BREAKER`，canonical 1440m recent 50 = **7/50**，距 release 還差 **8 勝**
- circuit-breaker audit：`canonical_breaker_active`，mixed-horizon 已不是 blocker 根因
- drift：primary window=`500`，`distribution_pathology`，`bull=100%`，`win_rate=0.806`
- targeted regression：
  - `python -m pytest tests/test_server_startup.py -q` → **23 passed**
  - `python -m pytest tests/test_execution_service.py tests/test_frontend_decision_contract.py tests/test_api_feature_history_and_predictor.py tests/test_hb_parallel_runner.py -q` → **107 passed**

---

## Open Issues

### P0. Circuit breaker 仍是 live deployment blocker
**現況**
- canonical 1440m recent 50 = `7/50`
- recent win rate = `14%`，仍低於 release floor `30%`
- `/api/status` / probe / drilldown / Dashboard 已能明確顯示 **還差 8 勝**

**風險**
- 若 operator surface 只看到 blocker 名稱、看不到 release math，就容易把 q15/q35/component patch 誤讀成更高優先級

**下一步**
- 持續以 breaker-first 追 canonical tail root-cause
- 任何 runtime candidate 都不得跳過 `7/50 → 15/50` 的 release 證據

### P0. Recent canonical window 仍是 distribution pathology，不可誤判為 readiness
**現況**
- primary drift window=`500`
- `bull=100%`
- `win_rate=0.806`、`avg_quality=0.3406`
- shared shift 仍集中在 `feat_4h_bias20 / feat_4h_ma_order / feat_4h_bb_pct_b`，並伴隨 `feat_dxy / feat_vix` compression

**風險**
- 若只看高 win-rate，會把 bull-only concentration 誤判成 deployment readiness

**下一步**
- 繼續對 canonical recent-window 做 root-cause drill-down
- 維持 decision-quality / execution guardrails，不因局部高分放寬 live runtime

### P1. Current live q35 / support-aware governance 仍未收斂
**現況**
- live predictor 仍被 breaker 先擋下，當前 exact bucket 支持仍不足
- `q15_support_audit`：`insufficient_support_everywhere`
- `q15_bucket_root_cause`：`missing_structure_quality`
- leaderboard probe 仍是 `dual_role_governance_active`

**風險**
- 若把 q35 redesign 或 profile split 寫成 closure，會掩蓋真正的 breaker-first blocker

**下一步**
- breaker 未解除前，q35 / support-aware work 僅能作 governance candidate，不得升級成 deployment closure
- 補 exact support 與 live row structure-quality evidence

### P1. Fast heartbeat 仍依賴 timeout fallback 才能關閉多個治理腳本
**現況**
- 本輪 `recent_drift_report`、`hb_q35_scaling_audit`、`feature_group_ablation`、`bull_4h_pocket_ablation`、`hb_leaderboard_candidate_probe` 皆 timeout，但 runner 有沿用最新 artifact 做 machine-readable summary

**風險**
- cron 雖已 fail-soft，但 serial governance 腳本若長期 timeout，artifact freshness 會變成隱性治理風險

**下一步**
- 優先縮短上述 P1 腳本 runtime 或強化 freshness / stale 標示
- 不可把 timeout fallback 誤寫成 artifact 已即時刷新

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
- 持續把 sparse-source 嚴格留在 research / blocked 層

---

## Not Issues
- 不是 collect pipeline 停住：本輪 `raw/features/labels` 皆有新增
- 不是 mixed-horizon breaker 假陽性：本輪 audit 已確認 `canonical_breaker_active`
- 不是 operator surface 看不到 breaker gap：`/api/status` runtime closure summary 已補上 release math
- 不是主要產品面 regression：本輪關鍵 regression **130 tests passed**

---

## Current Priority
1. 維持 **breaker-first**，直接追 `7/50 → 15/50` 的 canonical release 證據與 root-cause
2. 收斂 **recent 500 bull concentration pathology**，避免把局部高 win-rate 誤判成 readiness
3. 在 breaker 不鬆動前，僅把 **q35 / support-aware governance** 當 reference-only candidate
4. 補 **Binance 真實 venue artifact 鏈**，把 execution lane 從 product-like 推到 venue-backed
