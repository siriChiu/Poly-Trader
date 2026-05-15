# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-15 04:02:12 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_macro_plus_stable_4h | 38 | 0.4730 | 0.0285 | 0.4444 | 0.2775 | 0.7353 | 1.0000 | 0.0000 |
| core_plus_macro_plus_all_4h | 50 | 0.4610 | 0.0165 | 0.4444 | 0.2778 | 0.7941 | 1.0000 | 0.2667 |
| core_plus_macro | 10 | 0.4189 | 0.0255 | 0.3934 | 0.2795 | 0.7647 | 1.0000 | 0.5444 |
| core_only | 8 | 0.4099 | 0.0345 | 0.3754 | 0.2883 | 0.8971 | 1.0000 | 0.5444 |
| current_full | 131 | 0.4054 | 0.0390 | 0.3664 | 0.2849 | 0.8235 | 1.0000 | 0.2111 |
| current_full_no_bull_collapse_4h | 119 | 0.3739 | 0.0706 | 0.3033 | 0.2854 | 0.7353 | 1.0000 | 0.1000 |

## Notes

- Recommended profile this run: **`core_macro_plus_stable_4h`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
