# ISSUES.md — Current State Only

_最後更新：2026-04-19 03:30 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **本輪已修復 leaderboard candidate probe 的 placeholder-only 退化**：`scripts/hb_leaderboard_candidate_probe.py` 現在把 `leaderboard=[] + placeholder_count>0` 視為有效 payload，直接吃 `model_leaderboard_cache.json` / snapshot，不再強制 live rebuild；本輪實測完成時間約 **1.401s**。
- **本輪已修復 `/api/models/leaderboard` 的 governance freshness**：API 會用較新的 `leaderboard_feature_profile_probe.json` 覆寫較舊的 embedded cache governance；`hb_model_leaderboard_api_probe.py` 與瀏覽器 `/lab` 現在都顯示 **`generated_at=2026-04-18T19:29:22Z`**，不再卡在舊的 18:50 snapshot。
- **current-live 主 blocker 仍是 canonical circuit breaker**：`deployment_blocker=circuit_breaker_active`、`recent 50 wins=0/50`、`additional_recent_window_wins_needed=15`、`streak=137`、`allowed_layers=0`。
- **q15 exact support 仍低於 minimum 且本輪已確認停滯**：`current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15`、`rows=41/50`、`gap=9`、`support_progress.status=stalled_under_minimum`、`stagnant_run_count=2`。
- **leaderboard governance 仍未 closure，但 machine-read truth 已同步**：`dual_profile_state=train_exact_supported_profile_stale_under_minimum`、`train_selected_profile=core_plus_macro_plus_4h_structure_shift`、`leaderboard_selected_profile=core_only`、`comparable_count=0`、`placeholder_count=6`。
- **bull exact-vs-spillover pathology 仍在 operator surface 可見**：瀏覽器 `/lab` 顯示 `exact live lane=41 rows / WR 100% / quality 0.697`，`bull|ALLOW spillover=159 rows / WR 0% / quality -0.276`；這仍是後續 gate/calibration patch 的主根因。
- **venue readiness 仍未 closure**：`/lab` live deployment sync 仍顯示 `live exchange credential 尚未驗證 · order ack lifecycle 尚未驗證 · fill lifecycle 尚未驗證`。

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
**現況**
- `deployment_blocker=circuit_breaker_active`
- `recent_window=50`
- `current_recent_window_wins=0`
- `required_recent_window_wins=15`
- `additional_recent_window_wins_needed=15`
- `streak=137`
- `allowed_layers=0`

**風險**
- 若 heartbeat / UI 又把 q15 support、spillover、或單點 component gap 誤寫成主 blocker，operator 會再次失去 current-live 真相。

**下一步**
- 維持 breaker-first truth，所有 current-live surface 繼續以 release math 作唯一 deployment blocker。
- 驗證：`python scripts/hb_predict_probe.py`、`/lab` live deployment sync、`/execution/status`。

### P0. q15 exact support is stalled below minimum while train profile still claims exact-supported production
**現況**
- `current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15`
- `live_current_structure_bucket_rows=41`
- `minimum_support_rows=50`
- `gap_to_minimum=9`
- `support_progress.status=stalled_under_minimum`
- `stagnant_run_count=2`
- `dual_profile_state=train_exact_supported_profile_stale_under_minimum`
- `train_selected_profile=core_plus_macro_plus_4h_structure_shift`
- `leaderboard_selected_profile=core_only`

**風險**
- 若 train/runtime 繼續沿用 exact-supported production profile 敘事，會把 under-minimum 的 q15 bucket 假包裝成已 closure 的 production 支撐。

**下一步**
- 重跑 full train / support-aware profile refresh，讓 `feature_profile_meta` 回到 under-minimum-support 真相，除非 exact bucket 真正回到 `>=50` rows。
- 驗證：`python scripts/hb_leaderboard_candidate_probe.py`、`python scripts/hb_model_leaderboard_api_probe.py`、`python scripts/hb_predict_probe.py`、瀏覽器 `/lab` 模型排行榜治理卡。

### P1. bull exact-vs-spillover pathology still lacks a landed gate/calibration patch
**現況**
- exact live lane：`41 rows / WR=100% / quality=0.697 / pnl=+2.20%`
- broader spillover：`bull|ALLOW 159 rows / WR=0% / quality=-0.276 / pnl=-1.03%`
- runtime closure summary 仍顯示 recent pathology `100x0`，top shifts 仍集中在 `feat_4h_bias200 / feat_4h_dist_swing_low / feat_4h_dist_bb_lower`

**風險**
- 若不把 spillover pocket 轉成正式 gate/calibration/training patch，recent bull tail 仍會持續污染 runtime 解讀與 breaker recovery。

**下一步**
- 直接以 exact-live-lane vs broader spillover 對照追 root cause，優先處理 bull|ALLOW spillover 為何仍被 broader scope 吃進來。
- 驗證：`data/live_decision_quality_drilldown.json`、`python scripts/hb_predict_probe.py`、targeted pytest、瀏覽器 `/lab` 的 `🧬 Live lane / spillover 對照` 卡。

### P1. venue readiness is still unverified
**現況**
- live exchange credential 未驗證
- order ack lifecycle 未驗證
- fill lifecycle 未驗證

**風險**
- 即使 breaker 未來解除、leaderboard 與 gate 語義更清楚，也不能把 execution surface 誤讀成已可實盤。

**下一步**
- 持續在 operator surface 保留 venue blockers，直到 runtime artifact 證明 credentials / ack / fill 都 closure。
- 驗證：瀏覽器 `/execution`、`/execution/status`、`/lab` live deployment sync。

---

## Not Issues
- **direct candidate probe timeout**：不是；本輪已修復，`hb_leaderboard_candidate_probe.py` 約 **1.401s** 即可完成，且不再因 placeholder-only cache 觸發 live rebuild。
- **leaderboard governance API/UI freshness mismatch**：不是；本輪已修復，`/api/models/leaderboard` 與 `/lab` 都讀到 **`generated_at=2026-04-18T19:29:22Z`** 的最新 governance artifact。
- **model leaderboard 可部署排名**：不是；目前仍是 `placeholder_count=6 / comparable_count=0` 的 placeholder-only 狀態，不能把 #1 當 production deployment 排名。

---

## Current Priority
1. **維持 breaker release math 作為唯一 current-live blocker**
2. **把 train/runtime/leaderboard profile 敘事降回 41/50 under-minimum-support 真相**
3. **把 bull|ALLOW spillover pathology 轉成正式 gate/calibration/training patch**
4. **持續保留 venue blockers，直到 credentials / ack / fill 都有 runtime proof**
