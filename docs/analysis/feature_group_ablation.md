# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **5000**
- splits: **5** (TimeSeriesSplit)
- generated_at: **2026-04-19 18:55:08 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.6992 | 0.2297 | 0.4382 | 0.2472 | 0.7143 | - | 0.5801 |
| core_plus_macro_plus_all_4h | 50 | 0.6089 | 0.2544 | 0.3253 | 0.3245 | 0.7262 | - | 0.6758 |
| core_plus_macro_plus_4h_trend | 22 | 0.6000 | 0.2736 | 0.2533 | 0.3243 | 0.8071 | - | 0.7077 |
| core_plus_macro_plus_4h_structure_shift | 22 | 0.5892 | 0.2377 | 0.3265 | 0.3259 | 0.8690 | - | 0.7142 |
| core_plus_4h | 18 | 0.5887 | 0.2535 | 0.2665 | 0.3038 | 0.7190 | - | 0.5729 |
| core_macro_plus_stable_4h | 38 | 0.5808 | 0.2686 | 0.2581 | 0.3347 | 0.7333 | - | 0.6854 |
| core_plus_technical | 18 | 0.5741 | 0.2419 | 0.3373 | 0.2925 | 0.7500 | - | 0.4887 |
| full_no_macro | 129 | 0.5609 | 0.2519 | 0.3073 | 0.3554 | 0.7095 | - | 0.6613 |
| core_plus_macro | 10 | 0.5597 | 0.2571 | 0.2737 | 0.3400 | 0.9024 | - | 0.5956 |
| current_full | 131 | 0.5577 | 0.2541 | 0.3013 | 0.3560 | 0.7119 | - | 0.6565 |
| full_no_cross | 120 | 0.5525 | 0.2572 | 0.3025 | 0.3535 | 0.7238 | - | 0.6589 |
| core_plus_macro_plus_4h_momentum | 22 | 0.5501 | 0.2585 | 0.3301 | 0.3211 | 0.7571 | - | 0.7527 |
| full_no_technical | 121 | 0.5465 | 0.2646 | 0.2605 | 0.3555 | 0.7310 | - | 0.6589 |
| full_no_4h | 121 | 0.5438 | 0.2697 | 0.2329 | 0.3566 | 0.8071 | - | 0.6420 |
| current_full_no_bull_collapse_4h | 119 | 0.5306 | 0.2772 | 0.2317 | 0.3553 | 0.7667 | - | 0.6306 |
| full_no_lags | 41 | 0.5157 | 0.2903 | 0.2353 | 0.3370 | 0.7524 | - | 0.5633 |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
