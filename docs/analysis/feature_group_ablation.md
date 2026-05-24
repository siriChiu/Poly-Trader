# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-24 00:03:57 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_plus_macro | 10 | 0.5255 | 0.1502 | 0.3754 | 0.2734 | 0.3824 | 0.6094 | - |
| core_only | 8 | 0.5060 | 0.1306 | 0.3754 | 0.2682 | 0.3235 | 0.5938 | - |
| current_full_no_bull_collapse_4h | 119 | 0.3889 | 0.0135 | 0.3754 | 0.2782 | 0.2941 | 0.3375 | - |
| current_full | 131 | 0.3453 | 0.0480 | 0.2973 | 0.2837 | 0.2647 | 0.2562 | - |
| core_plus_macro_plus_all_4h | 50 | 0.3438 | 0.0315 | 0.3123 | 0.2764 | 0.3529 | 0.4531 | - |
| core_macro_plus_stable_4h | 38 | 0.3288 | 0.0465 | 0.2823 | 0.2846 | 0.5294 | 0.6625 | - |

## Notes

- Recommended profile this run: **`core_plus_macro`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
