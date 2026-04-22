# Q35 Scaling Audit

- generated_at: **2026-04-22 02:05:17.873413**
- overall_verdict: **bias50_formula_may_be_too_harsh**
- structure_scaling_verdict: **q35_structure_caution_not_root_cause**
- scope_applicability: **current_live_q35_lane_active**
- reason: current bias50 已回到 exact-lane p90 內，但 legacy 公式仍可能把它壓成 0 分；需改做 exact-lane 內的保守分段校準，而不是繼續把它視為 broader bull segmentation 問題。
- applicability_note: current live row 仍位於 q35 lane；本輪 q35 scaling / bias50 calibration 結論可直接視為 live governance 主路徑。

## Current live row

- regime/gate/quality: **bull / CAUTION / D**
- structure_bucket: **CAUTION|structure_quality_caution|q35**
- legacy_entry_quality: **0.5188** (raw_reason=`entry_quality_below_trade_floor`)
- calibration_runtime_entry_quality: **0.5188** (raw_reason=`entry_quality_below_trade_floor`)
- deployed_runtime_entry_quality: **0.5532** (raw_reason=`entry_quality_C_single_layer`, effective_reason=`unsupported_exact_live_structure_bucket`)
- q35_discriminative_redesign_applied: **True**
- feat_4h_bias50: **1.2325**
- structure_quality: **0.4073**

## Exact lane summary

- rows: **4262** | win_rate: **0.6096**
- bias50 distribution: {'min': 1.2403, 'p25': 3.2671, 'p50': 3.3094, 'p75': 3.3474, 'p90': 3.384, 'p95': 3.447, 'max': 4.9835, 'mean': 3.2564}
- current bias50 percentile in exact lane: **0.0**
- winner-only bias50 distribution: {'min': 1.2403, 'p25': 3.2671, 'p50': 3.3077, 'p75': 3.3474, 'p90': 3.3813, 'p95': 3.4256, 'max': 4.4393, 'mean': 3.244}

## Broader bull cohorts

- same_gate_same_quality: rows=**9565** | win_rate=**0.612** | bias50_pct=**0.0007** | dist={'min': -1.1489, 'p25': 2.6003, 'p50': 2.7934, 'p75': 3.3013, 'p90': 3.3536, 'p95': 3.3792, 'max': 4.9835, 'mean': 2.8863}
- same_bucket: rows=**4263** | win_rate=**0.6097** | bias50_pct=**0.0** | dist={'min': 1.2403, 'p25': 3.2671, 'p50': 3.3094, 'p75': 3.3474, 'p90': 3.384, 'p95': 3.447, 'max': 4.9835, 'mean': 3.2566}
- bull_all: rows=**10133** | win_rate=**0.5942** | bias50_pct=**0.0053** | dist={'min': -1.1554, 'p25': 2.5959, 'p50': 2.8045, 'p75': 3.3095, 'p90': 3.374, 'p95': 3.5102, 'max': 9.36, 'mean': 2.954}

## Segmented calibration

- status: **formula_review_required** | mode: **exact_lane_formula_review**
- runtime contract: **piecewise_runtime_not_required** — 本輪 audit 沒有要求 current row 套用 segmented calibration；runtime 可維持既有路徑。
- exact lane band: **core_normal** (pct=0.0, Δp90=-2.1515)
- same_gate_same_quality band: **core_normal** (pct=0.0007, Δp90=-2.1211)
- same_bucket band: **core_normal** (pct=0.0, Δp90=-2.1515)
- bull_all band: **core_normal** (pct=0.0053, Δp90=-2.1415)
- reference cohort: **same_gate_same_quality** / label=同 bull gate + 同 quality lane / pct=0.0007
- note: current bias50 已回到 exact lane p90 內；下一步應做 exact-lane 內的保守 bias50 校準 / 公式檢查，而不是再走 broader bull segmentation。
- runtime preview: applied=**False** | score=**0.23349999999999999** | legacy=**0.23349999999999999** | Δ=**0.0** | segment=**None**

## Deployment-grade component experiment

- verdict: **runtime_patch_crosses_trade_floor**
- baseline -> calibration runtime entry_quality: **0.5188 → 0.5188** (Δ=**0.0**)
- baseline -> deployed runtime entry_quality: **0.5188 → 0.5532** (Δ=**0.0344**)
- baseline -> calibration -> deployed layers: **0 → 0 → 1**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**True**
- runtime_source: **live_predict_probe** | q35_discriminative_redesign_applied=**True**
- runtime gap to floor: **-0.0032**
- next patch target: **verify_runtime_guardrails**

## Counterfactuals

- gate -> ALLOW only: entry_quality **0.5188**, layers **0**
- fully relax bias50 penalty: entry_quality **0.7488**, layers **2**
- required bias50 cap to cross trade floor: **0.7125** (current=1.2325)

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

- verdict: **base_mix_component_experiment_improves_but_still_below_floor**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- best scenario: **winner_triplet_p75** → entry_quality **0.5245** / layers **0** / gap **0.0255**
- required_bias50_cap_after_best_scenario: **0.8075**
- note: bias50 + pulse (+ nose) 的 base-mix uplift 明顯優於只補 structure component，但 current live row 仍未跨過 trade floor；下一輪需升級成 base-stack redesign blocker，而不是再做單點 component 微調。

## Base-stack redesign experiment（support-aware discriminative reweight）

- verdict: **base_stack_redesign_discriminative_reweight_crosses_trade_floor**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**True** | positive_gap=**True**
- rows / wins / losses: **4217 / 2564 / 1653**
- best discriminative candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.95, 'feat_pulse': 0.0, 'feat_ear': 0.05}** → entry_quality **0.5532** / gap **0.0** / mean_gap **0.0092**
- best floor candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 0.0, 'feat_ear': 1.0}** → entry_quality **0.8148** / gap **0.0** / mean_gap **-0.0044**
- unsafe floor-cross candidate: **{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 0.0, 'feat_ear': 1.0}**
- note: 在 runtime exact lane 內，以正向 discrimination 為約束的 base-stack reweight 已足以讓 current live row 跨過 trade floor。

## Recommended action

- base-mix experiment 已證明 bias50 + pulse (+ nose) uplift 仍未跨過 trade floor；下一輪必須升級成 base-stack redesign blocker，禁止再把結構 uplift 或單點 bias50 當成主 closure。
