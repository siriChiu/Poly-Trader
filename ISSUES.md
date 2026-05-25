# ISSUES.md — Current State Only

_最後更新：2026-05-25 08:11:47 CST_

只保留目前有效問題；由 heartbeat runner overwrite sync，避免 current-state markdown 落後 issues.json / live artifacts。

---

## 當前主線事實
- **最新 fast heartbeat #1495 已完成 collect + diagnostics refresh**
  - `Raw=34367 / Features=25313 / Labels=68162`
  - 歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`
  - `simulated_pyramid_win=56.46%`
- **canonical current-live blocker 已切到 current-live exact-support truth**
  - `deployment_blocker=under_minimum_exact_live_structure_bucket` / `streak=—` / `recent_window_wins=—/—` / `additional_recent_window_wins_needed=—`
  - `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q35` / `support=6/50` / `gap=44` / `support_route_verdict=exact_bucket_present_but_below_minimum`
  - support progress：`status=semantic_rebaseline_under_minimum` / `reason=current exact support 6/50 below minimum (gap=44); legacy 0/50@1238 remains reference-only` / `regression_basis=legacy_or_different_semantic_signature` / `current_rows=6` / `minimum_rows=50` / `gap_to_minimum=44` / `support_rows_needed=44` / `previous_rows=6` / `delta_vs_previous=0` / `legacy_supported_reference=0/50@1238` / `stagnant_run_count=2` / `stalled_support_accumulation=False` / `escalate_to_blocker=True` / `governance_reference_route=exact_live_bucket_present_but_below_minimum` / `exact_live_lane_proxy_rows=8` / `governance_reference_only=True`
- **PM handoff support-fill feasibility 已納入 current-state docs**
  - `artifact=data/q15_support_fill_feasibility.json` / `classification=semantic_window_gap_not_raw_backfill_gap` / `bucket=CAUTION|base_caution_regime_or_bias|q35` / `exact_rows=6/50` / `identity_rows=31` / `non_bucket_identity_rows=25` / `gap=44` / `time_to_evidence=semantic_rebaseline_review_required_before_reference_rows_count` / `missing_capability=Constraint/Review` / `alternative_solution_required=True`；next safe artifact：data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy；reference windows / governance rows 不可包裝成 deployable support。
- **anti-equilibrium forced execution governor 已啟用**
  - trigger：`same_identity_same_semantic_signature` + `delta_vs_previous=0` / stagnant support 或使用者指出趨近平衡時，heartbeat 不得只刷新 observation-only status。
  - forced branches：Venue lifecycle proof / Model shadow to decision / Strategy micro-canary readiness / Map-Signal redesign / hard no-go single failed gate。
  - bounded live-canary：任何 live buy/add pilot 必須有 `execution.live_canary.enabled=true`、explicit `allowed_symbols`、symbol-specific `max_base_qty_by_symbol`，缺 policy 或超 cap 會在 adapter 前拒單。
- **recent canonical diagnostics 已刷新**
  - `latest_window=100` / `win_rate=90.0%` / `dominant_regime=bear(90.0%)` / `avg_quality=+0.6209` / `avg_pnl=+0.0207` / `alerts=label_imbalance,regime_concentration,regime_shift`
  - shadow-only falsification：`mode=shadow_only_no_new_risk_falsification` / `deployable=false` / `risk_on_order_enabled=false` / `order_submission_enabled=false` / `baseline_win_rate=90.0%` / `best_gate=observable_4h_shift_shadow_gate` / `kept_rows=79` / `kept_win_rate=100.0%` / `loss_capture=100.0%` / `operator=僅限 paper/shadow；熔斷、support 與 venue gate 仍 fail-closed`
  - `blocking_window=1000` / `win_rate=47.6%` / `dominant_regime=bear(54.7%)` / `avg_quality=+0.1363` / `avg_pnl=+0.0011` / `alerts=regime_shift`
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=current_full_no_bull_collapse_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split` / `payload_source=latest_persisted_snapshot` / `payload_stale=false` / `payload_age=7.1m`
- **source / venue blockers 仍開啟**
  - `blocked_sparse_features=8` / `{'archive_required': 3, 'snapshot_only': 4, 'short_window_public_api': 1}`
  - top source blockers：`fin_netflow(source_auth_blocked/auth_missing, coverage=0.0%, archive_window=0.0%, forward_archive=ready, next=configure [REDACTED] source credentials)` / `claw(source_auth_blocked/auth_missing, coverage=14.1%, archive_window=75.2%, forward_archive=ready, next=configure [REDACTED] source credentials)` / `claw_intensity(source_auth_blocked/auth_missing, coverage=14.1%, archive_window=75.2%, forward_archive=ready, next=configure [REDACTED] source credentials)` / `nest_pred(source_tls_verify_failed/tls_verify_failed, coverage=15.7%, archive_window=83.6%, forward_archive=ready)`
  - fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=4722` / `archive_window_coverage_pct=0.0`
  - venue：`generated_at=2026-05-25T00:11:44.024641Z` / `venues_checked=2` / `ok_count=1` / `runtime_ready_count=0` / `runtime_ready=false` / `readiness_state=blocked_until_runtime_lifecycle_proof` / `runtime_ready_blockers=fill lifecycle 尚未驗證|live exchange credential 尚未驗證|order ack lifecycle 尚未驗證|元資料契約尚未通過|場館 adapter 尚未接入`；`okx=adapter_supported=true,enabled_in_config=true,credentials_configured=false,proof_state=public_metadata_only,runtime_ready=false,blockers=live exchange credential 尚未驗證|order ack lifecycle 尚未驗證|fill lifecycle 尚未驗證` / `binance=adapter_supported=false,enabled_in_config=false,credentials_configured=false,proof_state=adapter_unsupported,runtime_ready=false,blockers=場館 adapter 尚未接入|元資料契約尚未通過|場館設定停用`；`execution_metadata_smoke.venues[]` 已提供 per-venue `adapter_supported / enabled_in_config / credentials_configured / proof_state / runtime_ready / blockers /
    operator_next_action / verify_next` 給 Dashboard / Execution / Lab 直接顯示 adapter、credential boolean 與證據缺口；operator UI 會先 humanize backend error（例如 `unsupported venue` → `不支援的交易場館`），避免 raw venue error 洩漏到操作員畫面
- **Execution Console / `/api/trade` 已 fail-closed（同步中 + 阻塞 + 直接 API）**
  - 前端快捷：`manual_buy=paused_when_status_syncing_or_deployment_blocked` / `automation_enable=paused_when_status_syncing_or_deployment_blocked`；`/api/status` 初次同步前與阻塞期間只暫停買入 / 加倉與啟用自動模式，減碼 / 賣出風險降低、等待 / 觀望、切到手動模式、查看阻塞原因與重新整理仍可用。`/api/status` / `/api/execution/overview` / `/api/execution/runs` 已走 20s operator-workspace timeout，避免後端並行診斷或冷啟動時 8s default 把可用 payload 誤報成 `API timeout` / `載入失敗`。後端 `POST /api/trade` 對買入 / 加倉會先讀即時部署阻塞點；阻塞時回 409 `current_live_deployment_blocker`，只保留等待 / 觀望與減倉 / 賣出風險降低路徑；`data/live_predict_probe.json` 同步輸出 `api_trade_guardrail_active / api_trade_buy_guardrail / api_trade_allowed_risk_off_sides` 作為 machine-readable proof
- **Dashboard 啟動連續性 guardrail 已納入 feature deferred truth**
  - `/api/status.feature_continuity.status=deferred` 或 `repair_deferred=true` 時，Dashboard 連續性卡改用警示色並顯示 `特徵缺口已延後到心跳維護收斂`；避免 raw continuity clean/repaired 時，把啟動期 feature 缺口誤讀成全綠。
- **Execution Status / Bot 營運 已顯示即時部署阻塞條件**
  - `即時部署阻塞點=under_minimum_exact_live_structure_bucket`；當前 q35 分桶支持樣本=6/50，缺口=44；目前不是熔斷解除數學，候選修補不可取代同分桶最低樣本門檻；`/execution/status` 與 `/execution` 會先顯示即時部署阻塞點，再顯示 當前 q35 分桶 support / 治理背景；`runtime_closure_summary` 已由 `model/runtime_closure.py` 共用中文化，避免後端 bucket / route / source / reference raw token 泄漏到 Dashboard / Strategy Lab / Execution Status / live DQ operator markdown
- **Live DQ drilldown operator-facing markdown 已 enum-safe**
  - `docs/analysis/live_decision_quality_drilldown.md` 的 operator header、support summary、精準支持路徑、跨門檻 verdict、recommended patch 來源 / 範圍改用繁中標籤；machine JSON 保留 raw enum，operator markdown 不再洩漏後端 bucket / route / source / reference raw token。
- **Strategy Lab 高信心 OOS 列級訊號 copy 已 operator-safe**
  - `formatHighConvictionRuntimeSignalLabel()` 統一把即時訊號 enum 轉成繁中操作語；最接近部署候選列不再把內部訊號 token 直接丟給 operator，避免 OOS-pass / runtime-blocked 候選被誤讀為可部署動作。
- **Execution Console 高信心 Top-K 影子觀察入口已產品化**
  - `risk_qualified_rows=6` / `runtime_blocked_candidates=6` / `deployable_rows=0` / `paper_shadow=true` / `risk_on_order_enabled=false` / `support=6/50` / `gap=44`；高信心 Top-K OOS 候選已可在 Execution Console selective sleeve 啟動影子觀察：只鏡像即時決策、事件紀錄、帳戶與對帳摘要，不送單、不加倉；等即時支持、場館證據鏈與單一 Bot 帳本全部通過後才能升級小流量。
- **高低震盪 / 擁塞實戰拆解已產品化（fail-closed）**
  - `support=6/50` / `gap=44` / `paper_shadow=true` / `risk_on_order_enabled=false` / `order_submission_enabled=false` / `reduce_risk_allowed=true`；震盪不是停工，也不是永遠不能實戰：Bot 營運與 `/api/status.range_chop_playbook` 會把高低震盪拆成區間影子觀察、減碼 / 取消掛單與證據收集；進攻買入 / 加倉與啟用自動模式仍鎖住，必須等即時部署門檻與場館證據鏈通過。
- **M5 實戰準備度總卡已產品化**
  - `/api/execution/overview` 已輸出 `execution_readiness / shadow_trade_ledger / venue_dry_run_proof / canary_gap_answers`，且 `data/customer_safe_alternative_proof.json` / `docs/analysis/customer_safe_alternative_proof.md` 會把 PM alternative-solution handoff 濃縮成 customer-safe proof；模型 gate / 即時支持 gate / 熔斷 gate / 場館 gate / 影子觀察 gate 一次顯示。credential present 只顯示布林 / 狀態，不輸出 secret；影子觀察與減風險可前進，買入 / 加倉仍鎖住。
- **heartbeat current-state docs overwrite sync 已自動化**
  - `scripts/hb_parallel_runner.py` 現在會在 `auto_propose_fixes.py` 後自動覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 目的：避免 markdown docs 落後 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json / data/q15_support_fill_feasibility.json / data/execution_metadata_smoke.json / data/leaderboard_feature_profile_probe.json / data/high_conviction_topk_oos_matrix.json`，讓 cron 心跳真正完成 docs overwrite 閉環

---

## Open Issues

### P0. current live bucket CAUTION|base_caution_regime_or_bias|q35 exact support remains under minimum and remains the deployment blocker (6/50)
- 目前真相：`deployment_blocker=under_minimum_exact_live_structure_bucket` / `bucket=CAUTION|base_caution_regime_or_bias|q35` / `support=6/50` / `gap=44` / `runtime_closure_state=patch_inactive_or_blocked`
- same-bucket truth：`support_route_verdict=exact_bucket_present_but_below_minimum` / `support_governance_route=exact_live_bucket_present_but_below_minimum` / `recommended_patch=—` / `recommended_patch_status=—` / `reference_scope=—`
- support progress：`status=semantic_rebaseline_under_minimum` / `reason=current exact support 6/50 below minimum (gap=44); legacy 0/50@1238 remains reference-only` / `regression_basis=legacy_or_different_semantic_signature` / `current_rows=6` / `minimum_rows=50` / `gap_to_minimum=44` / `support_rows_needed=44` / `previous_rows=6` / `delta_vs_previous=0` / `legacy_supported_reference=0/50@1238` / `stagnant_run_count=2` / `stalled_support_accumulation=False` / `escalate_to_blocker=True` / `governance_reference_route=exact_live_bucket_present_but_below_minimum` / `exact_live_lane_proxy_rows=8` / `governance_reference_only=True`
- runtime/API guardrail：`POST /api/trade` 對買入 / 加倉會先讀即時部署阻塞點；阻塞時回 409 `current_live_deployment_blocker`，只保留等待 / 觀望與減倉 / 賣出風險降低路徑。
- 下一步：把 current-live blocker 語義切到 exact-support truth；在 current live bucket 補滿 minimum rows 前，不要把 proxy rows、reference patch、或 breaker 舊敘事誤當成已解除 blocker。

### P0. 建立 high-conviction top-k OOS ROI gate，讓 APP 從研究轉實戰
- 目前真相：`mode_label=模擬觀察_影子驗證_即時阻塞` / `validation=walk_forward_oos_topk_matrix` / `top_k_grid=1%,2%,5%,10%` / `output_artifact=data/high_conviction_topk_oos_matrix.json`
- latest matrix：`generated_at=2026-05-25T00:11:24.828560+00:00` / `freshness=fresh` / `age_min=0.4` / `stale_after_min=60` / `deployment_blocking=False` / `samples=25162` / `rows=24` / `models=logistic_regression,random_forest,xgboost` / `deployable_rows=0` / `risk_qualified_rows=6` / `runtime_blocked_candidates=6` / `support_route=exact_bucket_present_but_below_minimum` / `deployment_blocker=under_minimum_exact_live_structure_bucket` / `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q35` / `current_live_structure_bucket_rows=6/50` / `current_live_structure_bucket_gap_to_minimum=44` / `support_progress_status=semantic_rebaseline_under_minimum` / `support_progress_reason=current exact support 6/50 below minimum (gap=44); semantic mismatch=calibration_window` / `regression_basis=legacy_or_different_semantic_signature` / `delta_vs_previous=0` / `previous_rows=6` /
  `support_rows_needed=44` / `stagnant_run_count=2` / `stalled_support_accumulation=False` / `escalate_to_blocker=True`
- nearest deployable candidate：`model=logistic_regression` / `regime=all` / `top_k=top_2pct` / `oos_roi=0.9324` / `win_rate=0.8621` / `profit_factor=19.8864` / `max_drawdown=0.022` / `worst_fold=0.2068` / `trade_count=58` / `tier=runtime_blocked_oos_pass` / `oos_gate_passed=True` / `verdict=not_deployable` / `support_route=exact_bucket_present_but_below_minimum` / `governance=exact_live_bucket_present_but_below_minimum` / `bucket=CAUTION|base_caution_regime_or_bias|q35` / `bucket_rows=6/50` / `gap=44` / `support_progress_status=semantic_rebaseline_under_minimum` / `support_progress_reason=current exact support 6/50 below minimum (gap=44); semantic mismatch=calibration_window` / `regression_basis=legacy_or_different_semantic_signature` / `delta_vs_previous=0` / `previous_rows=6` / `support_rows_needed=44` / `stagnant_run_count=2` / `stalled_support_accumulation=False` / `escalate_to_blocker=True`
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

### P1. model stability still needs work (cv=0.4976, cv_std=0.0332, cv_worst=0.4644)
- 目前真相：`cv_accuracy=0.4975560081466395` / `cv_std=0.03319755600814664` / `cv_worst=0.46435845213849286`
- 下一步：優先比較 support-aware / shrinkage profiles 與 current bucket robustness，避免把治理 blocker 誤當單純 parity 問題。

### P1. TW-IC 29 vs Global IC 17 — 信號強依賴近期資料
- 目前真相：`global_pass=17` / `tw_pass=29` / `total_features=30`
- 下一步：市場 regime 可能已變化; 考慮 regime-gated feature weighting

### P1. OKX/Binance venue readiness is still unverified
- 目前真相：`generated_at=2026-05-25T00:11:44.024641Z` / `venues_checked=2` / `ok_count=1` / `runtime_ready_count=0` / `runtime_ready=false` / `readiness_state=blocked_until_runtime_lifecycle_proof` / `runtime_ready_blockers=fill lifecycle 尚未驗證|live exchange credential 尚未驗證|order ack lifecycle 尚未驗證|元資料契約尚未通過|場館 adapter 尚未接入`；`okx=adapter_supported=true,enabled_in_config=true,credentials_configured=false,proof_state=public_metadata_only,runtime_ready=false,blockers=live exchange credential 尚未驗證|order ack lifecycle 尚未驗證|fill lifecycle 尚未驗證` / `binance=adapter_supported=false,enabled_in_config=false,credentials_configured=false,proof_state=adapter_unsupported,runtime_ready=false,blockers=場館 adapter 尚未接入|元資料契約尚未通過|場館設定停用`
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
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=4722` / `archive_window_coverage_pct=0.0`
- 下一步：Configure [REDACTED], then keep heartbeat collection running until successful ETF-flow snapshots replace auth_missing rows and coverage starts to move.
- 驗證：
  - data/execution_metadata_smoke.json
  - /api/features/coverage

### P1. leaderboard comparable rows are back; keep the recent-window contract stable and cron-safe
- 目前真相：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=current_full_no_bull_collapse_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split` / `payload_source=latest_persisted_snapshot` / `payload_stale=false` / `payload_age=7.1m`
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

### P1. q35 lane still needs formula review / base-stack redesign before deploy
- 目前真相：`bucket=CAUTION|base_caution_regime_or_bias|q35` / `support=6/50` / `gap=44` / `support_route_verdict=exact_bucket_present_but_below_minimum` / `overall_verdict=bias50_formula_may_be_too_harsh` / `redesign_verdict=base_stack_redesign_discriminative_reweight_crosses_floor_but_execution_blocked` / `runtime_gap_to_floor=0.0829`
- q35 scaling audit 已指出目前不是單點 bias50 closure： `overall_verdict=bias50_formula_may_be_too_harsh` / `redesign_verdict=base_stack_redesign_discriminative_reweight_crosses_floor_but_execution_blocked` / `runtime_gap_to_floor=0.0829` / `redesign_entry_quality=0.5605` / `redesign_allowed_layers=0` / `positive_discriminative_gap=True` / `execution_blocked_after_floor_cross=True`
- 下一步：維持 q35 scaling audit 的 runtime gap / redesign entry_quality / allowed_layers 已同步到 docs/probe/issues；本輪 discriminative redesign 只跨過 scoring floor，runtime gate/support 仍讓 allowed_layers=0，下一步只追 exact-support 與 score-only 治理，不得把 floor-cross 當成 deployment closure。

### P1. recent canonical window 1000 rows = regime_concentration but current live regime is outside the blocker pocket
- 目前真相：`window=1000` / `interpretation=regime_concentration` / `win_rate=0.476` / `dominant_regime=bear` / `dominant_regime_share=0.547` / `avg_pnl=0.0011`
- 下一步：保留 recent canonical drift 監控與 blocker-window evidence；目前 live predictor 沒有套用 recent pathology guardrail，且 current live regime 不等於 blocker dominant regime，因此降為 P1 監控，不得當成 deployment closure。

---

## Current Priority
1. **維持 current-live exact-support blocker truth，同時保留 q35 current-live bucket support rows 可 machine-read**
2. **持續沿 recent canonical pathological slice 追根因，不要 generic 化 blocker**
3. **守住 q35 current-live bucket support truth / blocker truth、leaderboard dual-role governance、venue/source blockers 可見性**
4. **反平衡強制執行：same semantic signature + support delta=0 時必須選 forced branch，不得 observation-only**
5. **讓 heartbeat 自動 overwrite sync current-state docs，不再把 docs drift 留給人工補寫**
6. **P0 實戰化：建立 high-conviction top-k OOS ROI gate，把研究 winner 轉成可拒單部署候選**
   - `data/high_conviction_topk_oos_matrix.json` 已產出 `generated_at=2026-05-25T00:11:24.828560+00:00` / `freshness=fresh` / `age_min=0.4` / `stale_after_min=60` / `deployment_blocking=False` / `rows=24` / `deployable_rows=0` / `risk_qualified_rows=6` / `runtime_blocked_candidates=6` / `bucket_rows=6/50` / `gap=44` / `support_progress_status=semantic_rebaseline_under_minimum` / `support_progress_reason=current exact support 6/50 below minimum (gap=44); semantic mismatch=calibration_window` / `regression_basis=legacy_or_different_semantic_signature` / `delta_vs_previous=0` / `previous_rows=6` / `support_rows_needed=44` / `stagnant_run_count=2` / `stalled_support_accumulation=False` / `escalate_to_blocker=True`；`/api/models/leaderboard` 與 Strategy Lab 高信心 OOS Top-K 部署門檻面板已改為最接近部署候選優先，並以操作員繁中 copy 顯示矩陣新鮮度、breaker release math 與即時支持脈絡；矩陣過期或即時分桶 / 支持 / release 條件未解除前仍 fail-closed。
