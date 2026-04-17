# ISSUES.md — Current State Only

_最後更新：2026-04-17 13:38 UTC_

只保留目前有效 blocker；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線
本輪 heartbeat 已把 **fast governance 的第一條真 cache-hit lane** 落地為可驗證事實：
- `scripts/hb_parallel_runner.py` 新增 **leaderboard candidate alignment snapshot refresh**，當 semantic signature 沒變、只有 code-dependency freshness 過期時，會先輕量刷新 `data/leaderboard_feature_profile_probe.json`，再安全 reuse
- `tests/test_hb_parallel_runner.py` 已補 regression，證明：**只有 code freshness 過期時可 refresh+reuse；semantic drift 仍必須拒絕 cache**
- 最新 fast run 已拿到 machine-readable 證據：
  - `serial_results.hb_leaderboard_candidate_probe.cached=true`
  - `cache_reason=refreshed_leaderboard_candidate_artifact_reused`
  - `generated_at=2026-04-17T13:37:23.692942Z`

**本輪已驗證事實**
- fast heartbeat：`Raw=30615 / Features=22033 / Labels=61792`
- canonical diagnostics：`Global IC 14/30`、`TW-IC 28/30`
- live runtime：`CIRCUIT_BREAKER`
- canonical recent 50：`11/50`，recent win rate=`22%`，距 release floor `15/50` 還差 **4 勝**
- recent drift：`window=500`、`alerts=['label_imbalance','regime_concentration','regime_shift']`、`dominant_regime=bull(100%)`
- 測試：`python -m pytest tests/test_hb_parallel_runner.py -q` → **48 passed**
- runtime evidence：`python scripts/hb_parallel_runner.py --fast` → **leaderboard candidate lane cached=true**

---

## Open Issues

### P0. Circuit breaker 仍是唯一 deployment blocker
**現況**
- canonical 1440m recent 50 = `11/50`
- recent win rate = `22%`，低於 release floor `30%`
- `/predict` / drilldown / breaker audit 一致回報 `circuit_breaker_active`

**風險**
- breaker 未解除前，任何 q15/q35/support/profile 研究都不能包裝成 live-ready closure

**下一步**
- 直接追 canonical recent 50 tail root cause，目標從 `11/50 → 15/50`
- 所有主要 surface 維持 breaker-first truth

### P0. Recent canonical 500 仍是未解釋的 distribution pathology
**現況**
- `window=500`、`dominant_regime=bull(100%)`
- `alerts=['label_imbalance','regime_concentration','regime_shift']`
- `avg_quality=0.3407`，與前一個 sibling window 相比明顯轉弱，但目前仍只停在 artifact 描述

**風險**
- 若只看局部高 win rate (`0.806`)，會把 bull pocket 誤讀成 deployment readiness

**下一步**
- 把 recent 500 的 target path / feature variance / distinct-count 收斂成可 patch 的 root cause
- guardrail 繼續開啟，直到 pathology 被解釋或被修補

### P1. Fast governance 仍只有一條 cache-hit；其他重型 lanes 仍 timeout
**現況**
- 已解決：`hb_leaderboard_candidate_probe` 可 refresh+reuse，拿到 `cached=true`
- 尚未解決：`recent_drift_report`、`hb_q35_scaling_audit`、`feature_group_ablation`、`bull_4h_pocket_ablation` 仍 timeout
- fast summary 目前能區分 `cached / timeout / fallback artifact`，但 cache reuse 還沒擴到其他重型治理 lanes

**風險**
- cron 雖已不再完全卡死，但 fast governance 成本仍過高，重型 lane 仍欠缺真正的 reuse 閉環

**下一步**
- 優先把相同的 safe refresh / cache reuse 機制擴到 `recent_drift_report` 或 `feature_group_ablation`
- 下一輪至少再拿到一條非-leaderboard 的 `cached=true` 證據

### P1. q35 / base-stack redesign 仍是治理候選，不是 live closure
**現況**
- `hb_q35_scaling_audit` 雖 timeout，但 fallback artifact 仍顯示：`base_stack_redesign_discriminative_reweight_crosses_trade_floor`
- 同時 live runtime 仍被 `circuit_breaker_active` 先擋下
- 這代表 q35 redesign 目前只能算 **background governance candidate**，不是當前 blocker closure

**風險**
- 若把 q35 redesign 誤寫成主 blocker 已解，會偏離當前 runtime closure truth

**下一步**
- breaker 未解除前，q35/base-stack 只保留為治理候選
- 等 canonical recent tail 收斂後，再重新驗證 q35 runtime contract

---

## Not Issues
- 不是 collect pipeline 停住：本輪 `raw/features/labels` 都有新增
- 不是 leaderboard candidate cache 邏輯缺失：**已取得真實 cached=true 證據**
- 不是 IC 全面崩壞：本輪 `Global IC 14/30`、`TW-IC 28/30`

---

## Current Priority
1. 先解除 **circuit breaker**：把 `11/50` 推進到 `15/50`
2. 把 **recent canonical 500 pathology** 收斂成可修補根因
3. 把 **fast cache-hit** 從 leaderboard candidate 擴到至少另一條重型治理 lane
4. breaker 未解除前，q15/q35/base-stack 只作治理候選，不得覆蓋 live blocker truth
