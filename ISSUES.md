# ISSUES.md — Current State Only

_最後更新：2026-07-28 22:47:07 CST_

只保留目前有效問題；由 heartbeat runner overwrite sync，避免 current-state markdown 落後 issues.json / live artifacts。

---

## 當前主線事實
- **最新 fast heartbeat #58 已完成 diagnostics refresh（collect skipped）**
  - `Raw=38682 / Features=29357 / Labels=76425`
  - `strategy_data_sync_maintenance.attempted=false` / `success=true` / `reason=freshness_within_headroom` / `lanes=none` / `headroom_min=10.0`
  - 歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`
  - `simulated_pyramid_win=57.36%`
- **canonical 即時部署阻塞仍是熔斷優先真相**
  - `deployment_blocker=circuit_breaker_active` / `streak=35` / `recent_window_wins=13/50` / `additional_recent_window_wins_needed=2`
  - `current_live_structure_bucket=BLOCK|structure_quality_block|q00` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_unsupported_block`
  - support progress：`status=stalled_under_minimum` / `reason=current live exact support 連續 heartbeat 停在同一數量，屬於 support accumulation 停滯。` / `regression_basis=same_identity_same_semantic_signature` / `current_rows=0` / `minimum_rows=50` / `gap_to_minimum=50` / `support_rows_needed=50` / `previous_rows=0` / `delta_vs_previous=0` / `legacy_supported_reference=—` / `stagnant_run_count=2` / `stalled_support_accumulation=True` / `escalate_to_blocker=False` / `equilibrium_deadlock=equilibrium_deadlock_watch` / `equilibrium_deadlock_confirmed=False` / `forced_research_action_required=True` / `forced_research_action_output=data/equilibrium_deadlock_research_action.json` / `governance_reference_route=exact_live_lane_proxy_available` / `exact_live_lane_proxy_rows=43` / `governance_reference_only=True`；active repair：`phase=current_bucket_first` / `component_verify_ready=False` /
    `live_exposure_allowed=False` / `shadow_or_paper_allowed=True` / `current_signal=CIRCUIT_BREAKER` / `current_allowed_layers=0` / `guardrail=decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active` / `actions=collect_exact_current_bucket_rows,force_q15_support_audit_refresh,semantic_signature_map_signal_redesign_or_row_harvest,equilibrium_deadlock_research_action` / `forced_branch_status=hard_no_go_recorded` / `forced_branch_selected=hard_no_go_single_failed_gate` / `single_failed_gate=circuit_breaker_gate` / `next_validation_artifact=data/circuit_breaker_audit.json` / `decision_clock=72h_micro_canary_or_single_failed_gate`
  - `live_canary_structural_pivot.current_lane_actionability=no_trade_block_lane` / `support_evidence_role=no_trade_decision_validation_not_deployable_support` / `map_signal_forced_lane=no_trade_lane_audit`；當前即時 lane 是 BLOCK / 不交易決策 lane。精準支持 0/50 只可視為無風險觀望驗證，不可視為買入 / 加倉部署 closure。 next=data/no_trade_lane_replay.json；驗證觀望 / reduce-only 行為，不把它寫成 risk-on support closure。
  - live-canary structural pivot quick-read：`artifact=data/live_canary_structural_pivot.json` / `quick_read.deployment_blocker=circuit_breaker_active` / `bucket=BLOCK|structure_quality_block|q00` / `actionability=no_trade_block_lane` / `support=0/50` / `gap=50` / `support_route=exact_bucket_unsupported_block` / `release_ready=false` / `recent_window_wins=13/15` / `additional_recent_window_wins_needed=2` / `deployable_rows=0` / `paper_shadow_available=false` / `venue_runtime_ready=false` / `live_canary_policy_ready=false` / `micro_canary_ready=false` / `order_submission_enabled=false` / `single_failed_gate_for_72h_decision=circuit_breaker_gate` / `next_validation_artifact=data/circuit_breaker_audit.json after 24h canonical tail outcomes improve`；這是 72h hard-gate summary，不是 live clearance。
  - `no_trade_lane_replay.verdict=validated_abstain_reduce_only_no_trade_lane` / `validated=True` / `deployable=False` / `risk_on_order_enabled=False` / `order_submission_enabled=False` / `buy_add_support_closure_allowed=False` / `support=0/50` / `checks_all_passed=True`；這是觀望 / reduce-only / paper-shadow replay proof，不是 risk-on support closure。
- **PM handoff support-fill feasibility 已納入 current-state docs**
  - `artifact=data/q15_support_fill_feasibility.json` / `classification=true_support_under_minimum` / `bucket=BLOCK|structure_quality_block|q00` / `exact_rows=0/50` / `identity_rows=0` / `non_bucket_identity_rows=0` / `gap=50` / `time_to_evidence=unknown_until_exact_identity_rows_start_accumulating` / `missing_capability=Signal/Support` / `alternative_solution_required=True`；next safe artifact：data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy；reference windows / governance rows 不可包裝成 deployable support。
- **Exact bucket row-harvest proof 已納入 current-state docs**
  - `artifact=data/q15_exact_bucket_row_harvest_proof.json` / `status=exact_bucket_row_harvest_no_current_rows` / `bucket=BLOCK|structure_quality_block|q00` / `exact_rows=0/50` / `previous_rows=0` / `delta=0` / `identity_rows=0` / `non_bucket_identity_rows=0` / `gap=50` / `time_to_evidence=unknown_until_exact_identity_rows_start_accumulating` / `primary_failed_gate=current_live_support_gate` / `live_exposure_allowed=false` / `order_submission_enabled=false`；row harvest proof 只證明 exact support movement，不可單獨當成 deployment clearance。
- **drift-aware rebaseline proof 已納入 forced-execution current-state docs**
  - `artifact=data/q15_drift_rebaseline_backtest.json` / `status=no_rebaseline_candidate_found` / `candidate=—` / `candidate_status=—` / `current_window_rows=None/50` / `all_history_rows=None` / `current_exact=0/50` / `gap=50` / `primary_failed_gate=current_live_support_gate` / `live_exposure_allowed=false` / `order_submission_enabled=false` / `recent_drift=100:0.63:chop`；歷史 rebaseline candidate 只能作 OOS replay / redesign 參考，不可當成 current-live deployment clearance。
- **Map/Signal redesign proof 已納入 forced-execution current-state docs**
  - `artifact=data/q15_map_signal_redesign_proof.json` / `status=map_signal_redesign_reference_only_current_window_unproven` / `candidate=dominant_neighbor_exact_lane` / `candidate_status=reference_candidate_current_window_empty` / `target_bucket=BLOCK|structure_overextended_block|q85` / `current_window_rows=0/50` / `all_history_rows=338` / `best_reference=dominant_neighbor_exact_lane:338` / `root_cause=runtime_blocker_preempts_bucket_root_cause:—:—` / `dominant_neighbor=BLOCK|structure_overextended_block|q85:233` / `primary_failed_gate=current_window_support_gate` / `live_exposure_allowed=false` / `order_submission_enabled=false`；Map/Signal redesign rows are replay inputs only until current-window support, OOS, support audit, API guardrail, venue, and bounded-canary gates pass.
- **Customer-safe alternative quick-read proof 已納入 current-state truth**
  - `artifact=data/customer_safe_alternative_proof.json` / `live_exposure_allowed=false` / `order_submission_enabled=false` / `risk_on_order_enabled=false` / `primary_blocking_gate=circuit_breaker_gate` / `support=0/50` / `gap=50` / `topk_deployable_rows=0` / `topk_support_context_status=fresh_live_probe_overlay` / `topk_support_context_freshness=fresh` / `topk_support_context_deployment_blocking=false` / `topk_live_truth_overlay_blocker=—` / `venue_status=blocked_missing_runtime_backed_proof` / `blocked_live_lanes=3` / `alternative_solution_required=true` / `alternative_solution_options=3` / `selected_alternative=paper_shadow_decision_support_sleeve` / `next_customer_actions=4` / `selected_next_artifact=data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy`；alternatives=paper_shadow_decision_support_sleeve,
    semantic_rebaseline_review, venue_dry_run_readiness_proof；next_actions=open_execution_paper_shadow, review_strategy_lab_topk_shadow_candidates, verify_venue_dry_run_lifecycle, track_breaker_and_exact_support；blocked_live=live_buy_add_exposure, risk_on_automation_enable, unbounded_live_canary；這是 paper/shadow / dry-run / reduce-only proof，不是 live-ready 訊號。
- **LOB/order-flow minimum contract 已納入 current-state docs**
  - `artifact=data/microstructure_contract.json` / `status=observation_only` / `source_configured=true` / `source_available=true` / `source_freshness=ready` / `artifact_freshness=fresh` / `coverage=21/21` / `forecast_edge_bps=None` / `forecast_source=unavailable` / `decision_status=observation_only` / `paper_shadow_risk_on_allowed=false` / `live_risk_on_allowed=false`；缺source或forecast calibration時維持 observation-only，不把OOS/Top-K proxy當dynamic edge。
- **anti-equilibrium forced execution governor 已啟用**
  - trigger：`delta_vs_previous=0` / `stagnant_run_count=2` / `stalled_support_accumulation=true` 或使用者指出趨近平衡時，heartbeat 不得只刷新 observation-only status；必須選 Venue lifecycle proof / Model shadow to decision / Strategy micro-canary readiness / Map-Signal redesign / hard no-go single failed gate。
  - forced branches：Venue lifecycle proof / Model shadow to decision / Strategy micro-canary readiness / Map-Signal redesign / hard no-go single failed gate。
  - bounded live-canary：任何 live buy/add pilot 必須有 `execution.live_canary.enabled=true`、explicit `allowed_symbols`、symbol-specific `max_base_qty_by_symbol`，缺 policy 或超 cap 會在 adapter 前拒單。
- **recent canonical diagnostics 已刷新**
  - `latest_window=250` / `win_rate=50.8%` / `dominant_regime=chop(82.8%)` / `avg_quality=+0.1327` / `avg_pnl=-0.0010` / `alerts=regime_shift`
  - shadow-only falsification：`mode=shadow_only_no_new_risk_falsification` / `deployable=false` / `risk_on_order_enabled=false` / `order_submission_enabled=false` / `baseline_win_rate=63.0%` / `best_gate=dominant_regime_shadow_gate` / `kept_rows=43` / `kept_win_rate=100.0%` / `loss_capture=100.0%` / `operator=僅限 paper/shadow；熔斷、support 與 venue gate 仍 fail-closed`
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=0` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split` / `payload_source=latest_persisted_snapshot` / `payload_stale=false` / `payload_age=3.1m`
- **source / venue blockers 仍開啟**
  - `blocked_sparse_features=8` / `{'archive_required': 3, 'snapshot_only': 4, 'short_window_public_api': 1}`
  - top source blockers：`fin_netflow(source_auth_blocked/auth_missing, coverage=0.0%, archive_window=0.0%, forward_archive=ready, next=configure [REDACTED] source credentials)` / `claw(source_auth_blocked/auth_missing, coverage=12.6%, archive_window=61.3%, forward_archive=ready, next=configure [REDACTED] source credentials)` / `claw_intensity(source_auth_blocked/auth_missing, coverage=12.6%, archive_window=61.3%, forward_archive=ready, next=configure [REDACTED] source credentials)` / `nest_pred(source_tls_verify_failed/tls_verify_failed, coverage=13.9%, archive_window=68.2%, forward_archive=ready)`
  - fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=5788` / `archive_window_coverage_pct=0.0`
  - venue：`generated_at=2026-07-28T14:46:30.738494Z` / `venues_checked=2` / `ok_count=1` / `runtime_ready_count=0` / `runtime_ready=false` / `readiness_state=blocked_until_runtime_lifecycle_proof` / `runtime_ready_blockers=fill lifecycle 尚未驗證|live exchange credential 尚未驗證|order ack lifecycle 尚未驗證|元資料契約尚未通過|場館 adapter 尚未接入`；`okx=adapter_supported=true,enabled_in_config=true,credentials_configured=false,proof_state=public_metadata_only,runtime_ready=false,blockers=live exchange credential 尚未驗證|order ack lifecycle 尚未驗證|fill lifecycle 尚未驗證` / `binance=adapter_supported=false,enabled_in_config=false,credentials_configured=false,proof_state=adapter_unsupported,runtime_ready=false,blockers=場館 adapter 尚未接入|元資料契約尚未通過|場館設定停用`；`execution_metadata_smoke.venues[]` 已提供 per-venue `adapter_supported / enabled_in_config / credentials_configured / proof_state / runtime_ready / blockers /
    operator_next_action / verify_next` 給 Dashboard / Execution / Lab 直接顯示 adapter、credential boolean 與證據缺口；operator UI 會先 humanize backend error（例如 `unsupported venue` → `不支援的交易場館`），避免 raw venue error 洩漏到操作員畫面
  - venue dry-run proof：`artifact=data/venue_dry_run_proof.json` / `venue_dry_run_status=blocked_missing_runtime_backed_proof` / `generated_at=2026-07-28T14:46:31.353689Z` / `runtime_ready=false` / `runtime_ready_count=0` / `venues_checked=2` / `order_submission_enabled=false` / `risk_on_order_enabled=false` / `dry_run_only=true` / `ack=blocked_missing_credentials` / `cancel=blocked_missing_credentials` / `fill=blocked_missing_credentials` / `reconciliation=blocked_missing_credentials` / `local_rehearsal=passed_local_state_machine_runtime_unverified` / `local_scope=local_contract_rehearsal_not_exchange_proof` / `local_runtime_backed=false` / `local_live_adapter_called=false`；`okx=preview=blocked_missing_credentials,runtime_ready=false,credentials_configured=false` / `binance=preview=blocked_adapter_unsupported,runtime_ready=false,credentials_configured=false`；standalone artifact 可重跑、只做 dry-run preview / ack / cancel / fill / reconciliation checklist，`order_submission_enabled=false`。
- **Execution Console / `/api/trade` 已 fail-closed（同步中 + 阻塞 + 直接 API）**
  - 前端快捷：`manual_buy=paused_when_status_syncing_or_deployment_blocked` / `automation_enable=paused_when_status_syncing_or_deployment_blocked`；`/api/status` 初次同步前與阻塞期間只暫停買入 / 加倉與啟用自動模式，減碼 / 賣出風險降低、等待 / 觀望、切到手動模式、查看阻塞原因與重新整理仍可用。`/api/status` / `/api/execution/overview` / `/api/execution/runs` 已走 20s operator-workspace timeout，避免後端並行診斷或冷啟動時 8s default 把可用 payload 誤報成 `API timeout` / `載入失敗`。後端 `POST /api/trade` 對買入 / 加倉會先讀即時部署阻塞點；阻塞時真實買入 / 加倉回 409 `current_live_deployment_blocker`，仍保留等待 / 觀望、減倉 / 賣出風險降低，以及 `shadow_buy` / `paper_buy` 強制 dry-run paper/shadow 演練路徑；`data/live_predict_probe.json` 同步輸出 `api_trade_guardrail_active / api_trade_buy_guardrail / api_trade_allowed_risk_off_sides` 作為 machine-readable proof
  - active backend health：`active_backend_health_probe=passed` / `returncode=0` / `strict_ok=True` / `head_sync_status=current_head_commit` / `raw_continuity=repaired` / `feature_continuity=clean` / `restart_required=False` / `process_started_at=2026-07-26T13:21:21.349078+00:00` / `source=http://127.0.0.1:8000/health`；heartbeat runner 會在 API operator proof 前 fail-fast，stale backend 不可被當成 current truth。
- **Dashboard 啟動連續性 guardrail 已納入 feature deferred truth**
  - `/api/status.feature_continuity.status=deferred` 或 `repair_deferred=true` 時，Dashboard 連續性卡改用警示色並顯示 `特徵缺口已延後到心跳維護收斂`；避免 raw continuity clean/repaired 時，把啟動期 feature 缺口誤讀成全綠。
- **Execution Status / Bot 營運 已顯示熔斷解除條件**
  - `最近 50 筆目前 13/50，還差 2 勝；當前 q00 分桶支持樣本 / 候選修補不可取代熔斷解除條件`；`/execution/status` 與 `/execution` 會先顯示熔斷解除條件，再顯示 當前 q00 分桶 support / 治理背景；`runtime_closure_summary` 已由 `model/runtime_closure.py` 共用中文化，避免後端 bucket / route / source / reference raw token 泄漏到 Dashboard / Strategy Lab / Execution Status / live DQ operator markdown
- **Live DQ drilldown operator-facing markdown 已 enum-safe**
  - `docs/analysis/live_decision_quality_drilldown.md` 的 operator header、support summary、精準支持路徑、跨門檻 verdict、recommended patch 來源 / 範圍改用繁中標籤；machine JSON 保留 raw enum，operator markdown 不再洩漏後端 bucket / route / source / reference raw token。
- **Strategy Lab 高信心 OOS 列級訊號 copy 已 operator-safe**
  - `formatHighConvictionRuntimeSignalLabel()` 統一把即時訊號 enum 轉成繁中操作語；最接近部署候選列不再把內部訊號 token 直接丟給 operator，避免 OOS-pass / runtime-blocked 候選被誤讀為可部署動作。
- **Paper/shadow worker outcome reconciliation 已納入 current-state truth**
  - `artifact=data/paper_shadow_outcome_reconciliation.json` / `status=recording_with_resolved_outcomes` / `rehearsal_status=resolved_evidence_ready` / `worker_poll_events=4` / `pending_outcomes=0` / `resolved_outcomes=4` / `awaiting_label_replay=0` / `can_poll_workers=true` / `poll_blocked_by_pending_outcome=false` / `order_submission_enabled=false` / `risk_on_order_enabled=false` / `live_order_submitted=false` / `next_reconcile_at=—` / `current_pending_hours_remaining_hours=—` / `artifact_pending_hours_remaining_hours=None`；這是 24h 演練證據與 pending guard，不是 live-ready 訊號。
- **高低震盪 / 擁塞實戰拆解已產品化（fail-closed）**
  - `support=0/50` / `gap=50` / `paper_shadow=true` / `risk_on_order_enabled=false` / `order_submission_enabled=false` / `reduce_risk_allowed=true`；震盪不是停工，也不是永遠不能實戰：Bot 營運與 `/api/status.range_chop_playbook` 會把高低震盪拆成區間影子觀察、減碼 / 取消掛單與證據收集；進攻買入 / 加倉與啟用自動模式仍鎖住，必須等即時部署門檻與場館證據鏈通過。
- **M5 實戰準備度總卡已產品化**
  - 模型 gate / 即時支持 gate / 熔斷 gate / 場館 gate / live-canary policy gate / 影子觀察 gate 一次顯示；credential present 只顯示布林 / 狀態，不輸出 secret；影子觀察與減風險可前進，買入 / 加倉仍鎖住。
  - `/api/status` 會載入 `data/venue_dry_run_proof.json` 並在 `execution_surface_contract.live_canary_policy_gate` 顯示本地 bounded-canary policy gate；Dashboard / Execution Status / Strategy Lab status-only summaries 也會顯示同一 gate 與繁中 blocker copy；`/api/execution/overview` artifact-first 輸出 `execution_readiness / shadow_trade_ledger / venue_dry_run_proof / customer_safe_alternative_proof / canary_gap_answers`，且可用 `scripts/venue_dry_run_api_consistency_probe.py --strict` 驗證 status / overview / artifact 同源、fail-closed、secret-safe；strict verifier 也會獨立拒絕缺失、非有限或不可能的本地生命週期數量關係（filled / remaining / canceled 算術），避免同源錯誤自我認證。另可用 `scripts/customer_safe_alternative_api_consistency_probe.py --strict` 驗證 customer-safe overview / artifact aliases、counts、selected next artifact、fail-closed、secret-safe 同源；`data/customer_safe_alternative_proof.json` / `docs/analysis/customer_safe_alternative_proof.md` 會把 PM alternative-solution handoff 濃縮成 customer-safe proof。
- **heartbeat current-state docs overwrite sync 已自動化**
  - `scripts/hb_parallel_runner.py` 現在會在 `auto_propose_fixes.py` 後自動覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 目的：避免 markdown docs 落後 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json / data/q15_support_fill_feasibility.json / data/q15_exact_bucket_row_harvest_proof.json / data/q15_drift_rebaseline_backtest.json / data/q15_map_signal_redesign_proof.json / data/no_trade_lane_replay.json / data/paper_shadow_outcome_reconciliation.json / data/execution_metadata_smoke.json / data/venue_dry_run_proof.json / data/leaderboard_feature_profile_probe.json / data/high_conviction_topk_oos_matrix.json`，讓 cron 心跳真正完成 docs overwrite 閉環

---

## Open Issues

### P0. 連續 35 筆 1440m simulated_pyramid_win=0
- 目前真相：`canonical_horizon_minutes=1440` / `losing_streak=35` / `all_horizon_losing_streak=6`
- 下一步：檢查 recent canonical labels / regime breakdown / circuit breaker；必要時升級為 distribution-aware drift 調查

### P0. 熔斷仍是當前 primary blocker；exact support / venue proof 仍未閉合
- 目前真相：`deployment_blocker=circuit_breaker_active` / `streak=35` / `recent 50 wins=13/50` / `additional_recent_window_wins_needed=2`
- same-bucket truth：`bucket=BLOCK|structure_quality_block|q00` / `support=0/50` / `support_route_verdict=exact_bucket_unsupported_block` / `support_governance_route=exact_live_lane_proxy_available`
- support progress：`status=stalled_under_minimum` / `reason=current live exact support 連續 heartbeat 停在同一數量，屬於 support accumulation 停滯。` / `regression_basis=same_identity_same_semantic_signature` / `current_rows=0` / `minimum_rows=50` / `gap_to_minimum=50` / `support_rows_needed=50` / `previous_rows=0` / `delta_vs_previous=0` / `legacy_supported_reference=—` / `stagnant_run_count=2` / `stalled_support_accumulation=True` / `escalate_to_blocker=False` / `equilibrium_deadlock=equilibrium_deadlock_watch` / `equilibrium_deadlock_confirmed=False` / `forced_research_action_required=True` / `forced_research_action_output=data/equilibrium_deadlock_research_action.json` / `governance_reference_route=exact_live_lane_proxy_available` / `exact_live_lane_proxy_rows=43` / `governance_reference_only=True`；active repair：`phase=current_bucket_first` / `component_verify_ready=False` /
  `live_exposure_allowed=False` / `shadow_or_paper_allowed=True` / `current_signal=CIRCUIT_BREAKER` / `current_allowed_layers=0` / `guardrail=decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active` / `actions=collect_exact_current_bucket_rows,force_q15_support_audit_refresh,semantic_signature_map_signal_redesign_or_row_harvest,equilibrium_deadlock_research_action` / `forced_branch_status=hard_no_go_recorded` / `forced_branch_selected=hard_no_go_single_failed_gate` / `single_failed_gate=circuit_breaker_gate` / `next_validation_artifact=data/circuit_breaker_audit.json` / `decision_clock=72h_micro_canary_or_single_failed_gate`
- runtime/API guardrail：`POST /api/trade` 對買入 / 加倉會先讀即時部署阻塞點；阻塞時真實買入 / 加倉回 409 `current_live_deployment_blocker`，仍保留等待 / 觀望、減倉 / 賣出風險降低，以及 `shadow_buy` / `paper_buy` 強制 dry-run paper/shadow 演練路徑。
- 下一步：即時部署阻塞語義切回熔斷解除條件：先把熔斷解除條件視為當前 immediate hard gate；同時保留 current exact support rows/minimum/gap、support_route、Top-K deployable=0 與 venue runtime proof 作為後續 live gates。熔斷期間不得把 support/proxy/reference rows 或 venue checklist 包裝成 deploy-ready，也不得把它們從 live gate 清單移除。 最近 50 筆目前 13/50 勝，解除至少需要 15 勝，還差 2 勝；同時連續虧損必須 < 50。

### P0. 建立 high-conviction top-k OOS ROI gate，讓 APP 從研究轉實戰
- 目前真相：`mode_label=模擬觀察_影子驗證_即時阻塞` / `validation=walk_forward_oos_topk_matrix` / `top_k_grid=1%,2%,5%,10%` / `output_artifact=data/high_conviction_topk_oos_matrix.json`
- latest matrix：`generated_at=2026-07-28T14:43:04.757908+00:00` / `freshness=fresh` / `age_min=4.1` / `stale_after_min=60` / `deployment_blocking=False` / `samples=29310` / `rows=24` / `models=logistic_regression,random_forest,xgboost` / `deployable_rows=0` / `risk_qualified_rows=0` / `runtime_blocked_candidates=0` / `support_route=exact_bucket_unsupported_block` / `deployment_blocker=circuit_breaker_active` / `current_live_structure_bucket=BLOCK|structure_quality_block|q00` / `current_live_structure_bucket_rows=0/50` / `current_live_structure_bucket_gap_to_minimum=50` / `support_progress_status=stalled_under_minimum` / `support_progress_reason=current live exact support 連續 heartbeat 停在同一數量，屬於 support accumulation 停滯。` / `regression_basis=same_identity_same_semantic_signature` / `delta_vs_previous=0` / `previous_rows=0` / `support_rows_needed=50` / `stagnant_run_count=2` / `stalled_support_accumulation=True` / `escalate_to_blocker=False`
- nearest deployable candidate：`model=logistic_regression` / `regime=all` / `top_k=top_1pct` / `oos_roi=0.2465` / `win_rate=0.6897` / `profit_factor=4.3797` / `max_drawdown=0.0478` / `worst_fold=0.0994` / `trade_count=29` / `tier=research_oos_gate_failed` / `oos_gate_passed=False` / `verdict=not_deployable` / `support_route=exact_bucket_unsupported_block` / `governance=exact_live_lane_proxy_available` / `bucket=BLOCK|structure_quality_block|q00` / `bucket_rows=0/50` / `gap=50` / `support_progress_status=stalled_under_minimum` / `support_progress_reason=current live exact support 連續 heartbeat 停在同一數量，屬於 support accumulation 停滯。` / `regression_basis=same_identity_same_semantic_signature` / `delta_vs_previous=0` / `previous_rows=0` / `support_rows_needed=50` / `stagnant_run_count=2` / `stalled_support_accumulation=True` / `escalate_to_blocker=False`
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

### P1. model stability still needs work (cv=0.6521, cv_std=0.0939, cv_worst=0.5568)
- 目前真相：`cv_accuracy=0.6520733061828952` / `cv_std=0.09385079630746362` / `cv_worst=0.5568308034061459`
- 下一步：優先比較 support-aware / shrinkage profiles 與 current bucket robustness，避免把治理 blocker 誤當單純 parity 問題。

### P1. TW-IC 25 vs Global IC 18 — 信號強依賴近期資料
- 目前真相：`global_pass=18` / `tw_pass=25` / `total_features=30`
- 下一步：市場 regime 可能已變化; 考慮 regime-gated feature weighting

### P1. OKX/Binance venue readiness is still unverified
- 目前真相：`generated_at=2026-07-28T14:46:30.738494Z` / `venues_checked=2` / `ok_count=1` / `runtime_ready_count=0` / `runtime_ready=false` / `readiness_state=blocked_until_runtime_lifecycle_proof` / `runtime_ready_blockers=fill lifecycle 尚未驗證|live exchange credential 尚未驗證|order ack lifecycle 尚未驗證|元資料契約尚未通過|場館 adapter 尚未接入`；`okx=adapter_supported=true,enabled_in_config=true,credentials_configured=false,proof_state=public_metadata_only,runtime_ready=false,blockers=live exchange credential 尚未驗證|order ack lifecycle 尚未驗證|fill lifecycle 尚未驗證` / `binance=adapter_supported=false,enabled_in_config=false,credentials_configured=false,proof_state=adapter_unsupported,runtime_ready=false,blockers=場館 adapter 尚未接入|元資料契約尚未通過|場館設定停用`
- API/UI contract：`execution_metadata_smoke.venues[]` 已帶 `adapter_supported / enabled_in_config / credentials_configured / proof_state / runtime_ready / blockers / operator_next_action / verify_next`，Dashboard、`/execution/status`、`/execution`、`/lab` 必須直接顯示 OKX 與 Binance 每個場館的 adapter、credential boolean 與實單證據缺口；`runtime_ready=true` 且 blockers 清空前不可宣稱 canary / live-ready。
- 下一步：Keep OKX runtime-proof blockers and Binance unsupported/disabled blockers explicitly visible on Dashboard, /lab, and /execution/status until credentials, order ack lifecycle, and fill lifecycle each have runtime-backed proof; unsupported venues must stay fail-closed; any readiness UI must require runtime_ready=true plus no blockers.
- Governor `run=59` 的 forced branch `venue_lifecycle_proof` 已綁定 fresh hard-no-go receipt：`data/venue_lifecycle_hard_no_go.json.receipt_valid=true` / `single_failed_gate=okx_sandbox_credentials_and_runtime_binding_gate` / `strict_ok=true` / `api_consistent=true` / `artifact_consistent=true` / `bound_to_venue_proof=true` / `live_adapter_called=false` / `live_order_submitted=false`。唯一下一個 venue artifact 是 `data/okx_runtime_lifecycle_proof.json`；只接受 secret-safe sandbox/runtime-backed ack + partial-fill-or-explicit-no-fill + cancel ack + 獨立重算 reconciliation，否則維持 hard no-go。
- 驗證：
  - browser /execution
  - browser /execution/status
  - browser /lab
  - data/execution_metadata_smoke.json
  - PYTHONPATH=. /home/kazuha/Poly-Trader/venv/bin/python scripts/execution_metadata_smoke.py --symbol BTCUSDT --venues okx binance
  - PYTHONPATH=. /home/kazuha/Poly-Trader/venv/bin/python /tmp/hb1195_metadata_api_probe.py
  - PYTHONPATH=. /home/kazuha/Poly-Trader/venv/bin/python -m pytest tests/test_execution_metadata_smoke.py tests/test_server_startup.py -k 'execution_metadata_smoke or venue_runtime_proof' tests/test_frontend_decision_contract.py -k 'venue_readiness or runtime_copy_humanizes_execution_governance' -q
  - cd web && npm run build

### P1. Dashboard「目前唯一阻塞點」卡片遮蔽 canonical breaker release truth
- 瀏覽器實測 `http://127.0.0.1:5173/` 在 `/api/execution/overview` settle 後只顯示 `目前即時證據 0/50` / `差距 50`，頁面沒有 `風控熔斷`、`13/50` 或 `還差 2 勝`；但同輪 `/api/status`、`/execution`、`/execution/status` 與 Strategy Lab Top-K 都正確顯示 `deployment_blocker=circuit_breaker_active`。這會把 support boundary 誤寫成唯一即時阻塞點。
- 下一步：讓 Dashboard 主卡先顯示 canonical `deployment_blocker` 與 breaker release math，再把 q00 exact support `0/50` 當後續 live gate；此 UI 修補不得取代 Governor `run=59` 的唯一 venue artifact `data/okx_runtime_lifecycle_proof.json`。
- 驗證：settled browser `/` 必須出現 `風控熔斷`、`13/50`、`還差 2 勝`，並保留 support `0/50` secondary copy；跑 `tests/test_frontend_decision_contract.py` 與 `cd web && npm run build`。

### P1. fin_netflow remains source_auth_blocked because [REDACTED] is missing
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=5788` / `archive_window_coverage_pct=0.0`
- 下一步：Configure [REDACTED], then keep heartbeat collection running until successful ETF-flow snapshots replace auth_missing rows and coverage starts to move.
- 驗證：
  - data/execution_metadata_smoke.json
  - /api/features/coverage

### P1. leaderboard comparable rows are missing; keep the recent-window contract honest
- 目前真相：`leaderboard_count=0` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split` / `payload_source=latest_persisted_snapshot` / `payload_stale=false` / `payload_age=3.1m`
- 下一步：Restore comparable leaderboard rows or keep placeholder-only state explicit; do not let Strategy Lab or docs imply a stable ranking when the recent-window contract is missing.
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

### P1. recent canonical window 250 rows = regime_concentration but current live regime is outside the blocker pocket
- 目前真相：`window=250` / `interpretation=regime_concentration` / `win_rate=0.508` / `dominant_regime=chop` / `dominant_regime_share=0.828` / `avg_pnl=-0.001`
- 下一步：保留 recent canonical drift 監控與 blocker-window evidence；目前 live predictor 沒有套用 recent pathology guardrail，且 current live regime 不等於 blocker dominant regime，因此降為 P1 監控，不得當成 deployment closure。

---

## Current Priority
1. **維持熔斷優先真相，同時保留 q00 current-live bucket support rows 可 machine-read**
2. **持續沿 recent canonical pathological slice 追根因，不要 generic 化 blocker**
3. **守住 q00 current-live bucket support truth / blocker truth、leaderboard dual-role governance、venue/source blockers 可見性**
4. **反平衡強制執行：same semantic signature + support delta=0 時必須選 forced branch，不得 observation-only**
5. **讓 heartbeat 自動 overwrite sync current-state docs，不再把 docs drift 留給人工補寫**
6. **P0 實戰化：建立 high-conviction top-k OOS ROI gate，把研究 winner 轉成可拒單部署候選**
   - `data/high_conviction_topk_oos_matrix.json` 已產出 `generated_at=2026-07-28T14:43:04.757908+00:00` / `freshness=fresh` / `age_min=4.1` / `stale_after_min=60` / `deployment_blocking=False` / `rows=24` / `deployable_rows=0` / `risk_qualified_rows=0` / `runtime_blocked_candidates=0` / `bucket_rows=0/50` / `gap=50` / `release_ready=False` / `recent_window_wins=13/50` / `required_recent_window_wins=15` / `additional_recent_window_wins_needed=2` / `current_recent_window_win_rate=0.260` / `support_progress_status=stalled_under_minimum` / `support_progress_reason=current live exact support 連續 heartbeat 停在同一數量，屬於 support accumulation 停滯。` / `regression_basis=same_identity_same_semantic_signature` / `delta_vs_previous=0` / `previous_rows=0` / `support_rows_needed=50` / `stagnant_run_count=2` / `stalled_support_accumulation=True` / `escalate_to_blocker=False`；
     `/api/models/leaderboard` 與 Strategy Lab 高信心 OOS Top-K 部署門檻面板已改為最接近部署候選優先，並以操作員繁中 copy 顯示矩陣新鮮度、breaker release math 與即時支持脈絡；矩陣過期或即時分桶 / 支持 / release 條件未解除前仍 fail-closed。
