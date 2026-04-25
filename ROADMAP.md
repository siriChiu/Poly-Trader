# ROADMAP.md — Current Plan Only

_最後更新：2026-04-26 03:57:33 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **full heartbeat #1041 已完成 collect + diagnostics refresh**
  - `Raw=32281 / Features=23699 / Labels=65118`
  - 歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`
  - `deployment_blocker=circuit_breaker_active` / `streak=26` / `recent_window_wins=9/50` / `additional_recent_window_wins_needed=6`
  - `latest_window=100` / `win_rate=9.0%` / `dominant_regime=bull(86.0%)` / `avg_quality=-0.1289` / `avg_pnl=-0.0052` / `alerts=label_imbalance,regime_shift`
- **current-state docs overwrite sync 已自動化**
  - heartbeat runner 會在 `auto_propose_fixes.py` 後直接覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 這條 lane 的目的不是美化文件，而是避免 `issues.json / live artifacts` 已更新、markdown docs 卻仍停在舊 truth 的治理裂縫
- **Execution Console / `/api/trade` 操作入口已 fail-closed（同步中 + 阻塞 + 直接 API）**
  - `/api/status` 初次同步前或部署阻塞存在時，買入 / 減碼 / 啟用自動模式快捷操作都顯示暫停並保持 disabled，只留下查看阻塞原因與重新整理；`/api/execution/overview` / `/api/execution/runs` 已走 20s operator-workspace timeout，避免後端並行診斷時 8s default 把可用 payload 誤報成 `API timeout`；後端 `POST /api/trade` 對買入 / 加倉會先讀即時部署阻塞點，阻塞時回 409 `current_live_deployment_blocker`，只保留減倉 / 賣出風險降低路徑
- **Execution Status / Bot 營運 已顯示熔斷解除條件**
  - `最近 50 筆目前 9/50，還差 6 勝；支持樣本 / q15 修補不可取代熔斷解除條件`；操作員執行介面先看熔斷解除條件，再看 support / q15 背景治理
- **本輪 current-state docs 已同步到最新 artifacts**
  - docs 與 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json` 的 current-state truth 已對齊

---

## 主目標

### 目標 A：維持熔斷解除條件作為唯一即時部署阻塞點
**目前真相**
- `deployment_blocker=circuit_breaker_active` / `streak=26` / `recent_window_wins=9/50` / `additional_recent_window_wins_needed=6`
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=14/50` / `gap=36` / `support_route_verdict=exact_bucket_present_but_below_minimum`
support progress：`status=semantic_rebaseline_under_minimum` / `regression_basis=legacy_or_different_semantic_signature` / `legacy_supported_reference=76/50@1039`
**成功標準**
- `/`、`/execution`、`/execution/status`、`/lab`、probe、drilldown、docs 都把熔斷解除條件視為唯一即時部署阻塞點；`/execution` 在 `/api/status` 初次同步前也不得開放買入 / 減碼 / 啟用自動模式；直接呼叫 `POST /api/trade` 的買入 / 加倉也必須依即時部署阻塞點以 409 暫停，且只保留減倉 / 賣出風險降低路徑。
- q15 current-live bucket truth (`bucket / rows / minimum / gap / support route`) 仍在 top-level surfaces 可 machine-read。

### 目標 B：持續把 recent canonical blocker pocket 當成 current blocker 根因來鑽
**目前真相**
- `latest_window=100` / `win_rate=9.0%` / `dominant_regime=bull(86.0%)` / `avg_quality=-0.1289` / `avg_pnl=-0.0052` / `alerts=label_imbalance,regime_shift`
**成功標準**
- drift / probe / docs 能同時指出 latest recent-window diagnostics 與 current blocker pocket，而不是退回 generic leaderboard / venue 摘要。

### 目標 C：守住 q15 current-live bucket support + reference-only patch 真相
**目前真相**
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=14/50` / `gap=36` / `support_route_verdict=exact_bucket_present_but_below_minimum`
support progress：`status=semantic_rebaseline_under_minimum` / `regression_basis=legacy_or_different_semantic_signature` / `legacy_supported_reference=76/50@1039`
- `recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_non_current_live_scope` / `reference_scope=bull|CAUTION`
**成功標準**
- probe / drilldown / `/api/status` / `/execution/status` / `/lab` / docs 全都承認 q15 current-live bucket exact support 未達 minimum rows，recommended patch 只能作治理 / 訓練參考。

### 目標 D：維持 leaderboard、venue/source blockers 與 docs automation 一致 product truth
**目前真相**
- `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=current_full_no_bull_collapse_4h` / `governance_contract=single_role_governance_ok` / `current_closure=single_profile_alignment` / `payload_source=latest_persisted_snapshot` / `payload_stale=true` / `payload_age=5.6h`
- fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3746` / `archive_window_coverage_pct=0.0`
- venue blockers：`live exchange credential / order ack lifecycle / fill lifecycle` 仍未驗證；API/UI 已把 per-venue proof state 與下一步驗證欄位掛到 metadata smoke venue rows
- docs automation：markdown docs 不再允許落後 live artifacts
**成功標準**
- Strategy Lab 不回退 placeholder-only；venue/source blockers 在 operator-facing surfaces 維持可見；docs automation 每輪心跳都自動完成 overwrite sync。

---

## 下一輪 gate
1. **維持熔斷優先真相 + q15 current-live bucket visibility across API / UI / docs**
   - 驗證：browser `/`、browser `/execution`（含初次同步時買入 / 減碼 / 自動模式暫停）、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、`python -m pytest tests/test_server_startup.py -k api_trade -q`
   - 升級 blocker：若熔斷解除條件被 support / floor-gap / venue 話題覆蓋，或 q15 current-live bucket rows 再次從 top-level surfaces 消失
2. **持續鑽 recent canonical pathological slice，而不是 generic 化 root cause**
   - 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`
   - 升級 blocker：若 drift artifact 再失去 target-path / adverse-streak / top-shift 證據
3. **守住 q15 current-live bucket support / reference-only patch、leaderboard governance、venue/source blockers 與 docs automation 閉環**
   - 驗證：browser `/lab`、`curl http://127.0.0.1:<active-backend>/api/models/leaderboard`（依 `/health` 選 8000/8001 健康 lane，不要硬綁單一 port）、`data/q15_support_audit.json`、`data/execution_metadata_smoke.json`、下輪 heartbeat docs sync status
   - 升級 blocker：若 patch 被誤升級成 deployable truth、排行榜 drift 成 placeholder-only、venue/source blocker 消失、或 docs 再次落後 latest artifacts

---

## 成功標準
- 即時部署阻塞點清楚且唯一：**熔斷解除條件**
- current live q15 truth 維持：**14/50 + exact_bucket_present_but_below_minimum + reference_only_non_current_live_scope**
- recent canonical diagnostics 與 current blocker pocket 需同步可見，不被 generic 問題稀釋
- leaderboard single-role governance 維持；venue/source blockers 持續可見
- heartbeat runner 每輪自動完成：**issue 對齊 → patch/automation lane → verify artifacts → docs overwrite sync**
- `/api/trade` 直接 API 不能繞過即時部署阻塞點：買入 / 加倉在 no-deploy 狀態必須 409，減倉 / 賣出仍可用
