# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-17 13:02:19 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.3919 | 0.1066 | 0.2853 | 0.3079 | 0.7647 | 0.7500 | 0.8889 |
| core_plus_macro | 10 | 0.3859 | 0.1006 | 0.2853 | 0.3141 | 0.8676 | 0.9167 | 0.8889 |
| core_macro_plus_stable_4h | 38 | 0.3859 | 0.1006 | 0.2853 | 0.3293 | 0.3971 | 0.9167 | 0.0000 |
| core_plus_macro_plus_all_4h | 50 | 0.3859 | 0.1006 | 0.2853 | 0.3334 | 0.3676 | 0.7083 | 0.0000 |
| current_full_no_bull_collapse_4h | 119 | 0.3859 | 0.1006 | 0.2853 | 0.3273 | 0.6765 | 0.6310 | 0.0000 |
| current_full | 131 | 0.3844 | 0.0991 | 0.2853 | 0.3230 | 0.6324 | 0.5000 | 0.0000 |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
