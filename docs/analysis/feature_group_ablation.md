# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-18 20:03:38 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_plus_macro_plus_all_4h | 50 | 0.3514 | 0.0180 | 0.3333 | 0.3391 | 0.5294 | 0.6190 | 0.0000 |
| core_macro_plus_stable_4h | 38 | 0.3498 | 0.0165 | 0.3333 | 0.3291 | 0.4265 | 0.8333 | 0.0000 |
| current_full_no_bull_collapse_4h | 119 | 0.3258 | 0.0075 | 0.3183 | 0.3118 | 0.7794 | 0.9286 | 0.0000 |
| current_full | 131 | 0.3213 | 0.0210 | 0.3003 | 0.3199 | 0.8824 | 0.9524 | 0.0000 |
| core_only | 8 | 0.2763 | 0.0571 | 0.2192 | 0.3114 | 0.7353 | 0.7381 | 0.8889 |
| core_plus_macro | 10 | 0.2763 | 0.0571 | 0.2192 | 0.3203 | 0.5882 | 0.9048 | 0.8889 |

## Notes

- Recommended profile this run: **`core_plus_macro_plus_all_4h`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
