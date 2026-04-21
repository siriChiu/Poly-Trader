# ROADMAP.md — Current Plan Only

_最後更新：2026-04-21 19:40:38 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **fast heartbeat #fast 已完成 collect + diagnostics refresh**
  - `Raw=31385 / Features=22803 / Labels=63286`
  - `deployment_blocker=under_minimum_exact_live_structure_bucket` / `streak=None` / `recent_window_wins=None/None` / `additional_recent_window_wins_needed=—`
  - `latest_window=100` / `win_rate=100.0%` / `dominant_regime=chop(100.0%)` / `avg_quality=+0.6589` / `avg_pnl=+0.0196` / `alerts=constant_target,regime_concentration,regime_shift`
  - `blocking_window=500` / `win_rate=28.0%` / `dominant_regime=bull(68.6%)` / `avg_quality=-0.0062` / `avg_pnl=-0.0008` / `alerts=regime_shift`
- **current-state docs overwrite sync 已自動化**
  - heartbeat runner 會在 `auto_propose_fixes.py` 後直接覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 這條 lane 的目的不是美化文件，而是避免 `issues.json / live artifacts` 已更新、markdown docs 卻仍停在舊 truth 的治理裂縫
- **本輪 current-state docs 已同步到最新 artifacts**
  - docs 與 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json` 的 current-state truth 已對齊
- **Strategy Lab / Execution guardrails 已產品化補強**
  - Strategy Lab：system-generated auto leaderboard rows 不能再直接覆寫；operator 必須先輸入新的唯一名稱，API 與 rescan lane 也會去重 duplicate auto rows，避免排行榜重複污染工作區
  - Execution Console：current live blocker 存在時，自然語句區的「買入 0.001 BTC」快捷鍵會自動 disabled，只保留減碼 / 模式切換 / 查看 blocker 這些安全操作

---

## 主目標

### 目標 A：維持 current-live exact-support blocker 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=under_minimum_exact_live_structure_bucket` / `streak=None` / `recent_window_wins=None/None` / `additional_recent_window_wins_needed=—`
- `current_live_structure_bucket=CAUTION|structure_quality_caution|q35` / `support=12/50` / `gap=38` / `support_route_verdict=exact_bucket_present_but_below_minimum`
**成功標準**
- `/`、`/execution`、`/execution/status`、`/lab`、probe、drilldown、docs 都把 `under_minimum_exact_live_structure_bucket` 視為唯一 current-live deployment blocker，且不再誤回退成 breaker-first 舊敘事。
- current live bucket truth (`bucket / rows / minimum / gap / support route`) 仍在 top-level surfaces 可 machine-read。

### 目標 B：持續把 recent canonical blocker pocket 當成 current blocker 根因來鑽
**目前真相**
- `latest_window=100` / `win_rate=100.0%` / `dominant_regime=chop(100.0%)` / `avg_quality=+0.6589` / `avg_pnl=+0.0196` / `alerts=constant_target,regime_concentration,regime_shift`
- `blocking_window=500` / `win_rate=28.0%` / `dominant_regime=bull(68.6%)` / `avg_quality=-0.0062` / `avg_pnl=-0.0008` / `alerts=regime_shift`
**成功標準**
- drift / probe / docs 能同時指出 latest recent-window diagnostics 與 current blocker pocket，而不是退回 generic leaderboard / venue 摘要。

### 目標 C：守住 current live bucket support + reference-only patch 真相
**目前真相**
- `current_live_structure_bucket=CAUTION|structure_quality_caution|q35` / `support=12/50` / `gap=38` / `support_route_verdict=exact_bucket_present_but_below_minimum`
- `recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_until_exact_support_ready` / `reference_scope=bull|CAUTION`
**成功標準**
- probe / drilldown / `/api/status` / `/execution/status` / `/lab` / docs 全都承認 current live bucket exact support 未達 minimum rows，recommended patch 只能作治理 / 訓練參考。

### 目標 D：維持 leaderboard、venue/source blockers 與 docs automation 一致 product truth
**目前真相**
- `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=2855` / `archive_window_coverage_pct=0.0`
- venue blockers：`live exchange credential / order ack lifecycle / fill lifecycle` 仍未驗證
- docs automation：markdown docs 不再允許落後 live artifacts
**成功標準**
- Strategy Lab 不回退 placeholder-only；venue/source blockers 在 operator-facing surfaces 維持可見；docs automation 每輪心跳都自動完成 overwrite sync。

---

## 下一輪 gate
1. **維持 current-live exact-support blocker + current live bucket visibility across API / UI / docs**
   - 驗證：browser `/`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`
   - 升級 blocker：若 current-live blocker 被 breaker 舊敘事 / venue 話題覆蓋，或 current live bucket rows 再次從 top-level surfaces 消失
2. **持續鑽 recent canonical pathological slice，而不是 generic 化 root cause**
   - 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`
   - 升級 blocker：若 drift artifact 再失去 target-path / adverse-streak / top-shift 證據
3. **守住 current live bucket support / reference-only patch、leaderboard governance、venue/source blockers 與 docs automation 閉環**
   - 驗證：browser `/lab`、`curl http://127.0.0.1:<active-backend>/api/models/leaderboard`（依 `/health` 選 8000/8001 健康 lane，不要硬綁單一 port）、`data/q15_support_audit.json`、`data/execution_metadata_smoke.json`、下輪 heartbeat docs sync status
   - 升級 blocker：若 patch 被誤升級成 deployable truth、排行榜 drift 成 placeholder-only、venue/source blocker 消失、或 docs 再次落後 latest artifacts

---

## 成功標準
- current-live blocker 清楚且唯一：**under_minimum_exact_live_structure_bucket**
- current live bucket support truth 維持：**12/50 + exact_bucket_present_but_below_minimum + reference_only_until_exact_support_ready**
- recent canonical diagnostics 與 current blocker pocket 需同步可見，不被 generic 問題稀釋
- leaderboard 維持 dual-role governance；venue/source blockers 持續可見
- heartbeat runner 每輪自動完成：**issue 對齊 → patch/automation lane → verify artifacts → docs overwrite sync**
