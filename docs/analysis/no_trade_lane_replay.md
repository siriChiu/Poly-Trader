# No-Trade Lane Replay

_Generated at: `2026-06-05T10:52:40.138706Z`_

## Decision
- verdict: `validated_abstain_reduce_only_no_trade_lane` / validated: `True`
- deployable: `False` / risk_on_order_enabled: `False` / order_submission_enabled: `False`
- support evidence role: `no_trade_decision_validation_not_deployable_support`
- buy/add support closure allowed: `False`
- operator summary: 當前 BLOCK / 不交易 lane 的 replay 結論是等待 / 觀望、減風險與 paper-shadow 可用；這份 artifact 不能作為買入 / 加倉 support closure。

## Current Lane
- signal: `HOLD` / should_trade: `False` / deployment_blocker: `exact_live_lane_toxic_sub_bucket_current_bucket`
- bucket: `BLOCK|bias200_below_min|q00` / actionability: `no_trade_block_lane`
- support: `131/50` / gap: `0` / route: `exact_bucket_supported`
- allowed actions: `wait, reduce, sell, shadow_buy, paper_buy, diagnostics, mode_toggle`
- risk-off sides: `reduce, sell` / paper-shadow sides: `shadow_buy, paper_buy`

## Replay Evidence
- abstain path validated: `True`
- reduce-only path validated: `True`
- paper-shadow path validated: `True`
- recent drift mode: `shadow_only_no_new_risk_falsification` / deployment verdict: `not_deployable_shadow_only_runtime_blocked`
- recent window: `100` / win_rate: `21.0%` / dominant_regime: `bear`
- best shadow gate: `observable_4h_shift_shadow_gate` / verdict: `fails_shadow_metric` / kept_win_rate: `21.5%`

## Machine Checks
- `current_lane_is_no_trade_block_lane`: `True`
- `should_trade_false`: `True`
- `allowed_layers_zero`: `True`
- `drift_replay_shadow_only`: `True`
- `risk_off_paths_visible`: `True`
- `paper_shadow_paths_visible`: `True`
- `support_evidence_not_deployable`: `True`
- `buy_add_support_closure_allowed`: `False`
- `risk_on_order_enabled`: `False`
- `order_submission_enabled`: `False`
- `live_exposure_allowed`: `False`
- `all_passed`: `True`
