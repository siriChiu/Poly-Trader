# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-21 04:51:30 CST_

---

## 心跳 #20260421-0446 ORID

### O｜客觀事實
- fast heartbeat 已完成 collect + diagnostics refresh：`Raw=31303 / Features=22721 / Labels=63106`；`simulated_pyramid_win=57.23%`。
- current-live blocker 仍是 `deployment_blocker=under_minimum_exact_live_structure_bucket`；`current_live_structure_bucket=CAUTION|structure_quality_caution|q35` / `support=12/50` / `gap=38` / `support_route_verdict=exact_bucket_present_but_below_minimum`。
- recent pathological slice 仍成立：`window=500` / `win_rate=11.6%` / `dominant_regime=bull(85.0%)` / `avg_quality=-0.1660` / `avg_pnl=-0.0060` / `alerts=label_imbalance,regime_shift`。
- 本輪產品化 patch 已落地：`Dashboard.tsx` 的 `💼 Execution 摘要` 與 `ExecutionStatus.tsx` hero / `可部署` metric 在第一次 `/api/status` 尚未返回前改顯示 `同步中`，不再先洩漏 `Blocked / unknown / automation OFF` 假陰性狀態。
- 驗證完成：`pytest tests/test_frontend_decision_contract.py -q`、`cd web && npm run build`、browser 初始 snapshot `/`、browser 初始 snapshot `/execution/status`、browser `/lab`、`python scripts/hb_parallel_runner.py --fast --hb 20260421-0446`。

### R｜感受直覺
- 目前最容易誤導 operator 的不是數值本身，而是 first paint 在 runtime truth 還沒 hydrate 前就先給出假陰性狀態；這會把「還在同步」誤讀成「真的 blocked / unknown」。
- exact-support blocker 仍未解除，所以任何 loading-state regression 都會把 current-live 真相再次稀釋成錯誤操作訊號。

### I｜意義洞察
1. **initial-sync copy 是 runtime contract，不是純 UI polish**：首頁與執行診斷頁若在 hydration 前先印出錯的 blocker/automation/venue 文案，使用者看到的是錯的產品真相。
2. **這輪 patch 改善的是 truthfulness，不是 readiness**：current-live blocker 仍是 `under_minimum_exact_live_structure_bucket (12/50)`；修掉 first-paint 假陰性，只是讓 operator 不再在同步階段被錯誤訊號污染。
3. **recent 500-row pathology 仍是主根因切片**：即使 q35 redesign 已把 raw `entry_quality` 拉到 `0.5562`、`allowed_layers_raw=1`，最終 execution 仍因 exact support 未達 minimum 被壓回 `allowed_layers=0`。

### D｜決策行動
- **Owner**：frontend runtime truth / current-live governance lane
- **Action**：守住 Dashboard 與 `/execution/status` 的 initial-sync contract，同時持續沿 `q35 12/50` exact-support shortage 與 recent 500-row pathology 追 current-live blocker 根因。
- **Artifacts**：`ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md`、`data/live_predict_probe.json`、`data/live_decision_quality_drilldown.json`、`data/recent_drift_report.json`、`data/heartbeat_20260421-0446_summary.json`。
- **Verify**：`pytest tests/test_frontend_decision_contract.py -q`、`cd web && npm run build`、browser `/`、browser `/execution/status`、browser `/lab`、`python scripts/hb_parallel_runner.py --fast --hb 20260421-0446`。
- **If fail**：只要 Dashboard 或 `/execution/status` 再次在 `/api/status` 首次返回前洩漏 `Blocked / unknown / automation OFF`，或 current-live blocker 被 venue / stale loading copy 稀釋，就升級回 frontend productization blocker。
