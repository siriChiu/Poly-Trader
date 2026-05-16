# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-16 00:02:19 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_plus_macro_plus_all_4h | 50 | 0.6006 | 0.0060 | 0.5946 | 0.2388 | 0.6324 | 1.0000 | 0.4375 |
| core_only | 8 | 0.5646 | 0.0360 | 0.5285 | 0.2451 | 0.8382 | 1.0000 | 0.5375 |
| current_full_no_bull_collapse_4h | 119 | 0.5541 | 0.0526 | 0.5015 | 0.2507 | 0.5294 | 1.0000 | 0.3125 |
| current_full | 131 | 0.5541 | 0.0526 | 0.5015 | 0.2495 | 0.6324 | 1.0000 | 0.1250 |
| core_macro_plus_stable_4h | 38 | 0.5330 | 0.0766 | 0.4565 | 0.2416 | 0.4706 | 1.0000 | 0.0000 |
| core_plus_macro | 10 | 0.5285 | 0.0871 | 0.4414 | 0.2413 | 0.6618 | 0.5714 | 0.4375 |

## Notes

- Recommended profile this run: **`core_plus_macro_plus_all_4h`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
