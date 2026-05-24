# Q35 Scaling Audit

- generated_at: **2026-05-24 11:37:11.707733**
- overall_verdict: **bias50_formula_may_be_too_harsh**
- structure_scaling_verdict: **q35_structure_caution_not_root_cause**
- scope_applicability: **current_live_q35_lane_active**
- reason: current bias50 已回到 exact-lane p90 內，但 legacy 公式仍可能把它壓成 0 分；需改做 exact-lane 內的保守分段校準，而不是繼續把它視為 broader bull segmentation 問題。
- applicability_note: current live row 仍位於 q35 lane；本輪 q35 scaling / bias50 calibration 結論可直接視為 live governance 主路徑。

## Current live row

- regime/gate/quality: **chop / CAUTION / C**
- structure_bucket: **CAUTION|base_caution_regime_or_bias|q35**
- legacy_entry_quality: **0.5813** (raw_reason=`entry_quality_C_single_layer`)
- calibration_runtime_entry_quality: **0.5813** (raw_reason=`entry_quality_C_single_layer`)
- deployed_runtime_entry_quality: **0.5813** (raw_reason=`entry_quality_C_single_layer`, effective_reason=`unsupported_exact_live_structure_bucket`)
- q35_discriminative_redesign_applied: **False**
- feat_4h_bias50: **0.1921**
- structure_quality: **0.5512**

## Exact lane summary

- rows: **575** | win_rate: **0.8957**
- bias50 distribution: {'min': -5.5588, 'p25': 0.0828, 'p50': 0.5825, 'p75': 0.9822, 'p90': 1.2216, 'p95': 1.4136, 'max': 1.6604, 'mean': 0.3764}
- current bias50 percentile in exact lane: **0.287**
- winner-only bias50 distribution: {'min': -5.5588, 'p25': 0.2359, 'p50': 0.6245, 'p75': 0.9998, 'p90': 1.2372, 'p95': 1.4262, 'max': 1.6604, 'mean': 0.5027}

## Broader bull cohorts

- same_gate_same_quality: rows=**1318** | win_rate=**0.8278** | bias50_pct=**0.4347** | dist={'min': -6.6008, 'p25': -0.6553, 'p50': 0.4441, 'p75': 1.458, 'p90': 4.4801, 'p95': 4.7505, 'max': 7.5411, 'mean': 0.7409}
- same_bucket: rows=**1562** | win_rate=**0.7875** | bias50_pct=**0.1805** | dist={'min': -5.5588, 'p25': 0.4479, 'p50': 0.9529, 'p75': 1.2659, 'p90': 1.533, 'p95': 1.7352, 'max': 4.4265, 'mean': 0.7255}
- bull_all: rows=**4579** | win_rate=**0.7759** | bias50_pct=**0.2931** | dist={'min': -6.9187, 'p25': 0.073, 'p50': 1.0869, 'p75': 3.0699, 'p90': 4.0978, 'p95': 4.6734, 'max': 8.0151, 'mean': 1.3662}

## Segmented calibration

- status: **formula_review_required** | mode: **exact_lane_formula_review**
- runtime contract: **piecewise_runtime_not_required** — 本輪 audit 沒有要求 current row 套用 segmented calibration；runtime 可維持既有路徑。
- exact lane band: **core_normal** (pct=0.287, Δp90=-1.0295)
- same_gate_same_quality band: **core_normal** (pct=0.4347, Δp90=-4.288)
- same_bucket band: **core_normal** (pct=0.1805, Δp90=-1.3409)
- bull_all band: **core_normal** (pct=0.2931, Δp90=-3.9057)
- reference cohort: **same_gate_same_quality** / label=同 bull gate + 同 quality lane / pct=0.4347
- note: current bias50 已回到 exact lane p90 內；下一步應做 exact-lane 內的保守 bias50 校準 / 公式檢查，而不是再走 broader bull segmentation。
- runtime preview: applied=**False** | score=**0.44158** | legacy=**0.44158** | Δ=**0.0** | segment=**None**

## Deployment-grade component experiment

- verdict: **runtime_patch_crosses_floor_but_execution_blocked**
- baseline -> calibration runtime entry_quality: **0.5813 → 0.5813** (Δ=**0.0**)
- baseline -> deployed runtime entry_quality: **0.5813 → 0.5813** (Δ=**0.0**)
- baseline -> calibration -> deployed layers: **1 → 1 → 1**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**False**
- runtime_source: **live_predict_probe** | q35_discriminative_redesign_applied=**False**
- runtime gap to floor: **-0.0313**
- next patch target: **feat_4h_bias50_formula**

## Counterfactuals

- gate -> ALLOW only: entry_quality **0.5813**, layers **1**
- fully relax bias50 penalty: entry_quality **0.7489**, layers **2**
- required bias50 cap to cross trade floor: **0.192** (current=0.1921)

## Joint component experiment（bias50 runtime patch + feat_4h_dist_swing_low uplift）

- verdict: **joint_component_experiment_crosses_trade_floor**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**True**
- best scenario: **winner_p75** → entry_quality **0.5854** / layers **1** / gap **0.0**
- required_bias50_cap_after_best_scenario: **0.192**
- note: 在維持 runtime bias50 calibration 的前提下，只把 feat_4h_dist_swing_low 拉回 exact-supported q35 lane 的 support target，就足以跨過 trade floor。

## Exact-supported bias50 component experiment

- verdict: **exact_supported_bias50_component_crosses_trade_floor**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**True** | used_exact_supported_target=**True**
- best scenario: **exact_runtime_p90** → entry_quality **0.6345** / layers **1** / gap **0.0** / target_score **0.6186**
- note: 只把 feat_4h_bias50 拉到 exact-supported / winner-supported runtime 分位，就足以跨過 trade floor。

## Base-mix component experiment（bias50 + pulse + nose）

- verdict: **base_mix_component_experiment_crosses_trade_floor**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**True**
- best scenario: **exact_lane_triplet_p75** → entry_quality **0.6456** / layers **1** / gap **0.0**
- required_bias50_cap_after_best_scenario: **0.083**
- note: 在保留 current q35 結構與 runtime bias50 calibration 的前提下，只把 bias50 + pulse (+ nose) 拉回 exact/winner cohort 的支持分位，就足以跨過 trade floor。

## Base-stack redesign experiment（support-aware discriminative reweight）

- verdict: **base_stack_redesign_discriminative_reweight_crosses_floor_but_execution_blocked**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**False** | positive_gap=**True** | execution_blocked_after_floor_cross=**True**
- rows / wins / losses: **575 / 515 / 60**
- best discriminative candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.45, 'feat_pulse': 0.55, 'feat_ear': 0.0}** → entry_quality **0.5642** / gap **0.0** / mean_gap **0.0908**
- best floor candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 0.0, 'feat_ear': 1.0}** → entry_quality **0.8716** / gap **0.0** / mean_gap **0.0063**
- unsafe floor-cross candidate: **None**
- note: 在 runtime exact lane 內，以正向 discrimination 為約束的 base-stack reweight 已讓 entry_quality 跨過 scoring floor；但 runtime gate/support 仍讓 allowed_layers=0，因此只能視為 score-only research closure，不可視為 deployment closure。

## Recommended action

- discriminative base-stack redesign 只能讓 entry_quality 跨過 scoring floor，runtime gate/support 仍讓 allowed_layers=0；下一輪必須把它治理成 score-only / execution-blocked，不得把 floor-cross 當成 deployment closure。
