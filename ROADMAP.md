# ROADMAP.md — Current Plan Only

_最後更新：2026-04-20 09:23:03 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **`/execution` initial-sync loading contract 已 productize**
  - `web/src/pages/ExecutionConsole.tsx` 現在在 `/api/status`、`/api/execution/overview`、`/api/execution/runs` 完成首次同步前，統一顯示 `同步中 / 正在向 ... 取得 ...`。
  - 首屏不再先渲染 `尚未提供 blocker 摘要`、`unknown`、`尚未取得 bot profile cards`、`尚未建立 stateful run` 假陰性。
  - 驗證：`pytest tests/test_frontend_decision_contract.py -q`、`cd web && npm run build`、browser `/execution` 首屏 + 3 秒後 re-check。
- **本輪已刷新 current-state runtime artifacts**
  - `python scripts/hb_predict_probe.py`
  - `python scripts/live_decision_quality_drilldown.py`
  - `python scripts/recent_drift_report.py`
  - `python scripts/auto_propose_fixes.py`
  - 產出：`data/live_predict_probe.json`、`data/live_decision_quality_drilldown.json`、`data/recent_drift_report.json`、`issues.json`、`docs/analysis/live_decision_quality_drilldown.md`
- **current-state docs overwrite sync 已完成**
  - `ISSUES.md` / `ROADMAP.md` 已改成反映本輪 `/execution` loading-contract 修復與最新 breaker-first truth

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=circuit_breaker_active` / `streak=191` / `recent_window_wins=0/50` / `additional_recent_window_wins_needed=15`
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q00` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_unsupported_block`
**成功標準**
- `/`、`/execution`、`/execution/status`、`/lab`、probe、drilldown、docs 都把 breaker release math 視為唯一 current-live deployment blocker。
- current live bucket truth（`bucket / rows / gap / support route`）仍在 top-level surfaces 可 machine-read。

### 目標 B：持續把 recent canonical pathological slice 當成 breaker 根因來鑽
**目前真相**
- `window=100` / `win_rate=0.0%` / `dominant_regime=bull(100.0%)` / `avg_quality=-0.2363` / `avg_pnl=-0.0095`
- `alerts=constant_target,regime_concentration,regime_shift` / `tail_streak=100x0`
**成功標準**
- drift / probe / docs 能直接指出 pathological slice、adverse streak、top feature shifts，而不是退回 generic leaderboard / venue 摘要。

### 目標 C：守住 reference-only patch / leaderboard governance / venue-source blockers 的 product truth
**目前真相**
- `recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_until_exact_support_ready`
- `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro`
- `fin_netflow=source_auth_blocked`；venue blockers 仍缺 credential / order ack / fill lifecycle proof
**成功標準**
- `/api/status`、`/execution/status`、`/lab`、docs 都維持 same current-live truth：reference-only patch 不被誤升級、leaderboard 不回退 placeholder-only、venue/source blockers 持續可見。

### 目標 D：守住 shared backend failover + initial-sync loading contract across all primary surfaces
**目前真相**
- Dashboard / Execution Status / Strategy Lab 已有 loading-safe current-live sync copy。
- 本輪已把 Execution Console 補齊：在 `/api/status`、`/api/execution/overview`、`/api/execution/runs` 未返回前，先顯示 `同步中`，不先渲染假 blocker / 假空狀態。
**成功標準**
- `/`、`/execution`、`/execution/status`、`/lab` 在 fresh session / backend lane 漂移時，都先顯示 loading-safe 文案，再切回真實 payload；不再出現 `unknown / unavailable / 尚未提供 blocker 摘要 / 尚未取得 bot profile cards` 假陰性。

---

## 下一輪 gate
1. **維持 breaker-first truth + current live bucket visibility across API / UI / docs**
   - 驗證：browser `/`、browser `/execution`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`
   - 升級 blocker：若 breaker release math 被 support / floor-gap / venue 話題覆蓋，或 current live bucket rows/support route 再次從 top-level surfaces 消失
2. **持續鑽 recent canonical pathological slice，而不是 generic 化 root cause**
   - 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`
   - 升級 blocker：若 drift artifact 再失去 target-path / adverse-streak / top-shift 證據
3. **守住 reference-only patch、leaderboard governance、venue/source blockers 與首屏 loading contract**
   - 驗證：browser `/`、browser `/execution`、browser `/execution/status`、browser `/lab`、`curl http://127.0.0.1:8001/api/models/leaderboard`、`pytest tests/test_frontend_decision_contract.py tests/test_model_leaderboard.py tests/test_strategy_lab.py -q`、`cd web && npm run build`
   - 升級 blocker：若 patch 被誤升級成 deployable truth、排行榜 drift 成 placeholder-only、venue/source blocker 消失，或任一主頁首屏再回到 `unknown / unavailable / 尚未提供 blocker 摘要` 假陰性

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- current live bucket truth 維持：**0/50 + exact_bucket_unsupported_block + reference_only_until_exact_support_ready**
- recent canonical pathological slice 仍以同一個 current window 為主敘事，不被 generic 問題稀釋
- leaderboard 維持 dual-role governance；venue/source blockers 持續可見
- `/, /execution, /execution/status, /lab` 首屏都先顯示 loading-safe current-state copy，再切回真實 runtime payload
