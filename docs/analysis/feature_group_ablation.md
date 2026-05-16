# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-16 22:03:51 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| current_full_no_bull_collapse_4h | 119 | 0.4474 | 0.0541 | 0.3934 | 0.3028 | 0.5588 | 1.0000 | 0.2143 |
| core_plus_macro | 10 | 0.4444 | 0.1051 | 0.3393 | 0.2835 | 0.6176 | 1.0000 | 0.5000 |
| current_full | 131 | 0.4429 | 0.0586 | 0.3844 | 0.2958 | 0.3971 | 1.0000 | 0.0000 |
| core_only | 8 | 0.4144 | 0.0751 | 0.3393 | 0.2827 | 0.7353 | 0.7500 | 0.5000 |
| core_plus_macro_plus_all_4h | 50 | 0.4129 | 0.0766 | 0.3363 | 0.3013 | 0.0882 | 0.5000 | 0.0000 |
| core_macro_plus_stable_4h | 38 | 0.4084 | 0.0811 | 0.3273 | 0.2998 | 0.0882 | 0.5000 | 0.0000 |

## Notes

- Recommended profile this run: **`current_full_no_bull_collapse_4h`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
