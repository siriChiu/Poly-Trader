# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-22 23:56:31 CST_

---

## 心跳 #20260422al ORID

### O｜客觀事實
- collect + diagnostics refresh 完成：`Raw=31558 / Features=22976 / Labels=63608`；`simulated_pyramid_win=57.37%`。
- current-live blocker：`deployment_blocker=unsupported_exact_live_structure_bucket` / `streak=None` / `recent_window_wins=None/None` / `additional_recent_window_wins_needed=—`。
- current live bucket truth：`current_live_structure_bucket=BLOCK|bull_high_bias200_overheat_block|q65` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_unsupported_block`。
- latest recent-window diagnostics：`latest_window=100` / `win_rate=94.0%` / `dominant_regime=bull(92.0%)` / `avg_quality=+0.5258` / `avg_pnl=+0.0163` / `alerts=label_imbalance,regime_concentration,regime_shift`。
- current blocking pathological pocket：`blocking_window=1000` / `win_rate=39.4%` / `dominant_regime=bull(81.3%)` / `avg_quality=+0.0814` / `avg_pnl=+0.0009` / `alerts=regime_shift`。
- leaderboard / governance：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`。
- Strategy Lab saved strategy detail：`/api/strategies/{name}` 的 `chart_context / available / effective` 已回到完整兩年回測 window，不再被 first→last trade window 裁短。
- source / venue blockers：`blocked_sparse_features=8`；fin_netflow=`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3028` / `archive_window_coverage_pct=0.0`；venue proof 仍缺 credential / order ack / fill lifecycle。
- 本輪產品化前進：current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth；`recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_non_current_live_scope` / `reference_scope=bull|CAUTION`。

### R｜感受直覺
- 這輪最需要防止的誤讀，是把 `0/50` 的 same-bucket support 或 `bull|CAUTION` 參考 patch 誤讀成已可部署；目前 live blocker 已切到 `unsupported_exact_live_structure_bucket`。
- current live 已落在 `bull/BLOCK/BLOCK|bull_high_bias200_overheat_block|q65`；如果 UI / docs 沒同步 latest artifacts，operator 很容易把 spillover pocket 或舊 bucket 當成現在的 runtime 真相。
- Strategy Lab 若把 chart payload 裁成交易視窗，operator 會把真正兩年回測誤讀成只有約一年可用歷史，直接破壞 recent-two-year product contract。

### I｜意義洞察
1. **support truth ≠ deployment closure**：`support=0/50` 且 `support_route_verdict=exact_bucket_unsupported_block` 只代表治理前進，還不能把 reference-only patch 升級成 runtime patch。
2. **Strategy detail 的 window contract 也是產品真相**：如果 `chart_context` 被 trade window 偷偷改寫，排行榜/策略詳情即使數值正確，operator 仍會被錯誤視窗誤導。
3. **真正主 blocker 已切到 current live bucket exact-support shortage**：recent pathological slice 仍是造成 `unsupported_exact_live_structure_bucket` 的根因切片，不能再沿用 breaker-first 舊敘事。
4. **docs overwrite sync 的角色是護欄，不是主 blocker**：current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth 讓 operator-facing surfaces 與 machine-readable artifacts 保持同輪收斂。

### D｜決策行動
- **Owner**：current-live runtime / governance lane
- **Action**：維持 current-live exact-support truth，並守住 Strategy Lab 兩年回測 window contract；下一步沿 recent pathological slice 與 exact-support accumulation 繼續追根因。
- **Artifacts**：`ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md`、`data/live_predict_probe.json`、`data/live_decision_quality_drilldown.json`、`data/recent_drift_report.json`。
- **Verify**：browser `/`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、`python scripts/recent_drift_report.py`。
- **If fail**：只要 docs / UI 再次把 `unsupported_exact_live_structure_bucket` 誤寫成 breaker-first、漏掉 current live bucket rows，或把 reference-only patch 誤包裝成可部署 truth，就把 heartbeat 升級回 current-state governance blocker。
