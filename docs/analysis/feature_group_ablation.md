# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-24 23:18:00 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_plus_macro | 10 | 0.5691 | 0.0946 | 0.4745 | 0.2499 | 0.5735 | 0.7407 | - |
| core_plus_macro_plus_all_4h | 50 | 0.4955 | 0.0390 | 0.4565 | 0.2581 | 0.4412 | 0.4653 | - |
| current_full | 131 | 0.4910 | 0.0255 | 0.4655 | 0.2570 | 0.6912 | 0.6852 | - |
| core_only | 8 | 0.4835 | 0.0450 | 0.4384 | 0.2516 | 0.4706 | 0.7407 | - |
| current_full_no_bull_collapse_4h | 119 | 0.4730 | 0.0075 | 0.4655 | 0.2575 | 0.8971 | 0.8889 | - |
| core_macro_plus_stable_4h | 38 | 0.4670 | 0.0075 | 0.4595 | 0.2559 | 0.6324 | 0.5972 | - |

## Notes

- Recommended profile this run: **`core_plus_macro`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
