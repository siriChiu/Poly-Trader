# ISSUES.md — Current State Only

_最後更新：2026-04-19 11:09 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **fast heartbeat `#20260419n` + collect 成功**：`Raw=31089 (+1) / Features=22507 (+1) / Labels=62582 (+0)`；`240m/1440m` freshness 仍屬 lookahead 的 expected lag，資料管線不是 frozen。
- **本輪產品化 patch 已修正 Live lane / spillover 卡片歧義**：`web/src/components/LivePathologySummaryCard.tsx` 現在會同時顯示 `focus_scope_rows` 與 `spillover rows`，並把右側標題改成依 `focus_scope_label` 派生的 `spillover pocket`；不再把「scope 外額外 rows」誤讀成整個 wider scope 的總樣本。`tests/test_frontend_decision_contract.py` 已補 regression。
- **canonical current-live 唯一 deployment blocker 仍是 circuit breaker**：`deployment_blocker=circuit_breaker_active`、`streak=243`、`recent 50 wins=0/50`、`additional_recent_window_wins_needed=15`、`allowed_layers=0`、`runtime_closure_state=circuit_breaker_active`。
- **current live bucket 已回到 `CAUTION|base_caution_regime_or_bias|q15`**：`regime=chop`、`gate=CAUTION`、`entry_quality=0.4119 (D)`；q15 exact support 目前 **0/50**，`gap_to_minimum=50`，`support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`，`support_governance_route=exact_live_bucket_proxy_available`。
- **live decision-quality truth 是 exact live lane 0 rows vs 同 quality 寬 scope 的 `bull|BLOCK` spillover 199 rows**：`chosen_scope=global`；exact live lane `rows=0`，wider same-quality spillover `rows=199`、`WR=0.0%`、`quality=-0.2857`。本輪 UI patch 已把 `focus_scope_rows=199` 與 `spillover rows=199` 並排顯示，避免把 spillover pocket 誤讀成整條 wider scope 的唯一真相。
- **leaderboard governance 仍是健康雙角色 split，但 candidate alignment snapshot 再次過舊**：`leaderboard_payload_stale=false`、`alignment_snapshot_stale=true`、`stale_against_bull_pocket=true`；目前 `global_profile=core_only`、`production_profile=core_plus_macro`、`governance_contract=dual_role_governance_active`，但對齊快照已落後最新 bull pocket artifact。
- **venue readiness truth 仍可在 operator surface 直接看到**：browser 實測 `http://127.0.0.1:5173/lab` 與 `http://127.0.0.1:5173/execution/status` 都可看到 breaker-first truth、`support 0/50`、`CAUTION|base_caution_regime_or_bias|q15`、Binance/OKX per-venue readiness cards；browser console 未觀察到 JS exception。
- **fin_netflow 仍是 source_auth_blocked**：CoinGlass ETF flow 仍因 `COINGLASS_API_KEY` 缺失而 `auth_missing`；forward archive 已累積 `2560` snapshots，但 `archive_window_coverage_pct=0.0%`。

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
**現況**
- `deployment_blocker=circuit_breaker_active`
- `recent_window=50`
- `current_recent_window_wins=0`
- `required_recent_window_wins=15`
- `additional_recent_window_wins_needed=15`
- `streak=243`
- `allowed_layers=0`
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`
- `runtime_closure_state=circuit_breaker_active`

**風險**
- 若任何 surface 把 q15 / spillover / venue blocker 排到 breaker 前面，operator 會失去唯一 current-live blocker 真相。

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
- `avg_quality=-0.2879`
- `tail_streak=100x0`
- top feature shifts：`feat_4h_vol_ratio`、`feat_mind`、`feat_4h_bb_pct_b`

**風險**
- breaker 若未解除，runtime 仍會被 recent pathological slice 持續壓回 `layers=0`；broader history 會掩蓋最近 canonical 崩塌口袋。

**下一步**
- 以 recent canonical rows 為主做 variance / distinct / target-path drilldown，避免把 current blocker 誤寫成單純 profile parity。
- 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`。

### P1. q15 exact support remains under minimum under breaker
**現況**
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`
- `live_current_structure_bucket_rows=0`
- `minimum_support_rows=50`
- `gap_to_minimum=50`
- `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`
- `support_governance_route=exact_live_bucket_proxy_available`
- `support_progress.status=stalled_under_minimum`
- `leaderboard_selected_profile=core_only`
- `train_selected_profile=core_plus_macro`
- `governance_contract=dual_role_governance_active`

**風險**
- 若 probe / docs / UI 把 `0/50` 與 `exact_live_bucket_proxy_available` 藏起來，operator 會誤判 q15 support 已 closure 或 current-live route 已可部署。

**下一步**
- 維持 `0/50 + exact_bucket_missing_exact_lane_proxy_only + exact_live_bucket_proxy_available + stalled_under_minimum` 在 probe / API / UI / docs / `issues.json` 一致 machine-read。
- 驗證：`python scripts/hb_q15_support_audit.py`、`python scripts/hb_predict_probe.py`、browser `/lab`、browser `/execution/status`。

### P1. exact live lane vs wider spillover truth must stay visible
**現況**
- exact live lane：`rows=0`、`bucket=CAUTION|base_caution_regime_or_bias|q15`
- focus scope：`同 quality 寬 scope`、`focus_scope_rows=199`
- spillover pocket：`bull|BLOCK`、`spillover_rows=199`、`WR=0.0%`、`quality=-0.2857`
- 本輪已補 UI context：`focus_scope_rows` 與 `spillover rows` 並排顯示，標題改為動態 `spillover pocket`

**風險**
- 若 UI 只顯示 `spillover rows` 而不顯示 `focus_scope_rows`，operator 會把 extra pocket rows 誤讀成整個 wider scope 的總樣本。

**下一步**
- 維持 `focus_scope_rows + spillover.extra_rows + exact live lane rows` 在 `/lab`、Dashboard、`/api/status`、`/api/predict/confidence` 一致。
- 驗證：`pytest tests/test_frontend_decision_contract.py -q`、`cd web && npm run build`、browser `/lab`。

### P1. leaderboard governance alignment snapshot is stale against the latest bull pocket artifact
**現況**
- `leaderboard_payload_stale=false`
- `alignment_snapshot_stale=true`
- `stale_against_bull_pocket=true`
- `leaderboard_selected_profile=core_only`
- `train_selected_profile=core_plus_macro`
- `governance_contract=dual_role_governance_active`

**風險**
- 即使 payload cache 本身仍新鮮，若 alignment snapshot 沒跟上最新 bull pocket artifact，Strategy Lab / heartbeat summary 仍可能拿舊治理快照判讀 current split。

**下一步**
- bull pocket artifact 變動時強制 refresh candidate alignment snapshot，再確認 `alignment_snapshot_stale=false` 後才引用治理結論。
- 驗證：`python scripts/hb_leaderboard_candidate_probe.py`、檢查 `data/leaderboard_feature_profile_probe.json` 的 `artifact_recency.alignment_snapshot_stale=false`。

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
- `forward_archive_rows=2560`
- `archive_window_coverage_pct=0.0%`

**風險**
- Feature coverage 會持續呈現假前進：archive 在長、但 live fetch 仍失敗，資料實際不可用。

**下一步**
- 配置 `COINGLASS_API_KEY`，先讓 ETF flow source 從 `auth_missing` 轉成成功 snapshot，再評估是否需要歷史 backfill。
- 驗證：`data/heartbeat_20260419n_summary.json` source blockers、`/api/features/coverage`。

### P1. model stability and live DQ robustness still need work
**現況**
- `cv_accuracy=60.8%`
- `cv_std=12.5pp`
- `cv_worst=44.5%`
- live path 仍落在 `label=D / layers=0`
- current chosen scope：`global`
- worst scope：`entry_quality_label` → `bull|BLOCK` 199 rows, `WR=0.0%`, `quality=-0.2857`

**風險**
- 即使 breaker 未來解除，若 profile robustness 沒改善，runtime 仍只會把 current bucket 壓回 0 layers。

**下一步**
- 優先比較 shrinkage / support-aware profiles 與 current bucket robustness，避免把治理 blocker 誤當單純 parity 問題。
- 驗證：`data/leaderboard_feature_profile_probe.json`、`data/live_predict_probe.json`、`data/live_decision_quality_drilldown.json`。

---

## Not Issues
- **data pipeline frozen**：不是；本輪 collect 實際新增 `+1 raw / +1 features / +0 labels`。
- **240m / 1440m freshness lag**：不是 blocker；目前仍屬 lookahead horizon 的 expected lag。
- **browser runtime regression**：不是；本輪 browser 實測 `/lab` 與 `/execution/status` 都成功渲染 breaker-first truth、q15 `0/50`、focus-scope/spillover context 與 venue cards，且未觀察到 JS exception。
- **spillover card sample-size 歧義**：不是 current issue；本輪 UI patch 已修正為同時顯示 `focus_scope_rows` 與 `spillover rows`。
- **leaderboard payload cache stale**：不是 current truth；目前 `leaderboard_payload_stale=false`。真正要修的是 `alignment_snapshot_stale=true`。

---

## Current Priority
1. **維持 breaker-first truth，讓 current-live blocker 始終是 release math，而不是 q15 / spillover / venue 雜訊**
2. **維持 q15 `0/50 + exact_bucket_missing_exact_lane_proxy_only + exact_live_bucket_proxy_available` 的單一 machine-read 真相**
3. **維持 exact live lane 0 rows vs 同 quality 寬 scope `bull|BLOCK` 199 rows 的對照可見，且保留 `focus_scope_rows` context**
4. **修復 leaderboard alignment snapshot stale，不讓 Strategy Lab / heartbeat summary 依賴過舊 bull pocket 對齊快照**
5. **持續保留 per-venue readiness cards，直到 credentials / ack / fill 有 runtime proof**
6. **解除 `fin_netflow` 的 `source_auth_blocked`（COINGLASS_API_KEY）以避免 sparse-source 假前進**
