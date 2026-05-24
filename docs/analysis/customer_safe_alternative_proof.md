# Customer-safe alternative proof

- generated_at: `2026-05-24T19:11:34.488774Z`
- current_live_blocker: `unsupported_exact_live_structure_bucket`
- current_live_structure_bucket: `CAUTION|base_caution_regime_or_bias|q35`
- exact support: `0/50` (gap `50`)
- support_route_verdict: `exact_bucket_unsupported_block`
- circuit_breaker_release_ready: `True` (wins `50/15`, gap `0`)
- primary_blocking_gate: `current_live_support_gate`
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
  - 展示 Strategy Lab / Execution Console 的高信心 OOS 候選，但標示 deployable=false
  - 做 venue dry-run preview / ack simulation / cancel simulation / reconciliation checklist
  - 保留等待 / 觀望、減碼 / 取消掛單 / 賣出風險降低路徑

## Not allowed
- 買入 / 加倉
- 啟用風險進攻自動下單或完整實單自動化
- 把 exact-live-lane proxy、reference windows、OOS pass、paper/shadow 或 dry-run 證據包裝成 live deployment closure
- 輸出 credential / API key / secret 值；只能顯示 boolean 或 [REDACTED]

## Lanes
- `paper_shadow_decision_support_sleeve`: status=`available`, deployable=`False`, live_exposure_allowed=`False`
- `venue_dry_run_readiness_proof`: status=`blocked_missing_runtime_backed_proof`, deployable=`False`, live_exposure_allowed=`False`
- `support_fill_feasibility`: status=`semantic_window_gap_not_raw_backfill_gap`, deployable=`False`, live_exposure_allowed=`False`
- `recent_window_no_new_risk_falsification`: status=`shadow_only_no_new_risk_falsification`, deployable=`False`, live_exposure_allowed=`False`, best_gate=`observable_4h_shift_shadow_gate`, kept=`78`, kept_win_rate=`1.0`, loss_capture=`1.0`

## Alternative solution option portfolio
- option_count: `3`
- selected_next_artifact: `data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy`
- time_to_evidence_bucket: `semantic_rebaseline_review_required_before_reference_rows_count`
- safety_invariant: All alternatives are customer-safe only: deployable=false, live_exposure_allowed=false, order_submission_enabled=false until exact support, Top-K deployability, and venue runtime proof all pass.
- `paper_shadow_decision_support_sleeve`: role=`customer_usable_now`, deployable=`False`, live_exposure_allowed=`False`, next=`data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy`
- `semantic_rebaseline_review`: role=`support_policy_alternative`, deployable=`False`, live_exposure_allowed=`False`, next=`OOS + Top-K + support audit replay under any proposed new calibration_window identity`
- `venue_dry_run_readiness_proof`: role=`delivery_risk_reduction`, deployable=`False`, live_exposure_allowed=`False`, next=`OKX/Binance dry-run lifecycle proof checklist with credential state as boolean only`

## Next gate
circuit_breaker release_ready=True，current exact support rows 0/50 必須補齊；同時 Top-K deployable_rows>0、venue runtime lifecycle proof complete，才允許最小 canary review。

