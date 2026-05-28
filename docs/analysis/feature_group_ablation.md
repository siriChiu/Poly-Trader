# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-28 08:11:35 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_macro_plus_stable_4h | 38 | 0.5691 | 0.2087 | 0.3604 | 0.2548 | 0.6029 | 0.6818 | - |
| current_full_no_bull_collapse_4h | 119 | 0.5691 | 0.2087 | 0.3604 | 0.2488 | 0.5441 | 0.8636 | - |
| core_plus_macro_plus_all_4h | 50 | 0.5571 | 0.2177 | 0.3393 | 0.2521 | 0.5882 | 0.5909 | - |
| current_full | 131 | 0.5450 | 0.1847 | 0.3604 | 0.2515 | 0.5882 | 0.6818 | - |
| core_plus_macro | 10 | 0.5090 | 0.1486 | 0.3604 | 0.2465 | 0.5294 | 0.8636 | - |
| core_only | 8 | 0.4384 | 0.0901 | 0.3483 | 0.2584 | 0.1618 | 0.3636 | - |

## Notes

- Recommended profile this run: **`current_full_no_bull_collapse_4h`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
