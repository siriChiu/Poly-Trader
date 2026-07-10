# Feature Coverage Report

- Total rows: **25842**
- Chart-usable: **27**
- Hidden by default: **13**

| Feature | Coverage | Archive-window coverage | Distinct | Chart usable | Quality | History policy | Forward archive | Freshness | Next action |
|---|---:|---:|---:|---|---|---|---|---|---|
| fin_netflow | 0.00% | 0.00% (0/4885) | 0 | ❌ | source_auth_blocked | archive_required | 4962/10 stale (fin_snapshot) · status=auth_missing ([REDACTED] is missing; ETF flow endpoint requires CoinGlass v4 auth.) | age=42863.6m / span=1412.31h | Configure [REDACTED] source credentials for the CoinGlass-backed source first; forward archive events are being logged, but they currently contain auth_missing snapshots so feature coverage cannot improve until credentials work. After auth is fixed, keep running heartbeat collection until at least 10 successful forward snapshots accumulate, then evaluate whether historical export/backfill is still needed. |
| claw_intensity | 13.84% | 71.59% (3497/4885) | 1591 | ❌ | source_auth_blocked | archive_required | 4962/10 stale (claw_snapshot) · status=auth_missing ([REDACTED] is missing in config.yaml.) | age=42863.6m / span=1412.31h | Configure [REDACTED] source credentials for this source first; forward archive events are being logged, but they currently contain auth_missing snapshots so feature coverage cannot improve until credentials work. After auth is fixed, keep running heartbeat collection until at least 10 successful forward snapshots accumulate, then evaluate whether historical export/backfill is still needed. |
| claw | 13.84% | 71.59% (3497/4885) | 1592 | ❌ | source_auth_blocked | archive_required | 4962/10 stale (claw_snapshot) · status=auth_missing ([REDACTED] is missing in config.yaml.) | age=42863.6m / span=1412.31h | Configure [REDACTED] source credentials for this source first; forward archive events are being logged, but they currently contain auth_missing snapshots so feature coverage cannot improve until credentials work. After auth is fixed, keep running heartbeat collection until at least 10 successful forward snapshots accumulate, then evaluate whether historical export/backfill is still needed. |
| nest_pred | 15.36% | 79.55% (3886/4885) | 21 | ❌ | source_tls_verify_failed | snapshot_only | 4962/10 stale (nest_snapshot) · status=tls_verify_failed (Polymarket Gamma TLS verification failed; refusing insecure fallback. Detail: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate (_ssl.c:1016)>) | age=42863.6m / span=1412.31h | Fix the current source TLS trust failure before treating this as a pure history gap: Fix the trusted CA / proxy root for Python and curl, or route the heartbeat through a verified network path. Do not disable TLS verification in production. Once verified TLS snapshots succeed, keep collecting until at least 10 forward raw snapshots accumulate, then decide whether a dedicated historical export/archive loader is still required. |
| scales_ssr | 25.89% | 98.81% (4827/4885) | 5132 | ❌ | source_history_gap | snapshot_only | 4962/10 stale (scales_snapshot) | age=42863.6m / span=1412.31h | Restart or re-run heartbeat collection immediately; latest snapshot archive event is 42863.6 minutes old (stale threshold 60m). After collection resumes, keep running until at least 10 forward raw snapshots accumulate; add historical export/API archive if you need rows before the cutoff. |
| fang_skew | 26.02% | 99.26% (4849/4885) | 1514 | ❌ | source_history_gap | snapshot_only | 4962/10 stale (fang_snapshot) | age=42863.6m / span=1412.31h | Restart or re-run heartbeat collection immediately; latest snapshot archive event is 42863.6 minutes old (stale threshold 60m). After collection resumes, keep running until at least 10 forward raw snapshots accumulate; add historical export/API archive if you need rows before the cutoff. |
| fang_pcr | 26.02% | 99.26% (4849/4885) | 5822 | ❌ | source_history_gap | snapshot_only | 4962/10 stale (fang_snapshot) | age=42863.6m / span=1412.31h | Restart or re-run heartbeat collection immediately; latest snapshot archive event is 42863.6 minutes old (stale threshold 60m). After collection resumes, keep running until at least 10 forward raw snapshots accumulate; add historical export/API archive if you need rows before the cutoff. |
| web_whale | 26.04% | 99.37% (4854/4885) | 1721 | ❌ | source_history_gap | short_window_public_api | 4962/10 stale (web_snapshot) | age=42863.6m / span=1412.31h | Restart or re-run heartbeat collection immediately; latest snapshot archive event is 42863.6 minutes old (stale threshold 60m). After collection resumes, keep running until at least 10 forward raw snapshots accumulate; add historical export/API archive if you need rows before the cutoff. |
| adx | 54.61% | n/a | 5515 | ❌ | low_coverage | native_timeseries | n/a | n/a | coverage<60% |
| donchian_pos | 54.61% | n/a | 13520 | ❌ | low_coverage | native_timeseries | n/a | n/a | coverage<60% |
| nw_width | 54.61% | n/a | 13757 | ❌ | low_coverage | native_timeseries | n/a | n/a | coverage<60% |
| nw_slope | 54.61% | n/a | 13757 | ❌ | low_coverage | native_timeseries | n/a | n/a | coverage<60% |
| choppiness | 54.61% | n/a | 13757 | ❌ | low_coverage | native_timeseries | n/a | n/a | coverage<60% |
| nq_return_24h | 66.61% | n/a | 11964 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| vix | 66.79% | n/a | 1441 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| nq_return_1h | 66.79% | n/a | 5107 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| dxy | 66.83% | n/a | 3376 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| pulse | 67.95% | n/a | 16926 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| mind | 67.95% | n/a | 17348 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| aura | 67.95% | n/a | 17447 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_bias200 | 98.95% | n/a | 24848 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_ma_order | 98.96% | n/a | 3 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_rsi14 | 98.96% | n/a | 6319 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_macd_hist | 98.96% | n/a | 6320 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_vol_ratio | 98.96% | n/a | 6483 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_dist_sl | 98.96% | n/a | 24770 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_bias50 | 98.96% | n/a | 24849 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_bias20 | 98.96% | n/a | 24849 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_dist_bb_lower | 98.96% | n/a | 24849 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_bb_pct_b | 98.96% | n/a | 24850 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| body | 100.00% | n/a | 17430 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| tongue | 100.00% | n/a | 17571 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| nose | 100.00% | n/a | 18238 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| rsi14 | 100.00% | n/a | 25324 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| vwap_dev | 100.00% | n/a | 25451 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| bb_pct_b | 100.00% | n/a | 25598 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| ear | 100.00% | n/a | 25605 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| macd_hist | 100.00% | n/a | 25638 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| atr_pct | 100.00% | n/a | 25639 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| eye | 100.00% | n/a | 25759 | ✅ | ok | native_timeseries | n/a | n/a | ok |
