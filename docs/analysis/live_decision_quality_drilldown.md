# Live Decision-Quality Drilldown

- feature_timestamp: **2026-05-02 08:03:30.194504**
- target: `simulated_pyramid_win`
- live path: **chop / CAUTION / D**
- signal: **HOLD** @ confidence **0.3549**
- layers: **0 → 0**
- allowed_layers_raw_reason: `entry_quality_below_trade_floor`
- allowed_layers_reason: `under_minimum_exact_live_structure_bucket`
- execution_guardrail_reason: `under_minimum_exact_live_structure_bucket`
- runtime_blocker: `None` | reason: `None`
- deployment_blocker: `under_minimum_exact_live_structure_bucket` | reason: `current live structure bucket 已有 exact rows，但仍低於 deployment-grade minimum support；在 support 補滿前，runtime 只能維持 guardrail，不可把這條 lane 視為已可部署。`
- support blocker summary: **exact support 26/50 (gap 24) 未達 current-live exact support；broader/proxy rows 僅可作治理參考。**
- support next action: 保持 no-deploy；先累積或回放同一 current-live structure bucket 的 exact lane 樣本，不可用 broader/proxy support 放行。
- q15 exact-supported patch: **inactive** | support_route `exact_bucket_present_but_below_minimum` | floor_cross `None`
- runtime closure summary: **current live bucket CAUTION|base_caution_regime_or_bias|q35 的 exact support 仍未就緒（26/50，route=exact_bucket_present_but_below_minimum / governance=exact_live_bucket_present_but_below_minimum）；broader / proxy rows 目前都只屬 reference-only 治理，不可視為 deployment closure。 blocker=current live structure bucket 已有 exact rows，但仍低於 deployment-grade minimum support；在 support 補滿前，runtime 只能維持 guardrail，不可把這條 lane 視為已可部署。. exact-vs-spillover=同 quality 寬 scope 出現 bear|CAUTION spillover，22 rows / WR 50.0% / 品質 0.169，明顯劣於 exact live lane WR 73.1% / 品質 0.472。**
- q35 scaling audit: overall=`bias50_formula_may_be_too_harsh` / redesign=`base_stack_redesign_discriminative_reweight_crosses_floor_but_execution_blocked` / runtime_gap=`0.1406` / mode=`exact_lane_formula_review` / next_patch=`feat_4h_bias50_formula`
- q35 audit action: discriminative base-stack redesign 只能讓 entry_quality 跨過 scoring floor，runtime gate/support 仍讓 allowed_layers=0；下一輪必須把它治理成 score-only / execution-blocked，不得把 floor-cross 當成 deployment closure。
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- recommended_patch: **None** / status `None` / support_route `None` / gap `None` / reference_scope `None` / source `None`
- recommended_patch_features: None
- recommended_patch_reason: None
- recommended_patch_action: None

## Entry-quality component breakdown

- final entry_quality: **0.4094** / trade_floor **0.55** / gap **-0.1406**
- base_quality: **0.4202** × weight **0.75**
- structure_quality: **0.377** × weight **0.25**
- base components: feat_4h_bias50=0.2457 (w=0.4, contrib=0.0983), feat_nose=0.5534 (w=0.18, contrib=0.0996), feat_pulse=0.2726 (w=0.27, contrib=0.0736), feat_ear=0.9909 (w=0.15, contrib=0.1486)
- structure components: feat_4h_bb_pct_b=0.5506 (w=0.34, contrib=0.1872), feat_4h_dist_bb_lower=0.1577 (w=0.33, contrib=0.0521), feat_4h_dist_swing_low=0.4174 (w=0.33, contrib=0.1377)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.1406**
- base_group_max_entry_gain: **0.4349** | structure_group_max_entry_gain: **0.1558**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.4687, max_gain≈0.2263）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.4687), feat_pulse (Δscore≈0.6943)
- bias50 fully relaxed: entry≈**0.6356** / layers≈**1** / required_bias50_cap≈**-1.172**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_gate+entry_quality_label` | 48 | 0.625 | 0.3331 | 0.1717 | 0.3956 | 26 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 26 | 0.7308 | 0.4721 | 0.1156 | 0.3598 | 26 | False |
| narrow `regime_label+entry_quality_label` | 26 | 0.7308 | 0.4721 | 0.1156 | 0.3598 | 26 | False |
| broad `regime_gate+entry_quality_label` | 48 | 0.625 | 0.3331 | 0.1717 | 0.3956 | 26 | False |

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
