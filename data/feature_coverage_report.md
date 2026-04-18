# Feature Coverage Report

- Total rows: **12876**
- Chart-usable: **24**
- Hidden by default: **16**

| Feature | Coverage | Archive-window coverage | Distinct | Chart usable | Quality | History policy | Forward archive | Freshness | Next action |
|---|---:|---:|---:|---|---|---|---|---|---|
| fin_netflow | 0.00% | 0.00% (0/1576) | 0 | ❌ | source_auth_blocked | archive_required | 1603/10 ready (fin_snapshot) · status=auth_missing (COINGLASS_API_KEY is missing; ETF flow endpoint requires CoinGlass v4 auth.) | age=0.7m / span=151.21h | Configure COINGLASS_API_KEY for the CoinGlass-backed source first; forward archive events are being logged, but they currently contain auth_missing snapshots so feature coverage cannot improve until credentials work. After auth is fixed, keep running heartbeat collection until at least 10 successful forward snapshots accumulate, then evaluate whether historical export/backfill is still needed. |
| donchian_pos | 8.90% | n/a | 884 | ❌ | low_coverage | native_timeseries | n/a | n/a | coverage<60% |
| adx | 8.90% | n/a | 897 | ❌ | low_coverage | native_timeseries | n/a | n/a | coverage<60% |
| nw_width | 8.90% | n/a | 900 | ❌ | low_coverage | native_timeseries | n/a | n/a | coverage<60% |
| nw_slope | 8.90% | n/a | 900 | ❌ | low_coverage | native_timeseries | n/a | n/a | coverage<60% |
| choppiness | 8.90% | n/a | 900 | ❌ | low_coverage | native_timeseries | n/a | n/a | coverage<60% |
| claw | 9.35% | 74.68% (1177/1576) | 398 | ❌ | source_history_gap | archive_required | 1603/10 ready (claw_snapshot) | age=0.7m / span=151.21h | Forward raw snapshot archive is ready for recent-window diagnostics; keep collection running to extend the archive span, but historical rows before the cutoff still require a dedicated export/archive loader before coverage can exceed the legacy gap. |
| claw_intensity | 9.35% | 74.68% (1177/1576) | 398 | ❌ | source_history_gap | archive_required | 1603/10 ready (claw_snapshot) | age=0.7m / span=151.21h | Forward raw snapshot archive is ready for recent-window diagnostics; keep collection running to extend the archive span, but historical rows before the cutoff still require a dedicated export/archive loader before coverage can exceed the legacy gap. |
| nest_pred | 12.36% | 99.05% (1561/1576) | 6 | ❌ | source_history_gap | snapshot_only | 1603/10 ready (nest_snapshot) | age=0.7m / span=151.21h | Forward raw snapshot archive is ready for recent-window diagnostics; keep collection running to extend the archive span, but historical rows before the cutoff still require a dedicated export/archive loader before coverage can exceed the legacy gap. |
| scales_ssr | 25.99% | 99.18% (1563/1576) | 2396 | ❌ | source_history_gap | snapshot_only | 1603/10 ready (scales_snapshot) | age=0.7m / span=151.21h | Forward raw snapshot archive is ready for recent-window diagnostics; keep collection running to extend the archive span, but historical rows before the cutoff still require a dedicated export/archive loader before coverage can exceed the legacy gap. |
| fang_skew | 26.16% | 99.81% (1573/1576) | 668 | ❌ | source_history_gap | snapshot_only | 1603/10 ready (fang_snapshot) | age=0.7m / span=151.21h | Forward raw snapshot archive is ready for recent-window diagnostics; keep collection running to extend the archive span, but historical rows before the cutoff still require a dedicated export/archive loader before coverage can exceed the legacy gap. |
| fang_pcr | 26.16% | 99.81% (1573/1576) | 2849 | ❌ | source_history_gap | snapshot_only | 1603/10 ready (fang_snapshot) | age=0.7m / span=151.21h | Forward raw snapshot archive is ready for recent-window diagnostics; keep collection running to extend the archive span, but historical rows before the cutoff still require a dedicated export/archive loader before coverage can exceed the legacy gap. |
| web_whale | 26.17% | 99.94% (1575/1576) | 753 | ❌ | source_history_gap | short_window_public_api | 1603/10 ready (web_snapshot) | age=0.7m / span=151.21h | Forward raw snapshot archive is ready for recent-window diagnostics; keep collection running to extend the archive span, but historical rows before the cutoff still require a dedicated export/archive loader before coverage can exceed the legacy gap. |
| pulse | 35.67% | n/a | 4007 | ❌ | low_coverage | native_timeseries | n/a | n/a | coverage<60% |
| mind | 35.67% | n/a | 4461 | ❌ | low_coverage | native_timeseries | n/a | n/a | coverage<60% |
| aura | 35.67% | n/a | 4512 | ❌ | low_coverage | native_timeseries | n/a | n/a | coverage<60% |
| 4h_vol_ratio | 96.42% | n/a | 3283 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_bias200 | 96.42% | n/a | 12211 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_dist_bb_lower | 96.42% | n/a | 12211 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_ma_order | 96.43% | n/a | 3 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_rsi14 | 96.43% | n/a | 3237 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_macd_hist | 96.43% | n/a | 3238 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_dist_sl | 96.43% | n/a | 12182 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_bias50 | 96.43% | n/a | 12212 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_bias20 | 96.43% | n/a | 12212 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| 4h_bb_pct_b | 96.43% | n/a | 12212 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| nq_return_24h | 99.74% | n/a | 9339 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| vix | 99.91% | n/a | 1434 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| nq_return_1h | 99.92% | n/a | 2742 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| dxy | 99.98% | n/a | 3265 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| body | 100.00% | n/a | 4544 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| tongue | 100.00% | n/a | 4628 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| nose | 100.00% | n/a | 5323 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| vwap_dev | 100.00% | n/a | 12639 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| rsi14 | 100.00% | n/a | 12652 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| bb_pct_b | 100.00% | n/a | 12741 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| ear | 100.00% | n/a | 12747 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| macd_hist | 100.00% | n/a | 12781 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| atr_pct | 100.00% | n/a | 12782 | ✅ | ok | native_timeseries | n/a | n/a | ok |
| eye | 100.00% | n/a | 12830 | ✅ | ok | native_timeseries | n/a | n/a | ok |
