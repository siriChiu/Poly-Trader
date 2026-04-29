# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-04-29 09:03:13 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_plus_macro | 10 | 0.5435 | 0.1231 | 0.4204 | 0.2578 | 0.3235 | - | 0.0973 |
| core_only | 8 | 0.4985 | 0.0781 | 0.4204 | 0.2570 | 0.3382 | - | 0.1505 |
| core_macro_plus_stable_4h | 38 | 0.4880 | 0.0676 | 0.4204 | 0.2635 | 0.2647 | - | 0.1414 |
| current_full_no_bull_collapse_4h | 119 | 0.4730 | 0.0526 | 0.4204 | 0.2598 | 0.1471 | - | 0.2771 |
| core_plus_macro_plus_all_4h | 50 | 0.4700 | 0.0495 | 0.4204 | 0.2693 | 0.2500 | - | 0.1029 |
| current_full | 131 | 0.4474 | 0.0270 | 0.4204 | 0.2676 | 0.1029 | - | 0.2002 |

## Notes

- Recommended profile this run: **`core_plus_macro`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
