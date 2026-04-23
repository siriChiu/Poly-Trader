# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-24 03:28:21 CST_

---

## 心跳 #20260424d ORID

### O｜客觀事實
- collect + diagnostics refresh 完成：`Raw=32089 / Features=23507 / Labels=64399`；`2y_backfill_ok=True`；`simulated_pyramid_win=56.99%`。
- current-live blocker：`deployment_blocker=circuit_breaker_active` / `recent_window_wins=14/50` / `additional_recent_window_wins_needed=1` / `streak=0`。
- q15 current-live bucket truth：`current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_proxy_reference_only`。
- latest recent-window diagnostics：`latest_window=100` / `win_rate=36.0%` / `dominant_regime=bull(99.0%)` / `avg_quality=-0.0395` / `avg_pnl=-0.0025` / `alerts=regime_concentration,regime_shift`。
- Strategy Lab 產品化 patch 已落地：`/api/strategies/{name}` detail 現在 bounded 為 `equity_curve<=1000` / `score_series<=300`，但保留完整兩年 `chart_context.start/end`；瀏覽器 cache 也同步 bounded（`polytrader.strategylab.cache.v1 = 1000 / 300`）；實際 detail payload probe=`324162 bytes`。
- leaderboard / governance：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active`。
- source / venue blockers：`blocked_sparse_features=8`；fin_netflow=`source_auth_blocked` / `auth_missing`；venue proof 仍缺 `credential / order ack / fill lifecycle`。

### R｜感受直覺
- 這輪最危險的誤讀，仍是把 `0/50` support 或 `bull|CAUTION` 參考 patch 誤讀成已可部署；breaker 仍是唯一 current-live blocker。
- 另一個實際產品風險不是模型，而是 Strategy Lab 工作區把長期序列原封不動塞進 API/detail/cache，造成 workspace 越跑越重；這輪已先把 payload/caching 收斂回可運營範圍。

### I｜意義洞察
1. **support truth ≠ deployment closure**：`support=0/50` 且 `support_route_verdict=exact_bucket_missing_proxy_reference_only` 只代表治理參考，不能把 reference-only patch 升級成 runtime patch。
2. **真正主 blocker 仍是 breaker + recent pathological slice**：目前最該追的是 release math 與 recent canonical pathology，而不是把 q15/q35 support 或 venue 話題誤升級成唯一根因。
3. **Strategy Lab 也有 productization budget**：保留兩年 chart context 很重要，但若 detail payload / session cache 不設上限，排行榜與工作區再正確也會退化成操作不穩、載入過重的假產品化。

### D｜決策行動
- **Owner**：current-live runtime / governance / Strategy Lab workspace lane
- **Action**：維持 breaker-first truth；繼續沿 recent pathological slice 追根因；同時守住 Strategy Lab bounded payload/cache，不讓 leaderboard detail 或 cache 再回到多 MB 膨脹。
- **Artifacts**：`ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md`、`data/live_predict_probe.json`、`data/live_decision_quality_drilldown.json`、`data/recent_drift_report.json`
- **Verify**：browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、`python scripts/recent_drift_report.py`、`pytest tests/test_strategy_lab.py tests/test_strategy_lab_manual_model_and_auto_contract.py tests/test_frontend_decision_contract.py -q`、`cd web && npm run build`
- **If fail**：只要 docs / UI 再次隱藏 breaker-first truth、漏掉 q15 current-live bucket rows，或 Strategy Lab detail / cache 回退成不受控膨脹，就把 heartbeat 升級回 current-state productization blocker。
