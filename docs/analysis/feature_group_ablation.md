# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-23 20:02:04 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.4925 | 0.1592 | 0.3333 | 0.2833 | 0.2794 | 0.5333 | - |
| core_plus_macro | 10 | 0.4895 | 0.1562 | 0.3333 | 0.2800 | 0.2794 | 0.4833 | - |
| core_plus_macro_plus_all_4h | 50 | 0.3964 | 0.0631 | 0.3333 | 0.2922 | 0.3088 | 0.5500 | - |
| current_full_no_bull_collapse_4h | 119 | 0.3904 | 0.0571 | 0.3333 | 0.2843 | 0.3971 | 0.4000 | - |
| current_full | 131 | 0.3514 | 0.0180 | 0.3333 | 0.2864 | 0.2941 | 0.3500 | - |
| core_macro_plus_stable_4h | 38 | 0.3063 | 0.0270 | 0.2793 | 0.2936 | 0.5441 | 0.7167 | - |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
