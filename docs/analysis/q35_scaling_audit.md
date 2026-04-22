# Q35 Scaling Audit

- generated_at: **2026-04-22 08:43:09.576235**
- overall_verdict: **bias50_formula_may_be_too_harsh**
- structure_scaling_verdict: **q35_structure_caution_not_root_cause**
- scope_applicability: **current_live_q35_lane_active**
- reason: current bias50 已回到 exact-lane p90 內，但 legacy 公式仍可能把它壓成 0 分；需改做 exact-lane 內的保守分段校準，而不是繼續把它視為 broader bull segmentation 問題。
- applicability_note: current live row 仍位於 q35 lane；本輪 q35 scaling / bias50 calibration 結論可直接視為 live governance 主路徑。

## Current live row

- regime/gate/quality: **bull / BLOCK / D**
- structure_bucket: **BLOCK|bull_high_bias200_overheat_block|q35**
- legacy_entry_quality: **0.3473** (raw_reason=`regime_gate_block`)
- calibration_runtime_entry_quality: **0.3473** (raw_reason=`regime_gate_block`)
- deployed_runtime_entry_quality: **0.3473** (raw_reason=`regime_gate_block`, effective_reason=`unsupported_exact_live_structure_bucket`)
- q35_discriminative_redesign_applied: **False**
- feat_4h_bias50: **3.2625**
- structure_quality: **0.6208**

## Exact lane summary

- rows: **143** | win_rate: **0.0**
- bias50 distribution: {'min': 4.4309, 'p25': 5.0051, 'p50': 5.1899, 'p75': 5.2591, 'p90': 5.3636, 'p95': 5.4247, 'max': 5.5332, 'mean': 5.1062}
- current bias50 percentile in exact lane: **0.0**
- winner-only bias50 distribution: {'min': None, 'p25': None, 'p50': None, 'p75': None, 'p90': None, 'p95': None, 'max': None, 'mean': None}

## Broader bull cohorts

- same_gate_same_quality: rows=**376** | win_rate=**0.0** | bias50_pct=**0.2872** | dist={'min': 2.0009, 'p25': 2.1335, 'p50': 5.2024, 'p75': 5.4245, 'p90': 6.0169, 'p95': 6.183, 'max': 9.36, 'mean': 4.5057}
- same_bucket: rows=**144** | win_rate=**0.0** | bias50_pct=**0.0** | dist={'min': 4.4309, 'p25': 5.0051, 'p50': 5.1899, 'p75': 5.2591, 'p90': 5.3636, 'p95': 5.4247, 'max': 5.5332, 'mean': 5.106}
- bull_all: rows=**10159** | win_rate=**0.5952** | bias50_pct=**0.6313** | dist={'min': -1.1554, 'p25': 2.5954, 'p50': 2.8025, 'p75': 3.3094, 'p90': 3.374, 'p95': 3.5102, 'max': 9.36, 'mean': 2.9501}

## Segmented calibration

- status: **formula_review_required** | mode: **exact_lane_formula_review**
- runtime contract: **piecewise_runtime_not_required** — 本輪 audit 沒有要求 current row 套用 segmented calibration；runtime 可維持既有路徑。
- exact lane band: **core_normal** (pct=0.0, Δp90=-2.1011)
- same_gate_same_quality band: **core_normal** (pct=0.2872, Δp90=-2.7544)
- same_bucket band: **core_normal** (pct=0.0, Δp90=-2.1011)
- bull_all band: **warm** (pct=0.6313, Δp90=-0.1115)
- reference cohort: **same_gate_same_quality** / label=同 bull gate + 同 quality lane / pct=0.2872
- note: current bias50 已回到 exact lane p90 內；下一步應做 exact-lane 內的保守 bias50 校準 / 公式檢查，而不是再走 broader bull segmentation。
- runtime preview: applied=**False** | score=**0.0** | legacy=**0.0** | Δ=**0.0** | segment=**None**

## Deployment-grade component experiment

- verdict: **runtime_patch_no_material_improvement**
- baseline -> calibration runtime entry_quality: **0.3473 → 0.3473** (Δ=**0.0**)
- baseline -> deployed runtime entry_quality: **0.3473 → 0.3473** (Δ=**0.0**)
- baseline -> calibration -> deployed layers: **0 → 0 → 0**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- runtime_source: **live_predict_probe** | q35_discriminative_redesign_applied=**False**
- runtime gap to floor: **0.2027**
- next patch target: **feat_4h_bias50_formula**

## Counterfactuals

- gate -> ALLOW only: entry_quality **0.3473**, layers **0**
- fully relax bias50 penalty: entry_quality **0.6473**, layers **0**
- required bias50 cap to cross trade floor: **-0.9785** (current=3.2625)

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
- best scenario: **exact_lane_triplet_p75** → entry_quality **0.5094** / layers **0** / gap **0.0406**
- required_bias50_cap_after_best_scenario: **1.7235**
- note: bias50 + pulse (+ nose) 的 base-mix uplift 明顯優於只補 structure component，但 current live row 仍未跨過 trade floor；下一輪需升級成 base-stack redesign blocker，而不是再做單點 component 微調。

## Base-stack redesign experiment（support-aware discriminative reweight）

- verdict: **base_stack_redesign_candidate_grid_empty**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False** | positive_gap=**False**
- rows / wins / losses: **143 / 0 / 143**
- best discriminative candidate: weights=**None** → entry_quality **None** / gap **None** / mean_gap **None**
- best floor candidate: weights=**None** → entry_quality **None** / gap **None** / mean_gap **None**
- unsafe floor-cross candidate: **None**
- note: runtime exact lane grid search 沒有產生任何可比較候選。

## Recommended action

- base-mix experiment 已證明 bias50 + pulse (+ nose) uplift 仍未跨過 trade floor；下一輪必須升級成 base-stack redesign blocker，禁止再把結構 uplift 或單點 bias50 當成主 closure。
