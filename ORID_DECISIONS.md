# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-24 21:55:53 CST_

---

## 心跳 #20260424_214420 ORID

### O｜客觀事實
- collect + diagnostics refresh 完成：`Raw=32181 / Features=23599 / Labels=64896`；歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`；`simulated_pyramid_win=57.00%`。
- current-live blocker：`deployment_blocker=under_minimum_exact_live_structure_bucket` / `streak=None` / `recent_window_wins=None/None` / `additional_recent_window_wins_needed=—`。
- q15 current-live bucket truth：`current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15` / `support=33/50` / `gap=17` / `support_route_verdict=exact_bucket_present_but_below_minimum`。
- support progress：`status=semantic_rebaseline_under_minimum` / `regression_basis=legacy_or_different_semantic_signature` / `legacy_supported_reference=199/50@20260423i`。
- latest recent-window diagnostics：`latest_window=100` / `win_rate=79.0%` / `dominant_regime=bull(100.0%)` / `avg_quality=+0.3441` / `avg_pnl=+0.0042` / `alerts=regime_concentration,regime_shift`。
- current blocking pathological pocket：`blocking_window=500` / `win_rate=53.2%` / `dominant_regime=bull(99.6%)` / `avg_quality=+0.1080` / `avg_pnl=+0.0003` / `alerts=regime_concentration,regime_shift`。
- leaderboard / governance：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`。
- source / venue blockers：`blocked_sparse_features=8`；fin_netflow=`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3649` / `archive_window_coverage_pct=0.0`；venue proof 仍缺 credential / order ack / fill lifecycle。
- 本輪產品化前進：current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth；`recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_non_current_live_scope` / `reference_scope=bull|CAUTION`。
- 本輪 operator-facing copy 前進：Dashboard、`/execution/status`、`/lab` 已顯示 `舊版已就緒參考 #20260423i · 199 筆 · 基準 舊語義或不同語義簽章 · 支持語義 v2 · 1440m · 金字塔勝率`，且 raw `simulated_pyramid_win` 不再洩漏到 UI。

### R｜感受直覺
- 這輪最需要防止的誤讀，是把 `33/50` 的 same-bucket support 或 `bull|CAUTION` 參考 patch 誤讀成已可部署；目前 live blocker 已切到 `under_minimum_exact_live_structure_bucket`。
- current live 已落在 `bull/BLOCK/BLOCK|bull_q15_bias50_overextended_block|q15`；如果 UI / docs 沒同步 latest artifacts，operator 很容易把 spillover pocket 或舊 bucket 當成現在的 runtime 真相。

### I｜意義洞察
1. **support truth ≠ deployment closure**：`support=33/50` 且 `support_route_verdict=exact_bucket_present_but_below_minimum` 只代表治理前進，還不能把 reference-only patch 升級成 runtime patch。
2. **真正主 blocker 已切到 q15 current-live bucket exact-support shortage**：recent pathological slice 仍是造成 `under_minimum_exact_live_structure_bucket` 的根因切片，不能再沿用 breaker-first 舊敘事。
3. **semantic rebaseline 需要 operator-facing 解釋**：`legacy_supported_reference=199/50` 是舊語義參考，不是同語義 regression；UI 必須把 support_identity / regression_basis / legacy reference 直接說清楚，否則 operator 會把舊 support 誤讀成 closure。
4. **docs overwrite sync 的角色是護欄，不是主 blocker**：current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth 讓 operator-facing surfaces 與 machine-readable artifacts 保持同輪收斂。

### D｜決策行動
- **Owner**：current-live runtime / governance lane
- **Action**：維持 current-live exact-support truth，並把 q15 current-live bucket support、semantic rebaseline reference-only 語義、reference-only patch 持續顯示清楚；下一步沿 recent pathological slice 與 exact-support accumulation 繼續追根因。
- **Artifacts**：`ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md`、`web/src/utils/runtimeCopy.ts`、`tests/test_frontend_decision_contract.py`、`data/live_predict_probe.json`、`data/live_decision_quality_drilldown.json`、`data/recent_drift_report.json`。
- **Verify**：`python -m pytest tests/test_frontend_decision_contract.py -q`、`cd web && npm run build`、browser `/`、browser `/execution/status`、browser `/lab` DOM：`舊版已就緒參考 #20260423i` / `支持語義 v2` / `金字塔勝率` present，raw `simulated_pyramid_win` absent。
- **If fail**：只要 docs / UI 再次把 `under_minimum_exact_live_structure_bucket` 誤寫成 breaker-first、漏掉 q15 current-live bucket rows，或把 reference-only patch 誤包裝成可部署 truth，就把 heartbeat 升級回 current-state governance blocker。
