# ROADMAP.md — Current Plan Only

_最後更新：2026-04-20 07:29:32 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **fast heartbeat #20260420-0712 已完成 collect + diagnostics refresh**
  - `Raw=31184 / Features=22602 / Labels=62902`
  - `deployment_blocker=circuit_breaker_active` / `streak=186` / `recent_window_wins=0/50` / `additional_recent_window_wins_needed=15`
  - `window=100` / `win_rate=0.0%` / `dominant_regime=bull(100.0%)` / `avg_quality=-0.2343` / `avg_pnl=-0.0094` / `alerts=constant_target,regime_concentration,regime_shift`
- **current-state docs overwrite sync 已自動化**
  - heartbeat runner 會在 `auto_propose_fixes.py` 後直接覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 這條 lane 的目的不是美化文件，而是避免 `issues.json / live artifacts` 已更新、markdown docs 卻仍停在舊 truth 的治理裂縫
- **本輪 current-state docs 已同步到最新 artifacts**
  - docs 與 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json` 的 current-state truth 已對齊
- **本輪 runtime truth telemetry 已補強**
  - `scripts/hb_parallel_runner.py` 已改成 run-level monotonic elapsed，fast heartbeat 的 progress / summary / cron-budget issue 會對整輪 run 給出單調且正確的 elapsed
  - `web/src/hooks/useApi.ts` 已加入 superseded-request cancel + stale-timeout guard；在 `:8000` timeout、`:8001` 正常的 dev runtime 下，Dashboard / Strategy Lab / Execution Status 仍可穩定載入

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=circuit_breaker_active` / `streak=186` / `recent_window_wins=0/50` / `additional_recent_window_wins_needed=15`
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q00` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`
**成功標準**
- `/`、`/execution`、`/execution/status`、`/lab`、probe、drilldown、docs 都把 breaker release math 視為唯一 current-live deployment blocker。
- current live bucket truth (`bucket / rows / minimum / gap / support route`) 仍在 top-level surfaces 可 machine-read。

### 目標 B：持續把 recent canonical pathological slice 當成 breaker 根因來鑽
**目前真相**
- `window=100` / `win_rate=0.0%` / `dominant_regime=bull(100.0%)` / `avg_quality=-0.2343` / `avg_pnl=-0.0094` / `alerts=constant_target,regime_concentration,regime_shift`
**成功標準**
- drift / probe / docs 能直接指出 pathological slice、adverse streak 與 top feature shifts，而不是退回 generic leaderboard / venue 摘要。

### 目標 C：守住 current live bucket support + reference-only patch 真相
**目前真相**
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q00` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`
- `recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_until_exact_support_ready` / `reference_scope=bull|CAUTION`
**成功標準**
- probe / drilldown / `/api/status` / `/execution/status` / `/lab` / docs 全都承認 current live bucket exact support 未達 minimum rows，recommended patch 只能作治理 / 訓練參考。

### 目標 D：維持 leaderboard、venue/source blockers 與 docs automation 一致 product truth
**目前真相**
- `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=2655` / `archive_window_coverage_pct=0.0`
- venue blockers：`live exchange credential / order ack lifecycle / fill lifecycle` 仍未驗證
- docs automation：markdown docs 不再允許落後 live artifacts
**成功標準**
- Strategy Lab 不回退 placeholder-only；venue/source blockers 在 operator-facing surfaces 維持可見；docs automation 每輪心跳都自動完成 overwrite sync。

---

## 下一輪 gate
1. **維持 breaker-first truth + current live bucket visibility across API / UI / docs**
   - 驗證：browser `/`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`
   - 升級 blocker：若 breaker release math 被 support / floor-gap / venue 話題覆蓋，或 current live bucket rows 再次從 top-level surfaces 消失
2. **持續鑽 recent canonical pathological slice，而不是 generic 化 root cause**
   - 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`
   - 升級 blocker：若 drift artifact 再失去 target-path / adverse-streak / top-shift 證據
3. **守住 current live bucket support / reference-only patch、leaderboard governance、venue/source blockers 與 docs automation 閉環**
   - 驗證：browser `/lab`、`curl http://127.0.0.1:8000/api/models/leaderboard`、`data/q15_support_audit.json`、`data/execution_metadata_smoke.json`、下輪 heartbeat docs sync status
   - 升級 blocker：若 patch 被誤升級成 deployable truth、排行榜 drift 成 placeholder-only、venue/source blocker 消失、或 docs 再次落後 latest artifacts

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- current live bucket support truth 維持：**0/50 + exact_bucket_missing_exact_lane_proxy_only + reference_only_until_exact_support_ready**
- recent canonical pathological slice 仍以同一個 current window 為主敘事，不被 generic 問題稀釋
- leaderboard 維持 dual-role governance；venue/source blockers 持續可見
- heartbeat runner 每輪自動完成：**issue 對齊 → patch/automation lane → verify artifacts → docs overwrite sync**
