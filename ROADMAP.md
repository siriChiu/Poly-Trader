# ROADMAP.md — Current Plan Only

_最後更新：2026-04-19 08:14 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **fast heartbeat `#20260419c` + collect 成功**：`Raw=31074 (+2) / Features=22491 (+1) / Labels=62568 (+1)`；資料管線不是 frozen。
- **本輪產品化 patch 已完成 venue readiness 可視化 closure**：`web/src/components/VenueReadinessSummary.tsx` 新增 per-venue readiness cards，Strategy Lab `/lab` 與 Dashboard execution summary 現在都直接顯示 `config enabled/disabled`、`creds configured/public-only`、`metadata OK/FAIL`、`step/tick/min qty/min cost`、以及 `missing runtime proof`。
- **本輪驗證完成**：
  - `source venv/bin/activate && PYTHONPATH=. pytest tests/test_frontend_decision_contract.py tests/test_server_startup.py -q` → `43 passed`
  - `cd web && npm run build` 成功
  - browser `/lab`：已看到 `current live blocker`、`venue blockers`、`binance / okx` per-venue readiness cards、`recommended_patch=core_plus_macro`、console 無 JS exception
- **Architecture contract 已同步**：`ARCHITECTURE.md` 新增 Dashboard / Strategy Lab 的 venue-readiness summary contract，避免 operator 再把單一 blocker 字串誤讀成 venue closure。

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=circuit_breaker_active`
- `recent 50 wins=0/50`
- `additional_recent_window_wins_needed=15`
- `streak=238`
- `allowed_layers=0`

**成功標準**
- `/lab`、`/execution/status`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`issues.json`、`ISSUES.md` 全部一致把 breaker 視為唯一 current-live deployment blocker。

### 目標 B：維持 q15 `0/50` exact support shortage 的 support-aware governance
**目前真相**
- `current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15`
- `live_current_structure_bucket_rows=0 / minimum_support_rows=50`
- `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`
- `support_progress.status=stalled_under_minimum`
- `leaderboard_selected_profile=core_only`
- `train_selected_profile=core_plus_macro`
- `governance_contract=dual_role_governance_active`

**成功標準**
- probe / API / Strategy Lab / Execution Status / docs 都一致承認 `0/50 + exact_bucket_missing_exact_lane_proxy_only + gap_to_minimum=50`；
- breaker path 下不遮蔽 support metadata，也不把 broader spillover patch 誤當 exact support closure。

### 目標 C：維持 spillover patch parity closure，且嚴格保持 reference-only semantics
**目前真相**
- broader spillover：`bull|CAUTION 200 rows / WR=0.0% / quality=-0.2945 / pnl=-1.09%`
- `recommended_patch=core_plus_macro`
- `recommended_patch.status=reference_only_until_exact_support_ready`
- `collapse_features=feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`

**成功標準**
- 所有 surface 都讀同一份 patch summary；
- 在 exact support 達 `50` rows 前，任何 surface 都不把它包裝成 deployable patch。

### 目標 D：持續保留 venue blockers，直到 runtime artifact 真正 closure
**目前真相**
- `binance=config enabled + public-only`
- `okx=config disabled + public-only`
- `/lab`、Dashboard、`/execution/status` 都已可見 per-venue readiness truth
- 缺的 proof 仍是 `live exchange credential / order ack lifecycle / fill lifecycle`

**成功標準**
- 即使 breaker 未來解除，`/lab`、Dashboard、`/execution/status` 仍會保留 per-venue blockers，直到 credentials / ack / fill 各自都有 runtime proof。

### 目標 E：解除 sparse-source ETF flow auth blocker
**目前真相**
- `fin_netflow=source_auth_blocked`
- `COINGLASS_API_KEY` 缺失
- `forward_archive_rows=2545`
- `archive_window_coverage_pct=0.0%`

**成功標準**
- `fin_netflow` 從 `auth_missing` 轉成成功 snapshot source；
- heartbeat source blockers 不再把 ETF flow 列為 auth blocker。

---

## 下一步
1. **維持 breaker-first truth 與 support-aware governance 不回退**
   - 驗證：`python scripts/hb_predict_probe.py`、`python scripts/hb_q15_support_audit.py`、browser `/lab`、browser `/execution/status`
2. **把 `recommended_patch` 持續保留為單一真相，直到 exact support 達標才談 deployable promotion**
   - 驗證：`python scripts/live_decision_quality_drilldown.py`、targeted pytest、browser `/lab`
3. **持續保留 per-venue readiness cards，直到 credentials / ack / fill 有 runtime closure**
   - 驗證：browser `/lab`、browser `/execution/status`、`data/execution_metadata_smoke.json`
4. **解除 `fin_netflow` auth blocker**
   - 驗證：`data/heartbeat_20260419c_summary.json` source blockers、`/api/features/coverage`

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- `q15 support 0/50 + gap_to_minimum=50` 在 breaker path 下仍完整暴露於 probe / API / UI / docs
- `recommended_patch=core_plus_macro` 在 API / UI / probe / drilldown / heartbeat 全部一致，且明確標為 `reference_only_until_exact_support_ready`
- Strategy Lab / Dashboard / Execution Status 保持：**breaker-first truth 清楚、per-venue blockers 保留、runtime console 無 JS exception**
- heartbeat 維持：**issue 對齊 → patch → verify → docs overwrite → commit → push**
