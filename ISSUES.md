# ISSUES.md — Current State Only

_最後更新：2026-05-15 14:27:51 CST_

只保留目前有效問題；由 heartbeat runner overwrite sync，避免 current-state markdown 落後 issues.json / live artifacts。

---

## 當前主線事實
- **最新 full heartbeat #1242 已完成 collect + diagnostics refresh**
  - `Raw=33257 / Features=24444 / Labels=66482`
  - 歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`
  - `simulated_pyramid_win=56.83%`
- **canonical current-live blocker 已切到 current-live exact-support truth**
  - `deployment_blocker=under_minimum_exact_live_structure_bucket` / `streak=—` / `recent_window_wins=—/—` / `additional_recent_window_wins_needed=—`
  - `current_live_structure_bucket=CAUTION|structure_quality_caution|q15` / `support=4/50` / `gap=46` / `support_route_verdict=exact_bucket_present_but_below_minimum`
  - support progress：`status=semantic_rebaseline_under_minimum` / `regression_basis=legacy_or_different_semantic_signature` / `legacy_supported_reference=53/50@20260419b` / `stagnant_run_count=0` / `stalled_support_accumulation=False` / `escalate_to_blocker=True`；active repair：`phase=semantic_evidence_backfill_or_exact_accumulation` / `component_verify_ready=False` / `live_exposure_allowed=False` / `shadow_or_paper_allowed=True` / `current_signal=HOLD` / `current_allowed_layers=0` / `guardrail=under_minimum_exact_live_structure_bucket` / `actions=collect_exact_current_bucket_rows,force_q15_support_audit_refresh,semantic_legacy_evidence_backfill` / `legacy_evidence=reference_only_semantic_mismatch_or_missing_fields` / `legacy_supports_current_identity=False` / `legacy_promotable=False` / `legacy_mismatched=calibration_window,regime_label`
- **recent canonical diagnostics 已刷新**
  - `latest_window=100` / `win_rate=64.0%` / `dominant_regime=chop(75.0%)` / `avg_quality=+0.2965` / `avg_pnl=+0.0081` / `alerts=regime_shift`
  - `blocking_window=250` / `win_rate=60.4%` / `dominant_regime=chop(89.6%)` / `avg_quality=+0.2367` / `avg_pnl=+0.0034` / `alerts=regime_shift`
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=current_full_no_bull_collapse_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split` / `payload_source=latest_persisted_snapshot` / `payload_stale=false` / `payload_age=0.1m`
- **source / venue blockers 仍開啟**
  - `blocked_sparse_features=8` / `{'archive_required': 3, 'snapshot_only': 4, 'short_window_public_api': 1}`
  - top source blockers：`fin_netflow(source_auth_blocked/auth_missing, coverage=0.0%, archive_window=0.0%, forward_archive=ready)` / `claw(source_auth_blocked/auth_missing, coverage=14.6%, archive_window=87.2%, forward_archive=ready)` / `claw_intensity(source_auth_blocked/auth_missing, coverage=14.6%, archive_window=87.2%, forward_archive=ready)` / `nest_pred(source_tls_verify_failed/tls_verify_failed, coverage=16.2%, archive_window=96.9%, forward_archive=ready)`
  - fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=4066` / `archive_window_coverage_pct=0.0`
  - venue：`live exchange credential / order ack lifecycle / fill lifecycle` 尚未有 runtime-backed proof；`execution_metadata_smoke.venues[]` 已提供 per-venue `proof_state / blockers / operator_next_action / verify_next` 給 Dashboard / Execution / Lab 直接顯示證據缺口
- **Execution Console / `/api/trade` 已 fail-closed（同步中 + 阻塞 + 直接 API）**
  - 前端快捷：`manual_buy=paused_when_status_syncing_or_deployment_blocked` / `automation_enable=paused_when_status_syncing_or_deployment_blocked`；`/api/status` 初次同步前與阻塞期間只暫停買入 / 加倉與啟用自動模式，減碼 / 賣出風險降低、切到手動模式、查看阻塞原因與重新整理仍可用。`/api/execution/overview` / `/api/execution/runs` 已走 20s operator-workspace timeout，避免後端並行診斷時 8s default 把可用 payload 誤報成 `API timeout`。後端 `POST /api/trade` 對買入 / 加倉會先讀即時部署阻塞點；阻塞時回 409 `current_live_deployment_blocker`，只保留減倉 / 賣出風險降低路徑；`data/live_predict_probe.json` 同步輸出 `api_trade_guardrail_active / api_trade_buy_guardrail / api_trade_allowed_risk_off_sides` 作為 machine-readable proof
- **Execution Status / Bot 營運 已顯示即時部署阻塞條件**
  - `即時部署阻塞點=under_minimum_exact_live_structure_bucket`；當前 q15 分桶支持樣本=4/50，缺口=46；目前不是熔斷解除數學，候選修補不可取代同分桶最低樣本門檻；`/execution/status` 與 `/execution` 會先顯示即時部署阻塞點，再顯示 當前 q15 分桶 support / 治理背景；`runtime_closure_summary` 已由 `model/runtime_closure.py` 共用中文化，避免後端英文枚舉與混合式治理文案泄漏到 Dashboard / Strategy Lab / Execution Status
- **Live Decision-Quality Drilldown 已產品化語義重訂 / legacy reference guardrail**
  - `data/live_decision_quality_drilldown.json` 與 `docs/analysis/live_decision_quality_drilldown.md` 現在直接輸出 `support_progress_status=semantic_rebaseline_under_minimum`、`regression_basis=legacy_or_different_semantic_signature`、legacy `53/50@20260419b` 只能作歷史參考、`legacy_mismatched=calibration_window,regime_label`，並用繁中 operator copy 明確寫出「語義重訂後仍未達門檻 / 不可宣稱同一語義已閉環」。
  - 驗證：`tests/test_live_decision_quality_drilldown.py` 已鎖定 legacy reference 不得誤導為 exact support 或 deployment closure；本輪 targeted bundle 112/112、hb_parallel_runner docs guardrails 134/134、web build 均通過。
- **Strategy Lab 高信心 OOS 列級訊號 copy 已 operator-safe**
  - `formatHighConvictionRuntimeSignalLabel()` 統一把即時訊號 enum 轉成繁中操作語；最接近部署候選列不再把內部訊號 token 直接丟給 operator，避免 OOS-pass / runtime-blocked 候選被誤讀為可部署動作。
- **heartbeat current-state docs overwrite sync 已自動化**
  - `scripts/hb_parallel_runner.py` 現在會在 `auto_propose_fixes.py` 後自動覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 目的：避免 markdown docs 落後 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json`，讓 cron 心跳真正完成 docs overwrite 閉環

---

## Open Issues

### P0. current live bucket CAUTION|structure_quality_caution|q15 exact support remains under minimum and remains the deployment blocker (4/50)
- 目前真相：`deployment_blocker=under_minimum_exact_live_structure_bucket` / `bucket=CAUTION|structure_quality_caution|q15` / `support=4/50` / `gap=46` / `runtime_closure_state=patch_inactive_or_blocked`
- same-bucket truth：`support_route_verdict=exact_bucket_present_but_below_minimum` / `support_governance_route=exact_live_bucket_present_but_below_minimum` / `recommended_patch=—` / `recommended_patch_status=—` / `reference_scope=—`
- support progress：`status=semantic_rebaseline_under_minimum` / `regression_basis=legacy_or_different_semantic_signature` / `legacy_supported_reference=53/50@20260419b` / `stagnant_run_count=0` / `stalled_support_accumulation=False` / `escalate_to_blocker=True`；active repair：`phase=semantic_evidence_backfill_or_exact_accumulation` / `component_verify_ready=False` / `live_exposure_allowed=False` / `shadow_or_paper_allowed=True` / `current_signal=HOLD` / `current_allowed_layers=0` / `guardrail=under_minimum_exact_live_structure_bucket` / `actions=collect_exact_current_bucket_rows,force_q15_support_audit_refresh,semantic_legacy_evidence_backfill` / `legacy_evidence=reference_only_semantic_mismatch_or_missing_fields` / `legacy_supports_current_identity=False` / `legacy_promotable=False` / `legacy_mismatched=calibration_window,regime_label`
- runtime/API guardrail：`POST /api/trade` 對買入 / 加倉會先讀即時部署阻塞點；阻塞時回 409 `current_live_deployment_blocker`，只保留減倉 / 賣出風險降低路徑。
- 下一步：把 current-live blocker 語義切到 exact-support truth；在 current live bucket 補滿 minimum rows 前，不要把 proxy rows、reference patch、或 breaker 舊敘事誤當成已解除 blocker。

### P0. 建立 high-conviction top-k OOS ROI gate，讓 APP 從研究轉實戰
- 目前真相：`mode_label=模擬觀察_影子驗證_即時阻塞` / `validation=walk_forward_oos_topk_matrix` / `top_k_grid=1%,2%,5%,10%` / `output_artifact=data/high_conviction_topk_oos_matrix.json`
- latest matrix：`generated_at=2026-05-15T06:02:52.854327+00:00` / `freshness=fresh` / `age_min=0.2` / `stale_after_min=60` / `deployment_blocking=False` / `samples=24334` / `rows=24` / `models=logistic_regression,random_forest,xgboost` / `deployable_rows=0` / `risk_qualified_rows=6` / `runtime_blocked_candidates=6` / `support_route=exact_bucket_present_but_below_minimum` / `deployment_blocker=under_minimum_exact_live_structure_bucket` / `current_live_structure_bucket=CAUTION|structure_quality_caution|q15` / `current_live_structure_bucket_rows=4/50` / `current_live_structure_bucket_gap_to_minimum=46`
- nearest deployable candidate：`model=logistic_regression` / `regime=all` / `top_k=top_2pct` / `oos_roi=0.9324` / `win_rate=0.8621` / `profit_factor=19.8864` / `max_drawdown=0.022` / `worst_fold=0.2068` / `trade_count=58` / `tier=runtime_blocked_oos_pass` / `oos_gate_passed=True` / `verdict=not_deployable` / `support_route=exact_bucket_present_but_below_minimum` / `governance=exact_live_bucket_present_but_below_minimum` / `bucket=CAUTION|structure_quality_caution|q15` / `bucket_rows=4/50` / `gap=46`
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

### P1. model stability still needs work (cv=0.6315, cv_std=0.0524, cv_worst=0.5791)
- 目前真相：`cv_accuracy=0.6315248664200575` / `cv_std=0.052404438964241684` / `cv_worst=0.5791204274558158`
- 下一步：優先比較 support-aware / shrinkage profiles 與 current bucket robustness，避免把治理 blocker 誤當單純 parity 問題。

### P1. TW-IC 22 vs Global IC 17 — 信號強依賴近期資料
- 目前真相：`global_pass=17` / `tw_pass=22` / `total_features=30`
- 下一步：市場 regime 可能已變化; 考慮 regime-gated feature weighting

### P1. OKX-only venue readiness is still unverified
- 目前真相：`okx=config enabled + public-only + metadata OK` / `missing_runtime_proof=live exchange credential, order ack lifecycle, fill lifecycle`
- API/UI contract：`execution_metadata_smoke.venues[]` 已帶 `proof_state / blockers / operator_next_action / verify_next`，Dashboard、`/execution/status`、`/execution`、`/lab` 可直接顯示每個場館的實單證據缺口，不再只靠 metadata OK/FAIL 猜測 readiness。
- 下一步：Keep OKX blockers explicitly visible on Dashboard, /lab, and /execution/status until credentials, order ack lifecycle, and fill lifecycle each have runtime-backed proof; legacy venues must stay fail-closed; any readiness UI must require runtime_ready=true plus no blockers.
- 驗證：
  - browser /execution
  - browser /execution/status
  - browser /lab
  - data/execution_metadata_smoke.json
  - PYTHONPATH=. /home/kazuha/Poly-Trader/venv/bin/python scripts/execution_metadata_smoke.py --symbol BTCUSDT
  - PYTHONPATH=. /home/kazuha/Poly-Trader/venv/bin/python /tmp/hb1195_metadata_api_probe.py
  - PYTHONPATH=. /home/kazuha/Poly-Trader/venv/bin/python -m pytest tests/test_execution_metadata_smoke.py tests/test_server_startup.py -k 'execution_metadata_smoke or venue_runtime_proof' tests/test_frontend_decision_contract.py -k 'venue_readiness or runtime_copy_humanizes_execution_governance' -q
  - cd web && npm run build

### P1. fin_netflow remains source_auth_blocked because COINGLASS_API_KEY is missing
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=4066` / `archive_window_coverage_pct=0.0`
- 下一步：Configure COINGLASS_API_KEY, then keep heartbeat collection running until successful ETF-flow snapshots replace auth_missing rows and coverage starts to move.
- 驗證：
  - data/execution_metadata_smoke.json
  - /api/features/coverage

### P1. leaderboard comparable rows are back; keep the recent-window contract stable and cron-safe
- 目前真相：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=current_full_no_bull_collapse_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split` / `payload_source=latest_persisted_snapshot` / `payload_stale=false` / `payload_age=0.1m`
- 下一步：Keep /api/models/leaderboard and Strategy Lab aligned on latest bounded walk-forward plus the recent-two-year backtest policy; do not regress to placeholder-only or ambiguous backtest windows.
- 驗證：
  - browser /lab
  - curl http://127.0.0.1:<active-backend>/api/models/leaderboard
  - pytest tests/test_model_leaderboard.py tests/test_strategy_lab.py tests/test_frontend_decision_contract.py -q

### P1. nest_pred remains blocked by verified Polymarket Gamma TLS trust failure
- 目前真相：`feature=nest_pred` / `quality_flag=source_tls_verify_failed` / `latest_status=tls_verify_failed` / `source=polymarket_gamma` / `trust_policy=tls_verify_required_no_insecure_fallback` / `tls_verification=required`
- 下一步：Fix the Polymarket Gamma TLS trust chain before treating nest_pred as a pure historical coverage gap; keep TLS verification required and do not enable insecure production fallback.
- 驗證：
  - data/heartbeat_1190_summary.json source_blockers.nest_pred
  - PYTHONPATH=. python /tmp/hb1190_nest_tls_probe_after_patch.py
  - pytest tests/test_nest_polymarket.py tests/test_collector_snapshot_archives.py tests/test_feature_history_policy.py -q

### P1. q15 exact support under minimum after semantic rebaseline while breaker is clear (4/50)
- 目前真相：`bucket=CAUTION|structure_quality_caution|q15` / `support=4/50` / `gap=46` / `support_route_verdict=exact_bucket_present_but_below_minimum` / `governance_route=exact_live_bucket_present_but_below_minimum` / `breaker_context=breaker_clear`
- support progress：`status=semantic_rebaseline_under_minimum` / `regression_basis=legacy_or_different_semantic_signature` / `legacy_supported_reference=53/50@20260419b` / `stagnant_run_count=0` / `stalled_support_accumulation=False` / `escalate_to_blocker=True`；active repair：`phase=semantic_evidence_backfill_or_exact_accumulation` / `component_verify_ready=False` / `live_exposure_allowed=False` / `shadow_or_paper_allowed=True` / `current_signal=HOLD` / `current_allowed_layers=0` / `guardrail=under_minimum_exact_live_structure_bucket` / `actions=collect_exact_current_bucket_rows,force_q15_support_audit_refresh,semantic_legacy_evidence_backfill` / `legacy_evidence=reference_only_semantic_mismatch_or_missing_fields` / `legacy_supports_current_identity=False` / `legacy_promotable=False` / `legacy_mismatched=calibration_window,regime_label`
- 下一步：Treat legacy supported rows as reference-only: keep support_identity/regression_basis/legacy_supported_reference visible in probe/API/UI/docs, keep the current-live exact-support blocker open, and do not describe this as same-identity support regression unless the semantic signature matches.

### P1. recent canonical window 250 rows = regime_concentration but current live regime is outside the blocker pocket
- 目前真相：`window=250` / `interpretation=regime_concentration` / `win_rate=0.604` / `dominant_regime=chop` / `dominant_regime_share=0.896` / `avg_pnl=0.0034`
- 下一步：保留 recent canonical drift 監控與 blocker-window evidence；目前 live predictor 沒有套用 recent pathology guardrail，且 current live regime 不等於 blocker dominant regime，因此降為 P1 監控，不得當成 deployment closure。

---

## Current Priority
1. **維持 current-live exact-support blocker truth，同時保留 q15 current-live bucket support rows 可 machine-read**
2. **持續沿 recent canonical pathological slice 追根因，不要 generic 化 blocker**
3. **守住 q15 current-live bucket support truth / semantic rebaseline / blocker truth、leaderboard dual-role governance、venue/source blockers 可見性**
4. **讓 heartbeat 自動 overwrite sync current-state docs，不再把 docs drift 留給人工補寫**
5. **P0 實戰化：建立 high-conviction top-k OOS ROI gate，把研究 winner 轉成可拒單部署候選**
   - `data/high_conviction_topk_oos_matrix.json` 已產出 `generated_at=2026-05-15T06:02:52.854327+00:00` / `freshness=fresh` / `age_min=0.2` / `stale_after_min=60` / `deployment_blocking=False` / `rows=24` / `deployable_rows=0` / `risk_qualified_rows=6` / `runtime_blocked_candidates=6` / `bucket_rows=4/50` / `gap=46`；`/api/models/leaderboard` 與 Strategy Lab 高信心 OOS Top-K 部署門檻面板已改為最接近部署候選優先，並以操作員繁中 copy 顯示矩陣新鮮度、breaker release math 與即時支持脈絡；矩陣過期或即時分桶 / 支持 / release 條件未解除前仍 fail-closed。
