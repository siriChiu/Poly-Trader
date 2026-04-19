# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **5000**
- splits: **5** (TimeSeriesSplit)
- generated_at: **2026-04-19 03:53:24 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.7311 | 0.1402 | 0.5894 | 0.2215 | 0.6881 | - | 0.4888 |
| core_plus_4h | 18 | 0.7025 | 0.1834 | 0.5078 | 0.2295 | 0.9595 | - | 0.7211 |
| core_plus_technical | 18 | 0.6927 | 0.1634 | 0.5330 | 0.2199 | 0.8024 | - | 0.6132 |
| core_plus_macro_plus_4h_structure_shift | 22 | 0.6699 | 0.1916 | 0.4490 | 0.2509 | 0.8262 | - | 0.7041 |
| core_plus_macro_plus_4h_trend | 22 | 0.6665 | 0.1820 | 0.4514 | 0.2475 | 0.9643 | - | 0.8628 |
| core_plus_macro | 10 | 0.6660 | 0.1778 | 0.4802 | 0.2534 | 0.9690 | - | 0.8416 |
| core_macro_plus_stable_4h | 38 | 0.6595 | 0.1859 | 0.4490 | 0.2678 | 0.9786 | - | 0.9383 |
| core_plus_macro_plus_4h_momentum | 22 | 0.6595 | 0.1859 | 0.4466 | 0.2512 | 0.9786 | - | 0.9283 |
| full_no_technical | 121 | 0.6591 | 0.1913 | 0.4514 | 0.2595 | 0.8571 | - | 0.6781 |
| current_full_no_bull_collapse_4h | 119 | 0.6564 | 0.1872 | 0.4418 | 0.2493 | 0.9524 | - | 0.7405 |
| full_no_macro | 129 | 0.6557 | 0.1986 | 0.4526 | 0.2486 | 0.8476 | - | 0.6714 |
| current_full | 131 | 0.6547 | 0.1959 | 0.4430 | 0.2602 | 0.8524 | - | 0.7109 |
| core_plus_macro_plus_all_4h | 50 | 0.6531 | 0.1913 | 0.4478 | 0.2679 | 0.8333 | - | 0.7937 |
| full_no_cross | 120 | 0.6497 | 0.2021 | 0.4406 | 0.2609 | 0.8524 | - | 0.7267 |
| full_no_4h | 121 | 0.6478 | 0.2050 | 0.4286 | 0.2478 | 0.8762 | - | 0.7952 |
| full_no_lags | 41 | 0.6387 | 0.1993 | 0.4502 | 0.2555 | 0.9000 | - | 0.7784 |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
