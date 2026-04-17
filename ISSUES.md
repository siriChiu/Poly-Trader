# ISSUES.md — Current State Only

_最後更新：2026-04-17 11:43 UTC_

只保留目前有效 blocker；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線
本輪 heartbeat 聚焦 **runtime blocker truth + fast governance correctness**：
- fast heartbeat 已重新實測並刷新 current-state artifacts
- `hb_q15_bucket_root_cause.py` 已修正 **circuit breaker active 時誤把 q15 根因寫成 structure/projection 問題** 的治理誤報
- q15 root-cause 現在明確輸出 `runtime_blocker_preempts_bucket_root_cause`，避免 Dashboard / heartbeat / operator 把背景研究誤讀成當前 live blocker

**本輪已驗證事實**
- fast heartbeat：`Raw=30609 / Features=22027 / Labels=61781`
- canonical diagnostics：`Global IC 14/30`、`TW-IC 28/30`
- live runtime：`CIRCUIT_BREAKER`
- canonical recent 50：`8/50`，距 release floor `15/50` 還差 **7 勝**
- recent drift：`window=500`、`alerts=['label_imbalance','regime_concentration','regime_shift']`、`dominant_regime=bull(100%)`
- q15 root-cause：`runtime_blocker_preempts_bucket_root_cause`（已不再誤報 `missing_structure_quality`）
- 測試：`python -m pytest tests/test_q15_bucket_root_cause.py -q` → **4 passed**

---

## Open Issues

### P0. Circuit breaker 仍是唯一 deployment blocker
**現況**
- canonical 1440m recent 50 = `8/50`
- recent win rate = `16%`，低於 release floor `30%`
- probe / drilldown / breaker audit / q15 root-cause 現在都已對齊 breaker-first truth

**風險**
- 若把 q15/q35/support/profile split 誤寫成當前 blocker，會偏離真實 runtime closure

**下一步**
- 直接追 canonical recent 50/500 的 tail root cause
- breaker 未解除前，不得把 q15/q35 研究候選包裝成 deployment closure

### P0. Fast governance 仍有重型 lane timeout
**現況**
- fast mode 仍有 timeout lane：
  - `recent_drift_report`
  - `hb_q35_scaling_audit`
  - `feature_group_ablation`
  - `bull_4h_pocket_ablation`
  - `hb_leaderboard_candidate_probe`
- 雖然 fail-soft artifact 仍可讀，但 machine-readable summary 仍需更明確區分 fresh / timeout fallback / cached reuse

**風險**
- cron 仍可能長時間卡在重型治理腳本
- operator 容易把 fallback artifact 當成當輪 fresh fact

**下一步**
- 先讓至少一條重型 governance lane 真正命中 fresh cache reuse
- 補 semantic freshness gating，避免只靠 mtime 判新鮮度

### P1. Recent canonical window 仍是 distribution pathology
**現況**
- primary drift window=`500`
- `dominant_regime=bull(100%)`
- `tail_streak=6x1`，但同窗也存在 `adverse_streak=259x1`
- feature drift 顯示 `compressed=9`、`null_heavy=10`

**風險**
- 若只看局部高 win rate，會把 bull-concentrated pocket 誤判成 readiness

**下一步**
- 對 recent canonical rows 做 target-path / feature variance / distinct-count root cause drill-down
- 維持 decision-quality / execution guardrails，不因局部高分放寬 runtime

### P1. q35 support / profile governance 仍是背景治理，不是當前 live blocker
**現況**
- q35 audit 仍顯示 `bias50_formula_may_be_too_harsh`
- leaderboard/train 仍是 `dual_role_governance_active`
- 但本輪已確認：這些都在 circuit breaker 之後，不能覆蓋 live blocker truth

**下一步**
- breaker 未解除前，q35 / q15 / profile split 僅作治理候選
- 所有 surface 必須維持 breaker-first contract

### P1. Binance / OKX 仍缺真實 venue-backed execution artifact 鏈
**現況**
- execution/runtime surface 已有 machine-readable blocker 與 reconciliation path
- 但 partial-fill / cancel / restart-replay 的真實 venue-backed artifacts 仍不足

**下一步**
- 補 Binance 真實 venue artifact 鏈
- 驗證 `/api/status`、Dashboard、Strategy Lab 對同一 lane 顯示同一 execution truth

---

## Not Issues
- 不是 collect pipeline 停住：本輪 `raw/features` 仍有新增
- 不是 IC 全面崩壞：本輪 `Global IC 14/30`、`TW-IC 28/30`
- 不是 q15 root-cause 真的缺 structure_quality：本輪已修成 breaker-first truth

---

## Current Priority
1. 維持 **breaker-first**，直接追 `8/50 → 15/50`
2. 讓 fast governance 至少有一條重型 lane **真實 cache hit**
3. 把 recent 500 bull concentration 收斂成 machine-readable root cause
4. 補 **Binance 真實 venue-backed artifact 鏈**
