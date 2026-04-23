# Q35 Scaling Audit

- generated_at: **2026-04-23 18:12:29.261878**
- overall_verdict: **bias50_formula_may_be_too_harsh**
- structure_scaling_verdict: **q35_structure_caution_not_root_cause**
- scope_applicability: **current_live_q35_lane_active**
- reason: current bias50 已回到 exact-lane p90 內，但 legacy 公式仍可能把它壓成 0 分；需改做 exact-lane 內的保守分段校準，而不是繼續把它視為 broader bull segmentation 問題。
- applicability_note: current live row 仍位於 q35 lane；本輪 q35 scaling / bias50 calibration 結論可直接視為 live governance 主路徑。

## Current live row

- regime/gate/quality: **bull / BLOCK / D**
- structure_bucket: **BLOCK|bull_high_bias200_overheat_block|q35**
- legacy_entry_quality: **0.3923** (raw_reason=`regime_gate_block`)
- calibration_runtime_entry_quality: **0.3923** (raw_reason=`regime_gate_block`)
- deployed_runtime_entry_quality: **0.3923** (raw_reason=`regime_gate_block`, effective_reason=`unsupported_exact_live_structure_bucket`)
- q35_discriminative_redesign_applied: **False**
- feat_4h_bias50: **2.5193**
- structure_quality: **0.3651**

## Exact lane summary

- rows: **184** | win_rate: **0.6522**
- bias50 distribution: {'min': -0.7025, 'p25': 1.1363, 'p50': 1.8546, 'p75': 4.0418, 'p90': 4.9496, 'p95': 5.5827, 'max': 6.3969, 'mean': 2.5755}
- current bias50 percentile in exact lane: **0.5543**
- winner-only bias50 distribution: {'min': -0.7025, 'p25': 1.01, 'p50': 3.6097, 'p75': 4.4696, 'p90': 5.3929, 'p95': 5.7175, 'max': 6.3969, 'mean': 2.8845}

## Broader bull cohorts

- same_gate_same_quality: rows=**750** | win_rate=**0.532** | bias50_pct=**0.536** | dist={'min': -18.7285, 'p25': -0.0736, 'p50': 2.0406, 'p75': 5.6979, 'p90': 7.1403, 'p95': 8.8165, 'max': 17.0434, 'mean': 2.827}
- same_bucket: rows=**195** | win_rate=**0.6615** | bias50_pct=**0.5795** | dist={'min': -0.7025, 'p25': 1.0207, 'p50': 1.7335, 'p75': 3.9909, 'p90': 4.8559, 'p95': 5.5826, 'max': 6.3969, 'mean': 2.4738}
- bull_all: rows=**10384** | win_rate=**0.5964** | bias50_pct=**0.6639** | dist={'min': -20.6429, 'p25': -1.5049, 'p50': 1.097, 'p75': 3.2737, 'p90': 5.2257, 'p95': 6.1118, 'max': 17.0434, 'mean': 0.8734}

## Segmented calibration

- status: **formula_review_required** | mode: **exact_lane_formula_review**
- runtime contract: **piecewise_runtime_not_required** — 本輪 audit 沒有要求 current row 套用 segmented calibration；runtime 可維持既有路徑。
- exact lane band: **warm** (pct=0.5543, Δp90=-2.4303)
- same_gate_same_quality band: **warm** (pct=0.536, Δp90=-4.621)
- same_bucket band: **warm** (pct=0.5795, Δp90=-2.3366)
- bull_all band: **warm** (pct=0.6639, Δp90=-2.7064)
- reference cohort: **same_gate_same_quality** / label=同 bull gate + 同 quality lane / pct=0.536
- note: current bias50 已回到 exact lane p90 內；下一步應做 exact-lane 內的保守 bias50 校準 / 公式檢查，而不是再走 broader bull segmentation。
- runtime preview: applied=**False** | score=**0.0** | legacy=**0.0** | Δ=**0.0** | segment=**None**

## Deployment-grade component experiment

- verdict: **runtime_patch_no_material_improvement**
- baseline -> calibration runtime entry_quality: **0.3923 → 0.3923** (Δ=**0.0**)
- baseline -> deployed runtime entry_quality: **0.3923 → 0.3923** (Δ=**0.0**)
- baseline -> calibration -> deployed layers: **0 → 0 → 0**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- runtime_source: **live_predict_probe** | q35_discriminative_redesign_applied=**False**
- runtime gap to floor: **0.1577**
- next patch target: **feat_4h_bias50_formula**

## Counterfactuals

- gate -> ALLOW only: entry_quality **0.3923**, layers **0**
- fully relax bias50 penalty: entry_quality **0.6923**, layers **0**
- required bias50 cap to cross trade floor: **-0.2285** (current=2.5193)

## Joint component experiment（bias50 runtime patch + feat_4h_dist_swing_low uplift）

- verdict: **joint_component_experiment_improves_but_still_below_floor**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- best scenario: **exact_lane_p75** → entry_quality **0.4406** / layers **0** / gap **0.1094**
- required_bias50_cap_after_best_scenario: **0.5765**
- note: 加入 feat_4h_dist_swing_low uplift 後，entry_quality 有改善，但 exact-supported q35 lane 仍低於 trade floor；下一步需要更強的 bias50 / base-mix closure，而不是只補結構 component。

## Exact-supported bias50 component experiment

- verdict: **exact_supported_bias50_component_improves_but_still_below_floor**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False** | used_exact_supported_target=**True**
- best scenario: **exact_runtime_p90** → entry_quality **0.4913** / layers **0** / gap **0.0587** / target_score **0.33**
- note: 即使只用 exact-supported / winner-supported 的 bias50 runtime 目標做單點 component experiment，entry_quality 仍未跨過 trade floor；這表示 blocker 不再是『少一點點 bias50 support』。

## Base-mix component experiment（bias50 + pulse + nose）

- verdict: **base_mix_component_experiment_improves_but_still_below_floor**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- best scenario: **winner_triplet_p75** → entry_quality **0.4965** / layers **0** / gap **0.0535**
- required_bias50_cap_after_best_scenario: **0.1185**
- note: bias50 + pulse (+ nose) 的 base-mix uplift 明顯優於只補 structure component，但 current live row 仍未跨過 trade floor；下一輪需升級成 base-stack redesign blocker，而不是再做單點 component 微調。

## Base-stack redesign experiment（support-aware discriminative reweight）

- verdict: **base_stack_redesign_discriminative_reweight_still_below_floor**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**False** | positive_gap=**True**
- rows / wins / losses: **184 / 120 / 64**
- best discriminative candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.6, 'feat_pulse': 0.0, 'feat_ear': 0.4}** → entry_quality **0.57** / gap **0.0** / mean_gap **0.0016**
- best floor candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 0.0, 'feat_ear': 1.0}** → entry_quality **0.8118** / gap **0.0** / mean_gap **-0.0269**
- unsafe floor-cross candidate: **None**
- note: 即使在 runtime exact lane 內做 support-aware / discriminative reweight，最佳候選仍無法讓 current live row 跨過 trade floor；bull q35 lane 應升級為 no-deploy governance blocker，而不是再追單純 base-stack 權重微調。

## Recommended action

- 即使做 support-aware / discriminative base-stack redesign，current row 仍無法跨過 trade floor；下一輪必須升級為 bull q35 no-deploy governance blocker，禁止再把結構 uplift、單點 bias50 或 base-stack 權重微調當成主 closure。
