# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **5000**
- splits: **5** (TimeSeriesSplit)
- generated_at: **2026-04-18 11:14:29 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.7830 | 0.1914 | 0.4634 | 0.1928 | 0.7595 | - | 0.7333 |
| core_plus_4h | 18 | 0.6456 | 0.1769 | 0.4622 | 0.2788 | 0.7976 | - | 0.7333 |
| core_plus_technical | 18 | 0.5952 | 0.2344 | 0.2593 | 0.2891 | 0.9024 | - | 0.6321 |
| core_plus_macro | 10 | 0.5945 | 0.2153 | 0.3409 | 0.3197 | 1.0000 | - | 0.7458 |
| core_plus_macro_plus_4h_momentum | 22 | 0.5551 | 0.2438 | 0.1693 | 0.3044 | 0.9143 | - | 0.7980 |
| full_no_lags | 41 | 0.5527 | 0.2517 | 0.1357 | 0.3658 | 0.8905 | - | 0.6610 |
| core_plus_macro_plus_4h_trend | 22 | 0.5486 | 0.2606 | 0.1357 | 0.3616 | 0.7881 | - | 0.6618 |
| current_full_no_bull_collapse_4h | 119 | 0.5484 | 0.2418 | 0.1477 | 0.3737 | 0.9095 | - | 0.8000 |
| full_no_4h | 121 | 0.5316 | 0.2157 | 0.1549 | 0.3570 | 0.9619 | - | 0.8125 |
| core_plus_macro_plus_4h_structure_shift | 22 | 0.5270 | 0.1023 | 0.3854 | 0.3157 | 0.9762 | - | 0.8101 |
| core_macro_plus_stable_4h | 38 | 0.4922 | 0.1897 | 0.1417 | 0.3338 | 0.8167 | - | 0.7855 |
| full_no_technical | 121 | 0.4595 | 0.1765 | 0.1465 | 0.3794 | 0.9476 | - | 0.8000 |
| current_full | 131 | 0.4519 | 0.1815 | 0.1465 | 0.3798 | 0.9214 | - | 0.8000 |
| core_plus_macro_plus_all_4h | 50 | 0.4209 | 0.2195 | 0.0876 | 0.3377 | 0.9119 | - | 0.7952 |
| full_no_cross | 120 | 0.4122 | 0.2066 | 0.1561 | 0.3681 | 0.9333 | - | 0.8000 |
| full_no_macro | 129 | 0.4103 | 0.2397 | 0.1116 | 0.3740 | 0.9167 | - | 0.8000 |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
