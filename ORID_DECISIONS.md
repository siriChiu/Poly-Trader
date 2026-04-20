# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-21 01:53:40 CST_

---

## 心跳 #20260421-0147 ORID

### O｜客觀事實
- collect + diagnostics refresh 完成：`Raw=31277 / Features=22695 / Labels=63086`；`simulated_pyramid_win=57.22%`。
- current-live blocker：`deployment_blocker=unsupported_exact_live_structure_bucket` / `streak=None` / `recent_window_wins=None/None` / `additional_recent_window_wins_needed=—`。
- current live bucket truth：`current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q35` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_unsupported_block`。
- recent pathological slice：`window=500` / `win_rate=9.6%` / `dominant_regime=bull(87.0%)` / `avg_quality=-0.1829` / `avg_pnl=-0.0065` / `alerts=label_imbalance,regime_shift`。
- leaderboard / governance：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`。
- Strategy Lab productization：`Auto Leaderboard · ...` rows 現在帶 `source=auto_leaderboard / immutable=true`；operator rerun 另存 `Manual Copy · ...`；editor 提供 `strategy_type + model_name` controls 與 stale-result warning；`rule_baseline` 重掃維持 `type=rule_based`。
- source / venue blockers：`blocked_sparse_features=8`；fin_netflow=`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=2747` / `archive_window_coverage_pct=0.0`；venue proof 仍缺 credential / order ack / fill lifecycle。
- 本輪產品化前進：current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth；`recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_until_exact_support_ready` / `reference_scope=bull|CAUTION`。

### R｜感受直覺
- 這輪最需要防止的誤讀，是把 `0/50` 的 same-bucket support 或 `bull|CAUTION` 參考 patch 誤讀成已可部署；目前 live blocker 已切到 `unsupported_exact_live_structure_bucket`。
- current live 已落在 `chop/CAUTION/CAUTION|base_caution_regime_or_bias|q35`；如果 UI / docs 沒同步 latest artifacts，operator 很容易把 spillover pocket 或舊 bucket 當成現在的 runtime 真相。

### I｜意義洞察
1. **support accumulation ≠ deployment closure**：`support=0/50` 且 `support_route_verdict=exact_bucket_unsupported_block` 只代表治理前進，還不能把 reference patch 升級成 runtime patch。
2. **真正主 blocker 已切到 current live bucket exact-support shortage**：recent pathological slice 仍是造成 `unsupported_exact_live_structure_bucket` 的根因切片，不能再沿用 breaker-first 舊敘事。
3. **docs overwrite sync 的角色是護欄，不是主 blocker**：current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth 讓 operator-facing surfaces 與 machine-readable artifacts 保持同輪收斂。
4. **Strategy Lab rerun 必須區分 system refresh 與 operator rerun**：如果 system-generated auto rows 能被手動 rerun 覆蓋，排行榜就會失真；這輪把 `immutable auto row → Manual Copy rerun` 變成顯式 contract，才能守住 operator UX 與 cron refresh 的雙軌語義。

### D｜決策行動
- **Owner**：current-live runtime / governance lane
- **Action**：維持 current-live exact-support truth，並把 current live bucket support 與 recommended patch 持續顯示為 `reference_only`；同時守住 Strategy Lab 的 immutable auto-row / manual-copy rerun contract，避免 operator rerun 污染系統排行榜列。
- **Artifacts**：`ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md`、`data/live_predict_probe.json`、`data/live_decision_quality_drilldown.json`、`data/recent_drift_report.json`。
- **Verify**：browser `/`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、`python scripts/recent_drift_report.py`、`pytest tests/test_strategy_lab_manual_model_and_auto_contract.py tests/test_rescan_models_and_refresh_strategy_leaderboard.py -q`。
- **If fail**：只要 docs / UI 再次把 `unsupported_exact_live_structure_bucket` 誤寫成 breaker-first、漏掉 current live bucket rows、把 reference patch 誤包裝成可部署 truth，或讓 operator rerun 覆蓋 system-generated auto rows，就把 heartbeat 升級回 current-state governance blocker。
