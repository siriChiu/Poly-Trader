# q15 Boundary Replay

- generated_at: **2026-05-21 06:19:05.124886**
- target_col: **simulated_pyramid_win**
- verdict: **boundary_replay_has_no_supported_target_bucket**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q15', 'regime_label': 'chop', 'regime_gate': 'CAUTION', 'entry_quality_label': 'C', 'calibration_window': 200, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`
- reason: 就算把 q15↔q35 邊界向下回放，chosen scope 仍找不到可承接的 current bucket rows；boundary review 無法形成可部署支持。

## Current live row
- signal: **HOLD**
- regime/gate: **chop / CAUTION**
- structure bucket: **CAUTION|base_caution_regime_or_bias|q15**
- structure_quality: **0.3288**
- entry_quality: **0.5825** (trade_floor_gap=0.0325)
- support_route: **insufficient_support_everywhere**
- floor_cross_legality: **floor_crossed_but_support_not_ready**

## Boundary replay
- legacy bucket rows: **0**
- replay bucket: **CAUTION|base_caution_regime_or_bias|q65**
- replay bucket rows: **0**
- generated_rows_via_boundary_only: **2**
- preexisting_rows_in_replay_bucket: **0**
- generated_row_share: **None**
- generated_rows_exceed_replay_scope: **True** (excess=2)
- dominant_neighbor_bucket: **CAUTION|base_caution_regime_or_bias|q65** rows=67

## feat_4h_bb_pct_b minimal counterfactual
- raw before/after: **0.582 → 0.6444**
- structure_quality: **0.3288 → 0.35**
- bucket_after: **CAUTION|base_caution_regime_or_bias|q65**
- entry_quality: **0.5825 → 0.5878**
- trade_floor_gap_after: **0.0378**
- allowed_layers_after: **1** (entry_quality_C_single_layer)
- counterfactual verdict: **counterfactual_crosses_floor_after_rebucket**
- counterfactual reason: feat_4h_bb_pct_b 的最小反事實不只改變 bucket，也讓 entry_quality 跨過 trade floor；下一輪可升級成 guarded experiment。

## Next
- next_action: 停止把 boundary review 當主假設，回到 structure component 與 support accumulation。
- verify_next: 改查 structure component scoring / support accumulation，不再延長 boundary review。