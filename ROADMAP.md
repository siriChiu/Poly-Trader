# ROADMAP.md — Current Plan Only

_最後更新：2026-04-19 12:30 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **fast heartbeat `#20260419q` + collect 成功**：`Raw=31095 (+1) / Features=22513 (+1) / Labels=62594 (+3)`；`240m / 1440m` freshness 仍屬 expected horizon lag，資料管線不是 frozen。
- **本輪產品化 patch：修正 `/execution` / `/execution/status` blocker 排序 drift**
  - `web/src/pages/ExecutionStatus.tsx` 現在會先顯示 `deployment_blocker / deployment_blocker_reason`，再附上 `readiness_scope` 與 `venue blockers`；`主 blocker` 區塊不再被 `live_ready_blockers` 覆蓋。
  - `web/src/pages/ExecutionConsole.tsx` 現在會先顯示 current live breaker reason，再把 `live exchange credential / order ack lifecycle / fill lifecycle` 保留為 secondary blocker visibility；不再把 venue readiness 誤包裝成 current-live 主 blocker。
  - `tests/test_frontend_decision_contract.py` 已新增 breaker-first 排序 regression，鎖住 `/execution` 與 `/execution/status` 都要讓 `deployment_blocker_reason` 優先於 `live_ready_blockers`。
  - `ARCHITECTURE.md` 已同步加入 execution breaker-first visibility contract。
- **本輪驗證完成**：
  - `source venv/bin/activate && pytest tests/test_frontend_decision_contract.py -q` → `16 passed`
  - `cd web && npm run build` → 通過
  - browser `http://127.0.0.1:5173/execution/status`：首屏改為 `blocker circuit_breaker_active · Consecutive loss streak: 246 >= 50 ...`，venue blockers 降為 secondary line。
  - browser `http://127.0.0.1:5173/execution`：頂部 blocked banner 改為先顯示 breaker reason；部署狀態卡仍保留 venue blockers，但不再搶走 current-live blocker 主語義。
  - browser console on `/execution`、`/execution/status`：無 JS exception。
- **Current-state docs 已覆蓋同步**：`ISSUES.md`、`ROADMAP.md`、`ARCHITECTURE.md` 已改成最新 truth；`issues.json` 由本輪 heartbeat 重寫為 current-state。

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=circuit_breaker_active`
- `recent 50 wins=0/50`
- `additional_recent_window_wins_needed=15`
- `streak=246`
- `allowed_layers=0`
- `current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15`

**成功標準**
- `/execution`、`/execution/status`、`/lab`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`issues.json`、`ISSUES.md` 全部一致把 breaker 視為唯一 current-live deployment blocker。

### 目標 B：維持 q15 `1/50` support shortage 與 stalled-under-minimum truth
**目前真相**
- `current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15`
- `live_current_structure_bucket_rows=1 / minimum_support_rows=50`
- `gap_to_minimum=49`
- `support_route_verdict=exact_bucket_present_but_below_minimum`
- `support_progress.status=stalled_under_minimum`
- `support_progress.stagnant_run_count=5`
- `support_progress.escalate_to_blocker=true`

**成功標準**
- probe / API / Strategy Lab / Execution Status / docs / `issues.json` 都一致承認 `1/50 + present_but_below_minimum + stalled_under_minimum + escalate_to_blocker=true`；
- breaker path 下不遮蔽 q15 support metadata，也不把 reference patch 誤報成 exact support closure。

### 目標 C：維持 live spillover 與 reference patch scope 的分離
**目前真相**
- `actual_live_spillover_scope=bull|BLOCK`
- `reference_patch_scope=bull|CAUTION`
- `reference_source=bull_4h_pocket_ablation.bull_collapse_q35`
- `recommended_patch=core_plus_macro`
- `recommended_patch_status=reference_only_until_exact_support_ready`

**成功標準**
- `/api/status`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、Dashboard、Strategy Lab 都同時保留 `spillover_regime_gate` 與 `reference_patch_scope/reference_source`；
- exact support 未達標前，patch 永遠只可作 reference-only，不得被 UI / docs / issues 升級成 deployable runtime patch。

### 目標 D：持續保留 venue blockers，但必須位於 breaker-first truth 之後
**目前真相**
- `binance=config enabled + public-only`
- `okx=config disabled + public-only`
- `metadata freshness=fresh`
- 缺的 proof 仍是 `live exchange credential / order ack lifecycle / fill lifecycle`

**成功標準**
- `/execution`、`/execution/status`、`/lab` 都能同時看到 `current-live breaker` 與 `venue blockers`，且 breaker 永遠是主語義、venue blockers 永遠是 secondary readiness evidence。

### 目標 E：解除 sparse-source ETF flow auth blocker
**目前真相**
- `fin_netflow=source_auth_blocked`
- `COINGLASS_API_KEY` 缺失
- `forward_archive_rows=2566`
- `archive_window_coverage_pct=0.0%`

**成功標準**
- `fin_netflow` 從 `auth_missing` 轉成成功 snapshot source；
- heartbeat source blockers 不再把 ETF flow 列為 auth blocker。

### 目標 F：改善 model stability 與 comparable leaderboard rows
**目前真相**
- `cv_accuracy=60.8%`
- `cv_std=12.5pp`
- `cv_worst=44.5%`
- `leaderboard_count=0`（placeholder-only）
- `global_profile=core_only`、`train_selected_profile=core_plus_macro`

**成功標準**
- Strategy Lab 至少能維持可信的 placeholder-only warning，且不把空榜包裝成 deployment ranking；
- 下一步 profile / robustness 調整能同時改善 current bucket 語義與 comparable rows，而不是再次回到 generic parity drift 討論。

---

## 下一輪 gate
1. **維持 breaker-first truth across `/execution` / `/execution/status` / `/lab` / probe / drilldown**
   - 驗證：browser `/execution`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`
   - 升級 blocker：若任何 surface 再把 venue blockers、q15 support 或 reference patch 排到 breaker 前面
2. **維持 q15 `1/50` 與 stalled-under-minimum machine-read truth**
   - 驗證：`python scripts/hb_q15_support_audit.py`、`python scripts/hb_predict_probe.py`、檢查 `stagnant_run_count` 與 `escalate_to_blocker`
   - 升級 blocker：若 docs / issues / UI 遺失 `exact_bucket_present_but_below_minimum`、`1/50` 或 `escalate_to_blocker=true`
3. **鎖住 live spillover vs reference patch scope separation，不讓 `bull|CAUTION` 再被誤報成 current live pocket**
   - 驗證：`curl /api/status`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、browser `/lab`
   - 升級 blocker：若 `/api/status`、probe、drilldown、UI 任一條路失去 `reference_patch_scope/reference_source` 或再次覆蓋 `spillover_regime_gate`
4. **持續保留 per-venue readiness cards，但不能搶走 current-live blocker 主語義**
   - 驗證：browser `/execution`、browser `/execution/status`、browser `/lab`、`data/execution_metadata_smoke.json`
   - 升級 blocker：若 venue blockers 從 operator surface 消失，或再次被錯誤提升成主 blocker
5. **解除 `fin_netflow` auth blocker**
   - 驗證：`data/heartbeat_20260419q_summary.json` source blockers、`/api/features/coverage`
   - 升級 blocker：若 forward archive 持續增長但 `latest_status` 仍長期 `auth_missing`

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- `q15 support 1/50 + exact_bucket_present_but_below_minimum + stalled_under_minimum + escalate_to_blocker=true` 在 breaker path 下仍完整暴露於 probe / API / UI / docs / issues
- `spillover_regime_gate` 與 `reference_patch_scope/reference_source` 在 `/api/status`、`hb_predict_probe.py`、drilldown、Dashboard、Strategy Lab 一致，不再把 reference patch 誤讀成 current live pocket
- `/execution`、`/execution/status`、`/lab` 同時保留：**breaker-first truth 清楚、venue blockers 可見但不搶主語義、exact-vs-spillover 對照可見、runtime console 無 JS exception**
- heartbeat 維持：**issue 對齊 → patch → verify → docs overwrite → commit → push**
