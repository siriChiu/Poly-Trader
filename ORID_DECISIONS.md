# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-05-05 07:56:52 CST_

---

## 心跳 #1183 ORID

### O｜客觀事實
- collect + diagnostics refresh 完成：`Raw=32724 / Features=24125 / Labels=65894`；歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`；`simulated_pyramid_win=56.83%`。
- 即時部署阻塞點：`deployment_blocker=unsupported_exact_live_structure_bucket` / `streak=—` / `recent_window_wins=—/—` / `additional_recent_window_wins_needed=—`。
- q15 current-live bucket truth：`current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_proxy_reference_only`。
- support progress：`status=semantic_rebaseline_under_minimum` / `regression_basis=legacy_or_different_semantic_signature` / `legacy_supported_reference=199/50@20260423i` / `stagnant_run_count=2` / `stalled_support_accumulation=False` / `escalate_to_blocker=True`；active repair：`phase=semantic_evidence_backfill_or_exact_accumulation` / `component_verify_ready=False` / `live_exposure_allowed=False` / `shadow_or_paper_allowed=True` / `current_signal=HOLD` / `current_allowed_layers=0` / `guardrail=unsupported_exact_live_structure_bucket` / `actions=collect_exact_current_bucket_rows,force_q15_support_audit_refresh,semantic_legacy_evidence_backfill` / `legacy_evidence=reference_only_semantic_mismatch_or_missing_fields` / `legacy_supports_current_identity=False` / `legacy_promotable=False` / `legacy_mismatched=calibration_window`。
- latest recent-window diagnostics：`latest_window=100` / `win_rate=97.0%` / `dominant_regime=chop(71.0%)` / `avg_quality=+0.6271` / `avg_pnl=+0.0176` / `alerts=label_imbalance,regime_shift`。
- leaderboard / governance：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=current_full_no_bull_collapse_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split` / `payload_source=latest_persisted_snapshot` / `payload_stale=false` / `payload_age=3.5m`。
- source / venue blockers：`blocked_sparse_features=8`；fin_netflow=`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=3982` / `archive_window_coverage_pct=0.0`；venue proof 仍缺 credential / order ack / fill lifecycle；metadata smoke venue rows 已帶 proof_state / blockers / operator_next_action / verify_next。
- 實戰化 P0：`data/high_conviction_topk_oos_matrix.json` 已產出 `generated_at=2026-05-04T23:56:41.500766+00:00` / `freshness=fresh` / `age_min=0.2` / `stale_after_min=60` / `deployment_blocking=False` / `rows=24` / `deployable_rows=0` / `risk_qualified_rows=6` / `runtime_blocked_candidates=6` / `bucket_rows=0/50` / `gap=50`；最接近部署候選 `model=logistic_regression` / `top_k=top_2pct` / `tier=runtime_blocked_oos_pass` / `bucket_rows=0/50` / `gap=50`，仍被矩陣新鮮度或即時分桶 / 支持 gate 擋下。
- 本輪產品化前進：current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth；`/execution` 快捷列已補上 `/api/status` 初次同步 fail-closed：買入 / 啟用自動模式暫停，減碼保留；`/api/execution/overview` / `/api/execution/runs` 已走 20s operator-workspace timeout，避免 8s default 把可用 Bot 營運 payload 誤報成 `API timeout`；`/api/trade` 買入 / 加倉直接入口也會依即時部署阻塞點 409 暫停，且保留減倉 / 賣出風險降低路徑；`/execution/status` 與 `/execution` 已顯示即時部署阻塞條件卡；metadata smoke venue rows 已帶 per-venue proof_state / blockers / operator_next_action / verify_next，讓 Dashboard / Execution / Lab 直接顯示實單證據缺口；`recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_non_current_live_scope` / `reference_scope=bull|CAUTION`。

### R｜感受直覺
- 這輪最需要防止的誤讀，是把 `0/50` 的 same-bucket support 或 `bull|CAUTION` 參考 patch 誤讀成已可部署；目前 live blocker 已切到 `unsupported_exact_live_structure_bucket`。
- current live 已落在 `bull/BLOCK/BLOCK|bull_q15_bias50_overextended_block|q15`；如果 UI / docs 沒同步 latest artifacts，operator 很容易把 spillover pocket、舊 bucket，或 `/api/status` 尚未返回的 loading 狀態誤讀成可操作 runtime 真相。

### I｜意義洞察
1. **support truth ≠ deployment closure**：`support=0/50` 且 `support_route_verdict=exact_bucket_missing_proxy_reference_only` 只代表治理前進，還不能把 reference-only patch 升級成 runtime patch。
2. **真正主 blocker 已切到 q15 current-live bucket exact-support shortage**：recent pathological slice 仍是造成 `unsupported_exact_live_structure_bucket` 的根因切片，不能再沿用 breaker-first 舊敘事。
3. **docs overwrite sync 的角色是護欄，不是主阻塞**：current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth；`/execution` 快捷列已補上 `/api/status` 初次同步 fail-closed：買入 / 啟用自動模式暫停，減碼保留；`/api/execution/overview` / `/api/execution/runs` 已走 20s operator-workspace timeout，避免 8s default 把可用 Bot 營運 payload 誤報成 `API timeout`；`/api/trade` 買入 / 加倉直接入口也會依即時部署阻塞點 409 暫停，且保留減倉 / 賣出風險降低路徑；`/execution/status` 與 `/execution` 已顯示即時部署阻塞條件卡；metadata smoke venue rows 已帶 per-venue proof_state / blockers / operator_next_action / verify_next，讓 Dashboard / Execution / Lab 直接顯示實單證據缺口；這會讓 operator-facing surfaces 與 machine-readable artifacts 保持同輪收斂。
4. **實戰化不是堆模型，而是可拒單部署治理**：high-conviction top-k OOS ROI gate 把六色帽 / 研究交叉分析轉成產品契約；排序先分離離線驗證 / 模型風控門檻與即時分桶 / 支持 gate，避免最高 ROI 但高回撤 / 負最差分折的列誤導部署決策。

### D｜決策行動
- **Owner**：即時執行治理 lane
- **Action**：維持 current-live exact-support truth，並把 q15 current-live bucket support 與 reference-only patch 持續顯示清楚；下一步沿 recent pathological slice 與 exact-support accumulation 繼續追根因；`/execution` 操作入口在同步中 / 已阻塞時只對買入 / 加倉與啟用自動模式 fail-closed，減碼保留；直接 API 買入 / 加倉也必須 409 暫停，減倉 / 賣出保留風險降低路徑。
- **研究到產品 gate**：walk-forward OOS top-k matrix 已透過 `/api/models/leaderboard` 與 Strategy Lab 高信心 OOS Top-K 部署門檻面板可視化；operator 現在會先看到最接近部署候選（離線驗證 / 風控已過但只剩矩陣新鮮度 / 即時分桶 / 支持 gate 的 rows），並看到矩陣新鮮度、支持狀態、治理路徑、部署阻塞、即時分桶、樣本數與 gap；矩陣過期或即時分桶 / 支持 blockers 未解除前仍維持 fail-closed。
- **Artifacts**：`ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md`、`data/live_predict_probe.json`、`data/live_decision_quality_drilldown.json`、`data/recent_drift_report.json`、`data/high_conviction_topk_oos_matrix.json`。
- **Verify**：browser `/`、browser `/execution`（買入 / 啟用自動模式 fail-closed、減碼可用）、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、`python scripts/recent_drift_report.py`、`python -m pytest tests/test_server_startup.py -k api_trade -q`、`python -m pytest tests/test_topk_walkforward_precision.py -q`。
- **If fail**：只要 docs / UI 再次把 `unsupported_exact_live_structure_bucket` 誤寫成 breaker-first、漏掉 q15 current-live bucket rows，或把 reference-only patch 誤包裝成可部署 truth，就把 heartbeat 升級回 current-state governance blocker。
