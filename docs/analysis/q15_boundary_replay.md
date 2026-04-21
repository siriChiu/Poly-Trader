# q15 Boundary Replay

- generated_at: **2026-04-21 02:57:58.353169**
- target_col: **simulated_pyramid_win**
- verdict: **boundary_replay_not_applicable**
- reason: 目前 q15 root-cause verdict 不是 boundary_sensitivity_candidate，boundary replay 不是本輪主路徑。

## Current live row
- signal: **HOLD**
- regime/gate: **chop / CAUTION**
- structure bucket: **CAUTION|base_caution_regime_or_bias|q15**
- structure_quality: **0.336**
- entry_quality: **0.5183** (trade_floor_gap=-0.0317)
- support_route: **exact_bucket_supported**
- floor_cross_legality: **legal_component_experiment_after_support_ready**

## Boundary replay
- legacy bucket rows: **88**
- replay bucket: **CAUTION|base_caution_regime_or_bias|q35**
- replay bucket rows: **0**
- generated_rows_via_boundary_only: **0**
- preexisting_rows_in_replay_bucket: **0**
- generated_row_share: **None**
- dominant_neighbor_bucket: **CAUTION|base_caution_regime_or_bias|q35** rows=1117

## feat_4h_bb_pct_b minimal counterfactual
- raw before/after: **0.5411 → 0.5823**
- structure_quality: **0.336 → 0.35**
- bucket_after: **CAUTION|base_caution_regime_or_bias|q35**
- entry_quality: **0.5183 → 0.5217**
- trade_floor_gap_after: **-0.0283**
- allowed_layers_after: **0** (entry_quality_below_trade_floor)
- counterfactual verdict: **bucket_proxy_only_not_trade_floor_fix**
- counterfactual reason: 只把 feat_4h_bb_pct_b 補到剛好跨 q35，只會把結構 bucket 從 q15 改成 q35；entry_quality 仍低於 trade floor，allowed_layers 仍是 0，表示它更像 bucket proxy，而不是 deployable floor fix。

## Next
- next_action: 依 q15 root-cause / support audit 的既有 blocker 繼續治理。
- verify_next: 優先用 q15 root-cause artifact 鎖定的 component 做 counterfactual，確認 current row 是否能跨到 q35，且 exact-lane 仍不會因 boundary tweak 產生虛假支持。