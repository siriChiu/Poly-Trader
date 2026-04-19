# ISSUES.md — Current State Only

_最後更新：2026-04-19 23:35:07 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **本輪 heartbeat `--fast` 已完成 end-to-end 閉環**：`Raw=31146 / Features=22564 / Labels=62691`；本輪 collect 實際新增 `+1 raw / +1 features / +7 labels`，資料管線不是 frozen。
- **本輪產品化 patch：bull pocket fast path 已升級成 current-bucket refresh lane**
  - `scripts/bull_4h_pocket_ablation.py --refresh-live-context` 實測 **2.32s** 完成，不再走舊的 20s timeout-only fallback。
  - `scripts/hb_parallel_runner.py --fast` 現在會走 `BULL_4H_POCKET_ABLATION_REFRESH_CMD`，並把 artifact 寫成 `refresh_mode=live_context_only`。
  - `collect_bull_4h_pocket_diagnostics()` 現在會輸出 `production_profile_role=current_bucket_refresh_reference_only`、`support_pathology_summary.blocker_state=current_bucket_refresh_reference_only`，代表 **current live q35 truth 已刷新，但 live-specific proxy cohorts 仍維持 reference-only**。
- **bull pocket current live truth 已對齊最新 probe**
  - `current_live_structure_bucket=CAUTION|structure_quality_caution|q35`
  - `current_live_structure_bucket_rows=1 / minimum_support_rows=50 / gap_to_minimum=49`
  - `support_route_verdict=exact_bucket_present_but_below_minimum`
  - `recommended_patch=core_plus_macro_plus_all_4h`
  - `recommended_patch_status=reference_only_until_exact_support_ready`
- **breaker-first current-live truth 仍是唯一 deployment blocker**
  - `deployment_blocker=circuit_breaker_active`
  - `recent 50 wins=1/50`
  - `required_recent_window_wins=15`
  - `additional_recent_window_wins_needed=14`
  - `streak=10`
  - `allowed_layers=0`
  - `runtime_closure_state=circuit_breaker_active`
- **recent canonical 250 rows 仍是 distribution pathology**
  - `win_rate=0.0040 (1/250)`
  - `dominant_regime=bull(100%)`
  - `avg_simulated_pnl=-0.0095`
  - `avg_simulated_quality=-0.2785`
  - `avg_drawdown_penalty=0.3720`
  - `alerts=['label_imbalance','regime_concentration','regime_shift']`
  - `tail_streak=10x0`
  - top shifts=`feat_eye`、`feat_4h_bias20`、`feat_4h_bb_pct_b`
  - new compressed=`feat_vwap_dev`
- **leaderboard / governance 仍健康**
  - `leaderboard_count=6 / comparable_count=6 / placeholder_count=0`
  - top row=`rule_baseline / core_only / scan_backed_best`
  - `governance_contract=dual_role_governance_active`
  - `current_closure=global_ranking_vs_support_aware_production_split`
- **venue / source blockers 仍開啟**
  - venue：Binance / OKX 仍缺 `live exchange credential`、`order ack lifecycle`、`fill lifecycle`
  - source：`fin_netflow=source_auth_blocked`，根因仍是 `COINGLASS_API_KEY` 缺失
- **本輪驗證已完成**
  - `pytest tests/test_bull_4h_pocket_ablation.py::test_main_refresh_live_context_reuses_reference_profiles_but_clears_live_specific_profiles tests/test_hb_parallel_runner.py::test_run_bull_4h_pocket_ablation_uses_refresh_lane_in_fast_mode tests/test_hb_parallel_runner.py::test_collect_bull_4h_pocket_diagnostics_marks_current_bucket_refresh_reference_only tests/test_hb_parallel_runner.py::test_collect_bull_4h_pocket_diagnostics_marks_semantic_mismatch_reference_only tests/test_hb_parallel_runner.py::test_current_leaderboard_candidate_semantic_signature_prefers_live_probe_bucket_over_stale_bull_artifact tests/test_frontend_decision_contract.py::test_dashboard_execution_summary_keeps_current_live_blocker_ahead_of_venue_readiness_copy tests/test_frontend_decision_contract.py::test_strategy_lab_keeps_decision_quality_summary_surfaces -q` → `7 passed`
  - `python scripts/hb_parallel_runner.py --fast` → `1:22.81` 完成
  - browser 已重查 `/`、`/execution`、`/execution/status`、`/lab`：四個 surface 都能看到 breaker-first truth、q35 `1/50` support、reference-only patch、venue blockers

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
**現況**
- `deployment_blocker=circuit_breaker_active`
- `recent_window=50`
- `current_recent_window_wins=1`
- `required_recent_window_wins=15`
- `additional_recent_window_wins_needed=14`
- `streak=10`
- `allowed_layers=0`
- `runtime_closure_state=circuit_breaker_active`

**風險**
- 若 `/`、`/execution`、`/execution/status`、`/lab`、probe、drilldown、docs 任一 surface 把 q35 support 或 reference-only patch 排到 breaker release math 前面，operator 會失去唯一 current-live blocker 真相。

**下一步**
- 維持 breaker-first truth 在 `/`、`/execution`、`/execution/status`、`/lab`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`issues.json`、`ISSUES.md` 一致。
- 驗證：browser `/`、browser `/execution`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`。

### P0. recent canonical 250 rows remains a distribution pathology
**現況**
- `recent_window=250`
- `win_rate=0.0040`
- `dominant_regime=bull`
- `dominant_regime_share=1.0000`
- `avg_pnl=-0.0095`
- `avg_quality=-0.2785`
- `avg_drawdown_penalty=0.3720`
- `alerts=['label_imbalance','regime_concentration','regime_shift']`
- `tail_streak=10x0`
- top feature shifts=`feat_eye`、`feat_4h_bias20`、`feat_4h_bb_pct_b`
- new compressed=`feat_vwap_dev`

**風險**
- 若 breaker 根因被 generic leaderboard / venue 話題稀釋，heartbeat 會再次偏離真正的 pathological slice。

**下一步**
- 以 recent canonical rows 為主做 feature variance / target-path / gate-path drilldown，不要把 blocker 重述成 generic leaderboard 或 venue 問題。
- 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`。

### P1. bull pocket fast path is now cron-safe, but live-specific cohorts remain reference-only until exact support is ready
**現況**
- fast path 已不再 timeout；`bull_4h_pocket_ablation.py --refresh-live-context` 實測 `2.32s`
- artifact 語義：`refresh_mode=live_context_only`
- live-specific freshness：`live_specific_profiles_fresh=false`
- summary 語義：`current_bucket_refresh_reference_only`
- current live support：`1/50`、`gap_to_minimum=49`

**風險**
- 若後續 surface 把 refresh lane 誤讀成 full rebuild，會再次把 reference-only proxy cohorts 當成可部署 current truth。

**下一步**
- 維持 fast path 走 current-bucket refresh lane；只在 exact support 真正成熟或 full rebuild 成功時，才恢復 live-specific cohort 治理語義。
- 驗證：`python scripts/bull_4h_pocket_ablation.py --refresh-live-context`、`python scripts/hb_parallel_runner.py --fast`、`data/bull_4h_pocket_ablation.json`、`data/heartbeat_fast_summary.json`。

### P1. leaderboard recent-window contract is stable again; keep it stable and cron-safe
**現況**
- `/api/models/leaderboard`: `count=6`、`comparable_count=6`、`placeholder_count=0`
- top row=`rule_baseline / core_only / scan_backed_best`
- governance=`dual_role_governance_active`
- closure=`global_ranking_vs_support_aware_production_split`
- `leaderboard_payload_source=latest_persisted_snapshot`

**風險**
- 若 current-live signature 再被 stale artifact 影響，candidate probe 會重新誤判 cache mismatch，拖慢 fast heartbeat 並重新導致 leaderboard / docs split-brain。

**下一步**
- 維持 live-probe-priority current signature 與 payload freshness arbitration，不讓 stale artifact 重新覆蓋 current q35 truth。
- 驗證：`python scripts/hb_parallel_runner.py --fast`、`data/leaderboard_feature_profile_probe.json`、browser `/lab`。

### P1. venue readiness is still unverified
**現況**
- `binance=config enabled + public-only + metadata OK`
- `okx=config disabled + public-only + metadata OK`
- 缺的 runtime proof：`live exchange credential`、`order ack lifecycle`、`fill lifecycle`

**風險**
- breaker 未來解除後，若 venue blockers 被弱化成摘要字串或完全消失，使用者會被誤導成已可實盤。

**下一步**
- 維持 per-venue blockers 在 `/`、`/execution`、`/execution/status`、`/lab`、`ISSUES.md` 可見，但永遠排在 breaker-first current blocker 之後。
- 驗證：browser `/execution`、browser `/execution/status`、browser `/lab`、`data/execution_metadata_smoke.json`。

### P1. fin_netflow source_auth_blocked remains open
**現況**
- `fin_netflow=source_auth_blocked`
- `latest_status=auth_missing`
- blocker 根因：`COINGLASS_API_KEY is missing`
- `forward_archive_rows=2617`
- `archive_window_coverage_pct=0.0%`

**風險**
- Feature coverage 會持續呈現假前進：archive 在長，但 live fetch 仍失敗，資料實際不可用。

**下一步**
- 配置 `COINGLASS_API_KEY`，先讓 ETF flow source 從 `auth_missing` 轉成成功 snapshot，再評估是否需要歷史 backfill。
- 驗證：`data/execution_metadata_smoke.json`、`/api/features/coverage`、下輪 heartbeat source blockers。

---

## Not Issues
- **data pipeline frozen**：不是；本輪 collect 實際新增 `+1 raw / +1 features / +7 labels`。
- **bull pocket fast-mode timeout**：不是 current issue；fast heartbeat 已改走 `--refresh-live-context` current-bucket refresh lane。
- **stale bull artifact 汙染 current q35 truth**：不是 current issue；目前 current live truth 已由 latest probe + refresh lane 提供，live-specific cohorts 僅保留 reference-only。
- **leaderboard placeholder-only / split-brain**：不是 current issue；目前 `count=6 / comparable_count=6 / placeholder_count=0`，治理語義穩定。

---

## Current Priority
1. **維持 breaker-first truth across `/` / `/execution` / `/execution/status` / `/lab` / probe / drilldown / docs**
2. **把 q35 `1/50 + exact_bucket_present_but_below_minimum + reference_only_until_exact_support_ready` 固定成所有 surface 的同一個 machine-read truth**
3. **守住 bull pocket current-bucket refresh lane：fast path 保持 cron-safe，但不可誤升級成 full live-specific truth**
4. **持續鑽 recent canonical 250-row pathology，而不是 generic 化 blocker**
5. **持續保留 per-venue blockers 與 CoinGlass auth blocker，可見直到真實 closure**
