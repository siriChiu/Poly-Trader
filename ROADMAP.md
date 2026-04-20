# ROADMAP.md — Current Plan Only

_最後更新：2026-04-20 12:46:40 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **fast heartbeat #fast 已完成 collect + diagnostics refresh**
  - `Raw=31214 / Features=22632 / Labels=62947`
  - `deployment_blocker=circuit_breaker_active` / `streak=15` / `recent_window_wins=3/50` / `additional_recent_window_wins_needed=12`
  - `window=250` / `win_rate=1.6%` / `dominant_regime=bull(95.6%)` / `avg_quality=-0.2119` / `avg_pnl=-0.0066` / `alerts=label_imbalance,regime_concentration,regime_shift`
- **current-state docs overwrite sync 已自動化**
  - heartbeat runner 會在 `auto_propose_fixes.py` 後直接覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
- **venue readiness / public-only account wording 已 productize**
  - `VenueReadinessSummary`、Dashboard、Strategy Lab、Execution Status 現在把 public-only / disabled venue 明確渲染成 `READ-ONLY` / `DISABLED`，`metadata contract OK` 降為次層語義
  - Dashboard / Execution Status 的帳戶資金卡在 public-only 模式下改為顯示 `public-only / metadata only` 與 `private balance unavailable until exchange credentials are configured`
  - 驗證：`pytest tests/test_frontend_decision_contract.py -q`、`cd web && npm run build`、browser `/` `/execution/status` `/lab`

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=circuit_breaker_active` / `streak=15` / `recent_window_wins=3/50` / `additional_recent_window_wins_needed=12`
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=11/50` / `gap=39` / `support_route_verdict=exact_bucket_present_but_below_minimum`
**成功標準**
- `/`、`/execution`、`/execution/status`、`/lab`、probe、drilldown、docs 都把 breaker release math 視為唯一 current-live deployment blocker。
- q15 current-live bucket truth (`bucket / rows / minimum / gap / support route`) 仍在 top-level surfaces 可 machine-read。

### 目標 B：持續把 recent canonical pathological slice 當成 breaker 根因來鑽
**目前真相**
- `window=250` / `win_rate=1.6%` / `dominant_regime=bull(95.6%)` / `avg_quality=-0.2119` / `avg_pnl=-0.0066` / `alerts=label_imbalance,regime_concentration,regime_shift`
**成功標準**
- drift / probe / docs 能直接指出 pathological slice、adverse streak 與 top feature shifts，而不是退回 generic leaderboard / venue 摘要。

### 目標 C：守住 q15 current-live bucket support + reference-only patch 真相
**目前真相**
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=11/50` / `gap=39` / `support_route_verdict=exact_bucket_present_but_below_minimum`
- `recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_until_exact_support_ready` / `reference_scope=bull|CAUTION`
**成功標準**
- probe / drilldown / `/api/status` / `/execution/status` / `/lab` / docs 全都承認 q15 current-live bucket exact support 未達 minimum rows，recommended patch 只能作治理 / 訓練參考。

### 目標 D：維持 leaderboard、venue/source blockers 與 operator wording 一致 product truth
**目前真相**
- `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=2685` / `archive_window_coverage_pct=0.0`
- venue blockers：`live exchange credential / order ack lifecycle / fill lifecycle` 仍未驗證
- operator-facing wording 已不再把 public-only / disabled venue 誤標成泛化 OK，也不再把缺 private creds 的資金卡顯示成無語義破折號
**成功標準**
- Strategy Lab 不回退 placeholder-only；venue/source blockers 在 operator-facing surfaces 維持可見；public-only / disabled / metadata-only 語義在 `/` `/execution/status` `/lab` 一致。

---

## 下一輪 gate
1. **維持 breaker-first truth + q15 current-live bucket visibility across API / UI / docs**
   - 驗證：browser `/`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`
   - 升級 blocker：若 breaker release math 被 support / floor-gap / venue 話題覆蓋，或 q15 current-live bucket rows 再次從 top-level surfaces 消失
2. **持續鑽 recent canonical pathological slice，而不是 generic 化 root cause**
   - 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`
   - 升級 blocker：若 drift artifact 再失去 target-path / adverse-streak / top-shift 證據
3. **守住 venue/source blockers 與 operator wording，不讓 metadata OK 冒充 live-ready**
   - 驗證：browser `/`、browser `/execution/status`、browser `/lab`、`data/execution_metadata_smoke.json`
   - 升級 blocker：若 public-only / disabled venue 再次被渲染成泛化 OK，或缺 private creds 的帳戶卡再次退回無語義 `—`

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- current live q15 truth 維持：**11/50 + exact_bucket_present_but_below_minimum + reference_only_until_exact_support_ready**
- recent canonical pathological slice 仍以同一個 current window 為主敘事，不被 generic 問題稀釋
- leaderboard 維持 dual-role governance；venue/source blockers 持續可見
- public-only / disabled / metadata-only operator wording 在主要 execution surfaces 保持一致
- heartbeat runner 每輪自動完成：**issue 對齊 → patch/automation lane → verify artifacts → docs overwrite sync**
