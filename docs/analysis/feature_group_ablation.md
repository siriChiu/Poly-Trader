# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-04-24 19:10:29 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_macro_plus_stable_4h | 38 | 0.5435 | 0.0420 | 0.5015 | 0.2852 | 0.7059 | - | 0.7054 |
| core_plus_macro_plus_all_4h | 50 | 0.5435 | 0.0420 | 0.5015 | 0.2812 | 0.7647 | - | 0.7643 |
| core_only | 8 | 0.5375 | 0.0360 | 0.5015 | 0.2901 | 0.5588 | - | 0.5731 |
| core_plus_macro | 10 | 0.5375 | 0.0360 | 0.5015 | 0.2893 | 0.4706 | - | 0.4848 |
| current_full_no_bull_collapse_4h | 119 | 0.4700 | 0.0315 | 0.4384 | 0.2872 | 0.7500 | - | 0.7643 |
| current_full | 131 | 0.4580 | 0.0435 | 0.4144 | 0.2861 | 0.8088 | - | 0.8231 |

## Notes

- Recommended profile this run: **`core_plus_macro_plus_all_4h`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
