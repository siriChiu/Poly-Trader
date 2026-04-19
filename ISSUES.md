# ISSUES.md — Current State Only

_最後更新：2026-04-20 00:32:56 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **本輪 fast heartbeat #20260420a 已完成 collect + verify 閉環**
  - `Raw=31153 / Features=22571 / Labels=62743`
  - 本輪 collect 實際新增：`+1 raw / +1 features / +31 labels`
  - `Global IC=13/30`、`TW-IC=29/30`
- **canonical current-live blocker 仍只有 breaker，但 current-live bucket truth 已切到 q15**
  - `deployment_blocker=circuit_breaker_active`
  - `signal=CIRCUIT_BREAKER`
  - `reason=Consecutive loss streak: 60 >= 50; Recent 50-sample win rate: 0.00% < 30%`
  - `recent 50 wins=0/50`
  - `required_recent_window_wins=15`
  - `additional_recent_window_wins_needed=15`
  - `streak=60`
  - `allowed_layers=0`
  - `runtime_closure_state=circuit_breaker_active`
  - `regime_label=chop / regime_gate=CAUTION`
  - `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`
  - `current_live_structure_bucket_rows=0 / minimum_support_rows=50 / gap_to_minimum=50`
  - `support_route_verdict=exact_bucket_missing_proxy_reference_only`
  - `support_governance_route=exact_live_bucket_proxy_available`
- **recent canonical 250 rows 仍是 distribution pathology**
  - `win_rate=0.0040 (1/250)`
  - `dominant_regime=bull(100%)`
  - `avg_pnl=-0.0086`
  - `avg_quality=-0.2623`
  - `avg_drawdown_penalty=0.3488`
  - `alerts=['label_imbalance','regime_concentration','regime_shift']`
  - `tail_streak=60x0`
  - top shifts=`feat_4h_vol_ratio`、`feat_eye`、`feat_local_top_score`
- **leaderboard / governance 仍健康，但已縮成 4 rows**
  - `leaderboard_count=4`
  - `selected_feature_profile=core_only`
  - `support_aware_production_profile=core_plus_macro`
  - `governance_contract=dual_role_governance_active`
  - `current_closure=global_ranking_vs_support_aware_production_split`
  - `leaderboard_payload_source=latest_persisted_snapshot`
- **venue / source blockers 仍開啟**
  - venue：Binance / OKX 仍缺 `live exchange credential`、`order ack lifecycle`、`fill lifecycle`
  - source：`fin_netflow=source_auth_blocked`，根因仍是 `COINGLASS_API_KEY` 缺失
- **本輪產品化 patch：/api/status 不再把 current-live q15 support truth 藏成 null**
  - root cause：`server/routes/api.py::_build_live_runtime_closure_surface()` 沒把 `current_live_structure_bucket / current_live_structure_bucket_rows / minimum_support_rows / current_live_structure_bucket_gap_to_minimum / support_governance_route` 回傳到 `execution.live_runtime_truth` 頂層。
  - effect：`hb_predict_probe.py` 已經是 `q15 + 0/50`，但 `/api/status` 頂層仍是 `current_live_structure_bucket=null`，造成 API / UI / docs machine-read split-brain。
  - fix：runtime closure surface 現在會從 payload / blocker details / exact-scope fallback 統一回填上述欄位，breaker 下也維持 top-level 可見。
- **本輪驗證已完成**
  - `pytest tests/test_server_startup.py -q` → `29 passed`
  - `pytest tests/test_frontend_decision_contract.py -q` → `19 passed`
  - `cd web && npm run build` → pass
  - `curl http://127.0.0.1:8000/api/status`：已回傳 `current_live_structure_bucket=q15`、`rows=0/50`、`support_governance_route=exact_live_bucket_proxy_available`
  - browser `/execution/status`：已顯示 `chop / CAUTION / q15 / support 0/50`
  - browser `/lab`：已顯示 `current bucket 0 CAUTION|base_caution_regime_or_bias|q15` 與 `support 0/50`

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
**現況**
- `deployment_blocker=circuit_breaker_active`
- `streak=60`
- `recent_window=50`
- `current_recent_window_wins=0`
- `required_recent_window_wins=15`
- `additional_recent_window_wins_needed=15`
- `allowed_layers=0`
- `runtime_closure_state=circuit_breaker_active`
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`
- `current_live_structure_bucket_rows=0 / minimum_support_rows=50 / gap_to_minimum=50`

**風險**
- 如果 `/api/status`、`/execution/status`、`/lab`、probe、drilldown、docs 任何一個 surface 再把 q15 same-bucket truth 藏回 null、或把 q15 support/venue/blocker 順序排到 breaker release math 前面，operator 仍會被錯誤 current-live 敘事誤導。

**下一步**
- 維持 breaker-first truth，同時保留 q15 current-live bucket 與 support rows 在 top-level runtime surfaces 可見。
- 驗證：`curl /api/status`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`。

### P0. recent canonical 250 rows remains a distribution pathology
**現況**
- `recent_window=250`
- `win_rate=0.0040`
- `dominant_regime=bull`
- `dominant_regime_share=1.0000`
- `avg_pnl=-0.0086`
- `avg_quality=-0.2623`
- `avg_drawdown_penalty=0.3488`
- `alerts=['label_imbalance','regime_concentration','regime_shift']`
- `tail_streak=60x0`
- top shifts=`feat_4h_vol_ratio`、`feat_eye`、`feat_local_top_score`

**風險**
- breaker release math 持續惡化的根因仍在 canonical tail；若 heartbeat 把主敘事轉成 generic leaderboard 或 venue 話題，就會繼續錯過真正的 pathological slice。

**下一步**
- 直接沿 recent canonical rows 做 target-path / feature-shift / scope-pathology root-cause，不要 generic 化。
- 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`。

### P1. q15 exact support remains missing; support-aware patch must stay reference-only
**現況**
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`
- `current_live_structure_bucket_rows=0 / minimum_support_rows=50`
- `gap_to_minimum=50`
- `support_route_verdict=exact_bucket_missing_proxy_reference_only`
- `support_governance_route=exact_live_bucket_proxy_available`
- `recommended_patch=core_plus_macro_plus_all_4h`
- `recommended_patch_status=reference_only_until_exact_support_ready`
- `recommended_patch_reference_scope=bull|CAUTION`

**風險**
- 若任何 surface 把 proxy/reference patch 誤讀成 current deployable truth，會再次製造 current-live split-brain。

**下一步**
- 維持 `0/50 + proxy_reference_only` 在 API / UI / probe / docs 一致可見；exact support 未達門檻前，不可升級成 deployable truth。
- 驗證：browser `/execution/status`、browser `/lab`、`python scripts/live_decision_quality_drilldown.py`、`data/q15_support_audit.json`。

### P1. venue readiness is still unverified
**現況**
- `binance=config enabled + public-only + metadata OK`
- `okx=config disabled + public-only + metadata OK`
- 缺的 runtime proof：`live exchange credential`、`order ack lifecycle`、`fill lifecycle`

**風險**
- breaker 未來解除後，若 venue blockers 被弱化成摘要字串或短暫消失，使用者會被誤導成已可實盤。

**下一步**
- 維持 per-venue blockers 在 `/execution/status`、`/lab`、`/execution`、`/` 顯式可見，直到三項 runtime proof 都被 artifact 支撐。
- 驗證：browser `/execution/status`、browser `/lab`、`data/execution_metadata_smoke.json`。

### P1. fin_netflow source_auth_blocked remains open
**現況**
- `fin_netflow=source_auth_blocked`
- `latest_status=auth_missing`
- blocker 根因：`COINGLASS_API_KEY is missing`
- `forward_archive_rows=2624`
- `archive_window_coverage_pct=0.0%`

**風險**
- feature coverage 會持續呈現假前進：archive 在長，但 live fetch 仍失敗，資料實際不可用。

**下一步**
- 配置 `COINGLASS_API_KEY`，先把 `auth_missing` 轉成成功 snapshot，再評估是否需要額外歷史 backfill。
- 驗證：`data/execution_metadata_smoke.json`、`/api/features/coverage`、下輪 heartbeat source blockers。

### P1. leaderboard recent-window governance must stay stable
**現況**
- `leaderboard_count=4`
- `selected_feature_profile=core_only`
- `support_aware_production_profile=core_plus_macro`
- `governance_contract=dual_role_governance_active`
- `current_closure=global_ranking_vs_support_aware_production_split`
- `leaderboard_payload_source=latest_persisted_snapshot`

**風險**
- 如果排行榜又回退成 placeholder-only、或把 production fallback 誤寫成 parity blocker，Strategy Lab 會再次失去可信 ranking semantics。

**下一步**
- 維持 recent-window + dual-role governance contract，避免把 support-aware production fallback 誤報成 drift/blocker。
- 驗證：browser `/lab`、`curl /api/models/leaderboard`、`pytest tests/test_model_leaderboard.py tests/test_strategy_lab.py tests/test_frontend_decision_contract.py -q`。

---

## Not Issues
- **/api/status 把 current_live q15 support truth 回成 null**：不是 current issue；本輪已修成 `execution.live_runtime_truth` 頂層可 machine-read `current_live_structure_bucket / rows / gap / support_governance_route`。
- **data pipeline frozen**：不是；本輪 collect 實際新增 `+1 raw / +1 features / +31 labels`。
- **q35 仍是 current-live bucket**：不是；本輪 current-live 已切到 `q15`，q35 scaling audit 只剩 `reference_only_current_bucket_outside_q35`。

---

## Current Priority
1. **維持 breaker-first truth，同時守住 top-level q15 current-live bucket visibility across API / UI / docs**
2. **持續鑽 recent canonical 250-row pathology，而不是 generic 化 blocker**
3. **維持 q15 `0/50 + exact_bucket_missing_proxy_reference_only + reference_only_until_exact_support_ready` 的 patch visibility**
4. **保留 per-venue blockers 與 CoinGlass auth blocker，可見直到真實 closure**
