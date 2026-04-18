# q15 Boundary Replay

- generated_at: **2026-04-18 12:08:40.638156**
- target_col: **simulated_pyramid_win**
- verdict: **boundary_replay_not_applicable**
- reason: 目前 q15 root-cause verdict 不是 boundary_sensitivity_candidate，boundary replay 不是本輪主路徑。

## Current live row
- signal: **BUY**
- regime/gate: **bull / CAUTION**
- structure bucket: **CAUTION|structure_quality_caution|q15**
- structure_quality: **0.2656**
- entry_quality: **0.55** (trade_floor_gap=0.0)
- support_route: **exact_bucket_supported**
- floor_cross_legality: **legal_component_experiment_after_support_ready**

## Boundary replay
- legacy bucket rows: **96**
- replay bucket: **CAUTION|base_caution_regime_or_bias|q15**
- replay bucket rows: **0**
- generated_rows_via_boundary_only: **9**
- preexisting_rows_in_replay_bucket: **0**
- generated_row_share: **None**
- dominant_neighbor_bucket: **CAUTION|base_caution_regime_or_bias|q15** rows=50

## feat_4h_bb_pct_b minimal counterfactual
- raw before/after: **0.3079 → 0.5561**
- structure_quality: **0.2656 → 0.35**
- bucket_after: **CAUTION|base_caution_regime_or_bias|q15**
- entry_quality: **0.55 → 0.5711**
- trade_floor_gap_after: **0.0211**
- allowed_layers_after: **1** (entry_quality_C_single_layer)
- counterfactual verdict: **counterfactual_crosses_floor_after_rebucket**
- counterfactual reason: feat_4h_bb_pct_b 的最小反事實不只改變 bucket，也讓 entry_quality 跨過 trade floor；下一輪可升級成 guarded experiment。

## Next
- next_action: 依 q15 root-cause / support audit 的既有 blocker 繼續治理。
- verify_next: 比較 current row 與 dominant neighbor bucket 的 4H component 差值，再做最小 counterfactual。