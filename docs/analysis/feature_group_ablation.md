# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **5000**
- splits: **5** (TimeSeriesSplit)
- generated_at: **2026-04-22 23:41:19 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.6706 | 0.2101 | 0.4118 | 0.2682 | 0.5571 | - | 0.4882 |
| core_plus_macro_plus_4h_structure_shift | 22 | 0.5647 | 0.1128 | 0.4130 | 0.3279 | 0.6881 | - | 0.5280 |
| core_plus_4h | 18 | 0.5568 | 0.0801 | 0.4658 | 0.3433 | 0.5619 | - | 0.5469 |
| core_plus_macro_plus_4h_trend | 22 | 0.4989 | 0.1926 | 0.1417 | 0.3661 | 0.6381 | - | 0.5744 |
| core_plus_technical | 18 | 0.4970 | 0.1430 | 0.2677 | 0.3417 | 0.6405 | - | 0.4408 |
| core_plus_macro_plus_all_4h | 50 | 0.4884 | 0.1390 | 0.2497 | 0.3511 | 0.5786 | - | 0.6065 |
| core_plus_macro | 10 | 0.4864 | 0.1229 | 0.3517 | 0.3781 | 0.7476 | - | 0.5565 |
| full_no_lags | 41 | 0.4776 | 0.1848 | 0.1405 | 0.4191 | 0.6786 | - | 0.4891 |
| current_full | 131 | 0.4699 | 0.1775 | 0.1489 | 0.4174 | 0.6357 | - | 0.5443 |
| full_no_cross | 120 | 0.4677 | 0.1762 | 0.1489 | 0.4150 | 0.5405 | - | 0.5381 |
| full_no_technical | 121 | 0.4672 | 0.1760 | 0.1489 | 0.4193 | 0.6476 | - | 0.5781 |
| full_no_macro | 129 | 0.4660 | 0.1753 | 0.1489 | 0.4205 | 0.6167 | - | 0.5559 |
| current_full_no_bull_collapse_4h | 119 | 0.4617 | 0.1753 | 0.1465 | 0.4321 | 0.6119 | - | 0.5504 |
| core_macro_plus_stable_4h | 38 | 0.4607 | 0.1756 | 0.1453 | 0.3760 | 0.5786 | - | 0.6043 |
| core_plus_macro_plus_4h_momentum | 22 | 0.4595 | 0.1371 | 0.2485 | 0.3963 | 0.6714 | - | 0.5744 |
| full_no_4h | 121 | 0.4593 | 0.1827 | 0.1489 | 0.4209 | 0.6143 | - | 0.5049 |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
