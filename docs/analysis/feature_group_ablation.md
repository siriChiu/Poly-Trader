# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-17 09:01:57 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_plus_macro | 10 | 0.4084 | 0.0781 | 0.3303 | 0.2941 | 0.7353 | 0.6039 | 0.8889 |
| core_macro_plus_stable_4h | 38 | 0.4084 | 0.0781 | 0.3303 | 0.3068 | 0.2059 | 0.7273 | 0.0000 |
| core_plus_macro_plus_all_4h | 50 | 0.4069 | 0.0796 | 0.3273 | 0.3107 | 0.2647 | 0.9091 | 0.0000 |
| core_only | 8 | 0.3919 | 0.0616 | 0.3303 | 0.2920 | 0.6471 | 0.7273 | 0.5556 |
| current_full | 131 | 0.3589 | 0.0495 | 0.3093 | 0.3106 | 0.6324 | 0.5260 | 0.8889 |
| current_full_no_bull_collapse_4h | 119 | 0.3438 | 0.0375 | 0.3063 | 0.3081 | 0.5441 | 0.4805 | 0.8889 |

## Notes

- Recommended profile this run: **`core_plus_macro`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
