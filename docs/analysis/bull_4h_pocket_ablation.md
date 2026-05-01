# Bull 4H Collapse Pocket Ablation

- generated_at: **2026-05-01 23:03:56 UTC**
- target: `simulated_pyramid_win`
- collapse quantile: **q35**
- min collapse flags: **2 / 3**
- live context: **chop / CAUTION / D**
- live structure bucket: `CAUTION|base_caution_regime_or_bias|q35`
- refresh mode: **live_context_only**

## Cohorts

- bull_all rows: **2452** / win_rate **0.5000** / recommended **`current_full_minus_4h_structure_shift`**
- bull_collapse_q35 rows: **942** / win_rate **0.4406** / recommended **`core_plus_macro_plus_all_4h`**
- bull_exact_live_lane_proxy rows: **820** / win_rate **0.4841** / recommended **`None`**
- bull_live_exact_lane_bucket_proxy rows: **1** / win_rate **1.0000** / recommended **`None`**
- bull_supported_neighbor_buckets_proxy rows: **0** / win_rate **0.0000** / recommended **`None`**

## Bull-all ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|
| current_full_minus_4h_structure_shift | 128 | 0.5216 | 0.1989 | 0.3382 | 0.3133 | 0.7317 |
| core_plus_macro_plus_4h_structure_shift | 13 | 0.5176 | 0.2279 | 0.2745 | 0.3332 | 0.4829 |
| core_plus_macro_plus_all_4h | 20 | 0.5142 | 0.2211 | 0.2745 | 0.3160 | 0.5512 |
| core_plus_macro_plus_4h_trend | 13 | 0.5137 | 0.2004 | 0.3162 | 0.3162 | 0.4390 |
| current_full | 131 | 0.5118 | 0.2130 | 0.3015 | 0.3143 | 0.8634 |
| current_full_minus_4h | 121 | 0.4873 | 0.2161 | 0.3064 | 0.3095 | 0.7366 |
| core_plus_macro | 10 | 0.4809 | 0.1290 | 0.2770 | 0.3438 | 0.3707 |
| core_plus_macro_plus_4h_momentum | 13 | 0.4230 | 0.2084 | 0.1275 | 0.3293 | 0.7317 |

## Bull collapse-pocket ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|
| core_plus_macro_plus_all_4h | 20 | 0.4952 | 0.2006 | 0.1656 | 0.3472 | 0.2969 |
| core_plus_macro_plus_4h_trend | 13 | 0.3631 | 0.1603 | 0.1656 | 0.3788 | 0.5469 |
| current_full_minus_4h | 121 | 0.3471 | 0.1339 | 0.1656 | 0.3966 | 0.5625 |
| core_plus_macro | 10 | 0.3408 | 0.2482 | 0.1019 | 0.3861 | 0.5938 |
| current_full_minus_4h_structure_shift | 128 | 0.3344 | 0.1396 | 0.1656 | 0.3914 | 0.5312 |
| current_full | 131 | 0.3280 | 0.1330 | 0.1656 | 0.3948 | 0.3438 |
| core_plus_macro_plus_4h_structure_shift | 13 | 0.3185 | 0.1827 | 0.1465 | 0.3972 | 0.3906 |
| core_plus_macro_plus_4h_momentum | 13 | 0.3089 | 0.1922 | 0.1146 | 0.3985 | 0.3594 |

## Live-bucket proxy ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|

## Supported-neighbor bucket proxy ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|

## Support / pathology summary

- blocker_state: **exact_lane_proxy_fallback_only**
- preferred_support_cohort: **bull_exact_live_lane_proxy**
- current bucket gap to minimum: **32**
- exact-bucket proxy gap to minimum: **49**
- exact-lane proxy gap to minimum: **0**
- dominant neighbor bucket: `CAUTION|base_caution_regime_or_bias|q00` rows=3
- bucket gap vs dominant neighbor: **0**
- exact bucket root cause: **exact_bucket_present_but_below_minimum**
- broader q65 rows / dominant regime: **18 / chop (0.5111)**
- root cause interpretation: bull exact lane 已出現當前 bucket 樣本，但距離 minimum support 仍有缺口；需持續累積 exact rows，不能當成已解 blocker。
- bucket comparison takeaway: **support_gap_unresolved**
- proxy boundary verdict: **proxy_governance_reference_only_exact_support_blocked**
- proxy boundary reason: historical same-bucket proxy 可保留作 governance 參考，但 current live structure bucket 仍低於 minimum support；在 exact support 補滿前，proxy 不得當成 deployment 放行依據。
- decision-quality scope / label: **regime_gate+entry_quality_label / D**
- narrowed pathology scope: **None**
- worst pathology scope: **None**
- shared pathology shift features: []
- broader-bucket pathology shifts: []
- recommended_action: 維持部署 blocker；exact bucket 已出現但仍低於 minimum support，proxy 只可作治理參考。

## Bucket evidence comparison

| cohort | bucket | rows | win_rate | quality / cv | note |
|---|---|---:|---:|---:|---|
| exact live lane | CAUTION|base_caution_regime_or_bias|q35 | 23 | 0.6957 | 0.3809 | current bucket rows=18 |
| exact bucket proxy | CAUTION|base_caution_regime_or_bias|q35 | 1 | 1.0 | None | proxy-vs-broader win Δ=0.3889 |
| broader same bucket | CAUTION|base_caution_regime_or_bias|q35 | 18 | 0.6111 | 0.3741 | dominant_regime=chop |

## Proxy boundary diagnostics

- recent exact current bucket rows / win_rate: **1 / 1.0**
- recent exact live lane rows / win_rate: **23 / 0.1304**
- historical exact-bucket proxy rows / win_rate: **1 / 1.0**
- recent broader same-bucket rows / dominant regime: **18 / chop**
- proxy vs current bucket win Δ / row ratio: **0.0 / 1.0**
- exact lane vs current bucket win Δ / quality Δ: **-0.8696 / 0.0068**
- broader same-bucket vs current bucket win Δ / quality Δ: **-0.3889 / 0.0**

## Exact lane sub-bucket diagnostics

- verdict: **no_exact_lane_sub_bucket_split**
- reason: exact live lane 沒有可比較的非 current bucket 子 bucket。
- toxic bucket: **None**
- toxic bucket rows / win_rate / avg_quality: **None / None / None**
- toxic bucket vs current win Δ / quality Δ: **None / None**

## Notes

- collapse features under inspection: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- thresholds (bull q35): {"feat_4h_dist_swing_low": 4.9267, "feat_4h_dist_bb_lower": 4.2541, "feat_4h_bb_pct_b": 0.7069}
- exact live structure bucket: `CAUTION|base_caution_regime_or_bias|q35` rows=18
- supported neighbor buckets from exact scope: ["CAUTION|base_caution_regime_or_bias|q00", "CAUTION|base_caution_regime_or_bias|q15"]
- best bull-all profile: **current_full_minus_4h_structure_shift**
- best bull-collapse profile: **core_plus_macro_plus_all_4h**
- best live-bucket proxy profile: **None**
- If live-bucket proxy stays tiny and unstable while supported-neighbor buckets remain healthier, the next fix should become a support-aware deployment blocker / fallback policy rather than a broader feature expansion.
