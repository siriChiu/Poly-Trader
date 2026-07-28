# Venue dry-run proof

- generated_at: `2026-07-28T18:28:58.259919Z`
- status: `blocked_missing_runtime_backed_proof`
- symbol: `BTC/USDT`
- live_exposure_allowed: `False`
- order_submission_enabled: `False`
- risk_on_order_enabled: `False`
- dry_run_only: `True`
- runtime_ready: `False` (0/2)
- credential_present: `False` (values redacted)

## Venues
- `okx`: adapter_supported=`True`, enabled_in_config=`True`, credentials_configured=`False`, proof_state=`public_metadata_only`, runtime_ready=`False`, order_preview_status=`blocked_missing_credentials`
  - blocker: live exchange credential 尚未驗證
  - blocker: order ack lifecycle 尚未驗證
  - blocker: fill lifecycle 尚未驗證
  - blocker: order preview is dry-run only
  - blocker: runtime-backed order ack proof missing
  - blocker: runtime-backed cancel proof missing
- `binance`: adapter_supported=`False`, enabled_in_config=`False`, credentials_configured=`False`, proof_state=`adapter_unsupported`, runtime_ready=`False`, order_preview_status=`blocked_adapter_unsupported`
  - blocker: 場館 adapter 尚未接入
  - blocker: 元資料契約尚未通過
  - blocker: 場館設定停用
  - blocker: live exchange credential 尚未驗證
  - blocker: order ack lifecycle 尚未驗證
  - blocker: fill lifecycle 尚未驗證

## Lifecycle Checks
- ack: `blocked_missing_credentials` / runtime_backed=`False`
- cancel: `blocked_missing_credentials` / runtime_backed=`False`
- fill: `blocked_missing_credentials` / runtime_backed=`False`
- reconciliation: `blocked_missing_credentials` / runtime_backed=`False`

## Local contract rehearsal (not exchange proof)
- local lifecycle rehearsal: `passed_local_state_machine_runtime_unverified`
- scope: `local_contract_rehearsal_not_exchange_proof`
- venue: `okx`
- runtime_backed: `False`
- live_adapter_called: `False`
- interpretation: local state-machine/ledger proof only; exchange ack/fill/cancel/reconciliation remain unverified.
