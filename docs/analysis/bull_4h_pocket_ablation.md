# Bull 4H Collapse Pocket Ablation

- generated_at: **2026-04-18 15:32:19 UTC**
- target: `simulated_pyramid_win`
- collapse quantile: **q35**
- min collapse flags: **2 / 3**
- live context: **bull / None / None**
- live structure bucket: `None`

## Cohorts

- bull_all rows: **1225** / win_rate **0.7159** / recommended **`core_plus_macro_plus_all_4h`**
- bull_collapse_q35 rows: **425** / win_rate **0.7082** / recommended **`core_plus_macro`**
- bull_exact_live_lane_proxy rows: **0** / win_rate **0.0000** / recommended **`None`**
- bull_live_exact_lane_bucket_proxy rows: **0** / win_rate **0.0000** / recommended **`None`**
- bull_supported_neighbor_buckets_proxy rows: **0** / win_rate **0.0000** / recommended **`None`**

## Bull-all ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|
| core_plus_macro_plus_all_4h | 20 | 0.7216 | 0.1944 | 0.4608 | 0.1923 | 1.0000 |
| core_plus_macro_plus_4h_structure_shift | 13 | 0.6569 | 0.1560 | 0.4363 | 0.2252 | 0.8000 |
| core_plus_macro_plus_4h_trend | 13 | 0.6402 | 0.2396 | 0.4020 | 0.1967 | 1.0000 |
| core_plus_macro_plus_4h_momentum | 13 | 0.6402 | 0.2396 | 0.4020 | 0.2207 | 0.9429 |
| core_plus_macro | 10 | 0.6225 | 0.2590 | 0.3137 | 0.2418 | 0.9524 |
| current_full | 131 | 0.5412 | 0.3110 | 0.0049 | 0.2791 | 0.9333 |
| current_full_minus_4h_structure_shift | 128 | 0.5373 | 0.3107 | 0.0049 | 0.2881 | 1.0000 |
| current_full_minus_4h | 121 | 0.5353 | 0.3124 | 0.0049 | 0.2987 | 0.9619 |

## Bull collapse-pocket ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|
| core_plus_macro | 10 | 0.2143 | 0.0429 | 0.1714 | 0.3909 | 0.5000 |
| core_plus_macro_plus_4h_structure_shift | 13 | 0.2143 | 0.0429 | 0.1714 | 0.3909 | 0.5000 |
| core_plus_macro_plus_4h_trend | 13 | 0.2143 | 0.0429 | 0.1714 | 0.3909 | 0.5000 |
| core_plus_macro_plus_4h_momentum | 13 | 0.2143 | 0.0429 | 0.1714 | 0.3909 | 0.5000 |
| core_plus_macro_plus_all_4h | 20 | 0.2143 | 0.0429 | 0.1714 | 0.3909 | 0.5000 |
| current_full_minus_4h_structure_shift | 128 | 0.2143 | 0.0429 | 0.1714 | 0.3909 | 0.5000 |
| current_full_minus_4h | 121 | 0.2143 | 0.0429 | 0.1714 | 0.3909 | 0.5000 |
| current_full | 131 | 0.2143 | 0.0429 | 0.1714 | 0.3909 | 0.5000 |

## Live-bucket proxy ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|

## Supported-neighbor bucket proxy ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|

## Support / pathology summary

- blocker_state: **insufficient_support_everywhere**
- preferred_support_cohort: **None**
- current bucket gap to minimum: **50**
- exact-bucket proxy gap to minimum: **50**
- exact-lane proxy gap to minimum: **50**
- dominant neighbor bucket: `None` rows=0
- bucket gap vs dominant neighbor: **0**
- exact bucket root cause: **insufficient_scope_data**
- broader q65 rows / dominant regime: **0 / None (0.0000)**
- root cause interpretation: 目前支持資訊不足，需補更多 same-lane / broader-scope 證據。
- bucket comparison takeaway: **support_gap_unresolved**
- proxy boundary verdict: **insufficient_recent_exact_bucket_rows**
- proxy boundary reason: current live structure bucket 沒有 recent exact rows，無法判斷 proxy cohort 邊界。
- decision-quality scope / label: **None / None**
- narrowed pathology scope: **None**
- worst pathology scope: **None**
- shared pathology shift features: []
- broader-bucket pathology shifts: []
- recommended_action: support 全面不足；下一輪需優先擴充樣本或縮小治理範圍。

## Bucket evidence comparison

| cohort | bucket | rows | win_rate | quality / cv | note |
|---|---|---:|---:|---:|---|
| exact live lane | None | 0 | None | None | current bucket rows=0 |
| exact bucket proxy | None | 0 | 0.0 | None | proxy-vs-broader win Δ=None |
| broader same bucket | None | 0 | None | None | dominant_regime=None |

## Proxy boundary diagnostics

- recent exact current bucket rows / win_rate: **0 / None**
- recent exact live lane rows / win_rate: **0 / None**
- historical exact-bucket proxy rows / win_rate: **0 / None**
- recent broader same-bucket rows / dominant regime: **0 / None**
- proxy vs current bucket win Δ / row ratio: **None / None**
- exact lane vs current bucket win Δ / quality Δ: **None / None**
- broader same-bucket vs current bucket win Δ / quality Δ: **None / None**

## Exact lane sub-bucket diagnostics

- verdict: **no_exact_lane_sub_bucket_split**
- reason: exact live lane 沒有可比較的非 current bucket 子 bucket。
- toxic bucket: **None**
- toxic bucket rows / win_rate / avg_quality: **None / None / None**
- toxic bucket vs current win Δ / quality Δ: **None / None**

## Notes

- collapse features under inspection: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- thresholds (bull q35): {"feat_4h_dist_swing_low": 2.0689, "feat_4h_dist_bb_lower": 1.5434, "feat_4h_bb_pct_b": 0.4615}
- exact live structure bucket: `None` rows=None
- supported neighbor buckets from exact scope: []
- best bull-all profile: **core_plus_macro_plus_all_4h**
- best bull-collapse profile: **core_plus_macro**
- best live-bucket proxy profile: **None**
- If live-bucket proxy stays tiny and unstable while supported-neighbor buckets remain healthier, the next fix should become a support-aware deployment blocker / fallback policy rather than a broader feature expansion.
