# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-20 12:18:53 CST_

---

## 心跳 #20260420-1216 ORID

### O｜客觀事實
- collect + diagnostics refresh 完成：`Raw=31211 / Features=22629 / Labels=62946`；`simulated_pyramid_win=57.17%`。
- current-live blocker：`deployment_blocker=circuit_breaker_active` / `streak=14` / `recent_window_wins=3/50` / `additional_recent_window_wins_needed=12`。
- q15 current-live bucket truth：`current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=10/50` / `gap=40` / `support_route_verdict=exact_bucket_present_but_below_minimum`。
- recent pathological slice：`window=250` / `win_rate=1.6%` / `dominant_regime=bull(96.0%)` / `avg_quality=-0.2124` / `avg_pnl=-0.0067` / `alerts=label_imbalance,regime_concentration,regime_shift`。
- 本輪產品化 patch：`web/src/pages/Dashboard.tsx` 將 Dashboard 首次 `/ws/live` 連線改成 defer bootstrap，避開 React.StrictMode probe 自己把 socket 關掉造成的假性 console warning。
- 回歸保護：`tests/test_frontend_decision_contract.py` 新增 strict-mode-safe bootstrap regression；`pytest tests/test_frontend_decision_contract.py tests/test_hb_parallel_runner.py -q` 103 passed。
- runtime/browser 證據：`cd web && npm run build` 通過；browser `/` console 只剩 Vite / React info，無 `closed before the connection is established`。
- 文件覆蓋：`ISSUES.md / ROADMAP.md / ORID_DECISIONS.md` 已按最新 artifacts 與前端 patch 覆寫同步。

### R｜感受直覺
- 當 breaker-first truth 已經是主敘事時，Dashboard 首屏還冒出自傷型 WebSocket warning，會把 operator 注意力從真正 blocker 拉走，這是產品化噪音，不是小瑕疵。
- 這種 warning 最危險的地方在於它看起來像 lane failover 又壞了，但其實是前端自己在開發探測週期裡先把 socket 關掉。

### I｜意義洞察
1. **首屏 console 乾淨度也是產品契約的一部分**：即時頁面如果一進來就報假錯，operator 很難相信 blocker / venue / recovery 診斷是真訊號。
2. **這不是後端壞掉，而是前端 bootstrap 時機錯了**：HTTP/WS lane 都可用，但 StrictMode 的 mount→cleanup→mount 會把同步開啟的 WS 變成自我取消。
3. **最小有效修補是延後第一次 socket 建立，而不是亂改 lane 選擇**：保持現有 failover / retry 邏輯不變，只消除自傷型 handshake 噪音。

### D｜決策行動
- **Owner**：Dashboard runtime / operator-experience lane
- **Action**：首次載入先排入 bootstrap timer，再建立 WebSocket；cleanup 時同步清掉 bootstrap / reconnect timers，避免 StrictMode probe 啟動真實 handshake。
- **Artifacts**：`web/src/pages/Dashboard.tsx`、`tests/test_frontend_decision_contract.py`、`ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md`
- **Verify**：`python scripts/hb_parallel_runner.py --fast --hb 20260420-1216`、`pytest tests/test_frontend_decision_contract.py tests/test_hb_parallel_runner.py -q`、`cd web && npm run build`、browser `/` + console clean
- **If fail**：只要 Dashboard 首屏再出現自傷型 WS warning，就升級回 dev-runtime/operator-experience blocker，因為它會污染 current-live blocker 判讀與首屏信任感。
