# ROADMAP.md — Current Plan Only

_最後更新：2026-04-20 08:56:14 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **shared dev-runtime active-backend failover 已 productize 到共用 API/WS layer**
  - `web/src/hooks/useApi.ts` 新增 `/health` prewarm，會先在 `8000/8001` 中找出健康 lane，持久化 active backend base，再讓 `/api/status`、chart 與其他 GET/HEAD requests 共用同一條 fallback。
  - `web/src/pages/Dashboard.tsx` 的 `/ws/live` 在首次連線與 retry 前先 prewarm active backend，再依健康 lane 重排 candidates。
  - 驗證：`pytest tests/test_frontend_decision_contract.py -q`、`cd web && npm run build`、browser `/`、browser `/execution/status`。
- **本輪已刷新 current-state runtime artifacts**
  - `python scripts/hb_predict_probe.py`
  - `python scripts/live_decision_quality_drilldown.py`
  - `python scripts/recent_drift_report.py`
  - 產出：`data/live_predict_probe.json`、`data/live_decision_quality_drilldown.json`、`data/recent_drift_report.json`、`docs/analysis/live_decision_quality_drilldown.md`
- **current-state docs overwrite sync 已完成**
  - `ISSUES.md` / `ROADMAP.md` / `ARCHITECTURE.md` 已改成反映本輪 shared prewarm + current blocker truth

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=circuit_breaker_active` / `streak=191` / `recent_window_wins=0/50` / `additional_recent_window_wins_needed=15`
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q00` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_unsupported_block`
**成功標準**
- `/`、`/execution/status`、`/lab`、probe、drilldown、docs 都把 breaker release math 視為唯一 current-live deployment blocker。
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
- fin_netflow=`source_auth_blocked`；venue blockers 仍缺 credential / order ack / fill lifecycle proof
**成功標準**
- `/api/status`、`/execution/status`、`/lab`、docs 都維持 same current-live truth：reference-only patch 不被誤升級、leaderboard 不回退 placeholder-only、venue/source blockers 持續可見。

### 目標 D：守住 shared active-backend prewarm，不讓 frontend 回退成假性同步中
**目前真相**
- `useApi.ts` 已先用 `/health` 對 `8000/8001` 做短超時 prewarm，再把 active backend base 套用到 `/api/status`、chart 與其他 GET/HEAD requests。
- `Dashboard.tsx` 的 `/ws/live` 也會在首次連線與 retry 前先做同一條 prewarm。
**成功標準**
- `/`、`/execution/status`、`/lab` 在 fresh session / active backend lane 漂移時，仍能收斂到健康 lane，不會長時間停在 `同步中 / UNKNOWN / unavailable` 假陰性。

---

## 下一輪 gate
1. **維持 breaker-first truth + current live bucket visibility across API / UI / docs**
   - 驗證：browser `/`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`
   - 升級 blocker：若 breaker release math 被 support / floor-gap / venue 話題覆蓋，或 current live bucket rows/support route 再次從 top-level surfaces 消失
2. **持續鑽 recent canonical pathological slice，而不是 generic 化 root cause**
   - 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`
   - 升級 blocker：若 drift artifact 再失去 target-path / adverse-streak / top-shift 證據
3. **守住 reference-only patch、leaderboard governance、venue/source blockers 與 shared active-backend prewarm**
   - 驗證：browser `/`、browser `/execution/status`、browser `/lab`、`curl http://127.0.0.1:8001/api/models/leaderboard`、`pytest tests/test_frontend_decision_contract.py tests/test_model_leaderboard.py tests/test_strategy_lab.py -q`
   - 升級 blocker：若 patch 被誤升級成 deployable truth、排行榜 drift 成 placeholder-only、venue/source blocker 消失，或 frontend 再次出現長時間 `同步中 / UNKNOWN / unavailable`

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- current live bucket truth 維持：**0/50 + exact_bucket_unsupported_block + reference_only_until_exact_support_ready**
- recent canonical pathological slice 仍以同一個 current window 為主敘事，不被 generic 問題稀釋
- leaderboard 維持 dual-role governance；venue/source blockers 持續可見
- frontend shared active-backend prewarm/failover 持續把 `/`、`/execution/status`、`/lab` 收斂到健康 lane，不先顯示假性 blocker
