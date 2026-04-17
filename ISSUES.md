# ISSUES.md — Current State Only

_最後更新：2026-04-17 11:13 UTC_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留舊流水帳。

---

## 當前主線
本輪 heartbeat 聚焦 **fast governance de-timeout**，把 fast mode 的 freshness-reuse contract 從單一 `recent_drift_report` / `q35_scaling_audit` / leaderboard lane，擴到更多產品化治理腳本，避免 cron 每輪都重跑同一批重型分析。

**本輪已落地**
- `scripts/hb_parallel_runner.py`
  - 新增通用 `_artifact_cache_hit_from_dependencies()`
  - fast mode 新增 cache reuse lane：
    - `feature_group_ablation`
    - `bull_4h_pocket_ablation`
    - `hb_q15_support_audit`
    - `hb_q15_bucket_root_cause`
    - `hb_q15_boundary_replay`
  - 既有 leaderboard cache 也改走同一套 dependency-based contract，summary 會保留 `cached / cache_reason / cache_details`
- `tests/test_hb_parallel_runner.py`
  - 新增 cache hit / dependency invalidation / dispatcher regression
  - `python -m pytest tests/test_hb_parallel_runner.py -q` → **45 passed**

**本輪實測事實**
- fast heartbeat（含 collect）後：`Raw=30607 / Features=22025 / Labels=61780`
- canonical diagnostics：`Global IC 14/30`、`TW-IC 28/30`
- live predictor：`CIRCUIT_BREAKER`
- canonical recent 50：`8/50`，距 release floor `15/50` 還差 **7 勝**
- recent drift：`window=500`、`distribution_pathology`、`bull=100%`
- fast runtime 仍 timeout 的 lane：
  - `recent_drift_report`
  - `hb_q35_scaling_audit`
  - `feature_group_ablation`
  - `bull_4h_pocket_ablation`
  - `hb_leaderboard_candidate_probe`

---

## Open Issues

### P0. Circuit breaker 仍是 deployment blocker
**現況**
- canonical 1440m recent 50 = `8/50`
- recent win rate = `16%`，仍低於 release floor `30%`
- `/api/status` / probe / drilldown 都仍維持 breaker-first truth

**風險**
- 若把 q35 / q15 / profile split 誤寫成主 blocker，會偏離真實 runtime closure

**下一步**
- 繼續直接追 canonical recent 50/500 的 tail root cause
- breaker 未解除前，不得把治理候選包裝成 deployment closure

### P0. Fast governance timeout 仍未收斂到可穩定重用 fresh artifact
**現況**
- 本輪已把 cache contract 擴到 feature ablation / bull pocket / q15 lanes
- 但實際 fast run 仍未命中這些新 cache，因為當前 artifact 不是 fresh baseline，且部分 lane 仍受上游 live probe / drilldown 刷新影響

**風險**
- fast cron 仍在重跑重型治理腳本，timeout 後只能依賴 fallback artifact
- operator 仍難判斷哪些 lane 已可安全 reuse、哪些只是 timeout fail-soft

**下一步**
- 先產出一輪 fresh baseline artifact，讓新 cache contract 能真正接管下一輪 fast run
- 再把 `live_predict_probe` / `live_decision_quality_drilldown` 改成 semantic freshness gating，而不是只靠檔案 mtime

### P1. Recent canonical window 仍是 distribution pathology
**現況**
- primary drift window=`500`
- `alerts=['label_imbalance', 'regime_concentration', 'regime_shift']`
- `dominant_regime=bull(100%)`

**風險**
- 若只看局部高 win rate，會把 bull-only concentration 誤判成 readiness

**下一步**
- 做 canonical recent-window target-path / feature variance drill-down
- 維持 decision-quality / execution guardrails，不因局部高分放寬 live runtime

### P1. q35 / support-aware governance 仍是研究候選，不是 deployment closure
**現況**
- q35 audit 仍是 `bias50_formula_may_be_too_harsh`
- runtime 仍先被 breaker 擋下
- leaderboard / train 維持 dual-role governance split，不是 parity drift closure

**風險**
- 若把 q35 redesign 或 profile split 誤寫成 closure，會掩蓋 breaker 與 recent pathology

**下一步**
- breaker 未解除前，q35 / q15 / profile split 只可作治理候選
- 維持 live probe、drilldown、status 的 blocker-first 對齊

### P1. Binance / OKX 仍缺真實 venue-backed execution artifact 鏈
**現況**
- runtime truth / Dashboard / Strategy Lab surface 已存在
- 但 partial-fill / cancel / restart-replay 的真實 venue-backed artifact 仍不足

**下一步**
- 補 Binance 真實 venue artifact 鏈
- 驗證 `/api/status`、Dashboard、Strategy Lab 對同一 lane 顯示同一 execution truth

---

## Not Issues
- 不是 fast cache contract 完全缺席：本輪已把 reuse contract 擴到 feature ablation / bull pocket / q15 lanes
- 不是 breaker 假陽性：本輪 circuit-breaker audit 仍是 `canonical_breaker_active`
- 不是 collect pipeline 停住：本輪 `raw/features` 仍有新增
- 不是 IC 完全崩壞：本輪 `Global IC 14/30`、`TW-IC 28/30`

---

## Current Priority
1. 讓新 cache contract **真正命中一次 fresh artifact reuse**，把 fast governance timeout 從程式碼能力變成實際 runtime 事實
2. 維持 **breaker-first**，直接追 `8/50 → 15/50`
3. 收斂 **recent 500 bull concentration pathology** 的 machine-readable root cause
4. 補 **Binance 真實 venue artifact 鏈**，把 execution lane 從 product-like 推到 venue-backed
