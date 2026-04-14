# Bull 4H Collapse Pocket Ablation

- generated_at: **2026-04-14 15:00:14 UTC**
- target: `simulated_pyramid_win`
- collapse quantile: **q35**
- min collapse flags: **2 / 3**
- live context: **bull / ALLOW / D**
- live structure bucket: `ALLOW|base_allow|q65`

## Cohorts

- bull_all rows: **697** / win_rate **0.6743** / recommended **`core_plus_macro_plus_all_4h`**
- bull_collapse_q35 rows: **252** / win_rate **0.5040** / recommended **`core_plus_macro`**
- bull_exact_live_lane_proxy rows: **50** / win_rate **0.6400** / recommended **`core_plus_macro`**
- bull_live_exact_lane_bucket_proxy rows: **38** / win_rate **0.8421** / recommended **`core_plus_macro`**
- bull_supported_neighbor_buckets_proxy rows: **12** / win_rate **0.0000** / recommended **`None`**

## Bull-all ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|
| core_plus_macro_plus_all_4h | 20 | 0.6414 | 0.3004 | 0.0431 | 0.2190 | 0.7500 |
| core_plus_macro_plus_4h_trend | 13 | 0.6414 | 0.3004 | 0.0431 | 0.2240 | 0.6333 |
| current_full_minus_4h_structure_shift | 128 | 0.6414 | 0.3004 | 0.0431 | 0.2255 | 0.6667 |
| current_full | 131 | 0.6414 | 0.3004 | 0.0431 | 0.2265 | 0.6333 |
| current_full_minus_4h | 121 | 0.6414 | 0.3004 | 0.0431 | 0.2296 | 0.6667 |
| core_plus_macro_plus_4h_structure_shift | 13 | 0.6414 | 0.3004 | 0.0431 | 0.2423 | 0.7500 |
| core_plus_macro | 10 | 0.6414 | 0.3004 | 0.0431 | 0.2429 | 0.6333 |
| core_plus_macro_plus_4h_momentum | 13 | 0.6414 | 0.3004 | 0.0431 | 0.2469 | 0.6333 |

## Bull collapse-pocket ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|
| core_plus_macro | 10 | 0.7143 | 0.0778 | 0.6190 | 0.2184 | 0.6667 |
| core_plus_macro_plus_4h_structure_shift | 13 | 0.7143 | 0.0778 | 0.6190 | 0.2184 | 0.6667 |
| core_plus_macro_plus_4h_trend | 13 | 0.7143 | 0.0778 | 0.6190 | 0.2184 | 0.6667 |
| core_plus_macro_plus_4h_momentum | 13 | 0.7143 | 0.0778 | 0.6190 | 0.2184 | 0.6667 |
| core_plus_macro_plus_all_4h | 20 | 0.7143 | 0.0778 | 0.6190 | 0.2184 | 0.6667 |
| current_full_minus_4h_structure_shift | 128 | 0.7143 | 0.0778 | 0.6190 | 0.2184 | 0.6667 |
| current_full_minus_4h | 121 | 0.7143 | 0.0778 | 0.6190 | 0.2184 | 0.6667 |
| current_full | 131 | 0.7143 | 0.0778 | 0.6190 | 0.2184 | 0.6667 |

## Live-bucket proxy ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|
| core_plus_macro | 10 | 0.8333 | 0.0000 | 0.8333 | 0.1391 | 1.0000 |
| core_plus_macro_plus_4h_structure_shift | 13 | 0.8333 | 0.0000 | 0.8333 | 0.1391 | 1.0000 |
| core_plus_macro_plus_4h_trend | 13 | 0.8333 | 0.0000 | 0.8333 | 0.1391 | 1.0000 |
| core_plus_macro_plus_4h_momentum | 13 | 0.8333 | 0.0000 | 0.8333 | 0.1391 | 1.0000 |
| core_plus_macro_plus_all_4h | 20 | 0.8333 | 0.0000 | 0.8333 | 0.1391 | 1.0000 |
| current_full_minus_4h_structure_shift | 128 | 0.8333 | 0.0000 | 0.8333 | 0.1391 | 1.0000 |
| current_full_minus_4h | 121 | 0.8333 | 0.0000 | 0.8333 | 0.1391 | 1.0000 |
| current_full | 131 | 0.8333 | 0.0000 | 0.8333 | 0.1391 | 1.0000 |

## Supported-neighbor bucket proxy ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|

## Support / pathology summary

- blocker_state: **exact_lane_proxy_fallback_only**
- preferred_support_cohort: **bull_exact_live_lane_proxy**
- current bucket gap to minimum: **50**
- exact-bucket proxy gap to minimum: **12**
- exact-lane proxy gap to minimum: **0**
- dominant neighbor bucket: `ALLOW|base_allow|q85` rows=14
- bucket gap vs dominant neighbor: **14**
- decision-quality scope / label: **regime_label / D**
- narrowed pathology scope: **None**
- worst pathology scope: **regime_label+entry_quality_label**
- shared pathology shift features: ["feat_4h_dist_swing_low", "feat_4h_dist_bb_lower", "feat_4h_bb_pct_b"]
- recommended_action: 維持 0 layers；優先查 exact bucket 缺口與 same-bucket pathology，而不是再重訓。

## Notes

- collapse features under inspection: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- thresholds (bull q35): {"feat_4h_dist_swing_low": 1.7669, "feat_4h_dist_bb_lower": 0.4331, "feat_4h_bb_pct_b": 0.1274}
- exact live structure bucket: `ALLOW|base_allow|q65` rows=0
- supported neighbor buckets from exact scope: ["ALLOW|base_allow|q85"]
- best bull-all profile: **core_plus_macro_plus_all_4h**
- best bull-collapse profile: **core_plus_macro**
- best live-bucket proxy profile: **core_plus_macro**
- If live-bucket proxy stays tiny and unstable while supported-neighbor buckets remain healthier, the next fix should become a support-aware deployment blocker / fallback policy rather than a broader feature expansion.
