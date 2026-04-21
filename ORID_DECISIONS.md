# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-21 12:24:42 CST_

---

## 心跳 #20260421-1224 ORID

### O｜客觀事實
- collect + diagnostics refresh 完成：`Raw=31356 / Features=22774 / Labels=63208`；`simulated_pyramid_win=57.21%`。
- current-live blocker：`deployment_blocker=exact_live_lane_toxic_sub_bucket_current_bucket` / `streak=None` / `recent_window_wins=None/None` / `additional_recent_window_wins_needed=—`。
- q15 current-live bucket truth：`current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=97/50` / `gap=0` / `support_route_verdict=exact_bucket_supported`。
- recent pathological slice：`window=500` / `win_rate=19.8%` / `dominant_regime=bull(76.8%)` / `avg_quality=-0.0868` / `avg_pnl=-0.0034` / `alerts=label_imbalance,regime_shift`。
- leaderboard / governance：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`。
- source / venue blockers：`blocked_sparse_features=8`；fin_netflow=`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=2826` / `archive_window_coverage_pct=0.0`；venue proof 仍缺 credential / order ack / fill lifecycle。
- 本輪產品化前進：current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth；`recommended_patch=None` / `status=None` / `reference_scope=—`。

### R｜感受直覺
- 這輪最需要防止的誤讀，是讓舊 blocker 敘事覆蓋最新 `exact_live_lane_toxic_sub_bucket_current_bucket` runtime truth。
- current live 已落在 `chop/CAUTION/CAUTION|base_caution_regime_or_bias|q15`；如果 UI / docs 沒同步 latest artifacts，operator 很容易把 spillover pocket 或舊 bucket 當成現在的 runtime 真相。

### I｜意義洞察
1. **support accumulation ≠ deployment closure**：`support=97/50` 且 `support_route_verdict=exact_bucket_supported` 只代表治理前進，還不能把 reference patch 升級成 runtime patch。
2. **真正主 blocker 以 latest runtime truth 為準**：目前 deployment blocker 是 `exact_live_lane_toxic_sub_bucket_current_bucket`，後續 root-cause 與 docs 必須跟著這條 lane 收斂。
3. **docs overwrite sync 的角色是護欄，不是主 blocker**：current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth 讓 operator-facing surfaces 與 machine-readable artifacts 保持同輪收斂。

### D｜決策行動
- **Owner**：current-live runtime / governance lane
- **Action**：維持 latest runtime blocker truth，並把 q15 current-live bucket support 與 recommended patch 持續顯示為 `reference_only`；下一步沿對應 runtime lane 繼續追根因。
- **Artifacts**：`ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md`、`data/live_predict_probe.json`、`data/live_decision_quality_drilldown.json`、`data/recent_drift_report.json`。
- **Verify**：browser `/`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、`python scripts/recent_drift_report.py`。
- **If fail**：只要 docs / UI 再次把 `exact_live_lane_toxic_sub_bucket_current_bucket` 蓋回舊 blocker 敘事、漏掉 q15 current-live bucket rows，或把 reference patch 誤包裝成可部署 truth，就把 heartbeat 升級回 current-state governance blocker。
