# ROADMAP.md — Current Plan Only

_最後更新：2026-04-29 22:11:39 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **fast heartbeat #1128-productization 已完成 collect + diagnostics refresh**
  - `Raw=32476 / Features=23894 / Labels=65564`
  - 歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`
  - `deployment_blocker=unsupported_exact_live_structure_bucket` / `streak=None` / `recent_window_wins=None/None` / `additional_recent_window_wins_needed=—`
  - `latest_window=100` / `win_rate=18.0%` / `dominant_regime=chop(93.0%)` / `avg_quality=-0.1311` / `avg_pnl=-0.0069` / `alerts=label_imbalance,regime_concentration,regime_shift`
- **current-state docs overwrite sync 已自動化**
  - heartbeat runner 會在 `auto_propose_fixes.py` 後直接覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 這條 lane 的目的不是美化文件，而是避免 `issues.json / live artifacts` 已更新、markdown docs 卻仍停在舊 truth 的治理裂縫
- **Execution Console / `/api/trade` 操作入口已 fail-closed（同步中 + 阻塞 + 直接 API）**
  - `/api/status` 初次同步前或部署阻塞存在時，買入 / 加倉與啟用自動模式快捷操作顯示暫停並保持 disabled；減碼 / 賣出風險降低、切到手動模式、查看阻塞原因與重新整理仍可用；`/api/execution/overview` / `/api/execution/runs` 已走 20s operator-workspace timeout，避免後端並行診斷時 8s default 把可用 payload 誤報成 `API timeout`；後端 `POST /api/trade` 對買入 / 加倉會先讀即時部署阻塞點，阻塞時回 409 `current_live_deployment_blocker`，只保留減倉 / 賣出風險降低路徑；`data/live_predict_probe.json` 同步輸出 `api_trade_guardrail_active / api_trade_buy_guardrail / api_trade_allowed_risk_off_sides` 作為 machine-readable proof
- **Execution Status / Bot 營運 已顯示熔斷解除條件**
  - `最近 None 筆目前 None/None，還差 — 勝；當前 q15 分桶支持樣本 / 候選修補不可取代熔斷解除條件`；操作員執行介面先看熔斷解除條件，再看 當前 q15 分桶 support / 背景治理
- **本輪 current-state docs 已同步到最新 artifacts**
  - docs 與 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json` 的 current-state truth 已對齊

---

## 主目標

### 目標 A：維持 current-live exact-support blocker 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=unsupported_exact_live_structure_bucket` / `streak=None` / `recent_window_wins=None/None` / `additional_recent_window_wins_needed=—`
- `current_live_structure_bucket=CAUTION|structure_quality_caution|q15` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_proxy_reference_only`
support progress：`status=semantic_rebaseline_under_minimum` / `regression_basis=legacy_or_different_semantic_signature` / `legacy_supported_reference=53/50@20260419b`
**成功標準**
- `/`、`/execution`、`/execution/status`、`/lab`、probe、drilldown、docs 都把 `unsupported_exact_live_structure_bucket` 視為唯一 current-live deployment blocker，且不再誤回退成 breaker-first 舊敘事；`/execution` 在 `/api/status` 初次同步前也不得開放買入 / 啟用自動模式，阻塞期間只暫停買入 / 加倉與啟用自動模式，減碼 / 賣出風險降低路徑仍可用；直接呼叫 `POST /api/trade` 的買入 / 加倉也必須依即時部署阻塞點以 409 暫停，且只保留減倉 / 賣出風險降低路徑。
- q15 current-live bucket truth (`bucket / rows / minimum / gap / support route`) 仍在 top-level surfaces 可 machine-read。

### 目標 B：持續把 recent canonical blocker pocket 當成 current blocker 根因來鑽
**目前真相**
- `latest_window=100` / `win_rate=18.0%` / `dominant_regime=chop(93.0%)` / `avg_quality=-0.1311` / `avg_pnl=-0.0069` / `alerts=label_imbalance,regime_concentration,regime_shift`
**成功標準**
- drift / probe / docs 能同時指出 latest recent-window diagnostics 與 current blocker pocket，而不是退回 generic leaderboard / venue 摘要。

### 目標 C：守住 q15 current-live bucket support + reference-only patch 真相
**目前真相**
- `current_live_structure_bucket=CAUTION|structure_quality_caution|q15` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_proxy_reference_only`
support progress：`status=semantic_rebaseline_under_minimum` / `regression_basis=legacy_or_different_semantic_signature` / `legacy_supported_reference=53/50@20260419b`
- `recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_non_current_live_scope` / `reference_scope=bull|CAUTION`
**成功標準**
- probe / drilldown / `/api/status` / `/execution/status` / `/lab` / docs 全都承認 q15 current-live bucket exact support 未達 minimum rows，recommended patch 只能作治理 / 訓練參考。

### 目標 D：維持 leaderboard、venue/source blockers 與 docs automation 一致 product truth
**目前真相**
- `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=current_full_no_bull_collapse_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split` / `payload_source=latest_persisted_snapshot` / `payload_stale=false` / `payload_age=7.8m`
- fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3909` / `archive_window_coverage_pct=0.0`
- venue blockers：`live exchange credential / order ack lifecycle / fill lifecycle` 仍未驗證；API/UI 已把 per-venue proof state 與下一步驗證欄位掛到 metadata smoke venue rows
- docs automation：markdown docs 不再允許落後 live artifacts
**成功標準**
- Strategy Lab 不回退 placeholder-only；venue/source blockers 在 operator-facing surfaces 維持可見；docs automation 每輪心跳都自動完成 overwrite sync。

### 目標 E：建立 high-conviction top-k OOS ROI gate，把研究結論轉成實戰部署門檻
**目前真相**
- 六色帽會議與研究交叉分析已收斂：下一步不是增加交易頻率，而是用 walk-forward OOS / top-k precision / ROI / max drawdown / meta-labeling / uncertainty gate 決定是否允許 candidate 進入部署候選。
- 最新 matrix artifact 已產出：`artifact=data/high_conviction_topk_oos_matrix.json` / `samples=23858` / `rows=24` / `deployable_rows=0` / `risk_qualified_rows=6` / `runtime_blocked_candidates=6` / `support_route=exact_bucket_missing_proxy_reference_only` / `deployment_blocker=unsupported_exact_live_structure_bucket`。
- 最接近部署候選優先：`model=logistic_regression` / `regime=all` / `top_k=top_2pct` / `oos_roi=0.9324` / `win_rate=0.8621` / `profit_factor=19.8864` / `max_drawdown=0.022` / `worst_fold=0.2068` / `trades=58` / `tier=runtime_blocked_oos_pass` / `verdict=not_deployable`；若只剩 current-live/support gate，仍 paper-shadow / hold-only。
**成功標準**
- `data/high_conviction_topk_oos_matrix.json` 必須持續輸出 `model / feature_profile / regime / top_k / OOS ROI / win_rate / profit_factor / max_drawdown / worst_fold / trade_count / support_route / deployable_verdict / gate_failures / model_gate_failures / live_gate_failures / deployment_candidate_tier`。
- `/api/models/leaderboard` 與 Strategy Lab 高信心 OOS Top-K Gate panel 以最接近部署候選優先排序：先看 OOS/風控 gates、低回撤、worst fold，再看 ROI；若候選只剩 current-live/support/venue proof 未過，仍 fail-closed 到 paper/shadow/hold-only。

---

## 下一輪 gate
1. **維持 current-live exact-support blocker + q15 current-live bucket visibility across API / UI / docs**
   - 驗證：browser `/`、browser `/execution`（含初次同步時買入 / 啟用自動模式暫停、減碼可用）、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、`python -m pytest tests/test_server_startup.py -k api_trade -q`
   - 升級 blocker：若 current-live blocker 被 breaker 舊敘事 / venue 話題覆蓋，或 q15 current-live bucket rows 再次從 top-level surfaces 消失
2. **持續鑽 recent canonical pathological slice，而不是 generic 化 root cause**
   - 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`
   - 升級 blocker：若 drift artifact 再失去 target-path / adverse-streak / top-shift 證據
3. **守住 q15 current-live bucket support / reference-only patch、leaderboard governance、venue/source blockers 與 docs automation 閉環**
   - 驗證：browser `/lab`、`curl http://127.0.0.1:<active-backend>/api/models/leaderboard`（依 `/health` 選 8000/8001 健康 lane，不要硬綁單一 port）、`data/q15_support_audit.json`、`data/execution_metadata_smoke.json`、下輪 heartbeat docs sync status
   - 升級 blocker：若 patch 被誤升級成 deployable truth、排行榜 drift 成 placeholder-only、venue/source blocker 消失、或 docs 再次落後 latest artifacts
4. **建立 high-conviction top-k OOS ROI gate，讓 Strategy Lab winner 先經 research→paper→shadow→canary 分級**
   - 驗證：`data/high_conviction_topk_oos_matrix.json`、`/api/models/leaderboard.high_conviction_topk`、Strategy Lab 高信心 OOS Top-K Gate panel、`python -m pytest tests/test_model_leaderboard.py tests/test_frontend_decision_contract.py -k high_conviction -q`
   - 升級 blocker：若 scan winner 未經 OOS top-k / minimum support / drawdown gate 就被標成 deployable，或 current-live unsupported 時仍允許 buy/add exposure

---

## 成功標準
- current-live blocker 清楚且唯一：**unsupported_exact_live_structure_bucket**
- current live q15 truth 維持：**0/50 + exact_bucket_missing_proxy_reference_only + reference_only_non_current_live_scope**
- recent canonical diagnostics 與 current blocker pocket 需同步可見，不被 generic 問題稀釋
- leaderboard dual-role governance 維持；venue/source blockers 持續可見
- heartbeat runner 每輪自動完成：**issue 對齊 → patch/automation lane → verify artifacts → docs overwrite sync**
- `/api/trade` 直接 API 不能繞過即時部署阻塞點：買入 / 加倉在 no-deploy 狀態必須 409，減倉 / 賣出仍可用
