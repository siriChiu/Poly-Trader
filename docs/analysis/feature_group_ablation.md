# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **5000**
- splits: **5** (TimeSeriesSplit)
- generated_at: **2026-04-18 17:09:54 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.7690 | 0.1470 | 0.5702 | 0.1942 | 0.7571 | - | 0.7333 |
| core_plus_macro_plus_all_4h | 50 | 0.7371 | 0.1139 | 0.5510 | 0.2133 | 0.9762 | - | 0.7727 |
| core_plus_macro_plus_4h_structure_shift | 22 | 0.7285 | 0.1120 | 0.5582 | 0.2113 | 1.0000 | - | 0.7795 |
| full_no_4h | 121 | 0.7241 | 0.1631 | 0.4490 | 0.2044 | 0.9429 | - | 0.7243 |
| current_full | 131 | 0.7124 | 0.1513 | 0.4766 | 0.2051 | 0.9476 | - | 0.7036 |
| full_no_technical | 121 | 0.7054 | 0.1459 | 0.4886 | 0.2107 | 0.9571 | - | 0.7780 |
| full_no_macro | 129 | 0.7016 | 0.1557 | 0.4766 | 0.2042 | 0.9357 | - | 0.7190 |
| current_full_no_bull_collapse_4h | 119 | 0.7011 | 0.1410 | 0.6026 | 0.2012 | 0.9476 | - | 0.6834 |
| core_plus_4h | 18 | 0.6996 | 0.1725 | 0.5066 | 0.2443 | 0.7810 | - | 0.7237 |
| full_no_cross | 120 | 0.6987 | 0.1365 | 0.5018 | 0.2094 | 0.9667 | - | 0.7190 |
| core_plus_macro_plus_4h_momentum | 22 | 0.6843 | 0.1355 | 0.5354 | 0.2308 | 0.9810 | - | 0.7602 |
| core_plus_macro | 10 | 0.6785 | 0.1501 | 0.5138 | 0.2340 | 0.9452 | - | 0.7234 |
| core_macro_plus_stable_4h | 38 | 0.6703 | 0.1441 | 0.5114 | 0.2274 | 0.9810 | - | 0.7371 |
| core_plus_technical | 18 | 0.6598 | 0.1744 | 0.4946 | 0.2437 | 0.8333 | - | 0.5390 |
| full_no_lags | 41 | 0.6540 | 0.1716 | 0.4622 | 0.2306 | 0.9286 | - | 0.6276 |
| core_plus_macro_plus_4h_trend | 22 | 0.6305 | 0.1722 | 0.4346 | 0.2456 | 0.9595 | - | 0.6878 |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
