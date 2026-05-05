# q15 Boundary Replay

- generated_at: **2026-05-04 23:56:23.006167**
- target_col: **simulated_pyramid_win**
- verdict: **boundary_replay_not_applicable_for_current_context**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'BLOCK|bull_q15_bias50_overextended_block|q15', 'regime_label': 'bull', 'regime_gate': 'BLOCK', 'entry_quality_label': 'D', 'calibration_window': 100, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`
- reason: q15 root-cause verdict=structure_scoring_gap_not_boundary，不是 boundary_sensitivity_candidate；boundary replay 本輪不適用，舊 boundary counterfactual 不可當 current truth。

## Current live row
- signal: **HOLD**
- regime/gate: **bull / BLOCK**
- structure bucket: **BLOCK|bull_q15_bias50_overextended_block|q15**
- structure_quality: **0.3483**
- entry_quality: **0.3486** (trade_floor_gap=-0.2014)
- support_route: **exact_bucket_missing_proxy_reference_only**
- floor_cross_legality: **math_cross_possible_but_illegal_without_exact_support**

## Boundary replay
- legacy bucket rows: **0**
- replay bucket: **BLOCK|bull_high_bias200_overheat_block|q35**
- replay bucket rows: **0**
- generated_rows_via_boundary_only: **0**
- preexisting_rows_in_replay_bucket: **0**
- generated_row_share: **None**
- generated_rows_exceed_replay_scope: **False** (excess=0)
- dominant_neighbor_bucket: **BLOCK|bull_high_bias200_overheat_block|q35** rows=100

## feat_4h_bb_pct_b minimal counterfactual
- raw before/after: **0.6476 → 0.6526**
- structure_quality: **0.3483 → 0.35**
- bucket_after: **BLOCK|bull_high_bias200_overheat_block|q35**
- entry_quality: **0.3486 → 0.349**
- trade_floor_gap_after: **-0.201**
- allowed_layers_after: **0** (regime_gate_block)
- counterfactual verdict: **counterfactual_not_evaluated**
- counterfactual reason: boundary replay 不適用於目前 RCA verdict，因此不消費舊 q15 counterfactual。

## Next
- next_action: 維持 boundary replay 為 non-applicable，直到 RCA 重新輸出 boundary_sensitivity_candidate。
- verify_next: 優先用 current-live bucket root-cause artifact 鎖定的 component 做 counterfactual，確認 current row 是否能跨到 q35，且 exact-lane 仍不會因 boundary tweak 產生虛假支持。