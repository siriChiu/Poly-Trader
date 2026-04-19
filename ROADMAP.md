# ROADMAP.md — Current Plan Only

_最後更新：2026-04-19 09:36 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **fast heartbeat `#20260419h` + collect 成功**：`Raw=31081 (+1) / Features=22499 (+1) / Labels=62573 (+1)`；`240m`、`1440m` freshness 仍屬 expected horizon lag，資料管線不是 frozen。
- **本輪產品化 patch 已修復 current-state issue drift**：`scripts/auto_propose_fixes.py` 現在會優先使用 `live_predict_probe.json` 的 `support_route_verdict` 作為 canonical q15 issue truth，並把 `current_live_structure_bucket / current_live_structure_bucket_rows / gap_to_minimum / runtime_closure_state` 同步回寫 breaker issue；`issues.json` 不再卡在上一輪的 bull q15 bucket 與錯誤 route。
- **本輪驗證完成**：
  - `source venv/bin/activate && PYTHONPATH=. pytest tests/test_auto_propose_fixes.py tests/test_live_pathology_summary.py tests/test_hb_predict_probe.py::test_hb_predict_probe_surfaces_recommended_patch_summary_for_bull_caution_spillover tests/test_live_decision_quality_drilldown.py::test_live_decision_quality_drilldown_surfaces_recommended_patch_summary tests/test_server_startup.py::test_build_live_runtime_closure_surface_surfaces_bull_caution_patch_summary tests/test_frontend_decision_contract.py::test_live_pathology_summary_card_surfaces_recommended_patch_contract -q` → `28 passed`
  - `source venv/bin/activate && PYTHONPATH=. python scripts/auto_propose_fixes.py` 成功，`issues.json` 已刷新成 `q15 0/50 + exact_bucket_missing_exact_lane_proxy_only + current bucket=CAUTION|base_caution_regime_or_bias|q15`
  - browser `/lab`：看到 `current live blocker=circuit_breaker_active`、`support 0 / 50`、`exact live lane rows 0`、`bull|BLOCK spillover 199 rows`、Binance/OKX venue blockers，且無 JS exception
  - browser `/execution/status`：看到 `deployment blocker=circuit_breaker_active`、`current bucket=CAUTION|base_caution_regime_or_bias|q15`、`support 0 / 50`、per-venue readiness、無 JS exception
- **Current-state docs 已覆蓋同步**：`ISSUES.md`、`ROADMAP.md`、`issues.json` 現在只保留本輪最新 truth，移除舊的 bull q15 `1/50 + core_plus_macro reference-only` 敘事。

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=circuit_breaker_active`
- `recent 50 wins=0/50`
- `additional_recent_window_wins_needed=15`
- `streak=240`
- `allowed_layers=0`
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`

**成功標準**
- `/lab`、`/execution/status`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`issues.json`、`ISSUES.md` 全部一致把 breaker 視為唯一 current-live deployment blocker，且 current bucket context 不回退成上一輪 bull bucket。

### 目標 B：維持 q15 `0/50` exact-support shortage 的 machine-read truth
**目前真相**
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`
- `live_current_structure_bucket_rows=0 / minimum_support_rows=50`
- `gap_to_minimum=50`
- `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`
- `support_governance_route=exact_live_bucket_proxy_available`
- `support_progress.status=no_recent_comparable_history`
- `leaderboard_selected_profile=core_only`
- `train_selected_profile=core_plus_macro`

**成功標準**
- probe / API / Strategy Lab / Execution Status / docs / `issues.json` 都一致承認 `0/50 + exact_bucket_missing_exact_lane_proxy_only + exact_live_bucket_proxy_available`；
- breaker path 下不遮蔽 q15 support metadata，也不把 proxy lane 包裝成 exact support closure。

### 目標 C：維持 exact live lane vs broader spillover 對照
**目前真相**
- exact live lane：`rows=0`
- broader spillover：`bull|BLOCK`、`199 rows`、`WR 0.0%`、`avg_quality=-0.2853`
- top 4H shifts：`feat_4h_bias200`、`feat_4h_dist_bb_lower`、`feat_4h_dist_swing_low`
- current live pathology summary **沒有** bull-specific reference patch

**成功標準**
- `/lab`、`/execution/status`、`live_decision_quality_drilldown.py` 都能顯示相同的 exact-vs-spillover 摘要；
- 任何 surface 都不能把 `bull|BLOCK` broader toxic rows 誤當成 current q15 exact lane truth。

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
- forward archive 已持續累積，但 `archive_window_coverage_pct=0.0%`

**成功標準**
- `fin_netflow` 從 `auth_missing` 轉成成功 snapshot source；
- heartbeat source blockers 不再把 ETF flow 列為 auth blocker。

---

## 下一步
1. **維持 breaker-first truth 與 current bucket context 不回退**
   - 驗證：`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、browser `/lab`、browser `/execution/status`
2. **維持 q15 `0/50` exact-support metadata 的單一真相**
   - 驗證：`python scripts/hb_q15_support_audit.py`、`python scripts/auto_propose_fixes.py` 後檢查 `issues.json`、`ISSUES.md`
3. **維持 exact-live-lane vs broader spillover 對照，不讓 broader toxic pocket 汙染 current-live 敘事**
   - 驗證：`python scripts/live_decision_quality_drilldown.py`、browser `/lab`、browser `/execution/status`
4. **持續保留 per-venue readiness cards，直到 credentials / ack / fill 有 runtime closure**
   - 驗證：browser `/lab`、browser `/execution/status`、`data/execution_metadata_smoke.json`
5. **解除 `fin_netflow` auth blocker**
   - 驗證：`data/heartbeat_20260419h_summary.json` source blockers、`/api/features/coverage`

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- `q15 support 0/50 + exact_bucket_missing_exact_lane_proxy_only + exact_live_bucket_proxy_available` 在 breaker path 下仍完整暴露於 probe / API / UI / docs / issues
- Strategy Lab / Execution Status 保持：**breaker-first truth 清楚、exact-vs-spillover 對照可見、per-venue blockers 保留、runtime console 無 JS exception**
- heartbeat 維持：**issue 對齊 → patch → verify → docs overwrite → commit → push**
