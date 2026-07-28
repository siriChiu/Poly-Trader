# Customer-safe alternative proof

- generated_at: `2026-07-28T14:46:49.363683Z`
- current_live_blocker: `circuit_breaker_active`
- current_live_structure_bucket: `BLOCK|structure_quality_block|q00`
- exact support: `0/50` (gap `50`)
- support_route_verdict: `exact_bucket_unsupported_block`
- circuit_breaker_release_ready: `False` (wins `13/15`, gap `2`)
- primary_blocking_gate: `circuit_breaker_gate`
- canary_ready: **False**
- live_exposure_allowed: **False**
- order_submission_enabled: **False**

## PM handoff carried forward
維持 current-live exact-support blocker；若 exact rows 仍不足，交付 paper/shadow、dry-run、falsification 與 support-fill proof，不降低 live gate。

## Customer-safe lane available today
- Top-K risk-qualified rows: `0`
- Runtime-blocked candidates: `0`
- Deployable rows: `0`
- Top-K support overlay: status=`fresh_live_probe_overlay` / freshness=`fresh` / blocking=`False` / reason=`—`
- 最近研究候選：`logistic_regression` / `top_1pct` / OOS ROI=0.2465 / 勝率=0.6897 / profit factor=4.3797 / 最大回撤=0.0478 / 最差 fold=0.0994 / 交易數=29 / 候選層級=research_oos_gate_failed / 部署判定=不可部署 / 僅允許 paper-shadow，直到 live gates 全部通過
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
- `review_strategy_lab_topk_shadow_candidates`: surface=`/lab`, mode=`research_to_shadow`, live_exposure_allowed=`False`, next=data/high_conviction_topk_oos_matrix.json deployable_rows=0 until live gates pass; support_context_freshness_status=fresh
- `verify_venue_dry_run_lifecycle`: surface=`/execution/status`, mode=`venue_dry_run`, live_exposure_allowed=`False`, next=data/venue_dry_run_proof.json remains secret-safe and fail-closed until runtime proof passes.
- `track_breaker_and_exact_support`: surface=`artifacts`, mode=`gate_tracking`, live_exposure_allowed=`False`, next=data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy

## Blocked live lanes
- `live_buy_add_exposure`: blocked_actions=`live_buy, live_add, live_canary_buy`, gate=`circuit_breaker_gate`, support=`0/50`, breaker_wins=`13/15`, order_submission_enabled=`False`
- `risk_on_automation_enable`: blocked_actions=`automation_enable, risk_on_auto_ordering`, gate=`circuit_breaker_gate`, support=`0/50`, breaker_wins=`13/15`, order_submission_enabled=`False`
- `unbounded_live_canary`: blocked_actions=`unbounded_live_canary, uncapped_live_order`, gate=`circuit_breaker_gate`, support=`0/50`, breaker_wins=`13/15`, order_submission_enabled=`False`

## Recent-tail no-new-risk context
- window: `250` / win_rate=`0.508` / dominant_regime=盤整 share=`0.828`
- severity=高風險 / interpretation=單一市場狀態過度集中 / alerts=市場狀態切換
- avg_quality: `0.1327` / avg_pnl=`-0.001` / avg_drawdown_penalty=`0.1731`
- tail_streak: target=`0` count=`35` start=`2026-07-26 21:26:22.441129` end=`2026-07-27 15:12:07.304716`
- top_shift_features: 4h rsi14、4h macd hist、4h ma order、4h vol ratio、tunnel distance
- shadow_falsification: mode=只限影子驗證；不可送單 / best_gate=4H 可觀測位移影子 gate / deployable=`False` / order_submission_enabled=`False`
- actionable_summary: 近期負向分布病態，需要用現行視窗再驗證

## Lanes
- `paper_shadow_decision_support_sleeve`: status=可用（customer-safe）, deployable=`False`, live_exposure_allowed=`False`
- `venue_dry_run_readiness_proof`: status=缺少 runtime-backed proof, deployable=`False`, live_exposure_allowed=`False`
- `support_fill_feasibility`: status=true support under minimum, deployable=`False`, live_exposure_allowed=`False`
- `recent_window_no_new_risk_falsification`: status=只限影子驗證；不可送單, deployable=`False`, live_exposure_allowed=`False`, best_gate=4H 可觀測位移影子 gate, kept=`65`, kept_win_rate=`0.9538`, loss_capture=`0.9189`

## Alternative solution option portfolio
- option_count: `3`
- selected_next_artifact: `data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy`
- time_to_evidence_bucket: `unknown_until_exact_identity_rows_start_accumulating`
- safety_invariant: All alternatives are customer-safe only: deployable=false, live_exposure_allowed=false, order_submission_enabled=false until exact support, Top-K deployability, and venue runtime proof all pass.
- `paper_shadow_decision_support_sleeve`: role=`customer_usable_now`, deployable=`False`, live_exposure_allowed=`False`, next=`data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy`
- `semantic_rebaseline_review`: role=`support_policy_alternative`, deployable=`False`, live_exposure_allowed=`False`, next=`OOS + Top-K + support audit replay under any proposed new calibration_window identity`
- `venue_dry_run_readiness_proof`: role=`delivery_risk_reduction`, deployable=`False`, live_exposure_allowed=`False`, next=`OKX/Binance dry-run lifecycle proof checklist with credential state as boolean only`

## Next gate
circuit_breaker release_ready=False，current exact support rows 0/50 必須補齊；同時 Top-K deployable_rows>0、venue runtime lifecycle proof complete，才允許最小 canary review。

