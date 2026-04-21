# q15 Boundary Replay

- generated_at: **2026-04-21 04:23:23.782550**
- target_col: **simulated_pyramid_win**
- verdict: **boundary_replay_has_no_supported_target_bucket**
- reason: 就算把 q15↔q35 邊界向下回放，chosen scope 仍找不到可承接的 current bucket rows；boundary review 無法形成可部署支持。

## Current live row
- signal: **HOLD**
- regime/gate: **chop / CAUTION**
- structure bucket: **CAUTION|base_caution_regime_or_bias|q15**
- structure_quality: **0.32**
- entry_quality: **0.4331** (trade_floor_gap=-0.1169)
- support_route: **exact_bucket_supported**
- floor_cross_legality: **legal_component_experiment_after_support_ready**

## Boundary replay
- legacy bucket rows: **97**
- replay bucket: **CAUTION|base_caution_regime_or_bias|q35**
- replay bucket rows: **0**
- generated_rows_via_boundary_only: **12**
- preexisting_rows_in_replay_bucket: **0**
- generated_row_share: **None**
- dominant_neighbor_bucket: **CAUTION|base_caution_regime_or_bias|q35** rows=1117

## feat_4h_bb_pct_b minimal counterfactual
- raw before/after: **0.5073 → 0.5955**
- structure_quality: **0.32 → 0.35**
- bucket_after: **CAUTION|base_caution_regime_or_bias|q35**
- entry_quality: **0.4331 → 0.4406**
- trade_floor_gap_after: **-0.1094**
- allowed_layers_after: **0** (entry_quality_below_trade_floor)
- counterfactual verdict: **bucket_proxy_only_not_trade_floor_fix**
- counterfactual reason: 只把 feat_4h_bb_pct_b 補到剛好跨 q35，只會把結構 bucket 從 q15 改成 q35；entry_quality 仍低於 trade floor，allowed_layers 仍是 0，表示它更像 bucket proxy，而不是 deployable floor fix。

## Next
- next_action: 停止把 boundary review 當主假設，回到 structure component 與 support accumulation。
- verify_next: 改查 structure component scoring / support accumulation，不再延長 boundary review。