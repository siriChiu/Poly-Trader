# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-21 19:01:19.097308**
- target: `simulated_pyramid_win`
- live path: **bull / CAUTION / D**
- signal: **HOLD** @ confidence **0.4252**
- layers: **0 → 0**
- allowed_layers_raw_reason: `entry_quality_below_trade_floor`
- allowed_layers_reason: `unsupported_exact_live_structure_bucket`
- execution_guardrail_reason: `unsupported_exact_live_structure_bucket`
- runtime_blocker: `None` | reason: `None`
- deployment_blocker: `unsupported_exact_live_structure_bucket` | reason: `current live structure bucket 缺少 exact live lane 歷史支持；在 exact bucket 出現前，broader / proxy rows 只能作治理參考，不可作 deployment 放行依據。`
- q15 exact-supported patch: **inactive** | support_route `exact_bucket_missing_proxy_reference_only` | floor_cross `math_cross_possible_but_illegal_without_exact_support`
- runtime closure summary: **current live bucket CAUTION|structure_quality_caution|q15 的 exact support 仍未就緒（0/50，route=exact_bucket_missing_proxy_reference_only / governance=exact_live_bucket_proxy_available）；broader / proxy rows 與 recommended patch 目前都只屬 reference-only 治理，不可視為 deployment closure。 recommended_patch=core_plus_macro_plus_all_4h (reference_only_until_exact_support_ready). blocker=current live structure bucket 缺少 exact live lane 歷史支持；在 exact bucket 出現前，broader / proxy rows 只能作治理參考，不可作 deployment 放行依據。. exact-vs-spillover=同 quality 寬 scope 出現 bull|BLOCK spillover，169 rows / WR 0.0% / 品質 -0.180，明顯劣於 exact live lane WR 42.9% / 品質 0.047。**
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- recommended_patch: **core_plus_macro_plus_all_4h** / status `reference_only_until_exact_support_ready` / support_route `exact_bucket_missing_proxy_reference_only` / gap `50` / reference_scope `bull|CAUTION` / source `bull_4h_pocket_ablation.bull_collapse_q35`
- recommended_patch_features: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- recommended_patch_reason: 參考 patch 來自 bull|CAUTION（source: bull_4h_pocket_ablation.bull_collapse_q35），建議 profile=core_plus_macro_plus_all_4h；但 current live exact support 仍是 0/50；目前只能作治理 / 訓練參考，不可直接放行 runtime。
- recommended_patch_action: 維持部署 blocker；exact bucket 已出現但仍低於 minimum support，proxy 只可作治理參考。

## Entry-quality component breakdown

- final entry_quality: **0.4929** / trade_floor **0.55** / gap **-0.0571**
- base_quality: **0.5628** × weight **0.75**
- structure_quality: **0.2832** × weight **0.25**
- base components: feat_4h_bias50=0.3451 (w=0.4, contrib=0.138), feat_nose=0.5403 (w=0.18, contrib=0.0972), feat_pulse=0.6581 (w=0.27, contrib=0.1777), feat_ear=0.9993 (w=0.15, contrib=0.1499)
- structure components: feat_4h_bb_pct_b=0.4191 (w=0.34, contrib=0.1425), feat_4h_dist_bb_lower=0.1635 (w=0.33, contrib=0.054), feat_4h_dist_swing_low=0.2628 (w=0.33, contrib=0.0867)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0571**
- base_group_max_entry_gain: **0.3279** | structure_group_max_entry_gain: **0.1792**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.1903, max_gain≈0.1965）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.1903), feat_pulse (Δscore≈0.282), feat_nose (Δscore≈0.423), feat_4h_dist_bb_lower (Δscore≈0.6921)
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+entry_quality_label` | 33 | 0.3636 | 0.0128 | 0.3109 | 0.7672 | 0 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 28 | 0.4286 | 0.0472 | 0.3095 | 0.7497 | 0 | False |
| narrow `regime_label+entry_quality_label` | 33 | 0.3636 | 0.0128 | 0.3109 | 0.7672 | 0 | False |
| broad `regime_gate+entry_quality_label` | 192 | 0.7865 | 0.4159 | 0.1889 | 0.3725 | 0 | False |

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
