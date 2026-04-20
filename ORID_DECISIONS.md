# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-20 16:29:19 CST_

---

## 心跳 #20260420-1626 ORID

### O｜客觀事實
- collect + diagnostics refresh 完成：`Raw=31241 / Features=22659 / Labels=62994`；`simulated_pyramid_win=57.14%`。
- current-live blocker：`deployment_blocker=circuit_breaker_active` / `streak=8` / `recent_window_wins=5/50` / `additional_recent_window_wins_needed=10`。
- q15 current-live bucket truth：`current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=32/50` / `gap=18` / `support_route_verdict=exact_bucket_present_but_below_minimum`。
- recent pathological slice：`window=500` / `win_rate=1.2%` / `dominant_regime=bull(93.6%)` / `avg_quality=-0.2433` / `avg_pnl=-0.0083` / `alerts=label_imbalance,regime_concentration,regime_shift`。
- leaderboard / governance：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`。
- source / venue blockers：`blocked_sparse_features=8`；fin_netflow=`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=2712` / `archive_window_coverage_pct=0.0`；venue proof 仍缺 credential / order ack / fill lifecycle。
- 本輪產品化前進：current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth；`recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_until_exact_support_ready` / `reference_scope=bull|CAUTION`。
- Dashboard fresh-load WebSocket bootstrap 假警報已清除：首頁 browser fresh load 不再出現 `closed before the connection is established`，且 live feed 仍能回到 `即時連線`。

### R｜感受直覺
- 這輪最需要防止的誤讀，是把 `32/50` 的 same-bucket support 或 `bull|CAUTION` 參考 patch 誤讀成已可部署；breaker 仍是唯一 current-live blocker。
- current live 已落在 `chop/CAUTION/CAUTION|base_caution_regime_or_bias|q15`；如果 UI / docs 沒同步 latest artifacts，operator 很容易把 spillover pocket 或舊 bucket 當成現在的 runtime 真相。

### I｜意義洞察
1. **support accumulation ≠ deployment closure**：`support=32/50` 且 `support_route_verdict=exact_bucket_present_but_below_minimum` 只代表治理前進，還不能把 reference patch 升級成 runtime patch。
2. **真正主 blocker 仍是 breaker + recent pathological slice**：目前該追的是 release math 與 recent canonical 250-row pathology，不是把 q15/q35 support 或 venue 話題誤升級成唯一根因。
3. **docs overwrite sync 的角色是護欄，不是主 blocker**：current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth 讓 operator-facing surfaces 與 machine-readable artifacts 保持同輪收斂。

### D｜決策行動
- **Owner**：current-live runtime / governance lane
- **Action**：維持 breaker-first truth，並把 q15 current-live bucket support 與 recommended patch 持續顯示為 `reference_only`；下一步沿 recent pathological slice 與 release math 繼續追根因。
- **Artifacts**：`ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md`、`data/live_predict_probe.json`、`data/live_decision_quality_drilldown.json`、`data/recent_drift_report.json`。
- **Verify**：browser `/`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、`python scripts/recent_drift_report.py`。
- **If fail**：只要 docs / UI 再次隱藏 breaker-first truth、漏掉 support rows，或把 reference patch 誤包裝成可部署 truth，就把 heartbeat 升級回 current-state governance blocker。
