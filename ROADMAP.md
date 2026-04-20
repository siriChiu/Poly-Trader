# ROADMAP.md — Current Plan Only

_最後更新：2026-04-21 06:42:14 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 已完成
- **Execution Status diagnostics page 已改成 blocked-first posture**
  - 頁首新增 `overall execution posture`
  - `fresh / healthy` 現在只代表 observability，不再與 deployability 同級
  - `healthy + no_runtime_order` 會顯示 `limited evidence`
  - 私有憑證缺失時頂層改顯示 `metadata-only snapshot`
  - 驗證：`pytest tests/test_frontend_decision_contract.py -q`、`cd web && npm run build`、browser `/execution/status`
- **Strategy Lab detail payload parity 持續正常**
  - `/api/strategies/{name}` 與 leaderboard 仍共用 canonical DQ decoration
- **current-state docs overwrite sync 仍維持正常**
  - docs 與 live probe / drilldown / current blocker truth 已對齊

---

## 主目標

### 目標 A：守住 exact-support shortage 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=under_minimum_exact_live_structure_bucket`
- `current_live_structure_bucket=CAUTION|structure_quality_caution|q35`
- `support=12/50` / `gap=38`
- `support_route_verdict=exact_bucket_present_but_below_minimum`

**成功標準**
- `/`、`/execution/status`、`/lab`、probe、drilldown、docs 都把 exact-support shortage 視為唯一 current-live blocker
- 任何 `fresh / healthy / venue blockers` 都不得覆蓋這個 blocker

### 目標 B：持續沿 recent pathological slice 追根因
**目前真相**
- `window=500` / `win_rate=12.8%` / `dominant_regime=bull(83.8%)`
- `avg_quality=-0.1547` / `avg_pnl=-0.0056`
- `alerts=label_imbalance,regime_shift`

**成功標準**
- recent-window diagnostics 持續能直接指出 target-path、adverse streak、top feature shifts
- 不回退成 generic leaderboard / venue 摘要

### 目標 C：守住 reference-only patch、venue/source blockers、leaderboard governance
**目前真相**
- `recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_until_exact_support_ready`
- venue 仍缺 credential / order ack / fill lifecycle proof
- `fin_netflow` 仍 `auth_missing`
- leaderboard 仍是 `core_only` global winner vs `core_plus_macro` support-aware production split

**成功標準**
- patch 只能維持 reference-only，不被誤升級成 deployable truth
- venue / source blockers 在 operator-facing surfaces 持續可見
- Strategy Lab / leaderboard 不回退 placeholder-only 或 ambiguous backtest window

---

## 下一輪 gate
1. **把 exact-support blocker truth 守到 Dashboard / Execution Status / Strategy Lab / probe / docs 完全一致**
   - 驗證：browser `/`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`
   - 升級 blocker：若任何 surface 再把 fresh/healthy/venue blocker 放到 current-live blocker 之前
2. **沿 recent pathological slice 繼續做 root-cause drill-down**
   - 驗證：`python scripts/recent_drift_report.py`、`python scripts/live_decision_quality_drilldown.py`
   - 升級 blocker：若 artifact 再失去 target-path / adverse-streak / top-shift 證據
3. **守住 reference-only patch、venue/source blockers、leaderboard dual-role governance**
   - 驗證：browser `/lab`、browser `/execution/status`、`data/execution_metadata_smoke.json`、`curl http://127.0.0.1:8000/api/models/leaderboard`
   - 升級 blocker：若 patch 被誤升級成 deployable、venue/source blockers 消失、或排行榜再 split-brain

---

## 成功標準
- current-live blocker 清楚且唯一：`under_minimum_exact_live_structure_bucket`
- current live bucket support truth 維持：`12/50 + gap=38 + exact_bucket_present_but_below_minimum`
- Execution Status 首屏已固定為 blocker-first posture，fresh/healthy 不再被誤讀成 deployability
- recent pathological slice 仍被當成 current blocker 根因來追，不被 generic 摘要稀釋
- reference-only patch、venue/source blockers、leaderboard dual-role governance 維持 operator-facing 可見性
