# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **5000**
- splits: **5** (TimeSeriesSplit)
- generated_at: **2026-04-14 18:16:40 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.7433 | 0.1877 | 0.4538 | 0.2112 | 0.6929 | 0.4516 | 0.3056 |
| core_plus_4h | 18 | 0.7023 | 0.1423 | 0.4550 | 0.2550 | 0.7357 | 0.5161 | 0.2500 |
| core_plus_macro | 10 | 0.6867 | 0.1705 | 0.4370 | 0.2400 | 0.8929 | 0.6452 | 0.3333 |
| core_plus_technical | 18 | 0.6240 | 0.2156 | 0.3553 | 0.2583 | 0.9190 | 0.7742 | 0.2639 |
| full_no_lags | 41 | 0.5849 | 0.1020 | 0.4550 | 0.2809 | 0.9048 | 0.6129 | 0.2500 |
| full_no_technical | 121 | 0.5719 | 0.1415 | 0.3685 | 0.2981 | 0.9071 | 0.7742 | 0.3333 |
| core_macro_plus_stable_4h | 38 | 0.5678 | 0.1415 | 0.3697 | 0.3022 | 0.7548 | 0.5484 | 0.2222 |
| current_full | 131 | 0.5527 | 0.1466 | 0.3830 | 0.2953 | 0.7929 | 0.6774 | 0.3056 |
| full_no_macro | 129 | 0.5465 | 0.1496 | 0.3806 | 0.3013 | 0.8214 | 0.7097 | 0.3056 |
| full_no_cross | 120 | 0.5424 | 0.1454 | 0.3709 | 0.3016 | 0.7976 | 0.6774 | 0.3194 |
| full_no_4h | 121 | 0.5390 | 0.1367 | 0.3866 | 0.3008 | 0.8738 | 0.7419 | 0.3194 |
| current_full_no_bull_collapse_4h | 119 | 0.5212 | 0.1334 | 0.3697 | 0.3214 | 0.8190 | 0.6129 | 0.3056 |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
