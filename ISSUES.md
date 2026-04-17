# ISSUES.md — Current State Only

_最後更新：2026-04-17 10:47 UTC_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留舊流水帳。

---

## 當前主線
本輪 heartbeat 先修 **fast heartbeat 的 recent drift 重跑超時問題**，把它從「每輪都可能 30s timeout」推進成「**canonical label 輸入沒變時直接重用 fresh artifact**」。

**本輪已落地**
- `scripts/recent_drift_report.py` 現在會把 `source_meta={label_rows, latest_label_timestamp}` 寫進 artifact
- `scripts/hb_parallel_runner.py` fast mode 新增 fresh-artifact reuse：
  - 針對 `recent_drift_report`
  - 若 canonical 1440m labels 簽名沒變，且 artifact 新於腳本依賴，就**不重跑**
  - `serial_results` 明確新增 `cached / cache_reason / cache_details`
- targeted regression：`python -m pytest tests/test_hb_parallel_runner.py -q` → **42 passed**
- runtime evidence：
  - `python scripts/recent_drift_report.py` → **77.7s**，成功重建含 `source_meta` 的 drift artifact
  - 之後 `_run_serial_command(['python','scripts/recent_drift_report.py'])` 在 fast mode 會回傳 `cached=True`、`cache_reason=fresh_recent_drift_artifact_reused`

**本輪實測事實**
- fast heartbeat：`Raw=30605 / Features=22023 / Labels=61777`
- canonical diagnostics：`Global IC 14/30`、`TW-IC 28/30`
- live predictor：`CIRCUIT_BREAKER`
- canonical 1440m recent 50：**7/50**，距 release 還差 **8 勝**
- recent drift：primary window=`500`，`distribution_pathology`，`bull=100%`

---

## Open Issues

### P0. Circuit breaker 仍是 live deployment blocker
**現況**
- canonical 1440m recent 50 = `7/50`
- recent win rate = `14%`，仍低於 release floor `30%`
- `/api/status` / probe / drilldown 都仍指向 canonical breaker truth

**風險**
- 若把 q15/q35 或 profile split 誤寫成主 blocker，會偏離 breaker-first 真相

**下一步**
- 直接追 `7/50 → 15/50` 的 canonical tail root cause
- breaker 未解除前，不得把治理候選包裝成 deployment closure

### P0. Recent canonical window 仍是 distribution pathology
**現況**
- primary drift window=`500`
- `alerts=['label_imbalance', 'regime_concentration', 'regime_shift']`
- `bull=100%`、`win_rate=0.806`

**風險**
- 若只看高 win rate，會把 bull-only concentration 誤判成 readiness

**下一步**
- 做 canonical recent-window root-cause drill-down
- 維持 decision-quality / execution guardrails，不因局部高分放寬 live runtime

### P1. Fast governance timeout 仍未收斂，只是先拿下 recent drift lane
**已改善**
- `recent_drift_report` 現在在 **canonical labels 未變** 時可直接重用 fresh artifact
- fast summary 可明確區分：`cached` vs `fallback_artifact_used`

**仍未解**
- `hb_q35_scaling_audit`
- `feature_group_ablation`
- `bull_4h_pocket_ablation`
- `hb_leaderboard_candidate_probe`
仍會 hit fast timeout

**下一步**
- 對上述腳本做同級別的 freshness gating / dependency signature reuse，或直接縮時
- 不可把 timeout fallback 誤寫成 fresh recompute

### P1. q35 / support-aware governance 仍未收斂
**現況**
- q35 audit 仍給 `bias50_formula_may_be_too_harsh`
- live 仍先被 breaker 擋下
- 目前還不是 q35 deployment closure，而是 governance candidate

**風險**
- 若把 q35 redesign 誤寫成 closure，會掩蓋 breaker 與 recent pathology

**下一步**
- breaker 未解除前，q35 僅能作治理候選
- 補 exact support 與 live row 結構證據

### P1. Leaderboard / shrinkage / bull-pocket governance artifact 仍偏慢
**現況**
- current truth 仍顯示 dual-role governance：`leaderboard=core_only` vs `train=core_plus_macro`
- 但 fast lane 對應 probe / ablation artifact 仍常 timeout

**風險**
- operator 看到的是舊 governance snapshot，不是當輪 fresh closure

**下一步**
- 把 feature ablation / bull pocket / leaderboard probe 納入同一套 freshness reuse 或 runtime 縮時策略

### P1. Binance / OKX 仍缺真實 venue-backed partial-fill / cancel / restart-replay artifact
**現況**
- runtime truth / drilldown / Dashboard / Strategy Lab 已有產品 surface
- 但 execution artifact 鏈仍不足，尚不能宣稱 live-ready

**下一步**
- 補 Binance 真實 venue-backed artifact 鏈
- 驗證 `/api/status`、Dashboard、Strategy Lab 對同一 lane 的 execution truth 完全一致

---

## Not Issues
- 不是 recent drift artifact 完全不可重用：**本輪已補 fresh cache reuse contract**
- 不是 fast summary 看不出 reuse/fallback 差異：`serial_results` 已新增 `cached / cache_reason / cache_details`
- 不是 collect pipeline 停住：本輪 `raw/features/labels` 仍有新增
- 不是 mixed-horizon breaker 假陽性：breaker audit 仍是 `canonical_breaker_active`

---

## Current Priority
1. 維持 **breaker-first**，直接追 `7/50 → 15/50`
2. 把 **recent drift cache reuse** 從 `recent_drift_report` 擴到其餘重型治理腳本
3. 收斂 **recent 500 bull concentration pathology** 的 root cause
4. 補 **Binance 真實 venue artifact 鏈**，把 execution lane 從 product-like 推到 venue-backed
