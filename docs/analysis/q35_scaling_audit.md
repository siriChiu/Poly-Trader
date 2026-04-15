# Q35 Scaling Audit

- generated_at: **2026-04-15 11:50:55.689653**
- overall_verdict: **bias50_formula_may_be_too_harsh**
- structure_scaling_verdict: **q35_structure_caution_not_root_cause**
- scope_applicability: **current_live_q35_lane_active**
- reason: current bias50 已回到 exact-lane p90 內，但 legacy 公式仍可能把它壓成 0 分；需改做 exact-lane 內的保守分段校準，而不是繼續把它視為 broader bull segmentation 問題。
- applicability_note: current live row 仍位於 q35 lane；本輪 q35 scaling / bias50 calibration 結論可直接視為 live governance 主路徑。

## Current live row

- regime/gate/quality: **bull / CAUTION / D**
- structure_bucket: **CAUTION|structure_quality_caution|q35**
- legacy_entry_quality: **0.4218** (reason=`entry_quality_below_trade_floor`)
- runtime_entry_quality: **0.4919** (reason=`entry_quality_below_trade_floor`)
- feat_4h_bias50: **2.8867**
- structure_quality: **0.3887**

## Exact lane summary

- rows: **126** | win_rate: **0.9524**
- bias50 distribution: {'min': 1.6545, 'p25': 2.7464, 'p50': 2.9576, 'p75': 4.0464, 'p90': 4.2197, 'p95': 4.2326, 'max': 4.5647, 'mean': 3.1132}
- current bias50 percentile in exact lane: **0.3968**
- winner-only bias50 distribution: {'min': 1.6545, 'p25': 2.7178, 'p50': 2.9474, 'p75': 3.4661, 'p90': 4.2088, 'p95': 4.2231, 'max': 4.2354, 'mean': 3.0497}

## Broader bull cohorts

- same_gate_same_quality: rows=**140** | win_rate=**0.8857** | bias50_pct=**0.4357** | dist={'min': -1.1489, 'p25': 2.5728, 'p50': 2.947, 'p75': 3.8185, 'p90': 4.2124, 'p95': 4.2258, 'max': 4.5647, 'mean': 2.8763}
- same_bucket: rows=**127** | win_rate=**0.9528** | bias50_pct=**0.3937** | dist={'min': 1.6545, 'p25': 2.7542, 'p50': 2.9632, 'p75': 4.0169, 'p90': 4.2197, 'p95': 4.2326, 'max': 4.5647, 'mean': 3.1203}
- bull_all: rows=**441** | win_rate=**0.6599** | bias50_pct=**0.4853** | dist={'min': -1.1554, 'p25': 2.0452, 'p50': 2.9328, 'p75': 4.2808, 'p90': 4.4404, 'p95': 5.1867, 'max': 9.36, 'mean': 2.9542}

## Segmented calibration

- status: **formula_review_required** | mode: **exact_lane_formula_review**
- runtime contract: **piecewise_runtime_active** — piecewise bias50 calibration 已由 predictor / q35 audit 實際套用到 current bull q35 lane；後續 heartbeat 不得再把這題描述成 runtime 尚未吃到新公式。
- exact lane band: **core_normal** (pct=0.3968, Δp90=-1.333)
- same_gate_same_quality band: **core_normal** (pct=0.4357, Δp90=-1.3257)
- same_bucket band: **core_normal** (pct=0.3937, Δp90=-1.333)
- bull_all band: **core_normal** (pct=0.4853, Δp90=-1.5537)
- reference cohort: **same_gate_same_quality** / label=同 bull gate + 同 quality lane / pct=0.4357
- note: current bias50 已回到 exact lane p90 內；下一步應做 exact-lane 內的保守 bias50 校準 / 公式檢查，而不是再走 broader bull segmentation。
- runtime preview: applied=**True** | score=**0.2335** | legacy=**0.0** | Δ=**0.2335** | segment=**exact_lane_supported_within_p75**

## Deployment-grade component experiment

- verdict: **runtime_patch_improves_but_still_below_floor**
- baseline -> runtime entry_quality: **0.4218 → 0.4919** (Δ=**0.0701**)
- baseline -> runtime layers: **0 → 0**
- machine_read: entry_quality>=0.55=**False** | allowed_layers>0=**False**
- runtime gap to floor: **0.0581**
- next patch target: **feat_4h_bias50_formula**

## Counterfactuals

- gate -> ALLOW only: entry_quality **0.4218**, layers **0**
- fully relax bias50 penalty: entry_quality **0.7218**, layers **2**
- required bias50 cap to cross trade floor: **0.2635** (current=2.8867)

## Recommended action

- 維持 q35=CAUTION；把本輪焦點放在 bias50 正規化是否應改成分段/分位數縮放，只有當 current bias50 落在 exact-lane 常見區間時才放寬。
