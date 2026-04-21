# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-21 20:05:35 CST_

---

## 心跳 #fast ORID

### O｜客觀事實
- collect + diagnostics refresh 完成：`Raw=31387 / Features=22805 / Labels=63289`；`simulated_pyramid_win=57.28%`。
- current-live blocker：`deployment_blocker=under_minimum_exact_live_structure_bucket` / `streak=None` / `recent_window_wins=None/None` / `additional_recent_window_wins_needed=—`。
- current live bucket truth：`current_live_structure_bucket=CAUTION|structure_quality_caution|q35` / `support=12/50` / `gap=38` / `support_route_verdict=exact_bucket_present_but_below_minimum`。
- latest recent-window diagnostics：`latest_window=100` / `win_rate=100.0%` / `dominant_regime=chop(100.0%)` / `avg_quality=+0.6627` / `avg_pnl=+0.0198` / `alerts=constant_target,regime_concentration,regime_shift`。
- current blocking pathological pocket：`blocking_window=500` / `win_rate=28.2%` / `dominant_regime=bull(68.4%)` / `avg_quality=-0.0043` / `avg_pnl=-0.0007` / `alerts=regime_shift`。
- leaderboard / governance：`leaderboard_count=6` / `selected_feature_profile=core_plus_macro` / `support_aware_profile=core_plus_macro` / `governance_contract=dual_role_governance_active` / `current_closure=dual_role_split_but_aligned`。
- Strategy Lab workspace lane 對齊：`/api/strategies/leaderboard`、`/api/strategies/{name}`、`/api/strategy_data_range` 改為 same-origin shell 優先；在 `poly_trader.active_api_base=http://127.0.0.1:8001` 仍可維持 `/lab` 與目前 app shell 的 strategy/detail/date-range 一致。
- source / venue blockers：`blocked_sparse_features=8`；fin_netflow=`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=2857` / `archive_window_coverage_pct=0.0`；venue proof 仍缺 credential / order ack / fill lifecycle。
- 本輪產品化前進：current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth；`recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_until_exact_support_ready` / `reference_scope=bull|CAUTION`。

### R｜感受直覺
- 這輪最需要防止的誤讀，是把 `12/50` 的 same-bucket support 或 `bull|CAUTION` 參考 patch 誤讀成已可部署；目前 live blocker 已切到 `under_minimum_exact_live_structure_bucket`。
- current live 已落在 `bull/CAUTION/CAUTION|structure_quality_caution|q35`；如果 UI / docs 沒同步 latest artifacts，operator 很容易把 spillover pocket 或舊 bucket 當成現在的 runtime 真相。

### I｜意義洞察
1. **support accumulation ≠ deployment closure**：`support=12/50` 且 `support_route_verdict=exact_bucket_present_but_below_minimum` 只代表治理前進，還不能把 reference patch 升級成 runtime patch。
2. **真正主 blocker 已切到 current live bucket exact-support shortage**：recent pathological slice 仍是造成 `under_minimum_exact_live_structure_bucket` 的根因切片，不能再沿用 breaker-first 舊敘事。
3. **docs overwrite sync 的角色是護欄，不是主 blocker**：current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth 讓 operator-facing surfaces 與 machine-readable artifacts 保持同輪收斂。
4. **Strategy Lab 不能只靠 direct backend failover 判斷 workspace truth**：當同時存在 8000/8001 lane 時，策略排行榜 / 明細 / data-range 必須先跟當前 app shell 對齊，否則 `/lab` 會用較舊 lane 的資料把兩年區間與工作區狀態帶回 split-brain。

### D｜決策行動
- **Owner**：current-live runtime / governance lane
- **Action**：維持 current-live exact-support truth，並把 current live bucket support 與 recommended patch 持續顯示為 `reference_only`；同時把 Strategy Lab 的 strategy workspace 讀路徑鎖回 same-origin shell 優先，避免 `/lab` 對兩年區間與策略明細讀到 stale backend lane；下一步沿 recent pathological slice 與 exact-support accumulation 繼續追根因。
- **Artifacts**：`ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md`、`data/live_predict_probe.json`、`data/live_decision_quality_drilldown.json`、`data/recent_drift_report.json`。
- **Verify**：browser `/`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、`python scripts/recent_drift_report.py`。
- **If fail**：只要 docs / UI 再次把 `under_minimum_exact_live_structure_bucket` 誤寫成 breaker-first、漏掉 current live bucket rows，或把 reference patch 誤包裝成可部署 truth，就把 heartbeat 升級回 current-state governance blocker。
