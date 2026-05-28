# Customer-safe alternative proof

- generated_at: `2026-05-28T04:03:18.601803Z`
- current_live_blocker: `circuit_breaker_active`
- current_live_structure_bucket: `BLOCK|bear_bias200_hard_block|q00`
- exact support: `8/50` (gap `42`)
- support_route_verdict: `exact_bucket_present_but_below_minimum`
- circuit_breaker_release_ready: `False` (wins `0/15`, gap `15`)
- primary_blocking_gate: `circuit_breaker_gate`
- canary_ready: **False**
- live_exposure_allowed: **False**
- order_submission_enabled: **False**

## PM handoff carried forward
維持 current-live exact-support blocker；若 exact rows 仍不足，交付 paper/shadow、dry-run、falsification 與 support-fill proof，不降低 live gate。

## Customer-safe lane available today
- Top-K risk-qualified rows: `6`
- Runtime-blocked candidates: `6`
- Deployable rows: `0`
- 最近研究候選：`logistic_regression` / `top_2pct` / OOS ROI=0.9324 / 勝率=0.8621 / profit factor=19.8864 / 最大回撤=0.022 / 最差 fold=0.2068 / 交易數=58 / 候選層級=OOS 已過、即時 gate 阻塞（paper-shadow only） / 部署判定=不可部署 / 僅允許 paper-shadow，直到 live gates 全部通過
- Venue runtime_ready: `False` / `blocked_until_runtime_lifecycle_proof`
- Allowed today:
  - 啟動 paper-shadow 訊號帳本並追蹤 24h pyramid outcome
  - 透過 /api/trade shadow_buy / paper_buy 強制 dry-run，產出 paper/shadow 委託演練證據且不送 live order
  - 展示 Strategy Lab / Execution Console 的高信心 OOS 候選，但標示 deployable=false
  - 做 venue dry-run preview / ack simulation / cancel simulation / reconciliation checklist
  - 保留等待 / 觀望、減碼 / 取消掛單 / 賣出風險降低路徑

## Not allowed
- 真實/live 買入 / 加倉
- 啟用風險進攻自動下單或完整實單自動化
- 把 exact-live-lane proxy、reference windows、OOS pass、paper/shadow 或 dry-run 證據包裝成 live deployment closure
- 輸出 credential / API key / secret 值；只能顯示 boolean 或 [REDACTED]

## Recent-tail no-new-risk context
- window: `100` / win_rate=`0.0` / dominant_regime=盤整 share=`0.56`
- severity=高風險 / interpretation=近期目標單邊失敗／分布病態 / alerts=近期目標全為同一結果
- avg_quality: `-0.3179` / avg_pnl=`-0.0135` / avg_drawdown_penalty=`0.3261`
- tail_streak: target=`0` count=`100` start=`2026-05-25 20:00:00.000000` end=`2026-05-27 05:00:00.000000`
- top_shift_features: 局部頂部分數、局部底部分數、價格距離感測、RSI14、布林 %B
- shadow_falsification: mode=只限影子驗證；不可送單 / best_gate=4H 可觀測位移影子 gate / deployable=`False` / order_submission_enabled=`False`
- actionable_summary: 近期負向分布病態，需要用現行視窗再驗證

## Lanes
- `paper_shadow_decision_support_sleeve`: status=可用（customer-safe）, deployable=`False`, live_exposure_allowed=`False`
- `venue_dry_run_readiness_proof`: status=缺少 runtime-backed proof, deployable=`False`, live_exposure_allowed=`False`
- `support_fill_feasibility`: status=語義視窗缺口，不是 raw backfill 缺口, deployable=`False`, live_exposure_allowed=`False`
- `recent_window_no_new_risk_falsification`: status=只限影子驗證；不可送單, deployable=`False`, live_exposure_allowed=`False`, best_gate=4H 可觀測位移影子 gate, kept=`26`, kept_win_rate=`0.0`, loss_capture=`0.74`

## Alternative solution option portfolio
- option_count: `3`
- selected_next_artifact: `data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy`
- time_to_evidence_bucket: `semantic_rebaseline_review_required_before_reference_rows_count`
- safety_invariant: All alternatives are customer-safe only: deployable=false, live_exposure_allowed=false, order_submission_enabled=false until exact support, Top-K deployability, and venue runtime proof all pass.
- `paper_shadow_decision_support_sleeve`: role=`customer_usable_now`, deployable=`False`, live_exposure_allowed=`False`, next=`data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy`
- `semantic_rebaseline_review`: role=`support_policy_alternative`, deployable=`False`, live_exposure_allowed=`False`, next=`OOS + Top-K + support audit replay under any proposed new calibration_window identity`
- `venue_dry_run_readiness_proof`: role=`delivery_risk_reduction`, deployable=`False`, live_exposure_allowed=`False`, next=`OKX/Binance dry-run lifecycle proof checklist with credential state as boolean only`

## Next gate
circuit_breaker release_ready=False，current exact support rows 8/50 必須補齊；同時 Top-K deployable_rows>0、venue runtime lifecycle proof complete，才允許最小 canary review。

