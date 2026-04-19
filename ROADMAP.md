# ROADMAP.md — Current Plan Only

_最後更新：2026-04-19 17:41:32 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **本輪產品化 patch：q15 support truth 在 breaker 下也會觸發 runner second-pass resync**
  - `scripts/hb_parallel_runner.py` 現在不只在 `exact_supported_component_experiment_ready` 時重跑 probe / drilldown。
  - 只要 `hb_q15_support_audit.py` 在 breaker 下改寫 `support_route_verdict / support_governance_route / support_progress / minimum_support_rows / gap_to_minimum`，runner 就會把這些欄位提升成頂層 diagnostics，並立刻 second-pass 重跑 `hb_predict_probe.py` + `live_decision_quality_drilldown.py`。
  - 結果：`/execution`、`/execution/status`、`/lab`、`issues.json` 不再停在舊的 `exact_bucket_missing_exact_lane_proxy_only`；current live truth 已一致對齊 `exact_bucket_missing_proxy_reference_only`。
- **本輪產品化 patch：machine-readable current-state issue tracker 去掉 legacy duplicate reference-only issue**
  - `scripts/auto_propose_fixes.py` 現在會在 canonical `P1_bull_caution_spillover_patch_reference_only` 存在時自動 resolve 舊的 `P1_reference_only_patch_visibility`。
  - `issues.json` 已驗證只保留單一 reference-only patch issue，符合 current-state-only 文件治理。
- **本輪文件/架構同步已完成**
  - `ARCHITECTURE.md` 已補上 `q15 under-breaker route-resync contract`，把這次 runner 真正修掉的 runtime-truth drift 寫回架構規範。
  - `ISSUES.md` / `ROADMAP.md` 已依 `heartbeat #20260419ab` 與最新 artifacts 重新覆寫成 current-state-only。
- **本輪 fast heartbeat 已完成並留下新鮮 artifacts**
  - `heartbeat #20260419ab`: `Raw=31124 (+1) / Features=22542 (+1) / Labels=62636 (+0)`。
  - `support_route_verdict=exact_bucket_missing_proxy_reference_only`、`support_governance_route=exact_live_bucket_proxy_available`、`support_progress.status=stalled_under_minimum` 已同步落進 probe / drilldown / `issues.json` / docs。
  - recent pathology 仍固定指向 canonical 250-row bull toxic slice，而不是被 leaderboard / venue 議題稀釋。
- **驗證證據已落地**
  - `pytest tests/test_auto_propose_fixes.py tests/test_hb_parallel_runner.py -q` = `85 passed`
  - 先前 runtime/frontend regression suite：`pytest tests/test_hb_parallel_runner.py tests/test_hb_predict_probe.py tests/test_model_leaderboard.py tests/test_strategy_lab.py tests/test_frontend_decision_contract.py -q` = `175 passed`
  - `cd web && npm run build` 通過
  - browser runtime 驗證：`/execution`、`/execution/status`、`/lab` 均可打開，且顯示 breaker-first truth、q15 support truth、reference-only patch visibility、leaderboard two-year policy。

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=circuit_breaker_active`
- `recent 50 wins=0/50`
- `additional_recent_window_wins_needed=15`
- `streak=265`
- `allowed_layers=0`
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`

**成功標準**
- `/execution`、`/execution/status`、`/lab`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`issues.json`、`ISSUES.md` 全部一致把 breaker 視為唯一 current-live deployment blocker。

### 目標 B：維持 q15 `0/50` 與 reference-only patch 的分離真相
**目前真相**
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`
- `live_current_structure_bucket_rows=0 / minimum_support_rows=50`
- `gap_to_minimum=50`
- `support_route_verdict=exact_bucket_missing_proxy_reference_only`
- `support_governance_route=exact_live_bucket_proxy_available`
- `support_progress.status=stalled_under_minimum`
- `remaining_gap_to_floor=0.0812`
- `best_single_component=feat_4h_bias50`
- `recommended_patch=core_plus_macro`
- `recommended_patch_status=reference_only_until_exact_support_ready`
- `spillover_regime_gate=bull|CAUTION`

**成功標準**
- probe / drilldown / Strategy Lab / API / docs / `issues.json` 都一致承認：`0/50 + exact_bucket_missing_proxy_reference_only + stalled_under_minimum + reference_only_until_exact_support_ready`。
- `bull|CAUTION` spillover 與 q15 current-live truth 不能再混成 deployable advice。

### 目標 C：把 recent canonical 250-row pathology 當成 breaker 根因持續鑽深
**目前真相**
- `recent_window=250`
- `win_rate=0.0000`
- `dominant_regime=bull(100%)`
- `avg_pnl=-0.0103`
- `avg_quality=-0.2867`
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
- top row：`rule_baseline / core_only / scan_backed_best`
- governance：`dual_role_governance_active`（global winner=`core_only`，train support-aware profile=`core_plus_macro`）
- Strategy Lab 已明示：`排行榜回測固定使用最近兩年`

**成功標準**
- `/api/models/leaderboard` 維持 comparable rows；
- Strategy Lab 工作區與模型排行維持最近兩年 policy，不再回退成 placeholder-only 或短窗假樂觀；
- regression tests 與 build 長期守住這個 contract。

### 目標 E：把 venue / source blockers 維持在可見但不搶 breaker 主線的位置
**目前真相**
- `binance=config enabled + public-only + metadata OK`
- `okx=config disabled + public-only + metadata OK`
- `fin_netflow=source_auth_blocked`
- `COINGLASS_API_KEY` 缺失

**成功標準**
- `/execution`、`/execution/status`、`/lab`、`ISSUES.md`、`issues.json` 都保留 venue blockers 與 source auth blockers，但它們永遠排在 breaker-first current blocker 之後。

---

## 下一輪 gate
1. **維持 breaker-first truth across `/execution` / `/execution/status` / `/lab` / probe / drilldown**
   - 驗證：browser `/execution`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`
   - 升級 blocker：若任何 surface 再把 q15 / venue / spillover 排到 breaker 前面，或遺失 `additional_recent_window_wins_needed=15`
2. **鎖住 q15 `0/50` + reference-only `core_plus_macro` patch visibility，避免 route/progress 再 drift 或 duplicate issue id 回歸**
   - 驗證：`python scripts/hb_q15_support_audit.py`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、browser `/lab`、`pytest tests/test_auto_propose_fixes.py tests/test_hb_parallel_runner.py -q`
   - 升級 blocker：若 `support_route_verdict` 再回退成舊字串、`recommended_patch` 消失、probe/drilldown/API 不一致，或 `issues.json` 再出現 legacy duplicate reference-only issue
3. **守住 leaderboard recent-window + Strategy Lab 兩年 policy，同時保留 dual-role governance truth**
   - 驗證：`curl http://127.0.0.1:8000/api/models/leaderboard`、browser `/lab`、`pytest tests/test_model_leaderboard.py tests/test_strategy_lab.py tests/test_frontend_decision_contract.py -q`、`cd web && npm run build`
   - 升級 blocker：若 leaderboard 回到 placeholder-only、top row 不再能 machine-read、或 Strategy Lab 回退成模糊區間 / 無法顯示 current live blocker

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- `q15 support 0/50 + exact_bucket_missing_proxy_reference_only + stalled_under_minimum + reference_only_until_exact_support_ready` 在 probe / API / UI / docs / issues 全部 machine-read 一致
- recent canonical 250 rows pathology 仍被明確當成 breaker 根因，而不是被 leaderboard / venue 討論稀釋
- canonical leaderboard 維持：**6 筆 comparable rows、latest_bounded_walk_forward、rule_baseline/core_only top row、Strategy Lab 兩年回測 policy 可見**
- heartbeat 維持：**issue 對齊 → patch → verify → docs overwrite → commit → push**
