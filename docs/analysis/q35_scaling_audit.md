# Q35 Scaling Audit

- generated_at: **2026-05-24 00:12:29.917754**
- overall_verdict: **broader_bull_cohort_recalibration_candidate**
- structure_scaling_verdict: **q35_structure_caution_not_root_cause**
- scope_applicability: **current_live_q35_lane_active**
- reason: exact-lane 仍偏熱，但 current bias50 已回到至少一個更廣 bull cohort 的常見區間；若要主張公式過嚴，下一步應做分段 / 分位數校準，而不是直接放寬 q35 gate 或 trade floor。
- applicability_note: current live row 仍位於 q35 lane；本輪 q35 scaling / bias50 calibration 結論可直接視為 live governance 主路徑。

## Current live row

- regime/gate/quality: **bear / CAUTION / D**
- structure_bucket: **CAUTION|base_caution_regime_or_bias|q35**
- legacy_entry_quality: **0.5361** (raw_reason=`entry_quality_below_trade_floor`)
- calibration_runtime_entry_quality: **0.5361** (raw_reason=`entry_quality_below_trade_floor`)
- deployed_runtime_entry_quality: **0.5361** (raw_reason=`entry_quality_below_trade_floor`, effective_reason=`unsupported_exact_live_structure_bucket`)
- q35_discriminative_redesign_applied: **False**
- feat_4h_bias50: **-0.714**
- structure_quality: **0.4938**

## Exact lane summary

- rows: **0** | win_rate: **None**
- bias50 distribution: {'min': None, 'p25': None, 'p50': None, 'p75': None, 'p90': None, 'p95': None, 'max': None, 'mean': None}
- current bias50 percentile in exact lane: **None**
- winner-only bias50 distribution: {'min': None, 'p25': None, 'p50': None, 'p75': None, 'p90': None, 'p95': None, 'max': None, 'mean': None}

## Broader bull cohorts

- same_gate_same_quality: rows=**46** | win_rate=**0.5** | bias50_pct=**0.7174** | dist={'min': -1.9487, 'p25': -1.3726, 'p50': -1.1983, 'p75': -0.5653, 'p90': -0.3989, 'p95': -0.3047, 'max': -0.2201, 'mean': -1.0557}
- same_bucket: rows=**3** | win_rate=**1.0** | bias50_pct=**1.0** | dist={'min': -2.0431, 'p25': -2.0431, 'p50': -2.0241, 'p75': -2.0204, 'p90': -2.0204, 'p95': -2.0204, 'max': -2.0204, 'mean': -2.0292}
- bull_all: rows=**639** | win_rate=**0.6244** | bias50_pct=**0.9765** | dist={'min': -7.8921, 'p25': -2.9164, 'p50': -2.4101, 'p75': -1.3725, 'p90': -1.1566, 'p95': -0.9936, 'max': -0.2201, 'mean': -2.3165}

## Segmented calibration

- status: **segmented_calibration_required** | mode: **piecewise_quantile_calibration**
- runtime contract: **piecewise_runtime_not_required** — 本輪 audit 沒有要求 current row 套用 segmented calibration；runtime 可維持既有路徑。
- exact lane band: **no_data** (pct=None, Δp90=None)
- same_gate_same_quality band: **warm** (pct=0.7174, Δp90=-0.3151)
- same_bucket band: **overheat** (pct=1.0, Δp90=1.3064)
- bull_all band: **overheat** (pct=0.9765, Δp90=0.4426)
- reference cohort: **same_gate_same_quality** / label=同 bull gate + 同 quality lane / pct=0.7174
- note: exact lane 顯示過熱，但至少一個更廣 bull cohort 仍把 current bias50 視為 p90 內；應改做 bull cohort segmentation / piecewise quantile calibration，而不是直接 relax runtime gate。
- runtime preview: applied=**False** | score=**0.6228** | legacy=**0.6228** | Δ=**0.0** | segment=**None**

## Deployment-grade component experiment

- verdict: **runtime_patch_no_material_improvement**
- baseline -> calibration runtime entry_quality: **0.5361 → 0.5361** (Δ=**0.0**)
- baseline -> deployed runtime entry_quality: **0.5361 → 0.5361** (Δ=**0.0**)
- baseline -> calibration -> deployed layers: **0 → 0 → 0**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- runtime_source: **live_predict_probe** | q35_discriminative_redesign_applied=**False**
- runtime gap to floor: **0.0139**
- next patch target: **feat_4h_bias50_formula**

## Counterfactuals

- gate -> ALLOW only: entry_quality **0.5361**, layers **0**
- fully relax bias50 penalty: entry_quality **0.6493**, layers **1**
- required bias50 cap to cross trade floor: **-0.9455** (current=-0.714)

## Joint component experiment（bias50 runtime patch + feat_4h_dist_swing_low uplift）

- verdict: **joint_component_experiment_no_supportive_target**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- best scenario: **None** → entry_quality **None** / layers **None** / gap **None**
- required_bias50_cap_after_best_scenario: **None**
- note: 在 exact-supported q35 lane / winner cohorts 內找不到比 current row 更高的 dist_swing_low 支持目標；本輪無法形成可驗證的 joint component experiment。

## Exact-supported bias50 component experiment

- verdict: **exact_supported_bias50_component_no_higher_supported_target**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False** | used_exact_supported_target=**False**
- best scenario: **None** → entry_quality **None** / layers **None** / gap **None** / target_score **None**
- note: runtime exact-supported lane 裡找不到比 current bias50 score 更高、且仍屬 exact-supported / winner-supported 的單點目標；本輪無法形成更強的 bias50 component uplift。

## Base-mix component experiment（bias50 + pulse + nose）

- verdict: **base_mix_component_experiment_no_supportive_target**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- best scenario: **None** → entry_quality **None** / layers **None** / gap **None**
- required_bias50_cap_after_best_scenario: **None**
- note: 在 exact/winner cohorts 中找不到足以構成 base-mix 驗證的支持目標；本輪無法完成 bias50 + pulse (+ nose) 的可驗證 experiment。

## Base-stack redesign experiment（support-aware discriminative reweight）

- verdict: **base_stack_redesign_no_runtime_exact_lane_rows**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False** | positive_gap=**False** | execution_blocked_after_floor_cross=**None**
- rows / wins / losses: **0 / 0 / 0**
- best discriminative candidate: weights=**None** → entry_quality **None** / gap **None** / mean_gap **None**
- best floor candidate: weights=**None** → entry_quality **None** / gap **None** / mean_gap **None**
- unsafe floor-cross candidate: **None**
- note: runtime calibrated exact lane 沒有可用 rows，無法做 base-stack redesign grid search。

## Recommended action

- 維持 q35=CAUTION；把本輪焦點放在 bias50 正規化是否應改成分段/分位數縮放，只有當 current bias50 落在 exact-lane 常見區間時才放寬。
