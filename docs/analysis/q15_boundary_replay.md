# q15 Boundary Replay

- generated_at: **2026-04-24 13:12:04.596144**
- target_col: **simulated_pyramid_win**
- verdict: **boundary_replay_not_applicable_for_current_context**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'BLOCK|bull_high_bias200_overheat_block|q35', 'regime_label': 'bull', 'regime_gate': 'BLOCK', 'entry_quality_label': 'D', 'calibration_window': 600, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`
- reason: q15 root-cause verdict=current_row_already_above_q35_boundary，不是 boundary_sensitivity_candidate；boundary replay 本輪不適用，舊 boundary counterfactual 不可當 current truth。

## Current live row
- signal: **HOLD**
- regime/gate: **bull / BLOCK**
- structure bucket: **BLOCK|bull_high_bias200_overheat_block|q35**
- structure_quality: **0.3637**
- entry_quality: **0.3113** (trade_floor_gap=-0.2387)
- support_route: **exact_bucket_present_but_below_minimum**
- floor_cross_legality: **math_cross_possible_but_illegal_without_exact_support**

## Boundary replay
- legacy bucket rows: **5**
- replay bucket: **BLOCK|bull_high_bias200_overheat_block|q65**
- replay bucket rows: **0**
- generated_rows_via_boundary_only: **0**
- preexisting_rows_in_replay_bucket: **0**
- generated_row_share: **None**
- generated_rows_exceed_replay_scope: **False** (excess=0)
- dominant_neighbor_bucket: **BLOCK|bull_high_bias200_overheat_block|q65** rows=82

## feat_4h_bb_pct_b minimal counterfactual
- raw before/after: **0.6514 → 0.6514**
- structure_quality: **0.3637 → 0.3637**
- bucket_after: **BLOCK|bull_high_bias200_overheat_block|q65**
- entry_quality: **0.3113 → 0.3114**
- trade_floor_gap_after: **-0.2386**
- allowed_layers_after: **0** (regime_gate_block)
- counterfactual verdict: **counterfactual_not_evaluated**
- counterfactual reason: boundary replay 不適用於目前 RCA verdict，因此不消費舊 q15 counterfactual。

## Next
- next_action: 維持 boundary replay 為 non-applicable，直到 RCA 重新輸出 boundary_sensitivity_candidate。
- verify_next: 確認 current_live_structure_bucket_rows 是否增加到 minimum_support_rows。