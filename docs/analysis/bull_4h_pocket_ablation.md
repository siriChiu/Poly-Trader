# Bull 4H Collapse Pocket Ablation

- generated_at: **2026-04-14 18:16:42 UTC**
- target: `simulated_pyramid_win`
- collapse quantile: **q35**
- min collapse flags: **2 / 3**
- live context: **bull / CAUTION / D**
- live structure bucket: `CAUTION|structure_quality_caution|q35`

## Cohorts

- bull_all rows: **716** / win_rate **0.6830** / recommended **`core_plus_macro_plus_all_4h`**
- bull_collapse_q35 rows: **257** / win_rate **0.4942** / recommended **`core_plus_macro`**
- bull_exact_live_lane_proxy rows: **330** / win_rate **0.8061** / recommended **`core_plus_macro`**
- bull_live_exact_lane_bucket_proxy rows: **67** / win_rate **0.9552** / recommended **`None`**
- bull_supported_neighbor_buckets_proxy rows: **84** / win_rate **0.6905** / recommended **`core_plus_macro`**

## Bull-all ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|
| core_plus_macro_plus_all_4h | 20 | 0.8084 | 0.0936 | 0.6975 | 0.1814 | 0.8833 |
| current_full | 131 | 0.7950 | 0.0724 | 0.6975 | 0.1815 | 0.9333 |
| current_full_minus_4h | 121 | 0.7899 | 0.0655 | 0.6975 | 0.1829 | 0.9333 |
| current_full_minus_4h_structure_shift | 128 | 0.7866 | 0.0614 | 0.6975 | 0.1844 | 0.9333 |
| core_plus_macro_plus_4h_trend | 13 | 0.6555 | 0.2324 | 0.2017 | 0.1926 | 0.7333 |
| core_plus_macro_plus_4h_structure_shift | 13 | 0.6555 | 0.2324 | 0.2017 | 0.2045 | 0.9167 |
| core_plus_macro | 10 | 0.6555 | 0.2324 | 0.2017 | 0.2069 | 0.8833 |
| core_plus_macro_plus_4h_momentum | 13 | 0.6555 | 0.2324 | 0.2017 | 0.2145 | 0.7000 |

## Bull collapse-pocket ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|
| core_plus_macro | 10 | 0.6746 | 0.1294 | 0.5000 | 0.2453 | 0.6667 |
| core_plus_macro_plus_4h_structure_shift | 13 | 0.6746 | 0.1294 | 0.5000 | 0.2453 | 0.6667 |
| core_plus_macro_plus_4h_trend | 13 | 0.6746 | 0.1294 | 0.5000 | 0.2453 | 0.6667 |
| core_plus_macro_plus_4h_momentum | 13 | 0.6746 | 0.1294 | 0.5000 | 0.2453 | 0.6667 |
| core_plus_macro_plus_all_4h | 20 | 0.6746 | 0.1294 | 0.5000 | 0.2453 | 0.6667 |
| current_full_minus_4h_structure_shift | 128 | 0.6746 | 0.1294 | 0.5000 | 0.2453 | 0.6667 |
| current_full_minus_4h | 121 | 0.6746 | 0.1294 | 0.5000 | 0.2453 | 0.6667 |
| current_full | 131 | 0.6746 | 0.1294 | 0.5000 | 0.2453 | 0.6667 |

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

- blocker_state: **exact_lane_proxy_fallback_only**
- preferred_support_cohort: **bull_live_exact_lane_bucket_proxy**
- current bucket gap to minimum: **32**
- exact-bucket proxy gap to minimum: **0**
- exact-lane proxy gap to minimum: **0**
- dominant neighbor bucket: `CAUTION|base_caution_regime_or_bias|q15` rows=7
- bucket gap vs dominant neighbor: **0**
- exact bucket root cause: **exact_bucket_present_but_below_minimum**
- broader q65 rows / dominant regime: **20 / chop (0.9560)**
- root cause interpretation: bull exact lane 已出現當前 bucket 樣本，但距離 minimum support 仍有缺口；需持續累積 exact rows，不能當成已解 blocker。
- bucket comparison takeaway: **prefer_same_bucket_proxy_over_cross_regime_spillover**
- proxy boundary verdict: **proxy_boundary_inconclusive**
- proxy boundary reason: proxy 與 exact bucket 差距尚未大到可直接判定，但也不足以解除 runtime blocker。
- decision-quality scope / label: **regime_label+regime_gate+entry_quality_label / D**
- narrowed pathology scope: **None**
- worst pathology scope: **None**
- shared pathology shift features: []
- broader-bucket pathology shifts: []
- recommended_action: 維持部署 blocker；exact bucket 已出現但仍低於 minimum support，proxy 只可作治理參考。

## Bucket evidence comparison

| cohort | bucket | rows | win_rate | quality / cv | note |
|---|---|---:|---:|---:|---|
| exact live lane | CAUTION|structure_quality_caution|q35 | 35 | 0.6286 | 0.3328 | current bucket rows=18 |
| exact bucket proxy | CAUTION|structure_quality_caution|q35 | 67 | 0.9552238805970149 | None | proxy-vs-broader win Δ=0.0052 |
| broader same bucket | CAUTION|structure_quality_caution|q35 | 20 | 0.95 | 0.6457 | dominant_regime=chop |

## Proxy boundary diagnostics

- recent exact current bucket rows / win_rate: **18 / 1.0**
- recent exact live lane rows / win_rate: **35 / 0.8**
- historical exact-bucket proxy rows / win_rate: **67 / 0.9552**
- recent broader same-bucket rows / dominant regime: **20 / bull**
- proxy vs current bucket win Δ / row ratio: **-0.0448 / 3.7222**
- exact lane vs current bucket win Δ / quality Δ: **-0.2 / -0.3736**
- broader same-bucket vs current bucket win Δ / quality Δ: **0.0 / -0.0607**

## Exact lane sub-bucket diagnostics

- verdict: **toxic_sub_bucket_identified**
- reason: exact live lane 內的 `CAUTION|structure_quality_caution|q15` 明顯比 current bucket `CAUTION|structure_quality_caution|q35` 更差，bull exact lane 的病灶主要來自 lane-internal 子 bucket，而不是 current bucket 本身。
- toxic bucket: **CAUTION|structure_quality_caution|q15**
- toxic bucket rows / win_rate / avg_quality: **4 / 0.0 / None**
- toxic bucket vs current win Δ / quality Δ: **-1.0 / None**

## Notes

- collapse features under inspection: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- thresholds (bull q35): {"feat_4h_dist_swing_low": 1.7747, "feat_4h_dist_bb_lower": 0.4418, "feat_4h_bb_pct_b": 0.1286}
- exact live structure bucket: `CAUTION|structure_quality_caution|q35` rows=18
- supported neighbor buckets from exact scope: ["CAUTION|structure_quality_caution|q15", "CAUTION|base_caution_regime_or_bias|q15", "CAUTION|base_caution_regime_or_bias|q85"]
- best bull-all profile: **core_plus_macro_plus_all_4h**
- best bull-collapse profile: **core_plus_macro**
- best live-bucket proxy profile: **None**
- If live-bucket proxy stays tiny and unstable while supported-neighbor buckets remain healthier, the next fix should become a support-aware deployment blocker / fallback policy rather than a broader feature expansion.
