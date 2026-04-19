# Q35 Scaling Audit

- generated_at: **2026-04-19 15:28:20.758114**
- overall_verdict: **runtime_blocker_preempts_q35_scaling**
- structure_scaling_verdict: **runtime_blocker_preempts_q35_scaling**
- scope_applicability: **current_live_q35_lane_active**
- reason: Recent 50-sample win rate: 2.00% < 30%
- applicability_note: current live row 仍位於 q35 lane；本輪 q35 scaling / bias50 calibration 結論可直接視為 live governance 主路徑。

## Runtime blocker preempt

- blocker: **circuit_breaker_active** from **circuit_breaker**
- summary: circuit breaker active：Recent 50-sample win rate: 2.00% < 30%; release condition = streak < 50 且 recent 50 win rate >= 30%；目前 recent 50 只贏 1/50，至少還差 14 勝。 同時 recent pathology=recent scope slice 199 rows shows distribution_pathology alerts=['label_imbalance'] win_rate=0.005 avg_pnl=-0.0099 avg_quality=-0.2829 window=2026-04-17 17:43:38.299919->2026-04-18 16:28:02.554167 adverse_streak=188x0 (2026-04-17 17:43:38.299919->2026-04-18 13:43:25.809469)。
- allowed_layers: **0** (`decision_quality_below_trade_floor; unsupported_live_structure_bucket_blocks_trade; circuit_breaker_active`)

## Current live row

- regime/gate/quality: **bull / CAUTION / D**
- structure_bucket: **CAUTION|structure_quality_caution|q35**
- feat_4h_bias50: **2.3204**
- structure_quality: **0.3913**

## Recommended action

- 先解除 canonical circuit breaker 或至少接近 release condition，再重跑 q35 scaling audit；在 breaker 仍有效時，不得把 q35 formula / calibration 當成本輪 live blocker 主敘事。
