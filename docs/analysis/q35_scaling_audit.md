# Q35 Scaling Audit

- generated_at: **2026-05-20 06:12:25.971102**
- overall_verdict: **broader_bull_cohort_recalibration_candidate**
- structure_scaling_verdict: **q35_structure_caution_not_root_cause**
- scope_applicability: **current_live_q35_lane_active**
- reason: exact-lane 仍偏熱，但 current bias50 已回到至少一個更廣 bull cohort 的常見區間；若要主張公式過嚴，下一步應做分段 / 分位數校準，而不是直接放寬 q35 gate 或 trade floor。
- applicability_note: current live row 仍位於 q35 lane；本輪 q35 scaling / bias50 calibration 結論可直接視為 live governance 主路徑。

## Current live row

- regime/gate/quality: **bear / CAUTION / C**
- structure_bucket: **CAUTION|base_caution_regime_or_bias|q35**
- legacy_entry_quality: **0.6127** (raw_reason=`entry_quality_C_single_layer`)
- calibration_runtime_entry_quality: **0.6127** (raw_reason=`entry_quality_C_single_layer`)
- deployed_runtime_entry_quality: **0.6127** (raw_reason=`entry_quality_C_single_layer`, effective_reason=`unsupported_exact_live_structure_bucket`)
- q35_discriminative_redesign_applied: **False**
- feat_4h_bias50: **-2.0431**
- structure_quality: **0.3543**

## Exact lane summary

- rows: **0** | win_rate: **None**
- bias50 distribution: {'min': None, 'p25': None, 'p50': None, 'p75': None, 'p90': None, 'p95': None, 'max': None, 'mean': None}
- current bias50 percentile in exact lane: **None**
- winner-only bias50 distribution: {'min': None, 'p25': None, 'p50': None, 'p75': None, 'p90': None, 'p95': None, 'max': None, 'mean': None}

## Broader bull cohorts

- same_gate_same_quality: rows=**187** | win_rate=**0.4064** | bias50_pct=**0.7914** | dist={'min': -4.1725, 'p25': -3.3195, 'p50': -2.6042, 'p75': -2.1713, 'p90': -1.3611, 'p95': -1.0713, 'max': -0.4535, 'mean': -2.6377}
- same_bucket: rows=**0** | win_rate=**None** | bias50_pct=**None** | dist={'min': None, 'p25': None, 'p50': None, 'p75': None, 'p90': None, 'p95': None, 'max': None, 'mean': None}
- bull_all: rows=**486** | win_rate=**0.5782** | bias50_pct=**0.5185** | dist={'min': -7.8921, 'p25': -2.9698, 'p50': -2.152, 'p75': -1.2045, 'p90': -1.1476, 'p95': -0.9744, 'max': -0.2201, 'mean': -2.2761}

## Segmented calibration

- status: **segmented_calibration_required** | mode: **piecewise_quantile_calibration**
- runtime contract: **piecewise_runtime_not_required** — 本輪 audit 沒有要求 current row 套用 segmented calibration；runtime 可維持既有路徑。
- exact lane band: **no_data** (pct=None, Δp90=None)
- same_gate_same_quality band: **elevated_but_within_p90** (pct=0.7914, Δp90=-0.682)
- same_bucket band: **no_data** (pct=None, Δp90=None)
- bull_all band: **warm** (pct=0.5185, Δp90=-0.8955)
- reference cohort: **same_gate_same_quality** / label=同 bull gate + 同 quality lane / pct=0.7914
- note: exact lane 顯示過熱，但至少一個更廣 bull cohort 仍把 current bias50 視為 p90 內；應改做 bull cohort segmentation / piecewise quantile calibration，而不是直接 relax runtime gate。
- runtime preview: applied=**False** | score=**0.8886199999999999** | legacy=**0.8886199999999999** | Δ=**0.0** | segment=**None**

## Deployment-grade component experiment

- verdict: **runtime_patch_crosses_floor_but_execution_blocked**
- baseline -> calibration runtime entry_quality: **0.6127 → 0.6127** (Δ=**0.0**)
- baseline -> deployed runtime entry_quality: **0.6127 → 0.6127** (Δ=**0.0**)
- baseline -> calibration -> deployed layers: **1 → 1 → 1**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**False**
- runtime_source: **live_predict_probe** | q35_discriminative_redesign_applied=**False**
- runtime gap to floor: **-0.0627**
- next patch target: **feat_4h_bias50_formula**

## Counterfactuals

- gate -> ALLOW only: entry_quality **0.6127**, layers **1**
- fully relax bias50 penalty: entry_quality **0.6461**, layers **1**
- required bias50 cap to cross trade floor: **-2.043** (current=-2.0431)

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
