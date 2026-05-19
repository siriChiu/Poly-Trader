# q15 Boundary Replay

- generated_at: **2026-05-19 16:03:31.310518**
- target_col: **simulated_pyramid_win**
- verdict: **boundary_replay_not_applicable_for_current_context**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q15', 'regime_label': 'bear', 'regime_gate': 'CAUTION', 'entry_quality_label': 'C', 'calibration_window': 200, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`
- reason: q15 root-cause verdict=current_exact_support_under_minimum，不是 boundary_sensitivity_candidate；boundary replay 本輪不適用，舊 boundary counterfactual 不可當 current truth。

## Current live row
- signal: **HOLD**
- regime/gate: **bear / CAUTION**
- structure bucket: **CAUTION|base_caution_regime_or_bias|q15**
- structure_quality: **0.197**
- entry_quality: **0.6187** (trade_floor_gap=0.0687)
- support_route: **exact_bucket_present_but_below_minimum**
- floor_cross_legality: **floor_crossed_but_support_not_ready**

## Boundary replay
- legacy bucket rows: **2**
- replay bucket: **CAUTION|structure_quality_caution|q15**
- replay bucket rows: **68**
- generated_rows_via_boundary_only: **75**
- preexisting_rows_in_replay_bucket: **0**
- generated_row_share: **1.0**
- generated_rows_exceed_replay_scope: **True** (excess=7)
- dominant_neighbor_bucket: **CAUTION|structure_quality_caution|q15** rows=109

## feat_4h_bb_pct_b minimal counterfactual
- raw before/after: **0.3919 → None**
- structure_quality: **0.197 → 0.35**
- bucket_after: **CAUTION|structure_quality_caution|q15**
- entry_quality: **0.6187 → 0.657**
- trade_floor_gap_after: **0.107**
- allowed_layers_after: **1** (entry_quality_C_single_layer)
- counterfactual verdict: **counterfactual_not_evaluated**
- counterfactual reason: boundary replay 不適用於目前 RCA verdict，因此不消費舊 q15 counterfactual。

## Next
- next_action: 維持 boundary replay 為 non-applicable，直到 RCA 重新輸出 boundary_sensitivity_candidate。
- verify_next: 維持 minimum_support_rows=50 與 current-live guardrail，累積同 support_identity 的 exact rows；若只有 legacy / different semantic signature 支撐，文案必須標成 semantic rebaseline reference。