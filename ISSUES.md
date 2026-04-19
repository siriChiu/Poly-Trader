# ISSUES.md — Current State Only

_最後更新：2026-04-19 13:57 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **fast heartbeat + collect 成功**：`Raw=31102 (+1) / Features=22520 (+1) / Labels=62610 (+9)`；`240m / 1440m` freshness 仍屬 lookahead 的 expected lag，資料管線不是 frozen。
- **canonical current-live 唯一 deployment blocker 仍是 circuit breaker**：`deployment_blocker=circuit_breaker_active`、`streak=256`、`recent 50 wins=0/50`、`additional_recent_window_wins_needed=15`、`allowed_layers=0`、`runtime_closure_state=circuit_breaker_active`。
- **current live bucket 維持 `CAUTION|base_caution_regime_or_bias|q15`**：`regime=chop`、`gate=CAUTION`、`entry_quality=0.3792 (D)`；exact support 仍是 **0/50**，`support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`、`gap_to_minimum=50`、`support_progress.status=stalled_under_minimum`、`escalate_to_blocker=true`。
- **recent canonical 250 rows 仍是 distribution pathology**：`win_rate=0.0000`、`dominant_regime=bull(100%)`、`avg_pnl=-0.0104`、`avg_quality=-0.2843`、`tail_streak=250x0`；主 shifts 為 `feat_4h_bb_pct_b`、`feat_4h_bias20`、`feat_4h_rsi14`。
- **本輪產品化 patch 已修復 non-bull live row 的 patch visibility regression**：`data/live_predict_probe.json` 與 `data/live_decision_quality_drilldown.json` 現在都重新輸出 `recommended_patch={status=reference_only_until_exact_support_ready, recommended_profile=core_plus_macro, spillover_regime_gate=bull|BLOCK, reference_patch_scope=bull|CAUTION, reference_source=bull_4h_pocket_ablation.bull_collapse_q35}`，不再把 reference-only patch 掉成 `null`。
- **Strategy Lab `/lab` 已重新驗證 exact-vs-spillover + patch card 可見**：browser 顯示 breaker-first current live blocker、venue blockers、`bull|BLOCK` spillover，且 patch 卡明確標示 `core_plus_macro` 只是 `reference-only`；console 無 JS exception。
- **leaderboard governance 仍是健康雙角色 split，不是 stale drift**：`global_profile=core_only`、`train_selected_profile=core_plus_macro`、`governance_contract=dual_role_governance_active`；但 `leaderboard_count=0`，Strategy Lab 仍屬 placeholder-only model ranking。
- **venue readiness 仍只有 public metadata proof**：`binance=config enabled + public-only`、`okx=config disabled + public-only`；`data/execution_metadata_smoke.json` 新鮮，但仍缺 `live exchange credential / order ack lifecycle / fill lifecycle`。
- **fin_netflow 仍是 source_auth_blocked**：`COINGLASS_API_KEY` 缺失；forward archive 持續前進，但 `archive_window_coverage_pct=0.0%`。

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
**現況**
- `deployment_blocker=circuit_breaker_active`
- `recent_window=50`
- `current_recent_window_wins=0`
- `required_recent_window_wins=15`
- `additional_recent_window_wins_needed=15`
- `streak=256`
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
- `dominant_regime=bull(100%)`
- `alerts=['constant_target','regime_concentration','regime_shift']`
- `avg_pnl=-0.0104`
- `avg_quality=-0.2843`
- `tail_streak=250x0`
- top feature shifts：`feat_4h_bb_pct_b`、`feat_4h_bias20`、`feat_4h_rsi14`

**風險**
- 這個 recent canonical tail 仍是 breaker 的根因；若只看 broader history、profile split 或 venue blockers，會掩蓋 current pathological slice。

**下一步**
- 以 recent canonical rows 為主做 feature variance / distinct-count / target-path drilldown，避免把 blocker 誤寫成 generic profile parity。
- 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`。

### P1. q15 exact support is still missing under breaker (0/50)
**現況**
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`
- `live_current_structure_bucket_rows=0`
- `minimum_support_rows=50`
- `gap_to_minimum=50`
- `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`
- `support_governance_route=exact_live_lane_proxy_available`
- `support_progress.status=stalled_under_minimum`
- `support_progress.escalate_to_blocker=true`

**風險**
- 如果 probe / docs / UI 把 `0/50 + missing_exact_lane_proxy_only + stalled_under_minimum` 藏掉，operator 會誤判 q15 support 已接近 closure。

**下一步**
- 維持 `0/50 + exact_bucket_missing_exact_lane_proxy_only + stalled_under_minimum + escalate_to_blocker=true` 在 probe / API / UI / docs / `issues.json` 一致 machine-read。
- 驗證：`python scripts/hb_q15_support_audit.py`、`python scripts/hb_predict_probe.py`、browser `/lab`、browser `/execution/status`。

### P1. support-aware `core_plus_macro` patch must stay visible but reference-only
**現況**
- `actual_live_spillover_scope=bull|BLOCK`
- `reference_patch_scope=bull|CAUTION`
- `recommended_patch=core_plus_macro`
- `recommended_patch_status=reference_only_until_exact_support_ready`
- `reference_source=bull_4h_pocket_ablation.bull_collapse_q35`
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`
- `current_live_structure_bucket_rows=0`
- `minimum_support_rows=50`
- `gap_to_minimum=50`

**風險**
- 若 `recommended_patch` 再次在 non-bull live row 掉成 `null`，operator 會只看到 toxic spillover，卻失去唯一可追蹤的 support-aware 治理方向；若把它升級成 deployable patch，又會誤導成已可放行 runtime。

**下一步**
- 維持 `recommended_patch` 在 `/api/status`、`/lab`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`issues.json`、`ISSUES.md` 一致；只允許 `reference-only`，直到 exact support 達標。
- 驗證：`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、browser `/lab`、`pytest tests/test_live_pathology_summary.py tests/test_hb_predict_probe.py -q`。

### P1. venue readiness is still unverified
**現況**
- `binance`: `config enabled + public-only`
- `okx`: `config disabled + public-only`
- metadata smoke：`fresh / healthy`
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
- `forward_archive_rows=2573`
- `archive_window_coverage_pct=0.0%`

**風險**
- Feature coverage 會持續呈現假前進：archive 在長，但 live fetch 仍失敗，資料實際不可用。

**下一步**
- 配置 `COINGLASS_API_KEY`，先讓 ETF flow source 從 `auth_missing` 轉成成功 snapshot，再評估是否需要歷史 backfill。
- 驗證：`data/heartbeat_fast_summary.json` source blockers、`/api/features/coverage`。

### P1. model stability and comparable leaderboard rows still need work
**現況**
- `cv_accuracy=60.8%`
- `cv_std=12.5pp`
- `cv_worst=44.5%`
- `global_profile=core_only`
- `train_selected_profile=core_plus_macro`
- `leaderboard_count=0`（placeholder-only）

**風險**
- 即使 breaker 未來解除，若 profile robustness 沒改善、leaderboard 仍無 comparable rows，runtime 與 Strategy Lab 都會缺乏可信 deployment ranking。

**下一步**
- 優先比較 shrinkage / support-aware profiles 與 current bucket robustness；同時維持 placeholder-only warning，不讓空榜被誤讀成 deployment ranking。
- 驗證：`data/leaderboard_feature_profile_probe.json`、browser `/lab`、`python scripts/hb_leaderboard_candidate_probe.py`。

---

## Not Issues
- **data pipeline frozen**：不是；本輪 collect 實際新增 `+1 raw / +1 features / +9 labels`。
- **240m / 1440m freshness lag**：不是 blocker；目前仍屬 lookahead horizon 的 expected lag。
- **non-bull live row 的 reference-only patch 消失**：不是 current regression；本輪已修復，`live_predict_probe.json` / `live_decision_quality_drilldown.json` / Strategy Lab patch 卡都已重新可見。

---

## Current Priority
1. **維持 breaker-first truth，讓 current-live blocker 始終是 release math，而不是 q15 / venue / spillover 雜訊**
2. **把 recent canonical 250 rows pathology 當成 breaker 根因持續鑽深，不被 broader history 稀釋**
3. **把 q15 `0/50` 與 reference-only `core_plus_macro` patch 一起維持 machine-read，可見且不可被升級成 deployable**
4. **持續保留 per-venue blockers 與 metadata truth，可見直到 credentials / ack / fill 真正 closure，同時解除 `fin_netflow` auth blocker**
