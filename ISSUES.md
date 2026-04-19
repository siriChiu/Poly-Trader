# ISSUES.md — Current State Only

_最後更新：2026-04-19 10:36 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **fast heartbeat `#20260419l` + collect 成功**：`Raw=31086 (+1) / Features=22504 (+1) / Labels=62580 (+0)`；active horizons 仍是 `240m/1440m`，freshness 屬於 lookahead 預期 lag，資料管線不是 frozen。
- **本輪產品化 patch 已修復 leaderboard governance stale-cache 問題**：`scripts/hb_leaderboard_candidate_probe.py` 現在遇到 stale leaderboard cache / persisted snapshot 會先 live-rebuild 並回寫 cache/snapshot；`scripts/hb_parallel_runner.py` refresh candidate alignment artifact 時也改成走 `allow_rebuild=True`。本輪重新驗證後 `data/leaderboard_feature_profile_probe.json` 顯示 `leaderboard_payload_updated_at=2026-04-19T02:31:45.190677Z`、`leaderboard_payload_stale=false`、`snapshot_stale=false`。
- **canonical current-live 唯一 deployment blocker 仍是 circuit breaker**：`deployment_blocker=circuit_breaker_active`、`streak=242`、`recent 50 wins=0/50`、`additional_recent_window_wins_needed=15`、`allowed_layers=0`、`runtime_closure_state=circuit_breaker_active`。
- **current live bucket 已切到 `CAUTION|base_caution_regime_or_bias|q15`**：`regime=chop`、`gate=CAUTION`、`entry_quality=0.4206 (D)`；q15 exact support 目前 **0/50**，`gap_to_minimum=50`，`support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`，`support_governance_route=exact_live_lane_proxy_available`。
- **live decision-quality truth 現在是 exact lane 0 rows vs broader spillover 199 rows**：`chosen_scope=global`；exact live lane `rows=0`，broader spillover 為 `bull|BLOCK`、`rows=199`、`WR=0.0%`、`quality=-0.2856`。current-live blocker 仍應解讀為 breaker-first，不可把 spillover 當成 exact support closure。
- **venue readiness truth 仍可在 operator surface 直接看到**：browser 實測 `http://127.0.0.1:5173/lab` 與 `http://127.0.0.1:5173/execution/status` 都可看到 breaker-first truth、`support 0/50`、Binance/OKX per-venue readiness cards；browser console 未觀察到 JS exception。
- **fin_netflow 仍是 source_auth_blocked**：CoinGlass ETF flow 仍因 `COINGLASS_API_KEY` 缺失而 `auth_missing`；forward archive 已累積 `2557` snapshots，但 `archive_window_coverage_pct=0.0%`。

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
**現況**
- `deployment_blocker=circuit_breaker_active`
- `recent_window=50`
- `current_recent_window_wins=0`
- `required_recent_window_wins=15`
- `additional_recent_window_wins_needed=15`
- `streak=242`
- `allowed_layers=0`
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`
- `runtime_closure_state=circuit_breaker_active`

**風險**
- 若任何 surface 把 q15/support/spillover/venue blocker 排到 breaker 前面，operator 會失去唯一 current-live blocker 真相。

**下一步**
- 維持 breaker-first truth 在 `hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`/lab`、`/execution/status`、`issues.json`、`ISSUES.md` 一致。
- 驗證：`python scripts/hb_parallel_runner.py --fast --hb <N>`、`python scripts/hb_predict_probe.py`、browser `/lab`、browser `/execution/status`。

### P0. recent canonical window remains a distribution pathology
**現況**
- `recent_window=100`
- `win_rate=0.0000`
- `dominant_regime=bull(100%)`
- `alerts=['constant_target','regime_concentration','regime_shift']`
- `avg_pnl=-0.0095`
- `avg_quality=-0.2877`
- `tail_streak=100x0`
- top feature shifts：`feat_4h_vol_ratio`、`feat_mind`、`feat_4h_bb_pct_b`

**風險**
- breaker 若未解除，runtime 仍會持續被 recent pathological slice 壓回 `layers=0`，而 broader historical averages 會掩蓋最近 canonical 崩塌口袋。

**下一步**
- 以 recent canonical rows 為主做 variance/distinct/target-path drilldown，避免把 current blocker 誤寫成單純 profile parity。
- 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`。

### P1. q15 exact support remains under minimum under breaker
**現況**
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`
- `live_current_structure_bucket_rows=0`
- `minimum_support_rows=50`
- `gap_to_minimum=50`
- `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`
- `support_governance_route=exact_live_lane_proxy_available`
- `support_progress.status=stalled_under_minimum`
- `leaderboard_selected_profile=core_only`
- `train_selected_profile=core_plus_macro`
- `governance_contract=dual_role_governance_active`

**風險**
- 若 probe / docs / UI 把 `0/50` 與 `exact_live_lane_proxy_available` 藏起來，operator 會誤判 q15 support 已 closure 或 current-live route 已經可部署。

**下一步**
- 維持 `0/50 + exact_bucket_missing_exact_lane_proxy_only + exact_live_lane_proxy_available + stalled_under_minimum` 在 probe / API / UI / docs / `issues.json` 一致 machine-read。
- 驗證：`python scripts/hb_q15_support_audit.py`、`python scripts/hb_predict_probe.py`、browser `/lab`、browser `/execution/status`。

### P1. exact live lane vs broader spillover truth must stay visible
**現況**
- exact live lane：`rows=0`、`current bucket=CAUTION|base_caution_regime_or_bias|q15`
- broader spillover：`bull|BLOCK`、`199 rows`、`WR=0.0%`、`quality=-0.2856`
- chosen scope：`global`
- current top 4H shifts：`feat_4h_bias200`、`feat_4h_dist_bb_lower`、`feat_4h_dist_swing_low`

**風險**
- 若 UI / docs 把 exact lane 0-row truth 與 broader `bull|BLOCK` spillover 混成單一 current-live 口袋，會把 spillover pathology 誤讀成 exact support 或 runtime closure 依據。

**下一步**
- 維持 `/lab`、`/execution/status`、`live_decision_quality_drilldown.py` 對 exact lane 0 rows vs `bull|BLOCK` spillover 199 rows 的一致敘事。
- 驗證：`python scripts/live_decision_quality_drilldown.py`、browser `/lab`、browser `/execution/status`。

### P1. leaderboard governance cache freshness must not regress
**現況**
- 本輪已修復 stale-cache refresh：candidate probe 不再沿用過期 leaderboard snapshot 判讀 profile governance。
- 目前 probe 顯示：`leaderboard_payload_source=model_leaderboard_cache`、`leaderboard_payload_stale=false`、`snapshot_stale=false`、`governance_contract=dual_role_governance_active`。
- 目前健康 split：`global_profile=core_only`、`production_profile=core_plus_macro`、`support_governance_route=exact_live_lane_proxy_available`。

**風險**
- 若 stale cache refresh 回退，Strategy Lab / heartbeat summary 會再次把 profile governance 建立在舊排行榜快照上，造成假 drift 或假 closure。

**下一步**
- 固定保留 stale-cache refresh regression tests，並在每輪 heartbeat 檢查 `snapshot_stale=false`。
- 驗證：`pytest tests/test_hb_leaderboard_candidate_probe.py tests/test_hb_parallel_runner.py -q`、`python scripts/hb_leaderboard_candidate_probe.py`、`python scripts/hb_parallel_runner.py --fast --hb <N>`。

### P1. venue readiness is still unverified
**現況**
- `binance`: `config enabled + public-only`
- `okx`: `config disabled + public-only`
- `/lab`、`/execution/status` 已可見 per-venue readiness truth
- 缺的 runtime proof 仍是：`live exchange credential`、`order ack lifecycle`、`fill lifecycle`

**風險**
- breaker 未來解除後，若 venue blockers 被弱化成摘要字串，使用者會被誤導成已可實盤。

**下一步**
- 持續保留 per-venue cards 與 venue blockers，直到 credentials / ack / fill 都有 runtime-backed proof。
- 驗證：browser `/lab`、browser `/execution/status`、`data/execution_metadata_smoke.json`。

### P1. fin_netflow source_auth_blocked remains open
**現況**
- `fin_netflow`: `source_auth_blocked`
- `latest_status=auth_missing`
- blocker 根因：`COINGLASS_API_KEY is missing`
- `forward_archive_rows=2557`
- `archive_window_coverage_pct=0.0%`

**風險**
- Feature coverage 會持續呈現假前進：archive 在長、但 live fetch 仍失敗，資料實際不可用。

**下一步**
- 配置 `COINGLASS_API_KEY`，先讓 ETF flow source 從 `auth_missing` 轉成成功 snapshot，再評估是否需要歷史 backfill。
- 驗證：`data/heartbeat_20260419l_summary.json` source blockers、`/api/features/coverage`。

### P1. model stability and live DQ robustness still need work
**現況**
- `cv_accuracy=60.8%`
- `cv_std=12.5pp`
- `cv_worst=44.5%`
- live path 仍落在 `label=D / layers=0`
- recent pathology：`100x0`、`distribution_pathology`、`dominant_regime=bull(100%)`

**風險**
- 即使 breaker 未來解除，若 profile robustness 沒改善，runtime 仍只會把 current bucket 壓回 0 layers。

**下一步**
- 優先比較 shrinkage / support-aware profiles 與 current bucket robustness，避免把治理 blocker 誤當單純 parity 問題。
- 驗證：`data/leaderboard_feature_profile_probe.json`、`data/live_predict_probe.json`、`data/live_decision_quality_drilldown.json`。

---

## Not Issues
- **data pipeline frozen**：不是；本輪 collect 實際新增 `+1 raw / +1 features / +0 labels`。
- **240m / 1440m freshness lag**：不是 blocker；目前仍屬 lookahead horizon 的 expected lag。
- **leaderboard candidate snapshot stale**：不是 current truth；本輪 patch + 驗證後 `leaderboard_payload_stale=false`、`snapshot_stale=false`。
- **browser runtime regression**：不是；本輪 `http://127.0.0.1:5173/lab` 與 `http://127.0.0.1:5173/execution/status` 都成功渲染 breaker-first truth 與 venue cards，且未觀察到 JS exception。

---

## Current Priority
1. **維持 breaker-first truth，讓 current-live blocker 始終是 release math，而不是 q15/support/spillover/venue 雜訊**
2. **維持 q15 `0/50 + exact_bucket_missing_exact_lane_proxy_only + exact_live_lane_proxy_available` 的單一 machine-read 真相**
3. **維持 exact live lane 0 rows vs broader `bull|BLOCK` 199 rows 的對照可見，不讓 spillover 汙染 current-live 敘事**
4. **維持 leaderboard governance cache freshness，不讓 stale snapshot 再污染 Strategy Lab / heartbeat summary**
5. **持續保留 per-venue readiness cards，直到 credentials / ack / fill 有 runtime proof**
6. **解除 `fin_netflow` 的 `source_auth_blocked`（COINGLASS_API_KEY）以避免 sparse-source 假前進**
