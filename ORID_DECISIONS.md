# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-05-13 20:26:01 CST_

---

## 心跳 #1188 ORID

### O｜客觀事實
- collect + diagnostics refresh 完成：`Raw=32998 / Features=24328 / Labels=66288`；歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`；`simulated_pyramid_win=56.82%`。
- 即時部署阻塞點：`deployment_blocker=decision_quality_below_trade_floor` / `streak=—` / `recent_window_wins=—/—` / `additional_recent_window_wins_needed=—`。
- q15 current-live bucket truth：`current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=95/50` / `gap=0` / `support_route_verdict=exact_bucket_supported`。
- support progress：`status=exact_supported` / `regression_basis=current_identity` / `legacy_supported_reference=122/50@1094` / `stagnant_run_count=3` / `stalled_support_accumulation=False` / `escalate_to_blocker=False`；active repair：`phase=support_ready_floor_or_execution_verify` / `component_verify_ready=True` / `live_exposure_allowed=False` / `shadow_or_paper_allowed=True` / `current_signal=HOLD` / `current_allowed_layers=0` / `guardrail=decision_quality_below_trade_floor` / `actions=semantic_legacy_evidence_backfill,verify_floor_and_execution_guardrail` / `legacy_evidence=reference_only_semantic_mismatch_or_missing_fields` / `legacy_supports_current_identity=False` / `legacy_promotable=False` / `legacy_mismatched=calibration_window`。
- latest recent-window diagnostics：`latest_window=250` / `win_rate=67.2%` / `dominant_regime=chop(94.4%)` / `avg_quality=+0.3018` / `avg_pnl=+0.0047` / `alerts=regime_concentration,regime_shift`。
- leaderboard / governance：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=current_full_no_bull_collapse_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split` / `payload_source=latest_persisted_snapshot` / `payload_stale=false` / `payload_age=0.2m`。
- source / venue blockers：`blocked_sparse_features=8`；fin_netflow=`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3991` / `archive_window_coverage_pct=0.0`；venue proof 仍缺 credential / order ack / fill lifecycle；metadata smoke venue rows 已帶 proof_state / blockers / operator_next_action / verify_next。
- 實戰化 P0：`data/high_conviction_topk_oos_matrix.json` 已產出 `generated_at=2026-05-13T12:21:36.841568+00:00` / `freshness=fresh` / `age_min=0.2` / `stale_after_min=60` / `deployment_blocking=False` / `rows=24` / `deployable_rows=0` / `risk_qualified_rows=6` / `runtime_blocked_candidates=6` / `bucket_rows=95/50` / `gap=0`；最接近部署候選 `model=logistic_regression` / `top_k=top_2pct` / `tier=runtime_blocked_oos_pass` / `bucket_rows=95/50` / `gap=0`，仍被矩陣新鮮度或即時分桶 / 支持 gate 擋下。
- 本輪產品化前進：`model/predictor.py` 已收緊 q15 exact-supported component patch guardrail：只有 current-live q15 audit 同 identity、`exact_bucket_supported`、machine-readable answer、floor-cross legality 全通過時才套用 patch；同時 q15 audit canonical support rows（95/50）會覆蓋 stale DQ exact-scope 2-row 計數，避免 support closure 被錯誤回滾。最新 runtime 為 `q15_exact_supported_component_patch_applied=True` / `entry_quality=0.5501` / `allowed_layers_raw=1` / final `allowed_layers=0` / `runtime_closure_state=patch_active_but_execution_blocked` / blocker=`decision_quality_below_trade_floor`。current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth；`/execution` 快捷列與 `/api/trade` 仍維持買入 / 加倉 fail-closed，減碼 / 賣出風險降低路徑保留；metadata smoke venue rows 持續顯示 per-venue proof_state / blockers / operator_next_action / verify_next。

### R｜感受直覺
- 這輪最需要防止的誤讀，是讓舊 blocker 敘事覆蓋最新 `decision_quality_below_trade_floor` runtime truth。
- current live 已落在 `chop/CAUTION/CAUTION|base_caution_regime_or_bias|q15`；如果 UI / docs 沒同步 latest artifacts，operator 很容易把 spillover pocket、舊 bucket，或 `/api/status` 尚未返回的 loading 狀態誤讀成可操作 runtime 真相。

### I｜意義洞察
1. **support truth ≠ deployment closure**：`support=95/50` 且 `support_route_verdict=exact_bucket_supported` 只代表 same-bucket support 狀態，真正 deployment blocker 仍由 latest runtime truth 決定。
2. **真正主 blocker 以 latest runtime truth 為準**：目前 deployment blocker 是 `decision_quality_below_trade_floor`，後續 root-cause 與 docs 必須跟著這條 lane 收斂。
3. **docs overwrite sync + runtime guardrail 是護欄，不是主阻塞**：current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth；predictor 現在會拒絕 stale/mismatched q15 audit 套用 patch，並用 active current-live q15 audit 的 same-identity support rows 防止 support closure 被 stale 2-row scope 回滾；這會讓 operator-facing surfaces 與 machine-readable artifacts 保持同輪收斂。
4. **實戰化不是堆模型，而是可拒單部署治理**：high-conviction top-k OOS ROI gate 把六色帽 / 研究交叉分析轉成產品契約；排序先分離離線驗證 / 模型風控門檻與即時分桶 / 支持 gate，避免最高 ROI 但高回撤 / 負最差分折的列誤導部署決策。

### D｜決策行動
- **Owner**：即時執行治理 lane
- **Action**：維持 latest runtime blocker truth，並把 q15 current-live bucket support truth、q15 patch 狀態、allowed_layers_raw 與 final allowed_layers 邊界持續顯示清楚；下一步沿對應 runtime lane 繼續追根因；`/execution` 操作入口在同步中 / 已阻塞時只對買入 / 加倉與啟用自動模式 fail-closed，減碼保留；直接 API 買入 / 加倉也必須 409 暫停，減倉 / 賣出保留風險降低路徑。
- **研究到產品 gate**：walk-forward OOS top-k matrix 已透過 `/api/models/leaderboard` 與 Strategy Lab 高信心 OOS Top-K 部署門檻面板可視化；operator 現在會先看到最接近部署候選（離線驗證 / 風控已過但只剩矩陣新鮮度 / 即時分桶 / 支持 gate 的 rows），並看到矩陣新鮮度、支持狀態、治理路徑、部署阻塞、即時分桶、樣本數與 gap；矩陣過期或即時分桶 / 支持 blockers 未解除前仍維持 fail-closed。
- **Artifacts**：`ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md`、`data/live_predict_probe.json`、`data/live_decision_quality_drilldown.json`、`data/recent_drift_report.json`、`data/high_conviction_topk_oos_matrix.json`。
- **Verify**：browser `/`、browser `/execution`（買入 / 啟用自動模式 fail-closed、減碼可用）、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、`python scripts/recent_drift_report.py`、`python -m pytest tests/test_predictor_q15_component_patch.py tests/test_hb_predict_probe.py tests/test_q15_support_audit.py -q`、`python -m pytest tests/test_server_startup.py -k api_trade -q`、`python -m pytest tests/test_topk_walkforward_precision.py -q`。
- **If fail**：只要 docs / UI 再次把 `decision_quality_below_trade_floor` 蓋回舊 blocker 敘事、漏掉 q15 current-live bucket rows，或把 support closure 誤讀成 deployment closure，就把 heartbeat 升級回 current-state governance blocker。
