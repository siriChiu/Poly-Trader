# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-05-15 08:12:40 CST_

---

## 心跳 #1236 ORID

### O｜客觀事實
- collect + diagnostics refresh 完成：`Raw=33243 / Features=24430 / Labels=66447`；歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`；`simulated_pyramid_win=56.81%`。
- 即時部署阻塞點：`deployment_blocker=decision_quality_below_trade_floor` / `streak=—` / `recent_window_wins=—/—` / `additional_recent_window_wins_needed=—`。
- q35 current-live bucket truth：`current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q35` / `support=2/50` / `gap=48` / `support_route_verdict=exact_bucket_present_but_below_minimum`。
- support progress：`status=regressed_under_minimum` / `regression_basis=same_identity_same_semantic_signature` / `legacy_supported_reference=—` / `stagnant_run_count=2` / `stalled_support_accumulation=False` / `escalate_to_blocker=True`。
- latest recent-window diagnostics：`latest_window=100` / `win_rate=51.0%` / `dominant_regime=chop(94.0%)` / `avg_quality=+0.1698` / `avg_pnl=+0.0029` / `alerts=regime_concentration,regime_shift`。
- current blocking pathological pocket：`blocking_window=250` / `win_rate=60.4%` / `dominant_regime=chop(95.2%)` / `avg_quality=+0.2346` / `avg_pnl=+0.0030` / `alerts=regime_concentration,regime_shift`。
- leaderboard / governance：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=current_full_no_bull_collapse_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split` / `payload_source=latest_persisted_snapshot` / `payload_stale=false` / `payload_age=0.1m`。
- source / venue blockers：`blocked_sparse_features=8`；top source blockers=`fin_netflow(source_auth_blocked/auth_missing, coverage=0.0%, archive_window=0.0%, forward_archive=ready)` / `claw(source_auth_blocked/auth_missing, coverage=14.6%, archive_window=87.4%, forward_archive=ready)` / `claw_intensity(source_auth_blocked/auth_missing, coverage=14.6%, archive_window=87.4%, forward_archive=ready)` / `nest_pred(source_tls_verify_failed/tls_verify_failed, coverage=16.2%, archive_window=97.1%, forward_archive=ready)`；fin_netflow=`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=4057` / `archive_window_coverage_pct=0.0`；venue proof 仍缺 credential / order ack / fill lifecycle；metadata smoke venue rows 已帶 proof_state / blockers / operator_next_action / verify_next。
- q35 scaling audit 已指出目前不是單點 bias50 closure： `overall_verdict=bias50_formula_may_be_too_harsh` / `redesign_verdict=base_stack_redesign_discriminative_reweight_crosses_floor_but_execution_blocked` / `runtime_gap_to_floor=0.038` / `redesign_entry_quality=0.5679` / `redesign_allowed_layers=0` / `positive_discriminative_gap=True` / `execution_blocked_after_floor_cross=True`。
- 實戰化 P0：`data/high_conviction_topk_oos_matrix.json` 已產出 `generated_at=2026-05-15T00:02:39.538090+00:00` / `freshness=fresh` / `age_min=0.2` / `stale_after_min=60` / `deployment_blocking=False` / `rows=24` / `deployable_rows=0` / `risk_qualified_rows=6` / `runtime_blocked_candidates=6` / `bucket_rows=2/50` / `gap=48`；最接近部署候選 `model=logistic_regression` / `top_k=top_2pct` / `tier=runtime_blocked_oos_pass` / `bucket_rows=2/50` / `gap=48`，仍被矩陣新鮮度或即時分桶 / 支持 / release gate 擋下。
- 本輪產品化前進：current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth；`/execution` 快捷列已補上 `/api/status` 初次同步 fail-closed：買入 / 啟用自動模式暫停，減碼保留；`/api/execution/overview` / `/api/execution/runs` 已走 20s operator-workspace timeout，避免 8s default 把可用 Bot 營運 payload 誤報成 `API timeout`；`/api/trade` 買入 / 加倉直接入口也會依即時部署阻塞點 409 暫停，且保留減倉 / 賣出風險降低路徑；`/execution/status` 與 `/execution` 已顯示即時部署阻塞條件卡；`runtime_closure_summary` 已由 `model/runtime_closure.py` 共用中文化，避免後端英文枚舉與混合式治理文案泄漏到 Dashboard / Strategy Lab / Execution Status；metadata smoke venue rows 已帶 per-venue proof_state / blockers / operator_next_action / verify_next，讓 Dashboard / Execution / Lab 直接顯示實單證據缺口；FeatureChart 已把覆蓋率 / 稀疏來源阻塞 copy 轉成繁中 operator copy，隱藏特徵摘要不再顯示 raw `coverage/archive/last/latest/distinct/fallback` token；`recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_non_current_live_scope` / `reference_scope=bull|CAUTION`。

### R｜感受直覺
- 這輪最需要防止的誤讀，是讓舊 blocker 敘事覆蓋最新 `decision_quality_below_trade_floor` runtime truth。
- current live 已落在 `chop/CAUTION/CAUTION|base_caution_regime_or_bias|q35`；如果 UI / docs 沒同步 latest artifacts，operator 很容易把 spillover pocket、舊 bucket，或 `/api/status` 尚未返回的 loading 狀態誤讀成可操作 runtime 真相。

### I｜意義洞察
1. **support truth ≠ deployment closure**：`support=2/50` 且 `support_route_verdict=exact_bucket_present_but_below_minimum` 只代表治理前進，還不能把 reference-only patch 升級成 runtime patch。
2. **真正主 blocker 以 latest runtime truth 為準**：目前 deployment blocker 是 `decision_quality_below_trade_floor`，後續 root-cause 與 docs 必須跟著這條 lane 收斂。
3. **docs overwrite sync 的角色是護欄，不是主阻塞**：current-state docs 已 overwrite sync 到 `issues.json / live probe / drilldown` 最新 truth；FeatureChart 覆蓋率 / 稀疏來源 copy 已改用繁中 operator wording，讓 operator-facing surfaces 與 machine-readable artifacts 保持同輪收斂，而不再把 raw telemetry token 當成產品狀態。
4. **實戰化不是堆模型，而是可拒單部署治理**：high-conviction top-k OOS ROI gate 把六色帽 / 研究交叉分析轉成產品契約；排序先分離離線驗證 / 模型風控門檻與即時分桶 / 支持 gate，避免最高 ROI 但高回撤 / 負最差分折的列誤導部署決策。

### D｜決策行動
- **Owner**：即時執行治理 lane
- **Action**：維持 latest runtime blocker truth，並把 q35 current-live bucket support 與 reference-only patch 持續顯示清楚；下一步沿對應 runtime lane 繼續追根因；`/execution` 操作入口在同步中 / 已阻塞時只對買入 / 加倉與啟用自動模式 fail-closed，減碼保留；直接 API 買入 / 加倉也必須 409 暫停，減倉 / 賣出保留風險降低路徑。
- **Research-to-product gate**：walk-forward OOS top-k matrix 已透過 `/api/models/leaderboard` 與 Strategy Lab 高信心 OOS Top-K 部署門檻面板可視化；operator 現在會先看到最接近部署候選（離線驗證 / 風控已過但只剩矩陣新鮮度 / 即時分桶 / 支持 / release gate 的 rows），並看到矩陣新鮮度、支持狀態、治理路徑、部署阻塞、即時分桶、樣本數、recent-window wins、required wins、additional wins needed，且列級即時訊號已改用繁中操作語；矩陣過期或即時分桶 / 支持 / release blockers 未解除前仍維持 fail-closed。
- **Dashboard coverage gate**：FeatureChart 的覆蓋率 / 稀疏來源阻塞卡必須維持繁中 operator copy；若再出現 raw coverage/archive/last/latest/distinct/fallback token，下一輪直接升級成 operator-surface regression。
- **Artifacts**：`ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md`、`data/live_predict_probe.json`、`data/live_decision_quality_drilldown.json`、`data/recent_drift_report.json`、`data/high_conviction_topk_oos_matrix.json`。
- **Verify**：browser `/`、browser `/execution`（買入 / 啟用自動模式 fail-closed、減碼可用）、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、`python scripts/recent_drift_report.py`、`python -m pytest tests/test_server_startup.py -k api_trade -q`、`python -m pytest tests/test_topk_walkforward_precision.py -q`。
- **If fail**：只要 docs / UI 再次把 `decision_quality_below_trade_floor` 蓋回舊 blocker 敘事、漏掉 q35 current-live bucket rows，或把 reference-only patch 誤包裝成可部署 truth，就把 heartbeat 升級回 current-state governance blocker。
