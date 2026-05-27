# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-27 06:05:45 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| current_full_no_bull_collapse_4h | 119 | 0.5210 | 0.0946 | 0.4264 | 0.2320 | 1.0000 | 1.0000 | - |
| current_full | 131 | 0.5045 | 0.1111 | 0.3934 | 0.2331 | 1.0000 | 1.0000 | - |
| core_only | 8 | 0.5015 | 0.1141 | 0.3874 | 0.2709 | 0.6029 | 0.9231 | - |
| core_plus_macro | 10 | 0.5015 | 0.1141 | 0.3874 | 0.2709 | 0.5588 | 0.9000 | - |
| core_macro_plus_stable_4h | 38 | 0.5015 | 0.1141 | 0.3874 | 0.2394 | 1.0000 | 1.0000 | - |
| core_plus_macro_plus_all_4h | 50 | 0.5015 | 0.1141 | 0.3874 | 0.2404 | 1.0000 | 1.0000 | - |

## Notes

- Recommended profile this run: **`current_full_no_bull_collapse_4h`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
