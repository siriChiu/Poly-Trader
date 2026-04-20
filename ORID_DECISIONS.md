# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-20 19:17:47 CST_

---

## 心跳 #fast ORID

### O｜客觀事實
- collect + diagnostics refresh 完成：`Raw=31254 / Features=22672 / Labels=63024`；`simulated_pyramid_win=57.16%`。
- current-live blocker：`deployment_blocker=circuit_breaker_active` / `streak=0` / `recent_window_wins=14/50` / `additional_recent_window_wins_needed=1`。
- current live bucket truth：`current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q35` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`。
- recent pathological slice：`window=500` / `win_rate=3.6%` / `dominant_regime=bull(90.6%)` / `avg_quality=-0.2266` / `avg_pnl=-0.0078` / `alerts=label_imbalance,regime_concentration,regime_shift`。
- 本輪產品化前進：Strategy Lab legacy saved strategy 的 `backtest_range` 缺口已修復；`/api/strategies/*` 與 `/lab` 不再把實際區間顯示成 `— → —`。

### R｜感受直覺
- 這輪最直接的 operator 痛點不是模型數字，而是 Strategy Lab 在已有回測結果時仍顯示空白區間，讓人誤以為最近兩年 contract 或回測範圍已壞掉。
- breaker 仍是唯一 current-live blocker；range 修復只能算產品面修補，不能拿來掩蓋 canonical runtime blocker。

### I｜意義洞察
1. **產品 surface 的空白欄位也是治理 bug**：回測實際區間掉成 `— → —`，會讓 leaderboard recent-window contract 看起來像假資料或未載入，即使底層 definition / chart_context 其實都有範圍。
2. **legacy strategy payload 需要讀時修復**：只靠新存檔格式不夠，既有 saved strategies 必須在 load path 上補回 `requested/effective/available`，否則 UI 再漂亮也只能讀到空值。
3. **breaker-first truth 與 Strategy Lab UX 可以並行推進**：本輪沒有碰主 blocker 語義，但至少把 `/lab` 的可讀性與 API contract 往 production-quality 推進一格。

### D｜決策行動
- **Owner**：Strategy Lab / leaderboard product surface
- **Action**：保留 breaker-first 主線，同時把 Strategy Lab actual-range contract 視為已完成的 P1 子修復；下一步繼續維持 recent-two-year / actual-range / leaderboard payload 一致。
- **Artifacts**：`backtesting/strategy_lab.py`、`web/src/pages/StrategyLab.tsx`、`ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md`。
- **Verify**：browser `/lab`、`python scripts/hb_strategy_range_probe.py`、`pytest tests/test_strategy_lab.py tests/test_strategy_lab_date_range_contract.py tests/test_frontend_decision_contract.py tests/test_model_leaderboard.py tests/test_server_startup.py -q`、`cd web && npm run build`。
- **If fail**：只要 `/api/strategies/*` 再失去有效 `backtest_range`、`/lab` 再掉回 `— → —`，或 range contract 與 leaderboard 最近兩年政策分裂，就把它升級回 Strategy Lab product contract blocker。
