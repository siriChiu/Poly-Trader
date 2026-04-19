# ROADMAP.md — Current Plan Only

_最後更新：2026-04-19 11:09 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **fast heartbeat `#20260419n` + collect 成功**：`Raw=31089 (+1) / Features=22507 (+1) / Labels=62582 (+0)`；`240m / 1440m` freshness 仍屬 expected horizon lag，資料管線不是 frozen。
- **本輪產品化 patch：修復 Live lane / spillover 卡片的 sample-size 歧義**
  - `web/src/components/LivePathologySummaryCard.tsx` 現在會同時顯示 `focus_scope_rows` 與 `spillover rows`。
  - 右側標題改成依 `focus_scope_label` 派生的 `spillover pocket`，不再把 extra pocket rows 誤當成整個 wider scope 的總樣本。
  - `ARCHITECTURE.md` 已同步補上 `focus_scope_rows + spillover.extra_rows` 的 UI contract。
  - `tests/test_frontend_decision_contract.py` 已新增 regression，鎖住這個 product contract。
- **本輪驗證完成**：
  - `source venv/bin/activate && PYTHONPATH=. pytest tests/test_frontend_decision_contract.py -q` → `15 passed`
  - `cd web && npm run build` → 成功
  - browser `http://127.0.0.1:5173/lab`：看到 breaker-first truth、`support 0/50`、`CAUTION|base_caution_regime_or_bias|q15`、`focus scope rows + spillover rows`、Binance/OKX venue cards，且無 JS exception
  - browser `http://127.0.0.1:5173/execution/status`：看到 `deployment_blocker=circuit_breaker_active`、`support 0/50`、`active sleeves 0/4`、`bucket=CAUTION|base_caution_regime_or_bias|q15`、per-venue readiness，且無 JS exception
- **Current-state docs 已覆蓋同步**：`ISSUES.md`、`ROADMAP.md`、`issues.json` 現在只保留本輪最新 truth；`ARCHITECTURE.md` 已同步記錄本輪 UI contract 更新。

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=circuit_breaker_active`
- `recent 50 wins=0/50`
- `additional_recent_window_wins_needed=15`
- `streak=243`
- `allowed_layers=0`
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`

**成功標準**
- `/lab`、`/execution/status`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`issues.json`、`ISSUES.md` 全部一致把 breaker 視為唯一 current-live deployment blocker。

### 目標 B：維持 q15 `0/50` exact-support shortage 與 proxy route 的 machine-read truth
**目前真相**
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`
- `live_current_structure_bucket_rows=0 / minimum_support_rows=50`
- `gap_to_minimum=50`
- `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`
- `support_governance_route=exact_live_bucket_proxy_available`
- `support_progress.status=stalled_under_minimum`

**成功標準**
- probe / API / Strategy Lab / Execution Status / docs / `issues.json` 都一致承認 `0/50 + exact_bucket_missing_exact_lane_proxy_only + exact_live_bucket_proxy_available + stalled_under_minimum`；
- breaker path 下不遮蔽 q15 support metadata，也不把 proxy / governance fallback 誤報成 exact support closure。

### 目標 C：維持 exact live lane 0 rows vs 同 quality 寬 scope `bull|BLOCK` 199 rows 的對照，並保留 scope-row context
**目前真相**
- exact live lane：`rows=0`、`bucket=CAUTION|base_caution_regime_or_bias|q15`
- focus scope：`同 quality 寬 scope`、`focus_scope_rows=199`
- spillover pocket：`bull|BLOCK`、`spillover_rows=199`、`WR=0.0%`、`quality=-0.2857`
- 本輪 UI contract 已補：卡片同時顯示 `focus_scope_rows` 與 `spillover rows`

**成功標準**
- `/lab`、Dashboard、`/api/status`、`/api/predict/confidence` 都能顯示相同的 exact-vs-spillover 摘要；
- 任何 surface 都不能把 extra pocket rows 誤讀成 wider scope 的全部樣本。

### 目標 D：修復 leaderboard governance alignment snapshot stale
**目前真相**
- `leaderboard_payload_stale=false`
- `alignment_snapshot_stale=true`
- `stale_against_bull_pocket=true`
- `global_profile=core_only`
- `production_profile=core_plus_macro`
- `governance_contract=dual_role_governance_active`

**成功標準**
- bull pocket artifact 更新時，candidate alignment snapshot 會自動 refresh；
- `data/leaderboard_feature_profile_probe.json` 回到 `alignment_snapshot_stale=false`，再判讀 governance split。

### 目標 E：持續保留 venue blockers，直到 runtime artifact 真正 closure
**目前真相**
- `binance=config enabled + public-only`
- `okx=config disabled + public-only`
- `/lab`、`/execution/status` 都已可見 per-venue readiness truth
- 缺的 proof 仍是 `live exchange credential / order ack lifecycle / fill lifecycle`

**成功標準**
- 即使 breaker 未來解除，`/lab`、`/execution/status` 仍會保留 per-venue blockers，直到 credentials / ack / fill 各自都有 runtime proof。

### 目標 F：解除 sparse-source ETF flow auth blocker
**目前真相**
- `fin_netflow=source_auth_blocked`
- `COINGLASS_API_KEY` 缺失
- `forward_archive_rows=2560`
- `archive_window_coverage_pct=0.0%`

**成功標準**
- `fin_netflow` 從 `auth_missing` 轉成成功 snapshot source；
- heartbeat source blockers 不再把 ETF flow 列為 auth blocker。

---

## 下一步
1. **維持 breaker-first truth 與 release math 不回退**
   - 驗證：`python scripts/hb_parallel_runner.py --fast --hb <N>`、`python scripts/hb_predict_probe.py`、browser `/lab`、browser `/execution/status`
2. **維持 q15 `0/50 + exact_bucket_missing_exact_lane_proxy_only + exact_live_bucket_proxy_available` 的單一真相**
   - 驗證：`python scripts/hb_q15_support_audit.py`、`python scripts/hb_predict_probe.py`、browser `/lab`、browser `/execution/status`
3. **維持 exact live lane 0 rows vs 同 quality 寬 scope `bull|BLOCK` 199 rows 的對照，並保留 `focus_scope_rows` context**
   - 驗證：`pytest tests/test_frontend_decision_contract.py -q`、`cd web && npm run build`、browser `/lab`
4. **修復 leaderboard alignment snapshot stale**
   - 驗證：`python scripts/hb_leaderboard_candidate_probe.py`、檢查 `data/leaderboard_feature_profile_probe.json` 的 `artifact_recency.alignment_snapshot_stale=false`
5. **持續保留 per-venue readiness cards，直到 credentials / ack / fill 有 runtime closure**
   - 驗證：browser `/lab`、browser `/execution/status`、`data/execution_metadata_smoke.json`
6. **解除 `fin_netflow` auth blocker**
   - 驗證：`data/heartbeat_20260419n_summary.json` source blockers、`/api/features/coverage`

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- `q15 support 0/50 + exact_bucket_missing_exact_lane_proxy_only + exact_live_bucket_proxy_available` 在 breaker path 下仍完整暴露於 probe / API / UI / docs / issues
- Strategy Lab / Execution Status 保持：**breaker-first truth 清楚、exact-vs-spillover 對照可見、`focus_scope_rows` context 可見、per-venue blockers 保留、runtime console 無 JS exception**
- leaderboard governance 保持：**payload cache 可用，但 alignment snapshot 必須跟上最新 bull pocket artifact；不再出現 `alignment_snapshot_stale=true` 的假 current-state**
- heartbeat 維持：**issue 對齊 → patch → verify → docs overwrite → commit → push**
