# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-25 03:07:38 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_macro_plus_stable_4h | 38 | 0.5886 | 0.1261 | 0.4625 | 0.2504 | 0.7794 | 0.7692 | - |
| core_plus_macro_plus_all_4h | 50 | 0.5886 | 0.1261 | 0.4625 | 0.2536 | 0.5147 | 0.4183 | - |
| core_plus_macro | 10 | 0.5526 | 0.0901 | 0.4625 | 0.2546 | 0.6029 | 0.7500 | - |
| current_full | 131 | 0.5195 | 0.0631 | 0.4565 | 0.2560 | 0.8235 | 0.7885 | - |
| core_only | 8 | 0.5060 | 0.0435 | 0.4625 | 0.2539 | 0.4706 | 0.6803 | - |
| current_full_no_bull_collapse_4h | 119 | 0.4865 | 0.0240 | 0.4625 | 0.2553 | 0.9412 | 0.9231 | - |

## Notes

- Recommended profile this run: **`core_macro_plus_stable_4h`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
