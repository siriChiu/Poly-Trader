# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-22 09:28:47 CST_

---

## 心跳 #fast ORID

### O｜客觀事實
- collect + diagnostics refresh 完成：`Raw=31462 / Features=22880 / Labels=63441`；`simulated_pyramid_win=57.23%`。
- current-live blocker：`deployment_blocker=decision_quality_below_trade_floor` / `streak=None` / `recent_window_wins=None/None` / `additional_recent_window_wins_needed=—`。
- current live bucket truth：`current_live_structure_bucket=CAUTION|structure_quality_caution|q35` / `support=74/50` / `gap=0` / `support_route_verdict=exact_bucket_supported`。
- latest recent-window diagnostics：`latest_window=1000` / `win_rate=38.0%` / `dominant_regime=bull(82.0%)` / `avg_quality=+0.0663` / `avg_pnl=+0.0001` / `alerts=regime_shift`。
- leaderboard / governance：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`。
- source / venue blockers：`blocked_sparse_features=8`；fin_netflow=`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=2932` / `archive_window_coverage_pct=0.0`；venue proof 仍缺 credential / order ack / fill lifecycle。
- 本輪產品化前進：current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth；`recommended_patch=core_plus_macro_plus_all_4h` / `status=deployable_patch_candidate` / `reference_scope=bull|CAUTION`。

### R｜感受直覺
- 這輪最需要防止的誤讀，是讓舊 blocker 敘事覆蓋最新 `decision_quality_below_trade_floor` runtime truth。
- current live 已落在 `bull/CAUTION/CAUTION|structure_quality_caution|q35`；如果 UI / docs 沒同步 latest artifacts，operator 很容易把 spillover pocket 或舊 bucket 當成現在的 runtime 真相。

### I｜意義洞察
1. **support truth ≠ deployment closure**：`support=74/50` 且 `support_route_verdict=exact_bucket_supported` 只代表 same-bucket support / patch 治理真相，不能跳過 runtime verify。
2. **真正主 blocker 以 latest runtime truth 為準**：目前 deployment blocker 是 `decision_quality_below_trade_floor`，後續 root-cause 與 docs 必須跟著這條 lane 收斂。
3. **docs overwrite sync 的角色是護欄，不是主 blocker**：current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth 讓 operator-facing surfaces 與 machine-readable artifacts 保持同輪收斂。

### D｜決策行動
- **Owner**：current-live runtime / governance lane
- **Action**：維持 latest runtime blocker truth，並把 current live bucket support 與 recommended patch 持續顯示清楚；下一步沿對應 runtime lane 繼續追根因。
- **Artifacts**：`ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md`、`data/live_predict_probe.json`、`data/live_decision_quality_drilldown.json`、`data/recent_drift_report.json`。
- **Verify**：browser `/`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、`python scripts/recent_drift_report.py`。
- **If fail**：只要 docs / UI 再次把 `decision_quality_below_trade_floor` 蓋回舊 blocker 敘事、漏掉 current live bucket rows，或把 recommended patch 誤包裝成可部署 truth，就把 heartbeat 升級回 current-state governance blocker。
