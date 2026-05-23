# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-23 13:14:50 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_macro_plus_stable_4h | 38 | 0.4610 | 0.1997 | 0.2613 | 0.3274 | 0.7353 | 0.7500 | - |
| core_plus_macro_plus_all_4h | 50 | 0.4414 | 0.1802 | 0.2613 | 0.3299 | 0.6471 | 0.8571 | - |
| core_plus_macro | 10 | 0.4159 | 0.1547 | 0.2613 | 0.3320 | 0.2059 | 0.5036 | - |
| current_full | 131 | 0.3949 | 0.1336 | 0.2613 | 0.3265 | 0.4265 | 0.3643 | - |
| current_full_no_bull_collapse_4h | 119 | 0.3859 | 0.1246 | 0.2613 | 0.3266 | 0.4559 | 0.4464 | - |
| core_only | 8 | 0.3544 | 0.0931 | 0.2613 | 0.3275 | 0.2353 | 0.6250 | - |

## Notes

- Recommended profile this run: **`core_macro_plus_stable_4h`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
