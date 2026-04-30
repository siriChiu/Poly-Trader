# ROADMAP.md — Current Plan Only

_最後更新：2026-04-30 09:20:10 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **full heartbeat #1144 已完成 collect + diagnostics refresh**
  - `Raw=32497 / Features=23915 / Labels=65599`
  - 歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`
  - `simulated_pyramid_win=56.73%`
- **current-state docs overwrite sync 已自動化且本輪已覆蓋更新**
  - heartbeat runner 會在 `auto_propose_fixes.py` 後直接覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`。
  - 本輪 docs 重新同步到 heartbeat #1144 artifacts 與 high-conviction live overlay patch truth。
- **Execution Console / `/api/trade` 操作入口已 fail-closed（同步中 + 阻塞 + 直接 API）**
  - `/api/status` 初次同步前或部署阻塞存在時，買入 / 加倉與啟用自動模式快捷操作暫停；減碼 / 賣出風險降低、切到手動模式、查看阻塞原因與重新整理仍可用。
  - `POST /api/trade` 對買入 / 加倉會先讀即時部署阻塞點，阻塞時回 409 `current_live_deployment_blocker`，只保留減倉 / 賣出風險降低路徑。
- **Execution Status / Bot 營運 已顯示即時部署阻塞條件**
  - `即時部署阻塞點=under_minimum_exact_live_structure_bucket`；當前 q15 分桶支持樣本 `9/50`，缺口 `41`。
- **本輪產品化 patch 已完成：cached leaderboard 也會刷新 high-conviction Top-K live support overlay**
  - `/api/models/leaderboard` 即使回 stale-while-revalidate cached payload，也會重新載入 `_load_high_conviction_topk_summary()`，讓 Strategy Lab 看到 fresh `live_predict_probe.json` support truth。
  - runtime 驗證：`support_governance_route=exact_live_bucket_present_but_below_minimum` / `support_route_deployable=false` / `deployment_blocker=under_minimum_exact_live_structure_bucket` / `support=9/50` / `gap=41`。
  - test coverage：`tests/test_model_leaderboard.py::test_api_model_leaderboard_refreshes_cached_high_conviction_live_support_overlay`。

---

## 主目標

### 目標 A：維持 current-live exact-support blocker 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=under_minimum_exact_live_structure_bucket`
- `current_live_structure_bucket=CAUTION|structure_quality_caution|q15` / `support=9/50` / `gap=41`
- `support_route_verdict=exact_bucket_present_but_below_minimum` / `support_governance_route=exact_live_bucket_present_but_below_minimum` / `support_route_deployable=false`
- support progress：`status=semantic_rebaseline_under_minimum` / `regression_basis=legacy_or_different_semantic_signature` / `legacy_supported_reference=53/50@20260419b`

**成功標準**
- `/`、`/execution`、`/execution/status`、`/lab`、probe、drilldown、docs 都把 `under_minimum_exact_live_structure_bucket` 視為唯一 current-live deployment blocker。
- q15 current-live bucket truth (`bucket / rows / minimum / gap / support route`) 仍在 top-level surfaces 可 machine-read。

### 目標 B：持續把 recent canonical blocker pocket 當成 current blocker 根因來鑽
**目前真相**
- `latest_window=100` / `win_rate=24.0%` / `dominant_regime=chop(87.0%)` / `avg_quality=-0.0602` / `avg_pnl=-0.0043` / `alerts=regime_shift`

**成功標準**
- drift / probe / docs 能同時指出 latest recent-window diagnostics 與 current blocker pocket，而不是退回 generic leaderboard / venue 摘要。

### 目標 C：守住 q15 current-live bucket support + reference-only patch 真相
**目前真相**
- `current_live_structure_bucket=CAUTION|structure_quality_caution|q15` / `support=9/50` / `gap=41`
- `recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_non_current_live_scope` / `reference_scope=bull|CAUTION`

**成功標準**
- probe / drilldown / `/api/status` / `/execution/status` / `/lab` / docs 全都承認 q15 current-live bucket exact support 未達 minimum rows，recommended patch 只能作治理 / 訓練參考。

### 目標 D：維持 leaderboard、venue/source blockers 與 docs automation 一致 product truth
**目前真相**
- `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=current_full_no_bull_collapse_4h` / `governance_contract=dual_role_governance_active` / `payload_source=latest_persisted_snapshot` / `payload_stale=false`。
- fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3930` / `archive_window_coverage_pct=0.0`。
- venue blockers：`live exchange credential / order ack lifecycle / fill lifecycle` 仍未驗證；API/UI 已把 per-venue proof state 與下一步驗證欄位掛到 metadata smoke venue rows。

**成功標準**
- Strategy Lab 不回退 placeholder-only；venue/source blockers 在 operator-facing surfaces 維持可見；docs automation 每輪心跳都自動完成 overwrite sync。

### 目標 E：high-conviction top-k OOS ROI gate 必須同時通過離線風控與 fresh live support overlay
**目前真相**
- 最新 matrix artifact：`artifact=data/high_conviction_topk_oos_matrix.json` / `samples=23869` / `rows=24` / `deployable_rows=0` / `risk_qualified_rows=6` / `runtime_blocked_candidates=6`。
- 最接近部署候選：`model=logistic_regression` / `regime=all` / `top_k=top_2pct` / `oos_roi=0.9324` / `win_rate=0.8621` / `profit_factor=19.8864` / `max_drawdown=0.022` / `worst_fold=0.2068` / `trades=58` / `tier=runtime_blocked_oos_pass` / `verdict=not_deployable`。
- 本輪修補：`/api/models/leaderboard.high_conviction_topk.support_context` 不再依賴 stale cached payload，會套用 fresh live q15 under-minimum truth。

**成功標準**
- `/api/models/leaderboard` 與 Strategy Lab 高信心 OOS Top-K 部署門檻面板以最接近部署候選優先排序；若候選只剩即時分桶 / 支持 / 場館 proof 未過，仍 fail-closed 到模擬觀察 / 影子驗證 / 僅觀察。
- cached payload 不得保留 stale `exact_live_lane_proxy_available` 或 deployable support truth 覆蓋 fresh `support=9/50` blocker。

---

## 下一輪 gate
1. **維持 current-live exact-support blocker + q15 current-live bucket visibility across API / UI / docs**
   - 驗證：browser `/`、browser `/execution`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、`python -m pytest tests/test_server_startup.py -k api_trade -q`。
2. **守住 high-conviction Top-K cached/live overlay contract**
   - 驗證：`curl /api/models/leaderboard` 或 helper script 應看到 `support_governance_route=exact_live_bucket_present_but_below_minimum`、`support_route_deployable=false`、`support=9/50`、`gap=41`。
   - 升級 blocker：若 cached leaderboard 再次顯示 stale proxy route 或 deployable support truth。
3. **持續鑽 recent canonical pathological slice，而不是 generic 化 root cause**
   - 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`。
4. **守住 q15 current-live bucket support / reference-only patch、leaderboard governance、venue/source blockers 與 docs automation 閉環**
   - 驗證：browser `/lab`、`data/q15_support_audit.json`、`data/execution_metadata_smoke.json`、下輪 heartbeat docs sync status。

---

## 成功標準
- current-live blocker 清楚且唯一：**under_minimum_exact_live_structure_bucket**。
- current live q15 truth 維持：**9/50 + exact_bucket_present_but_below_minimum + exact_live_bucket_present_but_below_minimum + support_route_deployable=false**。
- high-conviction OOS winner 不得因 stale cache 被誤升成 current-live deployable。
- recent canonical diagnostics 與 current blocker pocket 需同步可見，不被 generic 問題稀釋。
- leaderboard dual-role governance 維持；venue/source blockers 持續可見。
- heartbeat runner 每輪自動完成：**issue 對齊 → patch/automation lane → verify artifacts → docs overwrite sync**。
