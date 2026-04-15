# Q35 Scaling Audit

- generated_at: **2026-04-15 13:22:43.755638**
- overall_verdict: **bias50_formula_may_be_too_harsh**
- structure_scaling_verdict: **q35_structure_caution_not_root_cause**
- scope_applicability: **current_live_q35_lane_active**
- reason: current bias50 已回到 exact-lane p90 內，但 legacy 公式仍可能把它壓成 0 分；需改做 exact-lane 內的保守分段校準，而不是繼續把它視為 broader bull segmentation 問題。
- applicability_note: current live row 仍位於 q35 lane；本輪 q35 scaling / bias50 calibration 結論可直接視為 live governance 主路徑。

## Current live row

- regime/gate/quality: **bull / CAUTION / D**
- structure_bucket: **CAUTION|structure_quality_caution|q35**
- legacy_entry_quality: **0.324** (reason=`entry_quality_below_trade_floor`)
- runtime_entry_quality: **0.3944** (reason=`entry_quality_below_trade_floor`)
- feat_4h_bias50: **2.8698**
- structure_quality: **0.4138**

## Exact lane summary

- rows: **128** | win_rate: **0.9375**
- bias50 distribution: {'min': 1.6545, 'p25': 2.7542, 'p50': 2.9678, 'p75': 4.0562, 'p90': 4.2204, 'p95': 4.2331, 'max': 4.5647, 'mean': 3.131}
- current bias50 percentile in exact lane: **0.3828**
- winner-only bias50 distribution: {'min': 1.6545, 'p25': 2.7178, 'p50': 2.9474, 'p75': 3.4661, 'p90': 4.2088, 'p95': 4.2231, 'max': 4.2354, 'mean': 3.0497}

## Broader bull cohorts

- same_gate_same_quality: rows=**142** | win_rate=**0.8732** | bias50_pct=**0.4225** | dist={'min': -1.1489, 'p25': 2.5728, 'p50': 2.947, 'p75': 3.9692, 'p90': 4.2197, 'p95': 4.2326, 'max': 4.5647, 'mean': 2.8957}
- same_bucket: rows=**129** | win_rate=**0.938** | bias50_pct=**0.3798** | dist={'min': 1.6545, 'p25': 2.7542, 'p50': 2.9678, 'p75': 4.0562, 'p90': 4.2204, 'p95': 4.2331, 'max': 4.5647, 'mean': 3.1378}
- bull_all: rows=**445** | win_rate=**0.6539** | bias50_pct=**0.4787** | dist={'min': -1.1554, 'p25': 2.0471, 'p50': 2.947, 'p75': 4.2817, 'p90': 4.4496, 'p95': 5.2146, 'max': 9.36, 'mean': 2.9704}

## Segmented calibration

- status: **formula_review_required** | mode: **exact_lane_formula_review**
- runtime contract: **piecewise_runtime_active** — piecewise bias50 calibration 已由 predictor / q35 audit 實際套用到 current bull q35 lane；後續 heartbeat 不得再把這題描述成 runtime 尚未吃到新公式。
- exact lane band: **core_normal** (pct=0.3828, Δp90=-1.3506)
- same_gate_same_quality band: **core_normal** (pct=0.4225, Δp90=-1.3499)
- same_bucket band: **core_normal** (pct=0.3798, Δp90=-1.3506)
- bull_all band: **core_normal** (pct=0.4787, Δp90=-1.5798)
- reference cohort: **same_gate_same_quality** / label=同 bull gate + 同 quality lane / pct=0.4225
- note: current bias50 已回到 exact lane p90 內；下一步應做 exact-lane 內的保守 bias50 校準 / 公式檢查，而不是再走 broader bull segmentation。
- runtime preview: applied=**True** | score=**0.2347** | legacy=**0.0** | Δ=**0.2347** | segment=**exact_lane_supported_within_p75**

## Deployment-grade component experiment

- verdict: **runtime_patch_improves_but_still_below_floor**
- baseline -> runtime entry_quality: **0.324 → 0.3944** (Δ=**0.0704**)
- baseline -> runtime layers: **0 → 0**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- runtime gap to floor: **0.1556**
- next patch target: **feat_4h_bias50_formula**

## Counterfactuals

- gate -> ALLOW only: entry_quality **0.324**, layers **0**
- fully relax bias50 penalty: entry_quality **0.624**, layers **1**
- required bias50 cap to cross trade floor: **-1.3665** (current=2.8698)

## Joint component experiment（bias50 runtime patch + feat_4h_dist_swing_low uplift）

- verdict: **joint_component_experiment_improves_but_still_below_floor**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- best scenario: **exact_lane_p75** → entry_quality **0.3954** / layers **0** / gap **0.1546**
- required_bias50_cap_after_best_scenario: **-1.35**
- note: 加入 feat_4h_dist_swing_low uplift 後，entry_quality 有改善，但 exact-supported q35 lane 仍低於 trade floor；下一步需要更強的 bias50 / base-mix closure，而不是只補結構 component。

## Base-mix component experiment（bias50 + pulse + nose）

- verdict: **base_mix_component_experiment_improves_but_still_below_floor**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- best scenario: **winner_triplet_p75** → entry_quality **0.509** / layers **0** / gap **0.041**
- required_bias50_cap_after_best_scenario: **0.543**
- note: bias50 + pulse (+ nose) 的 base-mix uplift 明顯優於只補 structure component，但 current live row 仍未跨過 trade floor；下一輪需升級成 base-stack redesign blocker，而不是再做單點 component 微調。

## Base-stack redesign experiment（support-aware discriminative reweight）

- verdict: **base_stack_redesign_floor_cross_requires_non_discriminative_reweight**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False** | positive_gap=**True**
- rows / wins / losses: **107 / 99 / 8**
- best discriminative candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 1.0, 'feat_ear': 0.0}** → entry_quality **0.3767** / gap **0.1733** / mean_gap **0.2303**
- best floor candidate: weights=**{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 0.0, 'feat_ear': 1.0}** → entry_quality **0.8375** / gap **0.0** / mean_gap **-0.0109**
- unsafe floor-cross candidate: **{'feat_4h_bias50': 0.0, 'feat_nose': 0.0, 'feat_pulse': 0.0, 'feat_ear': 1.0}**
- note: 只有把權重大幅壓向低 discrimination component（主要是 ear）才會讓 current live row 跨過 trade floor；這會破壞 exact-lane 正負樣本分離，不能當成可部署 redesign。

## Recommended action

- base-stack redesign grid search 已證明：只有非 discriminative 的 ear-heavy 權重才會讓 current row 假性跨過 floor；下一輪必須升級為 bull q35 no-deploy governance blocker，停止再把 base-stack 權重微調包裝成可部署 closure。
