# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **5000**
- splits: **5** (TimeSeriesSplit)
- generated_at: **2026-04-18 14:34:43 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.7806 | 0.1603 | 0.5438 | 0.1904 | 0.7476 | - | 0.6667 |
| core_plus_4h | 18 | 0.6756 | 0.1551 | 0.4610 | 0.2684 | 0.7857 | - | 0.7213 |
| core_plus_technical | 18 | 0.6336 | 0.1875 | 0.4538 | 0.2667 | 0.8333 | - | 0.5365 |
| core_plus_macro | 10 | 0.6329 | 0.1848 | 0.4274 | 0.2615 | 0.9548 | - | 0.6982 |
| full_no_lags | 41 | 0.6127 | 0.1679 | 0.3433 | 0.2703 | 0.9238 | - | 0.6744 |
| full_no_4h | 121 | 0.6019 | 0.1146 | 0.4418 | 0.2531 | 0.9571 | - | 0.6928 |
| core_plus_macro_plus_4h_structure_shift | 22 | 0.5810 | 0.1331 | 0.3349 | 0.2487 | 0.9952 | - | 0.7649 |
| core_plus_macro_plus_4h_momentum | 22 | 0.5515 | 0.1382 | 0.3613 | 0.2761 | 0.9810 | - | 0.7413 |
| core_plus_macro_plus_4h_trend | 22 | 0.5496 | 0.1142 | 0.4022 | 0.2878 | 0.9929 | - | 0.6776 |
| current_full_no_bull_collapse_4h | 119 | 0.5431 | 0.1147 | 0.4022 | 0.2740 | 0.9333 | - | 0.6632 |
| core_macro_plus_stable_4h | 38 | 0.5359 | 0.1437 | 0.3277 | 0.2788 | 0.9810 | - | 0.7322 |
| current_full | 131 | 0.5335 | 0.1749 | 0.2113 | 0.2757 | 0.9690 | - | 0.7049 |
| core_plus_macro_plus_all_4h | 50 | 0.5321 | 0.2578 | 0.0240 | 0.2824 | 0.9810 | - | 0.7437 |
| full_no_technical | 121 | 0.5268 | 0.2039 | 0.1417 | 0.2748 | 0.9762 | - | 0.7710 |
| full_no_cross | 120 | 0.5239 | 0.1912 | 0.1669 | 0.2682 | 0.9833 | - | 0.7043 |
| full_no_macro | 129 | 0.5085 | 0.2179 | 0.0936 | 0.2742 | 0.9571 | - | 0.6880 |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
