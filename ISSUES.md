# ISSUES.md — Current State Only

_最後更新：2026-04-22 08:40:05 CST_

只保留目前有效問題；由 heartbeat runner overwrite sync，避免 current-state markdown 落後 issues.json / live artifacts。

---

## 當前主線事實
- **最新 fast heartbeat #20260422l 已完成 collect + diagnostics refresh**
  - `Raw=31455 / Features=22873 / Labels=63429`
  - `simulated_pyramid_win=57.21%`
- **canonical current-live blocker 以 latest runtime truth 為主**
  - `deployment_blocker=—` / `streak=None` / `recent_window_wins=None/None` / `additional_recent_window_wins_needed=—`
  - `current_live_structure_bucket=CAUTION|structure_quality_caution|q35` / `support=73/50` / `gap=0` / `support_route_verdict=exact_bucket_supported`
- **recent canonical diagnostics 已刷新**
  - `latest_window=1000` / `win_rate=38.0%` / `dominant_regime=bull(82.0%)` / `avg_quality=+0.0667` / `avg_pnl=+0.0001` / `alerts=regime_shift`
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- **source / venue blockers 仍開啟**
  - `blocked_sparse_features=8` / `{'archive_required': 3, 'snapshot_only': 4, 'short_window_public_api': 1}`
  - fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=2925` / `archive_window_coverage_pct=0.0`
  - venue：`live exchange credential / order ack lifecycle / fill lifecycle` 尚未有 runtime-backed proof
- **heartbeat current-state docs overwrite sync 已自動化**
  - `scripts/hb_parallel_runner.py` 現在會在 `auto_propose_fixes.py` 後自動覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 目的：避免 markdown docs 落後 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json`，讓 cron 心跳真正完成 docs overwrite 閉環

---

## Open Issues

### P0. recent canonical window 1000 rows = regime_concentration
- 目前真相：`window=1000` / `win_rate=38.0%` / `dominant_regime=bull(82.0%)` / `avg_quality=+0.0667` / `avg_pnl=+0.0001` / `alerts=regime_shift`
- 病態切片：`alerts=regime_shift` / `tail_streak=—` / `top_shift=feat_4h_bias200,feat_vwap_dev,feat_dxy` / `new_compressed=feat_vix`
- 下一步：直接對 recent canonical rows 做 feature variance / distinct-count / target-path drill-down；維持 decision-quality guardrails，並檢查 calibration scope 是否仍被病態 slice 稀釋。 recent_window=1000, alerts=['regime_shift'], win_rate=0.3800, delta_vs_full=-0.2458, dominant_regime=bull(82.00%), interpretation=regime_concentration, avg_pnl=+0.0001, avg_quality=0.0667, avg_dd_penalty=0.2365, spot_long_win_rate=0.1650, feature_diag=variance:7/56, frozen:0, compressed:7, expected_static:0, overlay_only:1, unexpected_frozen:0, distinct:10, null_heavy:10, tail_streak=19x1 since 2026-04-21 00:05:39.160858 -> 2026-04-21 01:31:46.693117, adverse_streak=273x0 since 2026-04-17 13:41:12.414408 -> 2026-04-18 13:43:25.809469, prev_win_rate=0.903, delta_vs_prev=-0.523, prev_quality=0.5183, quality_delta_vs_prev=-0.4516, prev_pnl=0.014, pnl_delta_vs_prev=-0.0139, top_shift_examples=feat_4h_bias200(4.1376→7.6436,Δσ=0.6416)/feat_vwap_dev(-0.3109→-0.1783,Δσ=0.5897)/feat_dxy(98.4949→98.1334,Δσ=0.3487), new_compressed=feat_vix, compressed_examples=feat_body(0.0001/998)/feat_ear(0.0103/996)/feat_tongue(0.0144/997), overlay_only_examples=feat_scales_ssr[research_sparse_source], distinct_examples=feat_4h_dist_swing_high(0/0)/feat_chorus(0/0)/feat_fin_netflow(0/0), null_examples=feat_4h_dist_swing_high(0.0)/feat_chorus(0.0)/feat_fin_netflow(0.0), recent_examples=2026-04-21 01:16:17.454932:1:bull:0.3879/2026-04-21 01:29:52.484270:1:bull:0.3425/2026-04-21 01:31:46.693117:1:bull:0.3243, adverse_examples=2026-04-18 13:00:00.000000:0:bull:-0.2342/2026-04-18 13:36:43.970223:0:bull:-0.2119/2026-04-18 13:43:25.809469:0:bull:-0.2137
- 驗證：
  - python scripts/recent_drift_report.py
  - python scripts/hb_predict_probe.py

### P1. venue readiness is still unverified
- 目前真相：`binance=config enabled + public-only + metadata OK` / `okx=config disabled + public-only + metadata OK` / `missing_runtime_proof=live exchange credential, order ack lifecycle, fill lifecycle`
- 下一步：Keep per-venue blockers explicitly visible on Dashboard, /lab, and /execution/status until credentials, order ack lifecycle, and fill lifecycle each have runtime-backed proof.
- 驗證：
  - browser /execution
  - browser /execution/status
  - browser /lab
  - data/execution_metadata_smoke.json

### P1. fin_netflow remains source_auth_blocked because COINGLASS_API_KEY is missing
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=2925` / `archive_window_coverage_pct=0.0`
- 下一步：Configure COINGLASS_API_KEY, then keep heartbeat collection running until successful ETF-flow snapshots replace auth_missing rows and coverage starts to move.
- 驗證：
  - data/execution_metadata_smoke.json
  - /api/features/coverage

### P1. leaderboard comparable rows are back; keep the recent-window contract stable and cron-safe
- 目前真相：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- 下一步：Keep /api/models/leaderboard and Strategy Lab aligned on latest bounded walk-forward plus the recent-two-year backtest policy; do not regress to placeholder-only or ambiguous backtest windows.
- 驗證：
  - browser /lab
  - curl http://127.0.0.1:<active-backend>/api/models/leaderboard
  - pytest tests/test_model_leaderboard.py tests/test_strategy_lab.py tests/test_frontend_decision_contract.py -q

---

## Current Priority
1. **維持 current-live blocker truth（—），同時保留 current live bucket support rows 可 machine-read**
2. **持續沿 recent canonical pathological slice 追根因，不要 generic 化 blocker**
3. **守住 current live bucket support / recommended patch、leaderboard dual-role governance、venue/source blockers 可見性**
4. **讓 heartbeat 自動 overwrite sync current-state docs，不再把 docs drift 留給人工補寫**
