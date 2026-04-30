# ISSUES.md — Current State Only

_最後更新：2026-04-30 08:12:12 CST_

只保留目前有效問題；由 heartbeat / productization run overwrite sync，避免 current-state markdown 落後 issues.json / live artifacts。

---

## 當前主線事實

- **最新 full heartbeat #1143 已完成 collect + diagnostics refresh**
  - `Raw=32495 / Features=23913 / Labels=65598`
  - 歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`
  - `simulated_pyramid_win=56.73%`
- **canonical current-live blocker 是 exact-support truth，不是 breaker 舊敘事**
  - `deployment_blocker=unsupported_exact_live_structure_bucket`
  - `current_live_structure_bucket=CAUTION|structure_quality_caution|q15` / `support=0/50` / `gap=50`
  - `support_route_verdict=insufficient_support_everywhere` / `support_governance_route=exact_live_lane_proxy_available`
  - support progress：`status=semantic_rebaseline_under_minimum` / `regression_basis=legacy_or_different_semantic_signature` / `legacy_supported_reference=53/50@20260419b`
- **recent canonical diagnostics 已刷新但不是 deployment closure**
  - `latest_window=100` / `win_rate=24.0%` / `dominant_regime=chop(87.0%)` / `avg_quality=-0.0602` / `avg_pnl=-0.0043` / `alerts=regime_shift`
- **Execution Console / Status 已 fail-closed 並維持操作員中文 copy**
  - `/api/status` 初次同步前與部署阻塞期間，買入 / 加倉 / 啟用自動模式暫停；減碼 / 賣出風險降低、切手動、查看阻塞原因、重新整理仍可用。
  - `POST /api/trade` 買入 / 加倉阻塞時回 409 `current_live_deployment_blocker`；風險降低方向保留。
  - 本輪補強 `web/src/utils/runtimeCopy.ts`：`insufficient_support_everywhere` 與 `exact_live_lane_proxy_available` 在支持路徑、治理路徑與 runtime summary 中都轉為繁中操作員 copy，不再在 `/execution` 洩漏 raw route token。
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=current_full_no_bull_collapse_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split` / `payload_source=latest_persisted_snapshot` / `payload_stale=true` / `payload_age=1.0h`
- **source / venue blockers 仍開啟**
  - `blocked_sparse_features=8` / `{'archive_required': 3, 'snapshot_only': 4, 'short_window_public_api': 1}`
  - fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3928` / `archive_window_coverage_pct=0.0`
  - venue：Binance metadata OK 但仍缺 live exchange credential、order ack lifecycle、fill lifecycle proof；OKX 設定停用且僅 metadata 觀測。
- **high-conviction Top-K OOS gate 已產出但仍 runtime-blocked**
  - `data/high_conviction_topk_oos_matrix.json`：`rows=24` / `deployable_rows=0` / `risk_qualified_rows=6` / `runtime_blocked_candidates=6`
  - nearest candidate：`logistic_regression / all / top_2pct`，`oos_roi=0.9324` / `win_rate=0.8621` / `profit_factor=19.8864` / `max_drawdown=0.022` / `trades=58`，但因 current-live support gate 仍 `not_deployable`。

---

## Open Issues

### P0. current live q15 exact support missing remains the deployment blocker (0/50)
- 目前真相：`deployment_blocker=unsupported_exact_live_structure_bucket` / `bucket=CAUTION|structure_quality_caution|q15` / `support=0/50` / `gap=50` / `runtime_closure_state=patch_inactive_or_blocked`
- same-bucket truth：`support_route_verdict=insufficient_support_everywhere` / `support_governance_route=exact_live_lane_proxy_available` / `recommended_patch=—` / `recommended_patch_status=—`
- 下一步：補 current-live bucket exact support rows 或明確維持 no-deploy；不得用 proxy rows、legacy reference、venue metadata OK、或 stale patch 當部署閉環。
- 驗證：`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、browser `/execution`、browser `/execution/status`、browser `/lab`。

### P0. high-conviction OOS candidates must stay fail-closed until live support / venue proof pass
- 目前真相：離線 Top-K OOS 有 risk-qualified rows，但 `deployable_rows=0`，最近部署候選仍被 `unsupported_exact_live_structure_bucket` 擋住。
- 下一步：Strategy Lab 排序可展示 nearest deployable candidate，但 UI/API 必須同時顯示 support route、governance route、deployment blocker、current bucket rows；不得把 ROI winner 直接標為 deployable。
- 驗證：`python -m pytest tests/test_model_leaderboard.py tests/test_frontend_decision_contract.py -k high_conviction -q`、browser `/lab`。

### P1. venue readiness remains metadata-only / unverified
- 目前真相：Binance 啟用但只有公開 metadata proof；OKX 停用；兩者都缺 credential、order ack、fill lifecycle runtime proof。
- 下一步：補交易所憑證與 sandbox / tiny order lifecycle proof；未完成前 Dashboard、Execution、Lab 必須顯示 per-venue blockers。
- 驗證：`data/execution_metadata_smoke.json`、browser `/execution`、browser `/execution/status`、browser `/lab`。

### P1. sparse-source history / auth blockers still limit production features
- 目前真相：8 個 sparse features blocked；fin_netflow 因 CoinGlass auth missing 仍 `source_auth_blocked`。
- 下一步：配置所需資料來源憑證後持續 heartbeat collection，讓 successful forward snapshots 取代 auth_missing rows；歷史缺口仍需 archive/export loader。
- 驗證：`/api/features/coverage`、`data/feature_coverage_report.json`、heartbeat source_blockers。

### P1. recent canonical pathology requires monitoring, not deployment override
- 目前真相：recent window 100 rows 呈現 regime concentration / low win rate，但 current-live blocker 是 exact support missing。
- 下一步：持續追 recent pathological slice，避免 drift truth 只存在 artifact；但不可把 recent drift 當成解除 exact support blocker 的理由。
- 驗證：`python scripts/recent_drift_report.py`、probe/API/UI drift cards。

---

## Current Priority

1. 守住 `unsupported_exact_live_structure_bucket` 作為唯一 current-live deployment blocker，並保持 q15 `0/50` support truth machine-readable。
2. 維持 Execution Console / Status fail-closed 與繁中 operator copy；route/governance token 不得在 runtime summary 直接外洩。
3. 讓 high-conviction Top-K OOS gate 繼續推進研究→模擬觀察→影子驗證，但在 support / venue proof 未過前不得部署。
4. 持續讓 venue/source blockers、leaderboard dual-role governance、docs overwrite sync 與 live artifacts 對齊。
