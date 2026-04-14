# Bull 4H Collapse Pocket Ablation

- generated_at: **2026-04-14 19:39:13 UTC**
- target: `simulated_pyramid_win`
- collapse quantile: **q35**
- min collapse flags: **2 / 3**
- live context: **bull / CAUTION / D**
- live structure bucket: `CAUTION|structure_quality_caution|q35`

## Cohorts

- bull_all rows: **759** / win_rate **0.7062** / recommended **`core_plus_macro_plus_4h_structure_shift`**
- bull_collapse_q35 rows: **259** / win_rate **0.4710** / recommended **`core_plus_macro`**
- bull_exact_live_lane_proxy rows: **392** / win_rate **0.8367** / recommended **`core_plus_macro`**
- bull_live_exact_lane_bucket_proxy rows: **129** / win_rate **0.9767** / recommended **`None`**
- bull_supported_neighbor_buckets_proxy rows: **84** / win_rate **0.6905** / recommended **`core_plus_macro`**

## Bull-all ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|
| core_plus_macro_plus_4h_structure_shift | 13 | 0.6222 | 0.2340 | 0.3333 | 0.2127 | 0.5077 |
| core_plus_macro | 10 | 0.6222 | 0.2340 | 0.3333 | 0.2347 | 0.5385 |
| core_plus_macro_plus_all_4h | 20 | 0.6190 | 0.2380 | 0.3175 | 0.2279 | 0.5692 |
| core_plus_macro_plus_4h_momentum | 13 | 0.6190 | 0.2380 | 0.3175 | 0.2453 | 0.5692 |
| current_full | 131 | 0.6190 | 0.2380 | 0.3175 | 0.2491 | 0.5538 |
| core_plus_macro_plus_4h_trend | 13 | 0.6190 | 0.2380 | 0.3175 | 0.2560 | 0.5385 |
| current_full_minus_4h | 121 | 0.6190 | 0.2380 | 0.3175 | 0.2606 | 0.6308 |
| current_full_minus_4h_structure_shift | 128 | 0.6190 | 0.2380 | 0.3175 | 0.2615 | 0.6154 |

## Bull collapse-pocket ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|
| core_plus_macro | 10 | 0.6279 | 0.1655 | 0.3953 | 0.2789 | 0.6667 |
| core_plus_macro_plus_4h_structure_shift | 13 | 0.6279 | 0.1655 | 0.3953 | 0.2789 | 0.6667 |
| core_plus_macro_plus_4h_trend | 13 | 0.6279 | 0.1655 | 0.3953 | 0.2789 | 0.6667 |
| core_plus_macro_plus_4h_momentum | 13 | 0.6279 | 0.1655 | 0.3953 | 0.2789 | 0.6667 |
| core_plus_macro_plus_all_4h | 20 | 0.6279 | 0.1655 | 0.3953 | 0.2789 | 0.6667 |
| current_full_minus_4h_structure_shift | 128 | 0.6279 | 0.1655 | 0.3953 | 0.2789 | 0.6667 |
| current_full_minus_4h | 121 | 0.6279 | 0.1655 | 0.3953 | 0.2789 | 0.6667 |
| current_full | 131 | 0.6279 | 0.1655 | 0.3953 | 0.2789 | 0.6667 |

## Live-bucket proxy ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|

## Supported-neighbor bucket proxy ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|
| core_plus_macro | 10 | 0.7308 | 0.0000 | 0.7308 | 0.2002 | 0.0000 |
| core_plus_macro_plus_4h_structure_shift | 13 | 0.7308 | 0.0000 | 0.7308 | 0.2002 | 0.0000 |
| core_plus_macro_plus_4h_trend | 13 | 0.7308 | 0.0000 | 0.7308 | 0.2002 | 0.0000 |
| core_plus_macro_plus_4h_momentum | 13 | 0.7308 | 0.0000 | 0.7308 | 0.2002 | 0.0000 |
| core_plus_macro_plus_all_4h | 20 | 0.7308 | 0.0000 | 0.7308 | 0.2002 | 0.0000 |
| current_full_minus_4h_structure_shift | 128 | 0.7308 | 0.0000 | 0.7308 | 0.2002 | 0.0000 |
| current_full_minus_4h | 121 | 0.7308 | 0.0000 | 0.7308 | 0.2002 | 0.0000 |
| current_full | 131 | 0.7308 | 0.0000 | 0.7308 | 0.2002 | 0.0000 |

## Support / pathology summary

- blocker_state: **exact_live_bucket_supported**
- preferred_support_cohort: **exact_live_bucket**
- current bucket gap to minimum: **0**
- exact-bucket proxy gap to minimum: **0**
- exact-lane proxy gap to minimum: **0**
- dominant neighbor bucket: `CAUTION|base_caution_regime_or_bias|q15` rows=7
- bucket gap vs dominant neighbor: **0**
- exact bucket root cause: **exact_bucket_supported**
- broader q65 rows / dominant regime: **87 / chop (0.8220)**
- root cause interpretation: exact bucket 已獲支持，可直接驗證 exact lane。
- bucket comparison takeaway: **exact_bucket_supported**
- proxy boundary verdict: **exact_bucket_supported_proxy_not_required**
- proxy boundary reason: current live structure bucket 已達 minimum support；後續治理與驗證應直接以 exact bucket 為主，proxy 只保留輔助比較，不再作 blocker 判讀。
- decision-quality scope / label: **regime_label+regime_gate+entry_quality_label / C**
- narrowed pathology scope: **None**
- worst pathology scope: **None**
- shared pathology shift features: []
- broader-bucket pathology shifts: []
- recommended_action: 可回到 exact live bucket 直接治理與驗證。

## Bucket evidence comparison

| cohort | bucket | rows | win_rate | quality / cv | note |
|---|---|---:|---:|---:|---|
| exact live lane | CAUTION|structure_quality_caution|q35 | 102 | 0.8725 | 0.576 | current bucket rows=85 |
| exact bucket proxy | CAUTION|structure_quality_caution|q35 | 129 | 0.9767441860465116 | None | proxy-vs-broader win Δ=-0.0118 |
| broader same bucket | CAUTION|structure_quality_caution|q35 | 87 | 0.9885 | 0.6898 | dominant_regime=chop |

## Proxy boundary diagnostics

- recent exact current bucket rows / win_rate: **85 / 1.0**
- recent exact live lane rows / win_rate: **102 / 0.9314**
- historical exact-bucket proxy rows / win_rate: **129 / 0.9767**
- recent broader same-bucket rows / dominant regime: **87 / bull**
- proxy vs current bucket win Δ / row ratio: **-0.0233 / 1.5176**
- exact lane vs current bucket win Δ / quality Δ: **-0.0686 / -0.1277**
- broader same-bucket vs current bucket win Δ / quality Δ: **0.0 / -0.0139**

## Exact lane sub-bucket diagnostics

- verdict: **toxic_sub_bucket_identified**
- reason: exact live lane 內的 `CAUTION|structure_quality_caution|q15` 明顯比 current bucket `CAUTION|structure_quality_caution|q35` 更差，bull exact lane 的病灶主要來自 lane-internal 子 bucket，而不是 current bucket 本身。
- toxic bucket: **CAUTION|structure_quality_caution|q15**
- toxic bucket rows / win_rate / avg_quality: **4 / 0.0 / None**
- toxic bucket vs current win Δ / quality Δ: **-1.0 / None**

## Notes

- collapse features under inspection: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- thresholds (bull q35): {"feat_4h_dist_swing_low": 1.8674, "feat_4h_dist_bb_lower": 1.1458, "feat_4h_bb_pct_b": 0.1375}
- exact live structure bucket: `CAUTION|structure_quality_caution|q35` rows=85
- supported neighbor buckets from exact scope: ["CAUTION|structure_quality_caution|q15", "CAUTION|base_caution_regime_or_bias|q15", "CAUTION|base_caution_regime_or_bias|q85"]
- best bull-all profile: **core_plus_macro_plus_4h_structure_shift**
- best bull-collapse profile: **core_plus_macro**
- best live-bucket proxy profile: **None**
- If live-bucket proxy stays tiny and unstable while supported-neighbor buckets remain healthier, the next fix should become a support-aware deployment blocker / fallback policy rather than a broader feature expansion.
