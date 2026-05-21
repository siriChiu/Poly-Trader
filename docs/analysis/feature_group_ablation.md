# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-21 12:14:20 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_plus_macro_plus_all_4h | 50 | 0.5495 | 0.0601 | 0.4895 | 0.2719 | 0.2206 | 0.1935 | 0.0000 |
| core_only | 8 | 0.5165 | 0.0270 | 0.4895 | 0.2665 | 0.5588 | 0.3441 | 0.0000 |
| current_full_no_bull_collapse_4h | 119 | 0.5150 | 0.0255 | 0.4895 | 0.2578 | 0.5441 | 0.6935 | 0.0000 |
| current_full | 131 | 0.4895 | 0.0000 | 0.4895 | 0.2599 | 0.5294 | 0.7419 | 0.0000 |
| core_plus_macro | 10 | 0.4820 | 0.0075 | 0.4745 | 0.2627 | 0.7059 | 0.7581 | 0.0000 |
| core_macro_plus_stable_4h | 38 | 0.4595 | 0.0300 | 0.4294 | 0.2704 | 0.1912 | 0.2330 | 0.0000 |

## Notes

- Recommended profile this run: **`core_plus_macro_plus_all_4h`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
