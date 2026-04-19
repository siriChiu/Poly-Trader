# ROADMAP.md — Current Plan Only

_最後更新：2026-04-19 11:35 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **fast heartbeat `#20260419o` + collect 成功**：`Raw=31090 (+1) / Features=22508 (+1) / Labels=62588 (+6)`；`240m / 1440m` freshness 仍屬 expected horizon lag，資料管線不是 frozen。
- **本輪產品化 patch：清掉已失效的 leaderboard alignment stale issue**
  - `scripts/auto_propose_fixes.py` 現在會在 alignment 已 current 時主動 resolve 舊的 `P1_leaderboard_alignment_snapshot_stale`，避免 `issues.json` / current-state docs 殘留已失效 blocker。
  - `tests/test_auto_propose_fixes.py` 已新增 regression，鎖住「alignment current 時 legacy stale issue 必須被 resolve」。
  - `README.md` 已同步移除過時的 `q15 exact-supported (77/50)` 敘述，改成 current live `0/50 + proxy reference only + breaker-first` truth。
- **本輪驗證完成**：
  - `source venv/bin/activate && pytest tests/test_auto_propose_fixes.py -q` → `26 passed`
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 20260419o` → 成功，並刷新 `data/heartbeat_20260419o_summary.json`
  - `source venv/bin/activate && python scripts/hb_leaderboard_candidate_probe.py` → `alignment_snapshot_stale=false`、`leaderboard_payload_source=live_rebuild`
  - `source venv/bin/activate && python scripts/auto_propose_fixes.py` → `issues.json` 已不再保留 `P1_leaderboard_alignment_snapshot_stale`
  - browser `http://127.0.0.1:5173/lab`：看到 breaker-first truth、q15 `0/50`、exact-vs-spillover 對照、Binance/OKX venue cards，且無 JS exception
  - browser `http://127.0.0.1:5173/execution/status`：看到 `deployment_blocker=circuit_breaker_active`、`support 0/50`、`bucket=CAUTION|base_caution_regime_or_bias|q15`、per-venue readiness，且無 JS exception
- **Current-state docs 已覆蓋同步**：`ISSUES.md`、`ROADMAP.md` 已改成最新 truth；`issues.json` 由 `auto_propose_fixes.py` 重新寫成 current-state。

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=circuit_breaker_active`
- `recent 50 wins=0/50`
- `additional_recent_window_wins_needed=15`
- `streak=244`
- `allowed_layers=0`
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`

**成功標準**
- `/lab`、`/execution/status`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`issues.json`、`ISSUES.md` 全部一致把 breaker 視為唯一 current-live deployment blocker。

### 目標 B：維持 q15 `0/50` exact-support shortage 與 stalled-under-minimum truth
**目前真相**
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`
- `live_current_structure_bucket_rows=0 / minimum_support_rows=50`
- `gap_to_minimum=50`
- `support_route_verdict=exact_bucket_missing_proxy_reference_only`
- `support_governance_route=exact_live_bucket_proxy_available`
- `support_progress.status=stalled_under_minimum`
- `support_progress.stagnant_run_count=4`
- `support_progress.escalate_to_blocker=true`

**成功標準**
- probe / API / Strategy Lab / Execution Status / docs / `issues.json` 都一致承認 `0/50 + exact_bucket_missing_proxy_reference_only + exact_live_bucket_proxy_available + stalled_under_minimum + escalate_to_blocker=true`；
- breaker path 下不遮蔽 q15 support metadata，也不把 proxy / governance fallback 誤報成 exact support closure。

### 目標 C：維持 exact live lane 0 rows vs `bull|BLOCK` spillover 199 rows 的對照可見
**目前真相**
- exact live lane：`rows=0`、`bucket=CAUTION|base_caution_regime_or_bias|q15`
- spillover pocket：`bull|BLOCK`、`rows=199`、`WR=0.0%`、`quality=-0.2857`
- Strategy Lab / Execution Status 都可直接看到 breaker-first truth、exact-vs-spillover 對照與 venue cards

**成功標準**
- `/lab`、`/execution/status`、`/api/status`、`/api/predict/confidence` 都能顯示相同的 exact-vs-spillover 摘要；
- 任何 surface 都不能把 `bull|BLOCK` spillover 當成 exact live lane 的可部署證據。

### 目標 D：維持 leaderboard governance current truth，避免 stale blocker 回歸
**目前真相**
- `leaderboard_payload_source=live_rebuild`
- `alignment_snapshot_stale=false`
- `current_alignment_inputs_stale=false`
- `global_profile=core_only`
- `production_profile=core_plus_macro`
- `governance_contract=dual_role_governance_active`
- `comparable_count=0 / placeholder_count=6`

**成功標準**
- `issues.json`、`ISSUES.md`、`ROADMAP.md` 不再把已 resolved 的 alignment stale 當 current blocker；
- Strategy Lab 繼續把 placeholder-only leaderboard 明示成不可部署 ranking，不讓 operator 把 `#1` 當成真排名。

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
- `forward_archive_rows=2561`
- `archive_window_coverage_pct=0.0%`

**成功標準**
- `fin_netflow` 從 `auth_missing` 轉成成功 snapshot source；
- heartbeat source blockers 不再把 ETF flow 列為 auth blocker。

---

## 下一輪 gate
1. **維持 breaker-first truth 與 release math 不回退**
   - 驗證：`python scripts/hb_parallel_runner.py --fast --hb <N>`、`python scripts/hb_predict_probe.py`、browser `/lab`、browser `/execution/status`
   - 升級 blocker：若任何 surface 把 q15 / spillover / venue blocker 排到 breaker 前面
2. **把 q15 `0/50` 停滯 4 輪的 support truth 維持 machine-read，直到 rows 真正增加**
   - 驗證：`python scripts/hb_q15_support_audit.py`、`python scripts/hb_predict_probe.py`、檢查 `stagnant_run_count` 與 `escalate_to_blocker`
   - 升級 blocker：若 docs / issues / UI 遺失 `exact_bucket_missing_proxy_reference_only` 或 `escalate_to_blocker=true`
3. **維持 leaderboard governance current truth 與 placeholder-only warning，不讓 stale alignment blocker 回歸**
   - 驗證：`python scripts/hb_leaderboard_candidate_probe.py`、`python scripts/auto_propose_fixes.py`、檢查 `alignment_snapshot_stale=false`、browser `/lab`
   - 升級 blocker：若 `issues.json` 或 current-state docs 再次殘留已 resolved 的 stale alignment issue，或 Strategy Lab 把 placeholder row 誤讀成 deployment ranking
4. **持續保留 per-venue readiness cards，直到 credentials / ack / fill 有 runtime closure**
   - 驗證：browser `/lab`、browser `/execution/status`、`data/execution_metadata_smoke.json`
   - 升級 blocker：若 venue blockers 從 operator surface 消失
5. **解除 `fin_netflow` auth blocker**
   - 驗證：`data/heartbeat_<N>_summary.json` source blockers、`/api/features/coverage`
   - 升級 blocker：若 forward archive 持續增長但 `latest_status` 仍長期 `auth_missing`

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- `q15 support 0/50 + exact_bucket_missing_proxy_reference_only + exact_live_bucket_proxy_available + stalled_under_minimum + escalate_to_blocker=true` 在 breaker path 下仍完整暴露於 probe / API / UI / docs / issues
- Strategy Lab / Execution Status 保持：**breaker-first truth 清楚、exact-vs-spillover 對照可見、per-venue blockers 保留、runtime console 無 JS exception**
- leaderboard governance 保持：**`alignment_snapshot_stale=false`、雙角色 split 明確、placeholder-only leaderboard 不被誤讀成 deployment ranking**
- heartbeat 維持：**issue 對齊 → patch → verify → docs overwrite → commit → push**
