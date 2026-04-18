# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **5000**
- splits: **5** (TimeSeriesSplit)
- generated_at: **2026-04-18 19:53:36 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.7525 | 0.1380 | 0.5954 | 0.2000 | 0.8095 | - | 0.6267 |
| full_no_macro | 129 | 0.7273 | 0.1560 | 0.5414 | 0.2039 | 0.9500 | - | 0.7488 |
| core_plus_macro_plus_4h_structure_shift | 22 | 0.7261 | 0.1746 | 0.5354 | 0.2073 | 0.9548 | - | 0.7585 |
| current_full_no_bull_collapse_4h | 119 | 0.7109 | 0.1471 | 0.6038 | 0.2057 | 0.9381 | - | 0.6888 |
| core_plus_macro_plus_all_4h | 50 | 0.7102 | 0.1472 | 0.5450 | 0.2154 | 0.9810 | - | 0.7465 |
| core_plus_macro_plus_4h_momentum | 22 | 0.7020 | 0.1545 | 0.5654 | 0.2249 | 0.9810 | - | 0.6819 |
| full_no_technical | 121 | 0.6989 | 0.1589 | 0.5354 | 0.2148 | 0.9429 | - | 0.7095 |
| current_full | 131 | 0.6963 | 0.1606 | 0.5306 | 0.2129 | 0.9357 | - | 0.6407 |
| full_no_cross | 120 | 0.6948 | 0.1601 | 0.5306 | 0.2135 | 0.9476 | - | 0.7395 |
| core_plus_macro | 10 | 0.6922 | 0.1576 | 0.5666 | 0.2237 | 0.9643 | - | 0.8113 |
| core_plus_4h | 18 | 0.6843 | 0.1860 | 0.4910 | 0.2449 | 0.8833 | - | 0.6789 |
| full_no_4h | 121 | 0.6843 | 0.1839 | 0.4310 | 0.2043 | 0.9190 | - | 0.7391 |
| core_macro_plus_stable_4h | 38 | 0.6807 | 0.1651 | 0.5558 | 0.2305 | 0.9810 | - | 0.7485 |
| core_plus_technical | 18 | 0.6764 | 0.1716 | 0.5450 | 0.2277 | 0.8214 | - | 0.4917 |
| core_plus_macro_plus_4h_trend | 22 | 0.6451 | 0.1871 | 0.4814 | 0.2404 | 0.9929 | - | 0.6470 |
| full_no_lags | 41 | 0.6387 | 0.2002 | 0.4490 | 0.2312 | 0.9381 | - | 0.6316 |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
