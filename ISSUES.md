# ISSUES.md — Current State Only

_最後更新：2026-04-19 12:30 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **fast heartbeat `#20260419q` + collect 成功**：`Raw=31095 (+1) / Features=22513 (+1) / Labels=62594 (+3)`；`240m / 1440m` freshness 仍屬 lookahead 的 expected lag，資料管線不是 frozen。
- **canonical current-live 唯一 deployment blocker 仍是 circuit breaker**：`deployment_blocker=circuit_breaker_active`、`streak=246`、`recent 50 wins=0/50`、`additional_recent_window_wins_needed=15`、`allowed_layers=0`、`runtime_closure_state=circuit_breaker_active`。
- **current live bucket 仍固定在 `BLOCK|bull_q15_bias50_overextended_block|q15`**：`regime=bull`、`gate=BLOCK`、`entry_quality=0.3234 (D)`；exact support 為 **1/50**，`support_route_verdict=exact_bucket_present_but_below_minimum`、`gap_to_minimum=49`、`support_progress.status=stalled_under_minimum`、`stagnant_run_count=5`、`escalate_to_blocker=true`。
- **recent canonical 100 rows 仍是 distribution pathology**：`win_rate=0.0000`、`dominant_regime=bull(100%)`、`avg_pnl=-0.0094`、`avg_quality=-0.2871`、`tail_streak=100x0`；主 shifts 仍是 `feat_4h_vol_ratio`、`feat_mind`、`feat_4h_bb_pct_b`。
- **live exact lane 與 spillover 仍是 199 vs 1 rows**：exact live lane=`regime_label+regime_gate+entry_quality_label` 199 rows、`WR=0.0%`、`quality=-0.2854`；wider spillover pocket 只剩 `bull|BLOCK` 1 row、`quality=-0.314`。
- **本輪產品化 patch 已修正 `/execution` / `/execution/status` blocker 排序 drift**：兩個 execution surface 現在都會先顯示 `circuit_breaker_active` 與 breaker reason，再把 `live exchange credential / order ack lifecycle / fill lifecycle` 保留為 secondary venue blockers；不再把 venue readiness 誤報成 current-live 主 blocker。
- **support-aware patch 仍只能 reference-only**：`recommended_patch=core_plus_macro`、`status=reference_only_until_exact_support_ready`、`support_route_verdict=exact_bucket_present_but_below_minimum`、`gap_to_minimum=49`；live spillover 仍是 `bull|BLOCK`，reference patch scope 仍是 `bull|CAUTION`。
- **leaderboard governance 仍是健康雙角色 split，不是 stale drift**：`global_profile=core_only`、`train_selected_profile=core_plus_macro`、`governance_contract=dual_role_governance_active`；但 `leaderboard_count=0`，Strategy Lab 仍屬 placeholder-only ranking。
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
- `streak=246`
- `allowed_layers=0`
- `current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15`
- `runtime_closure_state=circuit_breaker_active`

**風險**
- 若任何 surface 再把 venue blockers、q15 support 或 reference patch 排到 breaker 前面，operator 會失去唯一 current-live blocker 真相。

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
- `avg_quality=-0.2871`
- `tail_streak=100x0`
- top feature shifts：`feat_4h_vol_ratio`、`feat_mind`、`feat_4h_bb_pct_b`

**風險**
- 這個 recent canonical tail 仍是 breaker 的根因；若只看 broader history、profile split 或 venue blockers，會掩蓋 current pathological slice。

**下一步**
- 以 recent canonical rows 為主做 variance / distinct / target-path drilldown，避免把 blocker 誤寫成 profile parity 或單純 q15 floor gap。
- 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`。

### P1. q15 exact support remains under minimum under breaker
**現況**
- `current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15`
- `live_current_structure_bucket_rows=1`
- `minimum_support_rows=50`
- `gap_to_minimum=49`
- `support_route_verdict=exact_bucket_present_but_below_minimum`
- `support_governance_route=exact_live_bucket_present_but_below_minimum`
- `support_progress.status=stalled_under_minimum`
- `support_progress.stagnant_run_count=5`
- `support_progress.escalate_to_blocker=true`

**風險**
- 如果 probe / docs / UI 把 `1/50 + stalled_under_minimum + present_but_below_minimum` 藏掉，operator 會誤判 q15 support 已接近 closure。

**下一步**
- 維持 `1/50 + exact_bucket_present_but_below_minimum + stalled_under_minimum + escalate_to_blocker=true` 在 probe / API / UI / docs / `issues.json` 一致 machine-read。
- 驗證：`python scripts/hb_q15_support_audit.py`、`python scripts/hb_predict_probe.py`、browser `/lab`、browser `/execution/status`。

### P1. support-aware patch must remain visible, but only as reference
**現況**
- `actual_live_spillover_scope=bull|BLOCK`
- `reference_patch_scope=bull|CAUTION`
- `reference_source=bull_4h_pocket_ablation.bull_collapse_q35`
- `recommended_patch=core_plus_macro`
- `recommended_patch_status=reference_only_until_exact_support_ready`
- `support_route_verdict=exact_bucket_present_but_below_minimum`
- `gap_to_minimum=49`

**風險**
- 若 surface 再次把 `bull|CAUTION` reference patch 誤報成 current live spillover，operator 會把 artifact-backed patch 誤讀成 live pocket 已 closure。

**下一步**
- 保持 `spillover_regime_gate`（live pocket）與 `reference_patch_scope/reference_source`（artifact-backed patch）在 `/api/status`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`/lab`、`ISSUES.md` 一致；在 exact support 達標前，不可把 patch 升級成 deployable。
- 驗證：`curl /api/status`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、browser `/lab`。

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
- `forward_archive_rows=2566`
- `archive_window_coverage_pct=0.0%`

**風險**
- Feature coverage 會持續呈現假前進：archive 在長，但 live fetch 仍失敗，資料實際不可用。

**下一步**
- 配置 `COINGLASS_API_KEY`，先讓 ETF flow source 從 `auth_missing` 轉成成功 snapshot，再評估是否需要歷史 backfill。
- 驗證：`data/heartbeat_20260419q_summary.json` source blockers、`/api/features/coverage`。

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
- 優先比較 shrinkage / support-aware profiles 與 current bucket robustness，避免把治理 blocker 誤當單純 parity 問題；同時維持 placeholder-only warning，不讓 `#1` 被誤讀成可部署排名。
- 驗證：`data/leaderboard_feature_profile_probe.json`、browser `/lab`、`python scripts/hb_leaderboard_candidate_probe.py`。

---

## Not Issues
- **`/execution` / `/execution/status` blocker ordering drift**：不是了；本輪已修成 breaker-first，browser 可直接看到 `circuit_breaker_active` 與 venue blockers 的主次分離。
- **live spillover / reference patch visibility drift**：不是；`/lab` 與 `/api/status` 都能同時看到 `live spillover bull|BLOCK` 與 `reference patch bull|CAUTION`。
- **leaderboard alignment snapshot stale**：不是 current truth；`alignment_snapshot_stale=false`、`leaderboard_payload_stale=false`。
- **data pipeline frozen**：不是；本輪 collect 實際新增 `+1 raw / +1 features / +3 labels`。
- **240m / 1440m freshness lag**：不是 blocker；目前仍屬 lookahead horizon 的 expected lag。

---

## Current Priority
1. **維持 breaker-first truth，讓 current-live blocker 始終是 release math，而不是 venue / q15 / patch 雜訊**
2. **把 recent canonical 100 rows pathology 當成 breaker 根因持續鑽深，不被 broader history 稀釋**
3. **把 q15 exact support `1/50` 與 stalled-under-minimum 事實維持 machine-read，可見且不可被 reference patch 美化**
4. **保持 live spillover `bull|BLOCK` 與 reference patch `bull|CAUTION` 的分離，不讓 artifact patch 再被誤讀成 current live pocket**
5. **維持 per-venue blockers 與 metadata truth 可見，直到 credentials / ack / fill 真正 closure，同時解除 `fin_netflow` auth blocker**
