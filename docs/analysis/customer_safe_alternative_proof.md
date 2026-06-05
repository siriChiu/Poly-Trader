# Customer-safe alternative proof

- generated_at: `2026-06-05T14:00:41.175580Z`
- current_live_blocker: `exact_live_lane_toxic_sub_bucket_current_bucket`
- current_live_structure_bucket: `BLOCK|bias200_below_min|q00`
- exact support: `131/50` (gap `0`)
- support_route_verdict: `exact_bucket_supported`
- circuit_breaker_release_ready: `True` (wins `20/15`, gap `0`)
- primary_blocking_gate: `model_gate`
- canary_ready: **False**
- live_exposure_allowed: **False**
- order_submission_enabled: **False**

## PM handoff carried forward
承接 PM handoff：不降低 live gate；fresh runtime 已證明 current exact support 達標，本輪轉往 Top-K/model gate 與 venue runtime proof，同時維持 paper/shadow、dry-run、falsification proof。

## Customer-safe lane available today
- Top-K risk-qualified rows: `6`
- Runtime-blocked candidates: `6`
- Deployable rows: `0`
- Top-K support overlay: status=`stale_live_probe_shadow_only` / freshness=`stale` / blocking=`True` / reason=`artifact_older_than_policy`
- 最近研究候選：`logistic_regression` / `top_2pct` / OOS ROI=0.9324 / 勝率=0.8621 / profit factor=19.8864 / 最大回撤=0.022 / 最差 fold=0.2068 / 交易數=58 / 候選層級=OOS 已過、即時 gate 阻塞（paper-shadow only） / 部署判定=不可部署 / 僅允許 paper-shadow，直到 live gates 全部通過
- Venue runtime_ready: `False` / `blocked_missing_runtime_backed_proof` / artifact=`venue_dry_run_proof` status=`blocked_missing_runtime_backed_proof`
- Allowed today:
  - 啟動 paper-shadow 訊號帳本並追蹤 24h pyramid outcome
  - 透過 /api/trade shadow_buy / paper_buy 強制 dry-run，產出 paper/shadow 委託演練證據且不送 live order
  - 展示 Strategy Lab / Execution Console 的高信心 OOS 候選，但標示 deployable=false
  - 做 venue dry-run preview / ack simulation / cancel simulation / fill simulation / reconciliation checklist
  - 保留等待 / 觀望、減碼 / 取消掛單 / 賣出風險降低路徑

## Not allowed
- 真實/live 買入 / 加倉
- 啟用風險進攻自動下單或完整實單自動化
- 把 exact-live-lane proxy、reference windows、OOS pass、paper/shadow 或 dry-run 證據包裝成 live deployment closure
- 輸出 credential / API key / secret 值；只能顯示 boolean 或 [REDACTED]

## Next customer actions
- `open_execution_paper_shadow`: surface=`/execution`, mode=`paper_shadow`, live_exposure_allowed=`False`, next=data/paper_shadow_outcome_reconciliation.json pending/resolved outcome proof；live_order_submitted=false。
- `review_strategy_lab_topk_shadow_candidates`: surface=`/lab`, mode=`research_to_shadow`, live_exposure_allowed=`False`, next=data/high_conviction_topk_oos_matrix.json deployable_rows=0 until live gates pass; support_context_freshness_status=stale
- `verify_venue_dry_run_lifecycle`: surface=`/execution/status`, mode=`venue_dry_run`, live_exposure_allowed=`False`, next=data/venue_dry_run_proof.json remains secret-safe and fail-closed until runtime proof passes.
- `track_breaker_and_exact_support`: surface=`artifacts`, mode=`gate_tracking`, live_exposure_allowed=`False`, next=data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy

## Blocked live lanes
- `live_buy_add_exposure`: blocked_actions=`live_buy, live_add, live_canary_buy`, gate=`model_gate`, support=`131/50`, breaker_wins=`20/15`, order_submission_enabled=`False`
- `risk_on_automation_enable`: blocked_actions=`automation_enable, risk_on_auto_ordering`, gate=`model_gate`, support=`131/50`, breaker_wins=`20/15`, order_submission_enabled=`False`
- `unbounded_live_canary`: blocked_actions=`unbounded_live_canary, uncapped_live_order`, gate=`model_gate`, support=`131/50`, breaker_wins=`20/15`, order_submission_enabled=`False`

## Recent-tail no-new-risk context
- window: `100` / win_rate=`0.21` / dominant_regime=空頭 share=`0.94`
- severity=高風險 / interpretation=單一市場狀態過度集中 / alerts=單一市場狀態過度集中、市場狀態切換
- avg_quality: `-0.1998` / avg_pnl=`-0.0106` / avg_drawdown_penalty=`0.4769`
- tail_streak: target=`0` count=`2` start=`2026-06-04 03:00:00.000000` end=`2026-06-04 04:00:00.000000`
- top_shift_features: dist swing high、atr pct、nq return 24h、turning point score、tunnel distance
- shadow_falsification: mode=只限影子驗證；不可送單 / best_gate=主導市場狀態影子 gate / deployable=`False` / order_submission_enabled=`False`
- actionable_summary: 近期負向分布病態，需要用現行視窗再驗證

## Lanes
- `paper_shadow_decision_support_sleeve`: status=可用（customer-safe）, deployable=`False`, live_exposure_allowed=`False`
- `venue_dry_run_readiness_proof`: status=缺少 runtime-backed proof, deployable=`False`, live_exposure_allowed=`False`
- `support_fill_feasibility`: status=current identity support ready, deployable=`False`, live_exposure_allowed=`False`
- `recent_window_no_new_risk_falsification`: status=只限影子驗證；不可送單, deployable=`False`, live_exposure_allowed=`False`, best_gate=主導市場狀態影子 gate, kept=`6`, kept_win_rate=`0.0`, loss_capture=`0.9241`

## Alternative solution option portfolio
- option_count: `3`
- selected_next_artifact: `data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy`
- time_to_evidence_bucket: `ready_for_remaining_live_execution_gates`
- safety_invariant: All alternatives are customer-safe only: deployable=false, live_exposure_allowed=false, order_submission_enabled=false until exact support, Top-K deployability, and venue runtime proof all pass.
- `paper_shadow_decision_support_sleeve`: role=`customer_usable_now`, deployable=`False`, live_exposure_allowed=`False`, next=`data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy`
- `semantic_rebaseline_review`: role=`support_policy_alternative`, deployable=`False`, live_exposure_allowed=`False`, next=`OOS + Top-K + support audit replay under any proposed new calibration_window identity`
- `venue_dry_run_readiness_proof`: role=`delivery_risk_reduction`, deployable=`False`, live_exposure_allowed=`False`, next=`OKX/Binance dry-run lifecycle proof checklist with credential state as boolean only`

## Next gate
current exact support 已達標；Top-K deployable_rows>0、venue runtime lifecycle proof complete，且 circuit_breaker release_ready=true 後，才可考慮 live exposure。

