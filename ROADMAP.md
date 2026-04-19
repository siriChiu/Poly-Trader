# ROADMAP.md — Current Plan Only

_最後更新：2026-04-19 10:36 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **fast heartbeat `#20260419l` + collect 成功**：`Raw=31086 (+1) / Features=22504 (+1) / Labels=62580 (+0)`；`240m`、`1440m` freshness 仍屬 expected horizon lag，資料管線不是 frozen。
- **本輪產品化 patch：修復 leaderboard governance stale-cache refresh**
  - `scripts/hb_leaderboard_candidate_probe.py` 現在遇到 stale leaderboard cache / persisted snapshot 時，會先 live-rebuild leaderboard payload 並回寫 cache/snapshot，再輸出 probe artifact。
  - `scripts/hb_parallel_runner.py` refresh candidate alignment artifact 時改成走 `allow_rebuild=True`，不再把 stale snapshot 重新包裝成 fresh governance truth。
- **本輪驗證完成**：
  - `source venv/bin/activate && PYTHONPATH=. pytest tests/test_hb_leaderboard_candidate_probe.py tests/test_hb_parallel_runner.py -q` → `77 passed`
  - `source venv/bin/activate && python scripts/hb_leaderboard_candidate_probe.py` 成功，`data/leaderboard_feature_profile_probe.json` 顯示 `leaderboard_payload_updated_at=2026-04-19T02:31:45.190677Z`、`leaderboard_payload_stale=false`、`snapshot_stale=false`
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 20260419l` 成功，summary 顯示 `snapshot_stale=False`
  - browser `http://127.0.0.1:5173/lab`：看到 `current live blocker=circuit_breaker_active`、`support 0/50`、`gate=CAUTION`、`bucket=CAUTION|base_caution_regime_or_bias|q15`、Binance/OKX venue blockers，且無 JS exception
  - browser `http://127.0.0.1:5173/execution/status`：看到 `deployment blocker=circuit_breaker_active`、`support 0/50`、`active sleeves 0/4`、`bucket=CAUTION|base_caution_regime_or_bias|q15`、per-venue readiness，且無 JS exception
- **Current-state docs 已覆蓋同步**：`ISSUES.md`、`ROADMAP.md`、`issues.json` 現在只保留本輪最新 truth，移除舊的 `1/50` q15 敘事與 stale leaderboard snapshot 敘事。

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=circuit_breaker_active`
- `recent 50 wins=0/50`
- `additional_recent_window_wins_needed=15`
- `streak=242`
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
- `support_governance_route=exact_live_lane_proxy_available`
- `support_progress.status=stalled_under_minimum`

**成功標準**
- probe / API / Strategy Lab / Execution Status / docs / `issues.json` 都一致承認 `0/50 + exact_bucket_missing_exact_lane_proxy_only + exact_live_lane_proxy_available + stalled_under_minimum`；
- breaker path 下不遮蔽 q15 support metadata，也不把 proxy/reference 治理語義誤報成 exact support closure。

### 目標 C：維持 exact live lane 0 rows vs `bull|BLOCK` spillover 199 rows 的對照
**目前真相**
- exact live lane：`rows=0`、`bucket=CAUTION|base_caution_regime_or_bias|q15`
- broader spillover：`bull|BLOCK`、`199 rows`、`WR=0.0%`、`quality=-0.2856`
- chosen scope：`global`

**成功標準**
- `/lab`、`/execution/status`、`live_decision_quality_drilldown.py` 都能顯示相同的 exact-vs-spillover 摘要；
- 任何 surface 都不能把 `bull|BLOCK` spillover 病灶誤當成 current-live exact lane closure 依據。

### 目標 D：維持 leaderboard governance cache freshness 與雙角色治理
**目前真相**
- `leaderboard_payload_source=model_leaderboard_cache`
- `leaderboard_payload_stale=false`
- `artifact_recency.alignment_snapshot_stale=false`
- `global_profile=core_only`
- `production_profile=core_plus_macro`
- `governance_contract=dual_role_governance_active`

**成功標準**
- stale cache 再出現時，candidate probe / fast heartbeat 會先 refresh 再判讀 governance；
- Strategy Lab / heartbeat summary 不再建立在舊 leaderboard snapshot 上。

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
- `forward_archive_rows=2557`
- `archive_window_coverage_pct=0.0%`

**成功標準**
- `fin_netflow` 從 `auth_missing` 轉成成功 snapshot source；
- heartbeat source blockers 不再把 ETF flow 列為 auth blocker。

---

## 下一步
1. **維持 breaker-first truth 與 release math 不回退**
   - 驗證：`python scripts/hb_parallel_runner.py --fast --hb <N>`、`python scripts/hb_predict_probe.py`、browser `/lab`、browser `/execution/status`
2. **維持 q15 `0/50 + exact_bucket_missing_exact_lane_proxy_only + exact_live_lane_proxy_available` 的單一真相**
   - 驗證：`python scripts/hb_q15_support_audit.py`、`python scripts/hb_predict_probe.py`、browser `/lab`、browser `/execution/status`
3. **維持 exact live lane 0 rows vs `bull|BLOCK` spillover 199 rows 的對照可見**
   - 驗證：`python scripts/live_decision_quality_drilldown.py`、browser `/lab`、browser `/execution/status`
4. **防止 leaderboard stale snapshot regression**
   - 驗證：`pytest tests/test_hb_leaderboard_candidate_probe.py tests/test_hb_parallel_runner.py -q`、`python scripts/hb_leaderboard_candidate_probe.py`、檢查 `data/leaderboard_feature_profile_probe.json` 的 `leaderboard_payload_stale=false` 與 `alignment_snapshot_stale=false`
5. **持續保留 per-venue readiness cards，直到 credentials / ack / fill 有 runtime closure**
   - 驗證：browser `/lab`、browser `/execution/status`、`data/execution_metadata_smoke.json`
6. **解除 `fin_netflow` auth blocker**
   - 驗證：`data/heartbeat_20260419l_summary.json` source blockers、`/api/features/coverage`

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- `q15 support 0/50 + exact_bucket_missing_exact_lane_proxy_only + exact_live_lane_proxy_available` 在 breaker path 下仍完整暴露於 probe / API / UI / docs / issues
- Strategy Lab / Execution Status 保持：**breaker-first truth 清楚、exact-vs-spillover 對照可見、per-venue blockers 保留、runtime console 無 JS exception**
- leaderboard governance 保持：**stale cache 先 refresh，再判讀雙角色治理；不再出現 `snapshot_stale=true` 的假 alignment**
- heartbeat 維持：**issue 對齊 → patch → verify → docs overwrite → commit → push**
