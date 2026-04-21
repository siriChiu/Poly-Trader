# q15 Boundary Replay

- generated_at: **2026-04-21 18:06:23.922268**
- target_col: **simulated_pyramid_win**
- verdict: **same_lane_counterfactual_bucket_proxy_only**
- reason: 目前不是 boundary 問題，而是 same-lane q35 鄰近 bucket 已足夠明確；最小 feat_4h_bb_pct_b 反事實只會把 current row 重新分桶到 q35，但 entry_quality 仍過不了 trade floor，因此它只能當 bucket proxy 證據，不能視為 deployable 修補。

## Current live row
- signal: **HOLD**
- regime/gate: **bull / CAUTION**
- structure bucket: **CAUTION|structure_quality_caution|q15**
- structure_quality: **0.265**
- entry_quality: **0.4752** (trade_floor_gap=-0.0748)
- support_route: **exact_bucket_missing_proxy_reference_only**
- floor_cross_legality: **math_cross_possible_but_illegal_without_exact_support**

## Boundary replay
- legacy bucket rows: **0**
- replay bucket: **CAUTION|structure_quality_caution|q35**
- replay bucket rows: **25**
- generated_rows_via_boundary_only: **136**
- preexisting_rows_in_replay_bucket: **0**
- generated_row_share: **5.44**
- dominant_neighbor_bucket: **CAUTION|structure_quality_caution|q35** rows=674

## feat_4h_bb_pct_b minimal counterfactual
- raw before/after: **0.3883 → 0.6383**
- structure_quality: **0.265 → 0.35**
- bucket_after: **CAUTION|structure_quality_caution|q35**
- entry_quality: **0.4752 → 0.4965**
- trade_floor_gap_after: **-0.0535**
- allowed_layers_after: **0** (entry_quality_below_trade_floor)
- counterfactual verdict: **bucket_proxy_only_not_trade_floor_fix**
- counterfactual reason: 只把 feat_4h_bb_pct_b 補到剛好跨 q35，只會把結構 bucket 從 q15 改成 q35；entry_quality 仍低於 trade floor，allowed_layers 仍是 0，表示它更像 bucket proxy，而不是 deployable floor fix。

## Next
- next_action: 停止把 q15 問題包裝成 boundary review；維持 feat_4h_bb_pct_b 為 structure proxy 診斷，主修補焦點轉到 bias50 / exact-support accumulation。
- verify_next: 保留 feat_4h_bb_pct_b counterfactual 作為 bucket-proxy 證據；下一輪改直接檢查 feat_4h_bias50 / base stack 或 support accumulation 是否才是 floor-gap 主因。