# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-23 07:02:25 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_plus_macro | 10 | 0.3904 | 0.1111 | 0.2793 | 0.3342 | 0.2647 | 0.5714 | - |
| core_macro_plus_stable_4h | 38 | 0.3904 | 0.1111 | 0.2793 | 0.3310 | 0.5588 | 0.6131 | - |
| current_full | 131 | 0.3904 | 0.1111 | 0.2793 | 0.3219 | 0.6176 | 0.5357 | - |
| current_full_no_bull_collapse_4h | 119 | 0.3889 | 0.1096 | 0.2793 | 0.3259 | 0.5882 | 0.6131 | - |
| core_plus_macro_plus_all_4h | 50 | 0.3859 | 0.1066 | 0.2793 | 0.3397 | 0.4559 | 0.5357 | - |
| core_only | 8 | 0.3003 | 0.0210 | 0.2793 | 0.3257 | 0.1912 | 0.7143 | - |

## Notes

- Recommended profile this run: **`current_full`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
