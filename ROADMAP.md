# ROADMAP.md — Current Plan Only

_最後更新：2026-04-19 21:03:53 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **本輪產品化 patch：leaderboard freshness arbitration 已落地**
  - `server/routes/api.py::_load_model_leaderboard_cache_file()` 現在會同時比較 disk cache 與 persisted snapshot，採用 `updated_at` 較新的 payload，避免舊但非空的 cache 遮蔽更新的 snapshot。
  - `scripts/hb_leaderboard_candidate_probe.py::_load_leaderboard_payload()` 同步採用相同 freshness 規則，避免 probe / `issues.json` / docs 還停在舊 top model。
  - regression 已補齊：`tests/test_model_leaderboard.py::test_api_model_leaderboard_prefers_newer_snapshot_over_older_disk_cache`、`tests/test_hb_leaderboard_candidate_probe.py::test_load_leaderboard_payload_prefers_newer_snapshot_over_older_cache`。
- **本輪 fast heartbeat 已完成並留下新鮮 artifacts**
  - `heartbeat #20260419ah`: `Raw=31140 (+1) / Features=22558 (+1) / Labels=62665 (+4)`。
  - `Global IC=15/30`、`TW-IC=29/30`；recent canonical 250 rows 仍是 `distribution_pathology`。
  - `support_route_verdict=exact_bucket_missing_proxy_reference_only`、`current_live_structure_bucket_rows=0`、`minimum_support_rows=50`。
- **本輪 runtime / browser 驗證已完成**
  - `curl http://127.0.0.1:8000/api/models/leaderboard`：`count=6 / comparable_count=6 / placeholder_count=0 / top=rule_baseline / core_only / scan_backed_best`
  - browser `/lab`：顯示 `current live blocker circuit_breaker_active`、獨立 `venue blockers`、以及 `reference-only core_plus_macro patch`
  - browser `/execution/status`：顯示 `circuit_breaker_active`、`support 0/50`、`layers 0→0`、與 venue metadata cards
- **本輪驗證已補齊**
  - `pytest tests/test_auto_propose_fixes.py tests/test_model_leaderboard.py tests/test_hb_leaderboard_candidate_probe.py -q` = `85 passed`
  - `python scripts/hb_parallel_runner.py --fast --hb 20260419ah` 通過
- **本輪 current-state 文件覆寫已完成**
  - `ISSUES.md` / `ROADMAP.md` / `ORID_DECISIONS.md` 已覆寫成 heartbeat #20260419ah 的 current-state-only truth。
  - `ARCHITECTURE.md` 已補上 leaderboard freshness arbitration contract。

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=circuit_breaker_active`
- `recent 50 wins=0/50`
- `additional_recent_window_wins_needed=15`
- `streak=273`
- `allowed_layers=0`
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`

**成功標準**
- `/`、`/execution`、`/execution/status`、`/lab`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`issues.json`、`ISSUES.md` 全部一致把 breaker 視為唯一 current-live deployment blocker。

### 目標 B：維持 q15 `0/50`、reference-only patch、與 support route 真相分離
**目前真相**
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`
- `live_current_structure_bucket_rows=0 / minimum_support_rows=50`
- `gap_to_minimum=50`
- `support_route_verdict=exact_bucket_missing_proxy_reference_only`
- `support_governance_route=exact_live_bucket_proxy_available`
- `support_progress.status=stalled_under_minimum`
- `remaining_gap_to_floor=0.2215`
- `best_single_component=feat_4h_bias50`
- `recommended_patch=core_plus_macro`
- `recommended_patch_status=reference_only_until_exact_support_ready`

**成功標準**
- probe / drilldown / Strategy Lab / Execution Status / API / docs / `issues.json` / heartbeat summary 都一致承認：`0/50 + exact_bucket_missing_proxy_reference_only + stalled_under_minimum + reference_only_until_exact_support_ready`。

### 目標 C：把 recent canonical 250-row pathology 當成 breaker 根因持續鑽深
**目前真相**
- `recent_window=250`
- `win_rate=0.0000`
- `dominant_regime=bull(100%)`
- `avg_pnl=-0.0101`
- `avg_quality=-0.2845`
- `tail_streak=250x0`
- top shifts=`feat_4h_bb_pct_b`、`feat_4h_bias20`、`feat_4h_bias50`
- new compressed=`feat_vwap_dev`

**成功標準**
- recent drift / live probe / docs 能直接指出 pathological slice 與 feature shifts；
- 不再把 current blocker 稀釋成 generic leaderboard / venue 討論。

### 目標 D：守住 leaderboard recent-window contract 與 freshness arbitration
**目前真相**
- `/api/models/leaderboard`: `count=6`、`comparable_count=6`、`placeholder_count=0`
- top row：`rule_baseline / core_only / scan_backed_best`
- governance：`dual_role_governance_active`
- closure：`global_ranking_vs_support_aware_production_split`
- freshness arbitration 已落地：`newer snapshot > older cache`

**成功標準**
- `/api/models/leaderboard`、persisted snapshot、candidate probe、`issues.json`、Strategy Lab 對 top model / profile / governance 說同一個真相；
- 不再出現「舊 cache 有 rows，就遮蔽更新 snapshot」的 split-brain。

### 目標 E：把 venue / source blockers 維持在可見但不搶 breaker 主線的位置
**目前真相**
- `binance=config enabled + public-only + metadata OK`
- `okx=config disabled + public-only + metadata OK`
- `fin_netflow=source_auth_blocked`
- `COINGLASS_API_KEY` 缺失
- `source_blockers.blocked_count=8`

**成功標準**
- `/`、`/execution`、`/execution/status`、`/lab`、`ISSUES.md`、`issues.json` 都保留 venue blockers 與 source auth blockers，但它們永遠排在 breaker-first current blocker 之後。

---

## 下一輪 gate
1. **維持 breaker-first truth across `/` / `/execution` / `/execution/status` / `/lab` / probe / drilldown / docs**
   - 驗證：browser `/lab`、browser `/execution/status`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`
   - 升級 blocker：若任何 surface 再把 q15 / venue / spillover 排到 breaker 前面，或把 current blocker 改寫成非 breaker 主線
2. **鎖住 q15 `0/50` + reference-only `core_plus_macro` patch visibility**
   - 驗證：`python scripts/hb_q15_support_audit.py`、`python scripts/hb_predict_probe.py`、`python scripts/hb_parallel_runner.py --fast --hb <run>`、browser `/lab`
   - 升級 blocker：若 `support_route_verdict` 回退、`recommended_patch` 消失、或 q15 support truth 在 probe / UI / docs 不一致
3. **守住 leaderboard recent-window contract 與 freshness arbitration**
   - 驗證：`curl http://127.0.0.1:8000/api/models/leaderboard`、`pytest tests/test_model_leaderboard.py tests/test_hb_leaderboard_candidate_probe.py tests/test_auto_propose_fixes.py -q`、browser `/lab`
   - 升級 blocker：若 rowful older cache 再遮蔽 fresher snapshot、top model / profile 在 API vs docs 再 split-brain、或 leaderboard 回到 placeholder-only / ambiguous ranking

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- `/lab` 與 `/execution/status` 都先顯示 `deployment_blocker`，再顯示 venue blockers
- `q15 support 0/50 + exact_bucket_missing_proxy_reference_only + stalled_under_minimum + reference_only_until_exact_support_ready` 在 probe / API / UI / docs / summary 全部 machine-read 一致
- recent canonical 250 rows pathology 仍被明確當成 breaker 根因，而不是被 leaderboard / venue 討論稀釋
- canonical leaderboard 維持：**6 筆 comparable rows、最新 snapshot / cache freshness 對齊、top row = `rule_baseline / core_only / scan_backed_best`**
- heartbeat 維持：**issue 對齊 → patch → verify → docs overwrite → commit → push**
