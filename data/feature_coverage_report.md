# Feature Coverage Report

- Total rows: **24562**
- Chart-usable: **27**
- Hidden by default: **13**

| Feature | Coverage | Archive-window coverage | Distinct | Chart usable | Quality | History policy | Forward archive | Freshness | Next action |
|---|---:|---:|---:|---|---|---|---|---|---|
| fin_netflow | 0.00% | 0.00% (0/4091) | 0 | ❌ | source_auth_blocked | archive_required | 4147/10 ready (fin_snapshot) · status=auth_missing ([REDACTED] is missing; ETF flow endpoint requires CoinGlass v4 auth.) | age=2.1m / span=915.99h | Configure [REDACTED] source credentials for the CoinGlass-backed source first; forward archive events are being logged, but they currently contain auth_missing snapshots so feature coverage cannot improve until credentials work. After auth is fixed, keep running heartbeat collection until at least 10 successful forward snapshots accumulate, then evaluate whether historical export/backfill is still needed. |
| claw_intensity | 14.56% | 85.48% (3497/4091) | 1591 | ❌ | source_auth_blocked | archive_required | 4147/10 ready (claw_snapshot) · status=auth_missing ([REDACTED] is missing in config.yaml.) | age=2.1m / span=915.99h | Configure [REDACTED] source credentials for this source first; forward archive events are being logged, but they currently contain auth_missing snapshots so feature coverage cannot improve until credentials work. After auth is fixed, keep running heartbeat collection until at least 10 successful forward snapshots accumulate, then evaluate whether historical export/backfill is still needed. |
| claw | 14.56% | 85.48% (3497/4091) | 1592 | ❌ | source_auth_blocked | archive_required | 4147/10 ready (claw_snapshot) · status=auth_missing ([REDACTED] is missing in config.yaml.) | age=2.1m / span=915.99h | Configure [REDACTED] source credentials for this source first; forward archive events are being logged, but they currently contain auth_missing snapshots so feature coverage cannot improve until credentials work. After auth is fixed, keep running heartbeat collection until at least 10 successful forward snapshots accumulate, then evaluate whether historical export/backfill is still needed. |
| nest_pred | 16.16% | 94.99% (3886/4091) | 21 | ❌ | source_tls_verify_failed | snapshot_only | 4147/10 ready (nest_snapshot) · status=tls_verify_failed (Polymarket Gamma TLS verification failed; refusing insecure fallback. Detail: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate (_ssl.c:1016)>) | age=2.1m / span=915.99h | Fix the current source TLS trust failure before treating this as a pure history gap: Fix the trusted CA / proxy root for Python and curl, or route the heartbeat through a verified network path. Do not disable TLS verification in production. Once verified TLS snapshots succeed, keep collecting until at least 10 forward raw snapshots accumulate, then decide whether a dedicated historical export/archive loader is still required. |
| scales_ssr | 23.92% | 98.61% (4034/4091) | 4408 | ❌ | source_history_gap | snapshot_only | 4147/10 ready (scales_snapshot) | age=2.1m / span=915.99h | Forward raw snapshot archive is ready for recent-window diagnostics; keep collection running to extend the archive span, but historical rows before the cutoff still require a dedicated export/archive loader before coverage can exceed the legacy gap. |
| fang_skew | 24.06% | 99.19% (4058/4091) | 1320 | ❌ | source_history_gap | snapshot_only | 4147/10 ready (fang_snapshot) | age=2.1m / span=915.99h | Forward raw snapshot archive is ready for recent-window diagnostics; keep collection running to extend the archive span, but historical rows before the cutoff still require a dedicated export/archive loader before coverage can exceed the legacy gap. |
| fang_pcr | 24.06% | 99.19% (4058/4091) | 5044 | ❌ | source_history_gap | snapshot_only | 4147/10 ready (fang_snapshot) | age=2.1m / span=915.99h | Forward raw snapshot archive is ready for recent-window diagnostics; keep collection running to extend the archive span, but historical rows before the cutoff still require a dedicated export/archive loader before coverage can exceed the legacy gap. |
| web_whale | 24.07% | 99.27% (4061/4091) | 1718 | ❌ | source_history_gap | short_window_public_api | 4147/10 ready (web_snapshot) | age=2.1m / span=915.99h | Forward raw snapshot archive is ready for recent-window diagnostics; keep collection running to extend the archive span, but historical rows before the cutoff still require a dedicated export/archive loader before coverage can exceed the legacy gap. |
| adx | 52.24% | n/a | 4288 | ❌ | low_coverage | native_timeseries | n/a | n/a | coverage<60% |
| donchian_pos | 52.24% | n/a | 12354 | ❌ | low_coverage | native_timeseries | n/a | n/a | coverage<60% |
| nw_width | 52.24% | n/a | 12477 | ❌ | low_coverage | native_timeseries | n/a | n/a | coverage<60% |
| nw_slope | 52.24% | n/a | 12477 | ❌ | low_coverage | native_timeseries | n/a | n/a | coverage<60% |
| choppiness | 52.24% | n/a | 12477 | ❌ | low_coverage | native_timeseries | n/a | n/a | coverage<60% |
| nq_return_24h | 64.87% | n/a | 11396 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| vix | 65.06% | n/a | 1440 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| nq_return_1h | 65.06% | n/a | 4592 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| dxy | 65.10% | n/a | 3342 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| pulse | 66.28% | n/a | 15654 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| mind | 66.28% | n/a | 16086 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| aura | 66.28% | n/a | 16167 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_ma_order | 98.90% | n/a | 3 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_rsi14 | 98.90% | n/a | 5338 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_macd_hist | 98.90% | n/a | 5339 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_vol_ratio | 98.90% | n/a | 5461 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_dist_sl | 98.90% | n/a | 23790 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_bias200 | 98.90% | n/a | 23867 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_bias50 | 98.90% | n/a | 23868 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_bias20 | 98.90% | n/a | 23868 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_dist_bb_lower | 98.90% | n/a | 23868 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_bb_pct_b | 98.90% | n/a | 23869 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| body | 100.00% | n/a | 16150 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| tongue | 100.00% | n/a | 16291 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| nose | 100.00% | n/a | 16982 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| rsi14 | 100.00% | n/a | 24160 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| vwap_dev | 100.00% | n/a | 24171 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| bb_pct_b | 100.00% | n/a | 24318 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| macd_hist | 100.00% | n/a | 24358 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| atr_pct | 100.00% | n/a | 24359 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| ear | 100.00% | n/a | 24362 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| eye | 100.00% | n/a | 24483 | ✅ | ok | native_timeseries | n/a | n/a | ok |
