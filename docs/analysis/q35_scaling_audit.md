# Q35 Scaling Audit

- generated_at: **2026-05-15 02:09:17.235195**
- overall_verdict: **bias50_formula_may_be_too_harsh**
- structure_scaling_verdict: **q35_structure_caution_not_root_cause**
- scope_applicability: **current_live_q35_lane_active**
- reason: current bias50 已回到 exact-lane p90 內，但 legacy 公式仍可能把它壓成 0 分；需改做 exact-lane 內的保守分段校準，而不是繼續把它視為 broader bull segmentation 問題。
- applicability_note: current live row 仍位於 q35 lane；本輪 q35 scaling / bias50 calibration 結論可直接視為 live governance 主路徑。

## Current live row

- regime/gate/quality: **chop / CAUTION / D**
- structure_bucket: **CAUTION|base_caution_regime_or_bias|q35**
- legacy_entry_quality: **0.5444** (raw_reason=`entry_quality_below_trade_floor`)
- calibration_runtime_entry_quality: **0.5444** (raw_reason=`entry_quality_below_trade_floor`)
- deployed_runtime_entry_quality: **0.5444** (raw_reason=`entry_quality_below_trade_floor`, effective_reason=`unsupported_exact_live_structure_bucket`)
- q35_discriminative_redesign_applied: **False**
- feat_4h_bias50: **0.567**
- structure_quality: **0.4239**

## Exact lane summary

- rows: **904** | win_rate: **0.7799**
- bias50 distribution: {'min': -0.4035, 'p25': 0.8122, 'p50': 1.1354, 'p75': 1.3583, 'p90': 1.6878, 'p95': 1.8231, 'max': 4.4265, 'mean': 1.0991}
- current bias50 percentile in exact lane: **0.1681**
- winner-only bias50 distribution: {'min': -0.4035, 'p25': 0.6447, 'p50': 1.0641, 'p75': 1.3325, 'p90': 1.6071, 'p95': 1.7757, 'max': 3.9157, 'mean': 1.0251}

## Broader bull cohorts

- same_gate_same_quality: rows=**3082** | win_rate=**0.7914** | bias50_pct=**0.2625** | dist={'min': -1.7439, 'p25': 0.5007, 'p50': 1.3159, 'p75': 3.2171, 'p90': 4.0736, 'p95': 4.5615, 'max': 8.0151, 'mean': 1.7705}
- same_bucket: rows=**1439** | win_rate=**0.8402** | bias50_pct=**0.2787** | dist={'min': -5.5588, 'p25': 0.5106, 'p50': 0.9938, 'p75': 1.2846, 'p90': 1.552, 'p95': 1.7469, 'max': 4.4265, 'mean': 0.8288}
- bull_all: rows=**4283** | win_rate=**0.8158** | bias50_pct=**0.3292** | dist={'min': -6.9187, 'p25': 0.1795, 'p50': 1.1607, 'p75': 3.1532, 'p90': 4.1576, 'p95': 4.7078, 'max': 8.0151, 'mean': 1.5111}

## Segmented calibration

- status: **formula_review_required** | mode: **exact_lane_formula_review**
- runtime contract: **piecewise_runtime_not_required** — 本輪 audit 沒有要求 current row 套用 segmented calibration；runtime 可維持既有路徑。
- exact lane band: **core_normal** (pct=0.1681, Δp90=-1.1208)
- same_gate_same_quality band: **core_normal** (pct=0.2625, Δp90=-3.5066)
- same_bucket band: **core_normal** (pct=0.2787, Δp90=-0.985)
- bull_all band: **core_normal** (pct=0.3292, Δp90=-3.5906)
- reference cohort: **same_gate_same_quality** / label=同 bull gate + 同 quality lane / pct=0.2625
- note: current bias50 已回到 exact lane p90 內；下一步應做 exact-lane 內的保守 bias50 校準 / 公式檢查，而不是再走 broader bull segmentation。
- runtime preview: applied=**False** | score=**0.3666** | legacy=**0.3666** | Δ=**0.0** | segment=**None**

## Deployment-grade component experiment

- verdict: **runtime_patch_no_material_improvement**
- baseline -> calibration runtime entry_quality: **0.5444 → 0.5444** (Δ=**0.0**)
- baseline -> deployed runtime entry_quality: **0.5444 → 0.5444** (Δ=**0.0**)
- baseline -> calibration -> deployed layers: **0 → 0 → 0**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- runtime_source: **live_predict_probe** | q35_discriminative_redesign_applied=**False**
- runtime gap to floor: **0.0056**
- next patch target: **feat_4h_bias50_formula**

## Counterfactuals

- gate -> ALLOW only: entry_quality **0.5444**, layers **0**
- fully relax bias50 penalty: entry_quality **0.7344**, layers **2**
- required bias50 cap to cross trade floor: **0.4735** (current=0.567)

## Joint component experiment（bias50 runtime patch + feat_4h_dist_swing_low uplift）

- verdict: **joint_component_experiment_crosses_trade_floor**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**True**
- best scenario: **exact_lane_p75** → entry_quality **0.5615** / layers **1** / gap **0.0**
- required_bias50_cap_after_best_scenario: **0.567**
- note: 在維持 runtime bias50 calibration 的前提下，只把 feat_4h_dist_swing_low 拉回 exact-supported q35 lane 的 support target，就足以跨過 trade floor。

## Exact-supported bias50 component experiment

- verdict: **exact_supported_bias50_component_crosses_trade_floor**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**True** | used_exact_supported_target=**True**
- best scenario: **exact_runtime_p90** → entry_quality **0.5614** / layers **1** / gap **0.0** / target_score **0.4233**
- note: 只把 feat_4h_bias50 拉到 exact-supported / winner-supported runtime 分位，就足以跨過 trade floor。

## Base-mix component experiment（bias50 + pulse + nose）

- verdict: **base_mix_component_experiment_crosses_trade_floor**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**True**
- best scenario: **winner_triplet_p75** → entry_quality **0.5519** / layers **1** / gap **0.0**
- required_bias50_cap_after_best_scenario: **0.567**
- note: 在保留 current q35 結構與 runtime bias50 calibration 的前提下，只把 bias50 + pulse (+ nose) 拉回 exact/winner cohort 的支持分位，就足以跨過 trade floor。

## Base-stack redesign experiment（support-aware discriminative reweight）

- verdict: **base_stack_redesign_discriminative_reweight_crosses_floor_but_execution_blocked**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**False** | positive_gap=**True** | execution_blocked_after_floor_cross=**True**
- rows / wins / losses: **904 / 705 / 199**
- best discriminative candidate: weights=**{'feat_4h_bias50': 0.25, 'feat_nose': 0.0, 'feat_pulse': 0.75, 'feat_ear': 0.0}** → entry_quality **0.5546** / gap **0.0** / mean_gap **0.0429**
- best floor candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 0.0, 'feat_ear': 1.0}** → entry_quality **0.8359** / gap **0.0** / mean_gap **0.0101**
- unsafe floor-cross candidate: **None**
- note: 在 runtime exact lane 內，以正向 discrimination 為約束的 base-stack reweight 已讓 entry_quality 跨過 scoring floor；但 runtime gate/support 仍讓 allowed_layers=0，因此只能視為 score-only research closure，不可視為 deployment closure。

## Recommended action

- discriminative base-stack redesign 只能讓 entry_quality 跨過 scoring floor，runtime gate/support 仍讓 allowed_layers=0；下一輪必須把它治理成 score-only / execution-blocked，不得把 floor-cross 當成 deployment closure。
