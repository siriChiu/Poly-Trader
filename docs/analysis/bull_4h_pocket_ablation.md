# Bull 4H Collapse Pocket Ablation

- generated_at: **2026-04-14 18:42:00 UTC**
- target: `simulated_pyramid_win`
- collapse quantile: **q35**
- min collapse flags: **2 / 3**
- live context: **bull / CAUTION / D**
- live structure bucket: `CAUTION|structure_quality_caution|q35`

## Cohorts

- bull_all rows: **740** / win_rate **0.6932** / recommended **`core_plus_macro_plus_4h_structure_shift`**
- bull_collapse_q35 rows: **262** / win_rate **0.4962** / recommended **`core_plus_macro`**
- bull_exact_live_lane_proxy rows: **354** / win_rate **0.8192** / recommended **`core_plus_macro`**
- bull_live_exact_lane_bucket_proxy rows: **91** / win_rate **0.9670** / recommended **`None`**
- bull_supported_neighbor_buckets_proxy rows: **84** / win_rate **0.6905** / recommended **`core_plus_macro`**

## Bull-all ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|
| core_plus_macro_plus_4h_structure_shift | 13 | 0.7886 | 0.1406 | 0.5610 | 0.1857 | 0.9385 |
| core_plus_macro | 10 | 0.7707 | 0.1162 | 0.5610 | 0.1962 | 0.9231 |
| core_plus_macro_plus_all_4h | 20 | 0.7106 | 0.1056 | 0.5610 | 0.1806 | 0.8923 |
| current_full | 131 | 0.7106 | 0.1056 | 0.5610 | 0.1975 | 0.8615 |
| core_plus_macro_plus_4h_trend | 13 | 0.7106 | 0.1056 | 0.5610 | 0.2016 | 0.7538 |
| core_plus_macro_plus_4h_momentum | 13 | 0.7106 | 0.1056 | 0.5610 | 0.2026 | 0.7385 |
| current_full_minus_4h | 121 | 0.7106 | 0.1056 | 0.5610 | 0.2034 | 0.7846 |
| current_full_minus_4h_structure_shift | 128 | 0.7106 | 0.1056 | 0.5610 | 0.2051 | 0.7846 |

## Bull collapse-pocket ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|
| core_plus_macro | 10 | 0.6822 | 0.1264 | 0.5116 | 0.2409 | 0.6667 |
| core_plus_macro_plus_4h_structure_shift | 13 | 0.6822 | 0.1264 | 0.5116 | 0.2409 | 0.6667 |
| core_plus_macro_plus_4h_trend | 13 | 0.6822 | 0.1264 | 0.5116 | 0.2409 | 0.6667 |
| core_plus_macro_plus_4h_momentum | 13 | 0.6822 | 0.1264 | 0.5116 | 0.2409 | 0.6667 |
| core_plus_macro_plus_all_4h | 20 | 0.6822 | 0.1264 | 0.5116 | 0.2409 | 0.6667 |
| current_full_minus_4h_structure_shift | 128 | 0.6822 | 0.1264 | 0.5116 | 0.2409 | 0.6667 |
| current_full_minus_4h | 121 | 0.6822 | 0.1264 | 0.5116 | 0.2409 | 0.6667 |
| current_full | 131 | 0.6822 | 0.1264 | 0.5116 | 0.2409 | 0.6667 |

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
- current bucket gap to minimum: **8**
- exact-bucket proxy gap to minimum: **0**
- exact-lane proxy gap to minimum: **0**
- dominant neighbor bucket: `CAUTION|base_caution_regime_or_bias|q15` rows=7
- bucket gap vs dominant neighbor: **0**
- exact bucket root cause: **exact_bucket_present_but_below_minimum**
- broader q65 rows / dominant regime: **44 / chop (0.9080)**
- root cause interpretation: bull exact lane 已出現當前 bucket 樣本，但距離 minimum support 仍有缺口；需持續累積 exact rows，不能當成已解 blocker。
- bucket comparison takeaway: **support_gap_unresolved**
- proxy boundary verdict: **proxy_governance_reference_only_exact_support_blocked**
- proxy boundary reason: historical same-bucket proxy 可保留作 governance 參考，但 current live structure bucket 仍低於 minimum support；在 exact support 補滿前，proxy 不得當成 deployment 放行依據。
- decision-quality scope / label: **regime_label+regime_gate+entry_quality_label / C**
- narrowed pathology scope: **None**
- worst pathology scope: **None**
- shared pathology shift features: []
- broader-bucket pathology shifts: []
- recommended_action: 維持部署 blocker；exact bucket 已出現但仍低於 minimum support，proxy 只可作治理參考。

## Bucket evidence comparison

| cohort | bucket | rows | win_rate | quality / cv | note |
|---|---|---:|---:|---:|---|
| exact live lane | CAUTION|structure_quality_caution|q35 | 59 | 0.7797 | 0.4908 | current bucket rows=42 |
| exact bucket proxy | CAUTION|structure_quality_caution|q35 | 91 | 0.967032967032967 | None | proxy-vs-broader win Δ=-0.0103 |
| broader same bucket | CAUTION|structure_quality_caution|q35 | 44 | 0.9773 | 0.6868 | dominant_regime=chop |

## Proxy boundary diagnostics

- recent exact current bucket rows / win_rate: **42 / 1.0**
- recent exact live lane rows / win_rate: **59 / 0.8814**
- historical exact-bucket proxy rows / win_rate: **91 / 0.967**
- recent broader same-bucket rows / dominant regime: **44 / bull**
- proxy vs current bucket win Δ / row ratio: **-0.033 / 2.1667**
- exact lane vs current bucket win Δ / quality Δ: **-0.1186 / -0.224**
- broader same-bucket vs current bucket win Δ / quality Δ: **0.0 / -0.028**

## Exact lane sub-bucket diagnostics

- verdict: **toxic_sub_bucket_identified**
- reason: exact live lane 內的 `CAUTION|structure_quality_caution|q15` 明顯比 current bucket `CAUTION|structure_quality_caution|q35` 更差，bull exact lane 的病灶主要來自 lane-internal 子 bucket，而不是 current bucket 本身。
- toxic bucket: **CAUTION|structure_quality_caution|q15**
- toxic bucket rows / win_rate / avg_quality: **4 / 0.0 / None**
- toxic bucket vs current win Δ / quality Δ: **-1.0 / None**

## Notes

- collapse features under inspection: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- thresholds (bull q35): {"feat_4h_dist_swing_low": 1.7931, "feat_4h_dist_bb_lower": 0.6785, "feat_4h_bb_pct_b": 0.1316}
- exact live structure bucket: `CAUTION|structure_quality_caution|q35` rows=42
- supported neighbor buckets from exact scope: ["CAUTION|structure_quality_caution|q15", "CAUTION|base_caution_regime_or_bias|q15", "CAUTION|base_caution_regime_or_bias|q85"]
- best bull-all profile: **core_plus_macro_plus_4h_structure_shift**
- best bull-collapse profile: **core_plus_macro**
- best live-bucket proxy profile: **None**
- If live-bucket proxy stays tiny and unstable while supported-neighbor buckets remain healthier, the next fix should become a support-aware deployment blocker / fallback policy rather than a broader feature expansion.
