# ROADMAP.md — Current Plan Only

_最後更新：2026-04-19 18:15:53 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **本輪產品化 patch：q15 runtime resync reason 已與真實原因對齊**
  - `scripts/hb_parallel_runner.py` 新增 `_q15_post_audit_runtime_resync_reason()` 與 `_format_q15_post_audit_runtime_resync_message()`。
  - 當 q15 audit 只是修正 breaker 下的 `support_route_verdict / support_governance_route / support_progress` 時，runner 現在會輸出 `q15_runtime_resync.reason=support_truth_changed_under_breaker`，不再把這種 route/progress drift 說成 `patch-ready`。
  - `data/heartbeat_20260419ad_summary.json` 已持久化 `q15_runtime_resync={triggered, reason, message}`，讓後續 docs / automation / operator summary 能 machine-read 真正 resync 原因。
- **本輪回歸測試已補齊**
  - `tests/test_hb_parallel_runner.py` 新增 resync-reason 與 operator-message regression tests，鎖住 `patch_ready_probe_unpatched` 與 `support_truth_changed_under_breaker` 的區別。
  - `pytest tests/test_hb_parallel_runner.py tests/test_auto_propose_fixes.py -q` = `89 passed`。
- **本輪 fast heartbeat 已完成並留下新鮮 artifacts**
  - `heartbeat #20260419ad`: `Raw=31126 (+1) / Features=22544 (+1) / Labels=62639 (+2)`。
  - `q15_runtime_resync.reason=support_truth_changed_under_breaker`，live probe / drilldown 已 second-pass 重跑。
  - `Global IC=16/30`、`TW-IC=24/30`；recent canonical 250 rows 仍是 `distribution_pathology`。
- **本輪 current-state 文件覆寫已完成**
  - `ISSUES.md` / `ROADMAP.md` 已依 heartbeat #20260419ad 與最新 artifacts 覆寫成 current-state-only。
  - `ARCHITECTURE.md` 已補上 `q15 resync-reason truth contract`，把本輪真正修掉的 operator 誤讀風險寫回架構規範。

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=circuit_breaker_active`
- `recent 50 wins=0/50`
- `additional_recent_window_wins_needed=15`
- `streak=266`
- `allowed_layers=0`
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`

**成功標準**
- `/execution`、`/execution/status`、`/lab`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`issues.json`、`ISSUES.md` 全部一致把 breaker 視為唯一 current-live deployment blocker。

### 目標 B：維持 q15 `0/50`、reference-only patch、與 resync reason 的分離真相
**目前真相**
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`
- `live_current_structure_bucket_rows=0 / minimum_support_rows=50`
- `gap_to_minimum=50`
- `support_route_verdict=exact_bucket_missing_proxy_reference_only`
- `support_governance_route=exact_live_bucket_proxy_available`
- `support_progress.status=stalled_under_minimum`
- `remaining_gap_to_floor=0.0667`
- `best_single_component=feat_4h_bias50`
- `recommended_patch=core_plus_macro`
- `recommended_patch_status=reference_only_until_exact_support_ready`
- `q15_runtime_resync.reason=support_truth_changed_under_breaker`

**成功標準**
- probe / drilldown / Strategy Lab / API / docs / `issues.json` / heartbeat summary 都一致承認：`0/50 + exact_bucket_missing_proxy_reference_only + stalled_under_minimum + reference_only_until_exact_support_ready`。
- `q15_runtime_resync.reason` 必須與 console wording、summary JSON、docs 同步，不可再把 under-breaker support truth drift 誤包裝成 `patch-ready`。

### 目標 C：把 recent canonical 250-row pathology 當成 breaker 根因持續鑽深
**目前真相**
- `recent_window=250`
- `win_rate=0.0000`
- `dominant_regime=bull(100%)`
- `avg_pnl=-0.0103`
- `avg_quality=-0.2869`
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
2. **鎖住 q15 `0/50` + reference-only `core_plus_macro` patch visibility + `q15_runtime_resync.reason`**
   - 驗證：`python scripts/hb_q15_support_audit.py`、`python scripts/hb_predict_probe.py`、`python scripts/hb_parallel_runner.py --fast --hb <run>`、browser `/lab`、`pytest tests/test_hb_parallel_runner.py tests/test_auto_propose_fixes.py -q`
   - 升級 blocker：若 `support_route_verdict` 再回退成舊字串、`recommended_patch` 消失、resync reason/message 不一致，或 `issues.json` 再出現 stale route truth
3. **守住 leaderboard recent-window + Strategy Lab 兩年 policy，同時保留 dual-role governance truth**
   - 驗證：`curl http://127.0.0.1:8000/api/models/leaderboard`、browser `/lab`、`pytest tests/test_model_leaderboard.py tests/test_strategy_lab.py tests/test_frontend_decision_contract.py -q`、`cd web && npm run build`
   - 升級 blocker：若 leaderboard 回到 placeholder-only、top row 不再能 machine-read、或 Strategy Lab 回退成模糊區間 / 無法顯示 current live blocker

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- `q15 support 0/50 + exact_bucket_missing_proxy_reference_only + stalled_under_minimum + reference_only_until_exact_support_ready + q15_runtime_resync.reason` 在 probe / API / UI / docs / summary 全部 machine-read 一致
- recent canonical 250 rows pathology 仍被明確當成 breaker 根因，而不是被 leaderboard / venue 討論稀釋
- canonical leaderboard 維持：**6 筆 comparable rows、latest_bounded_walk_forward、rule_baseline/core_only top row、Strategy Lab 兩年回測 policy 可見**
- heartbeat 維持：**issue 對齊 → patch → verify → docs overwrite → commit → push**
