# ROADMAP.md — Current Plan Only

_最後更新：2026-04-21 13:19:21 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 已完成
- **fast heartbeat #20260421-1305 已完成 collect + diagnostics refresh**
  - `Raw=31360 / Features=22778 / Labels=63219`
  - `deployment_blocker=under_minimum_exact_live_structure_bucket`
  - `current_live_structure_bucket=CAUTION|structure_quality_caution|q35` / `support=12/50` / `gap=38`
- **operator surfaces 已補齊 support route / governance route product copy**
  - Dashboard、`/execution/status`、`/lab`、`LivePathologySummaryCard` 現在都會一起顯示 `support_route_verdict` 與 `support_governance_route`
  - regression lock：`pytest tests/test_frontend_decision_contract.py tests/test_server_startup.py tests/test_strategy_lab.py -q` → `124 passed`
  - build / runtime evidence：`cd web && npm run build` ✅；browser `/`、`/execution/status`、`/lab` 均確認 support/governance route 文案存在
- **current-state docs overwrite sync 仍維持自動化**
  - heartbeat runner 持續覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 目的：避免 markdown docs 落後 `issues.json / live artifacts`

---

## 主目標

### 目標 A：維持 current-live exact-support blocker 作為唯一 deployment blocker
**目前真相**
- `deployment_blocker=under_minimum_exact_live_structure_bucket`
- `current_live_structure_bucket=CAUTION|structure_quality_caution|q35`
- `support=12/50` / `gap=38` / `support_route_verdict=exact_bucket_present_but_below_minimum`
**成功標準**
- `/`、`/execution/status`、`/lab`、probe、drilldown、docs 全都維持同一個 blocker truth
- exact-support 補滿前，任何 surface 都不能把 reference patch 或 proxy rows 當成 deployable truth

### 目標 B：把 recent canonical pathological slice 當成當前根因主線繼續鑽
**目前真相**
- `recent_100=97.0% / chop(88.0%) / alerts=label_imbalance,regime_shift`
- `recent_500=20.6% / bull(76.0%) / interpretation=regime_concentration`
**成功標準**
- drift / probe / docs 能持續指出 target-path、top-shift、variance/distinct 問題
- 不回退成 generic leaderboard / venue / breaker 摘要

### 目標 C：守住 support/governance route visibility 與 reference-only patch 治理
**目前真相**
- operator surfaces 已同時顯示 `support_route_verdict` 與 `support_governance_route`
- `recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_until_exact_support_ready`
**成功標準**
- Dashboard、`/execution/status`、`/lab`、compact/full LivePathology card、docs 都維持同一組 support/governance route 文案
- regression tests / build / browser 不再出現型別漏欄位或 copy 漏顯示

### 目標 D：把 fast heartbeat 壓回 cron-safe budget
**目前真相**
- `elapsed_seconds=68.9` / `timed_out_lanes=['feature_group_ablation']`
**成功標準**
- `--fast` 只保留 collect / drift / probe / docs 必要 lanes，candidate-eval lane 不再拖垮 fast heartbeat

---

## 下一輪 gate
1. **維持 exact-support blocker + support/governance route visibility across API / UI / docs**
   - 驗證：browser `/`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`
   - 升級 blocker：若 blocker truth 被 breaker / venue 敘事覆蓋，或 support/governance route 從任何 top-level surface 消失
2. **持續鑽 recent canonical pathological slice，而不是 generic 化 root cause**
   - 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`
   - 升級 blocker：若 drift artifact 再失去 target-path / adverse-streak / top-shift 證據
3. **把 fast heartbeat 壓回 cron-safe，並守住 leaderboard / venue / source 治理**
   - 驗證：`python scripts/hb_parallel_runner.py --fast --hb <next>`、browser `/lab`、`curl http://127.0.0.1:<active-backend>/api/models/leaderboard`、`data/execution_metadata_smoke.json`
   - 升級 blocker：若 fast mode 再 timeout、排行榜回退 placeholder-only、venue/source blockers 消失或 docs 再次落後 latest artifacts

---

## 成功標準
- current-live blocker 清楚且唯一：**under_minimum_exact_live_structure_bucket**
- q35 current live support truth 維持：**12/50 + exact_bucket_present_but_below_minimum + reference_only_until_exact_support_ready**
- support/governance route 在 operator-facing surfaces 維持可見並有 regression lock
- recent canonical pathological slice 仍以同一個 current window 為主敘事
- fast heartbeat 恢復 cron-safe，不再被 candidate lane 拖垮
