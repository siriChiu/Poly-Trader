# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-22 20:57:34 CST_

---

## 心跳 #fast ORID

### O｜客觀事實
- collect + diagnostics refresh 完成：`Raw=31541 / Features=22959 / Labels=63568`；`simulated_pyramid_win=57.33%`。
- current-live blocker：`deployment_blocker=unsupported_exact_live_structure_bucket` / `streak=None` / `recent_window_wins=None/None` / `additional_recent_window_wins_needed=—`。
- current live bucket truth：`current_live_structure_bucket=BLOCK|bull_high_bias200_overheat_block|q35` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_unsupported_block`。
- latest recent-window diagnostics：`latest_window=100` / `win_rate=81.0%` / `dominant_regime=bull(92.0%)` / `avg_quality=+0.4136` / `avg_pnl=+0.0123` / `alerts=label_imbalance,regime_concentration,regime_shift`。
- current blocking pathological pocket：`blocking_window=1000` / `win_rate=39.4%` / `dominant_regime=bull(81.3%)` / `avg_quality=+0.0814` / `avg_pnl=+0.0009` / `alerts=regime_shift`。
- leaderboard / governance：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`。
- leaderboard background refresh 已 bounded：`refresh_model_scope=production_refresh_shortlist` / `background_refresh_surface=2 deployment × 2 feature profiles` / `GET /api/models/leaderboard` 200 in `~0.89s`。
- source / venue blockers：`blocked_sparse_features=8`；fin_netflow=`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3011` / `archive_window_coverage_pct=0.0`；venue proof 仍缺 credential / order ack / fill lifecycle。
- q35 scaling audit 已指出目前不是單點 bias50 closure：`overall_verdict=bias50_formula_may_be_too_harsh` / `redesign_verdict=base_stack_redesign_candidate_grid_empty` / `remaining_gap_to_floor=0.1238`。
- 本輪產品化前進：current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth；`recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_non_current_live_scope` / `reference_scope=bull|CAUTION`。

### R｜感受直覺
- 這輪最需要防止的誤讀，是把 `0/50` 的 same-bucket support 或 `bull|CAUTION` 參考 patch 誤讀成已可部署；目前 live blocker 已切到 `unsupported_exact_live_structure_bucket`。
- current live 已落在 `bull/BLOCK/BLOCK|bull_high_bias200_overheat_block|q35`；如果 UI / docs 沒同步 latest artifacts，operator 很容易把 spillover pocket 或舊 bucket 當成現在的 runtime 真相。

### I｜意義洞察
1. **support truth ≠ deployment closure**：`support=0/50` 且 `support_route_verdict=exact_bucket_unsupported_block` 只代表治理前進，還不能把 reference-only patch 升級成 runtime patch。
2. **真正主 blocker 已切到 current live bucket exact-support shortage**：recent pathological slice 仍是造成 `unsupported_exact_live_structure_bucket` 的根因切片，不能再沿用 breaker-first 舊敘事。
3. **docs overwrite sync 是護欄，leaderboard bounded refresh 是 product latency guardrail**：current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth，而 `/api/models/leaderboard` 背景刷新已收斂成 2×2 shortlist，避免 Strategy Lab 被 full fan-out refresh 拖慢。

### D｜決策行動
- **Owner**：current-live runtime / governance lane
- **Action**：維持 current-live exact-support truth，並把 current live bucket support 與 reference-only patch 持續顯示清楚；同時守住 leaderboard background refresh 的 2×2 bounded shortlist，避免 Strategy Lab 背景刷新回退成 full candidate fan-out。
- **Artifacts**：`ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md`、`data/live_predict_probe.json`、`data/live_decision_quality_drilldown.json`、`data/recent_drift_report.json`。
- **Verify**：browser `/`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、`python scripts/recent_drift_report.py`。
- **If fail**：只要 docs / UI 再次把 `unsupported_exact_live_structure_bucket` 誤寫成 breaker-first、漏掉 current live bucket rows，或把 reference-only patch 誤包裝成可部署 truth，就把 heartbeat 升級回 current-state governance blocker。
