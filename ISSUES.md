# ISSUES.md — Current State Only

_最後更新：2026-04-25 15:30:58 CST_

只保留目前有效問題；由 heartbeat runner overwrite sync，避免 current-state markdown 落後 issues.json / live artifacts。

---

## 當前主線事實
- **最新 full heartbeat #20260425_1527 已完成 collect + diagnostics refresh**
  - `Raw=32242 / Features=23660 / Labels=65045`
  - 歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`
  - `simulated_pyramid_win=56.88%`
- **canonical 即時部署阻塞仍是熔斷優先真相**
  - `deployment_blocker=circuit_breaker_active` / `streak=11` / `recent_window_wins=2/50` / `additional_recent_window_wins_needed=13`
  - `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=80/50` / `gap=0` / `support_route_verdict=exact_bucket_supported`
  - support progress：`status=exact_supported` / `regression_basis=current_identity` / `legacy_supported_reference=121/50@20260424a`
- **recent canonical diagnostics 已刷新**
  - `latest_window=100` / `win_rate=17.0%` / `dominant_regime=bull(99.0%)` / `avg_quality=-0.0621` / `avg_pnl=-0.0039` / `alerts=label_imbalance,regime_concentration,regime_shift`
- **leaderboard / governance 已收斂為 single-role alignment**
  - `leaderboard_count=6` / `selected_feature_profile=current_full_no_bull_collapse_4h` / `support_aware_profile=core_plus_macro` / `governance_contract=single_role_governance_ok` / `current_closure=single_profile_alignment` / `payload_source=latest_persisted_snapshot` / `payload_stale=true` / `payload_age=39.1m`
- **source / venue blockers 仍開啟**
  - `blocked_sparse_features=8` / `{'archive_required': 3, 'snapshot_only': 4, 'short_window_public_api': 1}`
  - fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3709` / `archive_window_coverage_pct=0.0`
  - venue：`live exchange credential / order ack lifecycle / fill lifecycle` 尚未有 runtime-backed proof；`execution_metadata_smoke.venues[]` 已提供 per-venue `proof_state / blockers / operator_next_action / verify_next` 給 Dashboard / Execution / Lab 直接顯示證據缺口
- **Execution Console / `/api/trade` 已 fail-closed（同步中 + 阻塞 + 直接 API）**
  - 前端快捷：`manual_trade=paused_when_status_syncing_or_deployment_blocked` / `automation_enable=paused_when_status_syncing_or_deployment_blocked`；`/api/status` 初次同步前與阻塞期間都只保留查看阻塞原因與重新整理入口。`/api/execution/overview` / `/api/execution/runs` 已走 20s operator-workspace timeout，避免後端並行診斷時 8s default 把可用 payload 誤報成 `API timeout`。後端 `POST /api/trade` 對買入 / 加倉會先讀即時部署阻塞點；阻塞時回 409 `current_live_deployment_blocker`，只保留減倉 / 賣出風險降低路徑
- **Execution Status / Bot 營運 已顯示熔斷解除條件**
  - `最近 50 筆目前 2/50，還差 13 勝；支持樣本 / q15 修補不可取代熔斷解除條件`；`/execution/status` 與 `/execution` 會先顯示熔斷解除條件，再顯示 support / q15 治理背景
- **heartbeat current-state docs overwrite sync 已自動化**
  - `scripts/hb_parallel_runner.py` 現在會在 `auto_propose_fixes.py` 後自動覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 目的：避免 markdown docs 落後 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json`，讓 cron 心跳真正完成 docs overwrite 閉環

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
- 目前真相：`deployment_blocker=circuit_breaker_active` / `streak=11` / `recent 50 wins=2/50` / `additional_recent_window_wins_needed=13`
- same-bucket truth：`bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=80/50` / `support_route_verdict=exact_bucket_supported` / `support_governance_route=exact_live_bucket_supported`
- support progress：`status=exact_supported` / `regression_basis=current_identity` / `legacy_supported_reference=121/50@20260424a`
- runtime/API guardrail：`POST /api/trade` 對買入 / 加倉會先讀即時部署阻塞點；阻塞時回 409 `current_live_deployment_blocker`，只保留減倉 / 賣出風險降低路徑。
- 下一步：先把 current-live blocker 語義切回 circuit breaker release math；在 breaker 未解除前，不要把 q15/q35 support 或 floor-gap 當成本輪主 blocker。 recent 50 需至少 15 勝，當前 2 勝，還差 13 勝；同時 streak 必須 < 50。

### P1. model stability still needs work (cv=0.5948, cv_std=0.1228, cv_worst=0.4720)
- 目前真相：`cv_accuracy=0.5947837150127226` / `cv_std=0.12277353689567427` / `cv_worst=0.4720101781170484`
- 下一步：優先比較 support-aware / shrinkage profiles 與 current bucket robustness，避免把治理 blocker 誤當單純 parity 問題。

### P1. TW-IC 27 vs Global IC 17 — 信號強依賴近期資料
- 目前真相：`global_pass=17` / `tw_pass=27` / `total_features=30`
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
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3709` / `archive_window_coverage_pct=0.0`
- 下一步：Configure COINGLASS_API_KEY, then keep heartbeat collection running until successful ETF-flow snapshots replace auth_missing rows and coverage starts to move.
- 驗證：
  - data/execution_metadata_smoke.json
  - /api/features/coverage

### P1. leaderboard comparable rows are back; keep the recent-window contract stable and cron-safe
- 目前真相：`leaderboard_count=6` / `selected_feature_profile=current_full_no_bull_collapse_4h` / `support_aware_profile=core_plus_macro` / `governance_contract=single_role_governance_ok` / `current_closure=single_profile_alignment` / `payload_source=latest_persisted_snapshot` / `payload_stale=true` / `payload_age=39.1m`
- 下一步：Keep /api/models/leaderboard and Strategy Lab aligned on latest bounded walk-forward plus the recent-two-year backtest policy; do not regress to placeholder-only or ambiguous backtest windows.
- 驗證：
  - browser /lab
  - curl http://127.0.0.1:<active-backend>/api/models/leaderboard
  - pytest tests/test_model_leaderboard.py tests/test_strategy_lab.py tests/test_frontend_decision_contract.py -q

### P1. recent canonical window 100 rows = distribution_pathology but current live regime is outside the blocker pocket
- 目前真相：`window=100` / `interpretation=distribution_pathology` / `win_rate=0.17` / `dominant_regime=bull` / `dominant_regime_share=0.99` / `avg_pnl=-0.0039`
- 下一步：保留 recent canonical drift 監控與 blocker-window evidence；目前 live predictor 沒有套用 recent pathology guardrail，且 current live regime 不等於 blocker dominant regime，因此降為 P1 監控，不得當成 deployment closure。

---

## Current Priority
1. **維持熔斷優先真相，同時保留 q15 current-live bucket support rows 可 machine-read**
2. **持續沿 recent canonical pathological slice 追根因，不要 generic 化 blocker**
3. **守住 q15 current-live bucket support truth / blocker truth、leaderboard single-role governance、venue/source blockers 可見性**
4. **讓 heartbeat 自動 overwrite sync current-state docs，不再把 docs drift 留給人工補寫**
