# Q35 Scaling Audit

- generated_at: **2026-04-23 03:15:06.138534**
- overall_verdict: **reference_only_current_bucket_outside_q35**
- structure_scaling_verdict: **reference_only_current_bucket_outside_q35**
- scope_applicability: **reference_only_current_bucket_outside_q35**
- reason: current live row 已不在 q35 lane；q35 scaling audit 只能保留為 reference-only calibration artifact，不得誤寫成當前 live blocker 已落在 q35 formula review。
- applicability_note: current live row 已不在 q35 lane；q35 scaling audit 只能保留為 reference-only calibration artifact，不得誤寫成當前 live blocker 已落在 q35 formula review。

## Reference-only current row

- regime/gate/quality: **bull / CAUTION / D**
- structure_bucket: **CAUTION|structure_quality_caution|q15**
- feat_4h_bias50: **2.475**
- structure_quality: **0.286**

## Recommended action

- current live row 已離開 q35 lane；本輪 q35 audit 保留為 reference-only。下一步應直接跟 current live bucket 的 support / runtime blocker，而不是再為 q35 calibration 重跑 historical lane 分析。
