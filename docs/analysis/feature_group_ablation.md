# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-13 21:02:17 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| current_full | 131 | 0.3994 | 0.1171 | 0.2823 | 0.3093 | 0.7500 | 1.0000 | 0.3333 |
| core_only | 8 | 0.3949 | 0.1216 | 0.2733 | 0.3058 | 0.8529 | 1.0000 | 0.3222 |
| current_full_no_bull_collapse_4h | 119 | 0.3949 | 0.1216 | 0.2733 | 0.3076 | 0.8382 | 1.0000 | 0.2111 |
| core_plus_macro | 10 | 0.3934 | 0.1231 | 0.2703 | 0.3082 | 0.8088 | 1.0000 | 0.5444 |
| core_macro_plus_stable_4h | 38 | 0.3934 | 0.1231 | 0.2703 | 0.3005 | 0.6029 | 1.0000 | 0.1000 |
| core_plus_macro_plus_all_4h | 50 | 0.3934 | 0.1231 | 0.2703 | 0.3049 | 0.6324 | 1.0000 | 0.1556 |

## Notes

- Recommended profile this run: **`current_full`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
