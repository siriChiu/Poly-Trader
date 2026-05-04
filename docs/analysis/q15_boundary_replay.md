# q15 Boundary Replay

- generated_at: **2026-05-04 13:26:55.013445**
- target_col: **simulated_pyramid_win**
- verdict: **boundary_replay_not_applicable_for_current_context**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|structure_quality_caution|q15', 'regime_label': 'bull', 'regime_gate': 'CAUTION', 'entry_quality_label': 'D', 'calibration_window': 100, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`
- reason: q15 root-cause verdict=same_lane_neighbor_bucket_dominates，不是 boundary_sensitivity_candidate；boundary replay 本輪不適用，舊 boundary counterfactual 不可當 current truth。

## Current live row
- signal: **HOLD**
- regime/gate: **bull / CAUTION**
- structure bucket: **CAUTION|structure_quality_caution|q15**
- structure_quality: **0.2117**
- entry_quality: **0.3502** (trade_floor_gap=-0.1998)
- support_route: **exact_bucket_missing_proxy_reference_only**
- floor_cross_legality: **math_cross_possible_but_illegal_without_exact_support**

## Boundary replay
- legacy bucket rows: **0**
- replay bucket: **CAUTION|structure_quality_caution|q35**
- replay bucket rows: **3**
- generated_rows_via_boundary_only: **128**
- preexisting_rows_in_replay_bucket: **0**
- generated_row_share: **1.0**
- generated_rows_exceed_replay_scope: **True** (excess=125)
- dominant_neighbor_bucket: **CAUTION|structure_quality_caution|q35** rows=687

## feat_4h_bb_pct_b minimal counterfactual
- raw before/after: **0.4082 → 0.815**
- structure_quality: **0.2117 → 0.35**
- bucket_after: **CAUTION|structure_quality_caution|q35**
- entry_quality: **0.3502 → 0.3847**
- trade_floor_gap_after: **-0.1653**
- allowed_layers_after: **0** (entry_quality_below_trade_floor)
- counterfactual verdict: **counterfactual_not_evaluated**
- counterfactual reason: boundary replay 不適用於目前 RCA verdict，因此不消費舊 q15 counterfactual。

## Next
- next_action: 維持 boundary replay 為 non-applicable，直到 RCA 重新輸出 boundary_sensitivity_candidate。
- verify_next: 比較 current row 與 dominant neighbor bucket 的 4H component 差值，再做最小 counterfactual。