# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-24 03:01:54 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.5165 | 0.0961 | 0.4204 | 0.2550 | 0.3824 | 0.6818 | - |
| core_plus_macro | 10 | 0.5075 | 0.0841 | 0.4234 | 0.2562 | 0.5147 | 0.5864 | - |
| core_plus_macro_plus_all_4h | 50 | 0.4294 | 0.0030 | 0.4264 | 0.2585 | 0.4118 | 0.6470 | - |
| current_full | 131 | 0.3949 | 0.0375 | 0.3574 | 0.2717 | 0.4118 | 0.6576 | - |
| current_full_no_bull_collapse_4h | 119 | 0.3949 | 0.0345 | 0.3604 | 0.2727 | 0.5000 | 0.5773 | - |
| core_macro_plus_stable_4h | 38 | 0.3784 | 0.0541 | 0.3243 | 0.2639 | 0.4265 | 0.4970 | - |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
