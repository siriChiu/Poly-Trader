# Feature Coverage Report

- Total rows: **11167**
- Chart-usable: **24**
- Hidden by default: **11**

| Feature | Coverage | Archive-window coverage | Distinct | Chart usable | Quality | History policy | Forward archive | Freshness | Next action |
|---|---:|---:|---:|---|---|---|---|---|---|
| claw | 0.00% | 0.00% (0/2) | 0 | ❌ | source_history_gap | archive_required | 3/10 building (claw_snapshot) | age=6.8m / span=1.12h | Keep heartbeat collection running until at least 10 forward raw snapshots accumulate; add historical export/API archive if you need to backfill rows before the archive cutoff. |
| claw_intensity | 0.00% | 0.00% (0/2) | 0 | ❌ | source_history_gap | archive_required | 3/10 building (claw_snapshot) | age=6.8m / span=1.12h | Keep heartbeat collection running until at least 10 forward raw snapshots accumulate; add historical export/API archive if you need to backfill rows before the archive cutoff. |
| fin_netflow | 0.00% | 0.00% (0/2) | 0 | ❌ | source_history_gap | archive_required | 3/10 building (fin_snapshot) | age=6.8m / span=1.12h | Keep heartbeat collection running until at least 10 forward raw snapshots accumulate; add historical export/API archive if you need to backfill rows before the archive cutoff. |
| nest_pred | 0.00% | 0.00% (0/2) | 0 | ❌ | source_history_gap | snapshot_only | 3/10 building (nest_snapshot) | age=6.8m / span=1.12h | Keep heartbeat collection running until at least 10 forward raw snapshots accumulate; add historical export/API archive if you need to backfill rows before the archive cutoff. |
| scales_ssr | 15.72% | 100.00% (2/2) | 1225 | ❌ | source_history_gap | snapshot_only | 3/10 building (scales_snapshot) | age=6.8m / span=1.12h | Keep heartbeat collection running until at least 10 forward raw snapshots accumulate; add historical export/API archive if you need to backfill rows before the archive cutoff. |
| web_whale | 15.81% | 100.00% (2/2) | 53 | ❌ | source_history_gap | short_window_public_api | 3/10 building (web_snapshot) | age=6.8m / span=1.12h | Keep heartbeat collection running until at least 10 forward raw snapshots accumulate; add historical export/API archive if you need to backfill rows before the archive cutoff. |
| fang_skew | 15.81% | 100.00% (2/2) | 356 | ❌ | source_history_gap | snapshot_only | 3/10 building (fang_snapshot) | age=6.8m / span=1.12h | Keep heartbeat collection running until at least 10 forward raw snapshots accumulate; add historical export/API archive if you need to backfill rows before the archive cutoff. |
| fang_pcr | 15.81% | 100.00% (2/2) | 1491 | ❌ | source_history_gap | snapshot_only | 3/10 building (fang_snapshot) | age=6.8m / span=1.12h | Keep heartbeat collection running until at least 10 forward raw snapshots accumulate; add historical export/API archive if you need to backfill rows before the archive cutoff. |
| pulse | 25.83% | n/a | 2324 | ❌ | low_coverage | native_timeseries | n/a | n/a | coverage<60% |
| mind | 25.83% | n/a | 2759 | ❌ | low_coverage | native_timeseries | n/a | n/a | coverage<60% |
| aura | 25.83% | n/a | 2803 | ❌ | low_coverage | native_timeseries | n/a | n/a | coverage<60% |
| 4h_vol_ratio | 97.34% | n/a | 2221 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_bias200 | 97.34% | n/a | 10759 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_dist_bb_lower | 97.34% | n/a | 10759 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_ma_order | 97.35% | n/a | 3 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_rsi14 | 97.35% | n/a | 2221 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_macd_hist | 97.35% | n/a | 2222 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_dist_sl | 97.35% | n/a | 10739 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_bias50 | 97.35% | n/a | 10760 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_bias20 | 97.35% | n/a | 10760 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_bb_pct_b | 97.35% | n/a | 10760 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| nq_return_24h | 99.70% | n/a | 8302 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| vix | 99.89% | n/a | 1418 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| nq_return_1h | 99.91% | n/a | 1775 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| dxy | 99.98% | n/a | 3224 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| body | 100.00% | n/a | 2835 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| tongue | 100.00% | n/a | 2919 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| nose | 100.00% | n/a | 3622 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| vwap_dev | 100.00% | n/a | 10990 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| rsi14 | 100.00% | n/a | 10995 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| ear | 100.00% | n/a | 11042 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| bb_pct_b | 100.00% | n/a | 11054 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| macd_hist | 100.00% | n/a | 11072 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| atr_pct | 100.00% | n/a | 11073 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| eye | 100.00% | n/a | 11121 | ✅ | ok | native_timeseries | n/a | n/a | ok |
