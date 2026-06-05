# ISSUES.md — Current State Only

_最後更新：2026-06-05 11:47:06 CST_

只保留目前有效問題；由 heartbeat runner overwrite sync，避免 current-state markdown 落後 issues.json / live artifacts。

---

## 當前主線事實
- **最新 fast heartbeat #adhoc_codex_20260605_pivot_quick_read_final_docs_resync 已完成 diagnostics refresh（collect skipped）**
  - `Raw=35124 / Features=25839 / Labels=69413`
  - `strategy_data_sync_maintenance.attempted=false` / `success=true` / `reason=freshness_within_headroom` / `lanes=none` / `headroom_min=10.0`
  - 歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`
  - `simulated_pyramid_win=56.09%`
- **canonical current-live blocker 以 latest runtime truth 為主**
  - `deployment_blocker=exact_live_lane_toxic_sub_bucket_current_bucket` / `streak=—` / `recent_window_wins=—/—` / `additional_recent_window_wins_needed=—`
  - `current_live_structure_bucket=BLOCK|bias200_below_min|q00` / `support=131/50` / `gap=0` / `support_route_verdict=exact_bucket_supported`
  - support progress：`status=exact_supported` / `reason=current live exact bucket 已達 minimum support，可轉向 exact-supported deployment verify。` / `regression_basis=current_identity` / `current_rows=131` / `minimum_rows=50` / `gap_to_minimum=0` / `support_rows_needed=0` / `previous_rows=131` / `delta_vs_previous=0` / `legacy_supported_reference=—` / `stagnant_run_count=4` / `stalled_support_accumulation=False` / `escalate_to_blocker=False` / `governance_reference_route=exact_live_bucket_supported` / `exact_live_lane_proxy_rows=10` / `governance_reference_only=False`
  - `live_canary_structural_pivot.current_lane_actionability=no_trade_block_lane` / `support_evidence_role=no_trade_decision_validation_not_deployable_support` / `map_signal_forced_lane=no_trade_lane_audit`；當前即時 lane 是 BLOCK / 不交易決策 lane。0/50 exact support 應視為無風險觀望驗證，不是可收集來支撐買入 / 加倉部署的 support。 next=data/no_trade_lane_replay.json；驗證觀望 / reduce-only 行為，不把它寫成 risk-on support closure。
  - live-canary structural pivot quick-read：`artifact=data/live_canary_structural_pivot.json` / `quick_read.deployment_blocker=exact_live_lane_toxic_sub_bucket_current_bucket` / `bucket=BLOCK|bias200_below_min|q00` / `actionability=no_trade_block_lane` / `support=131/50` / `gap=0` / `support_route=exact_bucket_supported` / `release_ready=true` / `recent_window_wins=20/15` / `additional_recent_window_wins_needed=0` / `deployable_rows=0` / `paper_shadow_available=true` / `venue_runtime_ready=false` / `live_canary_policy_ready=false` / `micro_canary_ready=false` / `order_submission_enabled=false` / `single_failed_gate_for_72h_decision=model_shadow_outcome_gate` / `next_validation_artifact=data/high_conviction_topk_oos_matrix.json + Shadow Trade Ledger 24h pyramid outcome rows`；這是 72h hard-gate summary，不是 live clearance。
  - `no_trade_lane_replay.verdict=validated_abstain_reduce_only_no_trade_lane` / `validated=True` / `deployable=False` / `risk_on_order_enabled=False` / `order_submission_enabled=False` / `buy_add_support_closure_allowed=False` / `support=131/50` / `checks_all_passed=True`；這是觀望 / reduce-only / paper-shadow replay proof，不是 risk-on support closure。
- **PM handoff support-fill feasibility 已納入 current-state docs**
  - `artifact=data/q15_support_fill_feasibility.json` / `classification=current_identity_support_ready` / `bucket=BLOCK|bias200_below_min|q00` / `exact_rows=131/50` / `identity_rows=183` / `non_bucket_identity_rows=52` / `gap=0` / `time_to_evidence=ready_for_remaining_live_execution_gates` / `missing_capability=Review` / `alternative_solution_required=False`；next safe artifact：data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy；reference windows / governance rows 不可包裝成 deployable support。
- **Exact bucket row-harvest proof 已納入 current-state docs**
  - `artifact=data/q15_exact_bucket_row_harvest_proof.json` / `status=exact_bucket_row_harvest_support_ready_remaining_gates` / `bucket=BLOCK|bias200_below_min|q00` / `exact_rows=131/50` / `previous_rows=131` / `delta=0` / `identity_rows=183` / `non_bucket_identity_rows=52` / `gap=0` / `time_to_evidence=ready_for_remaining_live_execution_gates` / `primary_failed_gate=remaining_live_gates` / `live_exposure_allowed=false` / `order_submission_enabled=false`；row harvest proof 只證明 exact support movement，不可單獨當成 deployment clearance。
- **drift-aware rebaseline proof 已納入 forced-execution current-state docs**
  - `artifact=data/q15_drift_rebaseline_backtest.json` / `status=current_identity_support_ready_rebaseline_not_needed` / `candidate=—` / `candidate_status=—` / `current_window_rows=None/50` / `all_history_rows=None` / `current_exact=131/50` / `gap=0` / `primary_failed_gate=current_live_support_gate` / `live_exposure_allowed=false` / `order_submission_enabled=false` / `recent_drift=100:0.21:bear`；歷史 rebaseline candidate 只能作 OOS replay / redesign 參考，不可當成 current-live deployment clearance。
- **Map/Signal redesign proof 已納入 forced-execution current-state docs**
  - `artifact=data/q15_map_signal_redesign_proof.json` / `status=map_signal_redesign_no_current_window_deployable_candidate` / `candidate=dominant_neighbor_exact_lane` / `candidate_status=count_ready_metric_rejected` / `target_bucket=BLOCK|bear_bias200_hard_block|q00` / `current_window_rows=28/50` / `all_history_rows=174` / `best_reference=best_historical_exact_lane_bucket:133` / `root_cause=same_lane_neighbor_bucket_dominates:structure_component_scoring:feat_4h_bb_pct_b` / `dominant_neighbor=BLOCK|bear_bias200_hard_block|q00:174` / `primary_failed_gate=current_live_support_gate` / `live_exposure_allowed=false` / `order_submission_enabled=false`；Map/Signal redesign rows are replay inputs only until current-window support, OOS, support audit, API guardrail, venue, and bounded-canary gates pass.
- **Customer-safe alternative quick-read proof 已納入 current-state truth**
  - `artifact=data/customer_safe_alternative_proof.json` / `live_exposure_allowed=false` / `order_submission_enabled=false` / `risk_on_order_enabled=false` / `primary_blocking_gate=model_gate` / `support=131/50` / `gap=0` / `topk_deployable_rows=0` / `topk_support_context_status=fresh_live_probe_overlay` / `topk_support_context_freshness=fresh` / `topk_support_context_deployment_blocking=false` / `topk_live_truth_overlay_blocker=—` / `venue_status=blocked_missing_runtime_backed_proof` / `blocked_live_lanes=3` / `alternative_solution_required=false` / `alternative_solution_options=3` / `selected_alternative=paper_shadow_decision_support_sleeve` / `next_customer_actions=4` / `selected_next_artifact=data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy`；alternatives=paper_shadow_decision_support_sleeve,
    semantic_rebaseline_review, venue_dry_run_readiness_proof；next_actions=open_execution_paper_shadow, review_strategy_lab_topk_shadow_candidates, verify_venue_dry_run_lifecycle, track_breaker_and_exact_support；blocked_live=live_buy_add_exposure, risk_on_automation_enable, unbounded_live_canary；這是 paper/shadow / dry-run / reduce-only proof，不是 live-ready 訊號。
- **anti-equilibrium forced execution governor 已啟用**
  - trigger：`delta_vs_previous=0` / `stagnant_run_count=4` 或使用者指出趨近平衡時，heartbeat 不得只刷新 observation-only status；必須選 Venue lifecycle proof / Model shadow to decision / Strategy micro-canary readiness / Map-Signal redesign / hard no-go single failed gate。
  - forced branches：Venue lifecycle proof / Model shadow to decision / Strategy micro-canary readiness / Map-Signal redesign / hard no-go single failed gate。
  - bounded live-canary：任何 live buy/add pilot 必須有 `execution.live_canary.enabled=true`、explicit `allowed_symbols`、symbol-specific `max_base_qty_by_symbol`，缺 policy 或超 cap 會在 adapter 前拒單。
- **recent canonical diagnostics 已刷新**
  - `latest_window=100` / `win_rate=21.0%` / `dominant_regime=bear(94.0%)` / `avg_quality=-0.1998` / `avg_pnl=-0.0106` / `alerts=regime_concentration,regime_shift`
  - shadow-only falsification：`mode=shadow_only_no_new_risk_falsification` / `deployable=false` / `risk_on_order_enabled=false` / `order_submission_enabled=false` / `baseline_win_rate=21.0%` / `best_gate=observable_4h_shift_shadow_gate` / `kept_rows=93` / `kept_win_rate=21.5%` / `loss_capture=7.6%` / `operator=僅限 paper/shadow；熔斷、support 與 venue gate 仍 fail-closed`
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=6` / `selected_feature_profile=core_plus_macro` / `support_aware_profile=current_full_no_bull_collapse_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split` / `payload_source=latest_persisted_snapshot` / `payload_stale=false` / `payload_age=2.8m`
- **source / venue blockers 仍開啟**
  - `blocked_sparse_features=8` / `{'archive_required': 3, 'snapshot_only': 4, 'short_window_public_api': 1}`
  - top source blockers：`fin_netflow(source_auth_blocked/auth_missing, coverage=0.0%, archive_window=0.0%, forward_archive=stale, next=configure [REDACTED] source credentials)` / `claw(source_auth_blocked/auth_missing, coverage=13.8%, archive_window=71.6%, forward_archive=stale, next=configure [REDACTED] source credentials)` / `claw_intensity(source_auth_blocked/auth_missing, coverage=13.8%, archive_window=71.6%, forward_archive=stale, next=configure [REDACTED] source credentials)` / `nest_pred(source_tls_verify_failed/tls_verify_failed, coverage=15.4%, archive_window=79.6%, forward_archive=stale)`
  - fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=4959` / `archive_window_coverage_pct=0.0`
  - venue：`generated_at=2026-06-05T03:46:51.433403Z` / `venues_checked=2` / `ok_count=1` / `runtime_ready_count=0` / `runtime_ready=false` / `readiness_state=blocked_until_runtime_lifecycle_proof` / `runtime_ready_blockers=fill lifecycle 尚未驗證|live exchange credential 尚未驗證|order ack lifecycle 尚未驗證|元資料契約尚未通過|場館 adapter 尚未接入`；`okx=adapter_supported=true,enabled_in_config=true,credentials_configured=false,proof_state=public_metadata_only,runtime_ready=false,blockers=live exchange credential 尚未驗證|order ack lifecycle 尚未驗證|fill lifecycle 尚未驗證` / `binance=adapter_supported=false,enabled_in_config=false,credentials_configured=false,proof_state=adapter_unsupported,runtime_ready=false,blockers=場館 adapter 尚未接入|元資料契約尚未通過|場館設定停用`；`execution_metadata_smoke.venues[]` 已提供 per-venue `adapter_supported / enabled_in_config / credentials_configured / proof_state / runtime_ready / blockers /
    operator_next_action / verify_next` 給 Dashboard / Execution / Lab 直接顯示 adapter、credential boolean 與證據缺口；operator UI 會先 humanize backend error（例如 `unsupported venue` → `不支援的交易場館`），避免 raw venue error 洩漏到操作員畫面
  - venue dry-run proof：`artifact=data/venue_dry_run_proof.json` / `venue_dry_run_status=blocked_missing_runtime_backed_proof` / `generated_at=2026-06-05T03:46:52.260101Z` / `runtime_ready=false` / `runtime_ready_count=0` / `venues_checked=2` / `order_submission_enabled=false` / `risk_on_order_enabled=false` / `dry_run_only=true` / `ack=blocked_missing_credentials` / `cancel=blocked_missing_credentials` / `fill=blocked_missing_credentials` / `reconciliation=blocked_missing_credentials`；`okx=preview=blocked_missing_credentials,runtime_ready=false,credentials_configured=false` / `binance=preview=blocked_adapter_unsupported,runtime_ready=false,credentials_configured=false`；standalone artifact 可重跑、只做 dry-run preview / ack / cancel / fill / reconciliation checklist，`order_submission_enabled=false`。
- **Execution Console / `/api/trade` 已 fail-closed（同步中 + 阻塞 + 直接 API）**
  - 前端快捷：`manual_buy=paused_when_status_syncing_or_deployment_blocked` / `automation_enable=paused_when_status_syncing_or_deployment_blocked`；`/api/status` 初次同步前與阻塞期間只暫停買入 / 加倉與啟用自動模式，減碼 / 賣出風險降低、等待 / 觀望、切到手動模式、查看阻塞原因與重新整理仍可用。`/api/status` / `/api/execution/overview` / `/api/execution/runs` 已走 20s operator-workspace timeout，避免後端並行診斷或冷啟動時 8s default 把可用 payload 誤報成 `API timeout` / `載入失敗`。後端 `POST /api/trade` 對買入 / 加倉會先讀即時部署阻塞點；阻塞時真實買入 / 加倉回 409 `current_live_deployment_blocker`，仍保留等待 / 觀望、減倉 / 賣出風險降低，以及 `shadow_buy` / `paper_buy` 強制 dry-run paper/shadow 演練路徑；`data/live_predict_probe.json` 同步輸出 `api_trade_guardrail_active / api_trade_buy_guardrail / api_trade_allowed_risk_off_sides` 作為 machine-readable proof
  - active backend health：`active_backend_health_probe=passed` / `returncode=0` / `strict_ok=True` / `head_sync_status=current_head_commit` / `raw_continuity=clean` / `feature_continuity=clean` / `restart_required=False` / `process_started_at=2026-06-05T03:29:18.793814+00:00` / `source=http://127.0.0.1:8000/health`；heartbeat runner 會在 API operator proof 前 fail-fast，stale backend 不可被當成 current truth。
- **Dashboard 啟動連續性 guardrail 已納入 feature deferred truth**
  - `/api/status.feature_continuity.status=deferred` 或 `repair_deferred=true` 時，Dashboard 連續性卡改用警示色並顯示 `特徵缺口已延後到心跳維護收斂`；避免 raw continuity clean/repaired 時，把啟動期 feature 缺口誤讀成全綠。
- **Execution Status / Bot 營運 已顯示即時部署阻塞條件**
  - `即時部署阻塞點=exact_live_lane_toxic_sub_bucket_current_bucket`；當前 q00 分桶支持樣本=131/50，缺口=0；目前不是熔斷解除數學，候選修補不可取代同分桶最低樣本門檻；`/execution/status` 與 `/execution` 會先顯示即時部署阻塞點，再顯示 當前 q00 分桶 support / 治理背景；`runtime_closure_summary` 已由 `model/runtime_closure.py` 共用中文化，避免後端 bucket / route / source / reference raw token 泄漏到 Dashboard / Strategy Lab / Execution Status / live DQ operator markdown
- **Live DQ drilldown operator-facing markdown 已 enum-safe**
  - `docs/analysis/live_decision_quality_drilldown.md` 的 operator header、support summary、精準支持路徑、跨門檻 verdict、recommended patch 來源 / 範圍改用繁中標籤；machine JSON 保留 raw enum，operator markdown 不再洩漏後端 bucket / route / source / reference raw token。
- **Strategy Lab 高信心 OOS 列級訊號 copy 已 operator-safe**
  - `formatHighConvictionRuntimeSignalLabel()` 統一把即時訊號 enum 轉成繁中操作語；最接近部署候選列不再把內部訊號 token 直接丟給 operator，避免 OOS-pass / runtime-blocked 候選被誤讀為可部署動作。
- **Execution Console 高信心 Top-K 影子觀察入口已產品化**
  - `risk_qualified_rows=6` / `runtime_blocked_candidates=6` / `deployable_rows=0` / `paper_shadow=true` / `risk_on_order_enabled=false` / `support=131/50` / `gap=0`；高信心 Top-K OOS 候選已可在 Execution Console selective sleeve 啟動影子觀察：只鏡像即時決策、事件紀錄、帳戶與對帳摘要，不送單、不加倉；等即時支持、場館證據鏈與單一 Bot 帳本全部通過後才能升級小流量。
- **Paper/shadow worker outcome reconciliation 已納入 current-state truth**
  - `artifact=data/paper_shadow_outcome_reconciliation.json` / `status=recording_with_resolved_outcomes` / `rehearsal_status=resolved_evidence_ready` / `worker_poll_events=1` / `pending_outcomes=0` / `resolved_outcomes=1` / `awaiting_label_replay=0` / `can_poll_workers=true` / `poll_blocked_by_pending_outcome=false` / `order_submission_enabled=false` / `risk_on_order_enabled=false` / `live_order_submitted=false` / `next_reconcile_at=—` / `current_pending_hours_remaining_hours=—` / `artifact_pending_hours_remaining_hours=None`；這是 24h 演練證據與 pending guard，不是 live-ready 訊號。
- **高低震盪 / 擁塞實戰拆解已產品化（fail-closed）**
  - `support=131/50` / `gap=0` / `paper_shadow=true` / `risk_on_order_enabled=false` / `order_submission_enabled=false` / `reduce_risk_allowed=true`；震盪不是停工，也不是永遠不能實戰：Bot 營運與 `/api/status.range_chop_playbook` 會把高低震盪拆成區間影子觀察、減碼 / 取消掛單與證據收集；進攻買入 / 加倉與啟用自動模式仍鎖住，必須等即時部署門檻與場館證據鏈通過。
- **M5 實戰準備度總卡已產品化**
  - 模型 gate / 即時支持 gate / 熔斷 gate / 場館 gate / live-canary policy gate / 影子觀察 gate 一次顯示；credential present 只顯示布林 / 狀態，不輸出 secret；影子觀察與減風險可前進，買入 / 加倉仍鎖住。
  - `/api/status` 會載入 `data/venue_dry_run_proof.json` 並在 `execution_surface_contract.live_canary_policy_gate` 顯示本地 bounded-canary policy gate；Dashboard / Execution Status / Strategy Lab status-only summaries 也會顯示同一 gate 與繁中 blocker copy；`/api/execution/overview` artifact-first 輸出 `execution_readiness / shadow_trade_ledger / venue_dry_run_proof / customer_safe_alternative_proof / canary_gap_answers`，且可用 `scripts/venue_dry_run_api_consistency_probe.py --strict` 驗證 status / overview / artifact 同源、fail-closed、secret-safe，並可用 `scripts/customer_safe_alternative_api_consistency_probe.py --strict` 驗證 customer-safe overview / artifact aliases、counts、selected next artifact、fail-closed、secret-safe 同源；`data/customer_safe_alternative_proof.json` / `docs/analysis/customer_safe_alternative_proof.md` 會把 PM alternative-solution handoff 濃縮成 customer-safe proof。
- **heartbeat current-state docs overwrite sync 已自動化**
  - `scripts/hb_parallel_runner.py` 現在會在 `auto_propose_fixes.py` 後自動覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 目的：避免 markdown docs 落後 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json / data/q15_support_fill_feasibility.json / data/q15_exact_bucket_row_harvest_proof.json / data/q15_drift_rebaseline_backtest.json / data/q15_map_signal_redesign_proof.json / data/no_trade_lane_replay.json / data/paper_shadow_outcome_reconciliation.json / data/execution_metadata_smoke.json / data/venue_dry_run_proof.json / data/leaderboard_feature_profile_probe.json / data/high_conviction_topk_oos_matrix.json`，讓 cron 心跳真正完成 docs overwrite 閉環

---

## Open Issues

### P0. current live bucket BLOCK|bias200_below_min|q00 is exact-lane toxic despite exact support (131 rows; minimum=50)
- 目前真相：`deployment_blocker=exact_live_lane_toxic_sub_bucket_current_bucket` / `primary_blocker=exact_live_lane_toxic_sub_bucket_current_bucket` / `circuit_breaker_active=False` / `current_live_structure_bucket=BLOCK|bias200_below_min|q00` / `current_live_structure_bucket_rows=131` / `minimum_support_rows=50`
- 下一步：把 current live bucket 視為 hold-only；維持 toxic sub-bucket blocker 在 runtime/docs 的 machine-read truth，直到 bucket-level win/quality 明顯改善。

### P0. current-live deployment blocker is exact_live_lane_toxic_sub_bucket_current_bucket
- 目前真相：`deployment_blocker=exact_live_lane_toxic_sub_bucket_current_bucket` / `bucket=BLOCK|bias200_below_min|q00` / `support=131/50` / `gap=0` / `runtime_closure_state=deployment_guardrail_blocks_trade`
- same-bucket truth：`support_route_verdict=exact_bucket_supported` / `support_governance_route=exact_live_bucket_supported` / `recommended_patch=—` / `recommended_patch_status=—` / `reference_scope=—`
- support progress：`status=exact_supported` / `reason=current live exact bucket 已達 minimum support，可轉向 exact-supported deployment verify。` / `regression_basis=current_identity` / `current_rows=131` / `minimum_rows=50` / `gap_to_minimum=0` / `support_rows_needed=0` / `previous_rows=131` / `delta_vs_previous=0` / `legacy_supported_reference=—` / `stagnant_run_count=4` / `stalled_support_accumulation=False` / `escalate_to_blocker=False` / `governance_reference_route=exact_live_bucket_supported` / `exact_live_lane_proxy_rows=10` / `governance_reference_only=False`
- runtime/API guardrail：`POST /api/trade` 對買入 / 加倉會先讀即時部署阻塞點；阻塞時真實買入 / 加倉回 409 `current_live_deployment_blocker`，仍保留等待 / 觀望、減倉 / 賣出風險降低，以及 `shadow_buy` / `paper_buy` 強制 dry-run paper/shadow 演練路徑。
- 下一步：把 current-live blocker 真相維持在 API / UI / docs；不要讓舊 breaker / support 敘事覆蓋最新 runtime truth。

### P0. 建立 high-conviction top-k OOS ROI gate，讓 APP 從研究轉實戰
- 目前真相：`mode_label=模擬觀察_影子驗證_即時阻塞` / `validation=walk_forward_oos_topk_matrix` / `top_k_grid=1%,2%,5%,10%` / `output_artifact=data/high_conviction_topk_oos_matrix.json`
- latest matrix：`generated_at=2026-06-05T03:43:30.458510+00:00` / `freshness=fresh` / `age_min=3.6` / `stale_after_min=60` / `deployment_blocking=False` / `samples=25814` / `rows=24` / `models=logistic_regression,random_forest,xgboost` / `deployable_rows=0` / `risk_qualified_rows=6` / `runtime_blocked_candidates=6` / `support_route=exact_bucket_supported` / `deployment_blocker=exact_live_lane_toxic_sub_bucket_current_bucket` / `current_live_structure_bucket=BLOCK|bias200_below_min|q00` / `current_live_structure_bucket_rows=131/50` / `current_live_structure_bucket_gap_to_minimum=0` / `support_progress_status=exact_supported` / `support_progress_reason=current live exact bucket 已達 minimum support，可轉向 exact-supported deployment verify。` / `regression_basis=current_identity` / `delta_vs_previous=0` / `previous_rows=131` / `support_rows_needed=0` / `stagnant_run_count=4` / `stalled_support_accumulation=False` / `escalate_to_blocker=False`
- nearest deployable candidate：`model=logistic_regression` / `regime=all` / `top_k=top_2pct` / `oos_roi=0.9324` / `win_rate=0.8621` / `profit_factor=19.8864` / `max_drawdown=0.022` / `worst_fold=0.2068` / `trade_count=58` / `tier=runtime_blocked_oos_pass` / `oos_gate_passed=True` / `verdict=not_deployable` / `support_route=exact_bucket_supported` / `governance=exact_live_bucket_supported` / `bucket=BLOCK|bias200_below_min|q00` / `bucket_rows=131/50` / `gap=0` / `support_progress_status=exact_supported` / `support_progress_reason=current live exact bucket 已達 minimum support，可轉向 exact-supported deployment verify。` / `regression_basis=current_identity` / `delta_vs_previous=0` / `previous_rows=131` / `support_rows_needed=0` / `stagnant_run_count=4` / `stalled_support_accumulation=False` / `escalate_to_blocker=False`
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

### P1. Train-CV gap = 16.8pp (66.6% vs 49.8%)
- 下一步：更正則化: 增加 reg_alpha/reg_lambda; 減少 max_depth; 或減少特徵數

### P1. live predictor decision-quality contract is runtime-blocked by recent pathology, a toxic exact live lane, or a severe narrowed pathology lane
- 目前真相：`live_scope=regime_label+regime_gate+entry_quality_label` / `deployment_blocker=exact_live_lane_toxic_sub_bucket_current_bucket` / `window=100` / `alerts=regime_concentration, regime_shift` / `allowed_layers=0`
- 下一步：把 hb_predict_probe 納入每輪 heartbeat 驗證，對 exact live lane、當前 calibration scope 與 worst narrowed scope 做 root-cause drill-down；優先檢查 exact lane 是否仍是 ALLOW 但 canonical true-negative share 已偏高，並交叉比對 recent same-scope / narrowed-scope 4H shifts、scope selection、與 execution guardrail 是否只是正確地把壞 pocket 擋下。 live_scope=regime_label+regime_gate+entry_quality_label, regime=bear/BLOCK, label=D, sample_size=183, window=100, alerts=['label_imbalance'], expected_win_rate=0.2, expected_pnl=-0.01, expected_quality=-0.1916, layers=0→0,…

### P1. model stability still needs work (cv=0.4976, cv_std=0.0332, cv_worst=0.4644)
- 目前真相：`cv_accuracy=0.4975560081466395` / `cv_std=0.03319755600814664` / `cv_worst=0.46435845213849286`
- 下一步：優先比較 support-aware / shrinkage profiles 與 current bucket robustness，避免把治理 blocker 誤當單純 parity 問題。

### P1. TW-IC 22 vs Global IC 16 — 信號強依賴近期資料
- 目前真相：`global_pass=16` / `tw_pass=22` / `total_features=30`
- 下一步：市場 regime 可能已變化; 考慮 regime-gated feature weighting

### P1. OKX/Binance venue readiness is still unverified
- 目前真相：`generated_at=2026-06-05T03:46:51.433403Z` / `venues_checked=2` / `ok_count=1` / `runtime_ready_count=0` / `runtime_ready=false` / `readiness_state=blocked_until_runtime_lifecycle_proof` / `runtime_ready_blockers=fill lifecycle 尚未驗證|live exchange credential 尚未驗證|order ack lifecycle 尚未驗證|元資料契約尚未通過|場館 adapter 尚未接入`；`okx=adapter_supported=true,enabled_in_config=true,credentials_configured=false,proof_state=public_metadata_only,runtime_ready=false,blockers=live exchange credential 尚未驗證|order ack lifecycle 尚未驗證|fill lifecycle 尚未驗證` / `binance=adapter_supported=false,enabled_in_config=false,credentials_configured=false,proof_state=adapter_unsupported,runtime_ready=false,blockers=場館 adapter 尚未接入|元資料契約尚未通過|場館設定停用`
- API/UI contract：`execution_metadata_smoke.venues[]` 已帶 `adapter_supported / enabled_in_config / credentials_configured / proof_state / runtime_ready / blockers / operator_next_action / verify_next`，Dashboard、`/execution/status`、`/execution`、`/lab` 必須直接顯示 OKX 與 Binance 每個場館的 adapter、credential boolean 與實單證據缺口；`runtime_ready=true` 且 blockers 清空前不可宣稱 canary / live-ready。
- 下一步：Keep OKX runtime-proof blockers and Binance unsupported/disabled blockers explicitly visible on Dashboard, /lab, and /execution/status until credentials, order ack lifecycle, and fill lifecycle each have runtime-backed proof; unsupported venues must stay fail-closed; any readiness UI must require runtime_ready=true plus no blockers.
- 驗證：
  - browser /execution
  - browser /execution/status
  - browser /lab
  - data/execution_metadata_smoke.json
  - PYTHONPATH=. /home/kazuha/Poly-Trader/venv/bin/python scripts/execution_metadata_smoke.py --symbol BTCUSDT --venues okx binance
  - PYTHONPATH=. /home/kazuha/Poly-Trader/venv/bin/python /tmp/hb1195_metadata_api_probe.py
  - PYTHONPATH=. /home/kazuha/Poly-Trader/venv/bin/python -m pytest tests/test_execution_metadata_smoke.py tests/test_server_startup.py -k 'execution_metadata_smoke or venue_runtime_proof' tests/test_frontend_decision_contract.py -k 'venue_readiness or runtime_copy_humanizes_execution_governance' -q
  - cd web && npm run build

### P1. fin_netflow remains source_auth_blocked because [REDACTED] is missing
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=4959` / `archive_window_coverage_pct=0.0`
- 下一步：Configure [REDACTED], then keep heartbeat collection running until successful ETF-flow snapshots replace auth_missing rows and coverage starts to move.
- 驗證：
  - data/execution_metadata_smoke.json
  - /api/features/coverage

### P1. leaderboard comparable rows are back; keep the recent-window contract stable and cron-safe
- 目前真相：`leaderboard_count=6` / `selected_feature_profile=core_plus_macro` / `support_aware_profile=current_full_no_bull_collapse_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split` / `payload_source=latest_persisted_snapshot` / `payload_stale=false` / `payload_age=2.8m`
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

---

## Current Priority
1. **維持 current-live blocker truth（exact_live_lane_toxic_sub_bucket_current_bucket），同時保留 q00 current-live bucket support rows 可 machine-read**
2. **持續沿 recent canonical pathological slice 追根因，不要 generic 化 blocker**
3. **守住 q00 current-live bucket support truth / blocker truth、leaderboard dual-role governance、venue/source blockers 可見性**
4. **反平衡強制執行：same semantic signature + support delta=0 時必須選 forced branch，不得 observation-only**
5. **讓 heartbeat 自動 overwrite sync current-state docs，不再把 docs drift 留給人工補寫**
6. **P0 實戰化：建立 high-conviction top-k OOS ROI gate，把研究 winner 轉成可拒單部署候選**
   - `data/high_conviction_topk_oos_matrix.json` 已產出 `generated_at=2026-06-05T03:43:30.458510+00:00` / `freshness=fresh` / `age_min=3.6` / `stale_after_min=60` / `deployment_blocking=False` / `rows=24` / `deployable_rows=0` / `risk_qualified_rows=6` / `runtime_blocked_candidates=6` / `bucket_rows=131/50` / `gap=0` / `release_ready=True` / `recent_window_wins=20/50` / `required_recent_window_wins=15` / `additional_recent_window_wins_needed=0` / `current_recent_window_win_rate=0.400` / `support_progress_status=exact_supported` / `support_progress_reason=current live exact bucket 已達 minimum support，可轉向 exact-supported deployment verify。` / `regression_basis=current_identity` / `delta_vs_previous=0` / `previous_rows=131` / `support_rows_needed=0` / `stagnant_run_count=4` / `stalled_support_accumulation=False` / `escalate_to_blocker=False`；
     `/api/models/leaderboard` 與 Strategy Lab 高信心 OOS Top-K 部署門檻面板已改為最接近部署候選優先，並以操作員繁中 copy 顯示矩陣新鮮度、breaker release math 與即時支持脈絡；矩陣過期或即時分桶 / 支持 / release 條件未解除前仍 fail-closed。
