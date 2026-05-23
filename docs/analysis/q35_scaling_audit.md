# Q35 Scaling Audit

- generated_at: **2026-05-23 23:10:26.702615**
- overall_verdict: **hold_only_bias50_overheat_confirmed**
- structure_scaling_verdict: **q35_structure_caution_not_root_cause**
- scope_applicability: **current_live_q35_lane_active**
- reason: 只把 q35 CAUTION 改回 ALLOW 仍無法增加層數；而 current bias50 不只高於 exact-lane p90，也高於更廣 bull cohorts 的 p90，代表主要是 bias50 過熱，不是 q35 結構縮放把可交易 lane 誤殺。
- applicability_note: current live row 仍位於 q35 lane；本輪 q35 scaling / bias50 calibration 結論可直接視為 live governance 主路徑。

## Current live row

- regime/gate/quality: **bear / CAUTION / C**
- structure_bucket: **CAUTION|base_caution_regime_or_bias|q35**
- legacy_entry_quality: **0.5842** (raw_reason=`entry_quality_C_single_layer`)
- calibration_runtime_entry_quality: **0.5842** (raw_reason=`entry_quality_C_single_layer`)
- deployed_runtime_entry_quality: **0.5842** (raw_reason=`entry_quality_C_single_layer`, effective_reason=`unsupported_exact_live_structure_bucket`)
- q35_discriminative_redesign_applied: **False**
- feat_4h_bias50: **-0.721**
- structure_quality: **0.4448**

## Exact lane summary

- rows: **3** | win_rate: **1.0**
- bias50 distribution: {'min': -2.0431, 'p25': -2.0431, 'p50': -2.0241, 'p75': -2.0204, 'p90': -2.0204, 'p95': -2.0204, 'max': -2.0204, 'mean': -2.0292}
- current bias50 percentile in exact lane: **1.0**
- winner-only bias50 distribution: {'min': -2.0431, 'p25': -2.0431, 'p50': -2.0241, 'p75': -2.0204, 'p90': -2.0204, 'p95': -2.0204, 'max': -2.0204, 'mean': -2.0292}

## Broader bull cohorts

- same_gate_same_quality: rows=**300** | win_rate=**0.56** | bias50_pct=**0.9933** | dist={'min': -4.1725, 'p25': -3.091, 'p50': -2.6515, 'p75': -2.0875, 'p90': -1.3774, 'p95': -1.1247, 'max': -0.4535, 'mean': -2.5562}
- same_bucket: rows=**3** | win_rate=**1.0** | bias50_pct=**1.0** | dist={'min': -2.0431, 'p25': -2.0431, 'p50': -2.0241, 'p75': -2.0204, 'p90': -2.0204, 'p95': -2.0204, 'max': -2.0204, 'mean': -2.0292}
- bull_all: rows=**634** | win_rate=**0.6215** | bias50_pct=**0.9763** | dist={'min': -7.8921, 'p25': -2.9137, 'p50': -2.4012, 'p75': -1.3593, 'p90': -1.1554, 'p95': -0.9936, 'max': -0.2201, 'mean': -2.3116}

## Segmented calibration

- status: **hold_only_confirmed** | mode: **keep_hold_only**
- runtime contract: **piecewise_runtime_not_required** — 本輪 audit 沒有要求 current row 套用 segmented calibration；runtime 可維持既有路徑。
- exact lane band: **overheat** (pct=1.0, Δp90=1.2994)
- same_gate_same_quality band: **overheat** (pct=0.9933, Δp90=0.6564)
- same_bucket band: **overheat** (pct=1.0, Δp90=1.2994)
- bull_all band: **overheat** (pct=0.9763, Δp90=0.4344)
- reference cohort: **None** / label=None / pct=None
- note: current bias50 高於所有候選 cohorts 的 p90，沒有可用的分段校準參考 cohort。
- runtime preview: applied=**False** | score=**0.6242** | legacy=**0.6242** | Δ=**0.0** | segment=**None**

## Deployment-grade component experiment

- verdict: **runtime_patch_crosses_floor_but_execution_blocked**
- baseline -> calibration runtime entry_quality: **0.5842 → 0.5842** (Δ=**0.0**)
- baseline -> deployed runtime entry_quality: **0.5842 → 0.5842** (Δ=**0.0**)
- baseline -> calibration -> deployed layers: **1 → 1 → 1**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**False**
- runtime_source: **live_predict_probe** | q35_discriminative_redesign_applied=**False**
- runtime gap to floor: **-0.0342**
- next patch target: **feat_4h_bias50_formula**

## Counterfactuals

- gate -> ALLOW only: entry_quality **0.5842**, layers **1**
- fully relax bias50 penalty: entry_quality **0.697**, layers **2**
- required bias50 cap to cross trade floor: **-0.721** (current=-0.721)

## Joint component experiment（bias50 runtime patch + feat_4h_dist_swing_low uplift）

- verdict: **joint_component_experiment_crosses_trade_floor**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**True**
- best scenario: **winner_p75** → entry_quality **0.597** / layers **1** / gap **0.0**
- required_bias50_cap_after_best_scenario: **-0.721**
- note: 在維持 runtime bias50 calibration 的前提下，只把 feat_4h_dist_swing_low 拉回 exact-supported q35 lane 的 support target，就足以跨過 trade floor。

## Exact-supported bias50 component experiment

- verdict: **exact_supported_bias50_component_crosses_trade_floor**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**True** | used_exact_supported_target=**True**
- best scenario: **winner_runtime_p75** → entry_quality **0.6635** / layers **1** / gap **0.0** / target_score **0.8886**
- note: 只把 feat_4h_bias50 拉到 exact-supported / winner-supported runtime 分位，就足以跨過 trade floor。

## Base-mix component experiment（bias50 + pulse + nose）

- verdict: **base_mix_component_experiment_crosses_trade_floor**
- machine_read: entry_quality>=0.55=**True** | allowed_layers>0=**True**
- best scenario: **winner_triplet_p75** → entry_quality **0.6705** / layers **1** / gap **0.0**
- required_bias50_cap_after_best_scenario: **-2.043**
- note: 在保留 current q35 結構與 runtime bias50 calibration 的前提下，只把 bias50 + pulse (+ nose) 拉回 exact/winner cohort 的支持分位，就足以跨過 trade floor。

## Base-stack redesign experiment（support-aware discriminative reweight）

- verdict: **base_stack_redesign_candidate_grid_empty**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False** | positive_gap=**False** | execution_blocked_after_floor_cross=**None**
- rows / wins / losses: **3 / 3 / 0**
- best discriminative candidate: weights=**None** → entry_quality **None** / gap **None** / mean_gap **None**
- best floor candidate: weights=**None** → entry_quality **None** / gap **None** / mean_gap **None**
- unsafe floor-cross candidate: **None**
- note: runtime exact lane grid search 沒有產生任何可比較候選。

## Recommended action

- 把這條 current bull q35 lane 正式治理成 hold-only 候選；除非 bias50 校準審計證明 current 值屬於 exact-lane常態，否則不要直接放寬 trade floor 或 q35 gate。
