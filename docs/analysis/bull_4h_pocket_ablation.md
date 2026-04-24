# Bull 4H Collapse Pocket Ablation

- generated_at: **2026-04-24 19:12:04 UTC**
- target: `simulated_pyramid_win`
- collapse quantile: **q35**
- min collapse flags: **2 / 3**
- live context: **chop / CAUTION / D**
- live structure bucket: `CAUTION|base_caution_regime_or_bias|q15`
- refresh mode: **live_context_only**

## Cohorts

- bull_all rows: **2323** / win_rate **0.5355** / recommended **`core_plus_macro_plus_4h_trend`**
- bull_collapse_q35 rows: **929** / win_rate **0.5630** / recommended **`core_plus_macro_plus_all_4h`**
- bull_exact_live_lane_proxy rows: **776** / win_rate **0.5090** / recommended **`None`**
- bull_live_exact_lane_bucket_proxy rows: **0** / win_rate **0.0000** / recommended **`None`**
- bull_supported_neighbor_buckets_proxy rows: **5** / win_rate **1.0000** / recommended **`None`**

## Bull-all ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|
| core_plus_macro_plus_4h_trend | 13 | 0.6367 | 0.2700 | 0.1908 | 0.2690 | 0.6000 |
| core_plus_macro_plus_4h_momentum | 13 | 0.6325 | 0.2792 | 0.1555 | 0.3148 | 0.4759 |
| core_plus_macro_plus_all_4h | 20 | 0.6134 | 0.2684 | 0.1802 | 0.2611 | 0.7655 |
| core_plus_macro_plus_4h_structure_shift | 13 | 0.6014 | 0.2848 | 0.1343 | 0.3029 | 0.5724 |
| current_full | 131 | 0.5929 | 0.2345 | 0.2226 | 0.2832 | 0.7655 |
| current_full_minus_4h_structure_shift | 128 | 0.5739 | 0.2322 | 0.1873 | 0.3003 | 0.7793 |
| current_full_minus_4h | 121 | 0.5696 | 0.2289 | 0.1908 | 0.3096 | 0.7793 |
| core_plus_macro | 10 | 0.5406 | 0.3019 | 0.1519 | 0.3344 | 0.6621 |

## Bull collapse-pocket ranking

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |
|---|---:|---:|---:|---:|---:|---:|
| core_plus_macro_plus_all_4h | 20 | 0.8586 | 0.0404 | 0.8182 | 0.1463 | 0.9500 |
| current_full_minus_4h_structure_shift | 128 | 0.7576 | 0.2020 | 0.5556 | 0.1587 | 0.9500 |
| core_plus_macro_plus_4h_structure_shift | 13 | 0.7424 | 0.1566 | 0.5859 | 0.1446 | 1.0000 |
| current_full | 131 | 0.7273 | 0.1717 | 0.5556 | 0.1646 | 0.8500 |
| current_full_minus_4h | 121 | 0.7273 | 0.1717 | 0.5556 | 0.1806 | 0.9500 |
| core_plus_macro_plus_4h_momentum | 13 | 0.6566 | 0.3434 | 0.3131 | 0.1743 | 0.8500 |
| core_plus_macro_plus_4h_trend | 13 | 0.4293 | 0.1263 | 0.3030 | 0.3119 | 0.5000 |
| core_plus_macro | 10 | 0.4040 | 0.1414 | 0.2626 | 0.3184 | 0.8000 |

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
- exact-lane proxy gap to minimum: **0**
- dominant neighbor bucket: `CAUTION|base_caution_regime_or_bias|q00` rows=49
- bucket gap vs dominant neighbor: **0**
- exact bucket root cause: **exact_bucket_supported**
- broader q65 rows / dominant regime: **123 / bull (0.5141)**
- root cause interpretation: exact bucket 已獲支持，可直接驗證 exact lane。
- bucket comparison takeaway: **exact_bucket_supported**
- proxy boundary verdict: **exact_bucket_supported_proxy_not_required**
- proxy boundary reason: current live structure bucket 已達 minimum support；後續治理與驗證應直接以 exact bucket 為主，proxy 只保留輔助比較，不再作 blocker 判讀。
- decision-quality scope / label: **regime_label+regime_gate+entry_quality_label / C**
- narrowed pathology scope: **None**
- worst pathology scope: **None**
- shared pathology shift features: []
- broader-bucket pathology shifts: []
- recommended_action: 可回到 exact live bucket 直接治理與驗證。

## Bucket evidence comparison

| cohort | bucket | rows | win_rate | quality / cv | note |
|---|---|---:|---:|---:|---|
| exact live lane | CAUTION|base_caution_regime_or_bias|q15 | 189 | 0.8307 | 0.47 | current bucket rows=123 |
| exact bucket proxy | CAUTION|base_caution_regime_or_bias|q15 | 0 | 0.0 | None | proxy-vs-broader win Δ=-0.8211 |
| broader same bucket | CAUTION|base_caution_regime_or_bias|q15 | 123 | 0.8211 | 0.4325 | dominant_regime=bull |

## Proxy boundary diagnostics

- recent exact current bucket rows / win_rate: **0 / None**
- recent exact live lane rows / win_rate: **189 / 0.8571**
- historical exact-bucket proxy rows / win_rate: **0 / None**
- recent broader same-bucket rows / dominant regime: **123 / chop**
- proxy vs current bucket win Δ / row ratio: **None / None**
- exact lane vs current bucket win Δ / quality Δ: **None / 0.0375**
- broader same-bucket vs current bucket win Δ / quality Δ: **None / 0.0**

## Exact lane sub-bucket diagnostics

- verdict: **sub_bucket_gap_present_but_inconclusive**
- reason: exact live lane 內部 bucket 有差異，但目前落差仍不足以下 toxic pocket 結論。
- toxic bucket: **CAUTION|base_caution_regime_or_bias|q35**
- toxic bucket rows / win_rate / avg_quality: **5 / 1.0 / None**
- toxic bucket vs current win Δ / quality Δ: **0.1789 / None**

## Notes

- collapse features under inspection: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- thresholds (bull q35): {"feat_4h_dist_swing_low": 5.1057, "feat_4h_dist_bb_lower": 4.7626, "feat_4h_bb_pct_b": 0.7172}
- exact live structure bucket: `CAUTION|base_caution_regime_or_bias|q15` rows=123
- supported neighbor buckets from exact scope: ["CAUTION|base_caution_regime_or_bias|q65", "CAUTION|base_caution_regime_or_bias|q35", "CAUTION|base_caution_regime_or_bias|q00"]
- best bull-all profile: **core_plus_macro_plus_4h_trend**
- best bull-collapse profile: **core_plus_macro_plus_all_4h**
- best live-bucket proxy profile: **None**
- If live-bucket proxy stays tiny and unstable while supported-neighbor buckets remain healthier, the next fix should become a support-aware deployment blocker / fallback policy rather than a broader feature expansion.
