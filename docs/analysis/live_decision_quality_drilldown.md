# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-30 00:02:24.247800**
- target: `simulated_pyramid_win`
- live path: **bear / CAUTION / C**
- signal: **HOLD** @ confidence **0.4804**
- layers: **1 → 0**
- allowed_layers_raw_reason: `entry_quality_C_single_layer`
- allowed_layers_reason: `unsupported_exact_live_structure_bucket`
- execution_guardrail_reason: `unsupported_exact_live_structure_bucket`
- runtime_blocker: `None` | reason: `None`
- deployment_blocker: `unsupported_exact_live_structure_bucket` | reason: `current live structure bucket 缺少 exact live lane 歷史支持；在 exact bucket 出現前，broader / proxy rows 只能作治理參考，不可作 deployment 放行依據。`
- q15 exact-supported patch: **inactive** | support_route `insufficient_support_everywhere` | floor_cross `floor_crossed_but_support_not_ready`
- runtime closure summary: **current live bucket CAUTION|structure_quality_caution|q15 的 exact support 仍未就緒（0/50，route=insufficient_support_everywhere / governance=exact_live_lane_proxy_available）；broader / proxy rows 目前都只屬 reference-only 治理，不可視為 deployment closure。 blocker=current live structure bucket 缺少 exact live lane 歷史支持；在 exact bucket 出現前，broader / proxy rows 只能作治理參考，不可作 deployment 放行依據。. exact-vs-spillover=同 gate 寬 scope 出現 bear|CAUTION spillover，256 rows / WR 11.1% / 品質 -0.108，明顯劣於 exact live lane WR — / 品質 —。**
- q35 scaling audit: overall=`None` / redesign=`None` / runtime_gap=`None` / mode=`None` / next_patch=`None`
- q35 audit action: None
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- recommended_patch: **None** / status `None` / support_route `None` / gap `None` / reference_scope `None` / source `None`
- recommended_patch_features: None
- recommended_patch_reason: None
- recommended_patch_action: None

## Entry-quality component breakdown

- final entry_quality: **0.5537** / trade_floor **0.55** / gap **0.0037**
- base_quality: **0.6868** × weight **0.75**
- structure_quality: **0.1543** × weight **0.25**
- base components: feat_4h_bias50=0.9058 (w=0.4, contrib=0.3623), feat_nose=0.5596 (w=0.18, contrib=0.1007), feat_pulse=0.3346 (w=0.27, contrib=0.0903), feat_ear=0.8895 (w=0.15, contrib=0.1334)
- structure components: feat_4h_bb_pct_b=0.3232 (w=0.34, contrib=0.1099), feat_4h_dist_bb_lower=0.1135 (w=0.33, contrib=0.0375), feat_4h_dist_swing_low=0.0209 (w=0.33, contrib=0.0069)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0**
- base_group_max_entry_gain: **0.2349** | structure_group_max_entry_gain: **0.2114**
- best_single_component: **None**（group=None, Δscore≈None, max_gain≈None）
- single-component floor crossers: None
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_gate` | 256 | 0.5078 | 0.1515 | 0.156 | 0.5348 | 36 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 0 | None | None | None | None | 0 | False |
| narrow `regime_label+entry_quality_label` | 0 | None | None | None | None | 0 | False |
| broad `regime_gate+entry_quality_label` | 16 | 0.75 | 0.4672 | 0.0656 | 0.2801 | 0 | False |

## Shared shifts

- None
- worst_pathology_scope: **None** rows=None win_rate=None quality=None

## Interpretation

- if `runtime_blocker.type=circuit_breaker`, the current live row is blocked before the decision-quality contract is evaluated; treat q35/q15 diagnostics as background research, not deployable live routing.
- if `deployment_blocker.type=bull_q35_no_deploy_governance`, the current bull q35 lane is exact-supported but still not deployable because only non-discriminative unsafe reweight can cross the floor; do not describe it as simple support shortage or generic floor gap.
- if `q15_exact_supported_component_patch_applied=true` while `signal=HOLD`, describe the state as 'capacity opened but signal still HOLD' — not as patch missing, and not as automatic BUY readiness.
- exact live lane and chosen scope are separated on purpose: if exact lane is tiny or lacks current structure-bucket support, runtime must not trust it blindly.
- broader same-gate scope is still useful only as a structure-bucket fallback, not as the primary semantic representative of the live bull path.
- if the shared shift set remains dominated by `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`, the next fix should stay on 4H structure collapse rather than generic calibration tuning.
