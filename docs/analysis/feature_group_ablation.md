# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-24 17:08:11 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_plus_macro | 10 | 0.5405 | 0.0841 | 0.4565 | 0.2515 | 0.3971 | 0.6286 | - |
| core_only | 8 | 0.4399 | 0.0015 | 0.4384 | 0.2526 | 0.3382 | 0.6286 | - |
| core_plus_macro_plus_all_4h | 50 | 0.4384 | 0.0030 | 0.4354 | 0.2594 | 0.5882 | 0.7333 | - |
| core_macro_plus_stable_4h | 38 | 0.4309 | 0.0135 | 0.4174 | 0.2599 | 0.4265 | 0.3857 | - |
| current_full | 131 | 0.4294 | 0.0270 | 0.4024 | 0.2682 | 0.6471 | 0.6571 | - |
| current_full_no_bull_collapse_4h | 119 | 0.4249 | 0.0315 | 0.3934 | 0.2642 | 0.8824 | 0.8833 | - |

## Notes

- Recommended profile this run: **`core_plus_macro`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
