# Bull 4H Collapse Pocket Ablation

- generated_at: **2026-04-19 18:55:11 UTC**
- target: `simulated_pyramid_win`
- collapse quantile: **q35**
- min collapse flags: **2 / 3**
- live context: **chop / CAUTION / D**
- live structure bucket: `CAUTION|base_caution_regime_or_bias|q00`
- refresh mode: **live_context_only**

## Cohorts

- bull_all rows: **1528** / win_rate **0.5360** / recommended **`core_plus_macro_plus_all_4h`**
- bull_collapse_q35 rows: **535** / win_rate **0.4374** / recommended **`core_plus_macro_plus_all_4h`**
- bull_exact_live_lane_proxy rows: **1000** / win_rate **0.6800** / recommended **`None`**
- bull_live_exact_lane_bucket_proxy rows: **0** / win_rate **0.0000** / recommended **`None`**
- bull_supported_neighbor_buckets_proxy rows: **649** / win_rate **0.7997** / recommended **`None`**

## Bull-all ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|
| core_plus_macro_plus_all_4h | 20 | 0.5626 | 0.3082 | 0.1261 | 0.2474 | 0.8000 |
| core_plus_macro_plus_4h_trend | 13 | 0.5583 | 0.3091 | 0.1261 | 0.2520 | 0.7043 |
| core_plus_macro_plus_4h_momentum | 13 | 0.5557 | 0.3111 | 0.1261 | 0.2942 | 0.7043 |
| core_plus_macro_plus_4h_structure_shift | 13 | 0.5296 | 0.3189 | 0.1261 | 0.3085 | 0.6870 |
| core_plus_macro | 10 | 0.4974 | 0.2735 | 0.1261 | 0.3211 | 0.6696 |
| current_full | 131 | 0.4565 | 0.2767 | 0.1261 | 0.2868 | 0.7913 |
| current_full_minus_4h_structure_shift | 128 | 0.4557 | 0.2751 | 0.1261 | 0.2786 | 0.8000 |
| current_full_minus_4h | 121 | 0.4330 | 0.2897 | 0.1261 | 0.3031 | 0.8000 |

## Bull collapse-pocket ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|
| core_plus_macro_plus_all_4h | 20 | 0.4136 | 0.4012 | 0.0123 | 0.3233 | 0.8889 |
| core_plus_macro | 10 | 0.4136 | 0.4012 | 0.0123 | 0.3319 | 1.0000 |
| core_plus_macro_plus_4h_momentum | 13 | 0.4136 | 0.4012 | 0.0123 | 0.3378 | 0.9444 |
| core_plus_macro_plus_4h_trend | 13 | 0.4136 | 0.4012 | 0.0123 | 0.3390 | 0.9444 |
| current_full | 131 | 0.4136 | 0.4012 | 0.0123 | 0.3395 | 0.8889 |
| current_full_minus_4h_structure_shift | 128 | 0.4136 | 0.4012 | 0.0123 | 0.3487 | 0.6667 |
| current_full_minus_4h | 121 | 0.4136 | 0.4012 | 0.0123 | 0.3523 | 0.7222 |
| core_plus_macro_plus_4h_structure_shift | 13 | 0.4074 | 0.3951 | 0.0123 | 0.3210 | 0.8889 |

## Live-bucket proxy ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|

## Supported-neighbor bucket proxy ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|

## Support / pathology summary

- blocker_state: **exact_lane_proxy_fallback_only**
- preferred_support_cohort: **bull_exact_live_lane_proxy**
- current bucket gap to minimum: **50**
- exact-bucket proxy gap to minimum: **50**
- exact-lane proxy gap to minimum: **0**
- dominant neighbor bucket: `None` rows=0
- bucket gap vs dominant neighbor: **0**
- exact bucket root cause: **same_lane_exists_but_q65_missing**
- broader q65 rows / dominant regime: **0 / bull (1.0000)**
- root cause interpretation: 目前支持資訊不足，需補更多 same-lane / broader-scope 證據。
- bucket comparison takeaway: **support_gap_unresolved**
- proxy boundary verdict: **insufficient_recent_exact_bucket_rows**
- proxy boundary reason: current live structure bucket 沒有 recent exact rows，無法判斷 proxy cohort 邊界。
- decision-quality scope / label: **global / D**
- narrowed pathology scope: **None**
- worst pathology scope: **entry_quality_label**
- shared pathology shift features: []
- broader-bucket pathology shifts: []
- recommended_action: 維持 0 layers；優先查 exact bucket 缺口與 same-bucket pathology，而不是再重訓。

## Bucket evidence comparison

| cohort | bucket | rows | win_rate | quality / cv | note |
|---|---|---:|---:|---:|---|
| exact live lane | None | 0 | None | None | current bucket rows=0 |
| exact bucket proxy | CAUTION|base_caution_regime_or_bias|q00 | 0 | 0.0 | None | proxy-vs-broader win Δ=None |
| broader same bucket | CAUTION|base_caution_regime_or_bias|q00 | 0 | None | None | dominant_regime=bull |

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
- thresholds (bull q35): {"feat_4h_dist_swing_low": 3.2449, "feat_4h_dist_bb_lower": 1.4863, "feat_4h_bb_pct_b": 0.4588}
- exact live structure bucket: `CAUTION|base_caution_regime_or_bias|q00` rows=0
- supported neighbor buckets from exact scope: ["CAUTION|structure_quality_caution|q35"]
- best bull-all profile: **core_plus_macro_plus_all_4h**
- best bull-collapse profile: **core_plus_macro_plus_all_4h**
- best live-bucket proxy profile: **None**
- If live-bucket proxy stays tiny and unstable while supported-neighbor buckets remain healthier, the next fix should become a support-aware deployment blocker / fallback policy rather than a broader feature expansion.
