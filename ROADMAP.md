# ROADMAP.md — Current Plan Only

_最後更新：2026-05-24 06:11:34 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **fast heartbeat #1470 已完成 collect + diagnostics refresh**
  - `Raw=34240 / Features=25208 / Labels=67944`
  - 歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`
  - `deployment_blocker=circuit_breaker_active` / `streak=0` / `recent_window_wins=13/50` / `additional_recent_window_wins_needed=2`
  - `latest_window=100` / `win_rate=13.0%` / `dominant_regime=chop(53.0%)` / `avg_quality=-0.2351` / `avg_pnl=-0.0101` / `alerts=label_imbalance`
  - shadow-only falsification：`mode=shadow_only_no_new_risk_falsification` / `deployable=false` / `risk_on_order_enabled=false` / `order_submission_enabled=false` / `baseline_win_rate=13.0%` / `best_gate=observable_4h_shift_shadow_gate` / `kept_rows=26` / `kept_win_rate=50.0%` / `loss_capture=85.1%` / `operator=僅限 paper/shadow；熔斷、support 與 venue gate 仍 fail-closed`
- **current-state docs overwrite sync 已自動化**
  - heartbeat runner 會在 `auto_propose_fixes.py` 後直接覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`
  - 這條 lane 的目的不是美化文件，而是避免 `issues.json / live artifacts` 已更新、markdown docs 卻仍停在舊 truth 的治理裂縫
- **Execution Console / `/api/trade` 操作入口已 fail-closed（同步中 + 阻塞 + 直接 API）**
  - `/api/status` 初次同步前或部署阻塞存在時，買入 / 加倉與啟用自動模式快捷操作顯示暫停並保持 disabled；減碼 / 賣出風險降低、等待 / 觀望、切到手動模式、查看阻塞原因與重新整理仍可用；`/api/status` / `/api/execution/overview` / `/api/execution/runs` 已走 20s operator-workspace timeout，避免後端並行診斷或冷啟動時 8s default 把可用 payload 誤報成 `API timeout` / `載入失敗`；後端 `POST /api/trade` 對買入 / 加倉會先讀即時部署阻塞點，阻塞時回 409 `current_live_deployment_blocker`，只保留等待 / 觀望與減倉 / 賣出風險降低路徑；`data/live_predict_probe.json` 同步輸出 `api_trade_guardrail_active / api_trade_buy_guardrail / api_trade_allowed_risk_off_sides` 作為 machine-readable proof
- **Dashboard 啟動連續性 guardrail 已納入 feature deferred truth**
  - `/api/status.feature_continuity.status=deferred` 或 `repair_deferred=true` 時，Dashboard 連續性卡改用警示色並顯示 `特徵缺口已延後到心跳維護收斂`；避免 raw continuity clean/repaired 時，把啟動期 feature 缺口誤讀成全綠。
- **Execution Status / Bot 營運 已顯示熔斷解除條件**
  - `最近 50 筆目前 13/50，還差 2 勝；當前 q35 分桶支持樣本 / 候選修補不可取代熔斷解除條件`；操作員執行介面先看熔斷解除條件，再看 當前 q35 分桶 support / 背景治理；`runtime_closure_summary` 已由 `model/runtime_closure.py` 共用中文化，避免後端 bucket / route / source / reference raw token 泄漏到 Dashboard / Strategy Lab / Execution Status / live DQ operator markdown
- **Live DQ drilldown operator-facing markdown 已 enum-safe**
  - `docs/analysis/live_decision_quality_drilldown.md` 的 operator header、support summary、精準支持路徑、跨門檻 verdict、recommended patch 來源 / 範圍改用繁中標籤；machine JSON 保留 raw enum，operator markdown 不再洩漏後端 bucket / route / source / reference raw token。
- **Strategy Lab 高信心 OOS 列級訊號 copy 已 operator-safe**
  - 列級 `signal` 透過 `formatHighConvictionRuntimeSignalLabel()` 轉成繁中操作語；即時分桶 / 支持 / release gate 未解除前，候選列維持模擬觀察 / 影子驗證 / 僅觀察，不用內部 enum 暗示可部署。
- **Execution Console 高信心 Top-K 影子觀察入口已產品化**
  - `risk_qualified_rows=6` / `runtime_blocked_candidates=6` / `deployable_rows=0` / `paper_shadow=true` / `risk_on_order_enabled=false` / `support=0/50` / `gap=50`；selective sleeve 在可部署仍為 0 時只允許 `paper_shadow`，不會送單或加倉。
- **高低震盪 / 擁塞不是停工：區間影子觀察 + 減風險劇本已產品化**
  - `support=0/50` / `gap=50` / `paper_shadow=true` / `risk_on_order_enabled=false` / `order_submission_enabled=false` / `reduce_risk_allowed=true`；只允許影子觀察、減碼 / 取消掛單與證據收集，進攻買入 / 加倉與啟用自動模式仍等即時部署門檻。
- **M5 實戰準備度總卡已產品化：Shadow Trade Ledger + Venue dry-run proof + canary gap 答案**
  - Shadow Trade Ledger 記錄訊號時間、candidate model、confidence、當時 regime、假想 entry、之後 24h 結果與是否符合 pyramid win；只做影子帳本，不送單。
  - Venue dry-run proof 顯示 credential present、order preview、ack simulation、cancel simulation、reconciliation check；credential present 只顯示布林 / 狀態，不輸出 secret。
  - UI 直接回答：目前距離 canary 還差什麼、今天可以演練什麼、哪一個 gate 卡住、如果 gate 全過，第一筆 canary 如何執行。
- **anti-equilibrium forced execution governor 已成為 current plan contract**
  - same semantic signature / support delta=0 / stagnant repeats 不能再產生 observation-only heartbeat；必須選 Venue lifecycle proof、Model shadow to decision、Strategy micro-canary readiness、Map-Signal redesign 或 hard no-go single failed gate。
  - bounded live-canary guard 已在 execution service 形成 hard gate：live buy/add 若缺 explicit `execution.live_canary` allowlist 與 symbol qty cap，adapter 前拒單；reduce/sell 風險降低路徑保留。
- **本輪 current-state docs 已同步到最新 artifacts**
  - docs 與 `issues.json / data/live_predict_probe.json / data/live_decision_quality_drilldown.json / data/q15_support_fill_feasibility.json / data/execution_metadata_smoke.json / data/leaderboard_feature_profile_probe.json / data/high_conviction_topk_oos_matrix.json` 的 current-state truth 已對齊
- **support-fill feasibility / alternative-solution gate 已納入 current plan**
  - `artifact=data/q15_support_fill_feasibility.json` / `classification=true_support_under_minimum` / `bucket=CAUTION|base_caution_regime_or_bias|q35` / `exact_rows=0/50` / `identity_rows=32` / `non_bucket_identity_rows=32` / `gap=50` / `time_to_evidence=unknown_until_exact_identity_rows_start_accumulating` / `missing_capability=Signal/Support` / `alternative_solution_required=True`；next safe artifact：data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy；reference windows / governance rows 不可包裝成 deployable support。
- **反平衡強制執行 contract**
  - 目前 same semantic signature + support delta=0 已觸發 forced branch：Venue lifecycle proof / Model shadow to decision / Strategy micro-canary readiness / Map-Signal redesign / hard no-go single failed gate；下一輪不得只輸出狀態刷新。

---

## 主目標

### 目標 A：維持熔斷解除條件作為唯一即時部署阻塞點
**目前真相**
- `deployment_blocker=circuit_breaker_active` / `streak=0` / `recent_window_wins=13/50` / `additional_recent_window_wins_needed=2`
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q35` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_unsupported_block`
- support progress：`status=semantic_rebaseline_under_minimum` / `reason=current exact support 0/50 below minimum (gap=50); legacy 0/50@1238 remains reference-only` / `regression_basis=legacy_or_different_semantic_signature` / `current_rows=0` / `minimum_rows=50` / `gap_to_minimum=50` / `support_rows_needed=50` / `previous_rows=0` / `delta_vs_previous=0` / `legacy_supported_reference=0/50@1238` / `stagnant_run_count=2` / `stalled_support_accumulation=False` / `escalate_to_blocker=True` / `governance_reference_route=no_support_proxy` / `exact_live_lane_proxy_rows=8` / `governance_reference_only=True`
**成功標準**
- `/`、`/execution`、`/execution/status`、`/lab`、probe、drilldown、docs 都把熔斷解除條件視為唯一即時部署阻塞點；`/execution` 在 `/api/status` 初次同步前也不得開放買入 / 啟用自動模式，阻塞期間只暫停買入 / 加倉與啟用自動模式，等待 / 觀望與減碼 / 賣出風險降低路徑仍可用；直接呼叫 `POST /api/trade` 的買入 / 加倉也必須依即時部署阻塞點以 409 暫停，且只保留等待 / 觀望與減倉 / 賣出風險降低路徑。
- q35 current-live bucket truth (`bucket / rows / minimum / gap / support route`) 仍在 top-level surfaces 可 machine-read。

### 目標 B：持續把 recent canonical blocker pocket 當成 current blocker 根因來鑽
**目前真相**
- `latest_window=100` / `win_rate=13.0%` / `dominant_regime=chop(53.0%)` / `avg_quality=-0.2351` / `avg_pnl=-0.0101` / `alerts=label_imbalance`
- shadow-only falsification：`mode=shadow_only_no_new_risk_falsification` / `deployable=false` / `risk_on_order_enabled=false` / `order_submission_enabled=false` / `baseline_win_rate=13.0%` / `best_gate=observable_4h_shift_shadow_gate` / `kept_rows=26` / `kept_win_rate=50.0%` / `loss_capture=85.1%` / `operator=僅限 paper/shadow；熔斷、support 與 venue gate 仍 fail-closed`
**成功標準**
- drift / probe / docs 能同時指出 latest recent-window diagnostics 與 current blocker pocket，而不是退回 generic leaderboard / venue 摘要。

### 目標 C：守住 q35 current-live bucket support truth 與 deployment closure 邊界
**目前真相**
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q35` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_unsupported_block`
- support progress：`status=semantic_rebaseline_under_minimum` / `reason=current exact support 0/50 below minimum (gap=50); legacy 0/50@1238 remains reference-only` / `regression_basis=legacy_or_different_semantic_signature` / `current_rows=0` / `minimum_rows=50` / `gap_to_minimum=50` / `support_rows_needed=50` / `previous_rows=0` / `delta_vs_previous=0` / `legacy_supported_reference=0/50@1238` / `stagnant_run_count=2` / `stalled_support_accumulation=False` / `escalate_to_blocker=True` / `governance_reference_route=no_support_proxy` / `exact_live_lane_proxy_rows=8` / `governance_reference_only=True`
- **support-fill feasibility / alternative-solution gate 已納入 current plan**
  - `artifact=data/q15_support_fill_feasibility.json` / `classification=true_support_under_minimum` / `bucket=CAUTION|base_caution_regime_or_bias|q35` / `exact_rows=0/50` / `identity_rows=32` / `non_bucket_identity_rows=32` / `gap=50` / `time_to_evidence=unknown_until_exact_identity_rows_start_accumulating` / `missing_capability=Signal/Support` / `alternative_solution_required=True`；next safe artifact：data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy；reference windows / governance rows 不可包裝成 deployable support。
- `recommended_patch=—` / `status=—` / `reference_scope=—`（本輪無 active recommended patch）
**成功標準**
- probe / drilldown / `/api/status` / `/execution/status` / `/lab` / docs 全都承認 q35 current-live bucket exact support 未達 minimum rows，recommended patch 只能作治理 / 訓練參考。

### 目標 D：維持 leaderboard、venue/source blockers 與 docs automation 一致 product truth
**目前真相**
- `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=current_full_no_bull_collapse_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split` / `payload_source=latest_persisted_snapshot` / `payload_stale=false` / `payload_age=5.5m`
- top source blockers：`fin_netflow(source_auth_blocked/auth_missing, coverage=0.0%, archive_window=0.0%, forward_archive=ready, next=configure [REDACTED] source credentials)` / `claw(source_auth_blocked/auth_missing, coverage=14.2%, archive_window=76.5%, forward_archive=ready, next=configure [REDACTED] source credentials)` / `claw_intensity(source_auth_blocked/auth_missing, coverage=14.2%, archive_window=76.5%, forward_archive=ready, next=configure [REDACTED] source credentials)` / `nest_pred(source_tls_verify_failed/tls_verify_failed, coverage=15.8%, archive_window=85.0%, forward_archive=ready)`
- fin_netflow：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=4640` / `archive_window_coverage_pct=0.0`
- venue blockers：`generated_at=2026-05-23T22:11:30.434524Z` / `venues_checked=2` / `ok_count=1` / `runtime_ready_count=0` / `runtime_ready=false` / `readiness_state=blocked_until_runtime_lifecycle_proof` / `runtime_ready_blockers=fill lifecycle 尚未驗證|live exchange credential 尚未驗證|order ack lifecycle 尚未驗證|元資料契約尚未通過|場館 adapter 尚未接入`；`okx=adapter_supported=true,enabled_in_config=true,credentials_configured=false,proof_state=public_metadata_only,runtime_ready=false,blockers=live exchange credential 尚未驗證|order ack lifecycle 尚未驗證|fill lifecycle 尚未驗證` / `binance=adapter_supported=false,enabled_in_config=false,credentials_configured=false,proof_state=adapter_unsupported,runtime_ready=false,blockers=場館 adapter 尚未接入|元資料契約尚未通過|場館設定停用`；metadata smoke venue rows 已帶 adapter_supported / enabled_in_config / credentials_configured / proof_state / runtime_ready / blockers / operator_next_action / verify_next；runtime_ready=true 且 blockers 清空前仍禁止 canary/live-ready 文案
- docs automation：markdown docs 不再允許落後 live artifacts
**成功標準**
- Strategy Lab 不回退 placeholder-only；venue/source blockers 在 operator-facing surfaces 維持可見；docs automation 每輪心跳都自動完成 overwrite sync。

### 目標 E：建立 high-conviction top-k OOS ROI gate，把研究結論轉成實戰部署門檻
**目前真相**
- 六色帽會議與研究交叉分析已收斂：下一步不是增加交易頻率，而是用 walk-forward OOS / top-k precision / ROI / max drawdown / meta-labeling / uncertainty gate 決定是否允許 candidate 進入部署候選。
- 最新 matrix artifact 已產出：`artifact=data/high_conviction_topk_oos_matrix.json` / `generated_at=2026-05-23T22:11:15.619804+00:00` / `freshness=fresh` / `age_min=0.3` / `stale_after_min=60` / `deployment_blocking=False` / `samples=25051` / `rows=24` / `deployable_rows=0` / `risk_qualified_rows=6` / `runtime_blocked_candidates=6` / `support_route=exact_bucket_unsupported_block` / `deployment_blocker=circuit_breaker_active` / `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q35` / `current_live_structure_bucket_rows=0/50` / `current_live_structure_bucket_gap_to_minimum=50` / `release_ready=False` / `recent_window_wins=13/50` / `required_recent_window_wins=15` / `additional_recent_window_wins_needed=2` / `current_recent_window_win_rate=0.260` / `support_progress_status=semantic_rebaseline_under_minimum` /
  `support_progress_reason=current exact support 0/50 below minimum (gap=50); semantic mismatch=calibration_window,entry_quality_label,regime_label` / `regression_basis=legacy_or_different_semantic_signature` / `delta_vs_previous=0` / `previous_rows=0` / `support_rows_needed=50` / `stagnant_run_count=2` / `stalled_support_accumulation=False` / `escalate_to_blocker=True`。
- 最接近部署候選優先：`model=logistic_regression` / `regime=all` / `top_k=top_2pct` / `oos_roi=0.9324` / `win_rate=0.8621` / `profit_factor=19.8864` / `max_drawdown=0.022` / `worst_fold=0.2068` / `trades=58` / `tier=runtime_blocked_oos_pass` / `verdict=not_deployable` / `support_route=exact_bucket_unsupported_block` / `governance=no_support_proxy` / `bucket=CAUTION|base_caution_regime_or_bias|q35` / `bucket_rows=0/50` / `gap=50` / `release_ready=False` / `recent_window_wins=13/50` / `required_recent_window_wins=15` / `additional_recent_window_wins_needed=2` / `current_recent_window_win_rate=0.260` / `support_progress_status=semantic_rebaseline_under_minimum` / `support_progress_reason=current exact support 0/50 below minimum (gap=50); semantic mismatch=calibration_window,entry_quality_label,regime_label` / `regression_basis=legacy_or_different_semantic_signature` / `delta_vs_previous=0` /
  `previous_rows=0` / `support_rows_needed=50` / `stagnant_run_count=2` / `stalled_support_accumulation=False` / `escalate_to_blocker=True`；若只剩即時分桶 / 支持 / release gate，仍模擬觀察 / 影子驗證 / 僅觀察。
**成功標準**
- `data/high_conviction_topk_oos_matrix.json` 必須持續輸出 `generated_at / artifact_freshness_status / artifact_age_minutes / artifact_stale_after_minutes / artifact_deployment_blocking / model / feature_profile / regime / top_k / OOS ROI / win_rate / profit_factor / max_drawdown / worst_fold / trade_count / support_route / support_governance_route / deployment_blocker / runtime_closure_state / current_live_structure_bucket / current_live_structure_bucket_rows / minimum_support_rows / current_live_structure_bucket_gap_to_minimum / release_ready / current_recent_window_wins / required_recent_window_wins / additional_recent_window_wins_needed / deployable_verdict / gate_failures / model_gate_failures / live_gate_failures / deployment_candidate_tier`。
- `/api/models/leaderboard` 與 Strategy Lab 高信心 OOS Top-K 部署門檻面板以最接近部署候選優先排序：先看離線驗證 / 風控門檻、低回撤、最差分折，再看 ROI；若候選只剩矩陣新鮮度 / 即時分桶 / 支持 / breaker release 條件 / 場館 proof 未過，仍 fail-closed 到模擬觀察 / 影子驗證 / 僅觀察，並顯示矩陣新鮮度、支持狀態、治理路徑、部署阻塞、即時分桶與樣本數，外加 release math。

---

## 下一輪 gate
1. **維持熔斷優先真相 + q35 current-live bucket visibility across API / UI / docs**
   - 驗證：browser `/`、browser `/execution`（含初次同步時買入 / 啟用自動模式暫停、等待 / 觀望與減碼可用）、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、`python -m pytest tests/test_server_startup.py -k api_trade -q`
   - 升級 blocker：若熔斷解除條件被 support / floor-gap / venue 話題覆蓋，或 q35 current-live bucket rows 再次從 top-level surfaces 消失
2. **持續鑽 recent canonical pathological slice，而不是 generic 化 root cause**
   - 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`
   - 升級 blocker：若 drift artifact 再失去 target-path / adverse-streak / top-shift 證據
3. **守住 q35 current-live bucket support truth / blocker truth、leaderboard governance、venue/source blockers 與 docs automation 閉環**
   - 驗證：browser `/lab`、`curl http://127.0.0.1:<active-backend>/api/models/leaderboard`（依 `/health` 選 8000/8001 健康 lane，不要硬綁單一 port）、`data/q15_support_audit.json`、`data/execution_metadata_smoke.json`、下輪 heartbeat docs sync status
   - 升級 blocker：若 support closure 被誤讀成 deployment closure、排行榜 drift 成 placeholder-only、venue/source blocker 消失、或 docs 再次落後 latest artifacts
4. **依 PM handoff 追 exact support-fill movement 與 alternative-solution proof**
   - 驗證：`python scripts/q15_support_fill_feasibility_scan.py`、`python scripts/customer_safe_alternative_proof.py`、`data/q15_support_fill_feasibility.json`、`data/customer_safe_alternative_proof.json`、`docs/analysis/q15_support_fill_feasibility.md`、`docs/analysis/customer_safe_alternative_proof.md`、`ISSUES.md / ROADMAP.md / ORID_DECISIONS.md` 是否同步 exact bucket rows / identity rows / missing capability / alternative solution
   - 升級 blocker：若 exact bucket rows 仍低於門檻卻沒有 missing_capability / time_to_evidence / alternative_solution artifact，或 identity/proxy/reference rows 被包裝成 deployable。
5. **反平衡 forced-execution gate：same semantic signature + support delta=0 不得再回到 observation-only**
   - 驗證：`docs/plans/2026-05-23-live-canary-structural-pivot.md`、`data/live_canary_structural_pivot.json`、`python -m pytest tests/test_execution_service.py -k live_canary -q`、`ISSUES.md / ROADMAP.md / ORID_DECISIONS.md` forced branch
   - 升級 blocker：若 72h 內沒有 bounded micro-canary policy proof 或 single failed gate，或下一輪 heartbeat 只重述 wait/support gap
6. **建立 high-conviction top-k OOS ROI gate，讓 Strategy Lab winner 先經研究→模擬觀察→影子驗證→小流量分級**
   - 驗證：`data/high_conviction_topk_oos_matrix.json`、`/api/models/leaderboard.high_conviction_topk`、Strategy Lab 高信心 OOS Top-K 部署門檻面板、`python -m pytest tests/test_model_leaderboard.py tests/test_frontend_decision_contract.py -k high_conviction -q`
   - 升級 blocker：若 scan winner 未經 OOS top-k / minimum support / drawdown / breaker release gate 就被標成 deployable，或 current-live unsupported 時仍允許 buy/add exposure

---

## 成功標準
- 即時部署阻塞點清楚且唯一：**熔斷解除條件**
- current live bucket support truth 維持：**0/50 + exact_bucket_unsupported_block + —**
- recent canonical diagnostics 與 current blocker pocket 需同步可見，不被 generic 問題稀釋
- support-fill feasibility 維持 PM-safe：current exact bucket rows、identity rows、missing capability、time-to-evidence、alternative-solution artifact 可見，且 identity/proxy/reference rows 不可升級成 deployable truth
- anti-equilibrium forced execution 維持：same semantic signature + support delta=0 觸發 forced branch；bounded live-canary policy / single failed gate 必須 machine-readable，禁止 observation-only heartbeat
- leaderboard dual-role governance 維持；venue/source blockers 持續可見
- heartbeat runner 每輪自動完成：**issue 對齊 → patch/automation lane → verify artifacts → docs overwrite sync**
- `/api/trade` 直接 API 不能繞過即時部署阻塞點：買入 / 加倉在 no-deploy 狀態必須 409，減倉 / 賣出仍可用
