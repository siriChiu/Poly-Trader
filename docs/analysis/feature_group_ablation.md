# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-21 22:11:38 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_plus_macro_plus_all_4h | 50 | 0.5736 | 0.1231 | 0.4505 | 0.2890 | 0.3235 | 0.5093 | - |
| core_macro_plus_stable_4h | 38 | 0.5270 | 0.0766 | 0.4505 | 0.2908 | 0.4265 | 0.6720 | - |
| core_only | 8 | 0.4970 | 0.0465 | 0.4505 | 0.2949 | 0.3235 | 0.2566 | - |
| core_plus_macro | 10 | 0.4865 | 0.0360 | 0.4505 | 0.2923 | 0.6912 | 0.7037 | - |
| current_full | 131 | 0.4610 | 0.0105 | 0.4505 | 0.2953 | 0.1765 | 0.4193 | - |
| current_full_no_bull_collapse_4h | 119 | 0.4474 | 0.0030 | 0.4444 | 0.2960 | 0.2059 | 0.4550 | - |

## Notes

- Recommended profile this run: **`core_plus_macro_plus_all_4h`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
