# Bull 4H Collapse Pocket Ablation

- generated_at: **2026-04-30 05:02:41 UTC**
- target: `simulated_pyramid_win`
- collapse quantile: **q35**
- min collapse flags: **2 / 3**
- live context: **bear / BLOCK / C**
- live structure bucket: `BLOCK|structure_quality_block|q00`
- refresh mode: **live_context_only**

## Cohorts

- bull_all rows: **2453** / win_rate **0.5002** / recommended **`core_plus_macro_plus_4h_trend`**
- bull_collapse_q35 rows: **943** / win_rate **0.4411** / recommended **`core_plus_macro_plus_all_4h`**
- bull_exact_live_lane_proxy rows: **3** / win_rate **0.0000** / recommended **`None`**
- bull_live_exact_lane_bucket_proxy rows: **0** / win_rate **0.0000** / recommended **`None`**
- bull_supported_neighbor_buckets_proxy rows: **0** / win_rate **0.0000** / recommended **`None`**

## Bull-all ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|
| core_plus_macro_plus_4h_trend | 13 | 0.6367 | 0.2700 | 0.1908 | 0.2690 | 0.6000 |
| core_plus_macro_plus_4h_momentum | 13 | 0.6325 | 0.2792 | 0.1555 | 0.3148 | 0.4759 |
| core_plus_macro_plus_all_4h | 20 | 0.6134 | 0.2684 | 0.1802 | 0.2611 | 0.7655 |
| core_plus_macro_plus_4h_structure_shift | 13 | 0.6014 | 0.2848 | 0.1343 | 0.3029 | 0.5724 |
| current_full | 131 | 0.5929 | 0.2345 | 0.2226 | 0.2832 | 0.7655 |
| current_full_minus_4h_structure_shift | 128 | 0.5739 | 0.2322 | 0.1873 | 0.3003 | 0.7793 |
| current_full_minus_4h | 121 | 0.5696 | 0.2289 | 0.1908 | 0.3096 | 0.7793 |
| core_plus_macro | 10 | 0.5406 | 0.3019 | 0.1519 | 0.3344 | 0.6621 |

## Bull collapse-pocket ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|
| core_plus_macro_plus_all_4h | 20 | 0.8586 | 0.0404 | 0.8182 | 0.1463 | 0.9500 |
| current_full_minus_4h_structure_shift | 128 | 0.7576 | 0.2020 | 0.5556 | 0.1587 | 0.9500 |
| core_plus_macro_plus_4h_structure_shift | 13 | 0.7424 | 0.1566 | 0.5859 | 0.1446 | 1.0000 |
| current_full | 131 | 0.7273 | 0.1717 | 0.5556 | 0.1646 | 0.8500 |
| current_full_minus_4h | 121 | 0.7273 | 0.1717 | 0.5556 | 0.1806 | 0.9500 |
| core_plus_macro_plus_4h_momentum | 13 | 0.6566 | 0.3434 | 0.3131 | 0.1743 | 0.8500 |
| core_plus_macro_plus_4h_trend | 13 | 0.4293 | 0.1263 | 0.3030 | 0.3119 | 0.5000 |
| core_plus_macro | 10 | 0.4040 | 0.1414 | 0.2626 | 0.3184 | 0.8000 |

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
- exact-lane proxy gap to minimum: **47**
- dominant neighbor bucket: `None` rows=0
- bucket gap vs dominant neighbor: **0**
- exact bucket root cause: **same_lane_exists_but_q65_missing**
- broader q65 rows / dominant regime: **0 / None (0.0000)**
- root cause interpretation: 目前支持資訊不足，需補更多 same-lane / broader-scope 證據。
- bucket comparison takeaway: **support_gap_unresolved**
- proxy boundary verdict: **insufficient_recent_exact_bucket_rows**
- proxy boundary reason: current live structure bucket 沒有 recent exact rows，無法判斷 proxy cohort 邊界。
- decision-quality scope / label: **global / D**
- narrowed pathology scope: **None**
- worst pathology scope: **None**
- shared pathology shift features: []
- broader-bucket pathology shifts: []
- recommended_action: support 全面不足；下一輪需優先擴充樣本或縮小治理範圍。

## Bucket evidence comparison

| cohort | bucket | rows | win_rate | quality / cv | note |
|---|---|---:|---:|---:|---|
| exact live lane | None | 0 | None | None | current bucket rows=0 |
| exact bucket proxy | BLOCK|structure_quality_block|q00 | 0 | 0.0 | None | proxy-vs-broader win Δ=None |
| broader same bucket | BLOCK|structure_quality_block|q00 | 0 | None | None | dominant_regime=None |

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
- thresholds (bull q35): {"feat_4h_dist_swing_low": 4.9263, "feat_4h_dist_bb_lower": 4.2535, "feat_4h_bb_pct_b": 0.7067}
- exact live structure bucket: `BLOCK|structure_quality_block|q00` rows=0
- supported neighbor buckets from exact scope: []
- best bull-all profile: **core_plus_macro_plus_4h_trend**
- best bull-collapse profile: **core_plus_macro_plus_all_4h**
- best live-bucket proxy profile: **None**
- If live-bucket proxy stays tiny and unstable while supported-neighbor buckets remain healthier, the next fix should become a support-aware deployment blocker / fallback policy rather than a broader feature expansion.
