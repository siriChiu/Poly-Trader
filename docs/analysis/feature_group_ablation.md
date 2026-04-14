# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **5000**
- splits: **5** (TimeSeriesSplit)
- generated_at: **2026-04-14 15:50:38 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.7443 | 0.1829 | 0.4538 | 0.2100 | 0.6833 | 0.4516 | 0.2949 |
| core_plus_macro | 10 | 0.6845 | 0.1697 | 0.4502 | 0.2332 | 0.9119 | 0.5806 | 0.3077 |
| core_plus_4h | 18 | 0.6727 | 0.1332 | 0.4550 | 0.2573 | 0.7524 | 0.4516 | 0.2564 |
| core_plus_technical | 18 | 0.6435 | 0.2046 | 0.3854 | 0.2524 | 0.8143 | 0.6129 | 0.2436 |
| full_no_technical | 121 | 0.6017 | 0.1538 | 0.3890 | 0.2864 | 0.8976 | 0.7419 | 0.3205 |
| core_macro_plus_stable_4h | 38 | 0.5796 | 0.1407 | 0.3890 | 0.2985 | 0.7476 | 0.5484 | 0.2308 |
| full_no_macro | 129 | 0.5640 | 0.1568 | 0.3878 | 0.3035 | 0.8857 | 0.6452 | 0.3077 |
| full_no_cross | 120 | 0.5618 | 0.1472 | 0.3902 | 0.2982 | 0.8929 | 0.6129 | 0.3077 |
| full_no_lags | 41 | 0.5594 | 0.1278 | 0.4442 | 0.2895 | 0.8667 | 0.4839 | 0.2564 |
| full_no_4h | 121 | 0.5570 | 0.1407 | 0.3974 | 0.2886 | 0.9238 | 0.7742 | 0.3205 |
| current_full | 131 | 0.5570 | 0.1452 | 0.3902 | 0.3028 | 0.8595 | 0.6129 | 0.3077 |
| current_full_no_bull_collapse_4h | 119 | 0.5409 | 0.1336 | 0.3914 | 0.3147 | 0.8833 | 0.7097 | 0.2949 |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
