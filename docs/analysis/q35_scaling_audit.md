# Q35 Scaling Audit

- generated_at: **2026-04-15 12:48:25.477859**
- overall_verdict: **bias50_formula_may_be_too_harsh**
- structure_scaling_verdict: **q35_structure_caution_not_root_cause**
- scope_applicability: **current_live_q35_lane_active**
- reason: current bias50 已回到 exact-lane p90 內，但 legacy 公式仍可能把它壓成 0 分；需改做 exact-lane 內的保守分段校準，而不是繼續把它視為 broader bull segmentation 問題。
- applicability_note: current live row 仍位於 q35 lane；本輪 q35 scaling / bias50 calibration 結論可直接視為 live governance 主路徑。

## Current live row

- regime/gate/quality: **bull / CAUTION / D**
- structure_bucket: **CAUTION|structure_quality_caution|q35**
- legacy_entry_quality: **0.3031** (reason=`entry_quality_below_trade_floor`)
- runtime_entry_quality: **0.3725** (reason=`entry_quality_below_trade_floor`)
- feat_4h_bias50: **2.9419**
- structure_quality: **0.4246**

## Exact lane summary

- rows: **128** | win_rate: **0.9375**
- bias50 distribution: {'min': 1.6545, 'p25': 2.7542, 'p50': 2.9678, 'p75': 4.0562, 'p90': 4.2204, 'p95': 4.2331, 'max': 4.5647, 'mean': 3.131}
- current bias50 percentile in exact lane: **0.4453**
- winner-only bias50 distribution: {'min': 1.6545, 'p25': 2.7178, 'p50': 2.9474, 'p75': 3.4661, 'p90': 4.2088, 'p95': 4.2231, 'max': 4.2354, 'mean': 3.0497}

## Broader bull cohorts

- same_gate_same_quality: rows=**142** | win_rate=**0.8732** | bias50_pct=**0.4789** | dist={'min': -1.1489, 'p25': 2.5728, 'p50': 2.947, 'p75': 3.9692, 'p90': 4.2197, 'p95': 4.2326, 'max': 4.5647, 'mean': 2.8957}
- same_bucket: rows=**129** | win_rate=**0.938** | bias50_pct=**0.4419** | dist={'min': 1.6545, 'p25': 2.7542, 'p50': 2.9678, 'p75': 4.0562, 'p90': 4.2204, 'p95': 4.2331, 'max': 4.5647, 'mean': 3.1378}
- bull_all: rows=**443** | win_rate=**0.6569** | bias50_pct=**0.4989** | dist={'min': -1.1554, 'p25': 2.0452, 'p50': 2.9431, 'p75': 4.2816, 'p90': 4.4404, 'p95': 5.1867, 'max': 9.36, 'mean': 2.9601}

## Segmented calibration

- status: **formula_review_required** | mode: **exact_lane_formula_review**
- runtime contract: **piecewise_runtime_active** — piecewise bias50 calibration 已由 predictor / q35 audit 實際套用到 current bull q35 lane；後續 heartbeat 不得再把這題描述成 runtime 尚未吃到新公式。
- exact lane band: **core_normal** (pct=0.4453, Δp90=-1.2785)
- same_gate_same_quality band: **core_normal** (pct=0.4789, Δp90=-1.2778)
- same_bucket band: **core_normal** (pct=0.4419, Δp90=-1.2785)
- bull_all band: **core_normal** (pct=0.4989, Δp90=-1.4985)
- reference cohort: **same_gate_same_quality** / label=同 bull gate + 同 quality lane / pct=0.4789
- note: current bias50 已回到 exact lane p90 內；下一步應做 exact-lane 內的保守 bias50 校準 / 公式檢查，而不是再走 broader bull segmentation。
- runtime preview: applied=**True** | score=**0.2314** | legacy=**0.0** | Δ=**0.2314** | segment=**exact_lane_supported_within_p75**

## Deployment-grade component experiment

- verdict: **runtime_patch_improves_but_still_below_floor**
- baseline -> runtime entry_quality: **0.3031 → 0.3725** (Δ=**0.0694**)
- baseline -> runtime layers: **0 → 0**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- runtime gap to floor: **0.1775**
- next patch target: **feat_4h_bias50_formula**

## Counterfactuals

- gate -> ALLOW only: entry_quality **0.3031**, layers **0**
- fully relax bias50 penalty: entry_quality **0.6031**, layers **1**
- required bias50 cap to cross trade floor: **-1.715** (current=2.9419)

## Joint component experiment（bias50 runtime patch + feat_4h_dist_swing_low uplift）

- verdict: **joint_component_experiment_improves_but_still_below_floor**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- best scenario: **exact_lane_p75** → entry_quality **0.3729** / layers **0** / gap **0.1771**
- required_bias50_cap_after_best_scenario: **-1.7085**
- note: 加入 feat_4h_dist_swing_low uplift 後，entry_quality 有改善，但 exact-supported q35 lane 仍低於 trade floor；下一步需要更強的 bias50 / base-mix closure，而不是只補結構 component。

## Base-mix component experiment（bias50 + pulse + nose）

- verdict: **base_mix_component_experiment_improves_but_still_below_floor**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- best scenario: **winner_triplet_p75** → entry_quality **0.5106** / layers **0** / gap **0.0394**
- required_bias50_cap_after_best_scenario: **0.5865**
- note: bias50 + pulse (+ nose) 的 base-mix uplift 明顯優於只補 structure component，但 current live row 仍未跨過 trade floor；下一輪需升級成 base-stack redesign blocker，而不是再做單點 component 微調。

## Recommended action

- base-mix experiment 已證明 bias50 + pulse (+ nose) uplift 仍未跨過 trade floor；下一輪必須升級成 base-stack redesign blocker，禁止再把結構 uplift 或單點 bias50 當成主 closure。
