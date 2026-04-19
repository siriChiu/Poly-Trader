# Bull 4H Collapse Pocket Ablation

- generated_at: **2026-04-19 03:53:26 UTC**
- target: `simulated_pyramid_win`
- collapse quantile: **q35**
- min collapse flags: **2 / 3**
- live context: **bull / BLOCK / D**
- live structure bucket: `BLOCK|bull_q15_bias50_overextended_block|q15`

## Cohorts

- bull_all rows: **1352** / win_rate **0.6220** / recommended **`core_plus_macro_plus_4h_trend`**
- bull_collapse_q35 rows: **475** / win_rate **0.7453** / recommended **`core_plus_macro`**
- bull_exact_live_lane_proxy rows: **348** / win_rate **0.0000** / recommended **`None`**
- bull_live_exact_lane_bucket_proxy rows: **0** / win_rate **0.0000** / recommended **`None`**
- bull_supported_neighbor_buckets_proxy rows: **242** / win_rate **0.0000** / recommended **`None`**

## Bull-all ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|
| core_plus_macro_plus_4h_trend | 13 | 0.6511 | 0.3025 | 0.1600 | 0.1749 | 0.8804 |
| core_plus_macro_plus_4h_momentum | 13 | 0.6511 | 0.3025 | 0.1600 | 0.1896 | 0.8696 |
| core_plus_macro_plus_all_4h | 20 | 0.6500 | 0.3036 | 0.1600 | 0.1795 | 0.9674 |
| core_plus_macro_plus_4h_structure_shift | 13 | 0.6044 | 0.2825 | 0.1600 | 0.1975 | 0.9457 |
| core_plus_macro | 10 | 0.5956 | 0.2790 | 0.1600 | 0.2145 | 0.8587 |
| current_full | 131 | 0.5433 | 0.2880 | 0.1600 | 0.2236 | 1.0000 |
| current_full_minus_4h | 121 | 0.5411 | 0.2870 | 0.1600 | 0.2286 | 1.0000 |
| current_full_minus_4h_structure_shift | 128 | 0.5400 | 0.2854 | 0.1600 | 0.2151 | 1.0000 |

## Bull collapse-pocket ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|
| core_plus_macro | 10 | 0.5253 | 0.4620 | 0.0633 | 0.2596 | 1.0000 |
| core_plus_macro_plus_4h_trend | 13 | 0.5253 | 0.4620 | 0.0633 | 0.2607 | 0.9375 |
| current_full_minus_4h_structure_shift | 128 | 0.5253 | 0.4620 | 0.0633 | 0.2656 | 1.0000 |
| core_plus_macro_plus_4h_momentum | 13 | 0.5253 | 0.4620 | 0.0633 | 0.2657 | 1.0000 |
| core_plus_macro_plus_all_4h | 20 | 0.5253 | 0.4620 | 0.0633 | 0.2658 | 1.0000 |
| current_full_minus_4h | 121 | 0.5253 | 0.4620 | 0.0633 | 0.2714 | 1.0000 |
| current_full | 131 | 0.5253 | 0.4620 | 0.0633 | 0.2715 | 1.0000 |
| core_plus_macro_plus_4h_structure_shift | 13 | 0.5253 | 0.4620 | 0.0633 | 0.2725 | 1.0000 |

## Live-bucket proxy ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|

## Supported-neighbor bucket proxy ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|

## Support / pathology summary

- blocker_state: **exact_lane_proxy_fallback_only**
- preferred_support_cohort: **bull_exact_live_lane_proxy**
- current bucket gap to minimum: **49**
- exact-bucket proxy gap to minimum: **50**
- exact-lane proxy gap to minimum: **0**
- dominant neighbor bucket: `BLOCK|bull_high_bias200_overheat_block|q35` rows=119
- bucket gap vs dominant neighbor: **118**
- exact bucket root cause: **exact_bucket_present_but_below_minimum**
- broader q65 rows / dominant regime: **1 / bull (1.0000)**
- root cause interpretation: bull exact lane 已出現當前 bucket 樣本，但距離 minimum support 仍有缺口；需持續累積 exact rows，不能當成已解 blocker。
- bucket comparison takeaway: **support_gap_unresolved**
- proxy boundary verdict: **insufficient_recent_exact_bucket_rows**
- proxy boundary reason: current live structure bucket 沒有 recent exact rows，無法判斷 proxy cohort 邊界。
- decision-quality scope / label: **regime_label+regime_gate+entry_quality_label / D**
- narrowed pathology scope: **None**
- worst pathology scope: **regime_label+regime_gate+entry_quality_label**
- shared pathology shift features: ["feat_4h_dist_bb_lower", "feat_4h_bb_pct_b", "feat_4h_dist_swing_low"]
- broader-bucket pathology shifts: ["feat_4h_dist_bb_lower", "feat_4h_bb_pct_b", "feat_4h_dist_swing_low"]
- recommended_action: 維持部署 blocker；exact bucket 已出現但仍低於 minimum support，proxy 只可作治理參考。

## Bucket evidence comparison

| cohort | bucket | rows | win_rate | quality / cv | note |
|---|---|---:|---:|---:|---|
| exact live lane | BLOCK|bull_q15_bias50_overextended_block|q15 | 199 | 0.0 | -0.2855 | current bucket rows=1 |
| exact bucket proxy | BLOCK|bull_q15_bias50_overextended_block|q15 | 0 | 0.0 | None | proxy-vs-broader win Δ=0.0 |
| broader same bucket | BLOCK|bull_q15_bias50_overextended_block|q15 | 1 | 0.0 | -0.2699 | dominant_regime=bull |

## Proxy boundary diagnostics

- recent exact current bucket rows / win_rate: **0 / None**
- recent exact live lane rows / win_rate: **199 / 0.0**
- historical exact-bucket proxy rows / win_rate: **0 / None**
- recent broader same-bucket rows / dominant regime: **0 / None**
- proxy vs current bucket win Δ / row ratio: **None / None**
- exact lane vs current bucket win Δ / quality Δ: **None / -0.0156**
- broader same-bucket vs current bucket win Δ / quality Δ: **None / 0.0**

## Exact lane sub-bucket diagnostics

- verdict: **sub_bucket_gap_present_but_inconclusive**
- reason: exact live lane 內部 bucket 有差異，但目前落差仍不足以下 toxic pocket 結論。
- toxic bucket: **BLOCK|bull_high_bias200_overheat_block|q35**
- toxic bucket rows / win_rate / avg_quality: **119 / 0.0 / None**
- toxic bucket vs current win Δ / quality Δ: **0.0 / None**

## Notes

- collapse features under inspection: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- thresholds (bull q35): {"feat_4h_dist_swing_low": 2.7305, "feat_4h_dist_bb_lower": 1.6044, "feat_4h_bb_pct_b": 0.4869}
- exact live structure bucket: `BLOCK|bull_q15_bias50_overextended_block|q15` rows=1
- supported neighbor buckets from exact scope: ["BLOCK|bull_high_bias200_overheat_block|q35", "BLOCK|bull_high_bias200_overheat_block|q65"]
- best bull-all profile: **core_plus_macro_plus_4h_trend**
- best bull-collapse profile: **core_plus_macro**
- best live-bucket proxy profile: **None**
- If live-bucket proxy stays tiny and unstable while supported-neighbor buckets remain healthier, the next fix should become a support-aware deployment blocker / fallback policy rather than a broader feature expansion.
