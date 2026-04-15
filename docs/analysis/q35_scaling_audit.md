# Q35 Scaling Audit

- generated_at: **2026-04-15 17:35:54.349131**
- overall_verdict: **bias50_formula_may_be_too_harsh**
- structure_scaling_verdict: **q35_structure_caution_not_root_cause**
- scope_applicability: **current_live_q35_lane_active**
- reason: current bias50 已回到 exact-lane p90 內，但 legacy 公式仍可能把它壓成 0 分；需改做 exact-lane 內的保守分段校準，而不是繼續把它視為 broader bull segmentation 問題。
- applicability_note: current live row 仍位於 q35 lane；本輪 q35 scaling / bias50 calibration 結論可直接視為 live governance 主路徑。

## Current live row

- regime/gate/quality: **bull / CAUTION / D**
- structure_bucket: **CAUTION|structure_quality_caution|q35**
- legacy_entry_quality: **0.3411** (reason=`entry_quality_below_trade_floor`)
- calibration_runtime_entry_quality: **0.4115** (reason=`entry_quality_below_trade_floor`)
- deployed_runtime_entry_quality: **0.4115** (reason=`entry_quality_below_trade_floor`)
- q35_discriminative_redesign_applied: **False**
- feat_4h_bias50: **2.4919**
- structure_quality: **0.3958**

## Exact lane summary

- rows: **135** | win_rate: **0.8889**
- bias50 distribution: {'min': 1.6545, 'p25': 2.7602, 'p50': 2.9829, 'p75': 4.1066, 'p90': 4.2258, 'p95': 4.3513, 'max': 4.9835, 'mean': 3.2015}
- current bias50 percentile in exact lane: **0.1704**
- winner-only bias50 distribution: {'min': 1.6545, 'p25': 2.7178, 'p50': 2.9474, 'p75': 3.4661, 'p90': 4.2088, 'p95': 4.2231, 'max': 4.2354, 'mean': 3.0497}

## Broader bull cohorts

- same_gate_same_quality: rows=**149** | win_rate=**0.8322** | bias50_pct=**0.2282** | dist={'min': -1.1489, 'p25': 2.6226, 'p50': 2.9632, 'p75': 4.082, 'p90': 4.2239, 'p95': 4.3513, 'max': 4.9835, 'mean': 2.9706}
- same_bucket: rows=**136** | win_rate=**0.8897** | bias50_pct=**0.1691** | dist={'min': 1.6545, 'p25': 2.7602, 'p50': 2.989, 'p75': 4.1066, 'p90': 4.2258, 'p95': 4.3513, 'max': 4.9835, 'mean': 3.2075}
- bull_all: rows=**455** | win_rate=**0.6396** | bias50_pct=**0.4088** | dist={'min': -1.1554, 'p25': 2.0523, 'p50': 2.9632, 'p75': 4.2895, 'p90': 4.4726, 'p95': 5.2146, 'max': 9.36, 'mean': 3.0095}

## Segmented calibration

- status: **formula_review_required** | mode: **exact_lane_formula_review**
- runtime contract: **piecewise_runtime_active** — piecewise bias50 calibration 已由 predictor / q35 audit 實際套用到 current bull q35 lane；後續 heartbeat 不得再把這題描述成 runtime 尚未吃到新公式。
- exact lane band: **core_normal** (pct=0.1704, Δp90=-1.7339)
- same_gate_same_quality band: **core_normal** (pct=0.2282, Δp90=-1.732)
- same_bucket band: **core_normal** (pct=0.1691, Δp90=-1.7339)
- bull_all band: **core_normal** (pct=0.4088, Δp90=-1.9807)
- reference cohort: **same_gate_same_quality** / label=同 bull gate + 同 quality lane / pct=0.2282
- note: current bias50 已回到 exact lane p90 內；下一步應做 exact-lane 內的保守 bias50 校準 / 公式檢查，而不是再走 broader bull segmentation。
- runtime preview: applied=**True** | score=**0.2346** | legacy=**0.0** | Δ=**0.2346** | segment=**exact_lane_core_band_below_p25**

## Deployment-grade component experiment

- verdict: **runtime_patch_improves_but_still_below_floor**
- baseline -> calibration runtime entry_quality: **0.3411 → 0.4115** (Δ=**0.0704**)
- baseline -> deployed runtime entry_quality: **0.3411 → 0.4115** (Δ=**0.0704**)
- baseline -> calibration -> deployed layers: **0 → 0 → 0**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- runtime_source: **live_predict_probe** | q35_discriminative_redesign_applied=**False**
- runtime gap to floor: **0.1385**
- next patch target: **feat_4h_bias50_formula**

## Counterfactuals

- gate -> ALLOW only: entry_quality **0.3411**, layers **0**
- fully relax bias50 penalty: entry_quality **0.6411**, layers **1**
- required bias50 cap to cross trade floor: **-1.0815** (current=2.4919)

## Joint component experiment（bias50 runtime patch + feat_4h_dist_swing_low uplift）

- verdict: **joint_component_experiment_improves_but_still_below_floor**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- best scenario: **exact_lane_p75** → entry_quality **0.4144** / layers **0** / gap **0.1356**
- required_bias50_cap_after_best_scenario: **-1.033**
- note: 加入 feat_4h_dist_swing_low uplift 後，entry_quality 有改善，但 exact-supported q35 lane 仍低於 trade floor；下一步需要更強的 bias50 / base-mix closure，而不是只補結構 component。

## Exact-supported bias50 component experiment

- verdict: **exact_supported_bias50_component_no_higher_supported_target**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False** | used_exact_supported_target=**False**
- best scenario: **None** → entry_quality **None** / layers **None** / gap **None** / target_score **None**
- note: runtime exact-supported lane 裡找不到比 current bias50 score 更高、且仍屬 exact-supported / winner-supported 的單點目標；本輪無法形成更強的 bias50 component uplift。

## Base-mix component experiment（bias50 + pulse + nose）

- verdict: **base_mix_component_experiment_improves_but_still_below_floor**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- best scenario: **winner_triplet_p75** → entry_quality **0.5038** / layers **0** / gap **0.0462**
- required_bias50_cap_after_best_scenario: **0.457**
- note: bias50 + pulse (+ nose) 的 base-mix uplift 明顯優於只補 structure component，但 current live row 仍未跨過 trade floor；下一輪需升級成 base-stack redesign blocker，而不是再做單點 component 微調。

## Base-stack redesign experiment（support-aware discriminative reweight）

- verdict: **base_stack_redesign_discriminative_reweight_crosses_trade_floor**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**True** | positive_gap=**True**
- rows / wins / losses: **114 / 99 / 15**
- best discriminative candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 0.6, 'feat_ear': 0.4}** → entry_quality **0.5645** / gap **0.0** / mean_gap **0.1141**
- best floor candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 0.0, 'feat_ear': 1.0}** → entry_quality **0.8283** / gap **0.0** / mean_gap **-0.0068**
- unsafe floor-cross candidate: **{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 0.0, 'feat_ear': 1.0}**
- note: 在 runtime exact lane 內，以正向 discrimination 為約束的 base-stack reweight 已足以讓 current live row 跨過 trade floor。

## Recommended action

- base-mix experiment 已證明 bias50 + pulse (+ nose) uplift 仍未跨過 trade floor；下一輪必須升級成 base-stack redesign blocker，禁止再把結構 uplift 或單點 bias50 當成主 closure。
