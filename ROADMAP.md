# ROADMAP.md — Current Plan Only

_最後更新：2026-04-19 07:48 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **本輪產品化 patch 已完成 API / UI / probe / drilldown parity**：`bull|CAUTION` spillover 的 `recommended_patch=core_plus_macro` 現在會同步出現在 `/api/status`、Strategy Lab `/lab`、`data/live_predict_probe.json`、`data/live_decision_quality_drilldown.json`、`docs/analysis/live_decision_quality_drilldown.md`。
- **drilldown 直接執行 contract 已補齊**：`python scripts/live_decision_quality_drilldown.py` 現在可從 repo root 直接執行，不再依賴外部手補 `PYTHONPATH=.`。
- **本輪驗證完成**：
  - `source venv/bin/activate && PYTHONPATH=. pytest tests/test_hb_predict_probe.py tests/test_live_decision_quality_drilldown.py tests/test_server_startup.py tests/test_frontend_decision_contract.py -q` → `66 passed`
  - `cd web && npm run build` 成功
  - browser `/lab`：看到 `circuit_breaker_active`、`support 0/50`、`venue blockers`、`recommended patch core_plus_macro`
  - browser `/execution/status`：看到 breaker-first blocker、support `0/50`、Binance/OKX `public-only`
  - browser console：無 JS errors
- **本輪 fast heartbeat + collect 實測前進資料面**：`Raw=31071 / Features=22489 / Labels=62567`；不是 frozen pipeline。

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live blocker，且在 operator surface 清楚可見
**目前真相**
- `deployment_blocker=circuit_breaker_active`
- `recent 50 wins=0/50`
- `additional_recent_window_wins_needed=15`
- `streak=238`
- `allowed_layers=0`

**成功標準**
- `/lab`、`/execution/status`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`issues.json`、`ISSUES.md` 全部一致把 breaker 視為唯一 current-live deployment blocker。

### 目標 B：把 q15 `0/50` exact support shortage 持續維持為可 machine-read 的 support-aware governance
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
- breaker path 下不再遮蔽 support metadata，也不把 spillover patch誤當 exact support closure。

### 目標 C：維持 spillover patch parity closure，且嚴格保持 reference-only semantics
**目前真相**
- broader spillover：`bull|CAUTION 200 rows / WR=0.0% / quality=-0.2945 / pnl=-1.09%`
- `recommended_patch=core_plus_macro`
- `recommended_patch.status=reference_only_until_exact_support_ready`
- `collapse_features=feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`
- parity 已覆蓋到 API / UI / probe / drilldown / docs

**成功標準**
- 所有 surface 都讀同一份 patch summary；
- 在 exact support 達 `50` rows 前，任何 surface 都不把它包裝成 deployable patch。

### 目標 D：持續保留 venue blockers，直到 runtime artifact 真正 closure
**目前真相**
- `binance=config enabled + public-only`
- `okx=config disabled + public-only`
- `live exchange credential / order ack lifecycle / fill lifecycle` 都尚未驗證

**成功標準**
- 即使 breaker 未來解除，`/lab` 與 `/execution/status` 仍會保留 venue blockers，直到 credentials / ack / fill 各自都有 runtime proof。

### 目標 E：解除 sparse-source ETF flow auth blocker
**目前真相**
- `fin_netflow` 仍是 `auth_missing`
- `COINGLASS_API_KEY` 缺失
- forward archive 正在累積，但目前只會記錄 `auth_missing` snapshots

**成功標準**
- `fin_netflow` 從 `auth_missing` 轉成成功 snapshot source；
- heartbeat source blockers 不再把 ETF flow 列為 auth blocker。

---

## 下一步
1. **維持 breaker-first truth 與 support-aware governance 不回退**
   - 驗證：`python scripts/hb_predict_probe.py`、`python scripts/hb_q15_support_audit.py`、browser `/lab`、browser `/execution/status`
2. **把 `recommended_patch` 持續保留為單一真相，直到 exact support 達標才談 deployable promotion**
   - 驗證：`python scripts/live_decision_quality_drilldown.py`、targeted pytest、browser `/lab`
3. **持續保留 venue blockers，直到 credentials / ack / fill 有 runtime closure**
   - 驗證：browser `/lab`、browser `/execution/status`、`data/execution_metadata_smoke.json`
4. **解除 `fin_netflow` auth blocker**
   - 驗證：`data/heartbeat_fast_summary.json` source blockers、`/api/features/coverage`

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- `q15 support 0/50 + gap_to_minimum=50` 在 breaker path 下仍完整暴露於 probe / API / UI / docs
- `recommended_patch=core_plus_macro` 在 API / UI / probe / drilldown / heartbeat 全部一致，且明確標為 `reference_only_until_exact_support_ready`
- Strategy Lab / Execution Status 保持：**blocker truth 清楚、venue blockers 保留、runtime console 無 JS exception**
- heartbeat 維持：**issue 對齊 → patch → verify → docs overwrite → commit → push**
