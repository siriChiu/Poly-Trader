# ISSUES.md — Current State Only

_最後更新：2026-04-28 03:43:44 CST_

只保留目前有效問題；由 heartbeat runner overwrite sync，避免 current-state markdown 落後 issues.json / live artifacts。

---

## 當前主線事實
- **最新 full heartbeat #1084 已完成 collect + diagnostics refresh**
  - `Raw=32392 / Features=23810 / Labels=65358`
  - 歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`
  - `simulated_pyramid_win=56.90%`
- **canonical current-live blocker 已切到 current-live exact-support truth**
  - `deployment_blocker=unsupported_exact_live_structure_bucket` / `streak=None` / `recent_window_wins=None/None` / `additional_recent_window_wins_needed=—`
  - `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q00` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_unsupported_block`
- **recent canonical diagnostics 已刷新**
  - `latest_window=100` / `win_rate=84.0%` / `dominant_regime=chop(82.0%)` / `avg_quality=+0.4164` / `avg_pnl=+0.0076` / `alerts=label_imbalance,regime_shift`
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split` / `payload_source=latest_persisted_snapshot` / `payload_stale=false` / `payload_age=0.0m`
- **source / venue blockers 仍開啟**
  - `blocked_sparse_features=8` / `{'archive_required': 3, 'snapshot_only': 4, 'short_window_public_api': 1}`
  - fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3833` / `archive_window_coverage_pct=0.0`
  - venue：`live exchange credential / order ack lifecycle / fill lifecycle` 尚未有 runtime-backed proof；`execution_metadata_smoke.venues[]` 已提供 per-venue `proof_state / blockers / operator_next_action / verify_next` 給 Dashboard / Execution / Lab 直接顯示證據缺口
- **Execution Console / `/api/trade` 已 fail-closed（同步中 + 阻塞 + 直接 API）**
  - 前端快捷：`manual_trade=paused_when_status_syncing_or_deployment_blocked` / `automation_enable=paused_when_status_syncing_or_deployment_blocked`；`/api/status` 初次同步前與阻塞期間都只保留查看阻塞原因與重新整理入口。`/api/execution/overview` / `/api/execution/runs` 已走 20s operator-workspace timeout，避免後端並行診斷時 8s default 把可用 payload 誤報成 `API timeout`。後端 `POST /api/trade` 對買入 / 加倉會先讀即時部署阻塞點；阻塞時回 409 `current_live_deployment_blocker`，只保留減倉 / 賣出風險降低路徑
- **Execution Status / Bot 營運 已顯示熔斷解除條件**
  - `最近 None 筆目前 None/None，還差 — 勝；支持樣本 / q15 修補不可取代熔斷解除條件`；`/execution/status` 與 `/execution` 會先顯示熔斷解除條件，再顯示 support / q15 治理背景
- **heartbeat current-state docs overwrite sync 已自動化**
  - `scripts/hb_parallel_runner.py` 現在會在 `auto_propose_fixes.py` 後自動覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 目的：避免 markdown docs 落後 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json`，讓 cron 心跳真正完成 docs overwrite 閉環

---

## Open Issues

### P0. current live bucket CAUTION|base_caution_regime_or_bias|q00 exact support is missing and remains the deployment blocker (0/50)
- 目前真相：`deployment_blocker=unsupported_exact_live_structure_bucket` / `bucket=CAUTION|base_caution_regime_or_bias|q00` / `support=0/50` / `gap=50` / `runtime_closure_state=patch_inactive_or_blocked`
- same-bucket truth：`support_route_verdict=exact_bucket_unsupported_block` / `support_governance_route=exact_live_lane_proxy_available` / `recommended_patch=core_plus_macro_plus_all_4h` / `recommended_patch_status=reference_only_non_current_live_scope` / `reference_scope=bull|CAUTION`
- runtime/API guardrail：`POST /api/trade` 對買入 / 加倉會先讀即時部署阻塞點；阻塞時回 409 `current_live_deployment_blocker`，只保留減倉 / 賣出風險降低路徑。
- 下一步：把 current-live blocker 語義切到 exact-support truth；在 current live bucket 補滿 minimum rows 前，不要把 proxy rows、reference patch、或 breaker 舊敘事誤當成已解除 blocker。

### P1. model stability still needs work (cv=0.5440, cv_std=0.0373, cv_worst=0.5067)
- 目前真相：`cv_accuracy=0.5440185341196293` / `cv_std=0.0372788542544229` / `cv_worst=0.5067396798652064`
- 下一步：優先比較 support-aware / shrinkage profiles 與 current bucket robustness，避免把治理 blocker 誤當單純 parity 問題。

### P1. TW-IC 28 vs Global IC 16 — 信號強依賴近期資料
- 目前真相：`global_pass=16` / `tw_pass=28` / `total_features=30`
- 下一步：市場 regime 可能已變化; 考慮 regime-gated feature weighting

### P1. support-aware core_plus_macro_plus_all_4h patch must stay visible but reference-only outside current live scope
- 目前真相：`bucket=CAUTION|base_caution_regime_or_bias|q00` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_unsupported_block` / `governance_route=exact_live_lane_proxy_available`
- 下一步：Keep the same recommended_patch summary across /api/status, /lab, hb_predict_probe.py, live_decision_quality_drilldown.py, and docs; the patch describes a spillover/broader lane rather than the current live scope, so do not promote it to a deployable runtime patch even though exact support is available.

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
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3833` / `archive_window_coverage_pct=0.0`
- 下一步：Configure COINGLASS_API_KEY, then keep heartbeat collection running until successful ETF-flow snapshots replace auth_missing rows and coverage starts to move.
- 驗證：
  - data/execution_metadata_smoke.json
  - /api/features/coverage

### P1. leaderboard comparable rows are back; keep the recent-window contract stable and cron-safe
- 目前真相：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split` / `payload_source=latest_persisted_snapshot` / `payload_stale=false` / `payload_age=0.0m`
- 下一步：Keep /api/models/leaderboard and Strategy Lab aligned on latest bounded walk-forward plus the recent-two-year backtest policy; do not regress to placeholder-only or ambiguous backtest windows.
- 驗證：
  - browser /lab
  - curl http://127.0.0.1:<active-backend>/api/models/leaderboard
  - pytest tests/test_model_leaderboard.py tests/test_strategy_lab.py tests/test_frontend_decision_contract.py -q

---

## Current Priority
1. **維持 current-live exact-support blocker truth，同時保留 current live bucket support rows 可 machine-read**
2. **持續沿 recent canonical pathological slice 追根因，不要 generic 化 blocker**
3. **守住 current live bucket support / reference-only patch、leaderboard dual-role governance、venue/source blockers 可見性**
4. **讓 heartbeat 自動 overwrite sync current-state docs，不再把 docs drift 留給人工補寫**
