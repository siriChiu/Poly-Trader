# Bull 4H Collapse Pocket Ablation

- generated_at: **2026-04-18 08:49:00 UTC**
- target: `simulated_pyramid_win`
- collapse quantile: **q35**
- min collapse flags: **2 / 3**
- live context: **bull / CAUTION / B**
- live structure bucket: `CAUTION|structure_quality_caution|q35`

## Cohorts

- bull_all rows: **1176** / win_rate **0.7611** / recommended **`core_plus_macro_plus_4h_structure_shift`**
- bull_collapse_q35 rows: **411** / win_rate **0.6788** / recommended **`core_plus_macro`**
- bull_exact_live_lane_proxy rows: **1** / win_rate **1.0000** / recommended **`None`**
- bull_live_exact_lane_bucket_proxy rows: **0** / win_rate **0.0000** / recommended **`None`**
- bull_supported_neighbor_buckets_proxy rows: **1** / win_rate **1.0000** / recommended **`None`**

## Bull-all ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|
| core_plus_macro_plus_4h_structure_shift | 13 | 0.5663 | 0.3341 | 0.0459 | 0.2530 | 0.9400 |
| core_plus_macro_plus_all_4h | 20 | 0.5663 | 0.3348 | 0.0459 | 0.2566 | 0.9800 |
| core_plus_macro_plus_4h_trend | 13 | 0.5643 | 0.3393 | 0.0306 | 0.2761 | 0.8600 |
| core_plus_macro_plus_4h_momentum | 13 | 0.5643 | 0.3393 | 0.0306 | 0.2839 | 0.8600 |
| core_plus_macro | 10 | 0.5643 | 0.3393 | 0.0306 | 0.3029 | 0.8300 |
| current_full | 131 | 0.4439 | 0.3226 | 0.0612 | 0.3055 | 0.9400 |
| current_full_minus_4h_structure_shift | 128 | 0.4439 | 0.3242 | 0.0459 | 0.3209 | 0.9400 |
| current_full_minus_4h | 121 | 0.4418 | 0.3256 | 0.0459 | 0.3322 | 0.9400 |

## Bull collapse-pocket ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|
| core_plus_macro | 10 | 0.6250 | 0.1544 | 0.4706 | 0.2137 | 0.5714 |
| core_plus_macro_plus_4h_structure_shift | 13 | 0.6250 | 0.1544 | 0.4706 | 0.2137 | 0.5714 |
| core_plus_macro_plus_4h_trend | 13 | 0.6250 | 0.1544 | 0.4706 | 0.2137 | 0.5714 |
| core_plus_macro_plus_4h_momentum | 13 | 0.6250 | 0.1544 | 0.4706 | 0.2137 | 0.5714 |
| core_plus_macro_plus_all_4h | 20 | 0.6250 | 0.1544 | 0.4706 | 0.2137 | 0.5714 |
| current_full_minus_4h_structure_shift | 128 | 0.6250 | 0.1544 | 0.4706 | 0.2137 | 0.5714 |
| current_full_minus_4h | 121 | 0.6250 | 0.1544 | 0.4706 | 0.2137 | 0.5714 |
| current_full | 131 | 0.6250 | 0.1544 | 0.4706 | 0.2137 | 0.5714 |

## Live-bucket proxy ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|

## Supported-neighbor bucket proxy ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|

## Support / pathology summary

- blocker_state: **exact_live_bucket_supported**
- preferred_support_cohort: **exact_live_bucket**
- current bucket gap to minimum: **0**
- exact-bucket proxy gap to minimum: **50**
- exact-lane proxy gap to minimum: **49**
- dominant neighbor bucket: `None` rows=0
- bucket gap vs dominant neighbor: **0**
- exact bucket root cause: **exact_bucket_supported**
- broader q65 rows / dominant regime: **100 / bull (0.9800)**
- root cause interpretation: exact bucket 已獲支持，可直接驗證 exact lane。
- bucket comparison takeaway: **exact_bucket_supported**
- proxy boundary verdict: **exact_bucket_supported_proxy_not_required**
- proxy boundary reason: current live structure bucket 已達 minimum support；後續治理與驗證應直接以 exact bucket 為主，proxy 只保留輔助比較，不再作 blocker 判讀。
- decision-quality scope / label: **regime_label / D**
- narrowed pathology scope: **None**
- worst pathology scope: **None**
- shared pathology shift features: []
- broader-bucket pathology shifts: []
- recommended_action: 可回到 exact live bucket 直接治理與驗證。

## Bucket evidence comparison

| cohort | bucket | rows | win_rate | quality / cv | note |
|---|---|---:|---:|---:|---|
| exact live lane | CAUTION|structure_quality_caution|q35 | 0 | None | None | current bucket rows=100 |
| exact bucket proxy | CAUTION|structure_quality_caution|q35 | 0 | 0.0 | None | proxy-vs-broader win Δ=-0.46 |
| broader same bucket | CAUTION|structure_quality_caution|q35 | 100 | 0.46 | 0.1281 | dominant_regime=bull |

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
- thresholds (bull q35): {"feat_4h_dist_swing_low": 2.0345, "feat_4h_dist_bb_lower": 1.4914, "feat_4h_bb_pct_b": 0.431}
- exact live structure bucket: `CAUTION|structure_quality_caution|q35` rows=100
- supported neighbor buckets from exact scope: ["CAUTION|structure_quality_caution|q15", "CAUTION|base_caution_regime_or_bias|q15", "CAUTION|base_caution_regime_or_bias|q00"]
- best bull-all profile: **core_plus_macro_plus_4h_structure_shift**
- best bull-collapse profile: **core_plus_macro**
- best live-bucket proxy profile: **None**
- If live-bucket proxy stays tiny and unstable while supported-neighbor buckets remain healthier, the next fix should become a support-aware deployment blocker / fallback policy rather than a broader feature expansion.
