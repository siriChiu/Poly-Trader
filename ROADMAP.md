# ROADMAP.md — Current Plan Only

_最後更新：2026-04-20 04:59:20 CST_

只保留目前計畫；每輪 heartbeat 必須覆寫更新，不保留歷史流水帳。

---

## 已完成
- **Heartbeat #20260420-runtimefallback 完成 collect + drift/probe refresh**
  - `Raw=31175 / Features=22593 / Labels=62881`
  - `simulated_pyramid_win=57.21%`
  - collect 本輪實際成長：`+1 raw / +1 features / +5 labels`
- **Dashboard / Strategy Lab dev-runtime backend failover 已產品化落地**
  - `web/src/hooks/useApi.ts`：新增 active backend base 持久化與 `8000/8001` timeout-aware fallback
  - `web/src/components/CandlestickChart.tsx`：改用 `fetchApiResponse()`，不再繞過 fallback
  - `web/src/pages/Dashboard.tsx`：每次 `/ws/live` retry 都重新計算 `buildWsUrl()`
  - 驗證：`pytest tests/test_frontend_decision_contract.py -q` ✅、`cd web && npm run build` ✅、browser `/` ✅、browser `/execution/status` ✅、browser `/lab` ✅
- **dev backend 健康 lane 已被實測區分**
  - `curl :8000/api/status` → timeout
  - `curl :8001/api/status` → `200` in `0.2086s`
  - `ws://127.0.0.1:8001/ws/live` → 握手成功

---

## 主目標

### 目標 A：維持 breaker-first truth，同時確保 operator-facing UI 真能連到健康 backend lane
**目前真相**
- `deployment_blocker=circuit_breaker_active` / `streak=175` / `recent_window_wins=0/50` / `additional_recent_window_wins_needed=15`
- 本地 dev runtime 下，`:8000` reload lane 會 timeout，`:8001` stable lane 健康；UI 已加入 failover，但仍需守住 contract
**成功標準**
- `/`、`/execution/status`、`/lab` 在 `:5173` Vite shell 下仍能穩定顯示 breaker-first truth、chart、venue blockers、q15 support truth
- 不再因單一 backend port 卡死而回退成 `UNKNOWN / 同步中` 假陰性

### 目標 B：把 recent 100-row pathological slice 當成 breaker 根因持續下鑽
**目前真相**
- `window=100` / `win_rate=0.0%` / `dominant_regime=bull(100.0%)` / `avg_quality=-0.2254` / `avg_pnl=-0.0088`
- `alerts=constant_target,regime_concentration,regime_shift` / `tail_streak=100x0`
**成功標準**
- drift / probe / docs 都直接呈現 pathological slice、adverse streak、top shifts，而不是退回 generic 摘要

### 目標 C：讓 fast heartbeat 真正回到 cron-safe bounded lane
**目前真相**
- `python scripts/hb_parallel_runner.py --fast --hb 20260420-runtimefallback` 在 `>240s` watchdog 內仍未完成
- timeout 前只完成 `hb_collect / regime_ic / full_ic / recent_drift_report`
**成功標準**
- `--fast` 能在 bounded watchdog 內完成 collect/drift/probe/docs overwrite sync
- leaderboard / candidate evaluation 不再拖垮 fast lane

### 目標 D：守住 q15 reference-only patch、leaderboard governance、venue/source blockers 可見性
**目前真相**
- `q15 support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`
- `recommended_patch=core_plus_macro_plus_all_4h` 仍只能 `reference_only_until_exact_support_ready`
- leaderboard：`selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro`
- venue blockers 與 `fin_netflow=source_auth_blocked` 仍是 open truth
**成功標準**
- probe / API / UI / docs 對 q15、leaderboard、venue、source blockers 維持單一 current truth，不互相漂移

---

## 下一輪 gate
1. **把 fast heartbeat 壓回 bounded cron lane**
   - 驗證：`python scripts/hb_parallel_runner.py --fast --hb <test>` 必須在 bounded watchdog 內完成，且完成 docs overwrite sync
   - 升級 blocker：若仍在 collect/IC/drift 後卡住，代表 fast lane productization 仍未完成
2. **守住 Dashboard / Strategy Lab 的 backend failover contract**
   - 驗證：`curl http://127.0.0.1:8000/api/status` timeout、`curl http://127.0.0.1:8001/api/status` 200、browser `/`、browser `/lab`、`pytest tests/test_frontend_decision_contract.py -q`、`cd web && npm run build`
   - 升級 blocker：若 `/` 或 `/lab` 再次因單一 backend port 掛住而掉回 loading/blank chart/UNKNOWN
3. **持續沿 pathological slice + q15 exact support 追根因**
   - 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`
   - 升級 blocker：若 breaker-first truth 被 support / venue / leaderboard 話題覆蓋，或 q15 0/50 / reference-only patch 從 top-level surfaces 消失

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- Vite dev shell 下的 Dashboard / Strategy Lab 仍能連到健康 backend lane 並呈現同一份 current-live truth
- recent pathological slice 仍以同一個 current window 為主敘事，不被 generic 問題稀釋
- `--fast` 回到真正 cron-safe 的 collect/drift/probe/docs lane
- q15、leaderboard、venue/source blockers 與 current-state docs 維持一致
