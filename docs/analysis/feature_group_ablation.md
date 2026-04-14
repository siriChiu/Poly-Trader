# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **5000**
- splits: **5** (TimeSeriesSplit)
- generated_at: **2026-04-14 19:09:29 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.7551 | 0.1819 | 0.4730 | 0.2127 | 0.7167 | 0.5484 | 0.2424 |
| core_plus_4h | 18 | 0.7176 | 0.1494 | 0.4826 | 0.2544 | 0.7357 | 0.4516 | 0.2424 |
| core_plus_macro | 10 | 0.6679 | 0.1793 | 0.4094 | 0.2502 | 0.8857 | 0.6452 | 0.2576 |
| full_no_lags | 41 | 0.6007 | 0.0972 | 0.4526 | 0.2713 | 0.8690 | 0.4839 | 0.2424 |
| core_plus_technical | 18 | 0.6002 | 0.2163 | 0.3505 | 0.2729 | 0.8643 | 0.5161 | 0.2273 |
| current_full | 131 | 0.5851 | 0.1601 | 0.3193 | 0.2831 | 0.7976 | 0.6452 | 0.2879 |
| full_no_cross | 120 | 0.5832 | 0.1606 | 0.3157 | 0.2806 | 0.8071 | 0.5806 | 0.3030 |
| full_no_4h | 121 | 0.5810 | 0.1314 | 0.3818 | 0.2866 | 0.8786 | 0.7097 | 0.2727 |
| full_no_technical | 121 | 0.5808 | 0.1593 | 0.3133 | 0.2868 | 0.8071 | 0.6774 | 0.2727 |
| full_no_macro | 129 | 0.5801 | 0.1593 | 0.3109 | 0.2899 | 0.7571 | 0.6774 | 0.2879 |
| core_macro_plus_stable_4h | 38 | 0.5714 | 0.1550 | 0.3145 | 0.2912 | 0.8143 | 0.5806 | 0.3182 |
| current_full_no_bull_collapse_4h | 119 | 0.5657 | 0.1463 | 0.3361 | 0.2977 | 0.8643 | 0.6774 | 0.3030 |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
