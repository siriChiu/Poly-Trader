# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-17 17:02:14 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.3619 | 0.1156 | 0.2462 | 0.3261 | 0.7794 | 0.8929 | 0.8889 |
| core_plus_macro | 10 | 0.3468 | 0.1006 | 0.2462 | 0.3311 | 0.7941 | 0.8571 | 0.8889 |
| core_macro_plus_stable_4h | 38 | 0.3468 | 0.1006 | 0.2462 | 0.3460 | 0.6029 | 0.8929 | 0.0000 |
| core_plus_macro_plus_all_4h | 50 | 0.3468 | 0.1006 | 0.2462 | 0.3505 | 0.4118 | 0.9286 | 0.0000 |
| current_full_no_bull_collapse_4h | 119 | 0.3468 | 0.1006 | 0.2462 | 0.3449 | 0.8088 | 0.7143 | 0.0000 |
| current_full | 131 | 0.3468 | 0.1006 | 0.2462 | 0.3464 | 0.6618 | 0.5714 | 0.0000 |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
