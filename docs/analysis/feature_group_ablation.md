# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-26 17:20:08 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| current_full_no_bull_collapse_4h | 119 | 0.5616 | 0.0601 | 0.5015 | 0.2667 | 0.9706 | 1.0000 | - |
| current_full | 131 | 0.5616 | 0.0601 | 0.5015 | 0.2763 | 0.8529 | 0.8542 | - |
| core_macro_plus_stable_4h | 38 | 0.5601 | 0.0586 | 0.5015 | 0.2713 | 0.8382 | 0.8646 | - |
| core_plus_macro_plus_all_4h | 50 | 0.5601 | 0.0586 | 0.5015 | 0.2702 | 0.6765 | 0.6042 | - |
| core_only | 8 | 0.4354 | 0.0661 | 0.3694 | 0.2926 | 0.7206 | 0.9688 | - |
| core_plus_macro | 10 | 0.4354 | 0.0661 | 0.3694 | 0.2900 | 0.6765 | 0.8438 | - |

## Notes

- Recommended profile this run: **`current_full_no_bull_collapse_4h`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
