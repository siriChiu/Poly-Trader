# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-21 05:35:21.001275**
- target: `simulated_pyramid_win`
- live path: **bull / CAUTION / C**
- signal: **HOLD** @ confidence **0.4885**
- layers: **1 → 0**
- allowed_layers_raw_reason: `entry_quality_C_single_layer`
- allowed_layers_reason: `under_minimum_exact_live_structure_bucket`
- execution_guardrail_reason: `under_minimum_exact_live_structure_bucket`
- runtime_blocker: `None` | reason: `None`
- deployment_blocker: `under_minimum_exact_live_structure_bucket` | reason: `current live structure bucket 已有 exact rows，但仍低於 deployment-grade minimum support；在 support 補滿前，runtime 只能維持 guardrail，不可把這條 lane 視為已可部署。`
- q15 exact-supported patch: **inactive** | support_route `exact_bucket_present_but_below_minimum` | floor_cross `None`
- runtime closure summary: **q35 discriminative redesign 已啟用並把 entry_quality 拉到 0.5517（raw layers=1），但最終 execution 仍被 under_minimum_exact_live_structure_bucket 擋住；目前不可把 patch active 誤讀成可部署。 exact-vs-spillover=同 regime 寬 scope 出現 bull|BLOCK spillover，77 rows / WR 0.0% / 品質 -0.260，明顯劣於 exact live lane WR — / 品質 —。**
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- recommended_patch: **core_plus_macro_plus_all_4h** / status `reference_only_until_exact_support_ready` / support_route `exact_bucket_present_but_below_minimum` / gap `38` / reference_scope `bull|CAUTION` / source `bull_4h_pocket_ablation.bull_collapse_q35`
- recommended_patch_features: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- recommended_patch_reason: 參考 patch 來自 bull|CAUTION（source: bull_4h_pocket_ablation.bull_collapse_q35），建議 profile=core_plus_macro_plus_all_4h；但 current live exact support 仍是 12/50；目前只能作治理 / 訓練參考，不可直接放行 runtime。
- recommended_patch_action: 維持部署 blocker；exact bucket 已出現但仍低於 minimum support，proxy 只可作治理參考。

## Entry-quality component breakdown

- final entry_quality: **0.5517** / trade_floor **0.55** / gap **0.0017**
- base_quality: **0.6119** × weight **0.75**
- structure_quality: **0.371** × weight **0.25**
- base components: feat_4h_bias50=0.2206 (w=0.0, contrib=0.0), feat_nose=0.3611 (w=0.6, contrib=0.2167), feat_pulse=0.5444 (w=0.0, contrib=0.0), feat_ear=0.9881 (w=0.4, contrib=0.3952)
- structure components: feat_4h_bb_pct_b=0.5952 (w=0.34, contrib=0.2024), feat_4h_dist_bb_lower=0.2284 (w=0.33, contrib=0.0754), feat_4h_dist_swing_low=0.2825 (w=0.33, contrib=0.0932)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0**
- base_group_max_entry_gain: **0.2911** | structure_group_max_entry_gain: **0.1573**
- best_single_component: **None**（group=None, Δscore≈None, max_gain≈None）
- single-component floor crossers: None
- bias50 fully relaxed: entry≈**0.6629** / layers≈**1** / required_bias50_cap≈**-0.718**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label` | 77 | 0.1558 | -0.1539 | 0.2956 | 0.7387 | 12 | True |
| exact `regime_label+regime_gate+entry_quality_label` | 0 | None | None | None | None | 0 | False |
| narrow `regime_label+entry_quality_label` | 0 | None | None | None | None | 0 | False |
| broad `regime_gate+entry_quality_label` | 3 | 1.0 | 0.7114 | 0.0118 | 0.0089 | 0 | False |

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
