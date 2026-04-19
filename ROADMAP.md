# ROADMAP.md — Current Plan Only

_最後更新：2026-04-20 00:32:56 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **fast heartbeat #20260420a 完成 collect + verify 閉環**
  - `python scripts/hb_parallel_runner.py --fast --hb 20260420a`
  - `Raw=31153 / Features=22571 / Labels=62743`
  - collect 實際新增 `+1 raw / +1 features / +31 labels`
  - `Global IC=13/30`、`TW-IC=29/30`
- **current-live breaker / q15 truth 已重新量測**
  - `deployment_blocker=circuit_breaker_active`
  - `reason=Consecutive loss streak: 60 >= 50; Recent 50-sample win rate: 0.00% < 30%`
  - `recent 50 wins=0/50`
  - `additional_recent_window_wins_needed=15`
  - `regime_label=chop / regime_gate=CAUTION`
  - `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`
  - `current_live_structure_bucket_rows=0 / minimum_support_rows=50 / gap_to_minimum=50`
  - `support_route_verdict=exact_bucket_missing_proxy_reference_only`
  - `support_governance_route=exact_live_bucket_proxy_available`
- **本輪產品化 patch：/api/status breaker 下也維持 same-bucket top-level truth**
  - `server/routes/api.py::_build_live_runtime_closure_surface()` 現在會在 `execution.live_runtime_truth` 頂層輸出：
    - `current_live_structure_bucket`
    - `current_live_structure_bucket_rows`
    - `minimum_support_rows`
    - `current_live_structure_bucket_gap_to_minimum`
    - `support_governance_route`
    - `support_route_deployable`
  - 不再只把 q15 support truth 藏在 `deployment_blocker_details`；`/api/status` 與 UI runtime surfaces 的 machine-read contract 已對齊 probe / drilldown。
- **recent pathological slice 與 leaderboard current truth 已確認**
  - recent canonical `250` rows：`win_rate=0.0040`、`dominant_regime=bull(100%)`、`avg_quality=-0.2623`
  - leaderboard：`count=4 / profile=core_only / governance=dual_role_governance_active`
- **本輪驗證已補齊**
  - `pytest tests/test_server_startup.py -q` → `29 passed`
  - `pytest tests/test_frontend_decision_contract.py -q` → `19 passed`
  - `cd web && npm run build` → pass
  - `curl http://127.0.0.1:8000/api/status`：已直接回傳 `q15 + 0/50 + exact_live_bucket_proxy_available`
  - browser `/execution/status`：已看到 `chop / CAUTION / q15 / support 0/50`
  - browser `/lab`：已看到 `current bucket 0 CAUTION|base_caution_regime_or_bias|q15`
- **current-state 文件覆寫已完成**
  - `ISSUES.md` / `ROADMAP.md` / `ORID_DECISIONS.md` 已覆寫為本輪 current state
  - `ARCHITECTURE.md` 已補上 breaker-first support visibility 的 top-level API contract

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live blocker，且 q15 same-bucket truth 在 top-level 可見
**目前真相**
- `deployment_blocker=circuit_breaker_active`
- `recent 50 wins=0/50`
- `required_recent_window_wins=15`
- `additional_recent_window_wins_needed=15`
- `streak=60`
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`
- `current_live_structure_bucket_rows=0 / minimum_support_rows=50 / gap_to_minimum=50`

**成功標準**
- `/api/status`、`/execution/status`、`/lab`、probe、drilldown、docs 全部一致把 breaker 視為唯一 current-live deployment blocker。
- same-bucket q15 support truth 以 top-level machine-read 欄位存在，不能只留在 nested blocker details。

### 目標 B：持續把 recent canonical 250-row pathology 當成 breaker 根因來鑽
**目前真相**
- `recent_window=250`
- `win_rate=0.0040`
- `dominant_regime=bull(100%)`
- `avg_pnl=-0.0086`
- `avg_quality=-0.2623`
- top shifts=`feat_4h_vol_ratio`、`feat_eye`、`feat_local_top_score`

**成功標準**
- drift / live probe / docs 能直接指出 pathological slice、adverse streak、top feature shifts；
- blocker 不再被 generic leaderboard / venue 討論稀釋。

### 目標 C：守住 q15 `0/50 + proxy-reference-only` 支撐真相
**目前真相**
- `support_route_verdict=exact_bucket_missing_proxy_reference_only`
- `support_governance_route=exact_live_bucket_proxy_available`
- `recommended_patch=core_plus_macro_plus_all_4h`
- `recommended_patch_status=reference_only_until_exact_support_ready`

**成功標準**
- probe / drilldown / `/api/status` / `/execution/status` / `/lab` / docs 全部一致承認：q15 仍是 `0/50`，patch 只能作治理 / 訓練參考。

### 目標 D：守住 leaderboard dual-role governance 與 venue/source blockers 的產品語義同步
**目前真相**
- leaderboard：`count=4`、`core_only vs core_plus_macro`、`dual_role_governance_active`
- venue blockers：`live exchange credential / order ack lifecycle / fill lifecycle` 未驗證
- `fin_netflow=source_auth_blocked`
- `COINGLASS_API_KEY` 仍缺失

**成功標準**
- Strategy Lab 不回退 placeholder-only；production fallback 不被誤寫成 parity blocker。
- `/`、`/execution`、`/execution/status`、`/lab`、docs 對 venue blockers 與 source auth blocker 說同一個真相。

---

## 下一輪 gate
1. **維持 breaker-first truth + q15 current-live bucket top-level visibility across API / UI / docs**
   - 驗證：`curl /api/status`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`
   - 升級 blocker：若 `current_live_structure_bucket / rows / gap / support_governance_route` 再次從 top-level runtime surfaces 消失或回成 null
2. **持續鑽 recent canonical 250-row pathology，而不是 generic 化 blocker**
   - 驗證：`python scripts/recent_drift_report.py`、`python scripts/live_decision_quality_drilldown.py`
   - 升級 blocker：若 drift artifact 再失去 target-path / adverse-streak / top-shift 證據，或 docs 又退回 generic leaderboard / venue 敘事
3. **守住 q15 reference-only patch 與 venue/source blockers 的可見性**
   - 驗證：browser `/execution/status`、browser `/lab`、`data/q15_support_audit.json`、`data/execution_metadata_smoke.json`
   - 升級 blocker：若 q15 patch 被誤升級成 deployable truth，或 venue / CoinGlass blocker 在 operator-facing surfaces 消失

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- `/api/status.execution.live_runtime_truth` 頂層直接輸出 **`current_live_structure_bucket / rows / minimum / gap / support_governance_route`**
- `current live q15 = 0/50 + exact_bucket_missing_proxy_reference_only + reference_only_until_exact_support_ready` 在 probe / drilldown / API / UI / docs 全部 machine-read 一致
- recent canonical pathology 仍以同一個 250-row slice 為主敘事，不被 generic 問題稀釋
- leaderboard 維持 dual-role governance；venue blockers 與 CoinGlass auth blocker 持續可見
- heartbeat 維持：**issue 對齊 → patch → verify → docs overwrite → commit → push**
