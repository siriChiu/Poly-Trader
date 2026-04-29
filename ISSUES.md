# ISSUES.md — Current State Only

_最後更新：2026-04-29 11:20:42 CST_

只保留目前有效問題；由 heartbeat runner overwrite sync，避免 current-state markdown 落後 issues.json / live artifacts。

---

## 當前主線事實
- **最新 full heartbeat #1115 已完成 collect + diagnostics refresh**
  - `Raw=32458 / Features=23876 / Labels=65529`
  - 歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`
  - `simulated_pyramid_win=56.72%`
- **canonical 即時部署阻塞仍是熔斷優先真相**
  - `deployment_blocker=circuit_breaker_active` / `streak=108` / `recent_window_wins=0/50` / `additional_recent_window_wins_needed=15`
  - `current_live_structure_bucket=CAUTION|structure_quality_caution|q15` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_proxy_reference_only`
  - support progress：`status=semantic_rebaseline_under_minimum` / `regression_basis=legacy_or_different_semantic_signature` / `legacy_supported_reference=53/50@20260419b`
- **recent canonical diagnostics 已刷新**
  - `latest_window=100` / `win_rate=0.0%` / `dominant_regime=chop(75.0%)` / `avg_quality=-0.2794` / `avg_pnl=-0.0110` / `alerts=constant_target,regime_shift`
  - canonical tail root cause 已產品化：`rows=100` / `losses=100` / `dominant_loss_regime=chop` / `tp_miss=100/100` / `high_underwater=86/100` / `top_4h_shift=feat_4h_bias200,feat_4h_bias50,feat_4h_bb_pct_b`；`/api/status.recent_canonical_drift.canonical_tail_root_cause` 與 Dashboard/Strategy Lab 共用的 RecentCanonicalDriftCard 會直接顯示 loss-path、regime loss breakdown、4H shift。
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split` / `payload_source=latest_persisted_snapshot` / `payload_stale=true` / `payload_age=7.9h`
- **source / venue blockers 仍開啟**
  - `blocked_sparse_features=8` / `{'archive_required': 3, 'snapshot_only': 4, 'short_window_public_api': 1}`
  - fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3891` / `archive_window_coverage_pct=0.0`
  - venue：`live exchange credential / order ack lifecycle / fill lifecycle` 尚未有 runtime-backed proof；`execution_metadata_smoke.venues[]` 已提供 per-venue `proof_state / blockers / operator_next_action / verify_next` 給 Dashboard / Execution / Lab 直接顯示證據缺口
- **Execution Console / `/api/trade` 已 fail-closed（同步中 + 阻塞 + 直接 API）**
  - 前端快捷：`manual_trade=paused_when_status_syncing_or_deployment_blocked` / `automation_enable=paused_when_status_syncing_or_deployment_blocked`；`/api/status` 初次同步前與阻塞期間都只保留查看阻塞原因與重新整理入口。`/api/execution/overview` / `/api/execution/runs` 已走 20s operator-workspace timeout，避免後端並行診斷時 8s default 把可用 payload 誤報成 `API timeout`。後端 `POST /api/trade` 對買入 / 加倉會先讀即時部署阻塞點；阻塞時回 409 `current_live_deployment_blocker`，只保留減倉 / 賣出風險降低路徑
- **Execution Status / Bot 營運 已顯示熔斷解除條件**
  - `最近 50 筆目前 0/50，還差 15 勝；支持樣本 / q15 修補不可取代熔斷解除條件`；`/execution/status` 與 `/execution` 會先顯示熔斷解除條件，再顯示 support / q15 治理背景
- **heartbeat current-state docs overwrite sync 已自動化**
  - `scripts/hb_parallel_runner.py` 現在會在 `auto_propose_fixes.py` 後自動覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 目的：避免 markdown docs 落後 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json`，讓 cron 心跳真正完成 docs overwrite 閉環

---

## Open Issues

### P0. 連續 108 筆 1440m simulated_pyramid_win=0
- 目前真相：`canonical_horizon_minutes=1440` / `losing_streak=108` / `all_horizon_losing_streak=0`
- 下一步：檢查 recent canonical labels / regime breakdown / circuit breaker；必要時升級為 distribution-aware drift 調查

### P0. 熔斷解除條件仍是唯一即時部署阻塞點
- 目前真相：`deployment_blocker=circuit_breaker_active` / `streak=108` / `recent 50 wins=0/50` / `additional_recent_window_wins_needed=15`
- same-bucket truth：`bucket=CAUTION|structure_quality_caution|q15` / `support=0/50` / `support_route_verdict=exact_bucket_missing_proxy_reference_only` / `support_governance_route=exact_live_bucket_proxy_available`
- support progress：`status=semantic_rebaseline_under_minimum` / `regression_basis=legacy_or_different_semantic_signature` / `legacy_supported_reference=53/50@20260419b`
- runtime/API guardrail：`POST /api/trade` 對買入 / 加倉會先讀即時部署阻塞點；阻塞時回 409 `current_live_deployment_blocker`，只保留減倉 / 賣出風險降低路徑。
- 下一步：先把即時部署阻塞語義切回熔斷解除條件；在熔斷未解除前，不要把 q15/q35 support 或 floor-gap 當成本輪主阻塞。 最近 50 筆需至少 15 勝，當前 0 勝，還差 15 勝；同時連續虧損必須 < 50。

### P0. recent canonical window 100 rows = distribution_pathology
- 目前真相：`latest_window=100` / `win_rate=0.0%` / `dominant_regime=chop(75.0%)` / `alerts=constant_target,regime_shift` / `tail_streak=100x0`
- canonical tail root cause：`rows=100` / `losses=100` / `tp_miss=100` / `dd_breach=0` / `high_underwater=86` / `avg_time_underwater=77.97%` / `dominant_loss_regime=chop` / `top_4h_shift=feat_4h_bias200,feat_4h_bias50,feat_4h_bb_pct_b`
- API/UI contract：`data/recent_drift_report.json` 與 `data/canonical_tail_root_cause.json` 持久化 root cause；`/api/status.recent_canonical_drift.canonical_tail_root_cause` 正規化後供 RecentCanonicalDriftCard 顯示。
- 下一步：用這個 loss-path + 4H shift truth 追 q15/bear/CAUTION live DQ，避免再把 recent pathology 寫成 generic drift；若 artifact/API/UI 任一層漏掉 root cause，升級為 product surface blocker。

### P1. Train-CV gap = 17.4pp (65.6% vs 48.2%)
- 下一步：更正則化: 增加 reg_alpha/reg_lambda; 減少 max_depth; 或減少特徵數

### P1. live predictor decision-quality contract is runtime-blocked by recent pathology, a toxic exact live lane, or a severe narrowed pathology lane
- 目前真相：`live_scope=regime_gate` / `deployment_blocker=circuit_breaker_active` / `window=100` / `alerts=constant_target, regime_shift` / `allowed_layers=0`
- 下一步：把 hb_predict_probe 納入每輪 heartbeat 驗證，對 exact live lane、當前 calibration scope 與 worst narrowed scope 做 root-cause drill-down；優先檢查 exact lane 是否仍是 ALLOW 但 canonical true-negative share 已偏高，並交叉比對 recent same-scope / narrowed-scope 4H shifts、scope selection、與 execution guardrail 是否只是正確地把壞 pocket 擋下。 live_scope=regime_gate, regime=bear/CAUTION, label=D, sample_size=225, window=100, alerts=['label_imbalance'], expected_win_rate=0.18, expected_pnl=-0.0056, expected_quality=-0.1032, layers=1→0, top_shifts=feat_4h_dist_swin…

### P1. model stability still needs work (cv=0.5271, cv_std=0.0275, cv_worst=0.4996)
- 目前真相：`cv_accuracy=0.5270553691275168` / `cv_std=0.027474832214765127` / `cv_worst=0.49958053691275167`
- 下一步：優先比較 support-aware / shrinkage profiles 與 current bucket robustness，避免把治理 blocker 誤當單純 parity 問題。

### P1. TW-IC 24 vs Global IC 19 — 信號強依賴近期資料
- 目前真相：`global_pass=19` / `tw_pass=24` / `total_features=30`
- 下一步：市場 regime 可能已變化; 考慮 regime-gated feature weighting

### P1. venue readiness is still unverified
- 目前真相：`binance=config enabled + public-only + metadata OK` / `okx=config disabled + public-only + metadata OK` / `missing_runtime_proof=live exchange credential, order ack lifecycle, fill lifecycle`
- API/UI contract：`execution_metadata_smoke.venues[]` 已帶 `proof_state / blockers / operator_next_action / verify_next`，Dashboard、`/execution/status`、`/execution`、`/lab` 可直接顯示每個場館的實單證據缺口，不再只靠 metadata OK/FAIL 猜測 readiness。
- 下一步：Keep per-venue blockers explicitly visible on Dashboard, /lab, and /execution/status until credentials, order ack lifecycle, and fill lifecycle each have runtime-backed proof.
- 驗證：
  - browser /execution
  - browser /execution/status
  - browser /lab
  - data/execution_metadata_smoke.json

### P1. fin_netflow remains source_auth_blocked because COINGLASS_API_KEY is missing
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3891` / `archive_window_coverage_pct=0.0`
- 下一步：Configure COINGLASS_API_KEY, then keep heartbeat collection running until successful ETF-flow snapshots replace auth_missing rows and coverage starts to move.
- 驗證：
  - data/execution_metadata_smoke.json
  - /api/features/coverage

### P1. leaderboard comparable rows are back; keep the recent-window contract stable and cron-safe
- 目前真相：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split` / `payload_source=latest_persisted_snapshot` / `payload_stale=true` / `payload_age=7.9h`
- 下一步：Keep /api/models/leaderboard and Strategy Lab aligned on latest bounded walk-forward plus the recent-two-year backtest policy; do not regress to placeholder-only or ambiguous backtest windows.
- 驗證：
  - browser /lab
  - curl http://127.0.0.1:<active-backend>/api/models/leaderboard
  - pytest tests/test_model_leaderboard.py tests/test_strategy_lab.py tests/test_frontend_decision_contract.py -q

### P1. q15 exact support under minimum after semantic rebaseline while breaker is active (0/50)
- 目前真相：`bucket=CAUTION|structure_quality_caution|q15` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_proxy_reference_only` / `governance_route=exact_live_bucket_proxy_available` / `breaker_context=circuit_breaker_active`
- support progress：`status=semantic_rebaseline_under_minimum` / `regression_basis=legacy_or_different_semantic_signature` / `legacy_supported_reference=53/50@20260419b`
- 下一步：Treat legacy supported rows as reference-only: keep support_identity/regression_basis/legacy_supported_reference visible in probe/API/UI/docs, keep the current-live exact-support blocker open, and do not describe this as same-identity support regression unless the semantic signature matches.

---

## Current Priority
1. **維持熔斷優先真相，同時保留 q15 current-live bucket support rows 可 machine-read**
2. **持續沿 recent canonical pathological slice 追根因；loss-path / regime loss breakdown / 4H shift 必須在 artifact + API + UI 同步可見**
3. **守住 q15 current-live bucket support truth / blocker truth、leaderboard dual-role governance、venue/source blockers 可見性**
4. **讓 heartbeat 自動 overwrite sync current-state docs，不再把 docs drift 留給人工補寫**
