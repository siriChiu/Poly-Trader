# Q35 Scaling Audit

- generated_at: **2026-05-21 08:28:07.498365**
- overall_verdict: **bias50_formula_may_be_too_harsh**
- structure_scaling_verdict: **q35_structure_caution_not_root_cause**
- scope_applicability: **current_live_q35_lane_active**
- reason: current bias50 已回到 exact-lane p90 內，但 legacy 公式仍可能把它壓成 0 分；需改做 exact-lane 內的保守分段校準，而不是繼續把它視為 broader bull segmentation 問題。
- applicability_note: current live row 仍位於 q35 lane；本輪 q35 scaling / bias50 calibration 結論可直接視為 live governance 主路徑。

## Current live row

- regime/gate/quality: **chop / CAUTION / C**
- structure_bucket: **CAUTION|base_caution_regime_or_bias|q35**
- legacy_entry_quality: **0.631** (raw_reason=`entry_quality_C_single_layer`)
- calibration_runtime_entry_quality: **0.631** (raw_reason=`entry_quality_C_single_layer`)
- deployed_runtime_entry_quality: **0.631** (raw_reason=`entry_quality_C_single_layer`, effective_reason=`under_minimum_exact_live_structure_bucket`)
- q35_discriminative_redesign_applied: **False**
- feat_4h_bias50: **-0.5045**
- structure_quality: **0.3708**

## Exact lane summary

- rows: **521** | win_rate: **0.9712**
- bias50 distribution: {'min': -5.5588, 'p25': 0.2586, 'p50': 0.6581, 'p75': 1.0196, 'p90': 1.2547, 'p95': 1.4262, 'max': 1.6604, 'mean': 0.5329}
- current bias50 percentile in exact lane: **0.0345**
- winner-only bias50 distribution: {'min': -5.5588, 'p25': 0.2584, 'p50': 0.6369, 'p75': 1.0085, 'p90': 1.2372, 'p95': 1.4412, 'max': 1.6604, 'mean': 0.5378}

## Broader bull cohorts

- same_gate_same_quality: rows=**1174** | win_rate=**0.8944** | bias50_pct=**0.253** | dist={'min': -6.6008, 'p25': -0.5603, 'p50': 0.6161, 'p75': 2.2944, 'p90': 4.6088, 'p95': 4.8005, 'max': 7.5411, 'mean': 0.9705}
- same_bucket: rows=**1489** | win_rate=**0.8187** | bias50_pct=**0.0302** | dist={'min': -5.5588, 'p25': 0.51, 'p50': 0.9869, 'p75': 1.2798, 'p90': 1.5493, 'p95': 1.7458, 'max': 4.4265, 'mean': 0.8128}
- bull_all: rows=**4356** | win_rate=**0.8053** | bias50_pct=**0.1297** | dist={'min': -6.9187, 'p25': 0.1709, 'p50': 1.1487, 'p75': 3.1252, 'p90': 4.1456, 'p95': 4.6967, 'max': 8.0151, 'mean': 1.4881}

## Segmented calibration

- status: **formula_review_required** | mode: **exact_lane_formula_review**
- runtime contract: **piecewise_runtime_not_required** — 本輪 audit 沒有要求 current row 套用 segmented calibration；runtime 可維持既有路徑。
- exact lane band: **core_normal** (pct=0.0345, Δp90=-1.7592)
- same_gate_same_quality band: **core_normal** (pct=0.253, Δp90=-5.1133)
- same_bucket band: **core_normal** (pct=0.0302, Δp90=-2.0538)
- bull_all band: **core_normal** (pct=0.1297, Δp90=-4.6501)
- reference cohort: **same_gate_same_quality** / label=同 bull gate + 同 quality lane / pct=0.253
- note: current bias50 已回到 exact lane p90 內；下一步應做 exact-lane 內的保守 bias50 校準 / 公式檢查，而不是再走 broader bull segmentation。
- runtime preview: applied=**False** | score=**0.5809** | legacy=**0.5809** | Δ=**0.0** | segment=**None**

## Deployment-grade component experiment

- verdict: **runtime_patch_crosses_floor_but_execution_blocked**
- baseline -> calibration runtime entry_quality: **0.631 → 0.631** (Δ=**0.0**)
- baseline -> deployed runtime entry_quality: **0.631 → 0.631** (Δ=**0.0**)
- baseline -> calibration -> deployed layers: **1 → 1 → 1**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**False**
- runtime_source: **live_predict_probe** | q35_discriminative_redesign_applied=**False**
- runtime gap to floor: **-0.081**
- next patch target: **feat_4h_bias50_formula**

## Counterfactuals

- gate -> ALLOW only: entry_quality **0.631**, layers **1**
- fully relax bias50 penalty: entry_quality **0.7567**, layers **2**
- required bias50 cap to cross trade floor: **-0.5045** (current=-0.5045)

## Joint component experiment（bias50 runtime patch + feat_4h_dist_swing_low uplift）

- verdict: **joint_component_experiment_crosses_trade_floor**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**True**
- best scenario: **exact_lane_p75** → entry_quality **0.6467** / layers **1** / gap **0.0**
- required_bias50_cap_after_best_scenario: **-0.5045**
- note: 在維持 runtime bias50 calibration 的前提下，只把 feat_4h_dist_swing_low 拉回 exact-supported q35 lane 的 support target，就足以跨過 trade floor。

## Exact-supported bias50 component experiment

- verdict: **exact_supported_bias50_component_no_higher_supported_target**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False** | used_exact_supported_target=**False**
- best scenario: **None** → entry_quality **None** / layers **None** / gap **None** / target_score **None**
- note: runtime exact-supported lane 裡找不到比 current bias50 score 更高、且仍屬 exact-supported / winner-supported 的單點目標；本輪無法形成更強的 bias50 component uplift。

## Base-mix component experiment（bias50 + pulse + nose）

- verdict: **base_mix_component_experiment_crosses_trade_floor**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**True**
- best scenario: **exact_lane_triplet_p75** → entry_quality **0.6604** / layers **1** / gap **0.0**
- required_bias50_cap_after_best_scenario: **-0.5045**
- note: 在保留 current q35 結構與 runtime bias50 calibration 的前提下，只把 bias50 + pulse (+ nose) 拉回 exact/winner cohort 的支持分位，就足以跨過 trade floor。

## Base-stack redesign experiment（support-aware discriminative reweight）

- verdict: **base_stack_redesign_discriminative_reweight_crosses_floor_but_execution_blocked**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**False** | positive_gap=**True** | execution_blocked_after_floor_cross=**True**
- rows / wins / losses: **521 / 506 / 15**
- best discriminative candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 1.0, 'feat_ear': 0.0}** → entry_quality **0.7787** / gap **0.0** / mean_gap **0.0035**
- best floor candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 0.0, 'feat_ear': 1.0}** → entry_quality **0.8416** / gap **0.0** / mean_gap **0.0024**
- unsafe floor-cross candidate: **None**
- note: 在 runtime exact lane 內，以正向 discrimination 為約束的 base-stack reweight 已讓 entry_quality 跨過 scoring floor；但 runtime gate/support 仍讓 allowed_layers=0，因此只能視為 score-only research closure，不可視為 deployment closure。

## Recommended action

- discriminative base-stack redesign 只能讓 entry_quality 跨過 scoring floor，runtime gate/support 仍讓 allowed_layers=0；下一輪必須把它治理成 score-only / execution-blocked，不得把 floor-cross 當成 deployment closure。
