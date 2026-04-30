# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-04-30 08:03:23 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.5090 | 0.1607 | 0.3483 | 0.2521 | 0.4265 | 0.5000 | 0.1971 |
| core_plus_macro | 10 | 0.5075 | 0.1592 | 0.3483 | 0.2573 | 0.3971 | 0.5000 | 0.1529 |
| core_plus_macro_plus_all_4h | 50 | 0.4760 | 0.1276 | 0.3483 | 0.2617 | 0.5147 | 0.0000 | 0.1441 |
| core_macro_plus_stable_4h | 38 | 0.4595 | 0.1111 | 0.3483 | 0.2617 | 0.3235 | 0.5000 | 0.1529 |
| current_full | 131 | 0.4429 | 0.0946 | 0.3483 | 0.2684 | 0.1912 | 0.5000 | 0.2588 |
| current_full_no_bull_collapse_4h | 119 | 0.4129 | 0.0646 | 0.3483 | 0.2715 | 0.1176 | 0.5000 | 0.0500 |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
