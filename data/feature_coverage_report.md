# Feature Coverage Report

- Total rows: **11564**
- Chart-usable: **24**
- Hidden by default: **11**

| Feature | Coverage | Archive-window coverage | Distinct | Chart usable | Quality | History policy | Forward archive | Freshness | Next action |
|---|---:|---:|---:|---|---|---|---|---|---|
| fin_netflow | 0.00% | 0.00% (0/326) | 0 | ❌ | source_auth_blocked | archive_required | 331/10 ready (fin_snapshot) · status=auth_missing (COINGLASS_API_KEY is missing; ETF flow endpoint requires CoinGlass v4 auth.) | age=14.2m / span=34.56h | Configure COINGLASS_API_KEY for the CoinGlass-backed source first; forward archive events are being logged, but they currently contain auth_missing snapshots so feature coverage cannot improve until credentials work. After auth is fixed, keep running heartbeat collection until at least 10 successful forward snapshots accumulate, then evaluate whether historical export/backfill is still needed. |
| claw | 0.03% | 0.00% (0/326) | 1 | ❌ | source_auth_blocked | archive_required | 331/10 ready (claw_snapshot) · status=auth_missing (COINGLASS_API_KEY is missing; liquidation history endpoint requires CoinGlass v4 auth.) | age=14.2m / span=34.56h | Configure COINGLASS_API_KEY for the CoinGlass-backed source first; forward archive events are being logged, but they currently contain auth_missing snapshots so feature coverage cannot improve until credentials work. After auth is fixed, keep running heartbeat collection until at least 10 successful forward snapshots accumulate, then evaluate whether historical export/backfill is still needed. |
| claw_intensity | 0.03% | 0.00% (0/326) | 1 | ❌ | source_auth_blocked | archive_required | 331/10 ready (claw_snapshot) · status=auth_missing (COINGLASS_API_KEY is missing; liquidation history endpoint requires CoinGlass v4 auth.) | age=14.2m / span=34.56h | Configure COINGLASS_API_KEY for the CoinGlass-backed source first; forward archive events are being logged, but they currently contain auth_missing snapshots so feature coverage cannot improve until credentials work. After auth is fixed, keep running heartbeat collection until at least 10 successful forward snapshots accumulate, then evaluate whether historical export/backfill is still needed. |
| nest_pred | 2.85% | 98.47% (321/326) | 4 | ❌ | source_history_gap | snapshot_only | 331/10 ready (nest_snapshot) | age=14.2m / span=34.56h | Forward raw snapshot archive is ready for recent-window diagnostics; keep collection running to extend the archive span, but historical rows before the cutoff still require a dedicated export/archive loader before coverage can exceed the legacy gap. |
| scales_ssr | 18.01% | 98.77% (322/326) | 1446 | ❌ | source_history_gap | snapshot_only | 331/10 ready (scales_snapshot) | age=14.2m / span=34.56h | Forward raw snapshot archive is ready for recent-window diagnostics; keep collection running to extend the archive span, but historical rows before the cutoff still require a dedicated export/archive loader before coverage can exceed the legacy gap. |
| web_whale | 18.14% | 100.00% (326/326) | 144 | ❌ | source_history_gap | short_window_public_api | 331/10 ready (web_snapshot) | age=14.2m / span=34.56h | Forward raw snapshot archive is ready for recent-window diagnostics; keep collection running to extend the archive span, but historical rows before the cutoff still require a dedicated export/archive loader before coverage can exceed the legacy gap. |
| fang_skew | 18.14% | 100.00% (326/326) | 401 | ❌ | source_history_gap | snapshot_only | 331/10 ready (fang_snapshot) | age=14.2m / span=34.56h | Forward raw snapshot archive is ready for recent-window diagnostics; keep collection running to extend the archive span, but historical rows before the cutoff still require a dedicated export/archive loader before coverage can exceed the legacy gap. |
| fang_pcr | 18.14% | 100.00% (326/326) | 1755 | ❌ | source_history_gap | snapshot_only | 331/10 ready (fang_snapshot) | age=14.2m / span=34.56h | Forward raw snapshot archive is ready for recent-window diagnostics; keep collection running to extend the archive span, but historical rows before the cutoff still require a dedicated export/archive loader before coverage can exceed the legacy gap. |
| pulse | 28.37% | n/a | 2717 | ❌ | low_coverage | native_timeseries | n/a | n/a | coverage<60% |
| mind | 28.37% | n/a | 3152 | ❌ | low_coverage | native_timeseries | n/a | n/a | coverage<60% |
| aura | 28.37% | n/a | 3200 | ❌ | low_coverage | native_timeseries | n/a | n/a | coverage<60% |
| 4h_vol_ratio | 98.13% | n/a | 2231 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_bias200 | 98.13% | n/a | 11205 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_dist_bb_lower | 98.13% | n/a | 11205 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_ma_order | 98.14% | n/a | 3 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_rsi14 | 98.14% | n/a | 2231 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_macd_hist | 98.14% | n/a | 2232 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_dist_sl | 98.14% | n/a | 11181 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_bias50 | 98.14% | n/a | 11206 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_bias20 | 98.14% | n/a | 11206 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_bb_pct_b | 98.14% | n/a | 11206 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| nq_return_24h | 99.71% | n/a | 8628 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| vix | 99.90% | n/a | 1418 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| nq_return_1h | 99.91% | n/a | 2081 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| dxy | 99.98% | n/a | 3236 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| body | 100.00% | n/a | 3232 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| tongue | 100.00% | n/a | 3316 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| nose | 100.00% | n/a | 4013 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| vwap_dev | 100.00% | n/a | 11370 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| rsi14 | 100.00% | n/a | 11379 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| ear | 100.00% | n/a | 11437 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| bb_pct_b | 100.00% | n/a | 11451 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| macd_hist | 100.00% | n/a | 11469 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| atr_pct | 100.00% | n/a | 11470 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| eye | 100.00% | n/a | 11518 | ✅ | ok | native_timeseries | n/a | n/a | ok |
