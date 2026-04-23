# ROADMAP.md — Current Plan Only

_最後更新：2026-04-24 03:28:21 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **fast heartbeat #20260424d 已完成 collect + diagnostics refresh**
  - `Raw=32089 / Features=23507 / Labels=64399`
  - `2y_backfill_ok=True` / `simulated_pyramid_win=56.99%`
  - `deployment_blocker=circuit_breaker_active` / `recent_window_wins=14/50` / `additional_recent_window_wins_needed=1`
  - `latest_window=100` / `win_rate=36.0%` / `dominant_regime=bull(99.0%)` / `avg_quality=-0.0395` / `avg_pnl=-0.0025`
- **current-state docs overwrite sync 已自動化**
  - heartbeat runner 會在 `auto_propose_fixes.py` 後直接覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - markdown docs 不再允許落後 `issues.json / live artifacts`
- **Strategy Lab detail payload / cache 已 bounded，保住兩年工作區但不再膨脹**
  - `/api/strategies/{name}` detail 現在把 `equity_curve` 壓到 `<=1000`、`score_series` 壓到 `<=300`，但保留完整 `chart_context.start/end`
  - 瀏覽器 cache 驗證：`polytrader.strategylab.cache.v1` 為 `equity_curve=1000` / `score_series=300` / `chart_context.limit=1000`
  - API probe：實際 detail payload `324162 bytes`，避免 Strategy Lab 工作區 / session cache 再塞進多 MB 歷史序列

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=circuit_breaker_active` / `recent_window_wins=14/50` / `additional_recent_window_wins_needed=1` / `streak=0`
- `current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_proxy_reference_only`
**成功標準**
- `/`、`/execution`、`/execution/status`、`/lab`、probe、drilldown、docs 都把 breaker release math 視為唯一 current-live deployment blocker。
- q15 current-live bucket truth（`bucket / rows / minimum / gap / support route`）仍在 top-level surfaces 可 machine-read。

### 目標 B：持續把 recent canonical blocker pocket 當成 current blocker 根因來鑽
**目前真相**
- `latest_window=100` / `win_rate=36.0%` / `dominant_regime=bull(99.0%)` / `avg_quality=-0.0395` / `avg_pnl=-0.0025`
- `alerts=regime_concentration,regime_shift` / `adverse_streak=42x0` / `top_shift=feat_local_top_score,feat_turning_point_score,feat_volume_exhaustion`
**成功標準**
- drift / probe / docs 能同時指出 latest recent-window diagnostics 與 current blocker pocket，而不是退回 generic leaderboard / venue 摘要。

### 目標 C：守住 q15 current-live bucket support + reference-only patch 真相
**目前真相**
- `current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15` / `support=0/50` / `gap=50`
- `support_route_verdict=exact_bucket_missing_proxy_reference_only` / `support_progress.status=regressed_under_minimum`
- `recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_non_current_live_scope` / `reference_scope=bull|CAUTION`
**成功標準**
- probe / drilldown / `/api/status` / `/execution/status` / `/lab` / docs 全都承認 q15 current-live bucket exact support 未達 minimum rows，recommended patch 只能作治理 / 訓練參考。

### 目標 D：維持 leaderboard、Strategy Lab、venue/source blockers 與 docs automation 一致 product truth
**目前真相**
- `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h` / `governance_contract=dual_role_governance_active`
- Strategy Lab detail payload / cache 已 bounded：`equity_curve<=1000` / `score_series<=300` / 保留兩年 `chart_context`
- fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3557` / `archive_window_coverage_pct=0.0`
- venue blockers：`live exchange credential / order ack lifecycle / fill lifecycle` 仍未驗證
- docs automation：markdown docs 不再允許落後 live artifacts
**成功標準**
- Strategy Lab 不回退 placeholder-only、stale detail 或多 MB workspace payload；venue/source blockers 在 operator-facing surfaces 維持可見；docs automation 每輪心跳都自動完成 overwrite sync。

---

## 下一輪 gate
1. **維持 breaker-first truth + q15 current-live bucket visibility across API / UI / docs**
   - 驗證：browser `/`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`
   - 升級 blocker：若 breaker release math 被 support / floor-gap / venue 話題覆蓋，或 q15 current-live bucket rows / gap / support route 再次從 top-level surfaces 消失
2. **持續鑽 recent canonical pathological slice，而不是 generic 化 root cause**
   - 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`
   - 升級 blocker：若 drift artifact 再失去 target-path / adverse-streak / sibling-window 對照證據
3. **守住 leaderboard / Strategy Lab bounded payload、reference-only patch、venue/source blockers 與 docs automation 閉環**
   - 驗證：browser `/lab`、`curl http://127.0.0.1:<active-backend>/api/models/leaderboard`、`curl http://127.0.0.1:<active-backend>/api/strategies/<name>`、`pytest tests/test_strategy_lab.py tests/test_strategy_lab_manual_model_and_auto_contract.py tests/test_frontend_decision_contract.py -q`、`cd web && npm run build`
   - 升級 blocker：若 Strategy Lab detail 再回到多 MB payload / cache 膨脹、排行榜 drift 成 placeholder-only、patch 被誤升級成 deployable truth、venue/source blocker 消失、或 docs 再次落後 latest artifacts

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- current live q15 truth 維持：**0/50 + exact_bucket_missing_proxy_reference_only + reference_only_non_current_live_scope**
- recent canonical diagnostics 與 current blocker pocket 需同步可見，不被 generic 問題稀釋
- Strategy Lab 工作區維持：**兩年 chart context 保留，但 detail payload / cache 被 bounded**
- leaderboard 維持 dual-role governance；venue/source blockers 持續可見
- heartbeat runner 每輪自動完成：**issue 對齊 → patch/automation lane → verify artifacts → docs overwrite sync**
