# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-15 17:01:22 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_plus_macro_plus_all_4h | 50 | 0.6081 | 0.0856 | 0.5225 | 0.2396 | 0.6471 | 1.0000 | 0.1000 |
| current_full_no_bull_collapse_4h | 119 | 0.6006 | 0.0961 | 0.5045 | 0.2479 | 0.8088 | 1.0000 | 0.1556 |
| current_full | 131 | 0.5976 | 0.0751 | 0.5225 | 0.2460 | 0.9118 | 1.0000 | 0.1556 |
| core_macro_plus_stable_4h | 38 | 0.5961 | 0.0976 | 0.4985 | 0.2438 | 0.8676 | 1.0000 | 0.0000 |
| core_plus_macro | 10 | 0.5571 | 0.0916 | 0.4655 | 0.2478 | 0.7059 | 1.0000 | 0.5444 |
| core_only | 8 | 0.5511 | 0.1066 | 0.4444 | 0.2546 | 0.8824 | 1.0000 | 0.5444 |

## Notes

- Recommended profile this run: **`core_plus_macro_plus_all_4h`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
