# Live Decision-Quality Drilldown

- feature_timestamp: **2026-05-13 13:01:14.216904**
- target: `simulated_pyramid_win`
- live path: **chop / CAUTION / D**
- signal: **HOLD** @ confidence **0.2922**
- layers: **0 → 0**
- allowed_layers_raw_reason: `entry_quality_below_trade_floor`
- allowed_layers_reason: `under_minimum_exact_live_structure_bucket`
- execution_guardrail_reason: `under_minimum_exact_live_structure_bucket`
- runtime_blocker: `None` | reason: `None`
- deployment_blocker: `under_minimum_exact_live_structure_bucket` | reason: `current live structure bucket 已有 exact rows，但仍低於 deployment-grade minimum support；在 support 補滿前，runtime 只能維持 guardrail，不可把這條 lane 視為已可部署。`
- support blocker summary: **exact support 1/50 (gap 49) 未達 current-live exact support；broader/proxy rows 僅可作治理參考。**
- support next action: 保持 no-deploy；先累積或回放同一 current-live structure bucket 的 exact lane 樣本，不可用 broader/proxy support 放行。
- q15 exact-supported patch: **inactive** | support_route `exact_bucket_present_but_below_minimum` | floor_cross `None`
- runtime closure summary: **current live bucket CAUTION|base_caution_regime_or_bias|q00 的 exact support 仍未就緒（1/50，route=exact_bucket_present_but_below_minimum / governance=exact_live_bucket_present_but_below_minimum）；broader / proxy rows 目前都只屬 reference-only 治理，不可視為 deployment closure。 blocker=current live structure bucket 已有 exact rows，但仍低於 deployment-grade minimum support；在 support 補滿前，runtime 只能維持 guardrail，不可把這條 lane 視為已可部署。. exact-vs-spillover=同 regime 寬 scope 出現 chop|CAUTION spillover，4 rows / WR 75.0% / 品質 0.300，明顯劣於 exact live lane WR 63.5% / 品質 0.255。**
- q35 scaling audit: overall=`None` / redesign=`None` / runtime_gap=`None` / mode=`None` / next_patch=`None`
- q35 audit action: None
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- recommended_patch: **None** / status `None` / support_route `None` / gap `None` / reference_scope `None` / source `None`
- recommended_patch_features: None
- recommended_patch_reason: None
- recommended_patch_action: None

## Entry-quality component breakdown

- final entry_quality: **0.5076** / trade_floor **0.55** / gap **-0.0424**
- base_quality: **0.6392** × weight **0.75**
- structure_quality: **0.1127** × weight **0.25**
- base components: feat_4h_bias50=0.6286 (w=0.4, contrib=0.2515), feat_nose=0.6515 (w=0.18, contrib=0.1173), feat_pulse=0.4593 (w=0.27, contrib=0.124), feat_ear=0.9764 (w=0.15, contrib=0.1465)
- structure components: feat_4h_bb_pct_b=0.2252 (w=0.34, contrib=0.0766), feat_4h_dist_bb_lower=0.0546 (w=0.33, contrib=0.018), feat_4h_dist_swing_low=0.0551 (w=0.33, contrib=0.0182)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0424**
- base_group_max_entry_gain: **0.2706** | structure_group_max_entry_gain: **0.2219**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.1413, max_gain≈0.1114）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.1413), feat_pulse (Δscore≈0.2094), feat_nose (Δscore≈0.3141), feat_4h_bb_pct_b (Δscore≈0.4988)
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+regime_gate+entry_quality_label` | 96 | 0.6354 | 0.2554 | 0.097 | 0.3492 | 1 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 96 | 0.6354 | 0.2554 | 0.097 | 0.3492 | 1 | False |
| narrow `regime_label+entry_quality_label` | 96 | 0.6354 | 0.2554 | 0.097 | 0.3492 | 1 | False |
| broad `regime_gate+entry_quality_label` | 96 | 0.6354 | 0.2554 | 0.097 | 0.3492 | 1 | False |

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
