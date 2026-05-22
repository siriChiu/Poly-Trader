# Live canary structural pivot

- generated_at: `2026-05-22T23:27:38.041057Z`
- deployment_blocker: `circuit_breaker_active`
- current bucket: `BLOCK|bear_bias200_hard_block|q00`
- support: `0/50` (gap `50`)
- release_ready: `False` / recent wins `7/50`, required `15`, needed `8`
- venue_runtime_ready: `False` / OKX credentials configured: `False`
- top-k: risk-qualified `6`, runtime-blocked `6`, deployable `0`

## Decision
停止只做 observation-only heartbeat。結構改成三條 lane：

1. **Venue lifecycle proof** — 先證明 OKX credential / ack / cancel 或 fill / reconciliation，不把模型風險混進來。
2. **Model shadow to decision** — 高信心 Top-K 只做影子決策與 24h pyramid outcome；如果 same semantic signature + support delta=0 連續 2 輪，直接切 Map/Signal redesign。
3. **Strategy micro-canary** — 真正策略實單只允許極小額、單商品、第一層、無自動加倉；任何 lifecycle / slippage / runtime hard-block 失敗即停。

## Code guard added in this turn
`execution/execution_service.py` 現在會在 live buy/add 送到 adapter 前先檢查：

- `execution.mode == live` 且 `enable_live_trading=true` 時，買入必須有 `execution.live_canary.enabled=true`。
- 必須有 explicit `allowed_symbols` 與 `max_base_qty_by_symbol`。
- 超過 symbol cap 的 live buy 會以 `live_canary_qty_cap_exceeded` 拒單。
- reduce/sell 風險降低路徑不被這個 canary policy 阻擋。

## Redacted local config shape
```yaml
execution:
  mode: live
  venue: okx
  enable_live_trading: true
  kill_switch: false
  max_daily_loss_pct: 0.003
  max_consecutive_failures: 1
  live_canary:
    enabled: true
    allowed_symbols: [BTC/USDT]
    max_base_qty_by_symbol:
      BTC/USDT: 0.0001
  venues:
    okx:
      enabled: true
      api_key: "[REDACTED]"
      api_secret: "[REDACTED]"
      passphrase: "[REDACTED]"
      default_type: spot
```

## 72h sequence
1. **T+0h** — 保持買入 / 加倉 fail-closed；只允許等待、影子觀察、減風險與 venue proof。  
2. **T+4h** — 配置 OKX credential 後重跑：`PYTHONPATH=. venv/bin/python scripts/execution_metadata_smoke.py --symbol BTCUSDT --venues okx`。  
3. **T+24h** — selective sleeve 跑最近 Top-K 候選的 shadow ledger，記錄 24h pyramid outcome。  
4. **T+48h** — 只有當 venue proof + breaker release + runtime 非 bear-hard-block 同時過，才準備一筆 micro-canary。  
5. **T+72h** — 要嘛執行一筆 bounded micro-canary，要嘛寫明唯一失敗 gate；禁止再產出沒有決策的 heartbeat。

## Hard no-go now
目前 `support=0/50`、`release_ready=false`、`venue_runtime_ready=false`，所以策略買入 / 加倉仍不應放行。實戰化第一步是把交易所生命週期與 micro-canary policy 做實，而不是把 q00 / 熔斷 gate 人工關掉。
