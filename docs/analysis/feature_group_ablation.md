# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-04-27 17:16:33 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.5315 | 0.0060 | 0.5255 | 0.2584 | 0.4559 | - | 0.5174 |
| core_plus_macro | 10 | 0.5315 | 0.0060 | 0.5255 | 0.2571 | 0.5588 | - | 0.5896 |
| current_full_no_bull_collapse_4h | 119 | 0.5315 | 0.0060 | 0.5255 | 0.2357 | 1.0000 | - | 1.0000 |
| current_full | 131 | 0.5315 | 0.0060 | 0.5255 | 0.2325 | 1.0000 | - | 1.0000 |
| core_plus_macro_plus_all_4h | 50 | 0.4925 | 0.0330 | 0.4595 | 0.2435 | 0.9706 | - | 1.0000 |
| core_macro_plus_stable_4h | 38 | 0.4565 | 0.0691 | 0.3874 | 0.2559 | 0.9412 | - | 1.0000 |

## Notes

- Recommended profile this run: **`current_full`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
