# ISSUES.md — Current State Only

_最後更新：2026-04-19 03:57 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **本輪已完成 full train / support-aware profile refresh**：`scripts/feature_group_ablation.py`、`scripts/bull_4h_pocket_ablation.py`、`model/train.py` 已重跑；`model/last_metrics.json` 現在改為 `feature_profile=core_plus_macro`、`feature_profile_meta.source=bull_4h_pocket_ablation.support_aware_profile`、`support_cohort=bull_collapse_q35`、`exact_live_bucket_rows=41/50`，不再沿用過期的 exact-supported production profile。
- **train/runtime/leaderboard 治理已重新對齊**：`scripts/hb_leaderboard_candidate_probe.py` 與 `scripts/hb_model_leaderboard_api_probe.py` 現在回報 `dual_profile_state=leaderboard_global_winner_vs_train_support_fallback`、`governance_contract.verdict=dual_role_governance_active`；global 排名維持 `core_only`，production 配置改為 support-aware `core_plus_macro`。
- **Strategy Lab / API / browser surface 已同步最新治理真相**：`/lab` 模型排行榜治理卡已顯示 `generated 2026/4/19 上午3:55:38`、`Global 排名 core_only`、`Production 配置 core_plus_macro`、`closure=global_ranking_vs_support_aware_production_split`；不再把 stale exact-supported profile 當 current-live closure。
- **current-live 主 blocker 仍是 canonical circuit breaker**：`deployment_blocker=circuit_breaker_active`、`recent 50 wins=0/50`、`additional_recent_window_wins_needed=15`、`streak=137`、`allowed_layers=0`。
- **q15 exact support 仍低於 minimum**：`current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15`、`rows=41/50`、`gap=9`、`support_progress.status=stalled_under_minimum`；但這已是治理上明示的 support-aware fallback，不再是 train/runtime parity blocker。
- **bull exact-vs-spillover pathology 仍未產品化 closure**：exact live lane `41 rows / WR 100% / quality 0.697 / pnl +2.20%`，broader `bull|ALLOW` spillover `159 rows / WR 0% / quality -0.276 / pnl -1.03%`。
- **venue readiness 仍未 closure**：`/execution/status` 與 `/lab` 皆顯示 `live exchange credential 尚未驗證 · order ack lifecycle 尚未驗證 · fill lifecycle 尚未驗證`。

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
- 若 heartbeat / UI 又把 q15 support、spillover 或 train-profile fallback 誤寫成主 blocker，operator 會再次失去 current-live 真相。

**下一步**
- 維持 breaker-first truth，所有 current-live surface 持續以 release math 作唯一 deployment blocker。
- 驗證：`python scripts/hb_predict_probe.py`、`/lab` live deployment sync、`/execution/status`。

### P1. q15 exact support remains under minimum, but governance is now correctly synced to support-aware production fallback
**現況**
- `current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15`
- `current_live_structure_bucket_rows=41`
- `minimum_support_rows=50`
- `gap_to_minimum=9`
- `support_progress.status=stalled_under_minimum`
- `dual_profile_state=leaderboard_global_winner_vs_train_support_fallback`
- `train_selected_profile=core_plus_macro`
- `train_selected_profile_source=bull_4h_pocket_ablation.support_aware_profile`
- `leaderboard_selected_profile=core_only`

**風險**
- 若 exact bucket 長期停在 41/50，production profile 只能持續 fallback 到 support-aware 路徑，無法回到真正 exact-supported 治理。

**下一步**
- 持續用 support-aware `core_plus_macro` 做 production 描述，直到 exact bucket 真正回到 `>=50` rows。
- 驗證：`python scripts/hb_leaderboard_candidate_probe.py`、`python scripts/hb_model_leaderboard_api_probe.py`、`python scripts/hb_predict_probe.py`、瀏覽器 `/lab` 模型排行榜治理卡。

### P1. bull exact-vs-spillover pathology still lacks a landed gate/calibration/training patch
**現況**
- exact live lane：`41 rows / WR=100% / quality=0.697 / pnl=+2.20%`
- broader spillover：`bull|ALLOW 159 rows / WR=0% / quality=-0.276 / pnl=-1.03%`
- recent pathology 仍是 `100x0`
- top shifts 仍集中在 `feat_4h_bias200 / feat_4h_dist_swing_low / feat_4h_dist_bb_lower`

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
- 驗證：瀏覽器 `/execution/status`、`/lab` live deployment sync。

---

## Not Issues
- **train/runtime/leaderboard exact-supported stale-under-minimum mismatch**：不是；本輪已透過 full train / support-aware profile refresh 修正，`model/last_metrics.json` 與 `/api/models/leaderboard` 現在一致指向 support-aware `core_plus_macro`。
- **leaderboard governance API/UI sync**：不是；`hb_model_leaderboard_api_probe.py` 與瀏覽器 `/lab` 都已顯示 `dual_role_governance_active` 與最新 `generated_at`。
- **model leaderboard 可部署排名**：不是；目前仍是 `placeholder_count=6 / comparable_count=0` 的 placeholder-only 狀態，不能把 #1 當 production deployment 排名。

---

## Current Priority
1. **維持 breaker release math 作為唯一 current-live blocker**
2. **在 exact bucket 未滿 50 rows 前，保持 support-aware `core_plus_macro` production fallback 語義清楚可見**
3. **把 bull|ALLOW spillover pathology 轉成正式 gate/calibration/training patch**
4. **持續保留 venue blockers，直到 credentials / ack / fill 都有 runtime proof**
