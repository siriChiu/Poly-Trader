# ROADMAP.md — Current Plan Only

_最後更新：2026-04-20 19:17:47 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **fast heartbeat #fast 已完成 collect + diagnostics refresh**
  - `Raw=31254 / Features=22672 / Labels=63024`
  - `deployment_blocker=circuit_breaker_active` / `streak=0` / `recent_window_wins=14/50` / `additional_recent_window_wins_needed=1`
  - `window=500` / `win_rate=3.6%` / `dominant_regime=bull(90.6%)` / `avg_quality=-0.2266` / `avg_pnl=-0.0078` / `alerts=label_imbalance,regime_concentration,regime_shift`
- **current-state docs overwrite sync 已自動化**
  - heartbeat runner 會在 `auto_propose_fixes.py` 後直接覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 目的不是美化文件，而是避免 `issues.json / live artifacts` 已更新、markdown docs 卻仍停在舊 truth
- **Strategy Lab 實際區間空白已修復**
  - `backtesting/strategy_lab.py` 現在會替 legacy saved strategies 補回 `backtest_range.requested/effective/available`
  - `web/src/pages/StrategyLab.tsx` 現在會用 `effective → requested → definition → chart_context` 顯示實際區間，不再把已知回測範圍顯示成 `— → —`
  - 已同步重啟 `:8001` backend，`python scripts/hb_strategy_range_probe.py` 與 browser `/lab` 均已看到有效區間

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=circuit_breaker_active` / `streak=0` / `recent_window_wins=14/50` / `additional_recent_window_wins_needed=1`
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q35` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`
**成功標準**
- `/`、`/execution`、`/execution/status`、`/lab`、probe、drilldown、docs 都把 breaker release math 視為唯一 current-live deployment blocker。
- current live bucket truth（`bucket / rows / minimum / gap / support route`）仍在 top-level surfaces 可 machine-read。

### 目標 B：持續把 recent canonical pathological slice 當成 breaker 根因來鑽
**目前真相**
- `window=500` / `win_rate=3.6%` / `dominant_regime=bull(90.6%)` / `avg_quality=-0.2266` / `avg_pnl=-0.0078` / `alerts=label_imbalance,regime_concentration,regime_shift`
**成功標準**
- drift / probe / docs 能直接指出 pathological slice、adverse streak 與 top feature shifts，而不是退回 generic leaderboard / venue 摘要。

### 目標 C：守住 current live bucket support + reference-only patch 真相
**目前真相**
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q35` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`
- `recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_until_exact_support_ready` / `reference_scope=bull|CAUTION`
**成功標準**
- probe / drilldown / `/api/status` / `/execution/status` / `/lab` / docs 全都承認 current live bucket exact support 未達 minimum rows，recommended patch 只能作治理 / 訓練參考。

### 目標 D：維持 Strategy Lab / leaderboard / venue-source blockers 的 product truth
**目前真相**
- `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`
- Strategy Lab legacy saved strategy 的實際區間已恢復，不再空白
- fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=2725` / `archive_window_coverage_pct=0.0`
- venue blockers：`live exchange credential / order ack lifecycle / fill lifecycle` 仍未驗證
**成功標準**
- Strategy Lab 不回退 placeholder-only，也不回退 `— → —` 假空白區間；排行榜 / 回測範圍 / 實際區間 contract 一致。
- venue/source blockers 在 operator-facing surfaces 維持可見；docs automation 每輪心跳都完成 overwrite sync。

---

## 下一輪 gate
1. **維持 breaker-first truth + current live bucket visibility across API / UI / docs**
   - 驗證：browser `/`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`
   - 升級 blocker：若 breaker release math 被 support / floor-gap / venue 話題覆蓋，或 current live bucket rows 再次從 top-level surfaces 消失
2. **持續鑽 recent canonical pathological slice，而不是 generic 化 root cause**
   - 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`
   - 升級 blocker：若 drift artifact 再失去 target-path / adverse-streak / top-shift 證據
3. **守住 Strategy Lab / leaderboard actual-range contract、reference-only patch、venue/source blockers 與 docs overwrite 閉環**
   - 驗證：browser `/lab`、`python scripts/hb_strategy_range_probe.py`、`curl http://127.0.0.1:<active-backend>/api/models/leaderboard`（依 `/health` 選健康 lane）、`data/q15_support_audit.json`、`data/execution_metadata_smoke.json`
   - 升級 blocker：若 patch 被誤升級成 deployable truth、排行榜 drift 成 placeholder-only、實際區間再掉回空白、venue/source blocker 消失、或 docs 再次落後 latest artifacts

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- current live bucket support truth 維持：**0/50 + exact_bucket_missing_exact_lane_proxy_only + reference_only_until_exact_support_ready**
- recent canonical pathological slice 仍以同一個 current window 為主敘事，不被 generic 問題稀釋
- Strategy Lab / leaderboard 維持 dual-role governance 與有效實際區間顯示；venue/source blockers 持續可見
- heartbeat runner 每輪自動完成：**issue 對齊 → patch/automation lane → verify artifacts → docs overwrite sync**
