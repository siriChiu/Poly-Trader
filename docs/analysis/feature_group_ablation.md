# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-28 04:02:23 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_macro_plus_stable_4h | 38 | 0.6502 | 0.1426 | 0.5075 | 0.2309 | 0.8235 | 0.7000 | - |
| core_plus_macro_plus_all_4h | 50 | 0.6396 | 0.1682 | 0.4715 | 0.2314 | 0.8235 | 0.7000 | - |
| current_full | 131 | 0.5931 | 0.1877 | 0.4054 | 0.2313 | 0.9118 | 0.9500 | - |
| current_full_no_bull_collapse_4h | 119 | 0.5766 | 0.2132 | 0.3634 | 0.2326 | 0.8971 | 0.9500 | - |
| core_plus_macro | 10 | 0.5180 | 0.1727 | 0.3453 | 0.2378 | 0.5294 | 0.8500 | - |
| core_only | 8 | 0.5135 | 0.0390 | 0.4745 | 0.2513 | 0.2353 | 0.5682 | - |

## Notes

- Recommended profile this run: **`core_macro_plus_stable_4h`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
