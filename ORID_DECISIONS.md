# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-18 19:50 CST_

---

## 心跳 #20260418b ORID

### O｜客觀事實
- `python scripts/hb_parallel_runner.py --fast --hb 20260418b` 成功推進 `Raw 30882→30883 / Features 22300→22301 / Labels 62143→62143`。
- q15 support 已是 `96 / 50 exact_bucket_supported`；最新 resynced live probe 顯示 `q15_exact_supported_component_patch_applied=true`、`entry_quality=0.5501 / allowed_layers_raw=1 / allowed_layers=0`、`runtime_closure_state=patch_active_but_execution_blocked`。
- `/execution/status` 瀏覽器已同步顯示 `q15 patch active`、`layers 1 → 0`、`support 96 / 50`。
- model leaderboard 仍是 placeholder-only：`count=0 / comparable_count=0 / placeholder_count=6`。
- 回歸驗證：`113 passed` + `npm run build` PASS。

### R｜感受直覺
- 目前最危險的不是 q15 support 不夠，而是 fast heartbeat 若還引用 pre-audit probe，會把產品真相寫回成舊的 `patch inactive`。
- q15 現在真正的 blocker 已從「support missing」轉成「final execution/venue closure 還沒成立」。

### I｜意義洞察
1. **q15 的產品語義已進入下一階段**：support closure 已經完成，現在必須守住的是 `patch active but execution blocked` 的 no-deploy truth。
2. **fast heartbeat 本身就是 operator-facing product surface**：若它先寫錯 live truth，後面的 root-cause、docs、UI 全都會被污染。
3. **leaderboard 目前不是 profile governance drift，而是 trade generation 問題**：空榜雖然已誠實，但還不能回答部署選擇。

### D｜決策行動
- **Owner**：AI Agent / heartbeat runner path
- **Action**：在 `hb_parallel_runner.py` 補上 q15 post-audit runtime resync；當 q15 support audit 已判定 patch-ready、但 probe/drilldown 還停在 pre-patch 狀態時，自動重跑 probe + drilldown，再讓後續 q15 artifacts 與 docs 只吃 resynced truth。
- **Artifact**：`scripts/hb_parallel_runner.py`、`tests/test_hb_parallel_runner.py`、`ISSUES.md`、`ROADMAP.md`、`issues.json`、`ORID_DECISIONS.md`
- **Verify**：`python -m pytest tests/test_hb_parallel_runner.py tests/test_hb_predict_probe.py tests/test_live_decision_quality_drilldown.py tests/test_execution_console_overview.py tests/test_server_startup.py tests/test_frontend_decision_contract.py -q`、`cd web && npm run build`、`python scripts/hb_parallel_runner.py --fast --hb 20260418b`、browser `/execution/status`
- **If fail**：若 resync 後仍回到 stale pre-patch truth，下一輪直接把 q15 support audit / probe ordering 升級成 hard sequencing contract，禁止 fast lane 先摘要後補 audit。
