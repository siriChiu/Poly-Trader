# Q35 Scaling Audit

- generated_at: **2026-05-01 09:07:56.961607**
- overall_verdict: **bias50_formula_may_be_too_harsh**
- structure_scaling_verdict: **q35_structure_caution_not_root_cause**
- scope_applicability: **current_live_q35_lane_active**
- reason: current bias50 已回到 exact-lane p90 內，但 legacy 公式仍可能把它壓成 0 分；需改做 exact-lane 內的保守分段校準，而不是繼續把它視為 broader bull segmentation 問題。
- applicability_note: current live row 仍位於 q35 lane；本輪 q35 scaling / bias50 calibration 結論可直接視為 live governance 主路徑。

## Current live row

- regime/gate/quality: **chop / CAUTION / D**
- structure_bucket: **CAUTION|base_caution_regime_or_bias|q35**
- legacy_entry_quality: **0.5053** (raw_reason=`entry_quality_below_trade_floor`)
- calibration_runtime_entry_quality: **0.5053** (raw_reason=`entry_quality_below_trade_floor`)
- deployed_runtime_entry_quality: **0.5053** (raw_reason=`entry_quality_below_trade_floor`, effective_reason=`under_minimum_exact_live_structure_bucket`)
- q35_discriminative_redesign_applied: **False**
- feat_4h_bias50: **0.091**
- structure_quality: **0.4513**

## Exact lane summary

- rows: **861** | win_rate: **0.7735**
- bias50 distribution: {'min': -0.4035, 'p25': 0.8169, 'p50': 1.1492, 'p75': 1.3777, 'p90': 1.6954, 'p95': 1.8399, 'max': 4.4265, 'mean': 1.1167}
- current bias50 percentile in exact lane: **0.0534**
- winner-only bias50 distribution: {'min': -0.4035, 'p25': 0.6536, 'p50': 1.0761, 'p75': 1.3543, 'p90': 1.6144, 'p95': 1.7809, 'max': 3.9157, 'mean': 1.0426}

## Broader bull cohorts

- same_gate_same_quality: rows=**2874** | win_rate=**0.8038** | bias50_pct=**0.1141** | dist={'min': -1.7439, 'p25': 0.7119, 'p50': 1.4353, 'p75': 3.2825, 'p90': 4.1006, 'p95': 4.6111, 'max': 8.0151, 'mean': 1.965}
- same_bucket: rows=**1394** | win_rate=**0.8379** | bias50_pct=**0.1119** | dist={'min': -5.5588, 'p25': 0.5133, 'p50': 0.9971, 'p75': 1.2913, 'p90': 1.5597, 'p95': 1.7562, 'max': 4.4265, 'mean': 0.8318}
- bull_all: rows=**4023** | win_rate=**0.8282** | bias50_pct=**0.176** | dist={'min': -6.9187, 'p25': 0.3707, 'p50': 1.2572, 'p75': 3.2302, 'p90': 4.2249, 'p95': 4.7285, 'max': 8.0151, 'mean': 1.6731}

## Segmented calibration

- status: **formula_review_required** | mode: **exact_lane_formula_review**
- runtime contract: **piecewise_runtime_not_required** — 本輪 audit 沒有要求 current row 套用 segmented calibration；runtime 可維持既有路徑。
- exact lane band: **core_normal** (pct=0.0534, Δp90=-1.6044)
- same_gate_same_quality band: **core_normal** (pct=0.1141, Δp90=-4.0096)
- same_bucket band: **core_normal** (pct=0.1119, Δp90=-1.4687)
- bull_all band: **core_normal** (pct=0.176, Δp90=-4.1339)
- reference cohort: **same_gate_same_quality** / label=同 bull gate + 同 quality lane / pct=0.1141
- note: current bias50 已回到 exact lane p90 內；下一步應做 exact-lane 內的保守 bias50 校準 / 公式檢查，而不是再走 broader bull segmentation。
- runtime preview: applied=**False** | score=**0.46179999999999993** | legacy=**0.46179999999999993** | Δ=**0.0** | segment=**None**

## Deployment-grade component experiment

- verdict: **runtime_patch_no_material_improvement**
- baseline -> calibration runtime entry_quality: **0.5053 → 0.5053** (Δ=**0.0**)
- baseline -> deployed runtime entry_quality: **0.5053 → 0.5053** (Δ=**0.0**)
- baseline -> calibration -> deployed layers: **0 → 0 → 0**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- runtime_source: **live_predict_probe** | q35_discriminative_redesign_applied=**False**
- runtime gap to floor: **0.0447**
- next patch target: **feat_4h_bias50_formula**

## Counterfactuals

- gate -> ALLOW only: entry_quality **0.5053**, layers **0**
- fully relax bias50 penalty: entry_quality **0.6668**, layers **1**
- required bias50 cap to cross trade floor: **-0.654** (current=0.091)

## Joint component experiment（bias50 runtime patch + feat_4h_dist_swing_low uplift）

- verdict: **joint_component_experiment_improves_but_still_below_floor**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- best scenario: **exact_lane_p75** → entry_quality **0.5207** / layers **0** / gap **0.0293**
- required_bias50_cap_after_best_scenario: **-0.3975**
- note: 加入 feat_4h_dist_swing_low uplift 後，entry_quality 有改善，但 exact-supported q35 lane 仍低於 trade floor；下一步需要更強的 bias50 / base-mix closure，而不是只補結構 component。

## Exact-supported bias50 component experiment

- verdict: **exact_supported_bias50_component_no_higher_supported_target**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False** | used_exact_supported_target=**False**
- best scenario: **None** → entry_quality **None** / layers **None** / gap **None** / target_score **None**
- note: runtime exact-supported lane 裡找不到比 current bias50 score 更高、且仍屬 exact-supported / winner-supported 的單點目標；本輪無法形成更強的 bias50 component uplift。

## Base-mix component experiment（bias50 + pulse + nose）

- verdict: **base_mix_component_experiment_crosses_trade_floor**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**True**
- best scenario: **exact_lane_triplet_p75** → entry_quality **0.5664** / layers **1** / gap **0.0**
- required_bias50_cap_after_best_scenario: **0.091**
- note: 在保留 current q35 結構與 runtime bias50 calibration 的前提下，只把 bias50 + pulse (+ nose) 拉回 exact/winner cohort 的支持分位，就足以跨過 trade floor。

## Base-stack redesign experiment（support-aware discriminative reweight）

- verdict: **base_stack_redesign_discriminative_reweight_crosses_trade_floor**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**True** | positive_gap=**True** | execution_blocked_after_floor_cross=**False**
- rows / wins / losses: **861 / 666 / 195**
- best discriminative candidate: weights=**{'feat_4h_bias50': 0.7, 'feat_nose': 0.0, 'feat_pulse': 0.0, 'feat_ear': 0.3}** → entry_quality **0.5546** / gap **0.0** / mean_gap **0.0423**
- best floor candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 0.0, 'feat_ear': 1.0}** → entry_quality **0.7771** / gap **0.0** / mean_gap **0.0101**
- unsafe floor-cross candidate: **None**
- note: 在 runtime exact lane 內，以正向 discrimination 為約束的 base-stack reweight 已足以讓 current live row 跨過 trade floor。

## Recommended action

- 維持 q35=CAUTION；把本輪焦點放在 bias50 正規化是否應改成分段/分位數縮放，只有當 current bias50 落在 exact-lane 常見區間時才放寬。
