# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-25 22:03:56 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| current_full_no_bull_collapse_4h | 119 | 0.6276 | 0.2072 | 0.4204 | 0.2653 | 0.8676 | 0.9211 | - |
| core_plus_macro_plus_all_4h | 50 | 0.6171 | 0.1967 | 0.4204 | 0.2665 | 0.7353 | 0.7895 | - |
| current_full | 131 | 0.5991 | 0.1787 | 0.4204 | 0.2726 | 0.6765 | 0.8421 | - |
| core_plus_macro | 10 | 0.5075 | 0.0871 | 0.4204 | 0.2822 | 0.7206 | 0.6579 | - |
| core_macro_plus_stable_4h | 38 | 0.5045 | 0.0841 | 0.4204 | 0.2667 | 0.6912 | 0.4770 | - |
| core_only | 8 | 0.4309 | 0.0105 | 0.4204 | 0.2805 | 0.5882 | 0.7319 | - |

## Notes

- Recommended profile this run: **`current_full_no_bull_collapse_4h`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
