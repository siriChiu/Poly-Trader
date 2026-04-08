# Feature Coverage Report

- Total rows: **11171**
- Chart-usable: **24**
- Hidden by default: **11**

| Feature | Coverage | Archive-window coverage | Distinct | Chart usable | Quality | History policy | Forward archive | Freshness | Next action |
|---|---:|---:|---:|---|---|---|---|---|---|
| claw | 0.00% | 0.00% (0/6) | 0 | ❌ | source_auth_blocked | archive_required | 7/10 building (claw_snapshot) · status=auth_missing (COINGLASS_API_KEY is missing; liquidation history endpoint requires CoinGlass v4 auth.) | age=3.3m / span=1.86h | Configure COINGLASS_API_KEY for the CoinGlass-backed source first; forward archive events are being logged, but they currently contain auth_missing snapshots so feature coverage cannot improve until credentials work. After auth is fixed, keep running heartbeat collection until at least 10 successful forward snapshots accumulate, then evaluate whether historical export/backfill is still needed. |
| claw_intensity | 0.00% | 0.00% (0/6) | 0 | ❌ | source_auth_blocked | archive_required | 7/10 building (claw_snapshot) · status=auth_missing (COINGLASS_API_KEY is missing; liquidation history endpoint requires CoinGlass v4 auth.) | age=3.3m / span=1.86h | Configure COINGLASS_API_KEY for the CoinGlass-backed source first; forward archive events are being logged, but they currently contain auth_missing snapshots so feature coverage cannot improve until credentials work. After auth is fixed, keep running heartbeat collection until at least 10 successful forward snapshots accumulate, then evaluate whether historical export/backfill is still needed. |
| fin_netflow | 0.00% | 0.00% (0/6) | 0 | ❌ | source_auth_blocked | archive_required | 7/10 building (fin_snapshot) · status=auth_missing (COINGLASS_API_KEY is missing; ETF flow endpoint requires CoinGlass v4 auth.) | age=3.3m / span=1.86h | Configure COINGLASS_API_KEY for the CoinGlass-backed source first; forward archive events are being logged, but they currently contain auth_missing snapshots so feature coverage cannot improve until credentials work. After auth is fixed, keep running heartbeat collection until at least 10 successful forward snapshots accumulate, then evaluate whether historical export/backfill is still needed. |
| nest_pred | 0.02% | 33.33% (2/6) | 2 | ❌ | source_history_gap | snapshot_only | 7/10 building (nest_snapshot) | age=3.3m / span=1.86h | Keep heartbeat collection running until at least 10 forward raw snapshots accumulate; add historical export/API archive if you need to backfill rows before the archive cutoff. |
| scales_ssr | 15.75% | 100.00% (6/6) | 1229 | ❌ | source_history_gap | snapshot_only | 7/10 building (scales_snapshot) | age=3.3m / span=1.86h | Keep heartbeat collection running until at least 10 forward raw snapshots accumulate; add historical export/API archive if you need to backfill rows before the archive cutoff. |
| web_whale | 15.84% | 100.00% (6/6) | 53 | ❌ | source_history_gap | short_window_public_api | 7/10 building (web_snapshot) | age=3.3m / span=1.86h | Keep heartbeat collection running until at least 10 forward raw snapshots accumulate; add historical export/API archive if you need to backfill rows before the archive cutoff. |
| fang_skew | 15.84% | 100.00% (6/6) | 357 | ❌ | source_history_gap | snapshot_only | 7/10 building (fang_snapshot) | age=3.3m / span=1.86h | Keep heartbeat collection running until at least 10 forward raw snapshots accumulate; add historical export/API archive if you need to backfill rows before the archive cutoff. |
| fang_pcr | 15.84% | 100.00% (6/6) | 1495 | ❌ | source_history_gap | snapshot_only | 7/10 building (fang_snapshot) | age=3.3m / span=1.86h | Keep heartbeat collection running until at least 10 forward raw snapshots accumulate; add historical export/API archive if you need to backfill rows before the archive cutoff. |
| pulse | 25.85% | n/a | 2328 | ❌ | low_coverage | native_timeseries | n/a | n/a | coverage<60% |
| mind | 25.85% | n/a | 2763 | ❌ | low_coverage | native_timeseries | n/a | n/a | coverage<60% |
| aura | 25.85% | n/a | 2807 | ❌ | low_coverage | native_timeseries | n/a | n/a | coverage<60% |
| 4h_ma_order | 97.31% | n/a | 3 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_rsi14 | 97.31% | n/a | 2221 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_vol_ratio | 97.31% | n/a | 2221 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_macd_hist | 97.31% | n/a | 2222 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_dist_sl | 97.31% | n/a | 10739 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_bias200 | 97.31% | n/a | 10759 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_dist_bb_lower | 97.31% | n/a | 10759 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_bias50 | 97.31% | n/a | 10760 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_bias20 | 97.31% | n/a | 10760 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_bb_pct_b | 97.31% | n/a | 10760 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| nq_return_24h | 99.70% | n/a | 8306 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| vix | 99.89% | n/a | 1418 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| nq_return_1h | 99.91% | n/a | 1779 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| dxy | 99.98% | n/a | 3224 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| body | 100.00% | n/a | 2839 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| tongue | 100.00% | n/a | 2923 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| nose | 100.00% | n/a | 3626 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| vwap_dev | 100.00% | n/a | 10994 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| rsi14 | 100.00% | n/a | 10999 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| ear | 100.00% | n/a | 11046 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| bb_pct_b | 100.00% | n/a | 11058 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| macd_hist | 100.00% | n/a | 11076 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| atr_pct | 100.00% | n/a | 11077 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| eye | 100.00% | n/a | 11125 | ✅ | ok | native_timeseries | n/a | n/a | ok |
