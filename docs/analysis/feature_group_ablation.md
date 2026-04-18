# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **5000**
- splits: **5** (TimeSeriesSplit)
- generated_at: **2026-04-18 13:38:24 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.7791 | 0.1711 | 0.5102 | 0.1906 | 0.7381 | - | 0.7333 |
| core_plus_4h | 18 | 0.6413 | 0.1217 | 0.4454 | 0.2760 | 0.7952 | - | 0.6570 |
| core_plus_macro | 10 | 0.6156 | 0.1930 | 0.3950 | 0.2739 | 0.9833 | - | 0.6853 |
| core_plus_technical | 18 | 0.6110 | 0.2036 | 0.3565 | 0.2767 | 0.8381 | - | 0.5438 |
| core_plus_macro_plus_all_4h | 50 | 0.5248 | 0.2549 | 0.0288 | 0.3099 | 0.9548 | - | 0.7222 |
| core_plus_macro_plus_4h_momentum | 22 | 0.5222 | 0.2028 | 0.1873 | 0.3004 | 0.9786 | - | 0.8018 |
| core_plus_macro_plus_4h_structure_shift | 22 | 0.4970 | 0.2344 | 0.0516 | 0.2960 | 0.9929 | - | 0.7472 |
| core_plus_macro_plus_4h_trend | 22 | 0.4872 | 0.1332 | 0.3133 | 0.3314 | 0.9381 | - | 0.6570 |
| full_no_cross | 120 | 0.4780 | 0.2379 | 0.0300 | 0.3326 | 0.9762 | - | 0.7303 |
| full_no_lags | 41 | 0.4759 | 0.1759 | 0.1897 | 0.3156 | 0.9000 | - | 0.6532 |
| core_macro_plus_stable_4h | 38 | 0.4711 | 0.2220 | 0.0768 | 0.3131 | 0.9095 | - | 0.7141 |
| full_no_4h | 121 | 0.4651 | 0.2196 | 0.1777 | 0.3060 | 0.9595 | - | 0.7141 |
| full_no_technical | 121 | 0.4384 | 0.2382 | 0.0396 | 0.3379 | 0.9929 | - | 0.7928 |
| current_full | 131 | 0.4379 | 0.2465 | 0.0348 | 0.3401 | 0.9976 | - | 0.7976 |
| current_full_no_bull_collapse_4h | 119 | 0.4341 | 0.2297 | 0.1429 | 0.3465 | 0.9786 | - | 0.7116 |
| full_no_macro | 129 | 0.4223 | 0.2580 | 0.0300 | 0.3417 | 0.9857 | - | 0.7213 |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
