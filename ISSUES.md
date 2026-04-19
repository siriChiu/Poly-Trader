# ISSUES.md — Current State Only

_最後更新：2026-04-19 13:31 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **fast heartbeat `#20260419t` + collect 成功**：`Raw=31101 (+1) / Features=22519 (+1) / Labels=62601 (+1)`；`240m / 1440m` freshness 仍屬 lookahead 的 expected lag，資料管線不是 frozen。
- **canonical current-live 唯一 deployment blocker 仍是 circuit breaker**：`deployment_blocker=circuit_breaker_active`、`streak=248`、`recent 50 wins=0/50`、`additional_recent_window_wins_needed=15`、`allowed_layers=0`、`runtime_closure_state=circuit_breaker_active`。
- **current live bucket 維持 `CAUTION|base_caution_regime_or_bias|q15`**：`regime=chop`、`gate=CAUTION`、`entry_quality=0.3784 (D)`；exact support 目前 **0/50**，`support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`、`gap_to_minimum=50`、`support_progress.status=stalled_under_minimum`、`escalate_to_blocker=true`。
- **recent canonical 100 rows 仍是 distribution pathology**：`win_rate=0.0000`、`dominant_regime=bull(100%)`、`avg_pnl=-0.0094`、`avg_quality=-0.2869`、`tail_streak=100x0`；主 shifts 仍是 `feat_4h_vol_ratio`、`feat_mind`、`feat_4h_bb_pct_b`。
- **current live exact lane 為 0 rows，但 broader spillover 仍是 bull toxic pocket**：`entry_quality_label` 寬 scope 仍有 `bull|BLOCK` 199 rows、`WR=0.0%`、`quality=-0.2852`；當前 current-live 不能把 bull pocket artifact 誤讀成現場可部署 patch。
- **本輪產品化 patch 已驗證**：`scripts/hb_parallel_runner.py` 現在會在 current live `regime != bull` 時把 `bull_4h_pocket_ablation` 當成 reference-only cache reuse；`data/heartbeat_20260419t_summary.json` 已記錄 `serial_results.bull_4h_pocket_ablation.cached=true` 與 `cache_reason=bounded_label_drift_non_bull_live_regime_reference_only_bull_4h_pocket_artifact_reused`，避免快心跳在錯 lane 上無謂重跑 bull-only 治理工作。
- **operator surfaces 已重新驗證 breaker-first + venue blockers 可見**：browser `/lab`、`/execution`、`/execution/status` 都同時顯示 `current live blocker=circuit_breaker_active` 與 `venue blockers`；console 無 JS exception。
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
- `streak=248`
- `allowed_layers=0`
- `runtime_closure_state=circuit_breaker_active`

**風險**
- 若任何 surface 再把 q15 support、venue blockers 或歷史 bull artifact 排到 breaker 前面，operator 會失去唯一 current-live blocker 真相。

**下一步**
- 維持 breaker-first truth 在 `/execution`、`/execution/status`、`/lab`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`issues.json`、`ISSUES.md` 一致。
- 驗證：browser `/execution`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`。

### P0. recent canonical window remains a distribution pathology
**現況**
- `recent_window=100`
- `win_rate=0.0000`
- `dominant_regime=bull(100%)`
- `alerts=['constant_target','regime_concentration','regime_shift']`
- `avg_pnl=-0.0094`
- `avg_quality=-0.2869`
- `tail_streak=100x0`
- top feature shifts：`feat_4h_vol_ratio`、`feat_mind`、`feat_4h_bb_pct_b`

**風險**
- 這個 recent canonical tail 仍是 breaker 的根因；若只看 broader history、profile split 或 venue blockers，會掩蓋 current pathological slice。

**下一步**
- 以 recent canonical rows 為主做 variance / distinct / target-path drilldown，避免把 blocker 誤寫成 generic profile parity。
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

### P1. current live chop q15 must stay separated from bull toxic spillover
**現況**
- current live：`regime=chop`、`gate=CAUTION`、`bucket=CAUTION|base_caution_regime_or_bias|q15`
- exact live lane：`rows=0`
- broader `entry_quality_label` spillover：`bull|BLOCK` 199 rows、`WR=0.0%`、`quality=-0.2852`
- `live_decision_quality_drilldown.recommended_patch=None`
- bull pocket artifact：僅可作 **reference-only** 背景治理，不是 current-live patch
- fast heartbeat：`serial_results.bull_4h_pocket_ablation.cached=true`、`reference_only=true`

**風險**
- 若 UI / docs / issues 再把 `bull|BLOCK` spillover 或 bull pocket artifact 誤寫成 current-live patch，會把非當前 lane 的研究結論誤升級成部署建議。

**下一步**
- 保持 current live chop q15、broader bull spillover、bull pocket reference artifact 三者分離；non-bull live row 時 bull pocket 只能 reference-only。
- 驗證：`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、browser `/lab`、browser `/execution/status`、`data/heartbeat_20260419t_summary.json` 的 `serial_results.bull_4h_pocket_ablation`。

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
- `forward_archive_rows=2572`
- `archive_window_coverage_pct=0.0%`

**風險**
- Feature coverage 會持續呈現假前進：archive 在長，但 live fetch 仍失敗，資料實際不可用。

**下一步**
- 配置 `COINGLASS_API_KEY`，先讓 ETF flow source 從 `auth_missing` 轉成成功 snapshot，再評估是否需要歷史 backfill。
- 驗證：`data/heartbeat_20260419t_summary.json` source blockers、`/api/features/coverage`。

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
- 優先比較 shrinkage / support-aware profiles 與 current bucket robustness；同時維持 placeholder-only warning，不讓 `#1` 被誤讀成可部署排名。
- 驗證：`data/leaderboard_feature_profile_probe.json`、browser `/lab`、`python scripts/hb_leaderboard_candidate_probe.py`。

---

## Not Issues
- **data pipeline frozen**：不是；本輪 collect 實際新增 `+1 raw / +1 features / +1 labels`。
- **240m / 1440m freshness lag**：不是 blocker；目前仍屬 lookahead horizon 的 expected lag。
- **non-bull live row 仍重跑 bull pocket ablation**：不是了；本輪已驗證 `serial_results.bull_4h_pocket_ablation.cached=true` 且 `reference_only=true`。
- **q35 scaling drift**：不是 current blocker；current live row 已不在 q35 lane，`q35_scaling_audit` 應維持 reference-only。

---

## Current Priority
1. **維持 breaker-first truth，讓 current-live blocker 始終是 release math，而不是 q15 / venue / bull artifact 雜訊**
2. **把 recent canonical 100 rows pathology 當成 breaker 根因持續鑽深，不被 broader history 稀釋**
3. **把 q15 `0/50` 與 `exact_bucket_missing_exact_lane_proxy_only` 維持 machine-read，可見且不可被 bull spillover artifact 美化**
4. **保持 current live chop q15 與 broader bull spillover / bull pocket reference artifact 的分離**
5. **持續保留 per-venue blockers 與 metadata truth，可見直到 credentials / ack / fill 真正 closure，同時解除 `fin_netflow` auth blocker**
