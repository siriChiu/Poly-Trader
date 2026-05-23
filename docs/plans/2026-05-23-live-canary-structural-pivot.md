# Live canary structural pivot

- generated_at: `2026-05-23T19:14:23.512603Z`
- PM handoff carried forward: `PM 強制反平衡：若 72h 內不能執行 bounded micro-canary，必須寫明單一失敗 gate 與下一個驗證 artifact；不得再只做 observation-only heartbeat。`
- deployment_blocker: `circuit_breaker_active`
- current bucket: `BLOCK|bear_bias200_hard_block|q15`
- support: `0/50` (gap `50`, delta `0`, stagnant `5`)
- semantic-signature progress: delta `0`, stagnant `5` (does not relax strict support_identity)
- release_ready: `False` / recent wins `6/50`, required `15`, needed `9`
- venue_runtime_ready: `False` / OKX credentials configured: `False`
- top-k: risk-qualified `6`, runtime-blocked `6`, deployable `0`
- local execution mode: `paper` / live_canary_policy_ready: `False`
- micro_canary_ready: **False** / order_submission_enabled: **False**
- single_failed_gate_for_72h_decision: `current_live_support_gate`
- next_validation_artifact: `data/q15_support_fill_feasibility.json + data/live_predict_probe.json after Map/Signal redesign or exact-bucket row harvest`

## Decision
停止重複 observation-only。每輪刷新 live-canary pivot，將 readiness 拆成 support、breaker、model-shadow、venue lifecycle、live-canary policy 五個 gate。

## Why this is not observation-only
本 artifact 由 fresh runtime artifacts 重新生成，保留數字零值（例如 support_rows=0、deployable_rows=0），並把 72h 決策壓成一個主要失敗 gate；其餘 gate 只列為補充 blocker，不拿來稀釋責任。

## Gates
- `current_live_support_gate`: ready=`False`, reason=current-live exact support must reach the minimum with matching support_identity.
- `circuit_breaker_gate`: ready=`False`, reason=recent canonical 24h outcomes must clear streak and win-rate release math.
- `model_shadow_outcome_gate`: ready=`False`, reason=OOS pass / paper-shadow rows are not live deployability until deployable_rows>0 under current gates.
- `venue_lifecycle_gate`: ready=`False`, reason=exchange credential boolean plus ack/fill/cancel/reconciliation proof must be runtime-backed.
- `live_canary_policy_gate`: ready=`False`, reason=local config must opt into explicit live_canary with symbol cap before adapter order submission.

## Supplementary blockers
`circuit_breaker_gate`, `model_shadow_outcome_gate`, `venue_lifecycle_gate`, `live_canary_policy_gate`

## Lanes
- `A_venue_lifecycle_proof`: status=`blocked_missing_runtime_backed_proof`, can_start_now=`True`, live_exposure=`none_or_min_exchange_probe_only`
- `B_model_shadow_to_decision`: status=`paper_shadow_available`, can_start_now=`True`, live_exposure=`paper_shadow_only`
- `C_strategy_micro_canary`: status=`blocked_by_current_live_support_gate`, can_start_now=`False`, live_exposure=`max one first-layer position, tiny symbol cap, no auto-add, no pyramiding until post-trade proof is clean`
- `D_map_signal_redesign_for_current_bucket`: status=`required`, can_start_now=`True`, live_exposure=`none`

## Local config snapshot (secret-safe)
- config: `config.yaml` exists=`True`
- execution_mode: `paper`
- enable_live_trading: `False`
- live_canary_enabled: `False`
- allowed_symbols_configured: `False`
- max_base_qty_by_symbol_configured: `False`
- credential_values_redacted: `True`

## 72h sequence
1. T+0h: Keep buy/add fail-closed; refresh this pivot from artifacts and name the single failed gate.
2. T+4h: If primary gate is venue, produce OKX runtime lifecycle proof; if credentials are missing, credential boolean remains false and secrets stay redacted.
3. T+24h: Run/select Shadow Trade Ledger sleeve for the nearest Top-K candidate and collect 24h pyramid outcome without order submission.
4. T+48h: If the single failed gate is support, produce Map/Signal redesign or exact-bucket support-harvest proof instead of another passive status refresh.
5. T+72h: Either execute one bounded micro-canary after all gates pass, or record hard no-go with this artifact's single_failed_gate_for_72h_decision.

## Hard no-go now
micro_canary_ready=`False`, live_exposure_allowed=`False`, order_submission_enabled=`False`.
primary_failed_gate=current_live_support_gate; next_validation_artifact=data/q15_support_fill_feasibility.json + data/live_predict_probe.json after Map/Signal redesign or exact-bucket row harvest
