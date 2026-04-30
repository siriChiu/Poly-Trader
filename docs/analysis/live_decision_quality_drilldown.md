# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-30 04:01:27.744662**
- target: `simulated_pyramid_win`
- live path: **bear / CAUTION / D**
- signal: **HOLD** @ confidence **0.4053**
- layers: **0 → 0**
- allowed_layers_raw_reason: `entry_quality_below_trade_floor`
- allowed_layers_reason: `under_minimum_exact_live_structure_bucket`
- execution_guardrail_reason: `under_minimum_exact_live_structure_bucket`
- runtime_blocker: `None` | reason: `None`
- deployment_blocker: `under_minimum_exact_live_structure_bucket` | reason: `current live structure bucket 已有 exact rows，但仍低於 deployment-grade minimum support；在 support 補滿前，runtime 只能維持 guardrail，不可把這條 lane 視為已可部署。`
- q15 exact-supported patch: **inactive** | support_route `exact_bucket_present_but_below_minimum` | floor_cross `math_cross_possible_but_illegal_without_exact_support`
- runtime closure summary: **current live bucket CAUTION|structure_quality_caution|q15 的 exact support 仍未就緒（10/50，route=exact_bucket_present_but_below_minimum / governance=exact_live_bucket_present_but_below_minimum）；broader / proxy rows 與 recommended patch 目前都只屬 reference-only 治理，不可視為 deployment closure。 recommended_patch=core_plus_macro_plus_all_4h (reference_only_non_current_live_scope). blocker=current live structure bucket 已有 exact rows，但仍低於 deployment-grade minimum support；在 support 補滿前，runtime 只能維持 guardrail，不可把這條 lane 視為已可部署。. exact-vs-spillover=同 gate 寬 scope 出現 bull|CAUTION spillover，90 rows / WR 0.0% / 品質 -0.301，明顯劣於 exact live lane WR 20.0% / 品質 -0.063。**
- q35 scaling audit: overall=`None` / redesign=`None` / runtime_gap=`None` / mode=`None` / next_patch=`None`
- q35 audit action: None
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- recommended_patch: **core_plus_macro_plus_all_4h** / status `reference_only_non_current_live_scope` / support_route `exact_bucket_present_but_below_minimum` / gap `40` / reference_scope `bull|CAUTION` / source `live_scope_spillover`
- recommended_patch_features: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- recommended_patch_reason: 參考 patch 來自 bull|CAUTION（source: live_scope_spillover），但 current live scope 是 bear|CAUTION；這代表 patch 描述的是 spillover / broader lane，而不是目前 current-live row 的 deploy patch。 current live exact support 目前仍是 10/50，因此這條 patch 同時不具備 same-scope 與 exact-support 放行條件。 即使 exact support 已達 minimum rows，也只能作治理 / 訓練參考，不可直接放行 runtime。
- recommended_patch_action: 維持 reference-only patch 可見性；目前 current live 是 bear|CAUTION，但 patch 來自 bull|CAUTION spillover。 在 scope 對齊前，只可作治理 / 訓練參考，不可把它升級成 current-live deploy patch。

## Entry-quality component breakdown

- final entry_quality: **0.5369** / trade_floor **0.55** / gap **-0.0131**
- base_quality: **0.6475** × weight **0.75**
- structure_quality: **0.2051** × weight **0.25**
- base components: feat_4h_bias50=0.8697 (w=0.4, contrib=0.3479), feat_nose=0.4353 (w=0.18, contrib=0.0784), feat_pulse=0.2773 (w=0.27, contrib=0.0749), feat_ear=0.9756 (w=0.15, contrib=0.1463)
- structure components: feat_4h_bb_pct_b=0.4215 (w=0.34, contrib=0.1433), feat_4h_dist_bb_lower=0.1486 (w=0.33, contrib=0.0491), feat_4h_dist_swing_low=0.0386 (w=0.33, contrib=0.0127)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0131**
- base_group_max_entry_gain: **0.2643** | structure_group_max_entry_gain: **0.1987**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.0437, max_gain≈0.0391）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.0437), feat_pulse (Δscore≈0.0647), feat_nose (Δscore≈0.097), feat_4h_bb_pct_b (Δscore≈0.1541)
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `global` | 100 | 0.25 | -0.0501 | 0.2483 | 0.6341 | 16 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 10 | 0.2 | -0.0629 | 0.2716 | 0.3884 | 10 | False |
| narrow `regime_label+entry_quality_label` | 10 | 0.2 | -0.0629 | 0.2716 | 0.3884 | 10 | False |
| broad `regime_gate+entry_quality_label` | 82 | 0.1585 | -0.1482 | 0.2815 | 0.7057 | 14 | True |

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
