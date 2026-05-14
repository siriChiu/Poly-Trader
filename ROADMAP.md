# ROADMAP.md — Current Plan Only

_最後更新：2026-05-14 15:11:52 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **fast heartbeat #1214 已完成 collect + diagnostics refresh**
  - `Raw=33182 / Features=24381 / Labels=66360`
  - 歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`
  - `deployment_blocker=circuit_breaker_active` / `streak=0` / `recent_window_wins=11/50` / `additional_recent_window_wins_needed=4`
  - `latest_window=100` / `win_rate=51.0%` / `dominant_regime=chop(100.0%)` / `avg_quality=+0.1522` / `avg_pnl=-0.0001` / `alerts=regime_concentration,regime_shift`
- **current-state docs overwrite sync 已自動化**
  - heartbeat runner 會在 `auto_propose_fixes.py` 後直接覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 這條 lane 的目的不是美化文件，而是避免 `issues.json / live artifacts` 已更新、markdown docs 卻仍停在舊 truth 的治理裂縫
- **Execution Console / `/api/trade` 操作入口已 fail-closed（同步中 + 阻塞 + 直接 API）**
  - `/api/status` 初次同步前或部署阻塞存在時，買入 / 加倉與啟用自動模式快捷操作顯示暫停並保持 disabled；減碼 / 賣出風險降低、切到手動模式、查看阻塞原因與重新整理仍可用；`/api/execution/overview` / `/api/execution/runs` 已走 20s operator-workspace timeout，避免後端並行診斷時 8s default 把可用 payload 誤報成 `API timeout`；後端 `POST /api/trade` 對買入 / 加倉會先讀即時部署阻塞點，阻塞時回 409 `current_live_deployment_blocker`，只保留減倉 / 賣出風險降低路徑；`data/live_predict_probe.json` 同步輸出 `api_trade_guardrail_active / api_trade_buy_guardrail / api_trade_allowed_risk_off_sides` 作為 machine-readable proof
- **Execution Status / Bot 營運 已顯示熔斷解除條件**
  - `最近 50 筆目前 11/50，還差 4 勝；當前 q15 分桶支持樣本 / 候選修補不可取代熔斷解除條件`；操作員執行介面先看熔斷解除條件，再看 當前 q15 分桶 support / 背景治理；`runtime_closure_summary` 已由 `model/runtime_closure.py` 共用中文化，避免後端英文枚舉與混合式治理文案泄漏到 Dashboard / Strategy Lab / Execution Status
- **本輪 current-state docs 已同步到最新 artifacts**
  - docs 與 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json` 的 current-state truth 已對齊

---

## 主目標

### 目標 A：維持熔斷解除條件作為唯一即時部署阻塞點
**目前真相**
- `deployment_blocker=circuit_breaker_active` / `streak=0` / `recent_window_wins=11/50` / `additional_recent_window_wins_needed=4`
- `current_live_structure_bucket=CAUTION|structure_quality_caution|q15` / `support=20/50` / `gap=30` / `support_route_verdict=exact_bucket_present_but_below_minimum`
- support progress：`status=semantic_rebaseline_under_minimum` / `regression_basis=legacy_or_different_semantic_signature` / `legacy_supported_reference=53/50@20260419b` / `stagnant_run_count=5` / `stalled_support_accumulation=False` / `escalate_to_blocker=True`；active repair：`phase=semantic_evidence_backfill_or_exact_accumulation` / `component_verify_ready=False` / `live_exposure_allowed=False` / `shadow_or_paper_allowed=True` / `current_signal=CIRCUIT_BREAKER` / `current_allowed_layers=0` / `guardrail=decision_quality_below_trade_floor; circuit_breaker_active` / `actions=collect_exact_current_bucket_rows,force_q15_support_audit_refresh,semantic_legacy_evidence_backfill` / `legacy_evidence=reference_only_semantic_mismatch_or_missing_fields` / `legacy_supports_current_identity=False` / `legacy_promotable=False` / `legacy_mismatched=calibration_window,entry_quality_label,regime_label`
**成功標準**
- `/`、`/execution`、`/execution/status`、`/lab`、probe、drilldown、docs 都把熔斷解除條件視為唯一即時部署阻塞點；`/execution` 在 `/api/status` 初次同步前也不得開放買入 / 啟用自動模式，阻塞期間只暫停買入 / 加倉與啟用自動模式，減碼 / 賣出風險降低路徑仍可用；直接呼叫 `POST /api/trade` 的買入 / 加倉也必須依即時部署阻塞點以 409 暫停，且只保留減倉 / 賣出風險降低路徑。
- q15 current-live bucket truth (`bucket / rows / minimum / gap / support route`) 仍在 top-level surfaces 可 machine-read。

### 目標 B：持續把 recent canonical blocker pocket 當成 current blocker 根因來鑽
**目前真相**
- `latest_window=100` / `win_rate=51.0%` / `dominant_regime=chop(100.0%)` / `avg_quality=+0.1522` / `avg_pnl=-0.0001` / `alerts=regime_concentration,regime_shift`
**成功標準**
- drift / probe / docs 能同時指出 latest recent-window diagnostics 與 current blocker pocket，而不是退回 generic leaderboard / venue 摘要。

### 目標 C：守住 q15 current-live bucket support + reference-only patch 真相
**目前真相**
- `current_live_structure_bucket=CAUTION|structure_quality_caution|q15` / `support=20/50` / `gap=30` / `support_route_verdict=exact_bucket_present_but_below_minimum`
- support progress：`status=semantic_rebaseline_under_minimum` / `regression_basis=legacy_or_different_semantic_signature` / `legacy_supported_reference=53/50@20260419b` / `stagnant_run_count=5` / `stalled_support_accumulation=False` / `escalate_to_blocker=True`；active repair：`phase=semantic_evidence_backfill_or_exact_accumulation` / `component_verify_ready=False` / `live_exposure_allowed=False` / `shadow_or_paper_allowed=True` / `current_signal=CIRCUIT_BREAKER` / `current_allowed_layers=0` / `guardrail=decision_quality_below_trade_floor; circuit_breaker_active` / `actions=collect_exact_current_bucket_rows,force_q15_support_audit_refresh,semantic_legacy_evidence_backfill` / `legacy_evidence=reference_only_semantic_mismatch_or_missing_fields` / `legacy_supports_current_identity=False` / `legacy_promotable=False` / `legacy_mismatched=calibration_window,entry_quality_label,regime_label`
- `recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_non_current_live_scope` / `reference_scope=bull|CAUTION`
**成功標準**
- probe / drilldown / `/api/status` / `/execution/status` / `/lab` / docs 全都承認 q15 current-live bucket exact support 未達 minimum rows，recommended patch 只能作治理 / 訓練參考。

### 目標 D：維持 leaderboard、venue/source blockers 與 docs automation 一致 product truth
**目前真相**
- `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=current_full_no_bull_collapse_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split` / `payload_source=latest_persisted_snapshot` / `payload_stale=false` / `payload_age=9.3m`
- top source blockers：`fin_netflow(source_auth_blocked/auth_missing, coverage=0.0%, archive_window=0.0%, forward_archive=ready)` / `claw(source_auth_blocked/auth_missing, coverage=14.7%, archive_window=88.1%, forward_archive=ready)` / `claw_intensity(source_auth_blocked/auth_missing, coverage=14.7%, archive_window=88.1%, forward_archive=ready)` / `nest_pred(source_tls_verify_failed/tls_verify_failed, coverage=16.3%, archive_window=97.9%, forward_archive=ready)`
- fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=4024` / `archive_window_coverage_pct=0.0`
- venue blockers：`live exchange credential / order ack lifecycle / fill lifecycle` 仍未驗證；API/UI 已把 per-venue proof state 與下一步驗證欄位掛到 metadata smoke venue rows
- docs automation：markdown docs 不再允許落後 live artifacts
**成功標準**
- Strategy Lab 不回退 placeholder-only；venue/source blockers 在 operator-facing surfaces 維持可見；docs automation 每輪心跳都自動完成 overwrite sync。

### 目標 E：建立 high-conviction top-k OOS ROI gate，把研究結論轉成實戰部署門檻
**目前真相**
- 六色帽會議與研究交叉分析已收斂：下一步不是增加交易頻率，而是用 walk-forward OOS / top-k precision / ROI / max drawdown / meta-labeling / uncertainty gate 決定是否允許 candidate 進入部署候選。
- 最新 matrix artifact 已產出：`artifact=data/high_conviction_topk_oos_matrix.json` / `generated_at=2026-05-14T07:02:29.999927+00:00` / `freshness=fresh` / `age_min=9.4` / `stale_after_min=60` / `deployment_blocking=False` / `samples=24274` / `rows=24` / `deployable_rows=0` / `risk_qualified_rows=6` / `runtime_blocked_candidates=6` / `support_route=exact_bucket_present_but_below_minimum` / `deployment_blocker=circuit_breaker_active` / `current_live_structure_bucket=CAUTION|structure_quality_caution|q15` / `current_live_structure_bucket_rows=20/50` / `current_live_structure_bucket_gap_to_minimum=30` / `release_ready=False` / `recent_window_wins=11/50` / `required_recent_window_wins=15` / `additional_recent_window_wins_needed=4` / `current_recent_window_win_rate=0.220`。
- 最接近部署候選優先：`model=logistic_regression` / `regime=all` / `top_k=top_2pct` / `oos_roi=0.9324` / `win_rate=0.8621` / `profit_factor=19.8864` / `max_drawdown=0.022` / `worst_fold=0.2068` / `trades=58` / `tier=runtime_blocked_oos_pass` / `verdict=not_deployable` / `support_route=exact_bucket_present_but_below_minimum` / `governance=exact_live_bucket_present_but_below_minimum` / `bucket=CAUTION|structure_quality_caution|q15` / `bucket_rows=20/50` / `gap=30` / `release_ready=False` / `recent_window_wins=11/50` / `required_recent_window_wins=15` / `additional_recent_window_wins_needed=4` / `current_recent_window_win_rate=0.220`；若只剩即時分桶 / 支持 / release gate，仍模擬觀察 / 影子驗證 / 僅觀察。
**成功標準**
- `data/high_conviction_topk_oos_matrix.json` 必須持續輸出 `generated_at / artifact_freshness_status / artifact_age_minutes / artifact_stale_after_minutes / artifact_deployment_blocking / model / feature_profile / regime / top_k / OOS ROI / win_rate / profit_factor / max_drawdown / worst_fold / trade_count / support_route / support_governance_route / deployment_blocker / runtime_closure_state / current_live_structure_bucket / current_live_structure_bucket_rows / minimum_support_rows / current_live_structure_bucket_gap_to_minimum / release_ready / current_recent_window_wins / required_recent_window_wins / additional_recent_window_wins_needed / deployable_verdict / gate_failures / model_gate_failures / live_gate_failures / deployment_candidate_tier`。
- `/api/models/leaderboard` 與 Strategy Lab 高信心 OOS Top-K 部署門檻面板以最接近部署候選優先排序：先看離線驗證 / 風控門檻、低回撤、最差分折，再看 ROI；若候選只剩矩陣新鮮度 / 即時分桶 / 支持 / breaker release 條件 / 場館 proof 未過，仍 fail-closed 到模擬觀察 / 影子驗證 / 僅觀察，並顯示矩陣新鮮度、支持狀態、治理路徑、部署阻塞、即時分桶與樣本數，外加 release math。

---

## 下一輪 gate
1. **維持熔斷優先真相 + q15 current-live bucket visibility across API / UI / docs**
   - 驗證：browser `/`、browser `/execution`（含初次同步時買入 / 啟用自動模式暫停、減碼可用）、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、`python -m pytest tests/test_server_startup.py -k api_trade -q`
   - 升級 blocker：若熔斷解除條件被 support / floor-gap / venue 話題覆蓋，或 q15 current-live bucket rows 再次從 top-level surfaces 消失
2. **持續鑽 recent canonical pathological slice，而不是 generic 化 root cause**
   - 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`
   - 升級 blocker：若 drift artifact 再失去 target-path / adverse-streak / top-shift 證據
3. **守住 q15 current-live bucket support / reference-only patch、leaderboard governance、venue/source blockers 與 docs automation 閉環**
   - 驗證：browser `/lab`、`curl http://127.0.0.1:<active-backend>/api/models/leaderboard`（依 `/health` 選 8000/8001 健康 lane，不要硬綁單一 port）、`data/q15_support_audit.json`、`data/execution_metadata_smoke.json`、下輪 heartbeat docs sync status
   - 升級 blocker：若 patch 被誤升級成 deployable truth、排行榜 drift 成 placeholder-only、venue/source blocker 消失、或 docs 再次落後 latest artifacts
4. **建立 high-conviction top-k OOS ROI gate，讓 Strategy Lab winner 先經研究→模擬觀察→影子驗證→小流量分級**
   - 驗證：`data/high_conviction_topk_oos_matrix.json`、`/api/models/leaderboard.high_conviction_topk`、Strategy Lab 高信心 OOS Top-K 部署門檻面板、`python -m pytest tests/test_model_leaderboard.py tests/test_frontend_decision_contract.py -k high_conviction -q`
   - 升級 blocker：若 scan winner 未經 OOS top-k / minimum support / drawdown / breaker release gate 就被標成 deployable，或 current-live unsupported 時仍允許 buy/add exposure

---

## 成功標準
- 即時部署阻塞點清楚且唯一：**熔斷解除條件**
- current live q15 truth 維持：**20/50 + exact_bucket_present_but_below_minimum + reference_only_non_current_live_scope**
- recent canonical diagnostics 與 current blocker pocket 需同步可見，不被 generic 問題稀釋
- leaderboard dual-role governance 維持；venue/source blockers 持續可見
- heartbeat runner 每輪自動完成：**issue 對齊 → patch/automation lane → verify artifacts → docs overwrite sync**
- `/api/trade` 直接 API 不能繞過即時部署阻塞點：買入 / 加倉在 no-deploy 狀態必須 409，減倉 / 賣出仍可用
