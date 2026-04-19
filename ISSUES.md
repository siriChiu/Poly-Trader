# ISSUES.md — Current State Only

_最後更新：2026-04-19 22:18:37 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **本輪 heartbeat `--fast` 已完成 end-to-end 閉環**：`Raw=31144 (+1) / Features=22562 (+1) / Labels=62676 (+2)`；active horizons `240m / 1440m` freshness 都是 `expected_horizon_lag`，資料管線不是 frozen。
- **本輪產品化 patch #1：leaderboard current-live signature 改成以 live probe 為主**
  - `scripts/hb_parallel_runner.py::_current_leaderboard_candidate_semantic_signature()` 現在優先讀 `data/live_predict_probe.json` 的 `current_live_structure_bucket / rows / support_governance_route / minimum_support_rows`。
  - 這修掉了舊的 `bull_4h_pocket_ablation.json` q15/chop live_context 把實際 bull/q35 current truth 誤判成 cache mismatch 的 bug；`hb_leaderboard_candidate_probe` 不再因 stale bull artifact 被迫重跑並拖慢 fast heartbeat。
- **本輪產品化 patch #2：bull pocket timeout fallback 改成 reference-only，不再假裝 stale q15 truth 是 current live**
  - 若 `bull_4h_pocket_ablation.py` 在 fast-mode 20s budget 內逾時，且現有 artifact live signature 與最新 `live_predict_probe` 不一致，`collect_bull_4h_pocket_diagnostics()` 現在會標成 `reference_only_stale_live_context`。
  - 這代表 heartbeat 會保留 `bull_all / bull_collapse_q35` 的 reference-only patch 可見性，但不再把 stale q15/chop live-specific proxy cohorts 說成 current bull/q35 truth。
- **驗證證據已齊**
  - `pytest tests/test_hb_parallel_runner.py::test_current_leaderboard_candidate_semantic_signature_prefers_live_probe_bucket_over_stale_bull_artifact tests/test_hb_parallel_runner.py::test_collect_bull_4h_pocket_diagnostics_marks_semantic_mismatch_reference_only tests/test_hb_parallel_runner.py::test_collect_bull_4h_pocket_diagnostics_reads_live_bucket_support tests/test_hb_parallel_runner.py::test_leaderboard_candidate_cache_hit_uses_semantic_alignment_signature -q` → `4 passed`
  - `python scripts/hb_parallel_runner.py --fast` → 完成，並寫出 `data/heartbeat_fast_summary.json`
  - browser `/lab`：顯示 `current live blocker = circuit_breaker_active`、`support 1/50`、`recommended patch = core_plus_macro (reference-only)`、venue blockers 可見
  - browser `/execution/status`：顯示 `deployment blocker = circuit_breaker_active`、`support 1/50`、`current bucket = CAUTION|structure_quality_caution|q35`、venue blockers 仍可見
- **canonical current-live blocker 仍只有 circuit breaker**：`deployment_blocker=circuit_breaker_active`、`recent 50 wins=1/50`、`streak=3`、`allowed_layers=0`、`runtime_closure_state=circuit_breaker_active`。
- **current live support truth 仍是 q35 under-minimum**：`current_live_structure_bucket=CAUTION|structure_quality_caution|q35`、`current_live_structure_bucket_rows=1`、`minimum_support_rows=50`、`gap_to_minimum=49`、`support_route_verdict=exact_bucket_present_but_below_minimum`、`recommended_patch=core_plus_macro`、`recommended_patch_status=reference_only_until_exact_support_ready`。
- **recent canonical 250 rows 仍是 distribution pathology**：`win_rate=0.0040`、`dominant_regime=bull(100%)`、`avg_pnl=-0.0099`、`avg_quality=-0.2813`、`avg_drawdown_penalty=0.3739`、`adverse_streak=246x0`；top shifts=`feat_4h_bb_pct_b`、`feat_4h_bias20`、`feat_eye`；new compressed=`feat_vwap_dev`。
- **leaderboard current truth 仍健康**：`count=6 / comparable_count=6 / placeholder_count=0`；top row=`rule_baseline / core_only / scan_backed_best`；`governance=dual_role_governance_active`、`closure=global_ranking_vs_support_aware_production_split`、`payload_source=latest_persisted_snapshot`。
- **bull pocket live-specific cohorts 仍未能在 fast mode 20s 內重建**：本輪 `bull_4h_pocket_ablation.py` 仍 `TIMEOUT after 20s`，但 current live q35 truth 已不再被舊 q15 artifact 污染。
- **venue / source blockers 仍未 closure**：Binance / OKX 仍缺 `live exchange credential / order ack lifecycle / fill lifecycle`；`fin_netflow` 仍是 `source_auth_blocked`，根因是 `COINGLASS_API_KEY` 缺失。

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
**現況**
- `deployment_blocker=circuit_breaker_active`
- `recent_window=50`
- `current_recent_window_wins=1`
- `required_recent_window_wins=15`
- `additional_recent_window_wins_needed=14`
- `streak=3`
- `allowed_layers=0`
- `runtime_closure_state=circuit_breaker_active`

**風險**
- 若 `/`、`/execution/status`、`/lab`、probe、drilldown、docs 任一 surface 把 q35 support 或 reference-only patch 排到 breaker release math 前面，operator 會失去唯一 current-live blocker 真相。

**下一步**
- 維持 breaker-first truth 在 `/`、`/execution/status`、`/lab`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`issues.json`、`ISSUES.md` 一致。
- 驗證：browser `/lab`、browser `/execution/status`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`。

### P0. recent canonical 250 rows remains a distribution pathology
**現況**
- `recent_window=250`
- `win_rate=0.0040`
- `dominant_regime=bull`
- `dominant_regime_share=1.0000`
- `avg_pnl=-0.0099`
- `avg_quality=-0.2813`
- `avg_drawdown_penalty=0.3739`
- `alerts=['label_imbalance','regime_concentration','regime_shift']`
- `adverse_streak=246x0`
- top feature shifts=`feat_4h_bb_pct_b`、`feat_4h_bias20`、`feat_eye`
- new compressed=`feat_vwap_dev`

**風險**
- 若 breaker 根因被 generic leaderboard / venue 話題稀釋，heartbeat 會再次偏離真正的 pathological slice。

**下一步**
- 以 recent canonical rows 為主做 feature variance / target-path / gate-path drilldown，不要把 blocker 重述成 generic leaderboard 或 venue 問題。
- 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`。

### P1. bull pocket fast-mode rebuild is still over budget; current live only has reference-only fallback
**現況**
- `bull_4h_pocket_ablation.py` 在 fast mode 仍 `TIMEOUT after 20s`
- 本輪 fallback 狀態：`reference_only_stale_live_context`
- current live truth 已由 probe 提供：`bull / CAUTION / q35 / 1 row`
- reference-only patch 仍可見：`bull_collapse_q35 -> core_plus_macro`

**風險**
- 若後續 heartbeat 再把 stale bull artifact 當成 current live proxy truth，會重新污染 q35 support / governance / leaderboard 判讀。

**下一步**
- 讓 bull pocket 在 fast path 內要嘛完成重建，要嘛有更便宜的 current-bucket refresh lane；在此之前，維持 `reference_only_stale_live_context` 明示 fallback。
- 驗證：`python scripts/hb_parallel_runner.py --fast`、`data/heartbeat_fast_summary.json`、`data/leaderboard_feature_profile_probe.json`。

### P1. leaderboard recent-window contract is stable again; keep it stable and cron-safe
**現況**
- `/api/models/leaderboard`: `count=6`、`comparable_count=6`、`placeholder_count=0`
- top row=`rule_baseline / core_only / scan_backed_best`
- governance=`dual_role_governance_active`
- closure=`global_ranking_vs_support_aware_production_split`
- `leaderboard_payload_source=latest_persisted_snapshot`

**風險**
- 若 current-live signature 再被 stale bull artifact 影響，candidate probe 會重新誤判 cache mismatch，拖慢 fast heartbeat 並重新導致 leaderboard / docs split-brain。

**下一步**
- 維持 live-probe-priority current signature 與 payload freshness arbitration，不讓 stale bull artifact 重新覆蓋 current q35 truth。
- 驗證：`python scripts/hb_parallel_runner.py --fast`、`pytest tests/test_hb_parallel_runner.py -q`、browser `/lab`。

### P1. venue readiness is still unverified
**現況**
- `binance=config enabled + public-only + metadata OK`
- `okx=config disabled + public-only + metadata OK`
- 缺的 runtime proof：`live exchange credential`、`order ack lifecycle`、`fill lifecycle`

**風險**
- breaker 未來解除後，若 venue blockers 被弱化成摘要字串或完全消失，使用者會被誤導成已可實盤。

**下一步**
- 維持 per-venue blockers 在 `/execution/status`、`/lab`、`ISSUES.md` 可見，但永遠排在 breaker-first current blocker 之後。
- 驗證：browser `/execution/status`、browser `/lab`、`data/execution_metadata_smoke.json`。

### P1. fin_netflow source_auth_blocked remains open
**現況**
- `fin_netflow=source_auth_blocked`
- `latest_status=auth_missing`
- blocker 根因：`COINGLASS_API_KEY is missing`
- `forward_archive_rows=2615`
- `archive_window_coverage_pct=0.0%`

**風險**
- Feature coverage 會持續呈現假前進：archive 在長，但 live fetch 仍失敗，資料實際不可用。

**下一步**
- 配置 `COINGLASS_API_KEY`，先讓 ETF flow source 從 `auth_missing` 轉成成功 snapshot，再評估是否需要歷史 backfill。
- 驗證：`data/execution_metadata_smoke.json`、`/api/features/coverage`、下輪 heartbeat source blockers。

---

## Not Issues
- **data pipeline frozen**：不是；本輪 collect 實際新增 `+1 raw / +1 features / +2 labels`，且 active horizons freshness 仍屬 expected lag。
- **leaderboard split-brain**：不是 current issue；leaderboard probe、`/lab`、`/execution/status` 目前都對齊 bull/q35 current truth 與 dual-role governance。
- **stale bull q15 artifact 仍污染 current live q35 truth**：不是 current issue；本輪已改成 `live-probe-priority signature + reference_only_stale_live_context`，不再把舊 q15/chop artifact 當成 current live proxy truth。
- **reference-only patch 消失**：不是 current issue；`core_plus_macro` 仍在 probe / drilldown / `/lab` 可見，且 status 正確為 `reference_only_until_exact_support_ready`。

---

## Current Priority
1. **維持 breaker-first truth across `/` / `/execution/status` / `/lab` / probe / drilldown / docs**
2. **把 q35 `1/50 + exact_bucket_present_but_below_minimum + reference_only_until_exact_support_ready` 固定成所有 surface 的同一個 machine-read truth**
3. **讓 bull pocket fast-path 不再 timeout 或至少有 current-bucket refresh lane；在此之前嚴格維持 reference-only fallback**
4. **守住 leaderboard recent-window contract：candidate probe 不再被 stale bull artifact 誤導成 cache mismatch**
5. **持續保留 per-venue blockers 與 CoinGlass auth blocker，可見直到真實 closure**
