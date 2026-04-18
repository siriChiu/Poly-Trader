# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-18 12:08:40.638156**
- target: `simulated_pyramid_win`
- live path: **bull / CAUTION / C**
- signal: **BUY** @ confidence **0.7646**
- layers: **1 → 0**
- allowed_layers_raw_reason: `entry_quality_C_single_layer`
- allowed_layers_reason: `decision_quality_below_trade_floor`
- execution_guardrail_reason: `decision_quality_below_trade_floor`
- runtime_blocker: `None` | reason: `None`
- deployment_blocker: `decision_quality_below_trade_floor` | reason: `current live structure bucket `CAUTION|structure_quality_caution|q15` 已完成 exact support closure（96/50），且 q15 patch 已啟用並把 raw entry 拉到 entry_quality=0.5500（raw layers=1），但 final execution 仍被 decision-quality trade floor 擋住；目前必須維持 patch_active_but_execution_blocked，不可把 q15 patch active 或 support closure 誤讀成 deployment closure。`
- q15 exact-supported patch: **active** | support_route `exact_bucket_supported` | floor_cross `legal_component_experiment_after_support_ready`
- runtime closure summary: **q15 patch 已啟用並把 entry_quality 拉到 0.5500（raw layers=1），但最終 execution 仍被 decision_quality_below_trade_floor 擋住；目前不可把 patch active 誤讀成可部署。**
- q15 patch machine-read: support_ready=True / entry_quality_ge_0_55=True / allowed_layers_gt_0=True / preserves_positive_discrimination_status=`verified_exact_lane_bucket_dominance`

## Entry-quality component breakdown

- final entry_quality: **0.55** / trade_floor **0.55** / gap **0.0**
- base_quality: **0.6448** × weight **0.75**
- structure_quality: **0.2656** × weight **0.25**
- base components: feat_4h_bias50=0.705 (w=0.4, contrib=0.282), feat_nose=0.7709 (w=0.18, contrib=0.1388), feat_pulse=0.3056 (w=0.27, contrib=0.0825), feat_ear=0.9437 (w=0.15, contrib=0.1416)
- structure components: feat_4h_bb_pct_b=0.3079 (w=0.34, contrib=0.1047), feat_4h_dist_bb_lower=0.1103 (w=0.33, contrib=0.0364), feat_4h_dist_swing_low=0.3772 (w=0.33, contrib=0.1245)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.2115**
- base_group_max_entry_gain: **0.4778** | structure_group_max_entry_gain: **0.1836**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.705, max_gain≈0.3）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.705)
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label` | 196 | 0.7041 | 0.3738 | 0.1263 | 0.3728 | 96 | False |
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
