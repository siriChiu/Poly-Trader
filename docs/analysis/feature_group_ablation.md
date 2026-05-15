# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-15 09:02:26 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_plus_macro | 10 | 0.5556 | 0.1111 | 0.4444 | 0.2610 | 0.8382 | 1.0000 | 0.5444 |
| core_plus_macro_plus_all_4h | 50 | 0.5060 | 0.0616 | 0.4444 | 0.2517 | 0.7794 | 1.0000 | 0.1000 |
| core_macro_plus_stable_4h | 38 | 0.4700 | 0.0255 | 0.4444 | 0.2562 | 0.8235 | 1.0000 | 0.0000 |
| core_only | 8 | 0.4354 | 0.0090 | 0.4264 | 0.2707 | 0.8235 | 1.0000 | 0.5444 |
| current_full_no_bull_collapse_4h | 119 | 0.4159 | 0.0285 | 0.3874 | 0.2690 | 0.7353 | 1.0000 | 0.1000 |
| current_full | 131 | 0.4084 | 0.0360 | 0.3724 | 0.2694 | 0.6471 | 1.0000 | 0.1000 |

## Notes

- Recommended profile this run: **`core_plus_macro`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
