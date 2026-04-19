# ROADMAP.md — Current Plan Only

_最後更新：2026-04-19 10:01 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **fast heartbeat `#20260419j` + collect 成功**：`Raw=31084 (+1) / Features=22502 (+1) / Labels=62576 (+1)`；`240m`、`1440m` freshness 仍屬 expected horizon lag，資料管線不是 frozen。
- **本輪產品化 patch：修復 auto-propose breaker streak 對齊**
  - `scripts/auto_propose_fixes.py` 移除 `_latest_zero_streak()` 的硬編碼 `LIMIT 200`
  - 改成 `timestamp DESC, id DESC`，避免 backfill/out-of-order IDs 讓 streak 與 canonical breaker math 分裂
  - `#H_AUTO_STREAK`、auto-propose 摘要、heartbeat summary 現在都與 `hb_circuit_breaker_audit.py` / `live_predict_probe.json` 對齊為 **241**
- **heartbeat docs-sync guardrail 已落地並驗證**
  - `scripts/hb_parallel_runner.py` 現在會把 `ISSUES.md` / `ROADMAP.md` 與 `issues.json`、`data/live_predict_probe.json`、`data/live_decision_quality_drilldown.json` 的新鮮度一起寫進 summary
  - 若 current-state docs 落後最新 artifact，runner 會明示 `docs_sync.stale_docs` 並把該輪標成 `completed_with_failures`
- **本輪驗證完成**：
  - `source venv/bin/activate && PYTHONPATH=. pytest tests/test_auto_propose_fixes.py -q` → `25 passed`
  - `source venv/bin/activate && PYTHONPATH=. pytest tests/test_hb_parallel_runner.py::test_collect_current_state_docs_sync_status_flags_stale_docs tests/test_hb_parallel_runner.py::test_save_summary_uses_run_label_and_persists_source_blockers -q` → `2 passed`
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 20260419j` 成功，`#H_AUTO_STREAK` 已從錯誤的 `200` 更正為 `241`
  - browser `/lab`：看到 `current live blocker=circuit_breaker_active`、`support 1/50`、`bucket=BLOCK|bull_q15_bias50_overextended_block|q15`、`core_plus_macro reference-only patch`、Binance/OKX venue blockers，且無 JS exception
  - browser `/execution/status`：看到 `deployment blocker=circuit_breaker_active`、`support 1/50`、`active sleeves 0/4`、`bucket=BLOCK|bull_q15_bias50_overextended_block|q15`、per-venue readiness，且無 JS exception
- **Current-state docs 已覆蓋同步**：`ISSUES.md`、`ROADMAP.md`、`issues.json` 現在只保留本輪最新 truth，移除舊的 `q15 0/50` 與 `#H_AUTO_STREAK=200` 敘事。

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=circuit_breaker_active`
- `recent 50 wins=0/50`
- `additional_recent_window_wins_needed=15`
- `streak=241`
- `allowed_layers=0`
- `current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15`

**成功標準**
- `/lab`、`/execution/status`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`issues.json`、`ISSUES.md` 全部一致把 breaker 視為唯一 current-live deployment blocker。
- `#H_AUTO_STREAK` 與 breaker audit / live probe streak 完全一致，不再出現 tracker 低報 breaker 嚴重度。

### 目標 B：維持 q15 `1/50` exact-support shortage 的 machine-read truth
**目前真相**
- `current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15`
- `live_current_structure_bucket_rows=1 / minimum_support_rows=50`
- `gap_to_minimum=49`
- `support_route_verdict=exact_bucket_present_but_below_minimum`
- `support_progress.status=stalled_under_minimum`
- `leaderboard_selected_profile=core_only`
- `train_selected_profile=core_plus_macro`

**成功標準**
- probe / API / Strategy Lab / Execution Status / docs / `issues.json` 都一致承認 `1/50 + exact_bucket_present_but_below_minimum + stalled_under_minimum`；
- breaker path 下不遮蔽 q15 support metadata，也不把 proxy/reference patch 包裝成 exact support closure。

### 目標 C：維持 exact live lane vs spillover 對照與 patch 可見性
**目前真相**
- exact live lane：`rows=199`、`WR=0.0%`、`quality=-0.2855`
- broader spillover：`bull|BLOCK`、`1 row`、`WR=0.0%`、`quality=-0.314`
- `recommended_patch=core_plus_macro`
- `recommended_patch_status=reference_only_until_exact_support_ready`

**成功標準**
- `/lab`、`/execution/status`、`live_decision_quality_drilldown.py` 都能顯示相同的 exact-vs-spillover 摘要與 patch reference；
- 任何 surface 都不能把 `core_plus_macro` reference patch 誤當 current-live runtime closure。

### 目標 D：持續保留 venue blockers，直到 runtime artifact 真正 closure
**目前真相**
- `binance=config enabled + public-only`
- `okx=config disabled + public-only`
- `/lab`、`/execution/status` 都已可見 per-venue readiness truth
- 缺的 proof 仍是 `live exchange credential / order ack lifecycle / fill lifecycle`

**成功標準**
- 即使 breaker 未來解除，`/lab`、`/execution/status` 仍會保留 per-venue blockers，直到 credentials / ack / fill 各自都有 runtime proof。

### 目標 E：解除 sparse-source ETF flow auth blocker
**目前真相**
- `fin_netflow=source_auth_blocked`
- `COINGLASS_API_KEY` 缺失
- `forward_archive_rows=2555`
- `archive_window_coverage_pct=0.0%`

**成功標準**
- `fin_netflow` 從 `auth_missing` 轉成成功 snapshot source；
- heartbeat source blockers 不再把 ETF flow 列為 auth blocker。

---

## 下一步
1. **維持 breaker-first truth 與 streak 對齊不回退**
   - 驗證：`pytest tests/test_auto_propose_fixes.py -q`、`python scripts/hb_parallel_runner.py --fast --hb <N>`、檢查 `issues.json` 的 `#H_AUTO_STREAK` 是否等於 `live_predict_probe.streak`
2. **維持 q15 `1/50` exact-support metadata 的單一真相**
   - 驗證：`python scripts/hb_q15_support_audit.py`、`python scripts/hb_predict_probe.py`、browser `/lab`、browser `/execution/status`
3. **維持 exact-live-lane vs spillover 對照與 `core_plus_macro` reference-only patch 可見**
   - 驗證：`python scripts/live_decision_quality_drilldown.py`、browser `/lab`、browser `/execution/status`
4. **持續保留 per-venue readiness cards，直到 credentials / ack / fill 有 runtime closure**
   - 驗證：browser `/lab`、browser `/execution/status`、`data/execution_metadata_smoke.json`
5. **解除 `fin_netflow` auth blocker**
   - 驗證：`data/heartbeat_20260419j_summary.json` source blockers、`/api/features/coverage`

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- `q15 support 1/50 + exact_bucket_present_but_below_minimum + stalled_under_minimum` 在 breaker path 下仍完整暴露於 probe / API / UI / docs / issues
- Strategy Lab / Execution Status 保持：**breaker-first truth 清楚、exact-vs-spillover 對照可見、per-venue blockers 保留、runtime console 無 JS exception**
- auto-propose / issues current-state 與 breaker audit 保持：**streak math 無 drift**
- heartbeat 維持：**issue 對齊 → patch → verify → docs overwrite → commit → push**
