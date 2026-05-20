# q15 Boundary Replay

- generated_at: **2026-05-20 15:09:05.149234**
- target_col: **simulated_pyramid_win**
- verdict: **boundary_replay_not_applicable_for_current_context**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q15', 'regime_label': 'chop', 'regime_gate': 'CAUTION', 'entry_quality_label': 'C', 'calibration_window': 200, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`
- reason: q15 root-cause verdict=structure_scoring_gap_not_boundary，不是 boundary_sensitivity_candidate；boundary replay 本輪不適用，舊 boundary counterfactual 不可當 current truth。

## Current live row
- signal: **HOLD**
- regime/gate: **chop / CAUTION**
- structure bucket: **CAUTION|base_caution_regime_or_bias|q15**
- structure_quality: **0.3488**
- entry_quality: **0.6703** (trade_floor_gap=0.1203)
- support_route: **insufficient_support_everywhere**
- floor_cross_legality: **floor_crossed_but_support_not_ready**

## Boundary replay
- legacy bucket rows: **0**
- replay bucket: **CAUTION|base_caution_regime_or_bias|q65**
- replay bucket rows: **0**
- generated_rows_via_boundary_only: **0**
- preexisting_rows_in_replay_bucket: **0**
- generated_row_share: **None**
- generated_rows_exceed_replay_scope: **False** (excess=0)
- dominant_neighbor_bucket: **CAUTION|base_caution_regime_or_bias|q65** rows=67

## feat_4h_bb_pct_b minimal counterfactual
- raw before/after: **0.6612 → 0.6647**
- structure_quality: **0.3488 → 0.35**
- bucket_after: **CAUTION|base_caution_regime_or_bias|q65**
- entry_quality: **0.6703 → 0.6705**
- trade_floor_gap_after: **0.1205**
- allowed_layers_after: **1** (entry_quality_C_single_layer)
- counterfactual verdict: **counterfactual_not_evaluated**
- counterfactual reason: boundary replay 不適用於目前 RCA verdict，因此不消費舊 q15 counterfactual。

## Next
- next_action: 維持 boundary replay 為 non-applicable，直到 RCA 重新輸出 boundary_sensitivity_candidate。
- verify_next: 優先用 current-live bucket root-cause artifact 鎖定的 component 做 counterfactual，確認 current row 是否能跨到 q35，且 exact-lane 仍不會因 boundary tweak 產生虛假支持。