# Bull 4H Collapse Pocket Ablation

- generated_at: **2026-04-14 17:46:27 UTC**
- target: `simulated_pyramid_win`
- collapse quantile: **q35**
- min collapse flags: **2 / 3**
- live context: **bull / CAUTION / D**
- live structure bucket: `CAUTION|structure_quality_caution|q35`

## Cohorts

- bull_all rows: **705** / win_rate **0.6780** / recommended **`core_plus_macro_plus_all_4h`**
- bull_collapse_q35 rows: **254** / win_rate **0.5000** / recommended **`core_plus_macro`**
- bull_exact_live_lane_proxy rows: **319** / win_rate **0.7994** / recommended **`core_plus_macro`**
- bull_live_exact_lane_bucket_proxy rows: **56** / win_rate **0.9464** / recommended **`None`**
- bull_supported_neighbor_buckets_proxy rows: **84** / win_rate **0.6905** / recommended **`core_plus_macro`**

## Bull-all ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|
| core_plus_macro_plus_all_4h | 20 | 0.6530 | 0.2654 | 0.1282 | 0.1977 | 0.8333 |
| current_full_minus_4h | 121 | 0.6530 | 0.2654 | 0.1282 | 0.2065 | 0.8667 |
| current_full | 131 | 0.6530 | 0.2654 | 0.1282 | 0.2069 | 0.8333 |
| current_full_minus_4h_structure_shift | 128 | 0.6530 | 0.2654 | 0.1282 | 0.2082 | 0.7833 |
| core_plus_macro_plus_4h_trend | 13 | 0.6496 | 0.2722 | 0.1111 | 0.2071 | 0.7333 |
| core_plus_macro_plus_4h_structure_shift | 13 | 0.6496 | 0.2722 | 0.1111 | 0.2237 | 0.9333 |
| core_plus_macro | 10 | 0.6496 | 0.2722 | 0.1111 | 0.2251 | 0.7333 |
| core_plus_macro_plus_4h_momentum | 13 | 0.6496 | 0.2722 | 0.1111 | 0.2340 | 0.7000 |

## Bull collapse-pocket ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|
| core_plus_macro | 10 | 0.6984 | 0.0978 | 0.5714 | 0.2291 | 0.6667 |
| core_plus_macro_plus_4h_structure_shift | 13 | 0.6984 | 0.0978 | 0.5714 | 0.2291 | 0.6667 |
| core_plus_macro_plus_4h_trend | 13 | 0.6984 | 0.0978 | 0.5714 | 0.2291 | 0.6667 |
| core_plus_macro_plus_4h_momentum | 13 | 0.6984 | 0.0978 | 0.5714 | 0.2291 | 0.6667 |
| core_plus_macro_plus_all_4h | 20 | 0.6984 | 0.0978 | 0.5714 | 0.2291 | 0.6667 |
| current_full_minus_4h_structure_shift | 128 | 0.6984 | 0.0978 | 0.5714 | 0.2291 | 0.6667 |
| current_full_minus_4h | 121 | 0.6984 | 0.0978 | 0.5714 | 0.2291 | 0.6667 |
| current_full | 131 | 0.6984 | 0.0978 | 0.5714 | 0.2291 | 0.6667 |

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
- current bucket gap to minimum: **37**
- exact-bucket proxy gap to minimum: **0**
- exact-lane proxy gap to minimum: **0**
- dominant neighbor bucket: `CAUTION|base_caution_regime_or_bias|q15` rows=7
- bucket gap vs dominant neighbor: **0**
- exact bucket root cause: **exact_bucket_present_but_below_minimum**
- broader q65 rows / dominant regime: **15 / chop (0.9660)**
- root cause interpretation: bull exact lane 已出現當前 bucket 樣本，但距離 minimum support 仍有缺口；需持續累積 exact rows，不能當成已解 blocker。
- bucket comparison takeaway: **prefer_same_bucket_proxy_over_cross_regime_spillover**
- proxy boundary verdict: **proxy_boundary_inconclusive**
- proxy boundary reason: proxy 與 exact bucket 差距尚未大到可直接判定，但也不足以解除 runtime blocker。
- decision-quality scope / label: **regime_label+regime_gate+entry_quality_label / D**
- narrowed pathology scope: **None**
- worst pathology scope: **regime_label+entry_quality_label**
- shared pathology shift features: []
- broader-bucket pathology shifts: []
- recommended_action: 維持部署 blocker；exact bucket 已出現但仍低於 minimum support，proxy 只可作治理參考。

## Bucket evidence comparison

| cohort | bucket | rows | win_rate | quality / cv | note |
|---|---|---:|---:|---:|---|
| exact live lane | CAUTION|structure_quality_caution|q35 | 30 | 0.5667 | 0.2694 | current bucket rows=13 |
| exact bucket proxy | CAUTION|structure_quality_caution|q35 | 56 | 0.9464285714285714 | None | proxy-vs-broader win Δ=0.0131 |
| broader same bucket | CAUTION|structure_quality_caution|q35 | 15 | 0.9333 | 0.6231 | dominant_regime=chop |

## Proxy boundary diagnostics

- recent exact current bucket rows / win_rate: **13 / 1.0**
- recent exact live lane rows / win_rate: **30 / 0.7667**
- historical exact-bucket proxy rows / win_rate: **56 / 0.9464**
- recent broader same-bucket rows / dominant regime: **15 / bull**
- proxy vs current bucket win Δ / row ratio: **-0.0536 / 4.3077**
- exact lane vs current bucket win Δ / quality Δ: **-0.2333 / -0.4342**
- broader same-bucket vs current bucket win Δ / quality Δ: **-0.0667 / -0.0805**

## Exact lane sub-bucket diagnostics

- verdict: **toxic_sub_bucket_identified**
- reason: exact live lane 內的 `CAUTION|structure_quality_caution|q15` 明顯比 current bucket `CAUTION|structure_quality_caution|q35` 更差，bull exact lane 的病灶主要來自 lane-internal 子 bucket，而不是 current bucket 本身。
- toxic bucket: **CAUTION|structure_quality_caution|q15**
- toxic bucket rows / win_rate / avg_quality: **4 / 0.0 / None**
- toxic bucket vs current win Δ / quality Δ: **-1.0 / None**

## Notes

- collapse features under inspection: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- thresholds (bull q35): {"feat_4h_dist_swing_low": 1.7704, "feat_4h_dist_bb_lower": 0.4371, "feat_4h_bb_pct_b": 0.1278}
- exact live structure bucket: `CAUTION|structure_quality_caution|q35` rows=13
- supported neighbor buckets from exact scope: ["CAUTION|structure_quality_caution|q15", "CAUTION|base_caution_regime_or_bias|q15", "CAUTION|base_caution_regime_or_bias|q85"]
- best bull-all profile: **core_plus_macro_plus_all_4h**
- best bull-collapse profile: **core_plus_macro**
- best live-bucket proxy profile: **None**
- If live-bucket proxy stays tiny and unstable while supported-neighbor buckets remain healthier, the next fix should become a support-aware deployment blocker / fallback policy rather than a broader feature expansion.
