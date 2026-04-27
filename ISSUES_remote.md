# ISSUES.md — Current State Only

_最後更新：2026-04-21 06:42:14 CST_

只保留目前有效問題；由 heartbeat overwrite sync，避免 current-state markdown 落後 live artifacts / issues.json。

---

## 當前主線事實
- **canonical current-live blocker 仍是 exact-support shortage**
  - `deployment_blocker=under_minimum_exact_live_structure_bucket`
  - `current_live_structure_bucket=CAUTION|structure_quality_caution|q35`
  - `support=12/50` / `gap=38`
  - `support_route_verdict=exact_bucket_present_but_below_minimum`
  - `runtime_closure_state=patch_active_but_execution_blocked`
- **recent canonical window 500 仍是 distribution pathology**
  - `win_rate=12.8%` / `dominant_regime=bull(83.8%)`
  - `avg_quality=-0.1547` / `avg_pnl=-0.0056`
  - `alerts=label_imbalance,regime_shift`
- **Strategy Lab detail payload parity 維持正常**
  - `/api/strategies/{name}` 與 leaderboard 仍共用 canonical DQ decoration
- **本輪產品化前進：Execution Status 已改成 blocked-first posture**
  - `/execution/status` 頁首新增 `overall execution posture`
  - `fresh / healthy` 明確降級為 observability-only，而不是 deployability truth
  - `healthy + no_runtime_order` 會顯示 `limited evidence`
  - 私有憑證缺失時頂層改顯示 `metadata-only snapshot`
  - 驗證：`pytest tests/test_frontend_decision_contract.py -q`、`cd web && npm run build`、browser `/execution/status`、browser console 無 JS errors
- **leaderboard / governance 仍是 dual-role current truth**
  - `leaderboard_count=6`
  - `selected_feature_profile=core_only`
  - `support_aware_profile=core_plus_macro`
  - `current_closure=global_ranking_vs_support_aware_production_split`
- **venue / source blockers 仍在**
  - venue：Binance / OKX 仍只有 public-only metadata proof；credential / order ack / fill lifecycle 未驗證
  - `fin_netflow`：`quality_flag=source_auth_blocked` / `latest_status=auth_missing`

---

## Open Issues

### P0. current live bucket q35 exact support remains under minimum (12/50)
- 真相：`under_minimum_exact_live_structure_bucket` / `bucket=CAUTION|structure_quality_caution|q35` / `support=12/50` / `gap=38` / `support_route_verdict=exact_bucket_present_but_below_minimum`
- 下一步：持續把 current-live blocker 固定在 exact-support truth；在 support 補滿前，不能把 same-bucket progress 或 reference patch 誤包裝成 deployment closure。
- 驗證：browser `/`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`

### P0. recent canonical window 500 rows remains distribution_pathology
- 真相：`window=500` / `win_rate=12.8%` / `dominant_regime=bull(83.8%)` / `avg_quality=-0.1547` / `avg_pnl=-0.0056` / `alerts=label_imbalance,regime_shift`
- 下一步：沿 current pathological slice 繼續追 feature variance / distinct-count / target-path；不要退回 generic blocker 敘事。
- 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`

### P1. support-aware patch must stay reference-only until exact support is ready
- 真相：`recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_until_exact_support_ready` / `reference_scope=bull|CAUTION`
- 下一步：維持 `/api/status`、`/execution/status`、`/lab`、probe、drilldown、docs 對同一個 reference-only patch contract 的機器可讀一致性。
- 驗證：browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`

### P1. venue readiness remains unverified
- 真相：Binance / OKX 目前都還停在 metadata / public-only lane；缺 `live exchange credential`、`order ack lifecycle`、`fill lifecycle` runtime-backed proof
- 下一步：持續把 venue blockers 保持在 Dashboard / Execution Status / Strategy Lab 可見，不可被 fresh/healthy 文案稀釋。
- 驗證：browser `/execution`、browser `/execution/status`、browser `/lab`、`data/execution_metadata_smoke.json`

### P1. fin_netflow remains auth-blocked
- 真相：`feature=fin_netflow` / `quality_flag=source_auth_blocked` / `latest_status=auth_missing`
- 下一步：配置 `COINGLASS_API_KEY`，讓 forward archive 與 coverage 開始脫離 `auth_missing`
- 驗證：`data/execution_metadata_smoke.json`、`/api/features/coverage`

### P1. leaderboard recent-window contract must stay stable and comparable
- 真相：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro` / `current_closure=global_ranking_vs_support_aware_production_split`
- 下一步：守住最近兩年 bounded walk-forward、Strategy Lab detail parity、與 dual-role governance，不回退 placeholder-only 或 ambiguous window。
- 驗證：browser `/lab`、`curl http://127.0.0.1:8000/api/models/leaderboard`、`pytest tests/test_model_leaderboard.py tests/test_strategy_lab.py tests/test_frontend_decision_contract.py -q`

---

## Current Priority
1. **維持 exact-support blocker truth = 唯一 current-live blocker**
2. **沿 recent canonical pathological slice 追根因，不讓 generic 摘要稀釋 current blocker**
3. **守住 reference-only patch、venue/source blockers、leaderboard dual-role governance 的 operator-facing 可見性**
