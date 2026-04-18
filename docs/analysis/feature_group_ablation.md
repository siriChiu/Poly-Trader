# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **5000**
- splits: **5** (TimeSeriesSplit)
- generated_at: **2026-04-18 21:35:41 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.7304 | 0.1394 | 0.5954 | 0.2197 | 0.7357 | - | 0.5010 |
| core_plus_technical | 18 | 0.6980 | 0.1580 | 0.5594 | 0.2190 | 0.8167 | - | 0.5908 |
| core_plus_4h | 18 | 0.6934 | 0.1645 | 0.5198 | 0.2247 | 0.9667 | - | 0.7008 |
| core_plus_macro_plus_4h_trend | 22 | 0.6773 | 0.1772 | 0.4574 | 0.2448 | 0.9476 | - | 0.6890 |
| core_plus_macro_plus_4h_structure_shift | 22 | 0.6771 | 0.1977 | 0.4550 | 0.2509 | 0.8405 | - | 0.7732 |
| core_plus_macro | 10 | 0.6694 | 0.1754 | 0.4862 | 0.2508 | 0.9667 | - | 0.9093 |
| core_plus_macro_plus_4h_momentum | 22 | 0.6653 | 0.1841 | 0.4514 | 0.2506 | 0.9690 | - | 0.9687 |
| current_full_no_bull_collapse_4h | 119 | 0.6648 | 0.1834 | 0.4478 | 0.2473 | 0.9643 | - | 0.7148 |
| core_macro_plus_stable_4h | 38 | 0.6593 | 0.1852 | 0.4526 | 0.2659 | 0.9595 | - | 0.8401 |
| full_no_macro | 129 | 0.6571 | 0.1979 | 0.4586 | 0.2470 | 0.8429 | - | 0.7389 |
| full_no_technical | 121 | 0.6555 | 0.1974 | 0.4586 | 0.2573 | 0.8429 | - | 0.6238 |
| current_full | 131 | 0.6533 | 0.2015 | 0.4490 | 0.2586 | 0.8405 | - | 0.7311 |
| full_no_4h | 121 | 0.6523 | 0.2069 | 0.4190 | 0.2461 | 0.8190 | - | 0.7690 |
| full_no_cross | 120 | 0.6521 | 0.2037 | 0.4454 | 0.2609 | 0.8405 | - | 0.6860 |
| core_plus_macro_plus_all_4h | 50 | 0.6495 | 0.1926 | 0.4538 | 0.2631 | 0.8452 | - | 0.7593 |
| full_no_lags | 41 | 0.6478 | 0.1949 | 0.4562 | 0.2514 | 0.8976 | - | 0.7515 |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
