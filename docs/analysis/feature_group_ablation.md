# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-24 06:26:37 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_plus_macro_plus_all_4h | 50 | 0.5661 | 0.0495 | 0.5165 | 0.2469 | 0.5441 | 0.6176 | - |
| core_plus_macro | 10 | 0.5285 | 0.0721 | 0.4565 | 0.2496 | 0.5588 | 0.5000 | - |
| core_only | 8 | 0.5045 | 0.0480 | 0.4565 | 0.2496 | 0.2500 | 0.4618 | - |
| core_macro_plus_stable_4h | 38 | 0.4970 | 0.0375 | 0.4595 | 0.2507 | 0.6324 | 0.6912 | - |
| current_full | 131 | 0.4114 | 0.0511 | 0.3604 | 0.2639 | 0.4118 | 0.5971 | - |
| current_full_no_bull_collapse_4h | 119 | 0.4084 | 0.0480 | 0.3604 | 0.2627 | 0.4559 | 0.6471 | - |

## Notes

- Recommended profile this run: **`core_plus_macro_plus_all_4h`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
