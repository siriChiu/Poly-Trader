# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-16 06:02:36 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_plus_macro | 10 | 0.5225 | 0.1261 | 0.3964 | 0.2493 | 0.6176 | 1.0000 | 0.9286 |
| current_full_no_bull_collapse_4h | 119 | 0.5180 | 0.0435 | 0.4745 | 0.2621 | 0.6618 | 0.5000 | 0.3571 |
| current_full | 131 | 0.5105 | 0.0541 | 0.4565 | 0.2562 | 0.7647 | 1.0000 | 0.3571 |
| core_only | 8 | 0.4850 | 0.0495 | 0.4354 | 0.2533 | 0.7059 | 1.0000 | 0.4429 |
| core_plus_macro_plus_all_4h | 50 | 0.4745 | 0.0901 | 0.3844 | 0.2483 | 0.5735 | 0.8000 | 0.0000 |
| core_macro_plus_stable_4h | 38 | 0.4459 | 0.1186 | 0.3273 | 0.2557 | 0.6471 | 0.8000 | 0.0000 |

## Notes

- Recommended profile this run: **`core_plus_macro`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
