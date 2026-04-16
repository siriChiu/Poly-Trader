# Q35 Scaling Audit

- generated_at: **2026-04-16 08:35:24.573669**
- overall_verdict: **bias50_formula_may_be_too_harsh**
- structure_scaling_verdict: **q35_structure_caution_not_root_cause**
- scope_applicability: **reference_only_current_bucket_outside_q35**
- reason: current bias50 已回到 exact-lane p90 內，但 legacy 公式仍可能把它壓成 0 分；需改做 exact-lane 內的保守分段校準，而不是繼續把它視為 broader bull segmentation 問題。
- applicability_note: current live row 已不在 q35 lane；q35 scaling audit 只能保留為 reference-only calibration artifact，不得誤寫成當前 live blocker 已落在 q35 formula review。

## Current live row

- regime/gate/quality: **bull / CAUTION / D**
- structure_bucket: **CAUTION|structure_quality_caution|q15**
- legacy_entry_quality: **0.3766** (reason=`entry_quality_below_trade_floor`)
- calibration_runtime_entry_quality: **0.4326** (reason=`entry_quality_below_trade_floor`)
- deployed_runtime_entry_quality: **0.4326** (reason=`entry_quality_below_trade_floor`)
- q35_discriminative_redesign_applied: **False**
- feat_4h_bias50: **2.736**
- structure_quality: **0.3024**

## Exact lane summary

- rows: **8** | win_rate: **0.5**
- bias50 distribution: {'min': 2.0074, 'p25': 2.0306, 'p50': 2.7648, 'p75': 2.8248, 'p90': 3.0559, 'p95': 3.095, 'max': 3.095, 'mean': 2.4812}
- current bias50 percentile in exact lane: **0.5**
- winner-only bias50 distribution: {'min': 2.7648, 'p25': 2.8248, 'p50': 3.0559, 'p75': 3.0559, 'p90': 3.095, 'p95': 3.095, 'max': 3.095, 'mean': 2.9351}

## Broader bull cohorts

- same_gate_same_quality: rows=**308** | win_rate=**0.9123** | bias50_pct=**0.1364** | dist={'min': -1.1489, 'p25': 2.9632, 'p50': 3.2706, 'p75': 3.3792, 'p90': 4.1462, 'p95': 4.2239, 'max': 4.9835, 'mean': 3.1477}
- same_bucket: rows=**8** | win_rate=**0.5** | bias50_pct=**0.5** | dist={'min': 2.0074, 'p25': 2.0306, 'p50': 2.7648, 'p75': 2.8248, 'p90': 3.0559, 'p95': 3.095, 'max': 3.095, 'mean': 2.4812}
- bull_all: rows=**614** | win_rate=**0.7296** | bias50_pct=**0.3176** | dist={'min': -1.1554, 'p25': 2.1166, 'p50': 3.2705, 'p75': 4.2258, 'p90': 4.4136, 'p95': 4.9192, 'max': 9.36, 'mean': 3.0883}

## Segmented calibration

- status: **formula_review_required** | mode: **exact_lane_formula_review**
- runtime contract: **piecewise_runtime_active** — piecewise bias50 calibration 已由 predictor / q35 audit 實際套用到 current bull q35 lane；後續 heartbeat 不得再把這題描述成 runtime 尚未吃到新公式。
- exact lane band: **core_normal** (pct=0.5, Δp90=-0.3199)
- same_gate_same_quality band: **core_normal** (pct=0.1364, Δp90=-1.4102)
- same_bucket band: **core_normal** (pct=0.5, Δp90=-0.3199)
- bull_all band: **core_normal** (pct=0.3176, Δp90=-1.6776)
- reference cohort: **same_gate_same_quality** / label=同 bull gate + 同 quality lane / pct=0.1364
- note: current bias50 已回到 exact lane p90 內；下一步應做 exact-lane 內的保守 bias50 校準 / 公式檢查，而不是再走 broader bull segmentation。
- runtime preview: applied=**True** | score=**0.1867** | legacy=**0.0** | Δ=**0.1867** | segment=**exact_lane_supported_within_p75**

## Deployment-grade component experiment

- verdict: **runtime_patch_improves_but_still_below_floor**
- baseline -> calibration runtime entry_quality: **0.3766 → 0.4326** (Δ=**0.056**)
- baseline -> deployed runtime entry_quality: **0.3766 → 0.4326** (Δ=**0.056**)
- baseline -> calibration -> deployed layers: **0 → 0 → 0**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- runtime_source: **live_predict_probe** | q35_discriminative_redesign_applied=**False**
- runtime gap to floor: **0.1174**
- next patch target: **feat_4h_bias50_formula**

## Counterfactuals

- gate -> ALLOW only: entry_quality **0.3766**, layers **0**
- fully relax bias50 penalty: entry_quality **0.6766**, layers **1**
- required bias50 cap to cross trade floor: **-0.49** (current=2.736)

## Joint component experiment（bias50 runtime patch + feat_4h_dist_swing_low uplift）

- verdict: **joint_component_experiment_improves_but_still_below_floor**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- best scenario: **winner_p50** → entry_quality **0.4587** / layers **0** / gap **0.0913**
- required_bias50_cap_after_best_scenario: **-0.055**
- note: 加入 feat_4h_dist_swing_low uplift 後，entry_quality 有改善，但 exact-supported q35 lane 仍低於 trade floor；下一步需要更強的 bias50 / base-mix closure，而不是只補結構 component。

## Exact-supported bias50 component experiment

- verdict: **exact_supported_bias50_component_improves_but_still_below_floor**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False** | used_exact_supported_target=**True**
- best scenario: **winner_runtime_p50** → entry_quality **0.4783** / layers **0** / gap **0.0717** / target_score **0.3392**
- note: 即使只用 exact-supported / winner-supported 的 bias50 runtime 目標做單點 component experiment，entry_quality 仍未跨過 trade floor；這表示 blocker 不再是『少一點點 bias50 support』。

## Base-mix component experiment（bias50 + pulse + nose）

- verdict: **base_mix_component_experiment_improves_but_still_below_floor**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- best scenario: **exact_lane_triplet_p75** → entry_quality **0.5212** / layers **0** / gap **0.0288**
- required_bias50_cap_after_best_scenario: **0.9865**
- note: bias50 + pulse (+ nose) 的 base-mix uplift 明顯優於只補 structure component，但 current live row 仍未跨過 trade floor；下一輪需升級成 base-stack redesign blocker，而不是再做單點 component 微調。

## Base-stack redesign experiment（support-aware discriminative reweight）

- verdict: **base_stack_redesign_discriminative_reweight_crosses_trade_floor**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**True** | positive_gap=**True**
- rows / wins / losses: **8 / 4 / 4**
- best discriminative candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.95, 'feat_pulse': 0.0, 'feat_ear': 0.05}** → entry_quality **0.5557** / gap **0.0** / mean_gap **0.4405**
- best floor candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 0.0, 'feat_ear': 1.0}** → entry_quality **0.8112** / gap **0.0** / mean_gap **-0.0229**
- unsafe floor-cross candidate: **{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 0.0, 'feat_ear': 1.0}**
- note: 在 runtime exact lane 內，以正向 discrimination 為約束的 base-stack reweight 已足以讓 current live row 跨過 trade floor。

## Recommended action

- current live row 已離開 q35 lane；本輪 q35 audit 僅保留為 reference-only。下一步應優先處理 current bucket 的 exact support / structure component blocker，不得把 q35 bias50 calibration 誤當成可直接放行 current live row 的 patch。
