# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-26 01:05:34 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| current_full_no_bull_collapse_4h | 119 | 0.5465 | 0.1261 | 0.4204 | 0.2842 | 0.9265 | 1.0000 | - |
| current_full | 131 | 0.4865 | 0.0661 | 0.4204 | 0.2840 | 0.8824 | 0.8333 | - |
| core_macro_plus_stable_4h | 38 | 0.4805 | 0.0601 | 0.4204 | 0.2766 | 0.8382 | 0.9167 | - |
| core_plus_macro | 10 | 0.4790 | 0.0586 | 0.4204 | 0.2828 | 0.5588 | 0.6146 | - |
| core_plus_macro_plus_all_4h | 50 | 0.4790 | 0.0586 | 0.4204 | 0.2901 | 0.8382 | 0.8333 | - |
| core_only | 8 | 0.4084 | 0.0120 | 0.3964 | 0.2876 | 0.5441 | 0.9132 | - |

## Notes

- Recommended profile this run: **`current_full_no_bull_collapse_4h`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
