# Q35 Scaling Audit

- generated_at: **2026-04-29 08:01:45.258474**
- overall_verdict: **runtime_blocker_preempts_q35_scaling**
- structure_scaling_verdict: **runtime_blocker_preempts_q35_scaling**
- scope_applicability: **current_live_q35_lane_active**
- reason: Recent 50-sample win rate: 24.00% < 30%
- applicability_note: current live row 仍位於 q35 lane；本輪 q35 scaling / bias50 calibration 結論可直接視為 live governance 主路徑。

## Runtime blocker preempt

- blocker: **circuit_breaker_active** from **circuit_breaker**
- summary: circuit breaker active：Recent 50-sample win rate: 24.00% < 30%; release condition = streak < 50 且 recent 50 win rate >= 30%；目前 recent 50 只贏 12/50，至少還差 3 勝。 exact-vs-spillover=同 quality 寬 scope 出現 bull|BLOCK spillover，395 rows / WR 15.3% / 品質 -0.101，明顯劣於 exact live lane WR — / 品質 —。
- allowed_layers: **0** (`decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active`)

## Current live row

- regime/gate/quality: **bear / CAUTION / D**
- structure_bucket: **CAUTION|structure_quality_caution|q35**
- feat_4h_bias50: **-0.5132**
- structure_quality: **0.3596**

## Recommended action

- 先解除 canonical circuit breaker 或至少接近 release condition，再重跑 q35 scaling audit；在 breaker 仍有效時，不得把 q35 formula / calibration 當成本輪 live blocker 主敘事。
