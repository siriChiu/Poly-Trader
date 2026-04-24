# ROADMAP.md — Current Plan Only

_最後更新：2026-04-24 09:51:56 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **fast heartbeat #20260424n 已完成 collect + diagnostics refresh**
  - `Raw=32134 / Features=23552 / Labels=64721`
  - 歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`
  - `deployment_blocker=unsupported_exact_live_structure_bucket` / `streak=None` / `recent_window_wins=None/None` / `additional_recent_window_wins_needed=—`
  - `latest_window=500` / `win_rate=45.0%` / `dominant_regime=bull(99.6%)` / `avg_quality=+0.0673` / `avg_pnl=0.0000` / `alerts=regime_concentration,regime_shift`
- **current-state docs overwrite sync 已自動化**
  - heartbeat runner 會在 `auto_propose_fixes.py` 後直接覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 這條 lane 的目的不是美化文件，而是避免 `issues.json / live artifacts` 已更新、markdown docs 卻仍停在舊 truth 的治理裂縫
- **本輪 current-state docs 已同步到最新 artifacts**
  - docs 與 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json` 的 current-state truth 已對齊
- **本輪 operator copy productization 已補強**
  - Execution Console run / sleeve / profile 文案已 humanize，不再把 control-plane token 直接丟給 operator
  - Strategy Lab 策略排行榜的 sleeve filter / badge / labels 已改為中文倉位腿語義，並由 frontend contract tests + build 鎖住

---

## 主目標

### 目標 A：維持 current-live exact-support blocker 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=unsupported_exact_live_structure_bucket` / `streak=None` / `recent_window_wins=None/None` / `additional_recent_window_wins_needed=—`
- `current_live_structure_bucket=BLOCK|bull_high_bias200_overheat_block|q35` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_unsupported_block`
**成功標準**
- `/`、`/execution`、`/execution/status`、`/lab`、probe、drilldown、docs 都把 `unsupported_exact_live_structure_bucket` 視為唯一 current-live deployment blocker，且不再誤回退成 breaker-first 舊敘事。
- current live bucket truth (`bucket / rows / minimum / gap / support route`) 仍在 top-level surfaces 可 machine-read。

### 目標 B：持續把 recent canonical blocker pocket 當成 current blocker 根因來鑽
**目前真相**
- `latest_window=500` / `win_rate=45.0%` / `dominant_regime=bull(99.6%)` / `avg_quality=+0.0673` / `avg_pnl=0.0000` / `alerts=regime_concentration,regime_shift`
**成功標準**
- drift / probe / docs 能同時指出 latest recent-window diagnostics 與 current blocker pocket，而不是退回 generic leaderboard / venue 摘要。

### 目標 C：守住 current live bucket support + reference-only patch 真相
**目前真相**
- `current_live_structure_bucket=BLOCK|bull_high_bias200_overheat_block|q35` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_unsupported_block`
- `recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_non_current_live_scope` / `reference_scope=bull|CAUTION`
- q35 scaling audit 已指出目前不是單點 bias50 closure：`overall_verdict=bias50_formula_may_be_too_harsh` / `redesign_verdict=base_stack_redesign_discriminative_reweight_still_below_floor` / `remaining_gap_to_floor=0.159`
**成功標準**
- probe / drilldown / `/api/status` / `/execution/status` / `/lab` / docs 全都承認 current live bucket exact support 未達 minimum rows，recommended patch 只能作治理 / 訓練參考。

### 目標 D：維持 leaderboard、venue/source blockers 與 docs automation 一致 product truth
**目前真相**
- `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3602` / `archive_window_coverage_pct=0.0`
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
- current-live blocker 清楚且唯一：**unsupported_exact_live_structure_bucket**
- current live bucket support truth 維持：**0/50 + exact_bucket_unsupported_block + reference_only_non_current_live_scope**
- recent canonical diagnostics 與 current blocker pocket 需同步可見，不被 generic 問題稀釋
- leaderboard 維持 dual-role governance；venue/source blockers 持續可見
- heartbeat runner 每輪自動完成：**issue 對齊 → patch/automation lane → verify artifacts → docs overwrite sync**
