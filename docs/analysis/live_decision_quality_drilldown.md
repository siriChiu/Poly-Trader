# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-21 02:57:58.353169**
- target: `simulated_pyramid_win`
- live path: **chop / CAUTION / D**
- signal: **HOLD** @ confidence **0.1806**
- layers: **0 → 0**
- allowed_layers_raw_reason: `entry_quality_below_trade_floor`
- allowed_layers_reason: `decision_quality_below_trade_floor; exact_live_lane_toxic_sub_bucket_current_bucket_blocks_trade`
- execution_guardrail_reason: `decision_quality_below_trade_floor; exact_live_lane_toxic_sub_bucket_current_bucket_blocks_trade`
- runtime_blocker: `None` | reason: `None`
- deployment_blocker: `exact_live_lane_toxic_sub_bucket_current_bucket` | reason: `exact live lane current bucket `CAUTION|base_caution_regime_or_bias|q15` 已被標記為 toxic sub-bucket (rows=88, win_rate=0.6591, quality=0.2712)`
- q15 exact-supported patch: **inactive** | support_route `exact_bucket_supported` | floor_cross `legal_component_experiment_after_support_ready`
- runtime closure summary: **current live bucket CAUTION|base_caution_regime_or_bias|q15 已具 exact support，但 runtime 仍被 exact_live_lane_toxic_sub_bucket_current_bucket 擋住；exact live lane current bucket `CAUTION|base_caution_regime_or_bias|q15` 已被標記為 toxic sub-bucket (rows=88, win_rate=0.6591, quality=0.2712)。目前保持 hold-only，不可把 support closure 誤讀成 deployment closure。 exact-vs-spillover=同 quality 寬 scope 出現 bull|BLOCK spillover，93 rows / WR 0.0% / 品質 -0.244，明顯劣於 exact live lane WR 71.7% / 品質 0.341。**
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- recommended_patch: **None** / status `None` / support_route `None` / gap `None` / reference_scope `None` / source `None`
- recommended_patch_features: None
- recommended_patch_reason: None
- recommended_patch_action: None

## Entry-quality component breakdown

- final entry_quality: **0.5183** / trade_floor **0.55** / gap **-0.0317**
- base_quality: **0.579** × weight **0.75**
- structure_quality: **0.336** × weight **0.25**
- base components: feat_4h_bias50=0.2583 (w=0.4, contrib=0.1033), feat_nose=0.7632 (w=0.18, contrib=0.1374), feat_pulse=0.7058 (w=0.27, contrib=0.1906), feat_ear=0.9851 (w=0.15, contrib=0.1478)
- structure components: feat_4h_bb_pct_b=0.5411 (w=0.34, contrib=0.184), feat_4h_dist_bb_lower=0.2098 (w=0.33, contrib=0.0692), feat_4h_dist_swing_low=0.2509 (w=0.33, contrib=0.0828)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0317**
- base_group_max_entry_gain: **0.3158** | structure_group_max_entry_gain: **0.166**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.1057, max_gain≈0.2225）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.1057), feat_pulse (Δscore≈0.1565), feat_nose (Δscore≈0.2348), feat_4h_bb_pct_b (Δscore≈0.3729)
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+regime_gate+entry_quality_label` | 106 | 0.717 | 0.3408 | 0.2649 | 0.4923 | 88 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 106 | 0.717 | 0.3408 | 0.2649 | 0.4923 | 88 | False |
| narrow `regime_label+entry_quality_label` | 106 | 0.717 | 0.3408 | 0.2649 | 0.4923 | 88 | False |
| broad `regime_gate+entry_quality_label` | 118 | 0.7458 | 0.3488 | 0.2764 | 0.5168 | 88 | False |

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
