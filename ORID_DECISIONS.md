# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-20 04:59:20 CST_

---

## 心跳 #20260420-runtimefallback ORID

### O｜客觀事實
- collect + diagnostics refresh：`Raw=31175 / Features=22593 / Labels=62881 / simulated_pyramid_win=57.21%`。
- current-live blocker 仍是 `deployment_blocker=circuit_breaker_active`：`streak=175` / `recent 50 wins=0/50` / `additional_recent_window_wins_needed=15`。
- q15 same-bucket truth 未變：`current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`。
- recent pathological slice 仍是 `window=100`：`win_rate=0.0%` / `dominant_regime=bull(100.0%)` / `avg_quality=-0.2254` / `avg_pnl=-0.0088` / `tail_streak=100x0`。
- dev runtime root cause 已重現：
  - `curl :8000/api/status` 在 watchdog 內 timeout
  - `curl :8001/api/status` 回 `200`（`0.2086s`）
  - `ws://127.0.0.1:8000/ws/live` handshake timeout
  - `ws://127.0.0.1:8001/ws/live` 握手成功
- 本輪 patch 已落地：`useApi.ts` active backend failover、`CandlestickChart.tsx` 改走 `fetchApiResponse()`、`Dashboard.tsx` WS retry 重算 `buildWsUrl()`。
- fast heartbeat timeout regression 仍存在：`python scripts/hb_parallel_runner.py --fast --hb 20260420-runtimefallback` 在 `>240s` 內仍未完成，只跑到 `hb_collect / regime_ic / full_ic / recent_drift_report`。

### R｜感受直覺
- 這輪真正的產品問題不是模型又少了幾個百分點，而是 **Vite shell 明明開著，Dashboard / Strategy Lab 卻可能連到錯的 backend lane，導致 current-live truth 看起來像「系統壞掉」**。
- 如果 operator 先看到 blank chart / UNKNOWN / 長時間同步中，就算 breaker-first contract 本身正確，也會被前端 runtime 假陰性掩蓋。
- 另一個風險是 fast heartbeat 名義上叫 fast，實際上還會卡在過重 lane，導致 docs overwrite 不能完全依賴 runner 自動收斂。

### I｜意義洞察
1. **backend lane 選對，breaker-first truth 才算真正交付到 UI**：current-live truth 不是只有 API payload 正確，還要確保 `/` 與 `/lab` 能在真實 dev shell 裡拿到健康 backend。
2. **chart / API / WebSocket 不能各走各的 backend 選擇邏輯**：只要 CandlestickChart 或 Dashboard WS 繞過統一 fallback，首頁就會重新 split-brain。
3. **fast lane 還沒 productized 完成**：既然 `--fast` 仍可超過 bounded watchdog，就不能假設 docs overwrite 一定會自動完成；本輪仍需人工覆蓋 current-state docs。

### D｜決策行動
- **Owner**：frontend runtime contract / heartbeat governance lane
- **Action 1**：保留並提交 dev-runtime backend failover patch，讓 Dashboard / Strategy Lab 在 `:5173` 下自動切到健康 backend。
- **Action 2**：用 browser + pytest + build 直接驗證 `/`、`/execution/status`、`/lab` 的 current-live truth 可見，不只看 source code。
- **Action 3**：把 fast heartbeat timeout regression 留作 open P1，要求下一輪把 candidate/leaderboard 評估從 `--fast` lane 收斂出去。
- **Artifacts**：`web/src/hooks/useApi.ts`、`web/src/components/CandlestickChart.tsx`、`web/src/pages/Dashboard.tsx`、`tests/test_frontend_decision_contract.py`、`ISSUES.md`、`ROADMAP.md`、`issues.json`、`ARCHITECTURE.md`。
- **Verify**：`pytest tests/test_frontend_decision_contract.py -q`、`cd web && npm run build`、browser `/`、browser `/execution/status`、browser `/lab`、`curl :8000/api/status` timeout、`curl :8001/api/status` 200、`/tmp/hb_ws_probe.py 8001` handshake success。
- **If fail**：只要 Dashboard / Strategy Lab 再次回到單一 backend port 綁死、blank chart、或 fast lane 仍拖垮 docs overwrite，就繼續視為 productization blocker，不得宣稱 heartbeat 完成。
