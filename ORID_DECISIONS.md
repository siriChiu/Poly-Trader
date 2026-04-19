# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-19 23:35:07 CST_

---

## 心跳 #fast ORID

### O｜客觀事實
- `python scripts/hb_parallel_runner.py --fast` 已完成 collect + verify 閉環：`Raw 31145→31146 / Features 22563→22564 / Labels 62684→62691`。
- `scripts/bull_4h_pocket_ablation.py --refresh-live-context` 已成為 fast path 正式 lane，實測 **2.32s** 完成。
- `scripts/hb_parallel_runner.py` fast mode 現在改走 `BULL_4H_POCKET_ABLATION_REFRESH_CMD`，不再把 bull pocket 完整 rebuild 當成 fast heartbeat 的必要前提。
- bull pocket artifact / summary 現在明確輸出：
  - `refresh_mode=live_context_only`
  - `live_specific_profiles_fresh=false`
  - `production_profile_role=current_bucket_refresh_reference_only`
  - `support_pathology_summary.blocker_state=current_bucket_refresh_reference_only`
- 本輪 current live truth：
  - `deployment_blocker=circuit_breaker_active`
  - `current_live_structure_bucket=CAUTION|structure_quality_caution|q35`
  - `current_live_structure_bucket_rows=1`
  - `minimum_support_rows=50`
  - `gap_to_minimum=49`
  - `support_route_verdict=exact_bucket_present_but_below_minimum`
  - `recommended_patch=core_plus_macro_plus_all_4h`
  - `recommended_patch_status=reference_only_until_exact_support_ready`
- recent canonical 250-row pathology 仍存在：`win_rate=0.0040`、`dominant_regime=bull(100%)`、`avg_quality=-0.2785`、`tail_streak=10x0`。
- leaderboard 仍穩定：`count=6 / comparable_count=6 / top=rule_baseline / core_only / scan_backed_best / latest_persisted_snapshot`。
- 驗證：
  - targeted pytest `7 passed`
  - `python scripts/hb_parallel_runner.py --fast` → `1:22.81`
  - browser `/`、`/execution`、`/execution/status`、`/lab` 均已看到 breaker-first truth、q35 `1/50` support、reference-only patch 與 venue blockers

### R｜感受直覺
- 這一輪最大的產品進展不是把 bull pocket 完整算完，而是把 **fast heartbeat 從「可能 timeout」變成「一定先說對 current truth」**。
- 真正需要避免的，不是少一份 live-specific proxy cohort，而是讓 stale artifact 冒充 current q35 runtime truth。
- breaker 仍是唯一 current-live blocker；bull pocket patch 只能是治理參考，不能搶主敘事。

### I｜意義洞察
1. **fast mode 的首要任務是 current-truth correctness，不是 full rebuild completeness**：只要 q35 exact support 仍是 `1/50`，refresh lane 的價值就大於勉強重建一份容易 timeout 的 live-specific artifact。
2. **reference-only 不是失敗，而是正確降級**：`current_bucket_refresh_reference_only` 讓 current live truth 與 patch visibility 同時存在，但不再把 live-specific proxy cohorts 假裝成 deployable evidence。
3. **這個修正直接提升 cron-safe 產品可信度**：heartbeat、Dashboard、Execution、Strategy Lab、probe、docs 現在都能先對齊同一個 q35 / breaker / support truth，再談 patch 與 venue。

### D｜決策行動
- **Owner**：AI Agent / heartbeat runtime-governance path
- **Action**：維持 `current-bucket refresh lane + reference-only live-specific cohorts` 的 product contract，直到 exact support 真正達到 minimum rows 或 full rebuild 有明確新證據。
- **Artifact**：`scripts/bull_4h_pocket_ablation.py`、`scripts/hb_parallel_runner.py`、`tests/test_bull_4h_pocket_ablation.py`、`tests/test_hb_parallel_runner.py`、`data/bull_4h_pocket_ablation.json`、`data/heartbeat_fast_summary.json`、`ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md`、`ARCHITECTURE.md`
- **Verify**：
  - `python -m pytest tests/test_bull_4h_pocket_ablation.py::test_main_refresh_live_context_reuses_reference_profiles_but_clears_live_specific_profiles tests/test_hb_parallel_runner.py::test_run_bull_4h_pocket_ablation_uses_refresh_lane_in_fast_mode tests/test_hb_parallel_runner.py::test_collect_bull_4h_pocket_diagnostics_marks_current_bucket_refresh_reference_only tests/test_hb_parallel_runner.py::test_collect_bull_4h_pocket_diagnostics_marks_semantic_mismatch_reference_only tests/test_hb_parallel_runner.py::test_current_leaderboard_candidate_semantic_signature_prefers_live_probe_bucket_over_stale_bull_artifact tests/test_frontend_decision_contract.py::test_dashboard_execution_summary_keeps_current_live_blocker_ahead_of_venue_readiness_copy tests/test_frontend_decision_contract.py::test_strategy_lab_keeps_decision_quality_summary_surfaces -q`
  - `python scripts/bull_4h_pocket_ablation.py --refresh-live-context`
  - `python scripts/hb_parallel_runner.py --fast`
  - browser `/`、`/execution`、`/execution/status`、`/lab`
- **If fail**：若 fast path 再 timeout、或 refresh lane 把 live-specific proxy cohorts 說成 current deployable truth，直接把它升級成 P1 cron-safe governance blocker，禁止 heartbeat 繼續沿用該 artifact 語義。
