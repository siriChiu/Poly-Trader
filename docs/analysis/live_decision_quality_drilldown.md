# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-20 21:10:05.044722**
- target: `simulated_pyramid_win`
- live path: **bull / CAUTION / D**
- signal: **HOLD** @ confidence **0.5069**
- layers: **0 → 0**
- allowed_layers_raw_reason: `entry_quality_below_trade_floor`
- allowed_layers_reason: `under_minimum_exact_live_structure_bucket`
- execution_guardrail_reason: `under_minimum_exact_live_structure_bucket`
- runtime_blocker: `None` | reason: `None`
- deployment_blocker: `under_minimum_exact_live_structure_bucket` | reason: `current live structure bucket 已有 exact rows，但仍低於 deployment-grade minimum support；在 support 補滿前，runtime 只能維持 guardrail，不可把這條 lane 視為已可部署。`
- q15 exact-supported patch: **inactive** | support_route `exact_bucket_present_but_below_minimum` | floor_cross `None`
- runtime closure summary: **current live bucket CAUTION|structure_quality_caution|q35 的 exact support 仍未就緒（12/50，route=exact_bucket_present_but_below_minimum / governance=exact_live_bucket_present_but_below_minimum）；broader / proxy rows 與 recommended patch 目前都只屬 reference-only 治理，不可視為 deployment closure。 recommended_patch=core_plus_macro_plus_all_4h (reference_only_until_exact_support_ready). blocker=current live structure bucket 已有 exact rows，但仍低於 deployment-grade minimum support；在 support 補滿前，runtime 只能維持 guardrail，不可把這條 lane 視為已可部署。. exact-vs-spillover=同 quality 寬 scope 出現 bull|BLOCK spillover，188 rows / WR 0.0% / 品質 -0.230，明顯劣於 exact live lane WR 100.0% / 品質 0.419。**
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- recommended_patch: **core_plus_macro_plus_all_4h** / status `reference_only_until_exact_support_ready` / support_route `exact_bucket_present_but_below_minimum` / gap `38` / reference_scope `bull|CAUTION` / source `bull_4h_pocket_ablation.bull_collapse_q35`
- recommended_patch_features: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- recommended_patch_reason: 參考 patch 來自 bull|CAUTION（source: bull_4h_pocket_ablation.bull_collapse_q35），建議 profile=core_plus_macro_plus_all_4h；但 current live exact support 仍是 12/50；目前只能作治理 / 訓練參考，不可直接放行 runtime。
- recommended_patch_action: 維持 0 layers；優先查 exact bucket 缺口與 same-bucket pathology，而不是再重訓。

## Entry-quality component breakdown

- final entry_quality: **0.4571** / trade_floor **0.55** / gap **-0.0929**
- base_quality: **0.4542** × weight **0.75**
- structure_quality: **0.466** × weight **0.25**
- base components: feat_4h_bias50=0.0982 (w=0.4, contrib=0.0393), feat_nose=0.5057 (w=0.18, contrib=0.091), feat_pulse=0.6451 (w=0.27, contrib=0.1742), feat_ear=0.9978 (w=0.15, contrib=0.1497)
- structure components: feat_4h_bb_pct_b=0.7746 (w=0.34, contrib=0.2634), feat_4h_dist_bb_lower=0.2976 (w=0.33, contrib=0.0982), feat_4h_dist_swing_low=0.3164 (w=0.33, contrib=0.1044)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0929**
- base_group_max_entry_gain: **0.4093** | structure_group_max_entry_gain: **0.1335**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.3097, max_gain≈0.2705）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.3097)
- bias50 fully relaxed: entry≈**0.7382** / layers≈**2** / required_bias50_cap≈**0.5375**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `entry_quality_label` | 200 | 0.295 | -0.0224 | 0.2884 | 0.6826 | 12 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 12 | 1.0 | 0.4193 | 0.3774 | 0.734 | 12 | False |
| narrow `regime_label+entry_quality_label` | 123 | 0.0976 | -0.1669 | 0.2564 | 0.7181 | 12 | True |
| broad `regime_gate+entry_quality_label` | 89 | 0.6629 | 0.2367 | 0.3446 | 0.6406 | 12 | False |

## Shared shifts

- None
- worst_pathology_scope: **regime_label+entry_quality_label** rows=123 win_rate=0.0976 quality=-0.1669

## Interpretation

- if `runtime_blocker.type=circuit_breaker`, the current live row is blocked before the decision-quality contract is evaluated; treat q35/q15 diagnostics as background research, not deployable live routing.
- if `deployment_blocker.type=bull_q35_no_deploy_governance`, the current bull q35 lane is exact-supported but still not deployable because only non-discriminative unsafe reweight can cross the floor; do not describe it as simple support shortage or generic floor gap.
- if `q15_exact_supported_component_patch_applied=true` while `signal=HOLD`, describe the state as 'capacity opened but signal still HOLD' — not as patch missing, and not as automatic BUY readiness.
- exact live lane and chosen scope are separated on purpose: if exact lane is tiny or lacks current structure-bucket support, runtime must not trust it blindly.
- broader same-gate scope is still useful only as a structure-bucket fallback, not as the primary semantic representative of the live bull path.
- if the shared shift set remains dominated by `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`, the next fix should stay on 4H structure collapse rather than generic calibration tuning.
