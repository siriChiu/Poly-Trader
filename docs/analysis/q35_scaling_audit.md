# Q35 Scaling Audit

- generated_at: **2026-05-25 05:39:50.094781**
- overall_verdict: **bias50_formula_may_be_too_harsh**
- structure_scaling_verdict: **q35_structure_caution_not_root_cause**
- scope_applicability: **current_live_q35_lane_active**
- reason: current bias50 已回到 exact-lane p90 內，但 legacy 公式仍可能把它壓成 0 分；需改做 exact-lane 內的保守分段校準，而不是繼續把它視為 broader bull segmentation 問題。
- applicability_note: current live row 仍位於 q35 lane；本輪 q35 scaling / bias50 calibration 結論可直接視為 live governance 主路徑。

## Current live row

- regime/gate/quality: **chop / CAUTION / D**
- structure_bucket: **CAUTION|base_caution_regime_or_bias|q35**
- legacy_entry_quality: **0.5051** (raw_reason=`entry_quality_below_trade_floor`)
- calibration_runtime_entry_quality: **0.5051** (raw_reason=`entry_quality_below_trade_floor`)
- deployed_runtime_entry_quality: **0.5051** (raw_reason=`entry_quality_below_trade_floor`, effective_reason=`under_minimum_exact_live_structure_bucket`)
- q35_discriminative_redesign_applied: **False**
- feat_4h_bias50: **0.5809**
- structure_quality: **0.477**

## Exact lane summary

- rows: **969** | win_rate: **0.7379**
- bias50 distribution: {'min': -1.2312, 'p25': 0.669, 'p50': 1.1111, 'p75': 1.3382, 'p90': 1.6456, 'p95': 1.8129, 'max': 4.4265, 'mean': 1.0423}
- current bias50 percentile in exact lane: **0.2043**
- winner-only bias50 distribution: {'min': -1.1316, 'p25': 0.6283, 'p50': 1.0626, 'p75': 1.3264, 'p90': 1.6068, 'p95': 1.7747, 'max': 3.9157, 'mean': 1.0024}

## Broader bull cohorts

- same_gate_same_quality: rows=**3226** | win_rate=**0.7601** | bias50_pct=**0.2908** | dist={'min': -1.9, 'p25': 0.3305, 'p50': 1.2851, 'p75': 3.1673, 'p90': 4.0359, 'p95': 4.5297, 'max': 8.0151, 'mean': 1.6812}
- same_bucket: rows=**1594** | win_rate=**0.7873** | bias50_pct=**0.3356** | dist={'min': -5.5588, 'p25': 0.4008, 'p50': 0.9384, 'p75': 1.2578, 'p90': 1.5259, 'p95': 1.7218, 'max': 4.4265, 'mean': 0.7021}
- bull_all: rows=**4611** | win_rate=**0.776** | bias50_pct=**0.3732** | dist={'min': -6.9187, 'p25': 0.0602, 'p50': 1.0792, 'p75': 3.0643, 'p90': 4.094, 'p95': 4.6724, 'max': 8.0151, 'mean': 1.3536}

## Segmented calibration

- status: **formula_review_required** | mode: **exact_lane_formula_review**
- runtime contract: **piecewise_runtime_not_required** — 本輪 audit 沒有要求 current row 套用 segmented calibration；runtime 可維持既有路徑。
- exact lane band: **core_normal** (pct=0.2043, Δp90=-1.0647)
- same_gate_same_quality band: **core_normal** (pct=0.2908, Δp90=-3.455)
- same_bucket band: **core_normal** (pct=0.3356, Δp90=-0.945)
- bull_all band: **core_normal** (pct=0.3732, Δp90=-3.5131)
- reference cohort: **same_gate_same_quality** / label=同 bull gate + 同 quality lane / pct=0.2908
- note: current bias50 已回到 exact lane p90 內；下一步應做 exact-lane 內的保守 bias50 校準 / 公式檢查，而不是再走 broader bull segmentation。
- runtime preview: applied=**False** | score=**0.36382** | legacy=**0.36382** | Δ=**0.0** | segment=**None**

## Deployment-grade component experiment

- verdict: **runtime_patch_no_material_improvement**
- baseline -> calibration runtime entry_quality: **0.5051 → 0.5051** (Δ=**0.0**)
- baseline -> deployed runtime entry_quality: **0.5051 → 0.5051** (Δ=**0.0**)
- baseline -> calibration -> deployed layers: **0 → 0 → 0**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- runtime_source: **live_predict_probe** | q35_discriminative_redesign_applied=**False**
- runtime gap to floor: **0.0449**
- next patch target: **feat_4h_bias50_formula**

## Counterfactuals

- gate -> ALLOW only: entry_quality **0.5051**, layers **0**
- fully relax bias50 penalty: entry_quality **0.696**, layers **2**
- required bias50 cap to cross trade floor: **-0.1675** (current=0.5809)

## Joint component experiment（bias50 runtime patch + feat_4h_dist_swing_low uplift）

- verdict: **joint_component_experiment_improves_but_still_below_floor**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- best scenario: **exact_lane_p75** → entry_quality **0.5114** / layers **0** / gap **0.0386**
- required_bias50_cap_after_best_scenario: **-0.0625**
- note: 加入 feat_4h_dist_swing_low uplift 後，entry_quality 有改善，但 exact-supported q35 lane 仍低於 trade floor；下一步需要更強的 bias50 / base-mix closure，而不是只補結構 component。

## Exact-supported bias50 component experiment

- verdict: **exact_supported_bias50_component_improves_but_still_below_floor**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False** | used_exact_supported_target=**True**
- best scenario: **exact_runtime_p90** → entry_quality **0.5291** / layers **0** / gap **0.0209** / target_score **0.4436**
- note: 即使只用 exact-supported / winner-supported 的 bias50 runtime 目標做單點 component experiment，entry_quality 仍未跨過 trade floor；這表示 blocker 不再是『少一點點 bias50 support』。

## Base-mix component experiment（bias50 + pulse + nose）

- verdict: **base_mix_component_experiment_improves_but_still_below_floor**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- best scenario: **exact_lane_triplet_p75** → entry_quality **0.5488** / layers **0** / gap **0.0012**
- required_bias50_cap_after_best_scenario: **0.561**
- note: bias50 + pulse (+ nose) 的 base-mix uplift 明顯優於只補 structure component，但 current live row 仍未跨過 trade floor；下一輪需升級成 base-stack redesign blocker，而不是再做單點 component 微調。

## Base-stack redesign experiment（support-aware discriminative reweight）

- verdict: **base_stack_redesign_discriminative_reweight_crosses_floor_but_execution_blocked**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**False** | positive_gap=**True** | execution_blocked_after_floor_cross=**True**
- rows / wins / losses: **969 / 715 / 254**
- best discriminative candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 0.95, 'feat_ear': 0.05}** → entry_quality **0.5625** / gap **0.0** / mean_gap **0.0588**
- best floor candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 0.0, 'feat_ear': 1.0}** → entry_quality **0.8327** / gap **0.0** / mean_gap **0.0183**
- unsafe floor-cross candidate: **None**
- note: 在 runtime exact lane 內，以正向 discrimination 為約束的 base-stack reweight 已讓 entry_quality 跨過 scoring floor；但 runtime gate/support 仍讓 allowed_layers=0，因此只能視為 score-only research closure，不可視為 deployment closure。

## Recommended action

- discriminative base-stack redesign 只能讓 entry_quality 跨過 scoring floor，runtime gate/support 仍讓 allowed_layers=0；下一輪必須把它治理成 score-only / execution-blocked，不得把 floor-cross 當成 deployment closure。
