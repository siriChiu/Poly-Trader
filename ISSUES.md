# ISSUES.md — Current State Only

_最後更新：2026-05-08 17:17:25 CST_

只保留目前有效問題；由 heartbeat runner overwrite sync，避免 current-state markdown 落後 issues.json / live artifacts。

---

## 當前主線事實
- **最新 fast heartbeat #1185 已完成 collect + diagnostics refresh**
  - `Raw=32850 / Features=24201 / Labels=66040`
  - 歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`
  - `simulated_pyramid_win=56.79%`
- **canonical 即時部署阻塞仍是熔斷優先真相**
  - `deployment_blocker=circuit_breaker_active` / `streak=28` / `recent_window_wins=11/50` / `additional_recent_window_wins_needed=4`
  - `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_proxy_reference_only`
  - support progress：`status=regressed_under_minimum` / `regression_basis=same_identity_same_semantic_signature` / `legacy_supported_reference=122/50@1094` / `stagnant_run_count=0` / `stalled_support_accumulation=False` / `escalate_to_blocker=True`；active repair：`phase=semantic_evidence_backfill_or_exact_accumulation` / `component_verify_ready=False` / `live_exposure_allowed=False` / `shadow_or_paper_allowed=True` / `current_signal=CIRCUIT_BREAKER` / `current_allowed_layers=0` / `guardrail=decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active` / `actions=collect_exact_current_bucket_rows,force_q15_support_audit_refresh,semantic_legacy_evidence_backfill` / `legacy_evidence=reference_only_semantic_mismatch_or_missing_fields` / `legacy_supports_current_identity=False` / `legacy_promotable=False` / `legacy_mismatched=calibration_window`
- **recent canonical diagnostics 已刷新**
  - `latest_window=100` / `win_rate=60.0%` / `dominant_regime=bull(74.0%)` / `avg_quality=+0.2836` / `avg_pnl=+0.0067` / `alerts=regime_shift`
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=current_full_no_bull_collapse_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split` / `payload_source=latest_persisted_snapshot` / `payload_stale=false` / `payload_age=0.2m`
- **source / venue blockers 仍開啟**
  - `blocked_sparse_features=8` / `{'archive_required': 3, 'snapshot_only': 4, 'short_window_public_api': 1}`
  - fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3986` / `archive_window_coverage_pct=0.0`
  - venue：`live exchange credential / order ack lifecycle / fill lifecycle` 尚未有 runtime-backed proof；`execution_metadata_smoke.venues[]` 已提供 per-venue `proof_state / blockers / operator_next_action / verify_next` 給 Dashboard / Execution / Lab 直接顯示證據缺口
- **Execution Console / `/api/trade` 已 fail-closed（同步中 + 阻塞 + 直接 API）**
  - 前端快捷：`manual_buy=paused_when_status_syncing_or_deployment_blocked` / `automation_enable=paused_when_status_syncing_or_deployment_blocked`；`/api/status` 初次同步前與阻塞期間只暫停買入 / 加倉與啟用自動模式，減碼 / 賣出風險降低、切到手動模式、查看阻塞原因與重新整理仍可用。`/api/execution/overview` / `/api/execution/runs` 已走 20s operator-workspace timeout，避免後端並行診斷時 8s default 把可用 payload 誤報成 `API timeout`。後端 `POST /api/trade` 對買入 / 加倉會先讀即時部署阻塞點；阻塞時回 409 `current_live_deployment_blocker`，只保留減倉 / 賣出風險降低路徑；`data/live_predict_probe.json` 同步輸出 `api_trade_guardrail_active / api_trade_buy_guardrail / api_trade_allowed_risk_off_sides` 作為 machine-readable proof
- **Execution Status / Bot 營運 已顯示熔斷解除條件**
  - `最近 50 筆目前 11/50，還差 4 勝；當前 q15 分桶支持樣本 / 候選修補不可取代熔斷解除條件`；`/execution/status` 與 `/execution` 會先顯示熔斷解除條件，再顯示 當前 q15 分桶 support / 治理背景
- **heartbeat current-state docs overwrite sync 已自動化**
  - `scripts/hb_parallel_runner.py` 現在會在 `auto_propose_fixes.py` 後自動覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 目的：避免 markdown docs 落後 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json`，讓 cron 心跳真正完成 docs overwrite 閉環

---

## Open Issues

### P0. 熔斷解除條件仍是唯一即時部署阻塞點
- 目前真相：`deployment_blocker=circuit_breaker_active` / `streak=28` / `recent 50 wins=11/50` / `additional_recent_window_wins_needed=4`
- same-bucket truth：`bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=0/50` / `support_route_verdict=exact_bucket_missing_proxy_reference_only` / `support_governance_route=exact_live_bucket_proxy_available`
- support progress：`status=regressed_under_minimum` / `regression_basis=same_identity_same_semantic_signature` / `legacy_supported_reference=122/50@1094` / `stagnant_run_count=0` / `stalled_support_accumulation=False` / `escalate_to_blocker=True`；active repair：`phase=semantic_evidence_backfill_or_exact_accumulation` / `component_verify_ready=False` / `live_exposure_allowed=False` / `shadow_or_paper_allowed=True` / `current_signal=CIRCUIT_BREAKER` / `current_allowed_layers=0` / `guardrail=decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active` / `actions=collect_exact_current_bucket_rows,force_q15_support_audit_refresh,semantic_legacy_evidence_backfill` / `legacy_evidence=reference_only_semantic_mismatch_or_missing_fields` / `legacy_supports_current_identity=False` / `legacy_promotable=False` / `legacy_mismatched=calibration_window`
- runtime/API guardrail：`POST /api/trade` 對買入 / 加倉會先讀即時部署阻塞點；阻塞時回 409 `current_live_deployment_blocker`，只保留減倉 / 賣出風險降低路徑。
- 下一步：先把即時部署阻塞語義切回熔斷解除條件；在熔斷未解除前，不要把 q15/q35 support 或 floor-gap 當成本輪主阻塞。 最近 50 筆需至少 15 勝，當前 11 勝，還差 4 勝；同時連續虧損必須 < 50。

### P0. 建立 high-conviction top-k OOS ROI gate，讓 APP 從研究轉實戰
- 目前真相：`mode_label=模擬觀察_影子驗證_即時阻塞` / `validation=walk_forward_oos_topk_matrix` / `top_k_grid=1%,2%,5%,10%` / `output_artifact=data/high_conviction_topk_oos_matrix.json`
- latest matrix：`generated_at=2026-05-08T09:17:10.116831+00:00` / `freshness=fresh` / `age_min=0.3` / `stale_after_min=60` / `deployment_blocking=False` / `samples=24131` / `rows=24` / `models=logistic_regression,random_forest,xgboost` / `deployable_rows=0` / `risk_qualified_rows=6` / `runtime_blocked_candidates=6` / `support_route=exact_bucket_missing_proxy_reference_only` / `deployment_blocker=circuit_breaker_active` / `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15` / `current_live_structure_bucket_rows=0/50` / `current_live_structure_bucket_gap_to_minimum=50`
- nearest deployable candidate：`model=logistic_regression` / `regime=all` / `top_k=top_2pct` / `oos_roi=0.9324` / `win_rate=0.8621` / `profit_factor=19.8864` / `max_drawdown=0.022` / `worst_fold=0.2068` / `trade_count=58` / `tier=runtime_blocked_oos_pass` / `oos_gate_passed=True` / `verdict=not_deployable` / `support_route=exact_bucket_missing_proxy_reference_only` / `governance=exact_live_bucket_proxy_available` / `bucket=CAUTION|base_caution_regime_or_bias|q15` / `bucket_rows=0/50` / `gap=50`
- 研究依據：`basis=walk_forward_oos,purged_cv,triple_barrier_pyramid_label,meta_labeling_take_skip,conformal_uncertainty_reject,regime_aware_deployment` / `目的=只讓高信心、低回撤、經 OOS 驗證的金字塔候選進入部署候選`
- 部署門檻：`min_trades>=50` / `win_rate>=0.6` / `max_drawdown<=0.08` / `profit_factor>=1.5` / `worst_fold=non_negative_or_above_baseline` / `support_route=deployable`
- 目前 scan 只能作線索：`model=catboost` / `roi=0.1978` / `win_rate=0.6216` / `max_drawdown=0.0655` / `trades=37` / `status_label=研究觀察_不可部署`
- 下一步：把 high-conviction top-k 從 ROI-only 觀測列升級為風控 / 離線驗證 / 部署門檻優先排序；nearest-deployable 候選優先顯示，但即時分桶 / 支持阻塞未解除前仍維持模擬觀察 / 影子驗證 / 僅觀察。
- 驗證：
  - data/high_conviction_topk_oos_matrix.json rows[].deployable_verdict/gate_failures
  - source venv/bin/activate && PYTHONPATH=. python -m pytest tests/test_topk_walkforward_precision.py -q
  - source venv/bin/activate && PYTHONPATH=. python scripts/topk_walkforward_precision.py
  - source venv/bin/activate && python -m pytest tests/test_model_leaderboard.py tests/test_frontend_decision_contract.py -k high_conviction -q
  - Strategy Lab 高信心 OOS Top-K 部署門檻面板與 /api/models/leaderboard.high_conviction_topk 顯示 walk-forward top-k OOS matrix；即時分桶 / 支持阻塞未解除前仍 fail-closed，且 UI 使用操作員繁中 copy
  - source venv/bin/activate && python -m pytest tests/test_topk_walkforward_precision.py -k nearest_deployable -q && python -m pytest tests/test_model_leaderboard.py -k high_conviction_topk -q && python -m pytest tests/test_frontend_decision_contract.py -k high_conviction_topk_gate_contract -q
  - PYTHONPATH=. python /tmp/hb1148_verify_topk_api.py
  - source venv/bin/activate && PYTHONPATH=. python -m pytest tests/test_model_leaderboard.py::test_high_conviction_topk_support_context_uses_fresher_live_probe -q
  - source venv/bin/activate && PYTHONPATH=. python -m pytest tests/test_model_leaderboard.py::test_high_conviction_topk_live_support_overlay_fail_closes_stale_deployable_rows -q

### P1. model stability still needs work (cv=0.6251, cv_std=0.0856, cv_worst=0.5395)
- 目前真相：`cv_accuracy=0.6250521920668058` / `cv_std=0.08559498956158662` / `cv_worst=0.5394572025052192`
- 下一步：優先比較 support-aware / shrinkage profiles 與 current bucket robustness，避免把治理 blocker 誤當單純 parity 問題。

### P1. TW-IC 24 vs Global IC 19 — 信號強依賴近期資料
- 目前真相：`global_pass=19` / `tw_pass=24` / `total_features=30`
- 下一步：市場 regime 可能已變化; 考慮 regime-gated feature weighting

### P1. support-aware core_plus_macro_plus_all_4h patch must stay visible but reference-only outside current live scope
- 目前真相：`bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_proxy_reference_only` / `governance_route=exact_live_bucket_proxy_available`
- support progress：`status=regressed_under_minimum` / `regression_basis=same_identity_same_semantic_signature` / `legacy_supported_reference=122/50@1094` / `stagnant_run_count=0` / `stalled_support_accumulation=False` / `escalate_to_blocker=True`；active repair：`phase=semantic_evidence_backfill_or_exact_accumulation` / `component_verify_ready=False` / `live_exposure_allowed=False` / `shadow_or_paper_allowed=True` / `current_signal=CIRCUIT_BREAKER` / `current_allowed_layers=0` / `guardrail=decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active` / `actions=collect_exact_current_bucket_rows,force_q15_support_audit_refresh,semantic_legacy_evidence_backfill` / `legacy_evidence=reference_only_semantic_mismatch_or_missing_fields` / `legacy_supports_current_identity=False` / `legacy_promotable=False` / `legacy_mismatched=calibration_window`
- 下一步：Keep the same recommended_patch summary across /api/status, /lab, hb_predict_probe.py, live_decision_quality_drilldown.py, and docs; the patch describes a spillover/broader lane rather than the current live scope, so do not promote it to a deployable runtime patch even though exact support is available.

### P1. OKX-only venue readiness is still unverified
- 目前真相：`okx=config enabled + public-only + metadata OK` / `missing_runtime_proof=live exchange credential, order ack lifecycle, fill lifecycle`
- API/UI contract：`execution_metadata_smoke.venues[]` 已帶 `proof_state / blockers / operator_next_action / verify_next`，Dashboard、`/execution/status`、`/execution`、`/lab` 可直接顯示每個場館的實單證據缺口，不再只靠 metadata OK/FAIL 猜測 readiness。
- 下一步：Keep OKX blockers explicitly visible on Dashboard, /lab, and /execution/status until credentials, order ack lifecycle, and fill lifecycle each have runtime-backed proof; legacy venues must stay fail-closed.
- 驗證：
  - browser /execution
  - browser /execution/status
  - browser /lab
  - data/execution_metadata_smoke.json

### P1. fin_netflow remains source_auth_blocked because COINGLASS_API_KEY is missing
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3986` / `archive_window_coverage_pct=0.0`
- 下一步：Configure COINGLASS_API_KEY, then keep heartbeat collection running until successful ETF-flow snapshots replace auth_missing rows and coverage starts to move.
- 驗證：
  - data/execution_metadata_smoke.json
  - /api/features/coverage

### P1. leaderboard comparable rows are back; keep the recent-window contract stable and cron-safe
- 目前真相：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=current_full_no_bull_collapse_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split` / `payload_source=latest_persisted_snapshot` / `payload_stale=false` / `payload_age=0.2m`
- 下一步：Keep /api/models/leaderboard and Strategy Lab aligned on latest bounded walk-forward plus the recent-two-year backtest policy; do not regress to placeholder-only or ambiguous backtest windows.
- 驗證：
  - browser /lab
  - curl http://127.0.0.1:<active-backend>/api/models/leaderboard
  - pytest tests/test_model_leaderboard.py tests/test_strategy_lab.py tests/test_frontend_decision_contract.py -q

### P1. q15 exact support regressed under minimum while breaker is active (0/50)
- 目前真相：`bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_proxy_reference_only` / `governance_route=exact_live_bucket_proxy_available` / `breaker_context=circuit_breaker_active`
- support progress：`status=regressed_under_minimum` / `regression_basis=same_identity_same_semantic_signature` / `legacy_supported_reference=122/50@1094` / `stagnant_run_count=0` / `stalled_support_accumulation=False` / `escalate_to_blocker=True`；active repair：`phase=semantic_evidence_backfill_or_exact_accumulation` / `component_verify_ready=False` / `live_exposure_allowed=False` / `shadow_or_paper_allowed=True` / `current_signal=CIRCUIT_BREAKER` / `current_allowed_layers=0` / `guardrail=decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active` / `actions=collect_exact_current_bucket_rows,force_q15_support_audit_refresh,semantic_legacy_evidence_backfill` / `legacy_evidence=reference_only_semantic_mismatch_or_missing_fields` / `legacy_supports_current_identity=False` / `legacy_promotable=False` / `legacy_mismatched=calibration_window`
- 下一步：Treat this as support regression, not ordinary stagnation: keep support_route_verdict/support_progress/minimum_support_rows/gap_to_minimum plus the last-supported reference visible in probe/API/UI/docs, verify why the current bucket fell back under minimum, and keep breaker context explicit.

---

## Current Priority
1. **維持熔斷優先真相，同時保留 q15 current-live bucket support rows 可 machine-read**
2. **持續沿 recent canonical pathological slice 追根因，不要 generic 化 blocker**
3. **守住 q15 current-live bucket support / reference-only patch、leaderboard dual-role governance、venue/source blockers 可見性**
4. **讓 heartbeat 自動 overwrite sync current-state docs，不再把 docs drift 留給人工補寫**
5. **P0 實戰化：建立 high-conviction top-k OOS ROI gate，把研究 winner 轉成可拒單部署候選**
   - `data/high_conviction_topk_oos_matrix.json` 已產出 `generated_at=2026-05-08T09:17:10.116831+00:00` / `freshness=fresh` / `age_min=0.3` / `stale_after_min=60` / `deployment_blocking=False` / `rows=24` / `deployable_rows=0` / `risk_qualified_rows=6` / `runtime_blocked_candidates=6` / `bucket_rows=0/50` / `gap=50`；`/api/models/leaderboard` 與 Strategy Lab 高信心 OOS Top-K 部署門檻面板已改為最接近部署候選優先，並以操作員繁中 copy 顯示矩陣新鮮度與即時支持脈絡；矩陣過期或即時分桶 / 支持阻塞未解除前仍 fail-closed。
