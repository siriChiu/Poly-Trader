# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-04-29 20:02:20 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.5390 | 0.1396 | 0.3994 | 0.2523 | 0.3529 | 0.0000 | 0.0858 |
| core_plus_macro | 10 | 0.5315 | 0.1321 | 0.3994 | 0.2541 | 0.3088 | 0.0000 | 0.0441 |
| core_plus_macro_plus_all_4h | 50 | 0.5105 | 0.1111 | 0.3994 | 0.2588 | 0.3382 | 0.0000 | 0.1005 |
| core_macro_plus_stable_4h | 38 | 0.4940 | 0.0946 | 0.3994 | 0.2571 | 0.3382 | 0.0000 | 0.1176 |
| current_full | 131 | 0.4580 | 0.0586 | 0.3994 | 0.2618 | 0.2941 | 0.0000 | 0.3015 |
| current_full_no_bull_collapse_4h | 119 | 0.4474 | 0.0480 | 0.3994 | 0.2598 | 0.1471 | 0.0000 | 0.2108 |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
