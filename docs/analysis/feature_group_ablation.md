# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **5000**
- splits: **5** (TimeSeriesSplit)
- generated_at: **2026-04-18 18:31:29 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.7597 | 0.1437 | 0.5750 | 0.1967 | 0.8048 | - | 0.6667 |
| core_plus_macro_plus_all_4h | 50 | 0.7297 | 0.1245 | 0.5594 | 0.2130 | 0.9333 | - | 0.7781 |
| current_full | 131 | 0.7263 | 0.1615 | 0.5138 | 0.2038 | 0.9262 | - | 0.6670 |
| full_no_macro | 129 | 0.7220 | 0.1628 | 0.5378 | 0.2035 | 0.9238 | - | 0.6646 |
| core_plus_macro_plus_4h_structure_shift | 22 | 0.7174 | 0.1471 | 0.5498 | 0.2044 | 0.9810 | - | 0.8000 |
| full_no_cross | 120 | 0.7140 | 0.1593 | 0.5234 | 0.2099 | 0.9286 | - | 0.7313 |
| full_no_4h | 121 | 0.7136 | 0.1822 | 0.4262 | 0.2038 | 0.9024 | - | 0.6648 |
| full_no_technical | 121 | 0.7116 | 0.1760 | 0.4766 | 0.2087 | 0.9190 | - | 0.6622 |
| current_full_no_bull_collapse_4h | 119 | 0.7078 | 0.1505 | 0.5918 | 0.1992 | 0.9262 | - | 0.6202 |
| core_plus_4h | 18 | 0.6888 | 0.1843 | 0.4886 | 0.2456 | 0.8095 | - | 0.6426 |
| core_plus_macro | 10 | 0.6816 | 0.1597 | 0.5294 | 0.2275 | 0.9429 | - | 0.7285 |
| core_plus_macro_plus_4h_momentum | 22 | 0.6804 | 0.1503 | 0.5282 | 0.2294 | 0.9310 | - | 0.6844 |
| core_plus_technical | 18 | 0.6727 | 0.1737 | 0.5378 | 0.2363 | 0.8286 | - | 0.5390 |
| core_macro_plus_stable_4h | 38 | 0.6699 | 0.1536 | 0.5030 | 0.2296 | 0.9333 | - | 0.6770 |
| full_no_lags | 41 | 0.6567 | 0.1863 | 0.4742 | 0.2297 | 0.9381 | - | 0.6336 |
| core_plus_macro_plus_4h_trend | 22 | 0.6355 | 0.1731 | 0.4754 | 0.2430 | 0.9643 | - | 0.7533 |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
