# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-20 07:29:32 CST_

---

## 心跳 #20260420-0712 ORID

### O｜客觀事實
- collect + diagnostics refresh 完成：`Raw=31184 / Features=22602 / Labels=62902`；`simulated_pyramid_win=57.18%`。
- current-live blocker 仍是 `deployment_blocker=circuit_breaker_active`：`streak=186` / `recent_window_wins=0/50` / `additional_recent_window_wins_needed=15`。
- current live bucket truth：`CAUTION|base_caution_regime_or_bias|q00` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`。
- recent pathological slice 仍集中在最近 `100` 筆：`win_rate=0.0%` / `dominant_regime=bull(100.0%)` / `avg_quality=-0.2343` / `avg_pnl=-0.0094` / `alerts=constant_target,regime_concentration,regime_shift`。
- 本輪驗證到本地 dev runtime 是 **`:8000 timeout、:8001 可用`**；`curl http://127.0.0.1:8000/api/status` timeout、`curl http://127.0.0.1:8001/api/status` 回 405/GET-only，browser 仍可從 `:5173` 載入 Dashboard / Strategy Lab / Execution Status。
- fast heartbeat 這輪仍超 budget：`elapsed_seconds=74.0` / `timed_out_lanes=feature_group_ablation`；但 elapsed telemetry 已改成 run-level monotonic baseline，不再出現 progress 倒退或 0 秒假完成。

### R｜感受直覺
- 這輪真正的產品風險不是「看不到 blocker」，而是 **runtime / cron telemetry 若被 stale timeout 或重設過的 elapsed 污染，operator 會讀到錯的 current state**。
- breaker-first truth 仍成立，但如果 Dashboard/Strategy Lab 因 dead backend lane 冒出假 error，或 heartbeat summary 把 74 秒 run 說成 0 秒，就會把產品面觀測拉回不可信。

### I｜意義洞察
1. **frontend failover 必須防 stale request**：dev runtime 有多 backend lane 時，只要舊 timeout 能覆蓋新成功 response，Dashboard / Lab 就會出現假陰性 UX。
2. **heartbeat elapsed 必須用整輪 monotonic baseline**：collect/preflight + parallel + serial 是同一輪 heartbeat；若只算 parallel phase，cron budget issue 會被錯誤淡化。
3. **這輪 patch 修的是觀測正確性，不是主 blocker 本身**：circuit breaker / pathological slice / exact support shortage 仍是 current-live 主線，但現在 UI 與 heartbeat 至少不會用錯 telemetry 掩蓋它們。

### D｜決策行動
- **Owner**：runtime truth / heartbeat telemetry lane
- **Action 1**：`web/src/hooks/useApi.ts` 加入 request sequence + AbortController，取消 superseded requests 並忽略 stale timeout completion，避免 `:8000` dead lane 在 `:8001` 成功後仍把 UI 拉回 error/loading 錯態。
- **Action 2**：`scripts/hb_parallel_runner.py` 改用 `run_start_monotonic` 驅動 progress watchdog、summary elapsed、fast-timeout issue sync，讓 elapsed 永遠單調遞增並反映整輪 heartbeat。
- **Artifacts**：`web/src/hooks/useApi.ts`、`tests/test_frontend_decision_contract.py`、`scripts/hb_parallel_runner.py`、`tests/test_hb_parallel_runner_elapsed_contract.py`、`data/heartbeat_20260420-0712_summary.json`。
- **Verify**：
  - `pytest tests/test_frontend_decision_contract.py -q`
  - `pytest tests/test_hb_parallel_runner.py -q -k 'sync_fast_heartbeat_timeout_issue_resolves_stale_issue_when_run_finishes_within_budget or save_summary_uses_run_label_and_persists_source_blockers or main_writes_final_progress_artifact or main_parallel_watchdog_writes_pending_tasks_to_progress'`
  - `pytest tests/test_hb_parallel_runner_elapsed_contract.py -q`
  - `cd web && npm run build`
  - browser `/`、`/lab`、`/execution/status`
  - `python scripts/hb_parallel_runner.py --fast --hb 20260420-0712`
- **If fail**：若 UI 再被 dead backend lane 拉回假 error，或 fast heartbeat elapsed 再次出現倒退 / 0 秒假完成，就把這條 lane 升級為 runtime-truth blocker，因為 current-state 觀測已不可信。
