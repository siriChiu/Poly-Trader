# Bull 4H Collapse Pocket Ablation

- generated_at: **2026-04-18 19:53:38 UTC**
- target: `simulated_pyramid_win`
- collapse quantile: **q35**
- min collapse flags: **2 / 3**
- live context: **bull / BLOCK / D**
- live structure bucket: `BLOCK|bull_q15_bias50_overextended_block|q15`

## Cohorts

- bull_all rows: **1301** / win_rate **0.6741** / recommended **`core_plus_macro_plus_4h_trend`**
- bull_collapse_q35 rows: **456** / win_rate **0.7237** / recommended **`core_plus_macro`**
- bull_exact_live_lane_proxy rows: **106** / win_rate **0.0000** / recommended **`None`**
- bull_live_exact_lane_bucket_proxy rows: **0** / win_rate **0.0000** / recommended **`None`**
- bull_supported_neighbor_buckets_proxy rows: **0** / win_rate **0.0000** / recommended **`None`**

## Bull-all ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|
| core_plus_macro_plus_4h_trend | 13 | 0.6690 | 0.0644 | 0.6019 | 0.2224 | 0.8750 |
| core_plus_macro_plus_all_4h | 20 | 0.6458 | 0.1334 | 0.4722 | 0.2206 | 0.9659 |
| current_full_minus_4h_structure_shift | 128 | 0.5926 | 0.1150 | 0.4028 | 0.2647 | 0.9205 |
| current_full_minus_4h | 121 | 0.5880 | 0.1197 | 0.3889 | 0.2815 | 0.8523 |
| current_full | 131 | 0.5810 | 0.1343 | 0.3565 | 0.2770 | 0.7273 |
| core_plus_macro_plus_4h_momentum | 13 | 0.5718 | 0.1325 | 0.3472 | 0.2638 | 0.8182 |
| core_plus_macro_plus_4h_structure_shift | 13 | 0.5694 | 0.1745 | 0.2778 | 0.2707 | 0.5795 |
| core_plus_macro | 10 | 0.4954 | 0.1645 | 0.2361 | 0.2903 | 0.8182 |

## Bull collapse-pocket ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|
| core_plus_macro | 10 | 0.2763 | 0.0132 | 0.2632 | 0.3661 | 0.5000 |
| core_plus_macro_plus_4h_structure_shift | 13 | 0.2763 | 0.0132 | 0.2632 | 0.3661 | 0.5000 |
| core_plus_macro_plus_4h_trend | 13 | 0.2763 | 0.0132 | 0.2632 | 0.3661 | 0.5000 |
| core_plus_macro_plus_4h_momentum | 13 | 0.2763 | 0.0132 | 0.2632 | 0.3661 | 0.5000 |
| core_plus_macro_plus_all_4h | 20 | 0.2763 | 0.0132 | 0.2632 | 0.3661 | 0.5000 |
| current_full_minus_4h_structure_shift | 128 | 0.2763 | 0.0132 | 0.2632 | 0.3661 | 0.5000 |
| current_full_minus_4h | 121 | 0.2763 | 0.0132 | 0.2632 | 0.3661 | 0.5000 |
| current_full | 131 | 0.2763 | 0.0132 | 0.2632 | 0.3661 | 0.5000 |

## Live-bucket proxy ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|

## Supported-neighbor bucket proxy ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|

## Support / pathology summary

- blocker_state: **exact_lane_proxy_fallback_only**
- preferred_support_cohort: **bull_exact_live_lane_proxy**
- current bucket gap to minimum: **9**
- exact-bucket proxy gap to minimum: **50**
- exact-lane proxy gap to minimum: **0**
- dominant neighbor bucket: `None` rows=0
- bucket gap vs dominant neighbor: **0**
- exact bucket root cause: **exact_bucket_present_but_below_minimum**
- broader q65 rows / dominant regime: **41 / bull (1.0000)**
- root cause interpretation: bull exact lane 已出現當前 bucket 樣本，但距離 minimum support 仍有缺口；需持續累積 exact rows，不能當成已解 blocker。
- bucket comparison takeaway: **support_gap_unresolved**
- proxy boundary verdict: **insufficient_recent_exact_bucket_rows**
- proxy boundary reason: current live structure bucket 沒有 recent exact rows，無法判斷 proxy cohort 邊界。
- decision-quality scope / label: **regime_label+entry_quality_label / D**
- narrowed pathology scope: **None**
- worst pathology scope: **regime_label+entry_quality_label**
- shared pathology shift features: ["feat_4h_dist_swing_low", "feat_4h_dist_bb_lower", "feat_4h_bb_pct_b"]
- broader-bucket pathology shifts: []
- recommended_action: 維持部署 blocker；exact bucket 已出現但仍低於 minimum support，proxy 只可作治理參考。

## Bucket evidence comparison

| cohort | bucket | rows | win_rate | quality / cv | note |
|---|---|---:|---:|---:|---|
| exact live lane | BLOCK|bull_q15_bias50_overextended_block|q15 | 41 | 1.0 | 0.697 | current bucket rows=41 |
| exact bucket proxy | BLOCK|bull_q15_bias50_overextended_block|q15 | 0 | 0.0 | None | proxy-vs-broader win Δ=-1.0 |
| broader same bucket | BLOCK|bull_q15_bias50_overextended_block|q15 | 41 | 1.0 | 0.697 | dominant_regime=bull |

## Proxy boundary diagnostics

- recent exact current bucket rows / win_rate: **0 / None**
- recent exact live lane rows / win_rate: **41 / 0.0**
- historical exact-bucket proxy rows / win_rate: **0 / None**
- recent broader same-bucket rows / dominant regime: **0 / None**
- proxy vs current bucket win Δ / row ratio: **None / None**
- exact lane vs current bucket win Δ / quality Δ: **None / 0.0**
- broader same-bucket vs current bucket win Δ / quality Δ: **None / 0.0**

## Exact lane sub-bucket diagnostics

- verdict: **no_exact_lane_sub_bucket_split**
- reason: exact live lane 沒有可比較的非 current bucket 子 bucket。
- toxic bucket: **None**
- toxic bucket rows / win_rate / avg_quality: **None / None / None**
- toxic bucket vs current win Δ / quality Δ: **None / None**

## Notes

- collapse features under inspection: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- thresholds (bull q35): {"feat_4h_dist_swing_low": 2.0838, "feat_4h_dist_bb_lower": 1.5728, "feat_4h_bb_pct_b": 0.4683}
- exact live structure bucket: `BLOCK|bull_q15_bias50_overextended_block|q15` rows=41
- supported neighbor buckets from exact scope: []
- best bull-all profile: **core_plus_macro_plus_4h_trend**
- best bull-collapse profile: **core_plus_macro**
- best live-bucket proxy profile: **None**
- If live-bucket proxy stays tiny and unstable while supported-neighbor buckets remain healthier, the next fix should become a support-aware deployment blocker / fallback policy rather than a broader feature expansion.
