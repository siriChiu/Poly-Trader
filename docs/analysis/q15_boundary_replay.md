# q15 Boundary Replay

- generated_at: **2026-04-21 11:37:21.661499**
- target_col: **simulated_pyramid_win**
- verdict: **boundary_replay_not_applicable**
- reason: 目前 q15 root-cause verdict 不是 boundary_sensitivity_candidate，boundary replay 不是本輪主路徑。

## Current live row
- signal: **HOLD**
- regime/gate: **bull / CAUTION**
- structure bucket: **CAUTION|structure_quality_caution|q35**
- structure_quality: **0.5019**
- entry_quality: **0.5556** (trade_floor_gap=0.0056)
- support_route: **exact_bucket_present_but_below_minimum**
- floor_cross_legality: **floor_crossed_but_support_not_ready**

## Boundary replay
- legacy bucket rows: **12**
- replay bucket: **CAUTION|structure_quality_caution|q35**
- replay bucket rows: **12**
- generated_rows_via_boundary_only: **0**
- preexisting_rows_in_replay_bucket: **12**
- generated_row_share: **0.0**
- dominant_neighbor_bucket: **CAUTION|structure_quality_caution|q35** rows=0

## feat_4h_bb_pct_b minimal counterfactual
- raw before/after: **0.8093 → 0.8093**
- structure_quality: **0.5019 → 0.5019**
- bucket_after: **CAUTION|structure_quality_caution|q35**
- entry_quality: **0.5556 → 0.5557**
- trade_floor_gap_after: **0.0057**
- allowed_layers_after: **1** (entry_quality_C_single_layer)
- counterfactual verdict: **counterfactual_crosses_floor_after_rebucket**
- counterfactual reason: feat_4h_bb_pct_b 的最小反事實不只改變 bucket，也讓 entry_quality 跨過 trade floor；下一輪可升級成 guarded experiment。

## Next
- next_action: 依 q15 root-cause / support audit 的既有 blocker 繼續治理。
- verify_next: 確認 current_live_structure_bucket_rows 是否增加到 minimum_support_rows。