# Feature Coverage Report

- Total rows: **11562**
- Chart-usable: **24**
- Hidden by default: **11**

| Feature | Coverage | Archive-window coverage | Distinct | Chart usable | Quality | History policy | Forward archive | Freshness | Next action |
|---|---:|---:|---:|---|---|---|---|---|---|
| fin_netflow | 0.00% | 0.00% (0/324) | 0 | ❌ | source_auth_blocked | archive_required | 329/10 ready (fin_snapshot) · status=auth_missing (COINGLASS_API_KEY is missing; ETF flow endpoint requires CoinGlass v4 auth.) | age=2.6m / span=34.26h | Configure COINGLASS_API_KEY for the CoinGlass-backed source first; forward archive events are being logged, but they currently contain auth_missing snapshots so feature coverage cannot improve until credentials work. After auth is fixed, keep running heartbeat collection until at least 10 successful forward snapshots accumulate, then evaluate whether historical export/backfill is still needed. |
| claw | 0.03% | 0.00% (0/324) | 1 | ❌ | source_auth_blocked | archive_required | 329/10 ready (claw_snapshot) · status=auth_missing (COINGLASS_API_KEY is missing; liquidation history endpoint requires CoinGlass v4 auth.) | age=2.6m / span=34.26h | Configure COINGLASS_API_KEY for the CoinGlass-backed source first; forward archive events are being logged, but they currently contain auth_missing snapshots so feature coverage cannot improve until credentials work. After auth is fixed, keep running heartbeat collection until at least 10 successful forward snapshots accumulate, then evaluate whether historical export/backfill is still needed. |
| claw_intensity | 0.03% | 0.00% (0/324) | 1 | ❌ | source_auth_blocked | archive_required | 329/10 ready (claw_snapshot) · status=auth_missing (COINGLASS_API_KEY is missing; liquidation history endpoint requires CoinGlass v4 auth.) | age=2.6m / span=34.26h | Configure COINGLASS_API_KEY for the CoinGlass-backed source first; forward archive events are being logged, but they currently contain auth_missing snapshots so feature coverage cannot improve until credentials work. After auth is fixed, keep running heartbeat collection until at least 10 successful forward snapshots accumulate, then evaluate whether historical export/backfill is still needed. |
| nest_pred | 2.84% | 98.46% (319/324) | 4 | ❌ | source_history_gap | snapshot_only | 329/10 ready (nest_snapshot) | age=2.6m / span=34.26h | Forward raw snapshot archive is ready for recent-window diagnostics; keep collection running to extend the archive span, but historical rows before the cutoff still require a dedicated export/archive loader before coverage can exceed the legacy gap. |
| scales_ssr | 18.00% | 98.77% (320/324) | 1444 | ❌ | source_history_gap | snapshot_only | 329/10 ready (scales_snapshot) | age=2.6m / span=34.26h | Forward raw snapshot archive is ready for recent-window diagnostics; keep collection running to extend the archive span, but historical rows before the cutoff still require a dedicated export/archive loader before coverage can exceed the legacy gap. |
| web_whale | 18.13% | 100.00% (324/324) | 143 | ❌ | source_history_gap | short_window_public_api | 329/10 ready (web_snapshot) | age=2.6m / span=34.26h | Forward raw snapshot archive is ready for recent-window diagnostics; keep collection running to extend the archive span, but historical rows before the cutoff still require a dedicated export/archive loader before coverage can exceed the legacy gap. |
| fang_skew | 18.13% | 100.00% (324/324) | 399 | ❌ | source_history_gap | snapshot_only | 329/10 ready (fang_snapshot) | age=2.6m / span=34.26h | Forward raw snapshot archive is ready for recent-window diagnostics; keep collection running to extend the archive span, but historical rows before the cutoff still require a dedicated export/archive loader before coverage can exceed the legacy gap. |
| fang_pcr | 18.13% | 100.00% (324/324) | 1753 | ❌ | source_history_gap | snapshot_only | 329/10 ready (fang_snapshot) | age=2.6m / span=34.26h | Forward raw snapshot archive is ready for recent-window diagnostics; keep collection running to extend the archive span, but historical rows before the cutoff still require a dedicated export/archive loader before coverage can exceed the legacy gap. |
| pulse | 28.36% | n/a | 2715 | ❌ | low_coverage | native_timeseries | n/a | n/a | coverage<60% |
| mind | 28.36% | n/a | 3150 | ❌ | low_coverage | native_timeseries | n/a | n/a | coverage<60% |
| aura | 28.36% | n/a | 3198 | ❌ | low_coverage | native_timeseries | n/a | n/a | coverage<60% |
| 4h_vol_ratio | 94.01% | n/a | 2221 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_bias200 | 94.01% | n/a | 10759 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_dist_bb_lower | 94.01% | n/a | 10759 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_ma_order | 94.02% | n/a | 3 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_rsi14 | 94.02% | n/a | 2221 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_macd_hist | 94.02% | n/a | 2222 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_dist_sl | 94.02% | n/a | 10739 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_bias50 | 94.02% | n/a | 10760 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_bias20 | 94.02% | n/a | 10760 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_bb_pct_b | 94.02% | n/a | 10760 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| nq_return_24h | 99.71% | n/a | 8626 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| vix | 99.90% | n/a | 1418 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| nq_return_1h | 99.91% | n/a | 2079 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| dxy | 99.98% | n/a | 3236 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| body | 100.00% | n/a | 3230 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| tongue | 100.00% | n/a | 3314 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| nose | 100.00% | n/a | 4011 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| vwap_dev | 100.00% | n/a | 11368 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| rsi14 | 100.00% | n/a | 11377 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| ear | 100.00% | n/a | 11435 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| bb_pct_b | 100.00% | n/a | 11449 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| macd_hist | 100.00% | n/a | 11467 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| atr_pct | 100.00% | n/a | 11468 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| eye | 100.00% | n/a | 11516 | ✅ | ok | native_timeseries | n/a | n/a | ok |
