# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **5000**
- splits: **5** (TimeSeriesSplit)
- generated_at: **2026-04-14 18:41:58 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.7469 | 0.1847 | 0.4514 | 0.2147 | 0.6833 | 0.4839 | 0.3188 |
| core_plus_4h | 18 | 0.7210 | 0.1703 | 0.4562 | 0.2545 | 0.7000 | 0.5161 | 0.2464 |
| core_plus_macro | 10 | 0.6629 | 0.1836 | 0.4094 | 0.2501 | 0.8976 | 0.6452 | 0.3333 |
| core_plus_technical | 18 | 0.6091 | 0.2175 | 0.3433 | 0.2726 | 0.9143 | 0.6129 | 0.2609 |
| full_no_lags | 41 | 0.5854 | 0.0899 | 0.4562 | 0.2855 | 0.8571 | 0.4839 | 0.2464 |
| current_full | 131 | 0.5851 | 0.1401 | 0.3854 | 0.2893 | 0.8619 | 0.6452 | 0.3043 |
| full_no_technical | 121 | 0.5784 | 0.1532 | 0.3421 | 0.2935 | 0.8881 | 0.6452 | 0.3188 |
| full_no_macro | 129 | 0.5678 | 0.1500 | 0.3457 | 0.2954 | 0.8095 | 0.7097 | 0.3043 |
| core_macro_plus_stable_4h | 38 | 0.5671 | 0.1501 | 0.3385 | 0.3033 | 0.7643 | 0.5161 | 0.3188 |
| full_no_cross | 120 | 0.5657 | 0.1383 | 0.3842 | 0.2974 | 0.7976 | 0.5806 | 0.3043 |
| full_no_4h | 121 | 0.5484 | 0.1137 | 0.4166 | 0.3003 | 0.8738 | 0.6774 | 0.3043 |
| current_full_no_bull_collapse_4h | 119 | 0.5342 | 0.1200 | 0.4022 | 0.3144 | 0.8333 | 0.5484 | 0.3043 |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
