# q15 Boundary Replay

- generated_at: **2026-04-20 06:18:10.229366**
- target_col: **simulated_pyramid_win**
- verdict: **boundary_replay_not_applicable**
- reason: 目前 q15 root-cause verdict 不是 boundary_sensitivity_candidate，boundary replay 不是本輪主路徑。

## Current live row
- signal: **CIRCUIT_BREAKER**
- regime/gate: **chop / CAUTION**
- structure bucket: **CAUTION|base_caution_regime_or_bias|q15**
- structure_quality: **0.1769**
- entry_quality: **0.5218** (trade_floor_gap=-0.0282)
- support_route: **exact_bucket_present_but_below_minimum**
- floor_cross_legality: **runtime_blocker_preempts_floor_analysis**

## Boundary replay
- legacy bucket rows: **15**
- replay bucket: **CAUTION|base_caution_regime_or_bias|q35**
- replay bucket rows: **0**
- generated_rows_via_boundary_only: **243**
- preexisting_rows_in_replay_bucket: **0**
- generated_row_share: **None**
- dominant_neighbor_bucket: **CAUTION|base_caution_regime_or_bias|q35** rows=1139

## feat_4h_bb_pct_b minimal counterfactual
- raw before/after: **0.2804 → 0.7895**
- structure_quality: **0.1769 → 0.35**
- bucket_after: **CAUTION|base_caution_regime_or_bias|q35**
- entry_quality: **0.5218 → 0.5651**
- trade_floor_gap_after: **0.0151**
- allowed_layers_after: **1** (entry_quality_C_single_layer)
- counterfactual verdict: **counterfactual_crosses_floor_after_rebucket**
- counterfactual reason: feat_4h_bb_pct_b 的最小反事實不只改變 bucket，也讓 entry_quality 跨過 trade floor；下一輪可升級成 guarded experiment。

## Next
- next_action: 依 q15 root-cause / support audit 的既有 blocker 繼續治理。
- verify_next: 先讓 canonical breaker release condition 接近解除，再重跑 hb_predict_probe.py 與 q15 root-cause artifact。