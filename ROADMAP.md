# ROADMAP.md — Current Plan Only

_最後更新：2026-04-19 23:35:07 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **本輪產品化 patch：bull pocket fast path 已從 timeout fallback 升級成 current-bucket refresh lane**
  - `scripts/bull_4h_pocket_ablation.py` 新增 `--refresh-live-context`。
  - `scripts/hb_parallel_runner.py --fast` 現在會改走 refresh lane，而不是在 fast path 重跑完整 bull pocket rebuild。
  - 實測：`python scripts/bull_4h_pocket_ablation.py --refresh-live-context` → **2.32s**。
- **本輪產品語義同步：fast summary / probe / bull pocket diagnostics 已承認 refresh lane 只提供 current truth，不提供 fresh live-specific cohorts**
  - `refresh_mode=live_context_only`
  - `live_specific_profiles_fresh=false`
  - `production_profile_role=current_bucket_refresh_reference_only`
  - `support_pathology_summary.blocker_state=current_bucket_refresh_reference_only`
- **本輪 fast heartbeat 已完成且留下新鮮 artifacts**
  - `python scripts/hb_parallel_runner.py --fast` → `1:22.81` 完成
  - `Raw=31146 / Features=22564 / Labels=62691`
  - `Global IC=13/30`、`TW-IC=28/30`
  - current live truth：`deployment_blocker=circuit_breaker_active`、`current_live_structure_bucket=CAUTION|structure_quality_caution|q35`、`current_live_structure_bucket_rows=1/50`、`support_route_verdict=exact_bucket_present_but_below_minimum`
- **本輪驗證已補齊**
  - `pytest tests/test_bull_4h_pocket_ablation.py::test_main_refresh_live_context_reuses_reference_profiles_but_clears_live_specific_profiles tests/test_hb_parallel_runner.py::test_run_bull_4h_pocket_ablation_uses_refresh_lane_in_fast_mode tests/test_hb_parallel_runner.py::test_collect_bull_4h_pocket_diagnostics_marks_current_bucket_refresh_reference_only tests/test_hb_parallel_runner.py::test_collect_bull_4h_pocket_diagnostics_marks_semantic_mismatch_reference_only tests/test_hb_parallel_runner.py::test_current_leaderboard_candidate_semantic_signature_prefers_live_probe_bucket_over_stale_bull_artifact tests/test_frontend_decision_contract.py::test_dashboard_execution_summary_keeps_current_live_blocker_ahead_of_venue_readiness_copy tests/test_frontend_decision_contract.py::test_strategy_lab_keeps_decision_quality_summary_surfaces -q` → `7 passed`
  - browser `/`、`/execution`、`/execution/status`、`/lab`：breaker-first truth、q35 `1/50` support、reference-only patch、venue blockers 都可見
- **本輪 current-state 文件覆寫已完成**
  - `ISSUES.md` / `ROADMAP.md` / `ORID_DECISIONS.md` 已覆寫成 heartbeat #fast 最新 current-state-only truth。
  - `ARCHITECTURE.md` 已同步補上 bull pocket current-bucket refresh lane contract。

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=circuit_breaker_active`
- `recent 50 wins=1/50`
- `required_recent_window_wins=15`
- `additional_recent_window_wins_needed=14`
- `streak=10`
- `allowed_layers=0`
- `current_live_structure_bucket=CAUTION|structure_quality_caution|q35`

**成功標準**
- `/`、`/execution`、`/execution/status`、`/lab`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`issues.json`、`ISSUES.md` 全部一致把 breaker 視為唯一 current-live deployment blocker。

### 目標 B：維持 q35 `1/50` 與 reference-only patch 真相
**目前真相**
- `current_live_structure_bucket=CAUTION|structure_quality_caution|q35`
- `current_live_structure_bucket_rows=1 / minimum_support_rows=50`
- `gap_to_minimum=49`
- `support_route_verdict=exact_bucket_present_but_below_minimum`
- `recommended_patch=core_plus_macro_plus_all_4h`
- `recommended_patch_status=reference_only_until_exact_support_ready`

**成功標準**
- probe / drilldown / `/` / `/execution` / `/execution/status` / `/lab` / docs / `issues.json` 都一致承認：`1/50 + exact_bucket_present_but_below_minimum + reference_only_until_exact_support_ready`。

### 目標 C：讓 bull pocket fast path 持續維持 cron-safe current-truth lane
**目前真相**
- fast path 已不再 timeout；改走 `--refresh-live-context`
- refresh lane 只保留 `bull_all / bull_collapse_q35` 的 reference-only patch 可見性
- live-specific proxy cohorts 仍不是 current deployable truth

**成功標準**
- `python scripts/bull_4h_pocket_ablation.py --refresh-live-context` 穩定在 fast budget 內完成；
- `python scripts/hb_parallel_runner.py --fast` 不再因 bull pocket rebuild 被卡住；
- 在任何情況下，都不得把 refresh lane 誤包裝成 full live-specific cohort rebuild。

### 目標 D：把 recent canonical 250-row pathology 當成 breaker 根因持續鑽深
**目前真相**
- `recent_window=250`
- `win_rate=0.0040`
- `dominant_regime=bull(100%)`
- `avg_pnl=-0.0095`
- `avg_quality=-0.2785`
- `tail_streak=10x0`
- top shifts=`feat_eye`、`feat_4h_bias20`、`feat_4h_bb_pct_b`
- new compressed=`feat_vwap_dev`

**成功標準**
- drift / live probe / docs 能直接指出 pathological slice 與 top feature shifts；
- 不再把 current blocker 稀釋成 generic leaderboard / venue 討論。

### 目標 E：守住 leaderboard / venue / source blocker 的產品語義同步
**目前真相**
- leaderboard：`count=6 / comparable_count=6 / top=rule_baseline / core_only / scan_backed_best`
- venue blockers：`live exchange credential / order ack lifecycle / fill lifecycle` 仍未驗證
- `fin_netflow=source_auth_blocked`

**成功標準**
- `/`、`/execution`、`/execution/status`、`/lab`、probe、`issues.json`、docs 對 leaderboard top row、current blocker、venue blockers、source auth blockers 說同一個真相。

---

## 下一輪 gate
1. **維持 breaker-first truth + q35 `1/50` support truth across UI / probe / docs**
   - 驗證：browser `/`、browser `/execution`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`
   - 升級 blocker：若任一 surface 再把 q35 `1/50` 說成 support 已 closure，或把 patch / venue 排到 breaker 前面
2. **守住 bull pocket current-bucket refresh lane，不讓它回退成 timeout 或假 full rebuild**
   - 驗證：`python scripts/bull_4h_pocket_ablation.py --refresh-live-context`、`python scripts/hb_parallel_runner.py --fast`、`data/bull_4h_pocket_ablation.json`
   - 升級 blocker：若 fast path 再 timeout，或 refresh lane 把 live-specific proxy cohorts 說成 current deployable truth
3. **持續鑽 recent canonical 250-row pathology，而不是 generic 化 blocker**
   - 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`
   - 升級 blocker：若 drift artifact 再失去 top shifts / tail-streak / target-path evidence，或 docs 又退回只寫 generic leaderboard / venue 問題

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- `/`、`/execution`、`/execution/status`、`/lab` 都先顯示 `deployment_blocker=circuit_breaker_active`，再顯示 venue blockers
- `current live q35 = 1/50 + exact_bucket_present_but_below_minimum + reference_only_until_exact_support_ready` 在 probe / drilldown / API / UI / docs / summary 全部 machine-read 一致
- bull pocket fast path 維持：**current-bucket refresh lane 可在 fast budget 內完成，且僅提供 reference-only patch 可見性**
- canonical leaderboard 維持：**6 筆 comparable rows、top row = `rule_baseline / core_only / scan_backed_best`**
- heartbeat 維持：**issue 對齊 → patch → verify → docs overwrite → commit → push**
