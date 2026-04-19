# ISSUES.md — Current State Only

_最後更新：2026-04-19 18:15:53 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **本輪 heartbeat #20260419ad 已完成 fast collect + current-state overwrite 閉環**：`Raw=31126 (+1) / Features=22544 (+1) / Labels=62639 (+2)`；active horizons `240m / 1440m` freshness 仍是 `expected_horizon_lag`，資料管線不是 frozen。
- **本輪產品化 patch 已落地：q15 runtime resync 會明確區分真正原因**：`scripts/hb_parallel_runner.py` 新增 machine-readable `q15_runtime_resync.reason` 與對應 operator 訊息；當 breaker 下只是 `support_route_verdict / support_governance_route / support_progress` 漂移時，console 與 `data/heartbeat_20260419ad_summary.json` 會標示 `support_truth_changed_under_breaker`，不再把 under-breaker support truth drift 誤報成 `patch-ready`。
- **canonical current-live 唯一 deployment blocker 仍是 circuit breaker**：`deployment_blocker=circuit_breaker_active`、`streak=266`、`recent 50 wins=0/50`、`additional_recent_window_wins_needed=15`、`allowed_layers=0`、`runtime_closure_state=circuit_breaker_active`。
- **current live bucket 維持 `CAUTION|base_caution_regime_or_bias|q15`**：`regime=chop`、`gate=CAUTION`、`entry_quality=0.4833 (D)`；exact support 仍是 **0/50**，`support_route_verdict=exact_bucket_missing_proxy_reference_only`、`support_governance_route=exact_live_bucket_proxy_available`、`support_progress.status=stalled_under_minimum`、`gap_to_minimum=50`、`remaining_gap_to_floor=0.0667`、`best_single_component=feat_4h_bias50`。
- **recent canonical 250 rows 仍是 distribution pathology**：`win_rate=0.0000`、`dominant_regime=bull(100%)`、`avg_pnl=-0.0103`、`avg_quality=-0.2869`、`avg_drawdown_penalty=0.3773`、`tail_streak=250x0`；主 shifts 為 `feat_4h_bb_pct_b`、`feat_4h_bias20`、`feat_4h_rsi14`，新增 `feat_vwap_dev` 壓縮。
- **support-aware patch 仍是 reference-only**：`recommended_patch=core_plus_macro`、`recommended_patch_status=reference_only_until_exact_support_ready`、`spillover_regime_gate=bull|CAUTION`、`spillover_rows=199`、`reference_source=live_scope_spillover`。
- **canonical leaderboard / Strategy Lab contract 仍守住**：`/api/models/leaderboard` 為 `count=6 / comparable_count=6 / placeholder_count=0`，`evaluation_fold_window=latest_bounded_walk_forward`、`evaluation_max_folds=4`；top row 仍是 `rule_baseline / core_only / scan_backed_best`；browser `/lab` 應繼續明示「排行榜回測固定使用最近兩年」。
- **venue readiness 仍只有 metadata proof**：`binance=config enabled + public-only + metadata OK`、`okx=config disabled + public-only + metadata OK`；`live exchange credential / order ack lifecycle / fill lifecycle` 仍未驗證。
- **fin_netflow 仍是 source_auth_blocked**：`COINGLASS_API_KEY` 缺失；forward archive 已累積 `2597` snapshots，但 `archive_window_coverage_pct=0.0%`。
- **驗證證據已齊**：`pytest tests/test_hb_parallel_runner.py tests/test_auto_propose_fixes.py -q` = `89 passed`；`python scripts/hb_parallel_runner.py --fast --hb 20260419ad` 通過，且 summary 已 machine-read `q15_runtime_resync.reason=support_truth_changed_under_breaker`。

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
**現況**
- `deployment_blocker=circuit_breaker_active`
- `streak=266`
- `recent_window=50`
- `current_recent_window_wins=0`
- `required_recent_window_wins=15`
- `additional_recent_window_wins_needed=15`
- `allowed_layers=0`
- `runtime_closure_state=circuit_breaker_active`

**風險**
- 若任何 surface 再把 q15 support、venue blockers 或 spillover artifact 排到 breaker 前面，operator 會失去唯一 current-live blocker 真相。

**下一步**
- 維持 breaker-first truth 在 `/execution`、`/execution/status`、`/lab`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`issues.json`、`ISSUES.md` 一致。
- 驗證：browser `/execution`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`。

### P0. recent canonical 250 rows remains a distribution pathology
**現況**
- `recent_window=250`
- `win_rate=0.0000`
- `dominant_regime=bull`
- `dominant_regime_share=1.0000`
- `avg_pnl=-0.0103`
- `avg_quality=-0.2869`
- `avg_drawdown_penalty=0.3773`
- `alerts=['constant_target','regime_concentration','regime_shift']`
- `tail_streak=250x0`
- top feature shifts：`feat_4h_bb_pct_b`、`feat_4h_bias20`、`feat_4h_rsi14`
- new compressed：`feat_vwap_dev`

**風險**
- 若 breaker 根因被 broader history、leaderboard 勝負或 venue 診斷稀釋，修復會再次偏離 pathological slice 本身。

**下一步**
- 以 recent canonical rows 為主做 feature variance / distinct-count / target-path drilldown，避免把 blocker 誤寫成 generic leaderboard 或 venue 議題。
- 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`。

### P1. q15 exact support remains under minimum under breaker (0/50)
**現況**
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`
- `live_current_structure_bucket_rows=0`
- `minimum_support_rows=50`
- `gap_to_minimum=50`
- `support_route_verdict=exact_bucket_missing_proxy_reference_only`
- `support_governance_route=exact_live_bucket_proxy_available`
- `support_progress.status=stalled_under_minimum`
- `remaining_gap_to_floor=0.0667`
- `best_single_component=feat_4h_bias50`
- `governance_contract=dual_role_governance_active`
- `q15_runtime_resync.reason=support_truth_changed_under_breaker`

**風險**
- 若 probe / docs / UI 再退回舊的 `exact_bucket_missing_exact_lane_proxy_only`，或把 under-breaker resync 說成 `patch-ready`，operator 會誤判 q15 support lane 與治理路徑。

**下一步**
- 維持 `0/50 + exact_bucket_missing_proxy_reference_only + stalled_under_minimum + gap_to_minimum=50` 與 `q15_runtime_resync.reason` 在 probe / API / UI / docs / summary 一致 machine-read。
- 驗證：`python scripts/hb_q15_support_audit.py`、`python scripts/hb_predict_probe.py`、`python scripts/hb_parallel_runner.py --fast --hb <run>`、browser `/lab`、browser `/execution/status`。

### P1. support-aware `core_plus_macro` patch must stay visible but reference-only
**現況**
- `recommended_patch=core_plus_macro`
- `recommended_patch_status=reference_only_until_exact_support_ready`
- `actual_live_spillover_scope=bull|CAUTION`
- `spillover_rows=199`
- `reference_source=live_scope_spillover`
- `support_route_verdict=exact_bucket_missing_proxy_reference_only`
- `gap_to_minimum=50`

**風險**
- 若 `recommended_patch` 消失或被升級成 deployable，operator 會失去唯一 support-aware 治理方向，或被誤導成 runtime 已可放行。

**下一步**
- 維持 `recommended_patch` 在 `/api/status`、`/lab`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`issues.json`、`ISSUES.md` 一致；只允許 `reference-only`，直到 exact support 達標。
- 驗證：`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、browser `/lab`。

### P1. leaderboard recent-window contract is delivered; keep it stable and cron-safe
**現況**
- `/api/models/leaderboard`: `count=6`、`comparable_count=6`、`placeholder_count=0`
- `evaluation_fold_window=latest_bounded_walk_forward`
- `evaluation_max_folds=4`
- top model（目前 API）=`rule_baseline / core_only / scan_backed_best`
- governance state=`dual_role_governance_active`（global winner=`core_only`，train support-aware profile=`core_plus_macro`）
- browser `/lab` 已顯示最近兩年回測 policy，且可讀到 `circuit_breaker_active`

**風險**
- 若 payload 回退到 placeholder-only、profile governance drift、或排行榜重算超出 cron 預算，canonical model surface 會再次退回不可比較狀態。

**下一步**
- 維持 `/api/models/leaderboard`、Strategy Lab 工作區與模型排行都使用 latest bounded walk-forward + 兩年預設區間，不可回退成 placeholder-only 或短窗過擬合。
- 驗證：browser `/lab`、`curl http://127.0.0.1:8000/api/models/leaderboard`、`pytest tests/test_model_leaderboard.py tests/test_strategy_lab.py tests/test_frontend_decision_contract.py -q`。

### P1. venue readiness is still unverified
**現況**
- `binance`: `config enabled + public-only + metadata OK`
- `okx`: `config disabled + public-only + metadata OK`
- 缺的 runtime proof：`live exchange credential`、`order ack lifecycle`、`fill lifecycle`

**風險**
- breaker 未來解除後，若 venue blockers 被弱化成摘要字串或完全消失，使用者會被誤導成已可實盤。

**下一步**
- 持續保留 per-venue blockers，但它們必須永遠位於 breaker-first current blocker 之後。
- 驗證：browser `/execution`、browser `/execution/status`、browser `/lab`、`data/execution_metadata_smoke.json`。

### P1. fin_netflow source_auth_blocked remains open
**現況**
- `fin_netflow=source_auth_blocked`
- `latest_status=auth_missing`
- blocker 根因：`COINGLASS_API_KEY is missing`
- `forward_archive_rows=2597`
- `archive_window_coverage_pct=0.0%`

**風險**
- Feature coverage 會持續呈現假前進：archive 在長，但 live fetch 仍失敗，資料實際不可用。

**下一步**
- 配置 `COINGLASS_API_KEY`，先讓 ETF flow source 從 `auth_missing` 轉成成功 snapshot，再評估是否需要歷史 backfill。
- 驗證：`data/execution_metadata_smoke.json`、`/api/features/coverage`、下輪 heartbeat source blockers。

---

## Not Issues
- **data pipeline frozen**：不是；本輪 collect 實際新增 `+1 raw / +1 features / +2 labels`，且 active horizons freshness 仍屬 expected lag。
- **q15 under-breaker resync 被誤報成 patch-ready**：不是 current issue；`hb_parallel_runner.py` 已 machine-read `q15_runtime_resync.reason` 並修正文案。
- **canonical model leaderboard placeholder-only**：不是 current issue；`/api/models/leaderboard` 維持 `6` 筆 comparable rows。
- **Strategy Lab 最近兩年 policy 消失**：不是 current regression；browser `/lab` 應保留「排行榜回測固定使用最近兩年」。

---

## Current Priority
1. **維持 breaker-first truth，讓 current-live blocker 始終是 release math，而不是 q15 / venue / spillover 雜訊**
2. **把 recent canonical 250 rows pathology 當成 breaker 根因持續鑽深，不被 broader history 或 leaderboard 勝負稀釋**
3. **把 q15 `0/50`、`support_route_verdict` 與 `q15_runtime_resync.reason` 一起維持 machine-read，避免 under-breaker 語義再 drift**
4. **守住 canonical leaderboard comparable rows、dual-role governance、以及 Strategy Lab 兩年回測 contract**
5. **持續保留 per-venue blockers 與 source auth blockers，可見直到 credentials / ack / fill / CoinGlass auth 真正 closure**
