# Bull 4H Collapse Pocket Ablation

- generated_at: **2026-04-19 00:19:49 UTC**
- target: `simulated_pyramid_win`
- collapse quantile: **q35**
- min collapse flags: **2 / 3**
- live context: **bull / BLOCK / D**
- live structure bucket: `BLOCK|bull_q15_bias50_overextended_block|q15`

## Cohorts

- bull_all rows: **1345** / win_rate **0.6253** / recommended **`core_plus_macro_plus_4h_trend`**
- bull_collapse_q35 rows: **473** / win_rate **0.7463** / recommended **`core_plus_macro`**
- bull_exact_live_lane_proxy rows: **342** / win_rate **0.0000** / recommended **`None`**
- bull_live_exact_lane_bucket_proxy rows: **0** / win_rate **0.0000** / recommended **`None`**
- bull_supported_neighbor_buckets_proxy rows: **236** / win_rate **0.0000** / recommended **`None`**

## Bull-all ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|
| core_plus_macro_plus_4h_trend | 13 | 0.6596 | 0.2985 | 0.1696 | 0.1716 | 0.8804 |
| core_plus_macro_plus_4h_momentum | 13 | 0.6596 | 0.2985 | 0.1696 | 0.1848 | 0.8913 |
| core_plus_macro_plus_all_4h | 20 | 0.6585 | 0.2995 | 0.1696 | 0.1757 | 0.9457 |
| core_plus_macro | 10 | 0.6038 | 0.2765 | 0.1696 | 0.2110 | 0.8478 |
| core_plus_macro_plus_4h_structure_shift | 13 | 0.5580 | 0.2751 | 0.1696 | 0.1929 | 0.9130 |
| current_full | 131 | 0.5558 | 0.2856 | 0.1696 | 0.2187 | 1.0000 |
| current_full_minus_4h | 121 | 0.5536 | 0.2845 | 0.1696 | 0.2214 | 1.0000 |
| current_full_minus_4h_structure_shift | 128 | 0.5525 | 0.2830 | 0.1696 | 0.2110 | 1.0000 |

## Bull collapse-pocket ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|
| core_plus_macro | 10 | 0.0385 | 0.0000 | 0.0385 | 0.5100 | 1.0000 |
| core_plus_macro_plus_4h_structure_shift | 13 | 0.0385 | 0.0000 | 0.0385 | 0.5100 | 1.0000 |
| core_plus_macro_plus_4h_trend | 13 | 0.0385 | 0.0000 | 0.0385 | 0.5100 | 1.0000 |
| core_plus_macro_plus_4h_momentum | 13 | 0.0385 | 0.0000 | 0.0385 | 0.5100 | 1.0000 |
| core_plus_macro_plus_all_4h | 20 | 0.0385 | 0.0000 | 0.0385 | 0.5100 | 1.0000 |
| current_full_minus_4h_structure_shift | 128 | 0.0385 | 0.0000 | 0.0385 | 0.5100 | 1.0000 |
| current_full_minus_4h | 121 | 0.0385 | 0.0000 | 0.0385 | 0.5100 | 1.0000 |
| current_full | 131 | 0.0385 | 0.0000 | 0.0385 | 0.5100 | 1.0000 |

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
- dominant neighbor bucket: `BLOCK|bull_high_bias200_overheat_block|q35` rows=113
- bucket gap vs dominant neighbor: **113**
- exact bucket root cause: **same_lane_shifted_to_neighbor_bucket**
- broader q65 rows / dominant regime: **0 / bull (1.0000)**
- root cause interpretation: bull exact lane 仍有同 lane 樣本，但當前結構已偏到鄰近 bucket，需先查 q65↔q85 分桶與 same-lane pathology。
- bucket comparison takeaway: **support_gap_unresolved**
- proxy boundary verdict: **insufficient_recent_exact_bucket_rows**
- proxy boundary reason: current live structure bucket 沒有 recent exact rows，無法判斷 proxy cohort 邊界。
- decision-quality scope / label: **regime_label+regime_gate+entry_quality_label / D**
- narrowed pathology scope: **None**
- worst pathology scope: **regime_label+regime_gate+entry_quality_label**
- shared pathology shift features: ["feat_4h_dist_bb_lower", "feat_4h_bb_pct_b", "feat_4h_dist_swing_low"]
- broader-bucket pathology shifts: ["feat_4h_dist_bb_lower", "feat_4h_bb_pct_b", "feat_4h_dist_swing_low"]
- recommended_action: 維持 0 layers；優先查 exact bucket 缺口與 same-bucket pathology，而不是再重訓。

## Bucket evidence comparison

| cohort | bucket | rows | win_rate | quality / cv | note |
|---|---|---:|---:|---:|---|
| exact live lane | BLOCK|bull_high_bias200_overheat_block|q35 | 199 | 0.0 | -0.2848 | current bucket rows=0 |
| exact bucket proxy | BLOCK|bull_q15_bias50_overextended_block|q15 | 0 | 0.0 | None | proxy-vs-broader win Δ=None |
| broader same bucket | BLOCK|bull_q15_bias50_overextended_block|q15 | 0 | None | None | dominant_regime=bull |

## Proxy boundary diagnostics

- recent exact current bucket rows / win_rate: **0 / None**
- recent exact live lane rows / win_rate: **199 / 0.0**
- historical exact-bucket proxy rows / win_rate: **0 / None**
- recent broader same-bucket rows / dominant regime: **0 / None**
- proxy vs current bucket win Δ / row ratio: **None / None**
- exact lane vs current bucket win Δ / quality Δ: **None / None**
- broader same-bucket vs current bucket win Δ / quality Δ: **None / None**

## Exact lane sub-bucket diagnostics

- verdict: **sub_bucket_gap_present_but_inconclusive**
- reason: exact live lane 內部 bucket 有差異，但目前落差仍不足以下 toxic pocket 結論。
- toxic bucket: **BLOCK|bull_high_bias200_overheat_block|q35**
- toxic bucket rows / win_rate / avg_quality: **113 / 0.0 / None**
- toxic bucket vs current win Δ / quality Δ: **None / None**

## Notes

- collapse features under inspection: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- thresholds (bull q35): {"feat_4h_dist_swing_low": 2.6831, "feat_4h_dist_bb_lower": 1.6042, "feat_4h_bb_pct_b": 0.4867}
- exact live structure bucket: `BLOCK|bull_q15_bias50_overextended_block|q15` rows=0
- supported neighbor buckets from exact scope: ["BLOCK|bull_high_bias200_overheat_block|q35", "BLOCK|bull_high_bias200_overheat_block|q65"]
- best bull-all profile: **core_plus_macro_plus_4h_trend**
- best bull-collapse profile: **core_plus_macro**
- best live-bucket proxy profile: **None**
- If live-bucket proxy stays tiny and unstable while supported-neighbor buckets remain healthier, the next fix should become a support-aware deployment blocker / fallback policy rather than a broader feature expansion.
