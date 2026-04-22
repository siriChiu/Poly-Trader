# ROADMAP.md — Current Plan Only

_最後更新：2026-04-22 17:41:54 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 已完成
- **fast heartbeat #fast 已完成 collect + diagnostics refresh**
  - `Raw=31506 / Features=22924 / Labels=63522`
  - `deployment_blocker=unsupported_exact_live_structure_bucket`
  - `latest_window=250` / `win_rate=82.8%` / `alerts=label_imbalance`
  - `blocking_window=1000` / `win_rate=39.4%` / `alerts=regime_shift`
- **本輪交付 runtime lane freshness guard**
  - `/health` 現在會回 `runtime_build={process_started_at, git_head_commit, head_sync_status}`
  - `web/src/hooks/useApi.ts` prewarm 在兩條 lane 都健康時，優先 `current_head_commit`，拒絕 stale stable lane
  - 已重啟 `:8001` stable lane；`/api/status` 與 `:8000` 重新對齊 `deployment_blocker / current_live_structure_bucket / recommended_patch_status`
  - browser 已驗證 `poly_trader.active_api_base` 只會收斂到 `head_sync_status=current_head_commit` 的 lane（本輪 `/`、`/lab` 觀察到 `:8000`）
- **本輪驗證已完成**
  - `pytest tests/test_server_startup.py tests/test_frontend_decision_contract.py -q`
  - `cd web && npm run build`
  - `curl :8000/health` / `curl :8001/health`
  - browser `/execution/status` / `/lab`

---

## 主目標

### 目標 A：維持 current-live exact-support blocker 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=unsupported_exact_live_structure_bucket`
- `current_live_structure_bucket=BLOCK|bull_high_bias200_overheat_block|q35` / `support=0/50` / `gap=50`
- `support_route_verdict=exact_bucket_unsupported_block` / `recommended_patch_status=reference_only_non_current_live_scope`
**成功標準**
- `/`、`/execution/status`、`/lab`、probe、drilldown、docs 都把 `unsupported_exact_live_structure_bucket` 視為唯一 current-live deployment blocker。
- current live bucket truth (`bucket / rows / minimum / gap / support route / governance route`) 在 top-level surfaces 持續可 machine-read。

### 目標 B：持續把 recent canonical blocker pocket 當成 current blocker 根因來鑽
**目前真相**
- `latest_window=250` / `win_rate=82.8%` / `dominant_regime=chop(57.6%)` / `alerts=label_imbalance`
- `blocking_window=1000` / `win_rate=39.4%` / `dominant_regime=bull(81.3%)` / `alerts=regime_shift`
**成功標準**
- drift / probe / docs 能同時指出 latest diagnostics 與 current blocker pocket，不回退成 generic leaderboard / venue 摘要。

### 目標 C：守住 current live bucket support + reference-only patch 真相
**目前真相**
- `recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_non_current_live_scope` / `reference_scope=bull|CAUTION`
- q35 scaling audit 仍是 `bias50_formula_may_be_too_harsh` / `base_stack_redesign_candidate_grid_empty`
**成功標準**
- probe / drilldown / `/api/status` / `/execution/status` / `/lab` / docs 全都承認 current live bucket exact support 未達 minimum rows，recommended patch 只能作治理 / 訓練參考。

### 目標 D：守住 runtime lane freshness + leaderboard / venue / source blockers 的一致 product truth
**目前真相**
- `:8000` / `:8001` 現在都回 `runtime_build.head_sync_status=current_head_commit`
- browser active lane 只要 `head_sync_status=current_head_commit` 即屬健康；本輪 `/`、`/lab` 觀察到 `:8000`
- `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h`
- fin_netflow 仍 `source_auth_blocked`；venue blockers 仍缺 runtime-backed proof
**成功標準**
- stale lane 不得再壓過 fresh lane；Dashboard / Execution Status / Strategy Lab 不再因為未重啟的 stable lane 而 split-brain。
- leaderboard、venue blockers、source blockers、docs overwrite sync 持續維持同一份 current-state truth。

---

## 下一輪 gate
1. **維持 current-live exact-support blocker + current live bucket visibility across API / UI / docs**
   - 驗證：browser `/`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`
   - 升級 blocker：若 current-live blocker 被 breaker 舊敘事 / venue 話題覆蓋，或 current live bucket rows 再次從 top-level surfaces 消失
2. **持續鑽 recent canonical pathological slice，而不是 generic 化 root cause**
   - 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`
   - 升級 blocker：若 drift artifact 再失去 target-path / sibling-window / top-shift 證據
3. **守住 runtime lane freshness + leaderboard / venue / source / docs 閉環**
   - 驗證：`curl http://127.0.0.1:8000/health`、`curl http://127.0.0.1:8001/health`、browser console `localStorage['poly_trader.active_api_base']`、`curl http://127.0.0.1:<active-backend>/api/models/leaderboard`、`data/execution_metadata_smoke.json`
   - 升級 blocker：若 `head_sync_status=stale_head_commit` 的 lane 再次被前端選成 active base，或 leaderboard / venue / source blocker 真相在 API / UI / docs 間重新 split-brain

---

## 成功標準
- current-live blocker 清楚且唯一：**unsupported_exact_live_structure_bucket**
- current live bucket support truth 維持：**0/50 + exact_bucket_unsupported_block + reference_only_non_current_live_scope**
- recent canonical diagnostics 與 current blocker pocket 同步可見，不被 generic 問題稀釋
- stale backend lane 不再覆蓋 current blocker truth；active frontend lane 會優先 current head commit
- leaderboard 維持 dual-role governance；venue/source blockers 持續可見；docs 每輪完成 overwrite sync
