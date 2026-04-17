# ISSUES.md — Current State Only

_最後更新：2026-04-17 13:16 UTC_

只保留目前有效 blocker；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線
本輪 heartbeat 聚焦 **fast governance 可重用性 + breaker-first runtime truth**：
- 已在 `scripts/hb_parallel_runner.py` 落地 **leaderboard candidate semantic cache reuse**，不再只靠 data artifact mtime 判定可否重用
- 新 contract 會比對當前 `feature_group_ablation / bull_4h_pocket_ablation / q15_support_audit / live_predict_probe / last_metrics` 的語義簽名，且保留 code dependency freshness（`hb_leaderboard_candidate_probe.py / server/routes/api.py / backtesting/model_leaderboard.py`）
- regression tests 已補上，證明：**語義相同可 reuse、語義漂移必須拒絕 reuse**

**本輪已驗證事實**
- fast heartbeat：`Raw=30614 / Features=22032 / Labels=61791`
- canonical diagnostics：`Global IC 14/30`、`TW-IC 28/30`
- live runtime：`CIRCUIT_BREAKER`
- canonical recent 50：`11/50`，recent win rate=`22%`，距 release floor `15/50` 還差 **4 勝**
- recent drift：`window=500`、`alerts=['label_imbalance','regime_concentration','regime_shift']`、`dominant_regime=bull(100%)`
- current live bucket support：`support_governance_route=no_support_proxy`、`minimum_support_rows=50`、`current_live_structure_bucket_rows=0`
- 測試：`PYTHONPATH=. pytest tests/test_hb_parallel_runner.py tests/test_hb_leaderboard_candidate_probe.py -q` → **60 passed**

---

## Open Issues

### P0. Circuit breaker 仍是唯一 deployment blocker
**現況**
- canonical 1440m recent 50 = `11/50`
- recent win rate = `22%`，低於 release floor `30%`
- live predictor / drilldown / breaker audit 仍一致回報 `circuit_breaker_active`

**風險**
- 只要 breaker 未解除，q15/q35/support/profile 研究都不能包裝成 live-ready closure

**下一步**
- 直接追 canonical recent 50/500 tail root cause
- breaker 未解除前，所有 surface 維持 breaker-first truth

### P0. Fast governance 仍未拿到「實際 cached=True」證據
**現況**
- 本輪已補上 leaderboard candidate 的 semantic cache reuse 邏輯，但最新 fast summary 仍是 `serial_results.cached=false`
- `data/leaderboard_feature_profile_probe.json` 目前早於 `server/routes/api.py`，因此 code-dependency freshness 仍拒絕 reuse
- 重型 lanes 仍 timeout：`recent_drift_report`、`hb_q35_scaling_audit`、`feature_group_ablation`、`bull_4h_pocket_ablation`、`hb_leaderboard_candidate_probe`

**風險**
- cron 仍缺真正的 cache-hit lane，可重用性仍停在 unit-test 正確、尚未拿到 live run evidence

**下一步**
- 先刷新一次 `hb_leaderboard_candidate_probe` artifact 到最新 codebase
- 下一輪 fast run 必須拿到至少一條 `cached=True` machine-readable 證據

### P1. Recent canonical 500 仍是 bull-concentrated distribution pathology
**現況**
- `window=500`、`dominant_regime=bull(100%)`
- recent win rate `0.806`，但被標記為 `distribution_pathology`
- feature drift：`variance=10/56`、`compressed=9`、`distinct=11`、`null_heavy=10`

**風險**
- 若只看局部高 win rate，會把 bull pocket 誤讀成 deployment readiness

**下一步**
- 對 recent canonical rows 做 target-path / feature variance / distinct-count drill-down
- guardrail 持續開啟，直到 pathology 被解釋或被 patch

### P1. q35 / q15 support 仍不足，且目前是 background governance 不是 live blocker 替身
**現況**
- `support_governance_route=no_support_proxy`
- `current_live_structure_bucket_rows=0 / minimum_support_rows=50`
- q15 root cause 仍正確回報 `runtime_blocker_preempts_bucket_root_cause`

**風險**
- 若把 exact support 不足誤寫成當前 deployment blocker，會偏離真實 runtime closure

**下一步**
- breaker-first 前提下，累積 exact support 並維持 q15/q35 僅作治理候選

---

## Not Issues
- 不是 collect pipeline 停住：本輪 `raw/features` 仍有新增
- 不是 IC 全面崩壞：本輪 `Global IC 14/30`、`TW-IC 28/30`
- 不是 leaderboard cache 邏輯缺失：semantic reuse contract 已落地且 regression tests 通過；缺的是 **live cache-hit artifact evidence**

---

## Current Priority
1. 先拿到 **fast governance 真實 cached=True** 證據（優先 leaderboard candidate lane）
2. 維持 **breaker-first**，直接追 `11/50 → 15/50`
3. 把 recent 500 bull concentration 收斂成 machine-readable root cause
4. exact support 未回來前，q15/q35 僅作治理候選，不得覆蓋 live blocker truth
