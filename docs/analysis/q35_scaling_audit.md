# Q35 Scaling Audit

- generated_at: **2026-05-24 23:17:30.543918**
- overall_verdict: **bias50_formula_may_be_too_harsh**
- structure_scaling_verdict: **q35_structure_caution_not_root_cause**
- scope_applicability: **current_live_q35_lane_active**
- reason: current bias50 已回到 exact-lane p90 內，但 legacy 公式仍可能把它壓成 0 分；需改做 exact-lane 內的保守分段校準，而不是繼續把它視為 broader bull segmentation 問題。
- applicability_note: current live row 仍位於 q35 lane；本輪 q35 scaling / bias50 calibration 結論可直接視為 live governance 主路徑。

## Current live row

- regime/gate/quality: **chop / CAUTION / C**
- structure_bucket: **CAUTION|base_caution_regime_or_bias|q35**
- legacy_entry_quality: **0.5686** (raw_reason=`entry_quality_C_single_layer`)
- calibration_runtime_entry_quality: **0.5686** (raw_reason=`entry_quality_C_single_layer`)
- deployed_runtime_entry_quality: **0.5686** (raw_reason=`entry_quality_C_single_layer`, effective_reason=`under_minimum_exact_live_structure_bucket`)
- q35_discriminative_redesign_applied: **False**
- feat_4h_bias50: **-0.159**
- structure_quality: **0.3885**

## Exact lane summary

- rows: **579** | win_rate: **0.8895**
- bias50 distribution: {'min': -5.5588, 'p25': 0.0596, 'p50': 0.565, 'p75': 0.9822, 'p90': 1.2182, 'p95': 1.4136, 'max': 1.6604, 'mean': 0.3712}
- current bias50 percentile in exact lane: **0.1762**
- winner-only bias50 distribution: {'min': -5.5588, 'p25': 0.2359, 'p50': 0.6245, 'p75': 0.9998, 'p90': 1.2372, 'p95': 1.4262, 'max': 1.6604, 'mean': 0.5027}

## Broader bull cohorts

- same_gate_same_quality: rows=**1322** | win_rate=**0.8253** | bias50_pct=**0.3608** | dist={'min': -6.6008, 'p25': -0.6541, 'p50': 0.4365, 'p75': 1.457, 'p90': 4.4801, 'p95': 4.7505, 'max': 7.5411, 'mean': 0.7375}
- same_bucket: rows=**1569** | win_rate=**0.7839** | bias50_pct=**0.1115** | dist={'min': -5.5588, 'p25': 0.4458, 'p50': 0.9518, 'p75': 1.2656, 'p90': 1.53, 'p95': 1.7352, 'max': 4.4265, 'mean': 0.7211}
- bull_all: rows=**4586** | win_rate=**0.7747** | bias50_pct=**0.1969** | dist={'min': -6.9187, 'p25': 0.0708, 'p50': 1.0844, 'p75': 3.0693, 'p90': 4.0963, 'p95': 4.6734, 'max': 8.0151, 'mean': 1.3637}

## Segmented calibration

- status: **formula_review_required** | mode: **exact_lane_formula_review**
- runtime contract: **piecewise_runtime_not_required** — 本輪 audit 沒有要求 current row 套用 segmented calibration；runtime 可維持既有路徑。
- exact lane band: **core_normal** (pct=0.1762, Δp90=-1.3772)
- same_gate_same_quality band: **core_normal** (pct=0.3608, Δp90=-4.6391)
- same_bucket band: **core_normal** (pct=0.1115, Δp90=-1.689)
- bull_all band: **core_normal** (pct=0.1969, Δp90=-4.2553)
- reference cohort: **same_gate_same_quality** / label=同 bull gate + 同 quality lane / pct=0.3608
- note: current bias50 已回到 exact lane p90 內；下一步應做 exact-lane 內的保守 bias50 校準 / 公式檢查，而不是再走 broader bull segmentation。
- runtime preview: applied=**False** | score=**0.5117999999999999** | legacy=**0.5117999999999999** | Δ=**0.0** | segment=**None**

## Deployment-grade component experiment

- verdict: **runtime_patch_crosses_floor_but_execution_blocked**
- baseline -> calibration runtime entry_quality: **0.5686 → 0.5686** (Δ=**0.0**)
- baseline -> deployed runtime entry_quality: **0.5686 → 0.5686** (Δ=**0.0**)
- baseline -> calibration -> deployed layers: **1 → 1 → 1**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**False**
- runtime_source: **live_predict_probe** | q35_discriminative_redesign_applied=**False**
- runtime gap to floor: **-0.0186**
- next patch target: **feat_4h_bias50_formula**

## Counterfactuals

- gate -> ALLOW only: entry_quality **0.5686**, layers **1**
- fully relax bias50 penalty: entry_quality **0.715**, layers **2**
- required bias50 cap to cross trade floor: **-0.159** (current=-0.159)

## Joint component experiment（bias50 runtime patch + feat_4h_dist_swing_low uplift）

- verdict: **joint_component_experiment_crosses_trade_floor**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**True**
- best scenario: **winner_p75** → entry_quality **0.5764** / layers **1** / gap **0.0**
- required_bias50_cap_after_best_scenario: **-0.159**
- note: 在維持 runtime bias50 calibration 的前提下，只把 feat_4h_dist_swing_low 拉回 exact-supported q35 lane 的 support target，就足以跨過 trade floor。

## Exact-supported bias50 component experiment

- verdict: **exact_supported_bias50_component_crosses_trade_floor**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**True** | used_exact_supported_target=**True**
- best scenario: **exact_runtime_p90** → entry_quality **0.6004** / layers **1** / gap **0.0** / target_score **0.6179**
- note: 只把 feat_4h_bias50 拉到 exact-supported / winner-supported runtime 分位，就足以跨過 trade floor。

## Base-mix component experiment（bias50 + pulse + nose）

- verdict: **base_mix_component_experiment_crosses_trade_floor**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**True**
- best scenario: **winner_triplet_p75** → entry_quality **0.6136** / layers **1** / gap **0.0**
- required_bias50_cap_after_best_scenario: **-0.159**
- note: 在保留 current q35 結構與 runtime bias50 calibration 的前提下，只把 bias50 + pulse (+ nose) 拉回 exact/winner cohort 的支持分位，就足以跨過 trade floor。

## Base-stack redesign experiment（support-aware discriminative reweight）

- verdict: **base_stack_redesign_discriminative_reweight_crosses_floor_but_execution_blocked**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**False** | positive_gap=**True** | execution_blocked_after_floor_cross=**True**
- rows / wins / losses: **579 / 515 / 64**
- best discriminative candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.4, 'feat_pulse': 0.6, 'feat_ear': 0.0}** → entry_quality **0.5555** / gap **0.0** / mean_gap **0.0901**
- best floor candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 0.0, 'feat_ear': 1.0}** → entry_quality **0.8417** / gap **0.0** / mean_gap **0.0136**
- unsafe floor-cross candidate: **None**
- note: 在 runtime exact lane 內，以正向 discrimination 為約束的 base-stack reweight 已讓 entry_quality 跨過 scoring floor；但 runtime gate/support 仍讓 allowed_layers=0，因此只能視為 score-only research closure，不可視為 deployment closure。

## Recommended action

- discriminative base-stack redesign 只能讓 entry_quality 跨過 scoring floor，runtime gate/support 仍讓 allowed_layers=0；下一輪必須把它治理成 score-only / execution-blocked，不得把 floor-cross 當成 deployment closure。
