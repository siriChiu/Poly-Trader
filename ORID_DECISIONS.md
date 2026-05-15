# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-05-15 11:36:39 CST_

---

## 心跳 #1239 ORID

### O｜客觀事實
- collect + diagnostics refresh 完成：`Raw=33252 / Features=24439 / Labels=66470`；歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`；`simulated_pyramid_win=56.83%`。
- 即時部署阻塞點：`deployment_blocker=unsupported_exact_live_structure_bucket` / `streak=—` / `recent_window_wins=—/—` / `additional_recent_window_wins_needed=—`。
- q35 current-live bucket truth：`current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q35` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`。
- support progress：`status=regressed_under_minimum` / `regression_basis=same_identity_same_semantic_signature` / `legacy_supported_reference=50/50@1237` / `stagnant_run_count=4` / `stalled_support_accumulation=False` / `escalate_to_blocker=True`。
- latest recent-window diagnostics：`latest_window=250` / `win_rate=60.4%` / `dominant_regime=chop(91.6%)` / `avg_quality=+0.2352` / `avg_pnl=+0.0032` / `alerts=regime_concentration,regime_shift`。
- leaderboard / governance：`leaderboard_count=6` / `selected_feature_profile=core_plus_macro_plus_all_4h` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=single_role_governance_ok` / `current_closure=single_profile_alignment` / `payload_source=latest_persisted_snapshot` / `payload_stale=false` / `payload_age=4.7m`。
- source / venue blockers：`blocked_sparse_features=8`；top source blockers=`fin_netflow(source_auth_blocked/auth_missing, coverage=0.0%, archive_window=0.0%, forward_archive=ready)` / `claw(source_auth_blocked/auth_missing, coverage=14.6%, archive_window=87.2%, forward_archive=ready)` / `claw_intensity(source_auth_blocked/auth_missing, coverage=14.6%, archive_window=87.2%, forward_archive=ready)` / `nest_pred(source_tls_verify_failed/tls_verify_failed, coverage=16.2%, archive_window=97.0%, forward_archive=ready)`；fin_netflow=`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=4063` / `archive_window_coverage_pct=0.0`；venue proof 仍缺 credential / order ack / fill lifecycle；metadata smoke venue rows 已帶 proof_state / blockers / operator_next_action / verify_next。
- q35 scaling audit 已指出目前不是單點 bias50 closure： `overall_verdict=bias50_formula_may_be_too_harsh` / `redesign_verdict=base_stack_redesign_discriminative_reweight_crosses_floor_but_execution_blocked` / `runtime_gap_to_floor=0.005` / `redesign_entry_quality=0.5535` / `redesign_allowed_layers=0` / `positive_discriminative_gap=True` / `execution_blocked_after_floor_cross=True`。
- 實戰化 P0：`data/high_conviction_topk_oos_matrix.json` 已產出 `generated_at=2026-05-15T03:02:59.085489+00:00` / `freshness=fresh` / `age_min=28.6` / `stale_after_min=60` / `deployment_blocking=False` / `rows=24` / `deployable_rows=0` / `risk_qualified_rows=6` / `runtime_blocked_candidates=6` / `bucket_rows=0/50` / `gap=50`；最接近部署候選 `model=logistic_regression` / `top_k=top_2pct` / `tier=runtime_blocked_oos_pass` / `bucket_rows=0/50` / `gap=50`，仍被矩陣新鮮度或即時分桶 / 支持 / release gate 擋下。
- 本輪產品化前進：current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth；q35 score-only / execution-blocked truth 已產品化到 `hb_predict_probe.py`、`live_decision_quality_drilldown.py` 與 `auto_propose_fixes.py`，probe/drilldown/issue copy 現在同步顯示 `redesign_entry_quality=0.5535`、`redesign_allowed_layers_after=0`、`runtime_allowed_layers=0`、`runtime_allowed_layers_reason=unsupported_exact_live_structure_bucket`、`runtime_deployment_blocker=unsupported_exact_live_structure_bucket`，避免 operator 把 discriminative redesign 的 scoring floor-cross 誤讀成 deployment closure；`/execution` 快捷列已補上 `/api/status` 初次同步 fail-closed：買入 / 啟用自動模式暫停，減碼保留；`/api/execution/overview` / `/api/execution/runs` 已走 20s operator-workspace timeout，避免 8s default 把可用 Bot 營運 payload 誤報成 `API timeout`；`/api/trade` 買入 / 加倉直接入口也會依即時部署阻塞點 409 暫停，且保留減倉 / 賣出風險降低路徑；`/execution/status` 與 `/execution` 已顯示即時部署阻塞條件卡；`runtime_closure_summary` 已由 `model/runtime_closure.py` 共用中文化，避免後端英文枚舉與混合式治理文案泄漏到 Dashboard / Strategy Lab / Execution Status；metadata smoke venue rows 已帶 per-venue proof_state / blockers / operator_next_action / verify_next，讓 Dashboard / Execution / Lab 直接顯示實單證據缺口；`recommended_patch=—` / `status=—` / `reference_scope=—`。

### R｜感受直覺
- 這輪最需要防止的誤讀，是把 `0/50` 的 same-bucket support 或 `—` 參考 patch 誤讀成已可部署；目前 live blocker 已切到 `unsupported_exact_live_structure_bucket`。
- current live 已落在 `chop/CAUTION/CAUTION|base_caution_regime_or_bias|q35`；如果 UI / docs 沒同步 latest artifacts，operator 很容易把 spillover pocket、舊 bucket，或 `/api/status` 尚未返回的 loading 狀態誤讀成可操作 runtime 真相。

### I｜意義洞察
1. **support truth ≠ deployment closure**：`support=0/50` 且 `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only` 只代表 same-bucket support 狀態，真正 deployment blocker 仍由 latest runtime truth 決定。
2. **真正主 blocker 已切到 q35 current-live bucket exact-support shortage**：recent pathological slice 仍是造成 `unsupported_exact_live_structure_bucket` 的根因切片，不能再沿用 breaker-first 舊敘事。
3. **docs overwrite sync 的角色是護欄，不是主阻塞**：current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth；q35 score-only / execution-blocked 欄位現在在 probe、drilldown、issue copy 同步出現，operator 會看到 scoring floor-cross 後仍 `allowed_layers=0` 與 `unsupported_exact_live_structure_bucket` blocker，而不是只看到 `redesign_entry_quality>=0.55`。
4. **實戰化不是堆模型，而是可拒單部署治理**：high-conviction top-k OOS ROI gate 把六色帽 / 研究交叉分析轉成產品契約；排序先分離離線驗證 / 模型風控門檻與即時分桶 / 支持 gate，避免最高 ROI 但高回撤 / 負最差分折的列誤導部署決策。

### D｜決策行動
- **Owner**：即時執行治理 lane
- **Action**：維持 current-live exact-support truth，並把 q35 current-live bucket support truth 與 deployment closure 邊界持續顯示清楚；下一步沿 recent pathological slice 與 exact-support accumulation 繼續追根因；probe/drilldown/issues 必須保留 q35 redesign/runtime 欄位，讓 score-only floor-cross 明確標為 execution-blocked。
- **研究到產品 gate**：walk-forward OOS top-k matrix 已透過 `/api/models/leaderboard` 與 Strategy Lab 高信心 OOS Top-K 部署門檻面板可視化；operator 現在會先看到最接近部署候選（離線驗證 / 風控已過但只剩矩陣新鮮度 / 即時分桶 / 支持 / release gate 的 rows），並看到矩陣新鮮度、支持狀態、治理路徑、部署阻塞、即時分桶、樣本數、recent-window wins、required wins、additional wins needed，且列級即時訊號已改用繁中操作語；矩陣過期或即時分桶 / 支持 / release blockers 未解除前仍維持 fail-closed。
- **Artifacts**：`ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md`、`data/live_predict_probe.json`、`data/live_decision_quality_drilldown.json`、`data/recent_drift_report.json`、`data/high_conviction_topk_oos_matrix.json`。
- **Verify**：`PYTHONPATH=. python -m pytest tests/test_auto_propose_fixes.py tests/test_hb_predict_probe.py tests/test_live_decision_quality_drilldown.py -q`（82 passed）；`PYTHONPATH=. python -m pytest tests/test_hb_parallel_runner.py -q`（134 passed）；`PYTHONPATH=. python -m pytest tests/test_server_startup.py tests/test_frontend_decision_contract.py -q`（130 passed）；`cd web && npm run build`（tsc+vite build passed）；`HB_RUN_LABEL=1239 PYTHONPATH=. python scripts/hb_parallel_runner.py --fast --hb 1239`（通過並刷新 docs/artifacts）；`data/live_predict_probe.json` 與 `data/live_decision_quality_drilldown.json` 均顯示 q35 runtime blocker / exact support gap。
- **If fail**：只要 docs / UI 再次把 `unsupported_exact_live_structure_bucket` 誤寫成 breaker-first、漏掉 q35 current-live bucket rows，或把 support closure 誤讀成 deployment closure，就把 heartbeat 升級回 current-state governance blocker。
