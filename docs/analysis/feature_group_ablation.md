# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-24 12:29:54 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_plus_macro | 10 | 0.4985 | 0.0420 | 0.4565 | 0.2541 | 0.2206 | 0.5885 | - |
| core_macro_plus_stable_4h | 38 | 0.4219 | 0.0556 | 0.3664 | 0.2625 | 0.5000 | 0.6042 | - |
| current_full_no_bull_collapse_4h | 119 | 0.4099 | 0.0435 | 0.3664 | 0.2780 | 0.6029 | 0.7812 | - |
| current_full | 131 | 0.4084 | 0.0420 | 0.3664 | 0.2746 | 0.6471 | 0.8125 | - |
| core_plus_macro_plus_all_4h | 50 | 0.3874 | 0.0360 | 0.3514 | 0.2640 | 0.3382 | 0.5729 | - |
| core_only | 8 | 0.3664 | 0.0300 | 0.3363 | 0.2568 | 0.1618 | 0.5729 | - |

## Notes

- Recommended profile this run: **`core_plus_macro`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
