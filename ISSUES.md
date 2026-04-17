# ISSUES.md — Current State Only

_最後更新：2026-04-17 10:16 UTC_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留舊流水帳。

---

## 當前主線
本輪 heartbeat 先修 **fast heartbeat timeout fallback 的可觀測性缺口**：
- `scripts/hb_parallel_runner.py` 現在會把 serial governance 步驟寫進 `data/heartbeat_<run>_summary.json > serial_results`
- 每一步都會顯示 `success / timed_out / fallback_artifact_used / artifact_path / artifact_generated_at / artifact_age_seconds`
- 目的：讓 operator 直接知道「本輪是即時刷新 artifact，還是 timeout 後沿用舊 snapshot fail-soft 關閉」，避免把 stale governance artifact 誤讀成已刷新事實
- regression 已鎖住 summary contract，避免之後又回退成只看到 stderr timeout、卻看不到 fallback artifact 新舊

本輪實測事實：
- runtime：`python scripts/hb_parallel_runner.py --fast` ✅ 完成（10:11:54 → 10:15 UTC 左右）
- collect：`Raw=30604 / Features=22022 / Labels=61776`，本輪 **+1 / +1 / +0**
- canonical diagnostics：`Global IC 14/30`、`TW-IC 28/30`
- live predictor：`CIRCUIT_BREAKER`，canonical 1440m recent 50 = **7/50**，距 release 還差 **8 勝**
- drift：primary window=`500`，`distribution_pathology`，`bull=100%`，recent artifact 本輪 **timeout fallback**，summary 已明示 fallback 狀態與 artifact age
- q35 / feature ablation / bull pocket / leaderboard probe 也都在本輪 summary 被明確標示為 **timeout + fallback artifact used**
- targeted regression：`python -m pytest tests/test_hb_parallel_runner.py -q` → **39 passed**

---

## Open Issues

### P0. Circuit breaker 仍是 live deployment blocker
**現況**
- canonical 1440m recent 50 = `7/50`
- recent win rate = `14%`，仍低於 release floor `30%`
- `/api/status` / probe / drilldown 已能直接回答還差 `8` 勝

**風險**
- 任何 q15/q35/component patch 若被寫成主 blocker，都會偏離 breaker-first 真相

**下一步**
- 直接追 `7/50 → 15/50` 的 canonical tail root-cause
- breaker 未解除前，不得把治理候選當成 deployment closure

### P0. Recent canonical window 仍是 distribution pathology
**現況**
- primary drift window=`500`
- `alerts=['label_imbalance', 'regime_concentration', 'regime_shift']`
- `bull=100%`、`win_rate=0.806`，但並不代表 live readiness

**風險**
- 若只看高 win-rate，會把 bull-only concentration 誤判成 readiness

**下一步**
- 繼續做 canonical recent-window root-cause drill-down
- 維持 decision-quality / execution guardrails，不因局部高分放寬 live runtime

### P1. Fast heartbeat 多個治理腳本仍依賴 timeout fallback
**現況**
- `recent_drift_report`
- `hb_q35_scaling_audit`
- `feature_group_ablation`
- `bull_4h_pocket_ablation`
- `hb_leaderboard_candidate_probe`
都在 fast mode timeout，runner 目前靠最新 artifact fail-soft 關閉

**本輪已完成**
- summary 現在會 machine-read 持久化每個 timeout/fallback artifact 的新舊與路徑

**剩餘缺口**
- timeout 本身還沒消失；目前只是從「隱性 stale」變成「顯性 stale」

**下一步**
- 優先縮短上述腳本 runtime，或補更嚴格的 stale / freshness policy
- 不可把 fallback artifact 誤寫成已即時刷新

### P1. q35 / support-aware governance 仍未收斂
**現況**
- live 仍先被 breaker 擋下
- q35 audit 結論仍是 `bias50_formula_may_be_too_harsh`
- leaderboard probe 仍是 `dual_role_governance_active`

**風險**
- 若把 q35 redesign 或 profile split 寫成 closure，會掩蓋真正 blocker

**下一步**
- breaker 未解除前，q35/support-aware 僅能作 governance candidate
- 補 exact support 與 live row structure-quality evidence

### P1. Binance / OKX 仍缺真實 venue-backed partial-fill / cancel / restart-replay artifact
**現況**
- runtime truth / drilldown / Dashboard / Strategy Lab 已有產品 surface
- 但 execution artifact 鏈仍不足，尚不能宣稱 live-ready

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
- 不是 collect pipeline 停住：本輪 `raw/features` 仍有新增
- 不是 fast heartbeat 失去閉環：本輪已完成 collect / IC / probe / auto-propose / summary 落地
- 不是 timeout fallback 無法辨識：本輪已把 serial fallback freshness 寫入 `serial_results`
- 不是 mixed-horizon breaker 假陽性：breaker audit 仍是 `canonical_breaker_active`

---

## Current Priority
1. 維持 **breaker-first**，直接追 `7/50 → 15/50` 的 canonical release 證據
2. 收斂 **recent 500 bull concentration pathology**，避免把局部高勝率誤判成 readiness
3. 把 **timeout fallback** 從「可觀測」推進到「真正縮時或刷新」
4. 補 **Binance 真實 venue artifact 鏈**，把 execution lane 從 product-like 推到 venue-backed
