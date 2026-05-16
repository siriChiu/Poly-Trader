# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-16 16:02:07 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_plus_macro | 10 | 0.4369 | 0.0916 | 0.3453 | 0.2771 | 0.4853 | 1.0000 | 0.5000 |
| core_plus_macro_plus_all_4h | 50 | 0.4249 | 0.0706 | 0.3544 | 0.2961 | 0.1618 | 0.5000 | 0.0833 |
| current_full_no_bull_collapse_4h | 119 | 0.4249 | 0.0706 | 0.3544 | 0.3006 | 0.3382 | 0.9286 | 0.0833 |
| core_only | 8 | 0.4174 | 0.0721 | 0.3453 | 0.2801 | 0.6029 | 1.0000 | 0.5000 |
| core_macro_plus_stable_4h | 38 | 0.4174 | 0.0781 | 0.3393 | 0.3041 | 0.3676 | 0.5000 | 0.0833 |
| current_full | 131 | 0.4084 | 0.0871 | 0.3213 | 0.2976 | 0.3971 | 1.0000 | 0.0833 |

## Notes

- Recommended profile this run: **`core_plus_macro`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
