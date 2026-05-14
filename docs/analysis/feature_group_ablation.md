# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-14 04:02:06 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| current_full | 131 | 0.4099 | 0.0856 | 0.3243 | 0.3103 | 0.8382 | 1.0000 | 0.4444 |
| current_full_no_bull_collapse_4h | 119 | 0.4039 | 0.0916 | 0.3123 | 0.3073 | 0.8088 | 1.0000 | 0.3333 |
| core_only | 8 | 0.3949 | 0.1006 | 0.2943 | 0.3073 | 0.7500 | 1.0000 | 0.2222 |
| core_plus_macro | 10 | 0.3934 | 0.1021 | 0.2913 | 0.3107 | 0.7059 | 1.0000 | 0.4444 |
| core_macro_plus_stable_4h | 38 | 0.3919 | 0.1036 | 0.2883 | 0.3041 | 0.5588 | 1.0000 | 0.0000 |
| core_plus_macro_plus_all_4h | 50 | 0.3829 | 0.1126 | 0.2703 | 0.3044 | 0.6471 | 1.0000 | 0.0000 |

## Notes

- Recommended profile this run: **`current_full`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
