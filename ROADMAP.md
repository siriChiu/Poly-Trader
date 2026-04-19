# ROADMAP.md — Current Plan Only

_最後更新：2026-04-19 13:31 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **fast heartbeat `#20260419t` + collect 成功**：`Raw=31101 (+1) / Features=22519 (+1) / Labels=62601 (+1)`；`240m / 1440m` freshness 仍屬 expected horizon lag，資料管線不是 frozen。
- **本輪產品化 patch：鎖住 non-bull live row 的 bull pocket reference-only reuse**
  - `scripts/hb_parallel_runner.py` 現在在 current live `regime != bull` 時，會把 `bull_4h_pocket_ablation` 視為 reference-only artifact，而不是在 fast heartbeat 重跑 bull-only cohort/backtest。
  - `tests/test_hb_parallel_runner.py` 已新增 regression，鎖住 non-bull live row 時必須回傳 `fresh_non_bull_live_regime_reference_only_bull_4h_pocket_artifact_reused` / `reference_only=true`。
  - `data/heartbeat_20260419t_summary.json` 已驗證 `serial_results.bull_4h_pocket_ablation.cached=true`、`cache_reason=bounded_label_drift_non_bull_live_regime_reference_only_bull_4h_pocket_artifact_reused`。
- **本輪 runtime / UI 驗證完成**：
  - `source venv/bin/activate && PYTHONPATH=. pytest tests/test_hb_parallel_runner.py -q` → `58 passed`
  - `source venv/bin/activate && PYTHONPATH=. pytest tests/test_frontend_decision_contract.py -q` → `16 passed`
  - `cd web && npm run build` → 通過
  - browser `http://127.0.0.1:5173/lab`：顯示 `current live blocker=circuit_breaker_active`、`venue blockers`、`exact live lane rows=0` 與 `bull|BLOCK spillover 199 rows`，current-live / spillover 分離正常。
  - browser `http://127.0.0.1:5173/execution/status`：首屏仍是 breaker-first，且 `deployment blocker / execution guardrail / support 0/50 / venue blockers` 同時可見。
  - browser `http://127.0.0.1:5173/execution`：blocked banner 仍先顯示 breaker reason，venue blockers 保留為 secondary readiness evidence。
  - browser console on `/lab`、`/execution`、`/execution/status`：無 JS exception。
- **Current-state docs 已覆蓋同步**：`ISSUES.md`、`ROADMAP.md`、`issues.json` 已改成最新 truth；`ARCHITECTURE.md` 已保留 fast heartbeat 的 non-bull reference-only reuse contract。

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=circuit_breaker_active`
- `recent 50 wins=0/50`
- `additional_recent_window_wins_needed=15`
- `streak=248`
- `allowed_layers=0`
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`

**成功標準**
- `/execution`、`/execution/status`、`/lab`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`issues.json`、`ISSUES.md` 全部一致把 breaker 視為唯一 current-live deployment blocker。

### 目標 B：維持 q15 `0/50` support shortage 與 stalled-under-minimum truth
**目前真相**
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`
- `live_current_structure_bucket_rows=0 / minimum_support_rows=50`
- `gap_to_minimum=50`
- `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`
- `support_progress.status=stalled_under_minimum`
- `support_progress.escalate_to_blocker=true`

**成功標準**
- probe / API / Strategy Lab / Execution Status / docs / `issues.json` 都一致承認 `0/50 + exact_bucket_missing_exact_lane_proxy_only + stalled_under_minimum + escalate_to_blocker=true`；
- breaker path 下不遮蔽 q15 support metadata，也不把 reference patch 誤報成 exact support closure。

### 目標 C：維持 live spillover 與 reference-only bull artifact 的分離
**目前真相**
- current live：`regime=chop`、`gate=CAUTION`、`bucket=CAUTION|base_caution_regime_or_bias|q15`
- broader spillover：`bull|BLOCK` 199 rows、`WR=0.0%`、`quality=-0.2852`
- bull pocket artifact：只能作 `reference-only`
- fast heartbeat：`serial_results.bull_4h_pocket_ablation.cached=true`

**成功標準**
- `/api/status`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、Dashboard、Strategy Lab 都同時保留 `spillover_regime_gate` 與 exact live lane 對照；
- non-bull live row 時 `bull_4h_pocket_ablation` 只可作 reference-only cache reuse，不得再被當成 current-live patch 或被快心跳無謂重跑。

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
- `forward_archive_rows=2572`
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
   - 升級 blocker：若任何 surface 再把 venue blockers、q15 support 或 bull artifact 排到 breaker 前面
2. **維持 q15 `0/50` 與 stalled-under-minimum machine-read truth**
   - 驗證：`python scripts/hb_q15_support_audit.py`、`python scripts/hb_predict_probe.py`、檢查 `support_progress` / `gap_to_minimum` / `escalate_to_blocker`
   - 升級 blocker：若 docs / issues / UI 遺失 `exact_bucket_missing_exact_lane_proxy_only`、`0/50` 或 `escalate_to_blocker=true`
3. **鎖住 live spillover vs reference-only bull artifact separation**
   - 驗證：`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、browser `/lab`、`data/heartbeat_<run>_summary.json` 的 `serial_results.bull_4h_pocket_ablation`
   - 升級 blocker：若 non-bull live row 再重跑 bull pocket，或 `/lab` / docs 把 bull artifact 誤包裝成 current-live patch
4. **持續保留 per-venue readiness cards，但不能搶走 current-live blocker 主語義**
   - 驗證：browser `/execution`、browser `/execution/status`、browser `/lab`、`data/execution_metadata_smoke.json`
   - 升級 blocker：若 venue blockers 從 operator surface 消失，或再次被錯誤提升成主 blocker
5. **解除 `fin_netflow` auth blocker**
   - 驗證：`data/heartbeat_20260419t_summary.json` source blockers、`/api/features/coverage`
   - 升級 blocker：若 forward archive 持續增長但 `latest_status` 仍長期 `auth_missing`

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- `q15 support 0/50 + exact_bucket_missing_exact_lane_proxy_only + stalled_under_minimum + escalate_to_blocker=true` 在 breaker path 下仍完整暴露於 probe / API / UI / docs / issues
- non-bull live row 時，`bull_4h_pocket_ablation` 明確以 reference-only cache reuse 存在於 fast heartbeat summary，而不是被誤當 current-live patch 或被快心跳無謂重跑
- `/execution`、`/execution/status`、`/lab` 同時保留：**breaker-first truth 清楚、venue blockers 可見但不搶主語義、exact-vs-spillover 對照可見、runtime console 無 JS exception**
- heartbeat 維持：**issue 對齊 → patch → verify → docs overwrite → commit → push**
