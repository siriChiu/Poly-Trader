# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-25 10:04:16 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_plus_macro_plus_all_4h | 50 | 0.6441 | 0.1787 | 0.4655 | 0.2532 | 0.7206 | 0.7609 | - |
| core_macro_plus_stable_4h | 38 | 0.6366 | 0.1712 | 0.4655 | 0.2562 | 0.7500 | 0.7609 | - |
| current_full | 131 | 0.5871 | 0.1216 | 0.4655 | 0.2563 | 0.8971 | 0.9130 | - |
| current_full_no_bull_collapse_4h | 119 | 0.5766 | 0.1111 | 0.4655 | 0.2576 | 0.9118 | 0.9130 | - |
| core_plus_macro | 10 | 0.4790 | 0.0135 | 0.4655 | 0.2677 | 0.6912 | 0.7323 | - |
| core_only | 8 | 0.4655 | 0.0000 | 0.4655 | 0.2644 | 0.6324 | 0.6957 | - |

## Notes

- Recommended profile this run: **`core_plus_macro_plus_all_4h`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
