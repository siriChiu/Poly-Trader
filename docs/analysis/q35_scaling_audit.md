# Q35 Scaling Audit

- generated_at: **2026-04-21 00:52:45.941761**
- overall_verdict: **bias50_formula_may_be_too_harsh**
- structure_scaling_verdict: **q35_structure_caution_not_root_cause**
- scope_applicability: **current_live_q35_lane_active**
- reason: current bias50 已回到 exact-lane p90 內，但 legacy 公式仍可能把它壓成 0 分；需改做 exact-lane 內的保守分段校準，而不是繼續把它視為 broader bull segmentation 問題。
- applicability_note: current live row 仍位於 q35 lane；本輪 q35 scaling / bias50 calibration 結論可直接視為 live governance 主路徑。

## Current live row

- regime/gate/quality: **bull / CAUTION / D**
- structure_bucket: **CAUTION|structure_quality_caution|q35**
- legacy_entry_quality: **0.5074** (raw_reason=`entry_quality_below_trade_floor`)
- calibration_runtime_entry_quality: **0.5074** (raw_reason=`entry_quality_below_trade_floor`)
- deployed_runtime_entry_quality: **0.5685** (raw_reason=`entry_quality_C_single_layer`, effective_reason=`unsupported_exact_live_structure_bucket`)
- q35_discriminative_redesign_applied: **True**
- feat_4h_bias50: **1.5195**
- structure_quality: **0.4001**

## Exact lane summary

- rows: **4194** | win_rate: **0.6133**
- bias50 distribution: {'min': 1.6545, 'p25': 3.2675, 'p50': 3.3114, 'p75': 3.3474, 'p90': 3.3846, 'p95': 3.4554, 'max': 4.9835, 'mean': 3.2801}
- current bias50 percentile in exact lane: **0.0**
- winner-only bias50 distribution: {'min': 1.6545, 'p25': 3.2677, 'p50': 3.3094, 'p75': 3.3476, 'p90': 3.3821, 'p95': 3.4283, 'max': 4.4393, 'mean': 3.2616}

## Broader bull cohorts

- same_gate_same_quality: rows=**9497** | win_rate=**0.6137** | bias50_pct=**0.0007** | dist={'min': -1.1489, 'p25': 2.604, 'p50': 2.7938, 'p75': 3.3017, 'p90': 3.354, 'p95': 3.38, 'max': 4.9835, 'mean': 2.8941}
- same_bucket: rows=**4195** | win_rate=**0.6133** | bias50_pct=**0.0** | dist={'min': 1.6545, 'p25': 3.2675, 'p50': 3.3114, 'p75': 3.3474, 'p90': 3.3848, 'p95': 3.4559, 'max': 4.9835, 'mean': 3.2802}
- bull_all: rows=**10065** | win_rate=**0.5956** | bias50_pct=**0.0054** | dist={'min': -1.1554, 'p25': 2.6033, 'p50': 2.807, 'p75': 3.3107, 'p90': 3.3745, 'p95': 3.5115, 'max': 9.36, 'mean': 2.9618}

## Segmented calibration

- status: **formula_review_required** | mode: **exact_lane_formula_review**
- runtime contract: **piecewise_runtime_not_required** — 本輪 audit 沒有要求 current row 套用 segmented calibration；runtime 可維持既有路徑。
- exact lane band: **core_normal** (pct=0.0, Δp90=-1.8651)
- same_gate_same_quality band: **core_normal** (pct=0.0007, Δp90=-1.8345)
- same_bucket band: **core_normal** (pct=0.0, Δp90=-1.8653)
- bull_all band: **core_normal** (pct=0.0054, Δp90=-1.855)
- reference cohort: **same_gate_same_quality** / label=同 bull gate + 同 quality lane / pct=0.0007
- note: current bias50 已回到 exact lane p90 內；下一步應做 exact-lane 內的保守 bias50 校準 / 公式檢查，而不是再走 broader bull segmentation。
- runtime preview: applied=**False** | score=**0.17609999999999998** | legacy=**0.17609999999999998** | Δ=**0.0** | segment=**None**

## Deployment-grade component experiment

- verdict: **runtime_patch_crosses_trade_floor**
- baseline -> calibration runtime entry_quality: **0.5074 → 0.5074** (Δ=**0.0**)
- baseline -> deployed runtime entry_quality: **0.5074 → 0.5685** (Δ=**0.0611**)
- baseline -> calibration -> deployed layers: **0 → 0 → 1**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**True**
- runtime_source: **live_predict_probe** | q35_discriminative_redesign_applied=**True**
- runtime gap to floor: **-0.0185**
- next patch target: **verify_runtime_guardrails**

## Counterfactuals

- gate -> ALLOW only: entry_quality **0.5074**, layers **0**
- fully relax bias50 penalty: entry_quality **0.7545**, layers **2**
- required bias50 cap to cross trade floor: **0.8095** (current=1.5195)

## Joint component experiment（bias50 runtime patch + feat_4h_dist_swing_low uplift）

- verdict: **joint_component_experiment_no_supportive_target**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- best scenario: **None** → entry_quality **None** / layers **None** / gap **None**
- required_bias50_cap_after_best_scenario: **None**
- note: 在 exact-supported q35 lane / winner cohorts 內找不到比 current row 更高的 dist_swing_low 支持目標；本輪無法形成可驗證的 joint component experiment。

## Exact-supported bias50 component experiment

- verdict: **exact_supported_bias50_component_improves_but_still_below_floor**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False** | used_exact_supported_target=**True**
- best scenario: **exact_runtime_p90** → entry_quality **0.5236** / layers **0** / gap **0.0264** / target_score **0.2304**
- note: 即使只用 exact-supported / winner-supported 的 bias50 runtime 目標做單點 component experiment，entry_quality 仍未跨過 trade floor；這表示 blocker 不再是『少一點點 bias50 support』。

## Base-mix component experiment（bias50 + pulse + nose）

- verdict: **base_mix_component_experiment_improves_but_still_below_floor**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- best scenario: **winner_triplet_p75** → entry_quality **0.5451** / layers **0** / gap **0.0049**
- required_bias50_cap_after_best_scenario: **1.438**
- note: bias50 + pulse (+ nose) 的 base-mix uplift 明顯優於只補 structure component，但 current live row 仍未跨過 trade floor；下一輪需升級成 base-stack redesign blocker，而不是再做單點 component 微調。

## Base-stack redesign experiment（support-aware discriminative reweight）

- verdict: **base_stack_redesign_discriminative_reweight_crosses_trade_floor**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**True** | positive_gap=**True**
- rows / wins / losses: **4148 / 2537 / 1611**
- best discriminative candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.55, 'feat_pulse': 0.45, 'feat_ear': -0.0}** → entry_quality **0.5685** / gap **0.0** / mean_gap **0.005**
- best floor candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 0.0, 'feat_ear': 1.0}** → entry_quality **0.8497** / gap **0.0** / mean_gap **-0.004**
- unsafe floor-cross candidate: **{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 0.0, 'feat_ear': 1.0}**
- note: 在 runtime exact lane 內，以正向 discrimination 為約束的 base-stack reweight 已足以讓 current live row 跨過 trade floor。

## Recommended action

- base-mix experiment 已證明 bias50 + pulse (+ nose) uplift 仍未跨過 trade floor；下一輪必須升級成 base-stack redesign blocker，禁止再把結構 uplift 或單點 bias50 當成主 closure。
