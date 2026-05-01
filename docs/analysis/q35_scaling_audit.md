# Q35 Scaling Audit

- generated_at: **2026-05-01 21:55:39.040809**
- overall_verdict: **bias50_formula_may_be_too_harsh**
- structure_scaling_verdict: **q35_structure_caution_not_root_cause**
- scope_applicability: **current_live_q35_lane_active**
- reason: current bias50 已回到 exact-lane p90 內，但 legacy 公式仍可能把它壓成 0 分；需改做 exact-lane 內的保守分段校準，而不是繼續把它視為 broader bull segmentation 問題。
- applicability_note: current live row 仍位於 q35 lane；本輪 q35 scaling / bias50 calibration 結論可直接視為 live governance 主路徑。

## Current live row

- regime/gate/quality: **chop / CAUTION / D**
- structure_bucket: **CAUTION|base_caution_regime_or_bias|q35**
- legacy_entry_quality: **0.4376** (raw_reason=`entry_quality_below_trade_floor`)
- calibration_runtime_entry_quality: **0.4376** (raw_reason=`entry_quality_below_trade_floor`)
- deployed_runtime_entry_quality: **0.4376** (raw_reason=`entry_quality_below_trade_floor`, effective_reason=`under_minimum_exact_live_structure_bucket`)
- q35_discriminative_redesign_applied: **False**
- feat_4h_bias50: **1.1472**
- structure_quality: **0.4678**

## Exact lane summary

- rows: **865** | win_rate: **0.7746**
- bias50 distribution: {'min': -0.4035, 'p25': 0.8069, 'p50': 1.147, 'p75': 1.3743, 'p90': 1.6954, 'p95': 1.8399, 'max': 4.4265, 'mean': 1.112}
- current bias50 percentile in exact lane: **0.5006**
- winner-only bias50 distribution: {'min': -0.4035, 'p25': 0.6447, 'p50': 1.0729, 'p75': 1.3542, 'p90': 1.6144, 'p95': 1.7809, 'max': 3.9157, 'mean': 1.037}

## Broader bull cohorts

- same_gate_same_quality: rows=**2878** | win_rate=**0.804** | bias50_pct=**0.3819** | dist={'min': -1.7439, 'p25': 0.706, 'p50': 1.4349, 'p75': 3.2805, 'p90': 4.0997, 'p95': 4.6111, 'max': 8.0151, 'mean': 1.9624}
- same_bucket: rows=**1398** | win_rate=**0.8383** | bias50_pct=**0.6345** | dist={'min': -5.5588, 'p25': 0.5105, 'p50': 0.9965, 'p75': 1.2909, 'p90': 1.5581, 'p95': 1.7562, 'max': 4.4265, 'mean': 0.8297}
- bull_all: rows=**4027** | win_rate=**0.8284** | bias50_pct=**0.4614** | dist={'min': -6.9187, 'p25': 0.3653, 'p50': 1.2568, 'p75': 3.2302, 'p90': 4.2246, 'p95': 4.7285, 'max': 8.0151, 'mean': 1.6716}

## Segmented calibration

- status: **formula_review_required** | mode: **exact_lane_formula_review**
- runtime contract: **piecewise_runtime_not_required** — 本輪 audit 沒有要求 current row 套用 segmented calibration；runtime 可維持既有路徑。
- exact lane band: **warm** (pct=0.5006, Δp90=-0.5482)
- same_gate_same_quality band: **core_normal** (pct=0.3819, Δp90=-2.9525)
- same_bucket band: **warm** (pct=0.6345, Δp90=-0.4109)
- bull_all band: **core_normal** (pct=0.4614, Δp90=-3.0774)
- reference cohort: **same_gate_same_quality** / label=同 bull gate + 同 quality lane / pct=0.3819
- note: current bias50 已回到 exact lane p90 內；下一步應做 exact-lane 內的保守 bias50 校準 / 公式檢查，而不是再走 broader bull segmentation。
- runtime preview: applied=**False** | score=**0.25056** | legacy=**0.25056** | Δ=**0.0** | segment=**None**

## Deployment-grade component experiment

- verdict: **runtime_patch_no_material_improvement**
- baseline -> calibration runtime entry_quality: **0.4376 → 0.4376** (Δ=**0.0**)
- baseline -> deployed runtime entry_quality: **0.4376 → 0.4376** (Δ=**0.0**)
- baseline -> calibration -> deployed layers: **0 → 0 → 0**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- runtime_source: **live_predict_probe** | q35_discriminative_redesign_applied=**False**
- runtime gap to floor: **0.1124**
- next patch target: **feat_4h_bias50_formula**

## Counterfactuals

- gate -> ALLOW only: entry_quality **0.4376**, layers **0**
- fully relax bias50 penalty: entry_quality **0.6625**, layers **1**
- required bias50 cap to cross trade floor: **-0.7265** (current=1.1472)

## Joint component experiment（bias50 runtime patch + feat_4h_dist_swing_low uplift）

- verdict: **joint_component_experiment_improves_but_still_below_floor**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- best scenario: **exact_lane_p75** → entry_quality **0.4444** / layers **0** / gap **0.1056**
- required_bias50_cap_after_best_scenario: **-0.613**
- note: 加入 feat_4h_dist_swing_low uplift 後，entry_quality 有改善，但 exact-supported q35 lane 仍低於 trade floor；下一步需要更強的 bias50 / base-mix closure，而不是只補結構 component。

## Exact-supported bias50 component experiment

- verdict: **exact_supported_bias50_component_improves_but_still_below_floor**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False** | used_exact_supported_target=**True**
- best scenario: **exact_runtime_p90** → entry_quality **0.4876** / layers **0** / gap **0.0624** / target_score **0.4172**
- note: 即使只用 exact-supported / winner-supported 的 bias50 runtime 目標做單點 component experiment，entry_quality 仍未跨過 trade floor；這表示 blocker 不再是『少一點點 bias50 support』。

## Base-mix component experiment（bias50 + pulse + nose）

- verdict: **base_mix_component_experiment_improves_but_still_below_floor**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- best scenario: **winner_triplet_p75** → entry_quality **0.5326** / layers **0** / gap **0.0174**
- required_bias50_cap_after_best_scenario: **0.3545**
- note: bias50 + pulse (+ nose) 的 base-mix uplift 明顯優於只補 structure component，但 current live row 仍未跨過 trade floor；下一輪需升級成 base-stack redesign blocker，而不是再做單點 component 微調。

## Base-stack redesign experiment（support-aware discriminative reweight）

- verdict: **base_stack_redesign_discriminative_reweight_crosses_trade_floor**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**True** | positive_gap=**True** | execution_blocked_after_floor_cross=**False**
- rows / wins / losses: **865 / 670 / 195**
- best discriminative candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 0.75, 'feat_ear': 0.25}** → entry_quality **0.5502** / gap **0.0** / mean_gap **0.0348**
- best floor candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 0.0, 'feat_ear': 1.0}** → entry_quality **0.776** / gap **0.0** / mean_gap **0.01**
- unsafe floor-cross candidate: **None**
- note: 在 runtime exact lane 內，以正向 discrimination 為約束的 base-stack reweight 已足以讓 current live row 跨過 trade floor。

## Recommended action

- base-mix experiment 已證明 bias50 + pulse (+ nose) uplift 仍未跨過 trade floor；下一輪必須升級成 base-stack redesign blocker，禁止再把結構 uplift 或單點 bias50 當成主 closure。
