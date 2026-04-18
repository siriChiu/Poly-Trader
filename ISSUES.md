# ISSUES.md — Current State Only

_最後更新：2026-04-18 12:55 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線
- **fast lane 已完成 ablation fail-soft 產品化**：`hb_parallel_runner.py` 現在會在 **canonical 1440m labels 只小幅 drift（<=12 rows / <=6h）** 時，安全重用 `feature_group_ablation.json` 與 `bull_4h_pocket_ablation.json`。
- 本輪 `data/heartbeat_fast_summary.json` 已驗證：
  - `serial_results.feature_group_ablation.cached=true`
  - `cache_reason=bounded_label_drift_feature_group_ablation_artifact_reused`
  - `serial_results.bull_4h_pocket_ablation.cached=true`
  - `cache_reason=bounded_label_drift_bull_4h_pocket_artifact_reused`
- 這代表 **fast heartbeat 不再因 ablation 重跑而卡在 45s/20s timeout**；cron 內能維持 machine-readable shrinkage / bull-pocket 治理證據。
- 目前真正的 deployment blocker 仍是 **current live q35 exact support = 0 / 50**，不是 fast-lane artifact freshness。

---

## Open Issues

### P0. current live q35 exact support 仍是 deployment blocker
**現況**
- live row = `bull / CAUTION / CAUTION|structure_quality_caution|q35`
- `current_live_structure_bucket_rows=0`
- `minimum_support_rows=50`
- `deployment_blocker=unsupported_exact_live_structure_bucket`
- `runtime_closure_state=patch_active_but_execution_blocked`
- q35 discriminative redesign 已把 raw entry quality 拉到可跨 floor 的區域，但 execution 仍被 exact-support blocker 壓回 `allowed_layers=0`

**風險**
- 若 surface 只看 patch active / entry quality，而沒有 exact-support blocker，operator 會誤讀成可部署。

**下一步**
- 只以 current live q35 bucket 當 deployment gate，持續追 `0 -> 50 rows`
- 確保 `live_predict_probe.json`、`live_decision_quality_drilldown.json`、`heartbeat_fast_summary.json` 三處對 blocker / minimum / gap / support route 完全一致

### P0. recent canonical 500-row distribution pathology 仍未收斂
**現況**
- primary window = recent 500
- `alerts = label_imbalance + regime_concentration + regime_shift`
- `win_rate=0.8560` vs full `0.6381`（`Δ=+0.2179`）
- dominant regime = `bull (99.20%)`
- sibling-window top shifts = `feat_4h_bb_pct_b / feat_4h_vol_ratio / feat_eye`
- new compressed = `feat_atr_pct / feat_vix`
- tail streak = `71x1`

**風險**
- calibration / governance 仍可能被 bull-only pathological window 汙染。
- 如果只看 broader scope 高分數，會再次把 pathology 包裝成 deployment-ready。

**下一步**
- 產出 recent 500 canonical rows 的 root-cause patch / artifact（variance、distinct-count、target-path）
- 在根因真正落地前，維持 decision-quality guardrails，不把 broader lane 當 current-live truth

### P1. leaderboard fresh cache refresh 仍停在 stale snapshot
**現況**
- `leaderboard_payload_source=latest_persisted_snapshot`
- `leaderboard_payload_stale=true`
- `leaderboard_payload_cache_error=CallbackContainer/xgboost circular import`
- candidate governance probe 雖可讀，但仍不是 fresh rebuild truth

**風險**
- Strategy Lab / leaderboard 仍有 stale-first 風險；模型治理可能繼續依賴舊 snapshot。

**下一步**
- 修復 `model_leaderboard_cache.json` refresh path
- 讓 probe 回到 fresh cache / current snapshot，而不是只靠 old snapshot fallback

---

## Not Issues
- **fast-lane ablation timeout**：本輪已降級為非 blocker。`feature_group_ablation` / `bull_4h_pocket_ablation` 已在 fast mode 成功 bounded-reuse，且 summary 保留 `cache_reason / cache_details / artifact_age_seconds`。
- **q15 exact support**：`q15_support_audit.json` 仍顯示 `exact_bucket_supported`，但 current live row 不是 q15，因此不是當輪 blocker。
- **240m / 1440m label freshness**：目前仍屬 lookahead horizon 預期，不是 blocker。

---

## Current Priority
1. **補 current q35 exact support 到 50 rows，解除 deployment blocker**
2. **把 recent 500 pathology 升級成可直接行動的 root-cause patch / artifact**
3. **修掉 leaderboard fresh cache refresh，讓治理不再 stale-first**
