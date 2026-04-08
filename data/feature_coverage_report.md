# Feature Coverage Report

- Total rows: **11165**
- Chart-usable: **24**
- Hidden by default: **11**

| Feature | Coverage | Distinct | Chart usable | Quality | History policy | Forward archive | Next action |
|---|---:|---:|---|---|---|---|---|
| claw | 0.00% | 0 | ❌ | source_history_gap | archive_required | 1 (claw_snapshot) | Keep heartbeat collection running to accumulate forward raw snapshots; add historical export/API archive if you need to backfill rows before the archive cutoff. |
| claw_intensity | 0.00% | 0 | ❌ | source_history_gap | archive_required | 1 (claw_snapshot) | Keep heartbeat collection running to accumulate forward raw snapshots; add historical export/API archive if you need to backfill rows before the archive cutoff. |
| fin_netflow | 0.00% | 0 | ❌ | source_history_gap | archive_required | 1 (fin_snapshot) | Keep heartbeat collection running to accumulate forward raw snapshots; add historical export/API archive if you need to backfill rows before the archive cutoff. |
| nest_pred | 0.00% | 0 | ❌ | source_history_gap | snapshot_only | 1 (nest_snapshot) | Keep heartbeat collection running to accumulate forward raw snapshots; add historical export/API archive if you need to backfill rows before the archive cutoff. |
| scales_ssr | 15.70% | 1223 | ❌ | source_history_gap | snapshot_only | 1 (scales_snapshot) | Keep heartbeat collection running to accumulate forward raw snapshots; add historical export/API archive if you need to backfill rows before the archive cutoff. |
| web_whale | 15.80% | 53 | ❌ | source_history_gap | short_window_public_api | 1 (web_snapshot) | Keep heartbeat collection running to accumulate forward raw snapshots; add historical export/API archive if you need to backfill rows before the archive cutoff. |
| fang_skew | 15.80% | 356 | ❌ | source_history_gap | snapshot_only | 1 (fang_snapshot) | Keep heartbeat collection running to accumulate forward raw snapshots; add historical export/API archive if you need to backfill rows before the archive cutoff. |
| fang_pcr | 15.80% | 1489 | ❌ | source_history_gap | snapshot_only | 1 (fang_snapshot) | Keep heartbeat collection running to accumulate forward raw snapshots; add historical export/API archive if you need to backfill rows before the archive cutoff. |
| pulse | 25.81% | 2322 | ❌ | low_coverage | native_timeseries | n/a | coverage<60% |
| mind | 25.81% | 2757 | ❌ | low_coverage | native_timeseries | n/a | coverage<60% |
| aura | 25.81% | 2801 | ❌ | low_coverage | native_timeseries | n/a | coverage<60% |
| 4h_vol_ratio | 97.36% | 2221 | ✅ | ok | native_timeseries | n/a | ok |
| 4h_bias200 | 97.36% | 10759 | ✅ | ok | native_timeseries | n/a | ok |
| 4h_dist_bb_lower | 97.36% | 10759 | ✅ | ok | native_timeseries | n/a | ok |
| 4h_ma_order | 97.37% | 3 | ✅ | ok | native_timeseries | n/a | ok |
| 4h_rsi14 | 97.37% | 2221 | ✅ | ok | native_timeseries | n/a | ok |
| 4h_macd_hist | 97.37% | 2222 | ✅ | ok | native_timeseries | n/a | ok |
| 4h_dist_sl | 97.37% | 10739 | ✅ | ok | native_timeseries | n/a | ok |
| 4h_bias50 | 97.37% | 10760 | ✅ | ok | native_timeseries | n/a | ok |
| 4h_bias20 | 97.37% | 10760 | ✅ | ok | native_timeseries | n/a | ok |
| 4h_bb_pct_b | 97.37% | 10760 | ✅ | ok | native_timeseries | n/a | ok |
| nq_return_24h | 99.70% | 8300 | ✅ | ok | native_timeseries | n/a | ok |
| vix | 99.89% | 1418 | ✅ | ok | native_timeseries | n/a | ok |
| nq_return_1h | 99.91% | 1773 | ✅ | ok | native_timeseries | n/a | ok |
| dxy | 99.98% | 3224 | ✅ | ok | native_timeseries | n/a | ok |
| body | 100.00% | 2833 | ✅ | ok | native_timeseries | n/a | ok |
| tongue | 100.00% | 2917 | ✅ | ok | native_timeseries | n/a | ok |
| nose | 100.00% | 3620 | ✅ | ok | native_timeseries | n/a | ok |
| vwap_dev | 100.00% | 10988 | ✅ | ok | native_timeseries | n/a | ok |
| rsi14 | 100.00% | 10993 | ✅ | ok | native_timeseries | n/a | ok |
| ear | 100.00% | 11040 | ✅ | ok | native_timeseries | n/a | ok |
| bb_pct_b | 100.00% | 11052 | ✅ | ok | native_timeseries | n/a | ok |
| macd_hist | 100.00% | 11070 | ✅ | ok | native_timeseries | n/a | ok |
| atr_pct | 100.00% | 11071 | ✅ | ok | native_timeseries | n/a | ok |
| eye | 100.00% | 11119 | ✅ | ok | native_timeseries | n/a | ok |
