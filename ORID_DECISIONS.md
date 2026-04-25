# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-25 22:01:58 CST_

---

## 心跳 #1029 ORID

### O｜客觀事實
- collect + diagnostics refresh 完成：`Raw=32257 / Features=23675 / Labels=65085`；歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`；`simulated_pyramid_win=56.87%`。
- 即時部署阻塞點：`deployment_blocker=circuit_breaker_active` / `streak=14` / `recent_window_wins=9/50` / `additional_recent_window_wins_needed=6`。
- q15 current-live bucket truth：`current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=67/50` / `gap=0` / `support_route_verdict=exact_bucket_supported`。
- support progress：`status=exact_supported` / `regression_basis=current_identity` / `legacy_supported_reference=121/50@20260424a`。
- latest recent-window diagnostics：`latest_window=100` / `win_rate=9.0%` / `dominant_regime=bull(97.0%)` / `avg_quality=-0.1245` / `avg_pnl=-0.0052` / `alerts=label_imbalance,regime_concentration,regime_shift`。
- leaderboard / governance：`leaderboard_count=6` / `selected_feature_profile=current_full_no_bull_collapse_4h` / `support_aware_profile=current_full_no_bull_collapse_4h` / `governance_contract=single_role_governance_ok` / `current_closure=single_profile_alignment` / `payload_source=latest_persisted_snapshot` / `payload_stale=true` / `payload_age=7.2h`。
- source / venue blockers：`blocked_sparse_features=8`；fin_netflow=`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3723` / `archive_window_coverage_pct=0.0`；venue proof 仍缺 credential / order ack / fill lifecycle；metadata smoke venue rows 已帶 proof_state / blockers / operator_next_action / verify_next。
- 本輪產品化前進：current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth；`/execution` 快捷列已補上 `/api/status` 初次同步 fail-closed；`/api/execution/overview` / `/api/execution/runs` 已走 20s operator-workspace timeout，避免 8s default 把可用 Bot 營運 payload 誤報成 `API timeout`；`/api/trade` 買入 / 加倉直接入口也會依即時部署阻塞點 409 暫停，且保留減倉 / 賣出風險降低路徑；`/execution/status` 與 `/execution` 已顯示熔斷解除條件卡；metadata smoke venue rows 已帶 per-venue proof_state / blockers / operator_next_action / verify_next，讓 Dashboard / Execution / Lab 直接顯示實單證據缺口；`recommended_patch=—` / `status=—` / `reference_scope=—`。

### R｜感受直覺
- 這輪最需要防止的誤讀，是把 `67/50` 的 same-bucket support 或 `—` 參考 patch 誤讀成已可部署；熔斷解除條件仍是唯一即時部署阻塞點。
- current live 已落在 `chop/CAUTION/CAUTION|base_caution_regime_or_bias|q15`；如果 UI / docs 沒同步 latest artifacts，operator 很容易把 spillover pocket、舊 bucket，或 `/api/status` 尚未返回的 loading 狀態誤讀成可操作 runtime 真相。

### I｜意義洞察
1. **support truth ≠ deployment closure**：`support=67/50` 且 `support_route_verdict=exact_bucket_supported` 只代表 same-bucket support 狀態，真正 deployment blocker 仍由 latest runtime truth 決定。
2. **真正主阻塞仍是熔斷 + recent pathological slice**：目前該追的是解除條件與 recent canonical pathology，不是把 q15/q35 support 或 venue 話題誤升級成唯一根因。
3. **docs overwrite sync 的角色是護欄，不是主阻塞**：current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth；`/execution` 快捷列已補上 `/api/status` 初次同步 fail-closed；`/api/execution/overview` / `/api/execution/runs` 已走 20s operator-workspace timeout，避免 8s default 把可用 Bot 營運 payload 誤報成 `API timeout`；`/api/trade` 買入 / 加倉直接入口也會依即時部署阻塞點 409 暫停，且保留減倉 / 賣出風險降低路徑；`/execution/status` 與 `/execution` 已顯示熔斷解除條件卡；metadata smoke venue rows 已帶 per-venue proof_state / blockers / operator_next_action / verify_next，讓 Dashboard / Execution / Lab 直接顯示實單證據缺口；這會讓 operator-facing surfaces 與 machine-readable artifacts 保持同輪收斂。

### D｜決策行動
- **Owner**：即時執行治理 lane
- **Action**：維持熔斷優先真相，並把 q15 current-live bucket support truth 與 deployment closure 邊界持續顯示清楚；下一步沿 recent pathological slice 與解除條件繼續追根因；`/execution` 操作入口在同步中 / 已阻塞兩種狀態都必須 fail-closed；直接 API 買入 / 加倉也必須 409 暫停，減倉 / 賣出保留風險降低路徑。
- **Artifacts**：`ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md`、`data/live_predict_probe.json`、`data/live_decision_quality_drilldown.json`、`data/recent_drift_report.json`。
- **Verify**：browser `/`、browser `/execution`（同步中 / 已阻塞快捷操作 fail-closed）、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、`python scripts/recent_drift_report.py`、`python -m pytest tests/test_server_startup.py -k api_trade -q`。
- **If fail**：只要 docs / UI 再次隱藏熔斷優先真相、漏掉 q15 current-live bucket rows，或把 support closure 誤讀成 deployment closure，就把 heartbeat 升級回 current-state governance blocker。
