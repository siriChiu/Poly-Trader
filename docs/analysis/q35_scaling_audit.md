# Q35 Scaling Audit

- generated_at: **2026-05-23 22:10:46.258308**
- overall_verdict: **runtime_blocker_preempts_q35_scaling**
- structure_scaling_verdict: **runtime_blocker_preempts_q35_scaling**
- scope_applicability: **current_live_q35_lane_active**
- reason: Recent 50-sample win rate: 26.00% < 30%
- applicability_note: current live row 仍位於 q35 lane；本輪 q35 scaling / bias50 calibration 結論可直接視為 live governance 主路徑。

## Runtime blocker preempt

- blocker: **circuit_breaker_active** from **circuit_breaker**
- summary: 風控熔斷啟用中：最近 50 筆勝率: 26.00% < 30%；解除條件：連續虧損筆數 < 50 且最近 50 筆勝率 >= 30%；目前最近 50 筆只贏 13/50，至少還差 2 勝。 精準路徑與外溢對照：同 gate 寬範圍出現 熊市｜觀察 外溢，153 筆 / 勝率 0.0% / 品質 -0.334，明顯劣於 精準即時路徑 勝率 34.4% / 品質 -0.043。
- allowed_layers: **0** (`decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active`)

## Current live row

- regime/gate/quality: **bear / CAUTION / C**
- structure_bucket: **CAUTION|base_caution_regime_or_bias|q35**
- feat_4h_bias50: **-0.6878**
- structure_quality: **0.4464**

## Recommended action

- 先解除 canonical circuit breaker 或至少接近 release condition，再重跑 q35 scaling audit；在 breaker 仍有效時，不得把 q35 formula / calibration 當成本輪 live blocker 主敘事。
