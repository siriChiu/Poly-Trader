# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-24 21:24:40 CST_

---

## 心跳 #20260424_2111 ORID

### O｜客觀事實
- collect + diagnostics refresh 完成：`Raw=32179 / Features=23597 / Labels=64891`；歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`；`simulated_pyramid_win=57.00%`。
- current-live blocker：`deployment_blocker=under_minimum_exact_live_structure_bucket` / `streak=None` / `recent_window_wins=None/None` / `additional_recent_window_wins_needed=—`。
- current live bucket truth：`current_live_structure_bucket=BLOCK|bull_high_bias200_overheat_block|q35` / `support=5/50` / `gap=45` / `support_route_verdict=exact_bucket_present_but_below_minimum`。
- latest recent-window diagnostics：`latest_window=100` / `win_rate=79.0%` / `dominant_regime=bull(100.0%)` / `avg_quality=+0.3416` / `avg_pnl=+0.0041` / `alerts=regime_concentration,regime_shift`。
- current blocking pathological pocket：`blocking_window=500` / `win_rate=52.6%` / `dominant_regime=bull(99.6%)` / `avg_quality=+0.1030` / `avg_pnl=+0.0001` / `alerts=regime_concentration,regime_shift`。
- leaderboard / governance：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`。
- source / venue blockers：`blocked_sparse_features=8`；fin_netflow=`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3647` / `archive_window_coverage_pct=0.0`；venue proof 仍缺 credential / order ack / fill lifecycle。
- q35 scaling audit 已指出目前不是單點 bias50 closure： `overall_verdict=bias50_formula_may_be_too_harsh` / `redesign_verdict=base_stack_redesign_discriminative_reweight_still_below_floor` / `runtime_gap_to_floor=0.2387` / `redesign_entry_quality=0.2546` / `redesign_allowed_layers=0` / `positive_discriminative_gap=True` / `execution_blocked_after_floor_cross=False`。
- 本輪產品化前進：current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth；`recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_non_current_live_scope` / `reference_scope=bull|CAUTION`。
- 本輪 operator-facing q35 current-bucket 根因 copy 已修正：Dashboard、`/execution/status`、`/lab` 對 q35 current bucket 顯示 `交易門檻缺口 0.2387 · q35 公式 / 重設仍只屬治理參考`，不再顯示 q15/q35 邊界差距。

### R｜感受直覺
- 這輪最需要防止的誤讀，是把 `5/50` 的 same-bucket support 或 `bull|CAUTION` 參考 patch 誤讀成已可部署；目前 live blocker 已切到 `under_minimum_exact_live_structure_bucket`。
- current live 已落在 `bull/BLOCK/BLOCK|bull_high_bias200_overheat_block|q35`；如果 UI / docs 沒同步 latest artifacts，operator 很容易把 spillover pocket 或舊 bucket 當成現在的 runtime 真相。

### I｜意義洞察
1. **support truth ≠ deployment closure**：`support=5/50` 且 `support_route_verdict=exact_bucket_present_but_below_minimum` 只代表治理前進，還不能把 reference-only patch 升級成 runtime patch。
2. **真正主 blocker 已切到 current live bucket exact-support shortage**：recent pathological slice 仍是造成 `under_minimum_exact_live_structure_bucket` 的根因切片，不能再沿用 breaker-first 舊敘事。
3. **UI copy 必須跟 current bucket 語義一致**：current row 已在 q35 時，operator card 要顯示 trade-floor gap；只有 q15 / boundary replay 才可顯示「距 q35 還差」。
4. **docs overwrite sync 的角色是護欄，不是主 blocker**：current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth 讓 operator-facing surfaces 與 machine-readable artifacts 保持同輪收斂。

### D｜決策行動
- **Owner**：current-live runtime / governance lane
- **Action**：維持 current-live exact-support truth，並把 current live bucket support、reference-only patch、q35 trade-floor gap 持續顯示清楚；下一步沿 recent pathological slice 與 exact-support accumulation 繼續追根因。
- **Artifacts**：`ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md`、`web/src/components/ConfidenceIndicator.tsx`、`web/src/pages/ExecutionStatus.tsx`、`web/src/pages/StrategyLab.tsx`、`data/live_predict_probe.json`、`data/live_decision_quality_drilldown.json`、`data/recent_drift_report.json`。
- **Verify**：`PYTHONPATH=. python -m pytest tests/test_frontend_decision_contract.py -q`、`cd web && npm run build`、browser `/`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、`python scripts/recent_drift_report.py`。
- **If fail**：只要 docs / UI 再次把 q35 current bucket 顯示成 q15/q35 邊界問題、把 `under_minimum_exact_live_structure_bucket` 誤寫成 breaker-first、漏掉 current live bucket rows，或把 reference-only patch 誤包裝成可部署 truth，就把 heartbeat 升級回 current-state governance blocker。
