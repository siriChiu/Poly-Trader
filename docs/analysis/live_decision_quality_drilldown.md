# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-17 00:54:21.709888**
- target: `simulated_pyramid_win`
- live path: **bull / CAUTION / C**
- signal: **HOLD** @ confidence **0.3245**
- layers: **1 → 1**
- allowed_layers_raw_reason: `entry_quality_C_single_layer`
- allowed_layers_reason: `entry_quality_C_single_layer`
- execution_guardrail_reason: `None`
- runtime_blocker: `None` | reason: `None`
- deployment_blocker: `None` | reason: `None`
- q15 exact-supported patch: **active** | support_route `exact_bucket_supported` | floor_cross `legal_component_experiment_after_support_ready`
- runtime closure summary: **support-ready + patch active；runtime 已開出 1 層 deployment capacity，但 signal 仍是 HOLD，不等於自動 BUY。**
- q15 patch machine-read: support_ready=True / entry_quality_ge_0_55=True / allowed_layers_gt_0=True / preserves_positive_discrimination_status=`verified_exact_lane_bucket_dominance`

## Entry-quality component breakdown

- final entry_quality: **0.55** / trade_floor **0.55** / gap **0.0**
- base_quality: **0.6303** × weight **0.75**
- structure_quality: **0.309** × weight **0.25**
- base components: feat_4h_bias50=0.8243 (w=0.4, contrib=0.3297), feat_nose=0.3542 (w=0.18, contrib=0.0638), feat_pulse=0.3571 (w=0.27, contrib=0.0964), feat_ear=0.936 (w=0.15, contrib=0.1404)
- structure components: feat_4h_bb_pct_b=0.5182 (w=0.34, contrib=0.1762), feat_4h_dist_bb_lower=0.2092 (w=0.33, contrib=0.069), feat_4h_dist_swing_low=0.1932 (w=0.33, contrib=0.0637)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0**
- base_group_max_entry_gain: **0.2773** | structure_group_max_entry_gain: **0.1728**
- best_single_component: **None**（group=None, Δscore≈None, max_gain≈None）
- single-component floor crossers: None
- bias50 fully relaxed: entry≈**0.5916** / layers≈**1** / required_bias50_cap≈**-1.9065**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label` | 200 | 0.91 | 0.4146 | 0.1096 | 0.2429 | 79 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 0 | None | None | None | None | 0 | False |
| narrow `regime_label+entry_quality_label` | 0 | None | None | None | None | 0 | False |
| broad `regime_gate+entry_quality_label` | 0 | None | None | None | None | 0 | False |

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
