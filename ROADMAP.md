# ROADMAP.md — Current Plan Only

_最後更新：2026-04-19 21:40:43 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **本輪產品化 patch：rows-aware support-route truth 已落地**
  - `model/predictor.py::_summarize_structure_bucket_support_route()` 現在先看 exact bucket rows 是否達到 `minimum_support_rows`，不再把 `exact_bucket_supported_*` mode hint 直接當成 closure。
  - 這修掉了 current live `q35` exact bucket 只有 `1/50` 時，probe / drilldown / docs 仍誤報 `exact_bucket_supported` 的 false-open 支援語義。
  - regression 已補齊：`tests/test_api_feature_history_and_predictor.py::test_summarize_structure_bucket_support_route_does_not_false_open_below_minimum_support`。
- **本輪 fast heartbeat 已完成並留下新鮮 artifacts**
  - `heartbeat #20260419aj`: `Raw=31142 (+1) / Features=22560 (+1) / Labels=62671 (+3)`。
  - `Global IC=15/30`、`TW-IC=26/30`；recent canonical 250 rows 仍是 `distribution_pathology`。
  - current live truth：`deployment_blocker=circuit_breaker_active`、`current_live_structure_bucket=CAUTION|structure_quality_caution|q35`、`current_live_structure_bucket_rows=1/50`、`support_route_verdict=exact_bucket_present_but_below_minimum`。
- **本輪 runtime artifact 驗證已完成**
  - `data/live_predict_probe.json`：`support_route_verdict=exact_bucket_present_but_below_minimum`、`allowed_layers=0`、`additional_recent_window_wins_needed=14`
  - `data/live_decision_quality_drilldown.json`：`recommended_patch=core_plus_macro`、`recommended_patch_status=reference_only_until_exact_support_ready`、`recommended_patch_support_route=exact_bucket_present_but_below_minimum`
  - `data/leaderboard_feature_profile_probe.json`：`count=6 / comparable_count=6 / top=rule_baseline / core_only / scan_backed_best`
- **本輪驗證已補齊**
  - `pytest tests/test_api_feature_history_and_predictor.py tests/test_hb_predict_probe.py -q` = `80 passed`
  - `python scripts/hb_parallel_runner.py --fast --hb 20260419aj` 通過
- **本輪 current-state 文件覆寫已完成**
  - `ISSUES.md` / `ROADMAP.md` / `ORID_DECISIONS.md` 已覆寫成 heartbeat #20260419aj 的 current-state-only truth。
  - `ARCHITECTURE.md` 已補上 rows-aware support-route contract。

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=circuit_breaker_active`
- `recent 50 wins=1/50`
- `additional_recent_window_wins_needed=14`
- `streak=1`
- `allowed_layers=0`
- `current_live_structure_bucket=CAUTION|structure_quality_caution|q35`

**成功標準**
- `/`、`/execution`、`/execution/status`、`/lab`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`issues.json`、`ISSUES.md` 全部一致把 breaker 視為唯一 current-live deployment blocker。

### 目標 B：維持 current-live q35 `1/50` 與 reference-only patch 真相
**目前真相**
- `current_live_structure_bucket=CAUTION|structure_quality_caution|q35`
- `current_live_structure_bucket_rows=1 / minimum_support_rows=50`
- `gap_to_minimum=49`
- `support_route_verdict=exact_bucket_present_but_below_minimum`
- `support_governance_route=exact_live_bucket_present_but_below_minimum`
- `recommended_patch=core_plus_macro`
- `recommended_patch_status=reference_only_until_exact_support_ready`
- `remaining_gap_to_floor=0.1963`
- `best_single_component=feat_4h_bias50`

**成功標準**
- probe / drilldown / API / UI / docs / `issues.json` / heartbeat summary 都一致承認：`1/50 + exact_bucket_present_but_below_minimum + reference_only_until_exact_support_ready`。

### 目標 C：把 recent canonical 250-row pathology 當成 breaker 根因持續鑽深
**目前真相**
- `recent_window=250`
- `win_rate=0.0040`
- `dominant_regime=bull(100%)`
- `avg_pnl=-0.0099`
- `avg_quality=-0.2816`
- `adverse_streak=248x0`
- top shifts=`feat_4h_bb_pct_b`、`feat_4h_bias20`、`feat_eye`
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
- `leaderboard_payload_source=latest_persisted_snapshot`

**成功標準**
- `/api/models/leaderboard`、persisted snapshot、candidate probe、`issues.json`、Strategy Lab 對 top model / profile / governance 說同一個真相；
- 不再出現 split-brain 或 placeholder-only 回歸。

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
1. **維持 breaker-first truth + q35 `1/50` support truth across probe / drilldown / UI / docs**
   - 驗證：`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、browser `/lab`、browser `/execution/status`
   - 升級 blocker：若任一 surface 再把 `1/50` 說成 support 已 closure，或把 q35 / patch / venue 排到 breaker release math 前面
2. **持續鑽 recent canonical 250-row pathology，而不是 generic 化 blocker**
   - 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_parallel_runner.py --fast --hb <run>`
   - 升級 blocker：若 drift artifact 再失去 top shifts / adverse streak / target-path evidence，或 docs 又退回只寫 generic leaderboard / venue 問題
3. **守住 leaderboard / venue / source blocker 的產品語義同步**
   - 驗證：`curl http://127.0.0.1:8000/api/models/leaderboard`、`pytest tests/test_model_leaderboard.py tests/test_hb_leaderboard_candidate_probe.py tests/test_auto_propose_fixes.py -q`、browser `/lab`
   - 升級 blocker：若 top model / profile 再 split-brain、venue blockers 消失、或 CoinGlass auth blocker 被誤包裝成 coverage 已改善

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- `/lab` 與 `/execution/status` 都先顯示 `deployment_blocker`，再顯示 venue blockers
- `current live q35 = 1/50 + exact_bucket_present_but_below_minimum + reference_only_until_exact_support_ready` 在 probe / drilldown / API / UI / docs / summary 全部 machine-read 一致
- recent canonical 250 rows pathology 仍被明確當成 breaker 根因，而不是被 leaderboard / venue 討論稀釋
- canonical leaderboard 維持：**6 筆 comparable rows、top row = `rule_baseline / core_only / scan_backed_best`**
- heartbeat 維持：**issue 對齊 → patch → verify → docs overwrite → commit → push**
