# ISSUES.md — Current State Only

_最後更新：2026-04-24 03:28:21 CST_

只保留目前有效問題；由 heartbeat overwrite sync，避免 current-state markdown 落後 issues.json / live artifacts。

---

## 當前主線事實
- **最新 fast heartbeat #20260424d 已完成 collect + diagnostics refresh**
  - `Raw=32089 / Features=23507 / Labels=64399`
  - `2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`
  - `simulated_pyramid_win=56.99%`
- **canonical current-live blocker 仍是 breaker-first truth**
  - `deployment_blocker=circuit_breaker_active` / `recent_window_wins=14/50` / `additional_recent_window_wins_needed=1` / `streak=0`
  - `current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_proxy_reference_only`
- **recent canonical diagnostics 已刷新**
  - `latest_window=100` / `win_rate=36.0%` / `dominant_regime=bull(99.0%)` / `avg_quality=-0.0395` / `avg_pnl=-0.0025`
  - `alerts=regime_concentration,regime_shift` / `top_shift=feat_local_top_score,feat_turning_point_score,feat_volume_exhaustion` / `new_compressed=feat_dxy`
- **Strategy Lab 工作區 payload / cache 已產品化收斂**
  - `/api/strategies/{name}` 現在會保留完整兩年 `chart_context.start/end`，但把 `equity_curve` 壓到 `<=1000` 點、`score_series` 壓到 `<=300` 點
  - 瀏覽器驗證：`sessionStorage[polytrader.strategylab.cache.v1]` 目前為 `equity_curve=1000` / `score_series=300` / `chart_context.limit=1000`
  - API probe：實際策略 detail payload 已落在 `324162 bytes`，不再把多 MB 明細直接塞進 Strategy Lab 工作區與 session cache
- **leaderboard / governance 與 venue/source blockers 仍維持 current truth**
  - `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active`
  - fin_netflow=`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3557` / `archive_window_coverage_pct=0.0`
  - venue proof 仍缺 `live exchange credential / order ack lifecycle / fill lifecycle`

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
- 目前真相：`deployment_blocker=circuit_breaker_active` / `recent 50 wins=14/50` / `additional_recent_window_wins_needed=1` / `streak=0`
- same-bucket truth：`bucket=BLOCK|bull_q15_bias50_overextended_block|q15` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_proxy_reference_only` / `support_governance_route=exact_live_bucket_proxy_available`
- 下一步：維持 breaker-first release math 作為唯一 current-live blocker；在 breaker 未解除前，不要把 q15/q35 support、floor-gap 或 venue 話題誤升級成主 blocker。

### P0. recent canonical window 100 rows = regime_concentration
- 目前真相：`window=100` / `win_rate=36.0%` / `dominant_regime=bull(99.0%)` / `avg_quality=-0.0395` / `avg_pnl=-0.0025`
- 病態切片：`alerts=regime_concentration,regime_shift` / `adverse_streak=42x0` / `top_shift=feat_local_top_score,feat_turning_point_score,feat_volume_exhaustion` / `new_compressed=feat_dxy`
- 下一步：直接沿 recent canonical rows 做 feature variance / target-path / sibling-window drill-down；維持 decision-quality guardrails，不讓較寬歷史平均值稀釋目前病態 pocket。
- 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`

### P1. support-aware core_plus_macro_plus_all_4h patch must stay visible but reference-only outside current live scope
- 目前真相：`recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_non_current_live_scope` / `reference_scope=bull|CAUTION`
- current live truth：`bucket=BLOCK|bull_q15_bias50_overextended_block|q15` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_proxy_reference_only`
- 下一步：持續讓 `/api/status`、`/lab`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、docs 同步保留 reference-only patch，但禁止誤包裝成可部署 runtime patch。

### P1. venue readiness is still unverified
- 目前真相：`binance=config enabled + public-only + metadata OK` / `okx=config disabled + public-only + metadata OK`
- 缺口：`live exchange credential` / `order ack lifecycle` / `fill lifecycle` 尚未有 runtime-backed proof
- 下一步：保持 Dashboard、`/lab`、`/execution/status` 的 per-venue blocker 可見，直到三條 runtime proof 都落地。
- 驗證：browser `/execution`、browser `/execution/status`、browser `/lab`、`data/execution_metadata_smoke.json`

### P1. fin_netflow remains source_auth_blocked because COINGLASS_API_KEY is missing
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3557` / `archive_window_coverage_pct=0.0`
- 下一步：配置 `COINGLASS_API_KEY`，讓 ETF-flow snapshots 從 auth_missing 轉成成功抓取，再觀察 coverage 是否開始移動。
- 驗證：`data/execution_metadata_smoke.json`、`/api/features/coverage`

### P1. leaderboard comparable rows are back; keep Strategy Lab aligned without payload bloat regression
- 目前真相：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active`
- 本輪已修：Strategy Lab detail payload / cache 已 bounded（`equity_curve<=1000` / `score_series<=300`），且仍保留兩年 `chart_context`
- 下一步：守住 `/api/models/leaderboard`、`/api/strategies/{name}`、Strategy Lab 工作區的一致性，不回退成 placeholder-only、stale detail、或多 MB payload / cache 膨脹。
- 驗證：browser `/lab`、`pytest tests/test_strategy_lab.py tests/test_strategy_lab_manual_model_and_auto_contract.py tests/test_frontend_decision_contract.py -q`、`cd web && npm run build`

### P1. q15 exact support regressed back under minimum under breaker (0/50)
- 目前真相：`bucket=BLOCK|bull_q15_bias50_overextended_block|q15` / `support=0/50` / `gap=50`
- 支持進度：`support_progress.status=regressed_under_minimum` / `recent_supported_reference=#20260423i · 199 rows`
- 下一步：把這條 lane 視為 support regression，而不是普通 stagnation；持續在 probe / API / UI / docs 顯示 `support_route_verdict / support_progress / minimum_support_rows / gap_to_minimum / recent_supported_reference`。

---

## Current Priority
1. **維持 breaker-first truth，同時保留 q15 current-live bucket rows / gap / support route 可 machine-read**
2. **持續沿 recent canonical pathological slice 追根因，不要 generic 化 blocker**
3. **守住 reference-only patch、leaderboard dual-role governance、Strategy Lab bounded payload/cache、venue/source blockers 可見性**
4. **維持 heartbeat docs overwrite sync，避免 docs drift 回來**
