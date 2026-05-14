# Q35 Scaling Audit

- generated_at: **2026-05-14 17:02:31.701120**
- overall_verdict: **bias50_formula_may_be_too_harsh**
- structure_scaling_verdict: **q35_structure_caution_not_root_cause**
- scope_applicability: **current_live_q35_lane_active**
- reason: current bias50 已回到 exact-lane p90 內，但 legacy 公式仍可能把它壓成 0 分；需改做 exact-lane 內的保守分段校準，而不是繼續把它視為 broader bull segmentation 問題。
- applicability_note: current live row 仍位於 q35 lane；本輪 q35 scaling / bias50 calibration 結論可直接視為 live governance 主路徑。

## Current live row

- regime/gate/quality: **chop / CAUTION / D**
- structure_bucket: **CAUTION|base_caution_regime_or_bias|q35**
- legacy_entry_quality: **0.42** (raw_reason=`entry_quality_below_trade_floor`)
- calibration_runtime_entry_quality: **0.42** (raw_reason=`entry_quality_below_trade_floor`)
- deployed_runtime_entry_quality: **0.42** (raw_reason=`entry_quality_below_trade_floor`, effective_reason=`under_minimum_exact_live_structure_bucket`)
- q35_discriminative_redesign_applied: **False**
- feat_4h_bias50: **1.5669**
- structure_quality: **0.605**

## Exact lane summary

- rows: **882** | win_rate: **0.7789**
- bias50 distribution: {'min': -0.4035, 'p25': 0.7877, 'p50': 1.147, 'p75': 1.3629, 'p90': 1.6898, 'p95': 1.8374, 'max': 4.4265, 'mean': 1.102}
- current bias50 percentile in exact lane: **0.8639**
- winner-only bias50 distribution: {'min': -0.4035, 'p25': 0.6355, 'p50': 1.0729, 'p75': 1.337, 'p90': 1.6072, 'p95': 1.7763, 'max': 3.9157, 'mean': 1.026}

## Broader bull cohorts

- same_gate_same_quality: rows=**3070** | win_rate=**0.7906** | bias50_pct=**0.5651** | dist={'min': -1.7439, 'p25': 0.477, 'p50': 1.3223, 'p75': 3.2221, 'p90': 4.0775, 'p95': 4.563, 'max': 8.0151, 'mean': 1.7665}
- same_bucket: rows=**1416** | win_rate=**0.8404** | bias50_pct=**0.9054** | dist={'min': -5.5588, 'p25': 0.506, 'p50': 0.9965, 'p75': 1.2879, 'p90': 1.5575, 'p95': 1.7536, 'max': 4.4265, 'mean': 0.8263}
- bull_all: rows=**4270** | win_rate=**0.8152** | bias50_pct=**0.6124** | dist={'min': -6.9187, 'p25': 0.1708, 'p50': 1.1667, 'p75': 3.1544, 'p90': 4.1615, 'p95': 4.7082, 'max': 8.0151, 'mean': 1.5076}

## Segmented calibration

- status: **formula_review_required** | mode: **exact_lane_formula_review**
- runtime contract: **piecewise_runtime_not_required** — 本輪 audit 沒有要求 current row 套用 segmented calibration；runtime 可維持既有路徑。
- exact lane band: **elevated_but_within_p90** (pct=0.8639, Δp90=-0.1229)
- same_gate_same_quality band: **warm** (pct=0.5651, Δp90=-2.5106)
- same_bucket band: **borderline_overheat** (pct=0.9054, Δp90=0.0094)
- bull_all band: **warm** (pct=0.6124, Δp90=-2.5946)
- reference cohort: **same_gate_same_quality** / label=同 bull gate + 同 quality lane / pct=0.5651
- note: current bias50 已回到 exact lane p90 內；下一步應做 exact-lane 內的保守 bias50 校準 / 公式檢查，而不是再走 broader bull segmentation。
- runtime preview: applied=**False** | score=**0.16662** | legacy=**0.16662** | Δ=**0.0** | segment=**None**

## Deployment-grade component experiment

- verdict: **runtime_patch_no_material_improvement**
- baseline -> calibration runtime entry_quality: **0.42 → 0.42** (Δ=**0.0**)
- baseline -> deployed runtime entry_quality: **0.42 → 0.42** (Δ=**0.0**)
- baseline -> calibration -> deployed layers: **0 → 0 → 0**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- runtime_source: **live_predict_probe** | q35_discriminative_redesign_applied=**False**
- runtime gap to floor: **0.13**
- next patch target: **feat_4h_bias50_formula**

## Counterfactuals

- gate -> ALLOW only: entry_quality **0.42**, layers **0**
- fully relax bias50 penalty: entry_quality **0.67**, layers **1**
- required bias50 cap to cross trade floor: **-0.5995** (current=1.5669)

## Joint component experiment（bias50 runtime patch + feat_4h_dist_swing_low uplift）

- verdict: **joint_component_experiment_improves_but_still_below_floor**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- best scenario: **exact_lane_p75** → entry_quality **0.429** / layers **0** / gap **0.121**
- required_bias50_cap_after_best_scenario: **-0.4495**
- note: 加入 feat_4h_dist_swing_low uplift 後，entry_quality 有改善，但 exact-supported q35 lane 仍低於 trade floor；下一步需要更強的 bias50 / base-mix closure，而不是只補結構 component。

## Exact-supported bias50 component experiment

- verdict: **exact_supported_bias50_component_improves_but_still_below_floor**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False** | used_exact_supported_target=**True**
- best scenario: **exact_runtime_p90** → entry_quality **0.4974** / layers **0** / gap **0.0526** / target_score **0.4245**
- note: 即使只用 exact-supported / winner-supported 的 bias50 runtime 目標做單點 component experiment，entry_quality 仍未跨過 trade floor；這表示 blocker 不再是『少一點點 bias50 support』。

## Base-mix component experiment（bias50 + pulse + nose）

- verdict: **base_mix_component_experiment_crosses_trade_floor**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**True**
- best scenario: **winner_triplet_p75** → entry_quality **0.566** / layers **1** / gap **0.0**
- required_bias50_cap_after_best_scenario: **0.6355**
- note: 在保留 current q35 結構與 runtime bias50 calibration 的前提下，只把 bias50 + pulse (+ nose) 拉回 exact/winner cohort 的支持分位，就足以跨過 trade floor。

## Base-stack redesign experiment（support-aware discriminative reweight）

- verdict: **base_stack_redesign_discriminative_reweight_crosses_floor_but_execution_blocked**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**False** | positive_gap=**True** | execution_blocked_after_floor_cross=**True**
- rows / wins / losses: **882 / 687 / 195**
- best discriminative candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 1.0, 'feat_ear': 0.0}** → entry_quality **0.5631** / gap **0.0** / mean_gap **0.0394**
- best floor candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 0.0, 'feat_ear': 1.0}** → entry_quality **0.804** / gap **0.0** / mean_gap **0.009**
- unsafe floor-cross candidate: **None**
- note: 在 runtime exact lane 內，以正向 discrimination 為約束的 base-stack reweight 已讓 entry_quality 跨過 scoring floor；但 runtime gate/support 仍讓 allowed_layers=0，因此只能視為 score-only research closure，不可視為 deployment closure。

## Recommended action

- discriminative base-stack redesign 只能讓 entry_quality 跨過 scoring floor，runtime gate/support 仍讓 allowed_layers=0；下一輪必須把它治理成 score-only / execution-blocked，不得把 floor-cross 當成 deployment closure。
