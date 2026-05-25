# Q35 Scaling Audit

- generated_at: **2026-05-25 00:10:56.242670**
- overall_verdict: **bias50_formula_may_be_too_harsh**
- structure_scaling_verdict: **q35_structure_caution_not_root_cause**
- scope_applicability: **current_live_q35_lane_active**
- reason: current bias50 已回到 exact-lane p90 內，但 legacy 公式仍可能把它壓成 0 分；需改做 exact-lane 內的保守分段校準，而不是繼續把它視為 broader bull segmentation 問題。
- applicability_note: current live row 仍位於 q35 lane；本輪 q35 scaling / bias50 calibration 結論可直接視為 live governance 主路徑。

## Current live row

- regime/gate/quality: **chop / CAUTION / D**
- structure_bucket: **CAUTION|base_caution_regime_or_bias|q35**
- legacy_entry_quality: **0.4671** (raw_reason=`entry_quality_below_trade_floor`)
- calibration_runtime_entry_quality: **0.4671** (raw_reason=`entry_quality_below_trade_floor`)
- deployed_runtime_entry_quality: **0.4671** (raw_reason=`entry_quality_below_trade_floor`, effective_reason=`under_minimum_exact_live_structure_bucket`)
- q35_discriminative_redesign_applied: **False**
- feat_4h_bias50: **0.2346**
- structure_quality: **0.4326**

## Exact lane summary

- rows: **963** | win_rate: **0.7362**
- bias50 distribution: {'min': -1.2312, 'p25': 0.6815, 'p50': 1.1118, 'p75': 1.3417, 'p90': 1.6507, 'p95': 1.8129, 'max': 4.4265, 'mean': 1.0518}
- current bias50 percentile in exact lane: **0.1049**
- winner-only bias50 distribution: {'min': -1.1316, 'p25': 0.6382, 'p50': 1.0639, 'p75': 1.3278, 'p90': 1.6068, 'p95': 1.7757, 'max': 3.9157, 'mean': 1.0148}

## Broader bull cohorts

- same_gate_same_quality: rows=**3220** | win_rate=**0.7596** | bias50_pct=**0.2357** | dist={'min': -1.9, 'p25': 0.3472, 'p50': 1.287, 'p75': 3.1735, 'p90': 4.0361, 'p95': 4.5297, 'max': 8.0151, 'mean': 1.6852}
- same_bucket: rows=**1572** | win_rate=**0.7844** | bias50_pct=**0.1978** | dist={'min': -5.5588, 'p25': 0.4441, 'p50': 0.9514, 'p75': 1.2656, 'p90': 1.53, 'p95': 1.7263, 'max': 4.4265, 'mean': 0.7188}
- bull_all: rows=**4589** | win_rate=**0.7749** | bias50_pct=**0.304** | dist={'min': -6.9187, 'p25': 0.0694, 'p50': 1.0844, 'p75': 3.0669, 'p90': 4.0963, 'p95': 4.6734, 'max': 8.0151, 'mean': 1.3625}

## Segmented calibration

- status: **formula_review_required** | mode: **exact_lane_formula_review**
- runtime contract: **piecewise_runtime_not_required** — 本輪 audit 沒有要求 current row 套用 segmented calibration；runtime 可維持既有路徑。
- exact lane band: **core_normal** (pct=0.1049, Δp90=-1.4161)
- same_gate_same_quality band: **core_normal** (pct=0.2357, Δp90=-3.8015)
- same_bucket band: **core_normal** (pct=0.1978, Δp90=-1.2954)
- bull_all band: **core_normal** (pct=0.304, Δp90=-3.8617)
- reference cohort: **same_gate_same_quality** / label=同 bull gate + 同 quality lane / pct=0.2357
- note: current bias50 已回到 exact lane p90 內；下一步應做 exact-lane 內的保守 bias50 校準 / 公式檢查，而不是再走 broader bull segmentation。
- runtime preview: applied=**False** | score=**0.43308** | legacy=**0.43308** | Δ=**0.0** | segment=**None**

## Deployment-grade component experiment

- verdict: **runtime_patch_no_material_improvement**
- baseline -> calibration runtime entry_quality: **0.4671 → 0.4671** (Δ=**0.0**)
- baseline -> deployed runtime entry_quality: **0.4671 → 0.4671** (Δ=**0.0**)
- baseline -> calibration -> deployed layers: **0 → 0 → 0**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- runtime_source: **live_predict_probe** | q35_discriminative_redesign_applied=**False**
- runtime gap to floor: **0.0829**
- next patch target: **feat_4h_bias50_formula**

## Counterfactuals

- gate -> ALLOW only: entry_quality **0.4671**, layers **0**
- fully relax bias50 penalty: entry_quality **0.6372**, layers **1**
- required bias50 cap to cross trade floor: **-1.147** (current=0.2346)

## Joint component experiment（bias50 runtime patch + feat_4h_dist_swing_low uplift）

- verdict: **joint_component_experiment_improves_but_still_below_floor**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- best scenario: **exact_lane_p75** → entry_quality **0.476** / layers **0** / gap **0.074**
- required_bias50_cap_after_best_scenario: **-0.999**
- note: 加入 feat_4h_dist_swing_low uplift 後，entry_quality 有改善，但 exact-supported q35 lane 仍低於 trade floor；下一步需要更強的 bias50 / base-mix closure，而不是只補結構 component。

## Exact-supported bias50 component experiment

- verdict: **exact_supported_bias50_component_improves_but_still_below_floor**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False** | used_exact_supported_target=**True**
- best scenario: **exact_runtime_p90** → entry_quality **0.4685** / layers **0** / gap **0.0815** / target_score **0.4376**
- note: 即使只用 exact-supported / winner-supported 的 bias50 runtime 目標做單點 component experiment，entry_quality 仍未跨過 trade floor；這表示 blocker 不再是『少一點點 bias50 support』。

## Base-mix component experiment（bias50 + pulse + nose）

- verdict: **base_mix_component_experiment_crosses_trade_floor**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**True**
- best scenario: **exact_lane_triplet_p75** → entry_quality **0.5589** / layers **1** / gap **0.0**
- required_bias50_cap_after_best_scenario: **0.2345**
- note: 在保留 current q35 結構與 runtime bias50 calibration 的前提下，只把 bias50 + pulse (+ nose) 拉回 exact/winner cohort 的支持分位，就足以跨過 trade floor。

## Base-stack redesign experiment（support-aware discriminative reweight）

- verdict: **base_stack_redesign_discriminative_reweight_crosses_floor_but_execution_blocked**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**False** | positive_gap=**True** | execution_blocked_after_floor_cross=**True**
- rows / wins / losses: **963 / 709 / 254**
- best discriminative candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 0.65, 'feat_ear': 0.35}** → entry_quality **0.5605** / gap **0.0** / mean_gap **0.0473**
- best floor candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 0.0, 'feat_ear': 1.0}** → entry_quality **0.8216** / gap **0.0** / mean_gap **0.0186**
- unsafe floor-cross candidate: **None**
- note: 在 runtime exact lane 內，以正向 discrimination 為約束的 base-stack reweight 已讓 entry_quality 跨過 scoring floor；但 runtime gate/support 仍讓 allowed_layers=0，因此只能視為 score-only research closure，不可視為 deployment closure。

## Recommended action

- discriminative base-stack redesign 只能讓 entry_quality 跨過 scoring floor，runtime gate/support 仍讓 allowed_layers=0；下一輪必須把它治理成 score-only / execution-blocked，不得把 floor-cross 當成 deployment closure。
