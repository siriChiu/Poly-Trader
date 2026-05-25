# q15 Boundary Replay

- generated_at: **2026-05-25 16:19:19.978544**
- target_col: **simulated_pyramid_win**
- verdict: **boundary_replay_has_no_supported_target_bucket**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q15', 'regime_label': 'chop', 'regime_gate': 'CAUTION', 'entry_quality_label': 'D', 'calibration_window': 200, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`
- reason: 就算把 q15↔q35 邊界向下回放，chosen scope 仍找不到可承接的 current bucket rows；boundary review 無法形成可部署支持。

## Current live row
- signal: **HOLD**
- regime/gate: **chop / CAUTION**
- structure bucket: **CAUTION|base_caution_regime_or_bias|q15**
- structure_quality: **0.3355**
- entry_quality: **0.4397** (trade_floor_gap=-0.1103)
- support_route: **exact_bucket_missing_exact_lane_proxy_only**
- floor_cross_legality: **math_cross_possible_but_illegal_without_exact_support**

## Boundary replay
- legacy bucket rows: **0**
- replay bucket: **CAUTION|base_caution_regime_or_bias|q00**
- replay bucket rows: **0**
- generated_rows_via_boundary_only: **25**
- preexisting_rows_in_replay_bucket: **0**
- generated_row_share: **None**
- generated_rows_exceed_replay_scope: **True** (excess=25)
- dominant_neighbor_bucket: **CAUTION|base_caution_regime_or_bias|q00** rows=370

## feat_4h_bb_pct_b minimal counterfactual
- raw before/after: **0.6485 → 0.6911**
- structure_quality: **0.3355 → 0.35**
- bucket_after: **CAUTION|base_caution_regime_or_bias|q00**
- entry_quality: **0.4397 → 0.4434**
- trade_floor_gap_after: **-0.1066**
- allowed_layers_after: **0** (entry_quality_below_trade_floor)
- counterfactual verdict: **bucket_proxy_only_not_trade_floor_fix**
- counterfactual reason: 只把 feat_4h_bb_pct_b 補到剛好跨 q35，只會把結構 bucket 從 q15 改成 q35；entry_quality 仍低於 trade floor，allowed_layers 仍是 0，表示它更像 bucket proxy，而不是 deployable floor fix。

## Next
- next_action: 停止把 boundary review 當主假設，回到 structure component 與 support accumulation。
- verify_next: 改查 structure component scoring / support accumulation，不再延長 boundary review。