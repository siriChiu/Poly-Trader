# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-25 02:42:59 CST_

---

## 心跳 #20260425_022713 ORID

### O｜客觀事實
- collect + diagnostics refresh 完成：`Raw=32192 / Features=23610 / Labels=64928`；歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`；`simulated_pyramid_win=56.98%`。
- current-live blocker：`deployment_blocker=decision_quality_below_trade_floor` / `streak=None` / `recent_window_wins=None/None` / `additional_recent_window_wins_needed=—`。
- q15 current-live bucket truth：`current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=123/50` / `gap=0` / `support_route_verdict=exact_bucket_supported`。
- support progress：`status=exact_supported` / `regression_basis=current_identity` / `legacy_supported_reference=121/50@20260424a`。
- latest recent-window diagnostics：`latest_window=500` / `win_rate=53.4%` / `dominant_regime=bull(99.4%)` / `avg_quality=+0.1145` / `avg_pnl=+0.0005` / `alerts=regime_concentration,regime_shift`。
- leaderboard / governance：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`。
- source / venue blockers：`blocked_sparse_features=8`；fin_netflow=`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3659` / `archive_window_coverage_pct=0.0`；venue proof 仍缺 credential / order ack / fill lifecycle。
- 本輪產品化前進：current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth；`recommended_patch=—` / `status=—` / `reference_scope=—`。

### R｜感受直覺
- 這輪最需要防止的誤讀，是讓舊 blocker 敘事覆蓋最新 `decision_quality_below_trade_floor` runtime truth。
- current live 已落在 `chop/CAUTION/CAUTION|base_caution_regime_or_bias|q15`；如果 UI / docs 沒同步 latest artifacts，operator 很容易把 spillover pocket 或舊 bucket 當成現在的 runtime 真相。

### I｜意義洞察
1. **support truth ≠ deployment closure**：`support=123/50` 且 `support_route_verdict=exact_bucket_supported` 只代表 same-bucket support 狀態，真正 deployment blocker 仍由 latest runtime truth 決定。
2. **真正主 blocker 以 latest runtime truth 為準**：目前 deployment blocker 是 `decision_quality_below_trade_floor`，後續 root-cause 與 docs 必須跟著這條 lane 收斂。
3. **docs overwrite sync 的角色是護欄，不是主 blocker**：current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth 讓 operator-facing surfaces 與 machine-readable artifacts 保持同輪收斂。

### D｜決策行動
- **Owner**：current-live runtime / governance lane
- **Action**：維持 latest runtime blocker truth，並把 q15 current-live bucket support truth 與 deployment closure 邊界持續顯示清楚；下一步沿對應 runtime lane 繼續追根因。
- **Artifacts**：`ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md`、`data/live_predict_probe.json`、`data/live_decision_quality_drilldown.json`、`data/recent_drift_report.json`。
- **Verify**：browser `/`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、`python scripts/recent_drift_report.py`。
- **If fail**：只要 docs / UI 再次把 `decision_quality_below_trade_floor` 蓋回舊 blocker 敘事、漏掉 q15 current-live bucket rows，或把 support closure 誤讀成 deployment closure，就把 heartbeat 升級回 current-state governance blocker。
