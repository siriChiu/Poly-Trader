# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-22 16:11:34 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.4565 | 0.1171 | 0.3393 | 0.3228 | 0.3676 | 0.3505 | - |
| core_plus_macro | 10 | 0.3799 | 0.0405 | 0.3393 | 0.3276 | 0.4412 | 0.3768 | - |
| core_plus_macro_plus_all_4h | 50 | 0.3724 | 0.0330 | 0.3393 | 0.3314 | 0.3382 | 0.3995 | - |
| core_macro_plus_stable_4h | 38 | 0.3709 | 0.0315 | 0.3393 | 0.3288 | 0.3824 | 0.4258 | - |
| current_full_no_bull_collapse_4h | 119 | 0.3243 | 0.0150 | 0.3093 | 0.3426 | 0.5147 | 0.4067 | - |
| current_full | 131 | 0.3228 | 0.0165 | 0.3063 | 0.3405 | 0.5294 | 0.4031 | - |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
