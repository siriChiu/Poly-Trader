# ISSUES.md — Current State Only

_最後更新：2026-04-19 11:35 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **fast heartbeat `#20260419o` + collect 成功**：`Raw=31090 (+1) / Features=22508 (+1) / Labels=62588 (+6)`；`240m / 1440m` freshness 仍屬 lookahead 的 expected lag，資料管線不是 frozen。
- **canonical current-live 唯一 deployment blocker 仍是 circuit breaker**：`deployment_blocker=circuit_breaker_active`、`streak=244`、`recent 50 wins=0/50`、`additional_recent_window_wins_needed=15`、`allowed_layers=0`、`runtime_closure_state=circuit_breaker_active`。
- **current live bucket 仍是 `CAUTION|base_caution_regime_or_bias|q15`**：`regime=chop`、`gate=CAUTION`、`entry_quality=0.4123 (D)`；exact support 仍是 **0/50**，`support_route_verdict=exact_bucket_missing_proxy_reference_only`、`support_governance_route=exact_live_bucket_proxy_available`。
- **q15 support 已連續 4 輪停滯**：`support_progress.status=stalled_under_minimum`、`stagnant_run_count=4`、`escalate_to_blocker=true`；目前不是 proxy 不可見，而是 exact bucket 真樣本完全沒有增加。
- **live decision-quality truth 仍是 exact live lane 0 rows vs 同 quality 寬 scope `bull|BLOCK` spillover 199 rows**：`spillover WR=0.0%`、`quality=-0.2857`；browser 實測 `/lab` 與 `/execution/status` 都能直接看到 breaker-first truth、q15 `0/50`、exact-vs-spillover 對照與 Binance/OKX venue cards，且未觀察到 JS exception。
- **本輪產品化 patch 已修正 legacy alignment governance issue 殘留**：`scripts/auto_propose_fixes.py` 現在會在 alignment 已 current 時主動 resolve 舊的 `P1_leaderboard_alignment_snapshot_stale`；`pytest tests/test_auto_propose_fixes.py -q` 已通過 `26 passed`。
- **leaderboard governance 已刷新為 current truth**：`data/leaderboard_feature_profile_probe.json` 顯示 `leaderboard_payload_source=live_rebuild`、`alignment_snapshot_stale=false`、`current_alignment_inputs_stale=false`、`governance_contract=dual_role_governance_active`；目前 `global_profile=core_only`、`production_profile=core_plus_macro` 是健康雙角色 split，不是 parity drift。
- **Strategy Lab leaderboard 目前仍是 placeholder-only**：`comparable_count=0`、`placeholder_count=6`；UI 已明示不可把 `#1` 當成可部署排名，但這仍代表排行榜暫時不能提供可比較的 deployment ranking。
- **venue readiness 仍只有 public metadata proof**：`binance=config enabled + public-only`、`okx=config disabled + public-only`；`data/execution_metadata_smoke.json` 新鮮且 healthy，但仍缺 `live exchange credential / order ack lifecycle / fill lifecycle`。
- **fin_netflow 仍是 source_auth_blocked**：`COINGLASS_API_KEY` 缺失；forward archive 已累積 `2561` snapshots，但 `archive_window_coverage_pct=0.0%`。

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
**現況**
- `deployment_blocker=circuit_breaker_active`
- `recent_window=50`
- `current_recent_window_wins=0`
- `required_recent_window_wins=15`
- `additional_recent_window_wins_needed=15`
- `streak=244`
- `allowed_layers=0`
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`
- `runtime_closure_state=circuit_breaker_active`

**風險**
- 若任何 surface 把 q15 support、spillover 或 venue blocker 排到 breaker 前面，operator 會失去唯一 current-live blocker 真相。

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
- `avg_quality=-0.2878`
- `tail_streak=100x0`
- top feature shifts：`feat_4h_vol_ratio`、`feat_mind`、`feat_4h_bb_pct_b`

**風險**
- canonical recent tail 仍是 breaker 的根因；若只看 broader history 或只看 global profile，會掩蓋 current pathological slice。

**下一步**
- 以 recent canonical rows 為主做 variance / distinct / target-path drilldown，避免把 blocker 誤寫成單純 profile parity 或 q15 floor gap。
- 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`。

### P1. q15 exact support remains under minimum under breaker
**現況**
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`
- `live_current_structure_bucket_rows=0`
- `minimum_support_rows=50`
- `gap_to_minimum=50`
- `support_route_verdict=exact_bucket_missing_proxy_reference_only`
- `support_governance_route=exact_live_bucket_proxy_available`
- `support_progress.status=stalled_under_minimum`
- `support_progress.stagnant_run_count=4`
- `support_progress.escalate_to_blocker=true`

**風險**
- 若 probe / docs / UI 把 `0/50 + proxy reference only + stalled_under_minimum` 藏起來，operator 會誤判 q15 support 正在 closure。

**下一步**
- 維持 `0/50 + exact_bucket_missing_proxy_reference_only + exact_live_bucket_proxy_available + stalled_under_minimum + escalate_to_blocker=true` 在 probe / API / UI / docs / `issues.json` 一致 machine-read。
- 驗證：`python scripts/hb_q15_support_audit.py`、`python scripts/hb_predict_probe.py`、browser `/lab`、browser `/execution/status`。

### P1. venue readiness is still unverified
**現況**
- `binance`: `config enabled + public-only`
- `okx`: `config disabled + public-only`
- metadata smoke：`fresh / healthy`
- 缺的 runtime proof：`live exchange credential`、`order ack lifecycle`、`fill lifecycle`

**風險**
- breaker 未來解除後，若 venue blockers 被弱化成摘要字串，使用者會被誤導成已可實盤。

**下一步**
- 持續保留 per-venue cards 與 venue blockers，直到 credentials / ack / fill 都有 runtime-backed proof。
- 驗證：browser `/lab`、browser `/execution/status`、`data/execution_metadata_smoke.json`。

### P1. fin_netflow source_auth_blocked remains open
**現況**
- `fin_netflow=source_auth_blocked`
- `latest_status=auth_missing`
- blocker 根因：`COINGLASS_API_KEY is missing`
- `forward_archive_rows=2561`
- `archive_window_coverage_pct=0.0%`

**風險**
- Feature coverage 會持續呈現假前進：archive 在長，但 live fetch 仍失敗，資料實際不可用。

**下一步**
- 配置 `COINGLASS_API_KEY`，先讓 ETF flow source 從 `auth_missing` 轉成成功 snapshot，再評估是否需要歷史 backfill。
- 驗證：`data/heartbeat_20260419o_summary.json` source blockers、`/api/features/coverage`。

### P1. model stability and live DQ robustness still need work
**現況**
- `cv_accuracy=60.8%`
- `cv_std=12.5pp`
- `cv_worst=44.5%`
- live path 仍落在 `label=D / layers=0`
- current chosen scope：`global`
- worst scope：`entry_quality_label` → `bull|BLOCK` 199 rows, `WR=0.0%`, `quality=-0.2857`

**風險**
- 即使 breaker 未來解除，若 profile robustness 沒改善，runtime 仍會把 current bucket 壓回 0 layers。

**下一步**
- 優先比較 shrinkage / support-aware profiles 與 current bucket robustness，避免把治理 blocker 誤當單純 parity 問題。
- 驗證：`data/leaderboard_feature_profile_probe.json`、`data/live_predict_probe.json`、`data/live_decision_quality_drilldown.json`。

---

## Not Issues
- **leaderboard alignment snapshot stale**：不是 current truth；本輪已用 live rebuild 刷新 `leaderboard_feature_profile_probe.json`，`alignment_snapshot_stale=false`，且 `issues.json` 已清掉舊的 `P1_leaderboard_alignment_snapshot_stale`。
- **leaderboard governance split itself**：不是 blocker；`global_profile=core_only` vs `production_profile=core_plus_macro` 目前是 `dual_role_governance_active`，不是 parity drift。
- **data pipeline frozen**：不是；本輪 collect 實際新增 `+1 raw / +1 features / +6 labels`。
- **240m / 1440m freshness lag**：不是 blocker；目前仍屬 lookahead horizon 的 expected lag。
- **browser runtime regression**：不是；本輪 browser 實測 `/lab` 與 `/execution/status` 都成功渲染 breaker-first truth、q15 `0/50`、exact-vs-spillover 對照與 per-venue cards，且未觀察到 JS exception。

---

## Current Priority
1. **維持 breaker-first truth，讓 current-live blocker 始終是 release math，而不是 q15 / spillover / venue 雜訊**
2. **把 q15 exact support `0/50` 停滯 4 輪的事實維持 machine-read，可見且不可被 proxy 美化**
3. **維持 exact live lane 0 rows vs `bull|BLOCK` spillover 199 rows 的對照與 venue blockers 在 `/lab`、`/execution/status` 可見**
4. **保持 leaderboard governance 的 current truth：`alignment_snapshot_stale=false`、雙角色 split 健康、placeholder-only 排行榜不可被誤讀成 deployment ranking**
5. **解除 `fin_netflow` 的 `source_auth_blocked`（COINGLASS_API_KEY）以避免 sparse-source 假前進**
