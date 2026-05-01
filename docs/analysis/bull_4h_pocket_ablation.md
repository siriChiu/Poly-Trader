# Bull 4H Collapse Pocket Ablation

- generated_at: **2026-05-01 09:06:23 UTC**
- target: `simulated_pyramid_win`
- collapse quantile: **q35**
- min collapse flags: **2 / 3**
- live context: **bear / CAUTION / D**
- live structure bucket: `CAUTION|structure_quality_caution|q15`
- refresh mode: **full_rebuild**

## Cohorts

- bull_all rows: **2453** / win_rate **0.5002** / recommended **`current_full_minus_4h_structure_shift`**
- bull_collapse_q35 rows: **943** / win_rate **0.4411** / recommended **`core_plus_macro_plus_all_4h`**
- bull_exact_live_lane_proxy rows: **821** / win_rate **0.4848** / recommended **`current_full_minus_4h_structure_shift`**
- bull_live_exact_lane_bucket_proxy rows: **132** / win_rate **0.5303** / recommended **`core_plus_macro`**
- bull_supported_neighbor_buckets_proxy rows: **687** / win_rate **0.4745** / recommended **`core_plus_macro_plus_all_4h`**

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
| core_plus_macro | 10 | 0.2576 | 0.1061 | 0.1515 | 0.4041 | 0.1250 |
| core_plus_macro_plus_4h_structure_shift | 13 | 0.2576 | 0.1061 | 0.1515 | 0.4041 | 0.1250 |
| core_plus_macro_plus_4h_trend | 13 | 0.2576 | 0.1061 | 0.1515 | 0.4041 | 0.1250 |
| core_plus_macro_plus_4h_momentum | 13 | 0.2576 | 0.1061 | 0.1515 | 0.4041 | 0.1250 |
| core_plus_macro_plus_all_4h | 20 | 0.2576 | 0.1061 | 0.1515 | 0.4041 | 0.1250 |
| current_full_minus_4h_structure_shift | 128 | 0.2576 | 0.1061 | 0.1515 | 0.4041 | 0.1250 |
| current_full_minus_4h | 121 | 0.2576 | 0.1061 | 0.1515 | 0.4041 | 0.1250 |
| current_full | 131 | 0.2576 | 0.1061 | 0.1515 | 0.4041 | 0.1250 |

## Supported-neighbor bucket proxy ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|
| core_plus_macro_plus_all_4h | 20 | 0.6491 | 0.0439 | 0.6053 | 0.2910 | 0.0000 |
| current_full | 131 | 0.6316 | 0.0614 | 0.5702 | 0.2755 | 0.0417 |
| current_full_minus_4h_structure_shift | 128 | 0.6316 | 0.0614 | 0.5702 | 0.2759 | 0.0417 |
| current_full_minus_4h | 121 | 0.6316 | 0.0614 | 0.5702 | 0.2780 | 0.0417 |
| core_plus_macro_plus_4h_structure_shift | 13 | 0.4561 | 0.2368 | 0.2193 | 0.3163 | 0.0000 |
| core_plus_macro_plus_4h_trend | 13 | 0.4518 | 0.2412 | 0.2105 | 0.3271 | 0.0000 |
| core_plus_macro | 10 | 0.4474 | 0.2456 | 0.2018 | 0.3544 | 0.0000 |
| core_plus_macro_plus_4h_momentum | 13 | 0.4430 | 0.2500 | 0.1930 | 0.3536 | 0.0000 |

## Support / pathology summary

- blocker_state: **exact_lane_proxy_fallback_only**
- preferred_support_cohort: **bull_live_exact_lane_bucket_proxy**
- current bucket gap to minimum: **37**
- exact-bucket proxy gap to minimum: **0**
- exact-lane proxy gap to minimum: **0**
- dominant neighbor bucket: `CAUTION|structure_quality_caution|q35` rows=3
- bucket gap vs dominant neighbor: **0**
- exact bucket root cause: **exact_bucket_present_but_below_minimum**
- broader q65 rows / dominant regime: **14 / chop (0.7875)**
- root cause interpretation: bull exact lane 已出現當前 bucket 樣本，但距離 minimum support 仍有缺口；需持續累積 exact rows，不能當成已解 blocker。
- bucket comparison takeaway: **prefer_same_bucket_proxy_over_cross_regime_spillover**
- proxy boundary verdict: **proxy_too_wide_vs_exact_bucket**
- proxy boundary reason: historical same-bucket proxy 與 recent exact bucket 的 win-rate 差距過大，應優先縮窄 proxy cohort，而不是把 proxy 直接當成 exact bucket 替身。
- decision-quality scope / label: **regime_gate / D**
- narrowed pathology scope: **None**
- worst pathology scope: **None**
- shared pathology shift features: []
- broader-bucket pathology shifts: []
- recommended_action: 維持部署 blocker；exact bucket 已出現但仍低於 minimum support，proxy 只可作治理參考。

## Bucket evidence comparison

| cohort | bucket | rows | win_rate | quality / cv | note |
|---|---|---:|---:|---:|---|
| exact live lane | CAUTION|structure_quality_caution|q15 | 16 | 0.3125 | -0.0199 | current bucket rows=13 |
| exact bucket proxy | CAUTION|structure_quality_caution|q15 | 132 | 0.5303030303030303 | 0.25757575757575757 | proxy-vs-broader win Δ=0.316 |
| broader same bucket | CAUTION|structure_quality_caution|q15 | 14 | 0.2143 | -0.081 | dominant_regime=chop |

## Proxy boundary diagnostics

- recent exact current bucket rows / win_rate: **13 / 0.0**
- recent exact live lane rows / win_rate: **16 / 0.0**
- historical exact-bucket proxy rows / win_rate: **132 / 0.5303**
- recent broader same-bucket rows / dominant regime: **14 / bear**
- proxy vs current bucket win Δ / row ratio: **0.5303 / 10.1538**
- exact lane vs current bucket win Δ / quality Δ: **0.0 / 0.0398**
- broader same-bucket vs current bucket win Δ / quality Δ: **0.2143 / -0.0213**

## Exact lane sub-bucket diagnostics

- verdict: **sub_bucket_gap_present_but_inconclusive**
- reason: exact live lane 內部 bucket 有差異，但目前落差仍不足以下 toxic pocket 結論。
- toxic bucket: **CAUTION|structure_quality_caution|q35**
- toxic bucket rows / win_rate / avg_quality: **3 / 1.0 / None**
- toxic bucket vs current win Δ / quality Δ: **0.7692 / None**

## Notes

- collapse features under inspection: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- thresholds (bull q35): {"feat_4h_dist_swing_low": 4.9263, "feat_4h_dist_bb_lower": 4.2535, "feat_4h_bb_pct_b": 0.7067}
- exact live structure bucket: `CAUTION|structure_quality_caution|q15` rows=13
- supported neighbor buckets from exact scope: ["CAUTION|structure_quality_caution|q35"]
- best bull-all profile: **current_full_minus_4h_structure_shift**
- best bull-collapse profile: **core_plus_macro_plus_all_4h**
- best live-bucket proxy profile: **core_plus_macro**
- If live-bucket proxy stays tiny and unstable while supported-neighbor buckets remain healthier, the next fix should become a support-aware deployment blocker / fallback policy rather than a broader feature expansion.
