# Q35 Scaling Audit

- generated_at: **2026-05-20 14:30:17.378943**
- overall_verdict: **bias50_formula_may_be_too_harsh**
- structure_scaling_verdict: **q35_structure_caution_not_root_cause**
- scope_applicability: **current_live_q35_lane_active**
- reason: current bias50 已回到 exact-lane p90 內，但 legacy 公式仍可能把它壓成 0 分；需改做 exact-lane 內的保守分段校準，而不是繼續把它視為 broader bull segmentation 問題。
- applicability_note: current live row 仍位於 q35 lane；本輪 q35 scaling / bias50 calibration 結論可直接視為 live governance 主路徑。

## Current live row

- regime/gate/quality: **chop / CAUTION / C**
- structure_bucket: **CAUTION|base_caution_regime_or_bias|q35**
- legacy_entry_quality: **0.6709** (raw_reason=`entry_quality_C_single_layer`)
- calibration_runtime_entry_quality: **0.6709** (raw_reason=`entry_quality_C_single_layer`)
- deployed_runtime_entry_quality: **0.6709** (raw_reason=`entry_quality_C_single_layer`, effective_reason=`unsupported_exact_live_structure_bucket`)
- q35_discriminative_redesign_applied: **False**
- feat_4h_bias50: **-1.5719**
- structure_quality: **0.3676**

## Exact lane summary

- rows: **511** | win_rate: **0.9706**
- bias50 distribution: {'min': -5.5588, 'p25': 0.3188, 'p50': 0.6721, 'p75': 1.0241, 'p90': 1.2568, 'p95': 1.4262, 'max': 1.6604, 'mean': 0.5782}
- current bias50 percentile in exact lane: **0.0157**
- winner-only bias50 distribution: {'min': -5.5588, 'p25': 0.3152, 'p50': 0.6598, 'p75': 1.0147, 'p90': 1.2547, 'p95': 1.4412, 'max': 1.6604, 'mean': 0.5846}

## Broader bull cohorts

- same_gate_same_quality: rows=**1161** | win_rate=**0.8932** | bias50_pct=**0.0431** | dist={'min': -6.6008, 'p25': -0.3648, 'p50': 0.6366, 'p75': 2.4842, 'p90': 4.6126, 'p95': 4.8007, 'max': 7.5411, 'mean': 1.0016}
- same_bucket: rows=**1479** | win_rate=**0.8174** | bias50_pct=**0.0237** | dist={'min': -5.5588, 'p25': 0.5168, 'p50': 0.9912, 'p75': 1.2819, 'p90': 1.551, 'p95': 1.7458, 'max': 4.4265, 'mean': 0.8303}
- bull_all: rows=**4342** | win_rate=**0.8047** | bias50_pct=**0.0223** | dist={'min': -6.9187, 'p25': 0.1774, 'p50': 1.1508, 'p75': 3.1304, 'p90': 4.1466, 'p95': 4.7009, 'max': 8.0151, 'mean': 1.4988}

## Segmented calibration

- status: **formula_review_required** | mode: **exact_lane_formula_review**
- runtime contract: **piecewise_runtime_not_required** — 本輪 audit 沒有要求 current row 套用 segmented calibration；runtime 可維持既有路徑。
- exact lane band: **core_normal** (pct=0.0157, Δp90=-2.8287)
- same_gate_same_quality band: **core_normal** (pct=0.0431, Δp90=-6.1845)
- same_bucket band: **core_normal** (pct=0.0237, Δp90=-3.1229)
- bull_all band: **core_normal** (pct=0.0223, Δp90=-5.7185)
- reference cohort: **same_gate_same_quality** / label=同 bull gate + 同 quality lane / pct=0.0431
- note: current bias50 已回到 exact lane p90 內；下一步應做 exact-lane 內的保守 bias50 校準 / 公式檢查，而不是再走 broader bull segmentation。
- runtime preview: applied=**False** | score=**0.79438** | legacy=**0.79438** | Δ=**0.0** | segment=**None**

## Deployment-grade component experiment

- verdict: **runtime_patch_crosses_floor_but_execution_blocked**
- baseline -> calibration runtime entry_quality: **0.6709 → 0.6709** (Δ=**0.0**)
- baseline -> deployed runtime entry_quality: **0.6709 → 0.6709** (Δ=**0.0**)
- baseline -> calibration -> deployed layers: **1 → 1 → 1**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**False**
- runtime_source: **live_predict_probe** | q35_discriminative_redesign_applied=**False**
- runtime gap to floor: **-0.1209**
- next patch target: **feat_4h_bias50_formula**

## Counterfactuals

- gate -> ALLOW only: entry_quality **0.6709**, layers **1**
- fully relax bias50 penalty: entry_quality **0.7326**, layers **2**
- required bias50 cap to cross trade floor: **-1.572** (current=-1.5719)

## Joint component experiment（bias50 runtime patch + feat_4h_dist_swing_low uplift）

- verdict: **joint_component_experiment_crosses_trade_floor**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**True**
- best scenario: **exact_lane_p75** → entry_quality **0.6924** / layers **2** / gap **0.0**
- required_bias50_cap_after_best_scenario: **-1.572**
- note: 在維持 runtime bias50 calibration 的前提下，只把 feat_4h_dist_swing_low 拉回 exact-supported q35 lane 的 support target，就足以跨過 trade floor。

## Exact-supported bias50 component experiment

- verdict: **exact_supported_bias50_component_no_higher_supported_target**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False** | used_exact_supported_target=**False**
- best scenario: **None** → entry_quality **None** / layers **None** / gap **None** / target_score **None**
- note: runtime exact-supported lane 裡找不到比 current bias50 score 更高、且仍屬 exact-supported / winner-supported 的單點目標；本輪無法形成更強的 bias50 component uplift。

## Base-mix component experiment（bias50 + pulse + nose）

- verdict: **base_mix_component_experiment_crosses_trade_floor**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**True**
- best scenario: **exact_lane_triplet_p75** → entry_quality **0.7024** / layers **2** / gap **0.0**
- required_bias50_cap_after_best_scenario: **-1.572**
- note: 在保留 current q35 結構與 runtime bias50 calibration 的前提下，只把 bias50 + pulse (+ nose) 拉回 exact/winner cohort 的支持分位，就足以跨過 trade floor。

## Base-stack redesign experiment（support-aware discriminative reweight）

- verdict: **base_stack_redesign_discriminative_reweight_crosses_floor_but_execution_blocked**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**False** | positive_gap=**True** | execution_blocked_after_floor_cross=**True**
- rows / wins / losses: **511 / 496 / 15**
- best discriminative candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 1.0, 'feat_ear': 0.0}** → entry_quality **0.7027** / gap **0.0** / mean_gap **0.0071**
- best floor candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 0.0, 'feat_ear': 1.0}** → entry_quality **0.8309** / gap **0.0** / mean_gap **0.0028**
- unsafe floor-cross candidate: **None**
- note: 在 runtime exact lane 內，以正向 discrimination 為約束的 base-stack reweight 已讓 entry_quality 跨過 scoring floor；但 runtime gate/support 仍讓 allowed_layers=0，因此只能視為 score-only research closure，不可視為 deployment closure。

## Recommended action

- discriminative base-stack redesign 只能讓 entry_quality 跨過 scoring floor，runtime gate/support 仍讓 allowed_layers=0；下一輪必須把它治理成 score-only / execution-blocked，不得把 floor-cross 當成 deployment closure。
