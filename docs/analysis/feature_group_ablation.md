# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **5000**
- splits: **5** (TimeSeriesSplit)
- generated_at: **2026-04-14 17:19:13 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.7465 | 0.1830 | 0.4538 | 0.2105 | 0.6881 | 0.4516 | 0.2933 |
| core_plus_macro | 10 | 0.6848 | 0.1697 | 0.4490 | 0.2318 | 0.9071 | 0.6129 | 0.3067 |
| core_plus_4h | 18 | 0.6639 | 0.1385 | 0.4550 | 0.2564 | 0.7452 | 0.4839 | 0.2533 |
| core_plus_technical | 18 | 0.6372 | 0.2085 | 0.3709 | 0.2549 | 0.8476 | 0.6129 | 0.2400 |
| full_no_technical | 121 | 0.5870 | 0.1474 | 0.3842 | 0.2936 | 0.8929 | 0.6774 | 0.3067 |
| full_no_lags | 41 | 0.5794 | 0.1150 | 0.4550 | 0.2846 | 0.8429 | 0.5484 | 0.2533 |
| core_macro_plus_stable_4h | 38 | 0.5731 | 0.1396 | 0.3842 | 0.3011 | 0.7476 | 0.5161 | 0.2267 |
| full_no_macro | 129 | 0.5637 | 0.1471 | 0.3854 | 0.2952 | 0.9095 | 0.6452 | 0.3067 |
| current_full | 131 | 0.5630 | 0.1475 | 0.3854 | 0.2933 | 0.8667 | 0.6129 | 0.3067 |
| full_no_4h | 121 | 0.5556 | 0.1382 | 0.3866 | 0.2936 | 0.8714 | 0.6774 | 0.3200 |
| full_no_cross | 120 | 0.5556 | 0.1425 | 0.3866 | 0.3035 | 0.8405 | 0.6774 | 0.3067 |
| current_full_no_bull_collapse_4h | 119 | 0.5306 | 0.1321 | 0.3854 | 0.3181 | 0.9024 | 0.6129 | 0.2933 |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
