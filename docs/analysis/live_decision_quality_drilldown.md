# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-22 03:05:43.313975**
- target: `simulated_pyramid_win`
- live path: **bull / BLOCK / D**
- signal: **HOLD** @ confidence **0.5509**
- layers: **0 → 0**
- allowed_layers_raw_reason: `regime_gate_block`
- allowed_layers_reason: `unsupported_exact_live_structure_bucket`
- execution_guardrail_reason: `unsupported_exact_live_structure_bucket`
- runtime_blocker: `None` | reason: `None`
- deployment_blocker: `unsupported_exact_live_structure_bucket` | reason: `current live structure bucket 缺少 exact live lane 歷史支持；在 exact bucket 出現前，broader / proxy rows 只能作治理參考，不可作 deployment 放行依據。`
- q15 exact-supported patch: **inactive** | support_route `exact_bucket_unsupported_block` | floor_cross `None`
- runtime closure summary: **current live bucket BLOCK|bull_high_bias200_overheat_block|q35 的 exact support 仍未就緒（0/50，route=exact_bucket_unsupported_block / governance=no_support_proxy）；broader / proxy rows 與 recommended patch 目前都只屬 reference-only 治理，不可視為 deployment closure。 recommended_patch=core_plus_macro_plus_all_4h (reference_only_until_exact_support_ready). blocker=current live structure bucket 缺少 exact live lane 歷史支持；在 exact bucket 出現前，broader / proxy rows 只能作治理參考，不可作 deployment 放行依據。. exact-vs-spillover=同 quality 寬 scope 出現 bull|CAUTION spillover，197 rows / WR 40.0% / 品質 0.037，明顯劣於 exact live lane WR — / 品質 —。**
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- recommended_patch: **core_plus_macro_plus_all_4h** / status `reference_only_until_exact_support_ready` / support_route `exact_bucket_unsupported_block` / gap `50` / reference_scope `bull|CAUTION` / source `live_scope_spillover`
- recommended_patch_features: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- recommended_patch_reason: 參考 patch 來自 bull|CAUTION（source: live_scope_spillover），建議 profile=core_plus_macro_plus_all_4h；但 current live exact support 仍是 0/50；目前只能作治理 / 訓練參考，不可直接放行 runtime。
- recommended_patch_action: 維持 reference-only patch truth；current live exact support 0/50 尚未達標，patch 只可作治理 / 訓練參考。

## Entry-quality component breakdown

- final entry_quality: **0.4467** / trade_floor **0.55** / gap **-0.1033**
- base_quality: **0.3805** × weight **0.75**
- structure_quality: **0.6453** × weight **0.25**
- base components: feat_4h_bias50=0.0 (w=0.4, contrib=0.0), feat_nose=0.1654 (w=0.18, contrib=0.0298), feat_pulse=0.7923 (w=0.27, contrib=0.2139), feat_ear=0.9122 (w=0.15, contrib=0.1368)
- structure components: feat_4h_bb_pct_b=1.0 (w=0.34, contrib=0.34), feat_4h_dist_bb_lower=0.4249 (w=0.33, contrib=0.1402), feat_4h_dist_swing_low=0.5002 (w=0.33, contrib=0.1651)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.1033**
- base_group_max_entry_gain: **0.4647** | structure_group_max_entry_gain: **0.0886**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.3443, max_gain≈0.3）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.3443), feat_nose (Δscore≈0.7652)
- bias50 fully relaxed: entry≈**0.7467** / layers≈**0** / required_bias50_cap≈**0.6785**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+entry_quality_label` | 70 | 0.4 | 0.0375 | 0.2541 | 0.6557 | 0 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 0 | None | None | None | None | 0 | False |
| narrow `regime_label+entry_quality_label` | 70 | 0.4 | 0.0375 | 0.2541 | 0.6557 | 0 | False |
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
