# No-Trade Lane Replay

_Generated at: `2026-07-28T18:29:28.867935Z`_

## Decision
- verdict: `not_applicable_or_incomplete_no_trade_replay` / validated: `False`
- deployable: `False` / risk_on_order_enabled: `False` / order_submission_enabled: `False`
- support evidence role: `deployment_support_identity_required`
- buy/add support closure allowed: `False`
- operator summary: 當前 BLOCK / 不交易 lane 的 replay 結論是等待 / 觀望、減風險與 paper-shadow 可用；這份 artifact 不能作為買入 / 加倉 support closure。

## Current Lane
- signal: `CIRCUIT_BREAKER` / should_trade: `False` / deployment_blocker: `circuit_breaker_active`
- bucket: `CAUTION|structure_quality_caution|q15` / actionability: `risk_on_candidate_lane`
- support: `10/50` / gap: `40` / route: `exact_bucket_present_but_below_minimum`
- allowed actions: `wait, reduce, sell, shadow_buy, paper_buy, diagnostics, mode_toggle`
- risk-off sides: `reduce, sell` / paper-shadow sides: `shadow_buy, paper_buy`

## Replay Evidence
- abstain path validated: `False`
- reduce-only path validated: `True`
- paper-shadow path validated: `True`
- recent drift mode: `shadow_only_no_new_risk_falsification` / deployment verdict: `not_deployable_shadow_only_runtime_blocked`
- recent window: `250` / win_rate: `50.8%` / dominant_regime: `chop`
- best shadow gate: `dominant_regime_shadow_gate` / verdict: `fails_shadow_metric` / kept_win_rate: `100.0%`

## Machine Checks
- `current_lane_is_no_trade_block_lane`: `False`
- `should_trade_false`: `True`
- `allowed_layers_zero`: `True`
- `drift_replay_shadow_only`: `True`
- `risk_off_paths_visible`: `True`
- `paper_shadow_paths_visible`: `True`
- `support_evidence_not_deployable`: `False`
- `buy_add_support_closure_allowed`: `False`
- `risk_on_order_enabled`: `False`
- `order_submission_enabled`: `False`
- `live_exposure_allowed`: `False`
- `all_passed`: `False`
