# q15 Boundary Replay

- generated_at: **2026-05-13 12:20:44.051389**
- target_col: **simulated_pyramid_win**
- verdict: **stale_or_non_current_context**
- artifact_context_freshness: **stale_or_non_current_context** (`['support_audit_entry_quality_label']`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q15', 'regime_label': 'chop', 'regime_gate': 'CAUTION', 'entry_quality_label': 'D', 'calibration_window': 100, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`
- reason: q15 boundary replay 的 probe / support audit / root-cause context 不一致；不得沿用舊 q15 boundary counterfactual 作為 current truth。

## Current live row
- signal: **HOLD**
- regime/gate: **chop / CAUTION**
- structure bucket: **CAUTION|base_caution_regime_or_bias|q15**
- structure_quality: **0.1712**
- entry_quality: **0.5501** (trade_floor_gap=0.0001)
- support_route: **exact_bucket_supported**
- floor_cross_legality: **legal_component_experiment_after_support_ready**

## Boundary replay
- legacy bucket rows: **95**
- replay bucket: **CAUTION|base_caution_regime_or_bias|q85**
- replay bucket rows: **0**
- generated_rows_via_boundary_only: **49**
- preexisting_rows_in_replay_bucket: **0**
- generated_row_share: **None**
- generated_rows_exceed_replay_scope: **True** (excess=49)
- dominant_neighbor_bucket: **CAUTION|base_caution_regime_or_bias|q85** rows=249

## feat_4h_bb_pct_b minimal counterfactual
- raw before/after: **0.3429 → 0.8688**
- structure_quality: **0.1712 → 0.35**
- bucket_after: **CAUTION|base_caution_regime_or_bias|q85**
- entry_quality: **0.5501 → 0.5947**
- trade_floor_gap_after: **0.0447**
- allowed_layers_after: **1** (entry_quality_C_single_layer)
- counterfactual verdict: **counterfactual_not_evaluated**
- counterfactual reason: boundary replay 不適用於目前 RCA verdict，因此不消費舊 q15 counterfactual。

## Next
- next_action: 停止消費 stale boundary replay；以最新 current-live support audit / RCA 為準。
- verify_next: 先重跑 hb_predict_probe.py、hb_q15_support_audit.py、hb_q15_bucket_root_cause.py，再判斷 boundary replay 是否適用。