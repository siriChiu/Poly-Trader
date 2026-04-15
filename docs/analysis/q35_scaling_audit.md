# Q35 Scaling Audit

- generated_at: **2026-04-15 16:49:37.984252**
- overall_verdict: **bias50_formula_may_be_too_harsh**
- structure_scaling_verdict: **q35_structure_caution_not_root_cause**
- scope_applicability: **current_live_q35_lane_active**
- reason: current bias50 已回到 exact-lane p90 內，但 legacy 公式仍可能把它壓成 0 分；需改做 exact-lane 內的保守分段校準，而不是繼續把它視為 broader bull segmentation 問題。
- applicability_note: current live row 仍位於 q35 lane；本輪 q35 scaling / bias50 calibration 結論可直接視為 live governance 主路徑。

## Current live row

- regime/gate/quality: **bull / CAUTION / D**
- structure_bucket: **CAUTION|structure_quality_caution|q35**
- legacy_entry_quality: **0.3142** (reason=`entry_quality_below_trade_floor`)
- runtime_entry_quality: **0.3142** (reason=`entry_quality_below_trade_floor`)
- feat_4h_bias50: **2.2406**
- structure_quality: **0.3569**

## Exact lane summary

- rows: **134** | win_rate: **0.8955**
- bias50 distribution: {'min': 1.6545, 'p25': 2.7575, 'p50': 2.9796, 'p75': 4.1307, 'p90': 4.2258, 'p95': 4.3513, 'max': 4.9835, 'mean': 3.1948}
- current bias50 percentile in exact lane: **0.1567**
- winner-only bias50 distribution: {'min': 1.6545, 'p25': 2.7178, 'p50': 2.9474, 'p75': 3.4661, 'p90': 4.2088, 'p95': 4.2231, 'max': 4.2354, 'mean': 3.0497}

## Broader bull cohorts

- same_gate_same_quality: rows=**148** | win_rate=**0.8378** | bias50_pct=**0.2162** | dist={'min': -1.1489, 'p25': 2.6226, 'p50': 2.9632, 'p75': 4.0562, 'p90': 4.2239, 'p95': 4.3513, 'max': 4.9835, 'mean': 2.963}
- same_bucket: rows=**135** | win_rate=**0.8963** | bias50_pct=**0.1556** | dist={'min': 1.6545, 'p25': 2.7602, 'p50': 2.9829, 'p75': 4.1066, 'p90': 4.2258, 'p95': 4.3513, 'max': 4.9835, 'mean': 3.2008}
- bull_all: rows=**454** | win_rate=**0.641** | bias50_pct=**0.3899** | dist={'min': -1.1554, 'p25': 2.0517, 'p50': 2.9576, 'p75': 4.2916, 'p90': 4.4726, 'p95': 5.2146, 'max': 9.36, 'mean': 3.0071}

## Segmented calibration

- status: **formula_review_required** | mode: **exact_lane_formula_review**
- runtime contract: **piecewise_runtime_not_required** — 本輪 audit 沒有要求 current row 套用 segmented calibration；runtime 可維持既有路徑。
- exact lane band: **core_normal** (pct=0.1567, Δp90=-1.9852)
- same_gate_same_quality band: **core_normal** (pct=0.2162, Δp90=-1.9833)
- same_bucket band: **core_normal** (pct=0.1556, Δp90=-1.9852)
- bull_all band: **core_normal** (pct=0.3899, Δp90=-2.232)
- reference cohort: **same_gate_same_quality** / label=同 bull gate + 同 quality lane / pct=0.2162
- note: current bias50 已回到 exact lane p90 內；下一步應做 exact-lane 內的保守 bias50 校準 / 公式檢查，而不是再走 broader bull segmentation。
- runtime preview: applied=**False** | score=**0.03187999999999995** | legacy=**0.03187999999999995** | Δ=**0.0** | segment=**None**

## Deployment-grade component experiment

- verdict: **runtime_patch_no_material_improvement**
- baseline -> runtime entry_quality: **0.3142 → 0.3142** (Δ=**0.0**)
- baseline -> runtime layers: **0 → 0**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- runtime gap to floor: **0.2358**
- next patch target: **feat_4h_bias50_formula**

## Counterfactuals

- gate -> ALLOW only: entry_quality **0.3142**, layers **0**
- fully relax bias50 penalty: entry_quality **0.6047**, layers **1**
- required bias50 cap to cross trade floor: **-1.6895** (current=2.2406)

## Joint component experiment（bias50 runtime patch + feat_4h_dist_swing_low uplift）

- verdict: **joint_component_experiment_improves_but_still_below_floor**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- best scenario: **exact_lane_p75** → entry_quality **0.3191** / layers **0** / gap **0.2309**
- required_bias50_cap_after_best_scenario: **-1.608**
- note: 加入 feat_4h_dist_swing_low uplift 後，entry_quality 有改善，但 exact-supported q35 lane 仍低於 trade floor；下一步需要更強的 bias50 / base-mix closure，而不是只補結構 component。

## Exact-supported bias50 component experiment

- verdict: **exact_supported_bias50_component_improves_but_still_below_floor**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False** | used_exact_supported_target=**True**
- best scenario: **exact_runtime_p90** → entry_quality **0.3744** / layers **0** / gap **0.1756** / target_score **0.2325**
- note: 即使只用 exact-supported / winner-supported 的 bias50 runtime 目標做單點 component experiment，entry_quality 仍未跨過 trade floor；這表示 blocker 不再是『少一點點 bias50 support』。

## Base-mix component experiment（bias50 + pulse + nose）

- verdict: **base_mix_component_experiment_improves_but_still_below_floor**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- best scenario: **winner_triplet_p75** → entry_quality **0.4355** / layers **0** / gap **0.1145**
- required_bias50_cap_after_best_scenario: **0.332**
- note: bias50 + pulse (+ nose) 的 base-mix uplift 明顯優於只補 structure component，但 current live row 仍未跨過 trade floor；下一輪需升級成 base-stack redesign blocker，而不是再做單點 component 微調。

## Base-stack redesign experiment（support-aware discriminative reweight）

- verdict: **base_stack_redesign_discriminative_reweight_crosses_trade_floor**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**True** | positive_gap=**True**
- rows / wins / losses: **112 / 98 / 14**
- best discriminative candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 0.45, 'feat_ear': 0.55}** → entry_quality **0.5667** / gap **0.0** / mean_gap **0.0838**
- best floor candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 0.0, 'feat_ear': 1.0}** → entry_quality **0.8337** / gap **0.0** / mean_gap **-0.0065**
- unsafe floor-cross candidate: **{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 0.0, 'feat_ear': 1.0}**
- note: 在 runtime exact lane 內，以正向 discrimination 為約束的 base-stack reweight 已足以讓 current live row 跨過 trade floor。

## Recommended action

- base-mix experiment 已證明 bias50 + pulse (+ nose) uplift 仍未跨過 trade floor；下一輪必須升級成 base-stack redesign blocker，禁止再把結構 uplift 或單點 bias50 當成主 closure。
