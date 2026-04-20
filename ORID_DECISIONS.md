# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-20 08:30:20 CST_

---

## 心跳 #fast + Dashboard failover ORID

### O｜客觀事實
- fast heartbeat 已完成：`Raw=31186 / Features=22604 / Labels=62909`；`simulated_pyramid_win=57.17%`。
- current-live blocker 仍是 `deployment_blocker=circuit_breaker_active`，`streak=191`，`recent_window_wins=0/50`，`additional_recent_window_wins_needed=15`。
- current live bucket 仍是 `CAUTION|base_caution_regime_or_bias|q00`，`rows=0/50`，`support_route_verdict=exact_bucket_unsupported_block`。
- recent canonical primary pathology 仍是 `window=100 / win_rate=0.0% / dominant_regime=bull(100%) / alerts=constant_target,regime_concentration,regime_shift`。
- root-cause 追查顯示：Dashboard 首次 WebSocket 會撞到 `ws://127.0.0.1:8000/ws/live` opening handshake timeout；`ws://127.0.0.1:8001/ws/live` 則可正常握手並回傳 `{"type":"connected"}`。
- browser `/` 在 patch 前會先顯示假性 `離線`；patch 後可在 active backend failover 下回到 `即時連線`，且 `circuit_breaker_active` / `Metadata freshness=fresh` 能正常顯示。

### R｜感受直覺
- 最危險的產品問題不是 breaker 本身，而是 operator 在 healthy stable lane 明明可用時，首頁卻先看到假性 `離線`；這會直接破壞對 runtime truth 的信任。
- 如果 Dashboard 自己在 lane failover 下失真，就算 breaker/venue/docs contract 都正確，使用者第一眼也會以為系統壞了。

### I｜意義洞察
1. **dev-runtime failover 不能只做在 GET/HEAD**：WebSocket 也必須吃同一條多-backend lane 邏輯，否則 UI 仍會 split-brain。
2. **user-facing truth 優先於 console 漂亮**：本輪最重要的是讓 Dashboard 在 8000 reload lane 掛住時仍能自動接到 8001 stable lane，先恢復正確的即時連線狀態。
3. **open-timeout fallback 比單純 retry 更接近產品需求**：如果 opening handshake 卡住，不應等到瀏覽器長 timeout 才恢復；應主動切下一個 candidate。

### D｜決策行動
- **Owner**：Dashboard / frontend failover lane
- **Action**：在 `web/src/hooks/useApi.ts` 新增 `buildWsCandidateUrls()` 與 `rememberActiveApiBaseFromWsUrl()`；在 `web/src/pages/Dashboard.tsx` 將 WebSocket 連線改成 candidate fallback + handshake timeout，讓 `8000 → 8001` 自動切換。
- **Patch 清單**：`web/src/hooks/useApi.ts`、`web/src/pages/Dashboard.tsx`、`tests/test_frontend_decision_contract.py`
- **Verify**：`pytest tests/test_frontend_decision_contract.py -q`、`cd web && npm run build`、browser `/` 顯示 `即時連線` 並載入 `circuit_breaker_active` / `Metadata freshness=fresh`
- **If fail**：只要 Dashboard / Strategy Lab 再次因 single-lane WebSocket 或 API failover 顯示假性 `離線` / `UNKNOWN` / 長時間 stale loading，就把 frontend failover UX 升級回 P1 product blocker。
