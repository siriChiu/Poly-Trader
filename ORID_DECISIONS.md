# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-18 21:46 CST_

---

## 心跳 #20260418f ORID

### O｜客觀事實
- `python scripts/hb_parallel_runner.py --fast --hb 20260418f` 完成 collect + verify 閉環：`Raw 30886→30887 / Features 22304→22305 / Labels 62192→62193`。
- current live 已不是 q15/q35 blocker，而是 **canonical circuit breaker**：`signal=CIRCUIT_BREAKER`、`deployment_blocker=circuit_breaker_active`、`recent 50 wins=4/50`、`additional_recent_window_wins_needed=11`、`streak=45`。
- 瀏覽器驗證 `http://127.0.0.1:5173/execution` 與 `/execution/status`：都顯示 `circuit_breaker_active`、`circuit_breaker_blocks_trade`、`layers — → 0`，並保留 `live exchange credential / order ack / fill lifecycle` blocker。
- `fetch('/api/models/leaderboard')` 回傳 `count=0 / comparable_count=0 / placeholder_count=4 / stale=true / refreshing=true / refresh_reason=cache_stale`。
- `recent_drift_report.py` 主視窗仍是最近 `1000` 筆 `distribution_pathology`，bull 佔比 `88.8%`；tail 已擴大到 `45` 連敗。
- 本輪 patch 驗證：`python -m pytest tests/test_auto_propose_fixes.py -q` → `19 passed`；`python -m pytest tests/test_api_feature_history_and_predictor.py tests/test_hb_predict_probe.py tests/test_q15_support_audit.py tests/test_auto_propose_fixes.py tests/test_server_startup.py -q` → `129 passed`。

### R｜感受直覺
- 最危險的不是 q15 patch 還沒完成，而是 **current-state docs/issue tracker 很容易繼續沿用過期 q15 敘事**，把真正的 breaker 主 blocker 蓋掉。
- 這一輪如果不把 current-live blocker 語義切回 breaker release math，接下來所有 patch 都會修錯地方。

### I｜意義洞察
1. **current-live truth 已切換**：現在主 blocker 是 breaker，不是 q15 exact support / floor-gap。
2. **machine-readable issue governance 也是產品面的一部分**：如果 `issues.json` 還在講 q15 patch-active，Dashboard / operator / heartbeat 文件就會一起被過期敘事污染。
3. **leaderboard honesty 仍然必要，但還不夠**：背景重算存在，不代表 canonical ranking 已可部署；空榜必須繼續誠實，但下一步要真正產出 comparable row。

### D｜決策行動
- **Owner**：AI Agent / heartbeat current-state governance path
- **Action**：修 `scripts/auto_propose_fixes.py`，在 live probe 進入 `CIRCUIT_BREAKER` / `circuit_breaker_active` 時，停止沿用 stale q15 bucket history，resolve `P0_q15_patch_active_but_execution_blocked`，改由 `#H_AUTO_CIRCUIT_BREAKER` 輸出 release math。
- **Artifact**：`scripts/auto_propose_fixes.py`、`tests/test_auto_propose_fixes.py`、`issues.json`、`ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md`
- **Verify**：
  - `python -m pytest tests/test_auto_propose_fixes.py -q`
  - `python -m pytest tests/test_api_feature_history_and_predictor.py tests/test_hb_predict_probe.py tests/test_q15_support_audit.py tests/test_auto_propose_fixes.py tests/test_server_startup.py -q`
  - `python scripts/hb_parallel_runner.py --fast --hb 20260418f`
  - Browser：`/execution`、`/execution/status`
- **If fail**：若下一輪 auto-propose 又把 q15 / q35 當 current-live 主 blocker，直接把 current-bucket truth contract 升級成 hard blocker，禁止 heartbeat 在 breaker 期間保留任何 stale lane-specific P0。
