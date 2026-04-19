# ROADMAP.md — Current Plan Only

_最後更新：2026-04-19 19:18:06 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **本輪產品化 patch：Dashboard Execution 摘要改成 blocker-first**
  - `web/src/pages/Dashboard.tsx` 現在先顯示 `current live blocker {deployment_blocker} · {deployment_blocker_reason}`，再顯示 `venue blockers`，避免首頁把 venue readiness copy 放到 current-live blocker 前面。
  - `tests/test_frontend_decision_contract.py` 新增 regression，固定驗證 Dashboard 先讀 `deployment_blocker_reason` 再讀 `live_ready_blockers`。
- **本輪 runtime recovery：`:8000` API 已恢復可用**
  - stale 的 uvicorn 進程先前讓 `/api/status`、`/api/predict/confidence`、`/api/models/leaderboard` 全部 timeout。
  - 本輪已重啟 `127.0.0.1:8000`，三條 API 現在都回 `200 OK`，browser DOM 也已讀到 `current live blocker circuit_breaker_active` 與獨立的 `venue blockers ...` 文案。
- **本輪 fast heartbeat 已完成並留下新鮮 artifacts**
  - `heartbeat #20260419ae`: `Raw=31131 (+1) / Features=22549 (+2) / Labels=62643 (+4)`。
  - `Global IC=15/30`、`TW-IC=25/30`；recent canonical 250 rows 仍是 `distribution_pathology`。
  - `support_route_verdict=exact_bucket_missing_proxy_reference_only`、`current_live_structure_bucket_rows=0`、`minimum_support_rows=50`。
- **本輪驗證已補齊**
  - `pytest tests/test_hb_parallel_runner.py tests/test_auto_propose_fixes.py tests/test_frontend_decision_contract.py -q` = `108 passed`
  - `pytest tests/test_model_leaderboard.py tests/test_strategy_lab.py tests/test_frontend_decision_contract.py -q` = `99 passed`
  - `cd web && npm run build` 通過
  - browser DOM 驗證 Dashboard 已顯示 `current live blocker circuit_breaker_active`，且 `venue blockers` 另起一行
- **本輪 current-state 文件覆寫已完成**
  - `ISSUES.md` / `ROADMAP.md` 已依 heartbeat #20260419ae 與最新 artifacts 覆寫成 current-state-only。
  - `ARCHITECTURE.md` 已補上 Dashboard execution-summary breaker-first contract。

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=circuit_breaker_active`
- `recent 50 wins=0/50`
- `additional_recent_window_wins_needed=15`
- `streak=268`
- `allowed_layers=0`
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`

**成功標準**
- `/`、`/execution`、`/execution/status`、`/lab`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`issues.json`、`ISSUES.md` 全部一致把 breaker 視為唯一 current-live deployment blocker。

### 目標 B：維持 q15 `0/50`、reference-only patch、與 support route 真相分離
**目前真相**
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`
- `live_current_structure_bucket_rows=0 / minimum_support_rows=50`
- `gap_to_minimum=50`
- `support_route_verdict=exact_bucket_missing_proxy_reference_only`
- `support_governance_route=exact_live_bucket_proxy_available`
- `support_progress.status=stalled_under_minimum`
- `remaining_gap_to_floor=0.1119`
- `best_single_component=feat_4h_bias50`
- `recommended_patch=core_plus_macro`
- `recommended_patch_status=reference_only_until_exact_support_ready`

**成功標準**
- probe / drilldown / Strategy Lab / Dashboard / API / docs / `issues.json` / heartbeat summary 都一致承認：`0/50 + exact_bucket_missing_proxy_reference_only + stalled_under_minimum + reference_only_until_exact_support_ready`。

### 目標 C：把 recent canonical 250-row pathology 當成 breaker 根因持續鑽深
**目前真相**
- `recent_window=250`
- `win_rate=0.0000`
- `dominant_regime=bull(100%)`
- `avg_pnl=-0.0103`
- `avg_quality=-0.2861`
- `tail_streak=250x0`
- top shifts：`feat_4h_bb_pct_b`、`feat_4h_bias20`、`feat_4h_rsi14`
- new compressed：`feat_vwap_dev`

**成功標準**
- recent drift / live probe / docs 能直接指出 pathological slice 與 feature shifts；
- 不再把 current blocker 稀釋成 generic leaderboard / venue 討論。

### 目標 D：守住 canonical leaderboard comparable rows、dual-role governance、與 Strategy Lab 兩年回測 contract
**目前真相**
- `/api/models/leaderboard`：`count=6`、`comparable_count=6`、`placeholder_count=0`
- `evaluation_fold_window=latest_bounded_walk_forward`
- `evaluation_max_folds=4`
- top row：`random_forest / core_only / scan_backed_best`
- governance：`dual_role_governance_active`
- runtime API `:8000` 已恢復可回應

**成功標準**
- `/api/models/leaderboard` 維持 comparable rows；
- Strategy Lab 維持最近兩年 policy，不回退成 placeholder-only 或短窗假樂觀；
- `:8000` 核心 API 維持可回應，不再讓 UI 落回 offline placeholder。

### 目標 E：把 venue / source blockers 維持在可見但不搶 breaker 主線的位置
**目前真相**
- `binance=config enabled + public-only + metadata OK`
- `okx=config disabled + public-only + metadata OK`
- `fin_netflow=source_auth_blocked`
- `COINGLASS_API_KEY` 缺失

**成功標準**
- `/`、`/execution`、`/execution/status`、`/lab`、`ISSUES.md`、`issues.json` 都保留 venue blockers 與 source auth blockers，但它們永遠排在 breaker-first current blocker 之後。

---

## 下一輪 gate
1. **維持 breaker-first truth across `/` / `/execution` / `/execution/status` / `/lab` / probe / drilldown**
   - 驗證：browser `/`、browser `/execution`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`
   - 升級 blocker：若任何 surface 再把 q15 / venue / spillover 排到 breaker 前面，或 `/api/status` 再次 timeout
2. **鎖住 q15 `0/50` + reference-only `core_plus_macro` patch visibility**
   - 驗證：`python scripts/hb_q15_support_audit.py`、`python scripts/hb_predict_probe.py`、`python scripts/hb_parallel_runner.py --fast --hb <run>`、browser `/lab`
   - 升級 blocker：若 `support_route_verdict` 回退、`recommended_patch` 消失、或 q15 support truth 在 probe / UI / docs 不一致
3. **守住 leaderboard recent-window contract 與 runtime API responsiveness**
   - 驗證：`curl http://127.0.0.1:8000/api/models/leaderboard`、`curl http://127.0.0.1:8000/api/status`、browser `/lab`、`pytest tests/test_model_leaderboard.py tests/test_strategy_lab.py tests/test_frontend_decision_contract.py -q`、`cd web && npm run build`
   - 升級 blocker：若 leaderboard 回到 placeholder-only、top row 無法 machine-read、Strategy Lab 回退成模糊區間，或 `:8000` 再次 timeout

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- Dashboard / Execution / Strategy Lab 都先顯示 `deployment_blocker`，再顯示 venue blockers
- `q15 support 0/50 + exact_bucket_missing_proxy_reference_only + stalled_under_minimum + reference_only_until_exact_support_ready` 在 probe / API / UI / docs / summary 全部 machine-read 一致
- recent canonical 250 rows pathology 仍被明確當成 breaker 根因，而不是被 leaderboard / venue 討論稀釋
- canonical leaderboard 維持：**6 筆 comparable rows、latest_bounded_walk_forward、可被 `:8000` runtime API 正常提供**
- heartbeat 維持：**issue 對齊 → patch → verify → docs overwrite → commit → push**
