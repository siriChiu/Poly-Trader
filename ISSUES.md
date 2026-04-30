# ISSUES.md — Current State Only

_最後更新：2026-04-30 09:20:10 CST_

只保留目前有效問題；由 heartbeat runner / heartbeat agent overwrite sync，避免 current-state markdown 落後 issues.json / live artifacts / runtime API truth。

---

## 當前主線事實
- **latest full heartbeat #1144 已完成 collect + diagnostics refresh**
  - `Raw=32497 / Features=23915 / Labels=65599`
  - 歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`
  - `simulated_pyramid_win=56.73%`
- **canonical current-live blocker 仍是 exact-support under-minimum truth**
  - `deployment_blocker=under_minimum_exact_live_structure_bucket`
  - `current_live_structure_bucket=CAUTION|structure_quality_caution|q15` / `support=9/50` / `gap=41`
  - `support_route_verdict=exact_bucket_present_but_below_minimum` / `support_governance_route=exact_live_bucket_present_but_below_minimum` / `support_route_deployable=false`
  - `allowed_layers=0` / `signal=HOLD` / `runtime_closure_state=patch_inactive_or_blocked`
  - support progress：`status=semantic_rebaseline_under_minimum` / `regression_basis=legacy_or_different_semantic_signature` / `legacy_supported_reference=53/50@20260419b`
- **recent canonical diagnostics 已刷新**
  - `latest_window=100` / `win_rate=24.0%` / `dominant_regime=chop(87.0%)` / `avg_quality=-0.0602` / `avg_pnl=-0.0043` / `alerts=regime_shift`
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=current_full_no_bull_collapse_4h` / `governance_contract=dual_role_governance_active`
  - `current_closure=global_ranking_vs_support_aware_production_split` / `payload_source=latest_persisted_snapshot` / `payload_stale=false` / `payload_age≈0.1m`
- **本輪產品化修補：Strategy Lab leaderboard cached payload 現在會覆蓋 fresh high-conviction live support overlay**
  - 修補前：`/api/models/leaderboard.high_conviction_topk.support_context` 可從 stale cache 保留 `support_governance_route=exact_live_lane_proxy_available`，與 fresh `live_predict_probe.json` 的 q15 exact under-minimum truth 不一致。
  - 修補後：cached leaderboard 回應每次都重新載入 `data/high_conviction_topk_oos_matrix.json` 並套用 fresh `data/live_predict_probe.json` overlay；runtime 驗證為 `support_governance_route=exact_live_bucket_present_but_below_minimum` / `support=9/50` / `gap=41` / `support_route_deployable=false`。
  - 回歸測試：`tests/test_model_leaderboard.py::test_api_model_leaderboard_refreshes_cached_high_conviction_live_support_overlay`。
- **source / venue blockers 仍開啟**
  - `blocked_sparse_features=8` / `{'archive_required': 3, 'snapshot_only': 4, 'short_window_public_api': 1}`
  - fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3930` / `archive_window_coverage_pct=0.0`
  - venue：`live exchange credential / order ack lifecycle / fill lifecycle` 尚未有 runtime-backed proof；`execution_metadata_smoke.venues[]` 已提供 per-venue `proof_state / blockers / operator_next_action / verify_next` 給 Dashboard / Execution / Lab 直接顯示證據缺口。
- **Execution Console / `/api/trade` 已 fail-closed（同步中 + 阻塞 + 直接 API）**
  - 前端快捷：`manual_buy=paused_when_status_syncing_or_deployment_blocked` / `automation_enable=paused_when_status_syncing_or_deployment_blocked`。
  - 後端 `POST /api/trade` 對買入 / 加倉會先讀即時部署阻塞點；阻塞時回 409 `current_live_deployment_blocker`，只保留減倉 / 賣出風險降低路徑。
- **heartbeat current-state docs overwrite sync 已自動化，且本輪已覆蓋更新**
  - `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md` 已同步到 heartbeat #1144 artifacts 與本輪 runtime overlay patch truth。

---

## Open Issues

### P0. current live bucket CAUTION|structure_quality_caution|q15 exact support remains under minimum and remains the deployment blocker (9/50)
- 目前真相：`deployment_blocker=under_minimum_exact_live_structure_bucket` / `bucket=CAUTION|structure_quality_caution|q15` / `support=9/50` / `gap=41` / `runtime_closure_state=patch_inactive_or_blocked`。
- same-bucket truth：`support_route_verdict=exact_bucket_present_but_below_minimum` / `support_governance_route=exact_live_bucket_present_but_below_minimum` / `support_route_deployable=false`。
- recommended patch：`core_plus_macro_plus_all_4h` 仍是 `reference_only_non_current_live_scope` / `reference_scope=bull|CAUTION`，不可視為 current-live deployable patch。
- 下一步：在 current live bucket 補滿 `minimum_support_rows=50` 前，不要把 proxy rows、reference patch、legacy supported rows 或 high-conviction OOS winner 誤當成已解除 blocker。

### P0. high-conviction top-k OOS ROI gate 必須保持 fresh live support overlay 才能從研究轉實戰
- 目前真相：`data/high_conviction_topk_oos_matrix.json` / `rows=24` / `deployable_rows=0` / `risk_qualified_rows=6` / `runtime_blocked_candidates=6`。
- nearest deployable candidate：`model=logistic_regression` / `regime=all` / `top_k=top_2pct` / `oos_roi=0.9324` / `win_rate=0.8621` / `profit_factor=19.8864` / `max_drawdown=0.022` / `worst_fold=0.2068` / `trade_count=58` / `tier=runtime_blocked_oos_pass` / `verdict=not_deployable`。
- 本輪已修補 API cache hazard：`/api/models/leaderboard` 即使回 cached leaderboard，也會重新覆蓋 high-conviction Top-K 的 live support context；runtime proof 顯示 `support_governance_route=exact_live_bucket_present_but_below_minimum` 而非 stale proxy route。
- 下一步：Strategy Lab 高信心 OOS Top-K 面板可以繼續用 nearest-deployable 排序，但即時分桶 / 支持 / venue proof 未過前仍維持 `模擬觀察 / 影子驗證 / 僅觀察`。
- 驗證：
  - `source venv/bin/activate && python -m pytest tests/test_model_leaderboard.py -q`
  - `source venv/bin/activate && python /tmp/hb1144_leaderboard_runtime_verify.py`
  - browser `/lab` raw-token probe：no probed raw deployment/support tokens visible；API resources loaded。

### P1. live predictor decision-quality contract is runtime-blocked by recent pathology, a toxic exact live lane, or a severe narrowed pathology lane
- 目前真相：`live_scope=regime_gate+entry_quality_label` / `deployment_blocker=under_minimum_exact_live_structure_bucket` / `window=100` / `alerts=regime_shift` / `allowed_layers=0`。
- 下一步：把 hb_predict_probe 納入每輪 heartbeat 驗證，對 exact live lane、當前 calibration scope 與 worst narrowed scope 做 root-cause drill-down；避免把 exact-support blocker 泛化成 generic model/venue 問題。

### P1. model stability still needs work (cv=0.6506, cv_std=0.1127, cv_worst=0.5379)
- 目前真相：`cv_accuracy=0.65060745705907` / `cv_std=0.1126937578550482` / `cv_worst=0.5379136992040218`。
- 下一步：優先比較 support-aware / shrinkage profiles 與 current bucket robustness，避免把治理 blocker 誤當單純 model parity 問題。

### P1. TW-IC 28 vs Global IC 19 — 信號強依賴近期資料
- 目前真相：`global_pass=19` / `tw_pass=28` / `total_features=30`。
- 下一步：市場 regime 可能已變化；考慮 regime-gated feature weighting，但不得繞過 current-live support blocker。

### P1. support-aware core_plus_macro_plus_all_4h patch must stay visible but reference-only outside current live scope
- 目前真相：`bucket=CAUTION|structure_quality_caution|q15` / `support=9/50` / `gap=41` / `support_route_verdict=exact_bucket_present_but_below_minimum` / `governance_route=exact_live_bucket_present_but_below_minimum`。
- 下一步：Keep the same recommended_patch summary across `/api/status`, `/lab`, `hb_predict_probe.py`, `live_decision_quality_drilldown.py`, and docs；patch describes a spillover/broader lane rather than the current live scope, so do not promote it to deployable runtime patch.

### P1. venue readiness is still unverified
- 目前真相：`binance=config enabled + public-only + metadata OK` / `okx=config disabled + public-only + metadata OK` / `missing_runtime_proof=live exchange credential, order ack lifecycle, fill lifecycle`。
- API/UI contract：`execution_metadata_smoke.venues[]` 已帶 `proof_state / blockers / operator_next_action / verify_next`，Dashboard、`/execution/status`、`/execution`、`/lab` 可直接顯示每個場館的實單證據缺口。
- 下一步：Keep per-venue blockers explicitly visible until credentials, order ack lifecycle, and fill lifecycle each have runtime-backed proof.

### P1. fin_netflow remains source_auth_blocked because COINGLASS_API_KEY is missing
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3930` / `archive_window_coverage_pct=0.0`。
- 下一步：Configure COINGLASS_API_KEY, then keep heartbeat collection running until successful ETF-flow snapshots replace auth_missing rows and coverage starts to move.

### P1. leaderboard comparable rows are back; keep recent-window and live-overlay contracts stable and cron-safe
- 目前真相：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=current_full_no_bull_collapse_4h` / `payload_source=latest_persisted_snapshot` / `payload_stale=false`。
- 本輪補強：cached `/api/models/leaderboard` now refreshes high-conviction live support overlay at request time, preventing stale cached support governance from overriding fresh q15 under-minimum truth.
- 下一步：Keep `/api/models/leaderboard` and Strategy Lab aligned on latest bounded walk-forward plus the recent-two-year backtest policy; do not regress to placeholder-only, ambiguous backtest windows, or stale live support overlays.

---

## Current Priority
1. **維持 current-live exact-support blocker truth，同時保留 q15 current-live bucket support rows 可 machine-read**。
2. **守住 high-conviction Top-K OOS winner 的 fail-closed live support overlay：OOS 過關 ≠ current-live deployable**。
3. **持續沿 recent canonical pathological slice 追根因，不要 generic 化 blocker**。
4. **守住 q15 current-live bucket support / reference-only patch、leaderboard dual-role governance、venue/source blockers 可見性**。
5. **保持 heartbeat docs overwrite sync 與 API runtime truth 同輪收斂**。
