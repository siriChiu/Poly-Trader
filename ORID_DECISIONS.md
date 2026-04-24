# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-24 15:12:44 CST_

---

## 心跳 #fast ORID

### O｜客觀事實
- collect + diagnostics refresh 完成：`Raw=32157 / Features=23575 / Labels=64844`；歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`；`simulated_pyramid_win=56.98%`。
- current-live blocker：`deployment_blocker=under_minimum_exact_live_structure_bucket` / `streak=None` / `recent_window_wins=None/None` / `additional_recent_window_wins_needed=—`。
- q15 current-live bucket truth：`current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15` / `support=10/50` / `gap=40` / `support_route_verdict=exact_bucket_present_but_below_minimum`。
- latest recent-window diagnostics：`latest_window=100` / `win_rate=82.0%` / `dominant_regime=bull(100.0%)` / `avg_quality=+0.3494` / `avg_pnl=+0.0048` / `alerts=label_imbalance,regime_concentration,regime_shift`。
- leaderboard / governance：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`。
- source / venue blockers：`blocked_sparse_features=8`；fin_netflow=`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3625` / `archive_window_coverage_pct=0.0`；venue proof 仍缺 credential / order ack / fill lifecycle。
- 本輪產品化前進：current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth；`recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_non_current_live_scope` / `reference_scope=bull|CAUTION`。
- UI productization patch：Dashboard / Strategy Lab current-bucket 卡片已移除 `q15 floor-cross`、`NW Envelope`、`NW Env`、`volume_exhaustion` 內部語彙，改用 `Q15 跨門檻合法性`、`4H NW 包絡位置`、`NW包絡`、`量能衰竭`；contract tests / build / browser DOM counts 已驗證。

### R｜感受直覺
- 這輪最需要防止的誤讀，是把 `10/50` 的 same-bucket support 或 `bull|CAUTION` 參考 patch 誤讀成已可部署；目前 live blocker 已切到 `under_minimum_exact_live_structure_bucket`。
- current live 已落在 `bull/BLOCK/BLOCK|bull_q15_bias50_overextended_block|q15`；如果 UI / docs 沒同步 latest artifacts，operator 很容易把 spillover pocket 或舊 bucket 當成現在的 runtime 真相。

### I｜意義洞察
1. **support truth ≠ deployment closure**：`support=10/50` 且 `support_route_verdict=exact_bucket_present_but_below_minimum` 只代表治理前進，還不能把 reference-only patch 升級成 runtime patch。
2. **真正主 blocker 已切到 q15 current-live bucket exact-support shortage**：recent pathological slice 仍是造成 `under_minimum_exact_live_structure_bucket` 的根因切片，不能再沿用 breaker-first 舊敘事。
3. **operator copy is part of blocker truth**：q15 current-bucket 卡片若繼續暴露 `floor-cross` / raw feature ids，operator 會把治理診斷誤讀成工程內部狀態；本輪已把這條 P0-facing copy 納入 contract tests 與 browser DOM 驗證。

### D｜決策行動
- **Owner**：current-live runtime / governance lane
- **Action**：維持 current-live exact-support truth，並把 q15 current-live bucket support、reference-only patch 與 q15 跨門檻 / 特徵名稱 copy 持續顯示清楚；下一步沿 recent pathological slice 與 exact-support accumulation 繼續追根因。
- **Artifacts**：`ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md`、`data/live_predict_probe.json`、`data/live_decision_quality_drilldown.json`、`data/recent_drift_report.json`。
- **Verify**：browser `/`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、`python scripts/recent_drift_report.py`。
- **If fail**：只要 docs / UI 再次把 `under_minimum_exact_live_structure_bucket` 誤寫成 breaker-first、漏掉 q15 current-live bucket rows，或把 reference-only patch 誤包裝成可部署 truth，就把 heartbeat 升級回 current-state governance blocker。
